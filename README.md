# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。  
ETL（J-Quants → DuckDB）、ニュース収集、ニュースNLP（OpenAI を利用したセンチメント）、市場レジーム判定、研究用ファクター計算、監査ログ（発注／約定のトレーサビリティ）など、取引システム／データ基盤で必要となるユーティリティ群を提供します。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（主要 API / サンプル）
- 環境変数（.env の例）
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株運用向けに設計されたライブラリ群です。主な目的は以下です。

- J-Quants API からのデータ取得（株価日足、財務、カレンダー等）と DuckDB への差分保存（ETL）
- RSS によるニュース収集と raw_news テーブルへの蓄積（SSRF 対策・正規化・冪等保存）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント解析（銘柄単位の ai_scores、マクロセンチメント）
- ETF を用いた市場レジーム判定の生成（ma200 と LLM マクロスコアの合成）
- 研究用途のファクター計算（Momentum / Value / Volatility）と特徴量解析ユーティリティ
- データ品質チェック、マーケットカレンダー管理
- 発注 → 約定までの監査ログ用スキーマの初期化ユーティリティ

設計方針として、バックテストでのルックアヘッドバイアス防止、API 失敗時のフェイルセーフ、DuckDB を中心としたローカルデータプラットフォームを重視しています。

---

## 主な機能一覧

- data:
  - ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（fetch_*, save_*）
  - 市場カレンダー管理（is_trading_day / next_trading_day / prev_trading_day / get_trading_days）
  - ニュース収集（RSS の安全な取得・正規化・raw_news への保存）
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
  - 監査ログ用スキーマ初期化（init_audit_schema / init_audit_db）

- ai:
  - score_news(conn, target_date, api_key=None): 銘柄ごとのニュースセンチメントを ai_scores に保存
  - score_regime(conn, target_date, api_key=None): ma200 と LLM マクロスコアを合成して market_regime を更新

- research:
  - calc_momentum / calc_value / calc_volatility: ファクター計算
  - calc_forward_returns / calc_ic / factor_summary / rank: 特徴量探索・統計解析
  - zscore_normalize: クロスセクション正規化（data.stats）

- config:
  - 環境変数読み込み（.env / .env.local の自動ロード）と Settings クラス（settings）でアクセス

---

## セットアップ手順

前提:
- Python 3.10+（typing の union 演算子や型ヒントを使用）
- DuckDB を利用するためローカル環境に依存しない（Python パッケージで動作）

1. リポジトリをクローン / 展開:
   git clone ... または該当ソースツリーを取得

2. 仮想環境の作成（推奨）:
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

3. 依存関係をインストール（例）:
   pip install duckdb openai defusedxml
   - 実運用では requirements.txt を用意している場合は pip install -r requirements.txt を推奨します。

4. 開発インストール（パッケージとして利用する場合）:
   pip install -e .

5. 環境変数設定:
   プロジェクトルートに .env / .env.local を置くと自動で読み込まれます（詳細は config モジュール参照）。
   自動ロードを無効化する場合:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 環境変数（.env の例）

必須（Settings.require で必須とされるもの）:
- JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
- KABU_API_PASSWORD=your_kabu_api_password
- SLACK_BOT_TOKEN=your_slack_token
- SLACK_CHANNEL_ID=your_slack_channel_id
- OPENAI_API_KEY=your_openai_api_key  # ai.score_* 呼び出しで使用

任意 / デフォルトあり:
- KABUSYS_ENV=development | paper_trading | live  (default: development)
- LOG_LEVEL=INFO | DEBUG | ...
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1  # 自動 .env 読み込みを無効化

例 (.env):
JQUANTS_REFRESH_TOKEN=xxxxx
OPENAI_API_KEY=sk-xxxx
KABU_API_PASSWORD=passwd
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## 使い方（主要 API / サンプル）

以下は代表的なユースケースの例です。実際には logging 設定や例外処理を追加してください。

- DuckDB 接続の用意:
  from kabusys.config import settings
  import duckdb
  conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL 実行（株価・財務・カレンダーの差分取得＋品質チェック）:
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースセンチメント（AI）スコアの実行:
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  n_written = score_news(conn, target_date=date(2026,3,20))
  print(f"written: {n_written}")

  note: OpenAI の API キーは OPENAI_API_KEY 環境変数、または api_key 引数で渡せます。

- 市場レジーム判定:
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date=date(2026,3,20))

- 研究用ファクター計算:
  from kabusys.research import calc_momentum, calc_value, calc_volatility
  m = calc_momentum(conn, date(2026,3,20))
  v = calc_value(conn, date(2026,3,20))
  vol = calc_volatility(conn, date(2026,3,20))

- 監査ログ用 DB 初期化:
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")
  # これで監査テーブル(signal_events, order_requests, executions) が作成されます

- ニュース収集（RSS）取得:
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES
  articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
  # 取得した記事は NewsArticle 型（dict）に準拠します

注意点:
- OpenAI 呼び出しは外部 API のため失敗やレート制限が発生します。各モジュールはリトライやフォールバックを実装していますが、API 使用量に注意してください。
- DuckDB 側のテーブルスキーマ（raw_prices, raw_financials, raw_news, ai_scores, market_regime 等）は ETL 部分の前提です。テスト用にスキーマ初期化関数やマイグレーションがあれば利用してください（本ソースではスキーマ定義の一部が監査ログで提供されています）。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py         # ニュースセンチメント（銘柄別 ai_scores）
  - regime_detector.py  # 市場レジーム判定（ma200 + マクロLLM）
- data/
  - __init__.py
  - jquants_client.py   # J-Quants API クライアント（fetch_* / save_*）
  - pipeline.py         # ETL パイプライン（run_daily_etl 等）
  - etl.py              # ETL 結果型の公開（ETLResult）
  - news_collector.py   # RSS ニュース収集（SSRF や Gzip 制限あり）
  - calendar_management.py  # 市場カレンダー関連ユーティリティ
  - quality.py          # データ品質チェック
  - stats.py            # 汎用統計ユーティリティ（zscore_normalize）
  - audit.py            # 監査ログスキーマ初期化
- research/
  - __init__.py
  - factor_research.py  # Momentum / Value / Volatility 計算
  - feature_exploration.py  # 将来リターン / IC / サマリー 等

その他:
- README.md（本ファイル）
- .env.example（環境変数のサンプルをプロジェクトルートに用意することを推奨）

---

## 補足 / 実運用上の注意

- 環境変数は .env / .env.local をルートから自動読み込みします。CI やテストで自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI は JSON Mode（response_format={"type":"json_object"}）を利用していますが、LLM の応答は常に期待どおりとは限らないためパース失敗時のフェイルセーフ（スコア=0.0 など）があります。テストは _call_openai_api のモックを推奨します。
- J-Quants API のレート制限と認証リフレッシュ処理（401→refresh）に対応していますが、ID トークンや refresh token の管理は安全なストレージを利用してください。
- DuckDB に対する executemany の空リストバインドなど、バージョン差異に起因する制約を考慮した実装が行われています。DuckDB バージョンに依存する挙動がある点に留意してください。

---

問題報告・貢献
- 問題や改善提案があれば Issue を立ててください。プルリクエストは歓迎します。

---

以上が KabuSys の README です。さらに詳細な使用例やテーブルスキーマ、CI 設定、運用ドキュメントが必要であれば追って追加できます。