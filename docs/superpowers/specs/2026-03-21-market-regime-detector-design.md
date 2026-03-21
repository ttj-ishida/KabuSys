# 市場レジーム判定エンジン 設計仕様

- 対象 Issue: Phase 3 AI Analysis — 市場レジーム判定（`regime_score`）
- 作成日: 2026-03-21

---

## 1. 目的

市場全体が「買い向かうべき環境か（Bull）、撤退すべき環境か（Bear）か」を日次で判定し、
`market_regime` テーブルに書き込む。Strategy 層は Bear 判定時に新規買いシグナルを遮断する。

**`ai_scores.regime_score` との関係:**
`ai_scores` テーブルの `regime_score` カラムは今後も NULL のまま使用しない。
レジームの唯一の参照元は `market_regime` テーブルとする（日付単位・1行）。
`ai_scores.regime_score` カラムはスキーマから削除せず NULL 許容で残す（将来の拡張用）。

---

## 2. 判定根拠

| 指標 | データソース | 重み |
|------|-------------|------|
| 日経225 200日移動平均との乖離（ma200_ratio） | `prices_daily` の ETF 1321（日経225連動型） | 70% |
| マクロ経済ニュースの LLM センチメント（macro_sentiment） | `raw_news` からキーワードフィルタ → gpt-4o-mini | 30% |

VIX / 日経VI は今フェーズでは使用しない（別 Issue）。

**ニュースソースについて:**
`raw_news` を直接参照する。これは `news_nlp.py` と同じ方針であり、Raw Layer のニュース生データを
AI モジュールが直接消費する設計を統一している（Processed Layer の `news_articles` は使用しない）。

---

## 3. アーキテクチャ

### 3.1 新規ファイル

```
src/kabusys/ai/regime_detector.py   # メインモジュール（新規）
tests/test_regime_detector.py       # テスト（新規）
```

### 3.2 変更ファイル

```
src/kabusys/data/schema.py          # market_regime テーブル追加
```

### 3.3 ランタイム位置（RuntimeJobSchedule 18:00 AI Analysis）

```
score_news(conn, target_date)    # 既存：銘柄ごと sentiment_score → ai_scores
score_regime(conn, target_date)  # 新規：市場全体 regime_score   → market_regime
```

### 3.4 OpenAI API 呼び出し方針

`regime_detector.py` は `news_nlp.py` のプライベート関数 `_call_openai_api()` を
インポートせず、**同等の関数を `regime_detector.py` 内に独自実装する**。

理由: モジュール間でプライベート関数を共有すると結合度が上がり、
いずれかの変更が意図せず他方に影響するリスクがある。
将来的に共通化が必要になった場合は `kabusys.ai.openai_utils` などに切り出す。

---

## 4. データスキーマ

### 4.1 新テーブル `market_regime`

```sql
CREATE TABLE IF NOT EXISTS market_regime (
    date             DATE      NOT NULL PRIMARY KEY,
    regime_score     DOUBLE    NOT NULL,   -- -1.0〜1.0
    regime_label     VARCHAR   NOT NULL,   -- 'bull' / 'neutral' / 'bear'
    ma200_ratio      DOUBLE,               -- 1321終値 / 200日MA（診断用）
    macro_sentiment  DOUBLE,               -- LLMマクロスコア（診断用）
    created_at       TIMESTAMP NOT NULL DEFAULT current_timestamp
)
```

`regime_score` は日付単位で 1 行のみ。Strategy 層は `SELECT * FROM market_regime WHERE date = ?`
で取得する（JOIN 不要）。

---

## 5. 処理フロー

```
score_regime(conn, target_date, api_key=None) -> int
  │
  ├─ [1] API キー解決（引数 or 環境変数 OPENAI_API_KEY）
  │       未設定の場合 → ValueError を raise
  │
  ├─ [2] 1321 の終値を prices_daily から取得
  │       クエリ:
  │         SELECT date, close FROM prices_daily
  │         WHERE code = '1321' AND date < target_date
  │         ORDER BY date DESC LIMIT _MA_WINDOW
  │       ※ target_date 未満（排他）でルックアヘッドバイアスを防止
  │       ※ 結果を日付昇順に並び直して単純移動平均を計算
  │       → ma200_ratio = 最終行の close / avg(close)
  │       ※ データが _MA_WINDOW 日未満の場合 → ma200_ratio = 1.0（WARNING ログ）
  │
  ├─ [3] マクロニュース取得（news_nlp と同じ時間ウィンドウ）
  │       calc_news_window(target_date) → (window_start, window_end)
  │       クエリ:
  │         SELECT title FROM raw_news
  │         WHERE datetime >= window_start AND datetime < window_end
  │           AND (title LIKE '%日銀%' OR title LIKE '%Fed%' OR ...)
  │         ORDER BY datetime DESC LIMIT _MAX_MACRO_ARTICLES
  │       ※ 0 件の場合 → macro_sentiment = 0.0 でスキップ（LLM コールなし）
  │
  ├─ [4] OpenAI API コール（記事あり場合のみ）
  │       _call_openai_api(client, messages) → response
  │         ※ regime_detector 内に独自実装（news_nlp からはインポートしない）
  │         ※ model=_MODEL, response_format={"type": "json_object"},
  │            temperature=0, timeout=30
  │       リトライ: RateLimitError / APIConnectionError / APITimeoutError /
  │                 APIError(5xx) → 指数バックオフ（_MAX_RETRIES 回）
  │       出力: {"macro_sentiment": -0.7}
  │       失敗時: macro_sentiment = 0.0（WARNING ログ、処理継続）
  │
  ├─ [5] レジームスコア合成
  │       regime_score = clip(
  │           _MA_WEIGHT  * (ma200_ratio - 1.0) * _MA_SCALE
  │         + _MACRO_WEIGHT * macro_sentiment,
  │           -1.0, 1.0
  │       )
  │
  │       スケーリング根拠（_MA_SCALE = 10）:
  │         1321 が 200MA から ±10% 乖離したとき、MA 成分の寄与が
  │         ±0.7（_MA_WEIGHT）に飽和するよう設計。
  │         例: ma200_ratio=1.10 → 0.7*(0.10)*10 = +0.70
  │             ma200_ratio=0.95 → 0.7*(-0.05)*10 = -0.35
  │
  │       regime_label:
  │           score >= +_BULL_THRESHOLD → 'bull'
  │           score <= -_BEAR_THRESHOLD → 'bear'
  │           それ以外                  → 'neutral'
  │
  └─ [6] market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）
          書き込み失敗時は ROLLBACK して例外を上位に伝播
          戻り値: 1（成功）
```

---

## 6. 定数

```python
_ETF_CODE           = "1321"   # 日経225連動型 ETF
_MA_WINDOW          = 200      # 移動平均期間（日数）
_MA_SCALE           = 10       # MA乖離のスケーリング係数（±10%乖離で±MA_WEIGHT に飽和）
_MA_WEIGHT          = 0.7      # スコア合成での 200MA の重み
_MACRO_WEIGHT       = 0.3      # マクロセンチメントの重み
_BULL_THRESHOLD     = 0.2      # これ以上 → 'bull'
_BEAR_THRESHOLD     = 0.2      # これ以下（-0.2） → 'bear'
_MAX_MACRO_ARTICLES = 20       # LLM に渡すマクロ記事数上限
_MODEL              = "gpt-4o-mini"
_MAX_RETRIES        = 3
_RETRY_BASE_SECONDS = 1.0
```

---

## 7. マクロキーワード

```python
_MACRO_KEYWORDS = [
    # 日本
    "日銀", "日本銀行", "金利", "利上げ", "利下げ", "政策金利",
    "為替", "円安", "円高", "為替介入", "インフレ", "物価", "GDP",
    # 米国・グローバル
    "Fed", "FOMC", "CPI", "PPI", "雇用統計", "失業率",
    "米国債", "リセッション", "景気後退",
]
```

SQL では `OR title LIKE '%<keyword>%'` を動的に展開して使用する。

---

## 8. LLM プロンプト

```python
_SYSTEM_PROMPT = (
    "あなたは日本株の市場アナリストです。"
    "以下のマクロ経済ニュースを読み、日本株市場全体のセンチメントを "
    "-1.0〜1.0 のスコアで評価してください。"
    "1.0=非常にポジティブ（強気）、0.0=中立、-1.0=非常にネガティブ（弱気）。"
    '出力は厳密なJSONのみとしてください: {"macro_sentiment": 0.0}'
)
```

---

## 9. フェイルセーフ

| 状況 | 動作 |
|------|------|
| 1321 のデータが `_MA_WINDOW` 日未満 | `ma200_ratio = 1.0`（中立）で継続、WARNING ログ |
| マクロニュース 0 件 | `macro_sentiment = 0.0` で継続（LLM コールなし） |
| OpenAI API 失敗（全リトライ消費） | `macro_sentiment = 0.0` で継続、WARNING ログ |
| JSON パース失敗 | `macro_sentiment = 0.0` で継続、WARNING ログ |
| `api_key` 未設定かつ環境変数なし | `ValueError` を raise |
| DB 書き込み失敗 | ROLLBACK して例外を上位に伝播 |

---

## 10. テスト方針

| テスト名 | 検証内容 |
|----------|----------|
| `test_bear_by_ma` | 1321 が 200MA を下回る → `regime_label='bear'` |
| `test_bull_by_ma` | 1321 が 200MA を大きく上回る → `regime_label='bull'` |
| `test_macro_pushes_to_bear` | MA は中立（ratio=1.0）、マクロ LLM が -1.0 → 'bear' |
| `test_no_macro_news` | マクロニュースなし → `macro_sentiment=0.0`、MA のみで判定 |
| `test_insufficient_prices` | 1321 データが `_MA_WINDOW` 日未満 → `ma200_ratio=1.0` フォールバック |
| `test_idempotent` | 同日 2 回実行 → レコード 1 件、2 回目の値に更新 |
| `test_api_failure` | API 例外 → `macro_sentiment=0.0`、処理継続、`regime_label` が確定 |
| `test_no_api_key` | API キー未設定 → `ValueError` |
| `test_db_write_failure` | DB 書き込み失敗 → ROLLBACK、例外が上位に伝播、`market_regime` に行なし |

---

## 11. 設計制約（CLAUDE.md 準拠）

- `datetime.today()` / `date.today()` は使用しない（ルックアヘッドバイアス防止）
- `prices_daily` クエリは `date < target_date` の排他条件でルックアヘッドを防止
- AI（LLM）はスコア生成のみ。発注判断は Strategy 層が行う
- フェイルセーフ: API 失敗時は `0.0` フォールバックでシステム継続
