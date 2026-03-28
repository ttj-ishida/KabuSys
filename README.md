# KabuSys

日本株向けのデータプラットフォーム兼自動売買基盤の一部実装です。  
ETL（J-Quants 経由の株価／財務／市場カレンダー取得）、ニュース収集・NLP（OpenAI）による銘柄・マクロセンチメント評価、研究用ファクター計算、監査ログスキーマなどを含みます。

バージョン: 0.1.0

---

## 主要な特徴（機能一覧）

- データ取得/保存（J-Quants API）
  - 株価日足（OHLCV）、財務データ、JPX マーケットカレンダーの取得と DuckDB への冪等保存
  - レート制御、再試行、トークン自動リフレッシュ対応
- ETL パイプライン
  - 差分取得、バックフィル、品質チェックを含む日次 ETL（run_daily_etl）
  - ETL 実行結果を ETLResult で返す
- データ品質チェック
  - 欠損、重複、スパイク、日付不整合の検出
- ニュース収集（RSS）
  - RSS を安全に取得して前処理（URL除去・正規化）し raw_news に保存する設計
  - SSRF／XML Bomb 等への対策を考慮
- ニュース NLP / マクロ判定（OpenAI）
  - 銘柄ごとのニュースをまとめて LLM に投げ、ai_scores テーブルへ保存（score_news）
  - マクロニュースと ETF (1321) の MA200乖離を組み合わせて市場レジームを判定（score_regime）
  - レート制限・リトライ・レスポンス検証を実装
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Spearman）、ファクターサマリー、Z スコア正規化
- 監査ログ（Audit）
  - signal_events / order_requests / executions 等、発注〜約定フローを UUID でトレース可能にする監査スキーマ定義と初期化関数（init_audit_schema / init_audit_db）

---

## 要求環境

- Python 3.10 以上（型ヒントで `|` 記法等を使用しているため）
- 主な依存パッケージ（必要に応じて最新版を指定してください）
  - duckdb
  - openai
  - defusedxml

（プロジェクト配布時は requirements.txt を用意してください）

例:
```
pip install duckdb openai defusedxml
```

または開発環境:
```
python -m venv .venv
source .venv/bin/activate
pip install -e .  # パッケージ化されている場合
pip install duckdb openai defusedxml
```

---

## 環境変数 / .env の扱い

パッケージ起動時にプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索し、`.env` および `.env.local` を自動読み込みします（OS 環境変数が優先）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主に使用される環境変数（必須は明記）:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants 用リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL (任意) — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — "development" / "paper_trading" / "live"（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト: INFO）
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime 実行時に参照）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env 自動読み込みを無効化

例 (.env):
```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-xxxx
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（簡易）

1. Python 仮想環境の作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 依存ライブラリをインストール
   ```
   pip install duckdb openai defusedxml
   ```

   （プロジェクトに requirements.txt がある場合は `pip install -r requirements.txt`）

3. 環境変数を設定（.env をプロジェクトルートに置くか、OS 環境変数で設定）
   - `.env.example` を参考に `.env` を作成してください（リポジトリに同梱されている想定）

4. DuckDB データベースを初期化（必要に応じて監査 DB を作る）
   - 監査用 DB を作る例:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```
   - メイン DB は別途スキーマ初期化関数 (存在する場合) を提供する想定です

---

## 基本的な使い方（例）

以下は Python REPL / スクリプトからの利用例です。事前に依存と環境変数を正しく設定しておいてください。

- DuckDB 接続取得
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行（run_daily_etl）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP（銘柄ごとのスコア付与）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

count = score_news(conn, target_date=date(2026, 3, 20))
print(f"wrote {count} ai_scores")
```

- 市場レジーム判定（ETF 1321 + マクロニュース）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

- 研究用ファクター計算
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value
from kabusys.research.feature_exploration import calc_forward_returns

t = date(2026, 3, 20)
mom = calc_momentum(conn, t)
vol = calc_volatility(conn, t)
val = calc_value(conn, t)
fwd = calc_forward_returns(conn, t, horizons=[1,5,21])
```

- J-Quants API を直接使う（例：ID トークン取得、銘柄一覧取得）
```python
from kabusys.data.jquants_client import get_id_token, fetch_listed_info

id_token = get_id_token()  # JQUANTS_REFRESH_TOKEN を参照
listed = fetch_listed_info(date_=date(2026,3,20))
```

- RSS フィード取得（ニュース収集ユーティリティ）
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles[:5]:
    print(a["id"], a["title"], a["datetime"])
```

---

## 監査ログ（Audit）初期化例

監査用の DuckDB データベースを作り、監査スキーマを初期化する：
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# 以降 conn を使い監査ログに書き込む
```
init_audit_db は親ディレクトリを自動作成し、UTC タイムゾーン設定も行います。

---

## 注意事項 / 設計上のポイント

- ルックアヘッドバイアス回避:
  - 各モジュール（news_nlp, regime_detector, pipeline 等）は内部で現在日時を直接参照せず、呼び出し元から target_date を渡す設計になっています。バックテストで必ず target_date を固定して使ってください。
- OpenAI 呼び出し:
  - APIキーは引数で注入可能（単体テスト時にモックしやすい）。
  - レスポンスパース失敗や API エラー時はフェイルセーフとして 0.0（中立）で処理継続する実装が多く用意されています。
- DuckDB と executemany:
  - DuckDB のバージョンによって executemany の空リスト処理が制限されるため、実装側で空チェックを行っています。
- セキュリティ:
  - news_collector は SSRF 対策、受信サイズ制限、defusedxml による XML パース保護を行います。
  - jquants_client はトークン自動リフレッシュとレート制御を実装しています。

---

## ディレクトリ構成（主なファイル）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数および .env 自動読み込み・検証
  - ai/
    - __init__.py
    - news_nlp.py — ニュースセンチメント算出（score_news）
    - regime_detector.py — マクロ + MA200 から市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（fetch / save / auth）
    - pipeline.py — ETL パイプライン（run_daily_etl ほか）
    - etl.py — ETLResult の再エクスポート
    - news_collector.py — RSS 収集・前処理
    - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
    - stats.py — 共通統計ユーティリティ（zscore_normalize）
    - quality.py — データ品質チェック（欠損／重複／スパイク等）
    - audit.py — 監査ログスキーマ定義 / 初期化（init_audit_schema / init_audit_db）
  - research/
    - __init__.py
    - factor_research.py — Momentum/Value/Volatility 計算
    - feature_exploration.py — 将来リターン / IC / 統計要約等

---

## 貢献 / テスト

- 単体テストに向け、OpenAI 呼び出しや外部ネットワーク呼び出しは各モジュールで差し替え可能な設計（内部 _call_openai_api、_urlopen など）になっています。unittest.mock を使って外部依存をモックしやすい構造です。
- issue や PR の際は .env やシークレットを含めないでください。

---

必要であれば、README にサンプル .env.example、より詳細なセットアップ手順（DB スキーマ初期化 SQL の有無、Docker/CI 用設定など）や開発フローを追加します。どの情報を優先して追記しましょうか？