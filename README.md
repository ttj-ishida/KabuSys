# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ集です。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP（OpenAI を用いたセンチメント）、研究用ファクター計算、監査ログ（発注・約定のトレーサビリティ）などを含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株アルゴリズム取引のための内部ライブラリ群で、主に以下を提供します。

- J-Quants API を用いたデータ取得（株価日足・財務・上場情報・市場カレンダー）
- ETL パイプライン（差分取得・保存・品質チェック）
- ニュース収集（RSS）と NLP による銘柄別センチメント（OpenAI）
- 市場レジーム判定（ETF とマクロニュースの組合せ）
- 研究用ユーティリティ（モメンタム、ボラティリティ、バリュー等のファクター計算）
- 監査ログ用テーブル生成（signal → order_request → execution のトレース）
- データ品質チェック（欠損・スパイク・重複・日付整合性）

設計上、バックテストや運用で「ルックアヘッドバイアス」を避ける実装方針（現在時刻参照を直接使わない等）を採用しています。

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（取得／保存／認証・リトライ・レート制御）
  - pipeline: 日次 ETL（run_daily_etl）と個別 ETL (prices/financials/calendar)
  - calendar_management: 市場カレンダー操作（is_trading_day, next_trading_day, get_trading_days 等）
  - news_collector: RSS 取得・前処理（fetch_rss, preprocess_text 等）
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit: 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - stats: zscore_normalize（研究用正規化ユーティリティ）
- ai/
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを ai_scores テーブルへ書き込む
  - regime_detector.score_regime: ETF とマクロニュースで市場レジームを判定し market_regime テーブルへ書き込む
- research/
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
- config: 環境変数読み込み・Settings（.env/.env.local 自動読み込み、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）

---

## セットアップ手順（開発・実行環境）

以下は推奨手順です。実プロジェクトの requirements.txt 等がある場合はそちらを利用してください。

1. Python
   - 推奨: Python 3.10 以上（PEP 604 の union 型（A | B）などを使用）
2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  # Windows: .venv\Scripts\activate
3. 依存パッケージをインストール
   - 例（最小限）:
     pip install duckdb openai defusedxml
   - 実運用では他にログライブラリ等が必要になる場合があります
4. パッケージをインストール（ローカル開発）
   - プロジェクトルートに setup.cfg / pyproject.toml 等があれば:
     pip install -e .
5. 環境変数の設定
   - プロジェクトルートに .env を作成して読み込ませる仕組みがあります（config.py が自動ロード）
   - もしくは OS の環境変数に直接設定してください

必須の環境変数（最低限）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（jquants_client.get_id_token で使用）
- OPENAI_API_KEY: OpenAI API キー（ai.news_nlp / ai.regime_detector の呼び出しに必要）
- KABU_API_PASSWORD: kabuステーション API のパスワード（発注機能を使う場合）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: 通知用 Slack（必要な場合）

任意（デフォルトあり）
- KABUSYS_ENV: development / paper_trading / live （デフォルト: development）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite 監視 DB（デフォルト data/monitoring.db）

.env の自動読み込みについて
- config.py はプロジェクトルート（.git または pyproject.toml を基準）から .env を自動読み込みします。
- テスト時などで自動読み込みを無効にする場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 使い方（簡単なコード例）

以下は Python API を直接呼ぶ例です。DuckDB の接続は duckdb.connect() をそのまま使えます（ファイル /memory:）。

- ETL（日次パイプライン）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントのスコア計算（OpenAI API KEY 必須）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"written: {n_written}")
```

- 市場レジーム判定（ETF 1321 の MA200 とマクロニュース）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- 監査ログ DB 初期化
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn は初期化済みの DuckDB 接続
```

- RSS フィード取得（ニュース）
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES
articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
# raw_news への保存はプロジェクト側の保存ロジックに準拠して行ってください
```

- 研究用ファクター計算
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, target_date=date(2026, 3, 20))
value = calc_value(conn, target_date=date(2026, 3, 20))
vol = calc_volatility(conn, target_date=date(2026, 3, 20))
```

注意:
- ai.* 関数は OpenAI の JSON-mode を使用して厳密 JSON を期待します。API 呼び出しで ValueError（キー未設定）やフォールバックが発生する設計になっています。
- jquants_client の関数は id_token を内部でキャッシュ・自動リフレッシュしますが、必要なら明示的に get_id_token を渡せます。

---

## ディレクトリ構成（主要ファイル）

プロジェクトの主要なファイル・モジュール構成（src/kabusys 以下）:

- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py            # ニュース → 銘柄センチメント（score_news）
  - regime_detector.py     # ETF+マクロで市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py      # J-Quants API クライアント + 保存関数
  - pipeline.py            # ETL パイプライン（run_daily_etl 等）
  - etl.py                 # ETL の公開インターフェース（ETLResult）
  - calendar_management.py # 市場カレンダー操作・更新ジョブ
  - news_collector.py      # RSS 取得・前処理
  - quality.py             # 品質チェック（check_missing_data, check_spike, ...）
  - stats.py               # zscore_normalize 等
  - audit.py               # 監査ログスキーマ初期化
- research/
  - __init__.py
  - factor_research.py     # calc_momentum, calc_volatility, calc_value
  - feature_exploration.py # calc_forward_returns, calc_ic, factor_summary, rank

各モジュールは単一責任を心がけ、DuckDB 接続や API キーは呼び出し側から注入できるように設計されています。

---

## 補足・トラブルシュート

- 環境変数が不足している場合、settings のプロパティから ValueError が発生します（例: OPENAI_API_KEY がないと ai.score_news は ValueError）。
- .env 自動ロード:
  - 自動でプロジェクトルートの .env を読み込みます（.env.local は上書き）。
  - 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- DuckDB への executemany はバージョン依存で空リストを受け付けない点を考慮しています（pipeline, news_nlp 等で考慮済み）。
- OpenAI API の呼び出しは再試行ロジックを実装していますが、レート制限管理はユーザ側でも注意してください。
- news_collector.fetch_rss は SSRF 対策（ホストのプライベート判定、リダイレクト検査、最大読み取りサイズ）を実装しています。

---

これで README の基本情報はカバーしています。必要であれば以下を追加します:
- 実際の requirements.txt（推奨バージョン）
- CI / ユニットテスト実行方法
- データベーススキーマ定義（DDL）やサンプル .env.example の雛形

どれを追加しますか？