# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quants）・ニュース収集・LLM を用いたニュースセンチメント評価・市場レジーム判定・ファクター計算・監査ログなど、バックテスト／運用に必要な機能をモジュール化して提供します。

---

主な特徴
- J-Quants API からの差分 ETL（株価日足・財務・カレンダー）と品質チェック
- RSS ベースのニュース収集（SSRF/サイズ制限/トラッキング除去対応）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント（銘柄別）スコアリング（JSON Mode）
- 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロニュースセンチメント）
- ファクター計算（モメンタム・ボラティリティ・バリュー等）と特徴量探索ユーティリティ
- 監査ログ（signal → order_request → execution のトレーサビリティ）用スキーマの初期化ユーティリティ
- 環境変数ベースの設定管理（.env 自動ロード、優先順あり）

---

機能一覧（モジュール別）
- kabusys.config
  - 環境変数読み込み（.env / .env.local 自動ロード）、Settings オブジェクト
  - 必須環境変数チェック
- kabusys.data
  - jquants_client: J-Quants からの取得・DuckDB への保存（差分取得 / ページネーション / リトライ）
  - pipeline: 日次 ETL 実行（run_daily_etl）と ETL 結果クラス（ETLResult）
  - news_collector: RSS 取得・前処理・記事 ID 生成（SSRF 保護・サイズ制限）
  - quality: データ品質チェック（欠損・スパイク・重複・日付整合性）
  - calendar_management: 市場カレンダー管理 / 営業日判定 / calendar_update_job
  - audit: 監査ログスキーマの初期化 / init_audit_db
  - stats: z-score 正規化などの統計ユーティリティ
- kabusys.ai
  - news_nlp.score_news: ニュースを LLM に送って銘柄ごと ai_scores を書き込む
  - regime_detector.score_regime: 市場レジーム判定（ma200 + マクロセンチメント）
- kabusys.research
  - factor_research: calc_momentum, calc_volatility, calc_value
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank

---

セットアップ手順（簡易）
1. リポジトリをクローン
   - git clone <repo-url>
2. Python 環境準備（推奨: venv）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 依存パッケージのインストール（例）
   - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt があれば pip install -r requirements.txt）
   - 開発時にローカルインストールする場合:
     - pip install -e .

4. 環境変数（.env）を用意
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に .env/.env.local を置くと自動読み込みされます。
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 主要な環境変数（例）
     - JQUANTS_REFRESH_TOKEN=...      # 必須（J-Quants 用リフレッシュトークン）
     - OPENAI_API_KEY=...            # OpenAI の API キー（score_news/score_regime で使用）
     - KABU_API_PASSWORD=...         # kabu ステーション API パスワード
     - KABU_API_BASE_URL=...         # kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
     - SLACK_BOT_TOKEN=...
     - SLACK_CHANNEL_ID=...
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PID_FILE_PATH=data/execution.pid
     - CPU_THRESHOLD_PCT=90.0
     - MEMORY_THRESHOLD_PCT=85.0
     - DISK_THRESHOLD_PCT=90.0
     - KABUSYS_ENV=development|paper_trading|live
     - LOG_LEVEL=DEBUG|INFO|WARNING|ERROR|CRITICAL
   - （.env のパースはシェル風の export やコメント、クォート、エスケープをサポートします）

---

使い方（代表的な例）

- Settings の利用
  - from kabusys.config import settings
  - settings.jquants_refresh_token, settings.duckdb_path, settings.env などで参照

- DuckDB 接続の作成
  - import duckdb
  - conn = duckdb.connect(str(settings.duckdb_path))

- ETL（日次）
  - from kabusys.data.pipeline import run_daily_etl
  - from datetime import date
  - result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  - print(result.to_dict())

- ニュースセンチメントスコア（LLM を使用）
  - from kabusys.ai.news_nlp import score_news
  - from datetime import date
  - n_written = score_news(conn, target_date=date(2026,3,20), api_key=None)  # api_key 指定が無ければ OPENAI_API_KEY を参照

- 市場レジーム判定
  - from kabusys.ai.regime_detector import score_regime
  - from datetime import date
  - score_regime(conn, target_date=date(2026,3,20), api_key=None)

- 監査ログ DB 初期化
  - from kabusys.data.audit import init_audit_db
  - conn_audit = init_audit_db(settings.duckdb_path)  # ファイル作成とスキーマ初期化

- RSS 取得（ニュースコレクタ）
  - from kabusys.data.news_collector import fetch_rss
  - articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  - 各記事は {id, datetime, source, title, content, url} の構造

注意点
- OpenAI 呼び出し（news_nlp / regime_detector）は API エラー時にフェイルセーフ（スコア 0 やスキップ）する設計です。API キーやリトライ方針は各関数の引数/実装に依存します。
- 日付の扱いはルックアヘッドバイアスを避けるため、内部で date.today() を乱用しない設計になっています（多くの関数は target_date を受け取る）。
- DuckDB への大量挿入や executemany に対する互換性（空リストの扱い等）に注意しています（実装でガード済み）。

---

ディレクトリ構成（主要ファイル）
- src/
  - kabusys/
    - __init__.py
    - config.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - data/
      - __init__.py
      - jquants_client.py
      - pipeline.py
      - etl.py
      - calendar_management.py
      - news_collector.py
      - quality.py
      - stats.py
      - audit.py
      - audit.py
      - etl.py
      - pipeline.py
      - audit.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - monitoring/  (パッケージ公開対象の例: README の最初に __all__ が示す通り監視関連モジュールを想定)
    - execution/   (約定実行関連)
    - strategy/    (戦略レイヤー)

（上記はコードベースの代表的なファイル一覧です）

---

開発・テストのヒント
- .env 自動ロードの動作
  - プロジェクトルートを .git または pyproject.toml から探索して .env / .env.local を読み込みます。
  - 読み込み順序（優先度が高い順）: OS 環境変数 > .env.local（override=True）> .env
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化できます（ユニットテストで便利）
- 単体テスト時は OpenAI 呼び出しやネットワークリソースをモックする（実装内で patch しやすい設計）
  - 例: unittest.mock.patch("kabusys.ai.news_nlp._call_openai_api")

---

ライセンス / 貢献
- （ここにプロジェクトのライセンスやコントリビュート手順を記載してください）

---

問い合わせ
- バグ報告・改善提案は Issue を立ててください。README の不足点や具体的なユースケースに応じてサンプルやユーティリティを追加します。

以上。README の内容を実運用に合わせて適宜補足してください。