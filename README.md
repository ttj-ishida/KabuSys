# KabuSys

KabuSys は日本株向けの自動売買システムのコアライブラリ群です。  
戦略のためのファクター計算、ポートフォリオ構築、注文管理・実行エンジン、監視・アラート、LLM を用いたニュースセンチメント評価など、運用に必要な主要コンポーネントを含みます。

主な設計方針
- DuckDB / SQLite を使ったローカルデータ処理（外部 API 呼び出しを最低限に）
- テスト可能な純粋関数群（ポートフォリオ、ファクター計算等）
- Paper Trading 環境と本番環境の分離（DB・挙動の分離）
- LLM 呼び出しはフェイルセーフ（失敗してもシステムは継続）

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（実行例）
- ディレクトリ構成
- 主要環境変数 / 設定

---

プロジェクト概要
- 名称: KabuSys
- 目的: 日本株の自動売買パイプライン（データ処理 → シグナル生成 → 注文発行 → 監視・リスク制御）を提供する。
- 言語: Python
- 主な依存: duckdb, psutil, requests, openai, streamlit（詳細は下記）

---

機能一覧
- execution（発注関連）
  - OrderManager / ExecutionEngine（注文生成・送信、リスク制御、再起動時のリコンシリエーション）
  - Broker クライアントファクトリ（本番 / モックの切り替え）
- monitoring（監視）
  - SystemMonitor（プロセス状態、CPU/メモリ/Disk、データ鮮度チェック）
  - TradeMonitor（滞留注文、約定価格異常検知）
  - RiskMonitor（ドローダウン・ポジション数制限）
  - KillSwitch（条件に応じた停止フラグ書き込み）
  - AlertManager（LINE によるプッシュ通知）
  - Streamlit ダッシュボード（監視用 UI）
- portfolio（ポートフォリオ構築）
  - 候補抽出、等分/スコア加重、リスク調整（セクターキャップ、レジーム乗数）、ポジションサイズ計算
- research（調査・ファクター計算）
  - momentum / volatility / value ファクター算出、将来リターン、IC（Information Coefficient）、統計サマリ
- ai（LLM を使った処理）
  - news_nlp: ニュース記事の銘柄別センチメント取得（OpenAI）
  - regime_detector: ETF の MA とマクロ記事のセンチメントを合成して市場レジーム判定
- tools
  - paper_verification_report: Paper Trading の検証レポート生成（稼働率、注文成功率、レイテンシ等）
  - streamlit_dashboard: 監視データ参照用ダッシュボード
- DB/ユーティリティ
  - MonitoringDB（SQLite による監視ログ永続化、テーブルの初期化・マイグレーション）
  - 設定管理（.env 自動読み込み、Settings クラス）

---

セットアップ手順（開発用）
前提
- Python 3.10+（typing の '|' 演算子を使用）
- git, sqlite3（OS 標準）など

1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install --upgrade pip
   - pip install duckdb psutil requests openai streamlit
   - （必要に応じて追加のライブラリをインストールしてください）

   ※ 実運用では requirements.txt を作成して pip install -r requirements.txt を使うことを推奨します。

4. データディレクトリ作成
   - mkdir -p data

5. 環境変数設定
   - プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 主要な環境変数については「主要環境変数 / 設定」を参照してください。

---

使い方（実行例）

1) Execution Engine を起動（通常運用）
- デフォルトでは KABUSYS_ENV により DB 等の挙動が変わります。
  - development（デフォルト）
  - paper_trading（Mock ブローカーを使用し data/paper_trading.db を使う）
  - live（本番）
- 実行:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - KABUSYS_ENV=live python -m kabusys.run_execution

2) Monitoring を起動（ポーリング）
- run_monitoring は定期的に SystemMonitor.check_once() を呼び出し監視ログを記録します。
- 実行:
  - python -m kabusys.run_monitoring
- ポーリング間隔を変更する場合:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - （単位: 秒、1 秒以上の正の整数。無効値はデフォルト 60 秒にフォールバック）

3) Paper Trading 検証レポート（コマンドライン）
- python -m kabusys.tools.paper_verification_report
- 期間指定:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- DB パスを指定:
  - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

4) Streamlit ダッシュボード（監視 UI）
- streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

5) AI 関連（ニューススコア / レジーム判定）
- OpenAI API キーが必要（環境変数 OPENAI_API_KEY または関数引数で渡す）
- 例（Python API 呼び出し）:
  - from kabusys.ai.news_nlp import score_news
    score_news(conn, target_date, api_key="...")

6) Kill Switch / フラグファイル
- KillSwitch は data/kill.flag（デフォルト）へ停止理由を書き込み、ExecutionEngine が検知して安全停止する用途に使う設計です。
- 設定は Settings.kill_flag_path 参照。

---

主要環境変数 / 設定
- 共通
  - KABUSYS_ENV: development | paper_trading | live（default: development）
  - LOG_LEVEL: DEBUG|INFO|...（default: INFO）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 にすると .env 自動読み込みを無効化
- 認証 / 外部 API
  - JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須として使う箇所あり）
  - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
  - OPENAI_API_KEY: OpenAI API キー（ニュース/レジーム機能で使用）
- DB / ファイルパス
  - DUCKDB_PATH: DuckDB ファイル（default: data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（default: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（default: data/paper_trading.db）
  - PID_FILE_PATH: ExecutionEngine の PID ファイル（default: data/execution.pid）
  - KILL_FLAG_PATH: kill.flag のパス（default: data/kill.flag）
- Paper Trading 固有
  - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）
- 監視しきい値（Settings プロパティで取得）
  - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT（%）

Settings（kabusys.config.Settings）クラスを通じて上述の値を参照できます。.env フォーマットは Bash 風の KEY=VALUE に対応し、シングル/ダブルクォートや export プレフィックスも扱います。

---

ディレクトリ構成（主要ファイル抜粋）
- src/
  - kabusys/
    - __init__.py
    - config.py
    - run_execution.py            — ExecutionEngine 起動スクリプト
    - run_monitoring.py          — SystemMonitor ポーリング起動スクリプト
    - data/                      — （DuckDB / データパイプライン関連、別ファイル）
    - execution/
      - execution_engine.py
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - broker_factory.py
      - ... (注文・ブローカー関連)
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - monitoring_engine.py
      - alert_manager.py
      - kill_switch.py
      - streamlit_dashboard.py
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
      - __init__.py
    - research/
      - factor_research.py
      - feature_exploration.py
      - __init__.py
    - ai/
      - news_nlp.py
      - regime_detector.py
      - __init__.py
    - tools/
      - paper_verification_report.py
      - __init__.py
    - utils/
      - process_priority.py
      - __init__.py

（実際のリポジトリではさらに多くのファイル・サブパッケージが存在します。上は読みやすさのため抜粋した一覧です。）

---

開発上の注意 / 実装上のポイント
- Paper Trading は本番 DB と完全に分離（PAPER_TRADING_SQLITE_PATH を使用）。
- run_execution / run_monitoring は起動時にプロセス優先度を上げようとします（psutil を使用）。権限不足等で失敗しても警告を出して継続します。
- モジュールは「ルックアヘッドバイアス」を避ける設計になっており、target_date を明示的に渡すよう作られています（date.today() を直接参照しない等）。
- OpenAI 呼び出しはリトライ・バックオフ処理やレスポンスバリデーションを行い、失敗時はフェイルセーフで継続します。
- MonitoringDB はテーブルの初期化と簡易マイグレーション処理を行います（スキーマ追加時の互換性確保）。

---

トラブルシューティング
- DB ファイルが開けない場合
  - monitoring 用 streamlit では read-only URI で開くため、ファイルが存在しないとエラーになります。まず MonitoringEngine を起動して monitoring DB を初期化してください。
- OpenAI 呼び出しでエラーが出る場合
  - OPENAI_API_KEY が設定されているか確認。ネットワークの問題やレート制限はログに記録され、実装側でリトライが行われます。
- 環境変数自動読み込みを無効化したい
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してからアプリケーションを起動してください。

---

ライセンス / 貢献
- 本 README はコードベースの理解を補助するためのドキュメントです。実運用前に十分なテスト・レビューを行ってください。
- 貢献やバグ報告はリポジトリの issue/PR を使用してください。

---

その他
- 実運用では logging 設定やプロセスマネージャ（systemd / supervisord など）との連携、バックアップ、監査ログの保管、セキュアな API キー管理など追加の運用設計が必要です。

必要であれば、README をベースにインストール用の requirements.txt、デプロイ手順（systemd ユニット例）、`.env.example` の雛形なども作成します。どれを優先して作成しましょうか？