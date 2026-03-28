# KabuSys

日本株向けの自動売買・データ基盤ライブラリ群です。  
データの収集・品質チェック・ETL・ファクター計算・ニュースNLP・市場レジーム判定・監査ログなどを含むモジュール群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システム構築のためのライブラリ群です。主に以下の役割を担います。

- J-Quants API からのデータ取得（株価日足・財務・上場銘柄情報・市場カレンダー）
- DuckDB を用いたデータ格納と冪等的保存
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- ニュース収集（RSS）とニュースの前処理
- OpenAI（gpt-4o-mini）を使ったニュースセンチメント分析および市場レジーム判定
- 研究用ファクター計算（モメンタム・バリュー・ボラティリティ等）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）用スキーマ初期化

設計上の共通方針として、バックテストでのルックアヘッドバイアスを避ける実装、冪等性・フェイルセーフ（API失敗時は部分継続）を重視しています。

---

## 機能一覧（主な公開 API・モジュール）

- kabusys.config
  - 環境変数読み込み（.env / .env.local の自動ロード）と Settings オブジェクト
  - 必須環境変数の取得 & 検証（KABUSYS_ENV, LOG_LEVEL など）

- kabusys.data
  - jquants_client: J-Quants API クライアント（取得・保存関数）
    - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar, fetch_listed_info
    - save_daily_quotes, save_financial_statements, save_market_calendar
    - get_id_token（リフレッシュ処理）
  - pipeline / etl: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - calendar_management: 営業日判定・next/prev_trading_day・calendar_update_job
  - news_collector: RSS 取得・前処理・SSRF 対策等のユーティリティ
  - audit: 監査ログ用スキーマ初期化（init_audit_schema / init_audit_db）
  - stats: zscore_normalize 等の統計ユーティリティ
  - ETLResult データクラスの公開（kabusys.data.etl）

- kabusys.ai
  - news_nlp.score_news(conn, target_date, api_key=None): ニュースを集約して銘柄ごとに AI スコアを ai_scores テーブルへ書き込み
  - regime_detector.score_regime(conn, target_date, api_key=None): ETF（1321）MA とマクロニュースの LLM スコアを合成して market_regime を作成

- kabusys.research
  - ファクター計算・特徴量解析
    - calc_momentum, calc_value, calc_volatility
    - calc_forward_returns, calc_ic, rank, factor_summary
  - data.stats.zscore_normalize と連携してクロスセクション正規化可能

（将来的に strategy / execution / monitoring モジュールと連携して売買実行フローを構築する想定）

---

## セットアップ手順

前提:
- Python 3.10 以上（型 | を使っているため）
- DuckDB を利用（ローカルファイル or :memory:）

例: 仮想環境作成・依存パッケージのインストール

1. リポジトリをクローン
   git clone <リポジトリURL>
   cd <repo>

2. 仮想環境を作成して有効化
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

3. 必要パッケージをインストール
   pip install duckdb openai defusedxml

   （プロジェクトで別途 requirements.txt / pyproject.toml があればそちらを利用してください。）

4. 環境変数 (.env) を準備
   ルートに .env または .env.local を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

   最低限設定すべき環境変数（例）:
   - JQUANTS_REFRESH_TOKEN=...
   - KABU_API_PASSWORD=...
   - SLACK_BOT_TOKEN=...
   - SLACK_CHANNEL_ID=...
   - OPENAI_API_KEY=...  # news_nlp / regime_detector が必要とする場合
   - KABUSYS_ENV=development  # 有効値: development / paper_trading / live
   - LOG_LEVEL=INFO
   - DUCKDB_PATH=data/kabusys.duckdb  # 任意
   - SQLITE_PATH=data/monitoring.db   # 任意

5. DuckDB ファイル用ディレクトリを作る（任意）
   mkdir -p data

---

## 使い方（簡単な例）

以下はライブラリを直接使う簡単なコード例です。実行はプロジェクトルートで行ってください。

- DuckDB 接続（例）

  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")

- 日次 ETL を実行してデータを取得・品質チェックする

  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースの AI スコアを生成（raw_news / news_symbols / ai_scores テーブルが必要）

  from datetime import date
  from kabusys.ai.news_nlp import score_news

  # OPENAI_API_KEY が環境変数にある場合は api_key を省略可
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"written: {n_written}")

- 市場レジームを計算して market_regime テーブルへ書き込む

  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))

- 監査ログ DB を初期化する

  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")
  # audit_conn をアプリの監査ログに利用

- RSS を取得する（news_collector）

  from kabusys.data.news_collector import fetch_rss
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
  for a in articles[:5]:
      print(a["id"], a["datetime"], a["title"])

注意:
- AI を呼ぶ関数（score_news, score_regime）は OpenAI API KEY が必要です（引数で渡すか、環境変数 OPENAI_API_KEY を設定）。
- 各書き込み先テーブル（raw_prices, raw_financials, raw_news, news_symbols, ai_scores, market_regime 等）は DB スキーマが前提になります。ETL / save 関数は既存のスキーマへ冪等的に保存する設計です。プロジェクト内にスキーマ初期化ユーティリティがあればそれを利用してください（このコードベースでは audit スキーマ初期化関数を提供しています）。

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu ステーション用パスワード（API 実行時）
- KABU_API_BASE_URL (任意) — kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- OPENAI_API_KEY (AI モジュール利用時に必須) — OpenAI API キー
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID — Slack 通知に使う場合
- KABUSYS_ENV — development / paper_trading / live（デフォルト development）
- LOG_LEVEL — ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）
- DUCKDB_PATH / SQLITE_PATH — データベースファイルパス
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動ロードを無効化

サンプル .env（例）

  JQUANTS_REFRESH_TOKEN=xxxxxxxx
  OPENAI_API_KEY=sk-xxxxxxxx
  KABU_API_PASSWORD=secret
  SLACK_BOT_TOKEN=xoxb-...
  SLACK_CHANNEL_ID=C01234567
  KABUSYS_ENV=development
  LOG_LEVEL=INFO
  DUCKDB_PATH=data/kabusys.duckdb

---

## ディレクトリ構成

以下はこのコードベースの主要ファイル / モジュール構成（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - calendar_management.py
    - pipeline.py
    - etl.py
    - jquants_client.py
    - news_collector.py
    - quality.py
    - stats.py
    - audit.py
    - (その他: jquants_client internal utilities 等)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research 関連で data.stats を参照
  - （公開トップレベルでは "data", "strategy", "execution", "monitoring" を __all__ に定義していますが、strategy/execution/monitoring の実装は別途）

---

## 注意点・設計上のポイント

- ルックアヘッドバイアス防止
  - 多くのモジュール（news_nlp, regime_detector, research 等）は内部で date.today() を直接参照せず、target_date を明示的に受け取る設計です。バックテストで現在時刻に関する偏りを避ける目的です。

- 冪等性
  - J-Quants から取得したデータ保存は ON CONFLICT DO UPDATE などで冪等に行われます。

- フェイルセーフ
  - 外部 API（OpenAI, J-Quants）失敗時は可能な範囲でスキップやデフォルト値で継続するようになっています（ログ出力と共に）。

- セキュリティ対策
  - news_collector は SSRF 対策、レスポンスサイズ制限、defusedxml を使った XML パース等の安全対策を実装しています。

---

## 貢献・拡張

- strategy / execution / monitoring 層を接続して実際の発注ワークフロー（リスク管理・ポジション管理・ブローカー API 連携）を実装できます。
- スキーマ初期化ユーティリティや運用ジョブ（cron / Airflow など）で run_daily_etl / calendar_update_job を定期実行してください。
- テスト: 外部 API 呼び出しはモック可能な設計（内部関数を差し替えられる）になっています。ユニットテストでの差し替えを推奨します。

---

必要であれば、README に以下を追記します：
- データベースのスキーマ（各テーブル定義）一覧
- 実運用時のデプロイ手順（systemd / Docker / Kubernetes）
- 詳しいサンプルコード（ETL ワークフロー、AI スコアの実例）
- CI / テストの実行方法

どの内容を優先するか教えてください。