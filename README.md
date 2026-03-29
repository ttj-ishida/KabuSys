# KabuSys — 日本株自動売買プラットフォーム（README）

概要
----
KabuSys は日本株向けのデータプラットフォームとリサーチ／自動売買支援ライブラリです。  
主に以下を提供します。

- J-Quants API からの株価・財務・市場カレンダー ETL（差分取得・保存・品質チェック）
- ニュース収集と NLP（OpenAI）による銘柄別センチメントスコアリング
- 市場レジーム判定（ETF MA とマクロニュースの合成）
- ファクター計算・特徴量探索（モメンタム・バリュー・ボラティリティ・IC 等）
- 監査ログ（signal → order → execution のトレーサビリティ）を格納する DuckDB 初期化ユーティリティ
- データ品質チェック、マーケットカレンダー管理、RSS ニュース収集等

主な機能一覧
-------------
- データ取得・保存
  - J-Quants API クライアント（fetch / save: daily_quotes, financial_statements, market_calendar, listed_info）
  - 差分ETL と日次パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
- データ品質管理
  - 欠損値検出、スパイク検出、重複チェック、日付整合性チェック（quality モジュール）
- ニュース収集 & NLP
  - RSS 収集（fetch_rss）と前処理（SSRF/サイズ/追跡パラメタ除去）
  - OpenAI（gpt-4o-mini）を用いた銘柄別ニューススコアリング（score_news）
- 市場レジーム判定
  - ETF 1321 の 200 日 MA とマクロニュースセンチメントの合成（score_regime）
- 研究／因子系
  - モメンタム・ボラティリティ・バリュー計算（calc_momentum / calc_volatility / calc_value）
  - 将来リターン計算、IC 計算、ファクター統計（feature_exploration）
- 監査ログ
  - 監査テーブル作成と初期化ユーティリティ（init_audit_schema / init_audit_db）
- 設定管理
  - .env/.env.local 自動ロード、環境変数ベースの設定取得（kabusys.config.settings）

前提・依存
-----------
（代表的なもの）
- Python 3.10+
- duckdb
- openai（OpenAI Python SDK、gpt-4o-mini 利用時）
- defusedxml
- その他、標準ライブラリ

インストール（開発環境）
-----------------------
リポジトリのルートで（pipenv / poetry / venv 等任意の仮想環境を推奨）:

例: editable install
```bash
python -m pip install -e .[dev]   # setup に extras があれば利用
```

（requirements.txt / pyproject.toml に依存関係がある想定です。必要パッケージを手動で入れてください）
例:
```bash
pip install duckdb openai defusedxml
```

環境変数と .env
----------------
kabusys.config はプロジェクトルート（.git または pyproject.toml を探索）から .env / .env.local を自動ロードします。自動ロードを無効化する場合は環境変数を設定してください:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1

必須の環境変数（少なくとも下記は設定が必要な場合があります）
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード（発注系で必要）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack 送信先チャンネル ID
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime で使用）

例 .env（プロジェクトルート）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

セットアップ（データベース等）
----------------------------
- DuckDB ファイルパスは settings.duckdb_path（デフォルト: data/kabusys.duckdb）
- 監査ログ専用 DB 初期化:
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # ":memory:" も可
```
- 必要なスキーマ（raw_prices, raw_financials, market_calendar, raw_news, ai_scores 等）は ETL や別スクリプトで作成してください（本 README ではスキーマ作成スクリプトは含めていません）。

基本的な使い方（コード例）
-------------------------

1) 日次 ETL 実行（例: run_daily_etl）
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニューススコアリング（OpenAI 必須）
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"written {n_written} scores")
```

3) 市場レジーム判定
```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")
```

4) 監査スキーマ初期化（既存接続を利用）
```python
from kabusys.data.audit import init_audit_schema
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
init_audit_schema(conn, transactional=True)
```

5) RSS を取得して raw_news に保存するワークフロー（fetch_rss を使って記事を取得後、DB に保存）
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES
articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
# 取得した articles を raw_news テーブルへ保存する処理を実装してください
```

主要モジュールとディレクトリ構成
------------------------------
（パッケージは src/kabusys 以下を想定）

- kabusys/
  - __init__.py — パッケージ定義、version
  - config.py — 環境変数/設定管理（.env 自動ロード、Settings クラス）
  - ai/
    - __init__.py
    - news_nlp.py — ニュース NLP（score_news, calc_news_window 等）
    - regime_detector.py — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - calendar_management.py — 市場カレンダー管理（is_trading_day / next_trading_day 等）
    - etl.py — ETL 型定義の再エクスポート
    - pipeline.py — ETL パイプライン（run_daily_etl, run_prices_etl 等）
    - stats.py — 統計ユーティリティ（zscore_normalize）
    - quality.py — データ品質チェック（check_missing_data, check_spike, run_all_checks）
    - audit.py — 監査ログスキーマ初期化（init_audit_schema, init_audit_db）
    - jquants_client.py — J-Quants API クライアント（fetch_/save_ 関数、認証、RateLimiter）
    - news_collector.py — RSS ニュース収集と前処理（fetch_rss 等）
  - research/
    - __init__.py
    - factor_research.py — ファクター計算（calc_momentum / calc_value / calc_volatility）
    - feature_exploration.py — 将来リターン, IC, 統計サマリー 等

設計上のポイント / 注意点
------------------------
- ルックアヘッドバイアス回避:
  - 日付参照（score_news, score_regime, ETL など）は内部で datetime.today() を直接参照せず、target_date を明示的に渡す設計です。
- 冪等性:
  - J-Quants から保存する際は INSERT ... ON CONFLICT DO UPDATE を使い冪等保存を実現しています。
- フェイルセーフ:
  - OpenAI や外部 API 呼び出しが失敗した場合、例外で停止させる箇所と、0.0 でフォールバックする箇所（スコア系）を使い分けています。
- セキュリティ:
  - RSS 収集では SSRF 対策、受信サイズ上限、XML の安全パーサ（defusedxml）を使用しています。
- 自動環境ロード:
  - .env/.env.local をプロジェクトルートから自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）

よくある質問（FAQ）
------------------
Q: OpenAI の API 呼び出しはどのように制御されていますか？  
A: gpt-4o-mini を用い、JSON Mode（response_format={"type": "json_object"}）で厳密な JSON を期待します。429/ネットワーク断/タイムアウト/5xx に対して指数バックオフを実装しています。

Q: J-Quants のトークン更新は自動ですか？  
A: get_id_token によりリフレッシュトークンから id_token を取得し、HTTP 401 でトークン切れを検出した場合は 1 回自動リフレッシュしてリトライします。

ライセンス / 貢献
-----------------
本 README はコードベースの説明用です。実際のプロジェクトに適用する際はライセンスファイル（LICENSE）を追加し、コントリビュートガイドラインを設けてください。

補足
----
この README は提供されたコードの静的解析に基づいてまとめた概要ドキュメントです。実行時の詳細挙動や環境依存の設定（証券 API の接続や具体的な DB スキーマ定義、Slack 通知ロジックなど）は本リポジトリ内の追加ファイルや運用ドキュメントを参照してください。必要であれば、README に含める実行例やスキーマ初期化スクリプトをさらに具体化します—希望があれば教えてください。