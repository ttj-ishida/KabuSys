# KabuSys

日本株向けの自動売買 / データパイプライン基盤（KabuSys）のリポジトリ用 README。  
このドキュメントはローカル開発者や運用担当者がプロジェクトを理解し、セットアップ・実行できるようにまとめたものです。

概要
- KabuSys は日本株のデータ取得（J-Quants）、ニュース収集・NLP スコアリング（OpenAI）、市場レジーム判定、ETL パイプライン、監査ログなどを備えた自動売買 / 研究基盤のコンポーネント群です。
- 主に DuckDB を用いたデータ管理、J-Quants API からの差分取得、OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価、研究用ファクター計算モジュールなどが含まれます。
- 設計方針として「ルックアヘッドバイアスの排除」「API 呼び出しのリトライ」「冪等（idempotent）保存」「テストしやすいインターフェース」を重視しています。

主な機能一覧
- データ取得 / ETL
  - J-Quants からの日次株価（OHLCV）・財務データ・上場銘柄情報・市場カレンダー取得（pagination・レート制御・トークン自動リフレッシュ）
  - 差分更新、バックフィル、品質チェック（欠損、スパイク、重複、日付不整合）
- ニュース収集
  - RSS からのニュース収集（SSRF 対策、URL 正規化、記事ID生成、前処理）
- ニュース NLP（OpenAI）
  - 銘柄別ニュースを集約して LLM に投げ、銘柄別 ai_score を ai_scores テーブルに保存
  - マクロニュースを使った市場レジーム判定（ETF 1321 の MA200 乖離と LLM センチメントの合成）
- 監査ログ（audit）
  - signal_events / order_requests / executions を含む監査テーブルを DuckDB に初期化・管理（冪等・UTC タイムスタンプ）
- 研究（research）
  - モメンタム・バリュー・ボラティリティ等のファクター計算、将来リターン計算、IC（Spearman）計算、Zスコア正規化など
- カレンダー管理
  - market_calendar テーブルの管理と営業日判定ユーティリティ（next_trading_day 等）

前提・依存
- Python 3.10+
  - （型注釈に | を使用しているため Python 3.10 以上を推奨）
- 主な Python パッケージ（例）
  - duckdb
  - openai
  - defusedxml
  - その他標準ライブラリ（urllib, json, datetime など）
- ネットワーク接続（J-Quants API, OpenAI, RSS ソース）

セットアップ手順（ローカル開発）
1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml
   - （開発用に setup.py / pyproject.toml があれば pip install -e . を使う）
4. 環境変数設定
   - プロジェクトルートに .env（または .env.local）を作成して必要な環境変数を設定します。
   - 自動ロード: kabusys.config モジュールはプロジェクトルート（.git or pyproject.toml）を探索して .env を自動で読み込みます。テストや明示的に無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
   - 必須の主要環境変数（最低限）
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
     - OPENAI_API_KEY        : OpenAI API キー（score_news / regime_detector 実行時に必須）
     - KABU_API_PASSWORD     : kabu ステーション API パスワード（発注周りがある場合）
     - SLACK_BOT_TOKEN       : Slack 通知が必要な場合
     - SLACK_CHANNEL_ID      : Slack チャネル ID
   - 任意 / デフォルト値を持つ環境変数
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
     - LOG_LEVEL (DEBUG/INFO/...) — デフォルト INFO
     - KABU_API_BASE_URL — デフォルト http://localhost:18080/kabusapi
     - DUCKDB_PATH — デフォルト data/kabusys.duckdb
     - SQLITE_PATH — デフォルト data/monitoring.db
     - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT など
5. データディレクトリ作成（必要に応じて）
   - mkdir -p data

基本的な使い方（例）
- DuckDB 接続を開いて ETL を実行する（日次 ETL）
  - 例（Python スクリプト / REPL）:
    - from datetime import date
      import duckdb
      from kabusys.data.pipeline import run_daily_etl
      conn = duckdb.connect(str(<あなたの DUCKDB パス>))  # 例: settings.duckdb_path を利用
      result = run_daily_etl(conn, target_date=date(2026, 3, 20))
      print(result.to_dict())
- ニューススコアリング（ai スコアを ai_scores テーブルに書き込む）
  - from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    n = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")
    print(f"wrote {n} scores")
  - api_key を省略すると環境変数 OPENAI_API_KEY が使用されます
- 市場レジーム判定
  - from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime
    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, target_date=date(2026,3,20), api_key=None)  # 環境変数経由でも可
- 監査 DB 初期化（監査テーブルを作成）
  - from kabusys.data.audit import init_audit_db
    conn = init_audit_db("data/audit.duckdb")
    # 以後 conn を使って監査関連操作

運用・運転例
- 日次バッチ（Cron / systemd timer）で run_daily_etl を呼ぶ（ターゲット日=当日）
- ニュース収集ジョブは複数 RSS を順次 fetch_rss して raw_news に書き込むフローを実装する
- OpenAI 呼び出しはレート制御 / リトライ済みだが、API キーとコスト制御・ロギングは必須
- 本番稼働時は KABUSYS_ENV=live を設定し、ロギングや Slack 通知を有効化する

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py                : パッケージ定義
  - config.py                  : 環境変数 / settings 管理（.env 自動読み込みロジック含む）
  - ai/
    - __init__.py
    - news_nlp.py              : ニュース NLP スコアリング（銘柄別 ai_scores 書込み）
    - regime_detector.py       : マクロセンチメント + MA200 で市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py        : J-Quants API クライアント（fetch/save の実装、レート制御、リトライ）
    - pipeline.py              : ETL パイプライン（run_daily_etl 等）
    - etl.py                   : ETLResult を再エクスポート
    - news_collector.py        : RSS 収集と前処理
    - calendar_management.py   : market_calendar 管理、営業日判定ユーティリティ
    - quality.py               : データ品質チェック（欠損・スパイク・重複・日付整合）
    - stats.py                 : 汎用統計ユーティリティ（zscore_normalize）
    - audit.py                 : 監査ログテーブル初期化・ユーティリティ
  - research/
    - __init__.py
    - factor_research.py       : モメンタム / バリュー / ボラティリティ等の計算
    - feature_exploration.py   : 将来リターン、IC、統計サマリー等
  - ai/、data/、research/ 以下はさらに細分化された関数群を持ちます。

設計上の重要点（運用時の注意）
- Look-ahead バイアス対策
  - 多くの処理（news_window, regime, ETL 等）は datetime.today() を直接参照せず、呼び出し側が target_date を渡す設計です。バックテスト時には必ず適切な target_date を渡してください。
- 冪等性
  - DB への保存は ON CONFLICT DO UPDATE / INSERT … DO NOTHING などで冪等に実装されています。複数実行しても問題が起きにくい設計です。
- OpenAI / J-Quants の API 呼び出しはリトライ・バックオフ・エラー時のフォールバック（例: macro_sentiment=0.0）を実装していますが、コストやレート制限には注意してください。
- セキュリティ
  - news_collector は SSRF 対策（ホスト検査、リダイレクト検査）・XML の安全パーサ（defusedxml）を使用しています。RSS ソースの追加時は信頼できるソースのみを指定してください。

よくある実行例（短いサンプル）
- 日次 ETL（スクリプト）
  - # run_etl.py
    from datetime import date
    import duckdb
    from kabusys.data.pipeline import run_daily_etl
    conn = duckdb.connect("data/kabusys.duckdb")
    res = run_daily_etl(conn, target_date=date.today())
    print(res.to_dict())
- ニューススコア（スクリプト）
  - # score_news.py
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    print(score_news(conn, target_date=date(2026,3,20)))

テスト・デバッグ
- 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると config の自動 .env ロードを無効化できます（ユニットテストで .env の自動ロードを防ぐ用途など）。
- OpenAI 呼び出しや外部 HTTP をモックしやすいよう、各モジュールは外部呼び出しを行う関数を内部で分離しています（テスト時はモック/patch 可能）。

ライセンス・貢献
- （ここにライセンス情報を明記してください。例: MIT ライセンス等）
- 貢献方法や issue / PR の運用ルールはリポジトリの CONTRIBUTING.md を参照してください（存在する場合）。

補足
- この README はソースコードのヘッダコメントとモジュール実装に基づいて作成しています。実際のデプロイ時は各 API キーやシークレットの管理、ログ収集、監視（monitoring モジュール）など運用面の追加設定が必要です。

もし README に追記したいサンプルや運用手順（systemd unit、Dockerfile、CI スクリプトなど）があれば教えてください。必要に応じて具体例を追加します。