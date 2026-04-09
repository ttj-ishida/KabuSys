# KabuSys — 日本株自動売買システム

KabuSys は日本株向けのデータプラットフォーム・研究・戦略・監査・ETL・AI 支援（ニュースセンチメント / 市場レジーム判定）を含む自動売買システムのライブラリ群です。DuckDB をデータレイヤに、J-Quants API でマーケットデータを収集し、OpenAI（gpt-4o-mini）でニュース解析・マクロセンチメントを行う設計になっています。

---

## 特徴（Overview / Features）
- データ層
  - J-Quants API からの株価（OHLCV）・財務・上場情報・JPX カレンダー取得
  - DuckDB への冪等保存（ON CONFLICT / UPDATE）
  - データ品質チェック（欠損・重複・スパイク・日付不整合）
  - ニュース収集（RSS）と前処理、記事→銘柄紐付け
- 研究（Research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）計算、Zスコア正規化
- AI サブシステム
  - ニュースセンチメント（news_nlp.score_news）：銘柄別 ai_score を生成して ai_scores に保存
  - 市場レジーム判定（regime_detector.score_regime）：ETF（1321）MA200乖離 + マクロニュースで日次レジーム判定（bull/neutral/bear）
  - OpenAI API 呼び出しはリトライ/バックオフや JSON Mode（厳密な JSON 出力）に対応
- 監査 / 実行
  - signal → order_request → execution のトレーサビリティ用監査テーブル・初期化ユーティリティ
  - Paper Trading 用 DB パス等の設定サポート
- 運用に配慮した設計
  - Look-ahead バイアス回避（target_date を明示、現在時刻参照を避ける設計）
  - 自動 .env ロード（プロジェクトルート検出）だが無効化可能
  - リトライ / レートリミット / SSRF 対策など堅牢さを重視

---

## 必要条件（Prerequisites）
- Python 3.10 以上（型アノテーションで | を使用）
- 主要ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants, OpenAI, RSS ソース）

インストール例（開発用仮想環境）:
- python -m venv .venv
- source .venv/bin/activate
- pip install duckdb openai defusedxml
- pip install -e .    （パッケージとしてセットアップしている場合）

（プロジェクトに requirements.txt / pyproject.toml がある想定でそちらを使用してください）

---

## 環境変数 / 設定（重要なキー）
設定は .env ファイル（プロジェクトルートの .env / .env.local）または環境変数から自動読み込みされます。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な環境変数:
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime にも引数で渡せます）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 通知用（任意）
- DUCKDB_PATH （デフォルト: data/kabusys.duckdb）
- SQLITE_PATH （デフォルト: data/monitoring.db）
- PAPER_FILL_MODE （paper_trading 用。instant|partial|never|reject、デフォルト: instant）
- PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
- KABUSYS_ENV（development | paper_trading | live、デフォルト: development）
- LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）

.env の簡易例:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

---

## セットアップ手順（Setup）
1. リポジトリをクローンしてワークディレクトリに移動
2. 仮想環境を作成して有効化
3. 依存パッケージをインストール（duckdb, openai, defusedxml など）
4. プロジェクトルートに .env を配置し必要なキーを設定
5. データディレクトリを作成（例: data/）
6. 監査用 DuckDB を初期化（オプション、下記参照）

監査DB初期化例（Python スクリプト）:
```python
import duckdb
from kabusys.data.audit import init_audit_db
# ファイル DB を初期化
conn = init_audit_db("data/audit.duckdb")
# あるいは ":memory:" でインメモリ DB
```

---

## 使い方（Usage / 主な API）
以下は代表的な利用例（Python REPL / スクリプト）です。target_date はルックアヘッドバイアスを避けるため明示してください（date オブジェクト）。

一般的な DuckDB 接続:
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")  # ファイルパスまたは ":memory:"
```

日次 ETL を実行（株価・財務・カレンダー更新 + 品質チェック）:
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

ニュースセンチメントを計算して ai_scores テーブルに保存:
```python
from kabusys.ai.news_nlp import score_news
from datetime import date
# api_key を引数で渡せる。None の場合 OPENAI_API_KEY を参照
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print("wrote", n_written, "codes")
```

市場レジーム判定（ETF 1321 の MA200 乖離 + マクロニュース）:
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

監査スキーマを DB に作成:
```python
from kabusys.data.audit import init_audit_schema
# 既存の duckdb 接続に監査テーブルを追加
init_audit_schema(conn, transactional=True)
```

カレンダー関連ユーティリティ:
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day
from datetime import date
is_td = is_trading_day(conn, date(2026,3,20))
next_td = next_trading_day(conn, date(2026,3,20))
```

研究（ファクター）関数例:
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date
moms = calc_momentum(conn, target_date=date(2026,3,20))
vols = calc_volatility(conn, target_date=date(2026,3,20))
vals = calc_value(conn, target_date=date(2026,3,20))
```

統計ユーティリティ:
```python
from kabusys.data.stats import zscore_normalize
normed = zscore_normalize(records, columns=["mom_1m", "mom_3m"])
```

注意:
- OpenAI 呼び出しは API キーを必要とします。api_key 引数で渡すか OPENAI_API_KEY 環境変数を設定してください。
- ETL / AI 呼び出しはネットワークや API エラーを考慮したリトライやフェイルセーフ実装がありますが、権限やキーが正しいことを確認してください。

---

## ディレクトリ構成（主要ファイル）
（ルート: src/kabusys 以下を抜粋）

- kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定読み込みロジック
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュースセンチメント解析（score_news）
    - regime_detector.py            — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント（fetch / save）
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - etl.py                        — ETLResult の再エクスポート
    - calendar_management.py        — マーケットカレンダー管理（is_trading_day 等）
    - news_collector.py             — RSS 収集・前処理
    - quality.py                    — データ品質チェック
    - stats.py                      — 統計ユーティリティ（zscore_normalize）
    - audit.py                      — 監査ログテーブル定義・初期化
  - research/
    - __init__.py
    - factor_research.py            — モメンタム / バリュー / ボラティリティ計算
    - feature_exploration.py        — 将来リターン, IC, サマリー, ランク
  - ai, research, data パッケージはそれぞれ公開関数群を提供

---

## 運用上のポイント / Tips
- Look-ahead バイアス低減: 各 AI / 研究関数は target_date ベースで設計され、内部で datetime.today() などを直接参照しません。バックテスト時は必ず適切な target_date を渡してください。
- .env 自動ロード: config.py はプロジェクトルート（.git または pyproject.toml を探索）を検出して .env / .env.local を自動読み込みします。テスト時や外部制御したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- Paper Trading: 環境 KABUSYS_ENV=paper_trading を使うことで paper_fill_mode 等を切り替え可能です。
- OpenAI 呼び出しは JSON Mode を利用し、応答の厳密パースを前提としているためレスポンス整形に注意してください（score_news / regime_detector はパース失敗時にフォールバックします）。
- J-Quants API はレート制限（120 req/min）に合わせた RateLimiter があるため、短時間に大量要求を投げない運用を心がけてください。

---

## 参考・開発メモ
- テストを行う際は OpenAI / J-Quants など外部 API 呼び出しをモックする設計（いくつかの内部関数は差し替え可能）になっています。
- DuckDB のバージョンや executemany の挙動に注意（コメントにある互換性考慮を参照）。
- セキュリティ面では RSS の SSRF 対策・defusedxml を用いた XML パース防護・URL 正規化等が組み込まれています。

---

必要であれば README に以下を追加できます:
- 具体的な requirements.txt / pyproject.toml の例
- CI / テストの実行手順
- デプロイ / コンテナ化（systemd / supervisor / Docker）に関する運用例

ご希望があれば、サンプル .env.example や具体的なスクリプト（ETL cron ジョブ、監視スクリプト等）も作成します。