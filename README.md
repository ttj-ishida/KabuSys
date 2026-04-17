# KabuSys

日本株向けの自動売買 / 研究プラットフォーム（モジュール群）。  
このリポジトリは、発注エンジンの起動スクリプト・監視・ポートフォリオ構築、ファクター計算、AI ニューススコアリング等の主要コンポーネントを含みます。

---

## プロジェクト概要

KabuSys は以下を目的とした Python ベースのシステムです。

- 発注エンジン（ExecutionEngine）による自動売買（本番 / ペーパートレード対応）
- 監視コンポーネントによるプロセス・注文・リスク監視と Kill Switch
- ポートフォリオ構築（候補選定、重み付け、ポジションサイジング）
- リサーチ用モジュール（ファクター計算、将来リターン、IC 等）
- AI（OpenAI）を用いたニュースセンチメント / レジーム判定
- 各種 CLI ツール（.env ウィザード、設定検証、ペーパートレード検証レポート）

設計方針として、DB（DuckDB / SQLite）を参照して計算を行い、外部依存（本番 API）への直接アクセスは環境に応じて切り替えられるようになっています。

---

## 主な機能一覧

- 起動スクリプト
  - run_execution.py — 発注エンジン起動（KABUSYS_ENV=paper_trading のときはモックブローカーを使用）
  - run_monitoring.py — SystemMonitor ポーリングループ起動（監視ログ保存）
- 設定管理
  - config_setup.py — 対話式 .env 作成ウィザード
  - validate_config.py — .env / config/*.yaml の静的チェック CLI
  - Settings クラス — 環境変数ラッパ（自動ロード機能あり）
- モニタリング
  - system_monitor, trade_monitor, risk_monitor, monitoring_engine, kill_switch, monitoring_db
  - SQLite に監視ログ（system_status, trade_logs, risk_logs, dashboard, positions）を保存
- 発注・実行（エンジン周辺）
  - ExecutionEngine, OrderManager, OrderRepository, Reconciler, RiskManager（実装ファイル群は execution パッケージ）
  - PID ファイル / stop フラグによる制御、paper_trading 用 DB 分離
- ポートフォリオ構築
  - 銘柄選定、等金額・スコア加重、セクター制約、ポジションサイズ計算、ロット丸め等
- リサーチ
  - ファクター（momentum, volatility, value）計算、将来リターン、IC、統計サマリー
  - DuckDB に格納された prices_daily / raw_financials を参照
- AI（OpenAI）
  - news_nlp.score_news — ニュースを LLM でスコアリングして ai_scores テーブルへ書き込み
  - regime_detector.score_regime — ETF とマクロニュースを合成して市場レジーム判定
- ツール
  - tools.paper_verification_report — ペーパートレード DB を集計して PASS/FAIL 判定およびレポート出力

---

## セットアップ手順（開発環境向け）

1. リポジトリをクローン
   - git clone <repo-url>

2. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージのインストール（最低限）
   - pip install duckdb psutil openai
   - validate_config の YAML 検証を有効にする場合: pip install PyYAML

   （プロジェクトに requirements.txt がある場合はそれを使用してください）

4. 初期設定 (.env) の作成
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - 生成される .env は Git にコミットしないでください（機密情報を含みます）。

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告もエラー扱いにしたい場合:
     - python -m kabusys.validate_config --strict

6. データディレクトリの準備（必要に応じて）
   - デフォルトでは data/ 以下に DB や PID/flag ファイルを作成します。必要なら先に作成してください:
     - mkdir -p data

7. 環境変数の注意点
   - 必須:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 主要なオプション（デフォルト値）
     - KABUSYS_ENV: development | paper_trading | live  （デフォルト: development）
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db (paper_trading 用)
     - LOG_LEVEL: INFO
     - OPENAI_API_KEY: OpenAI を使う場合に必須
     - PAPER_FILL_MODE: instant | partial | never | reject (デフォルト: "instant")
     - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
   - 自動 .env ロードを無効化する:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 使い方

- 発注エンジンを起動（通常）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV が paper_trading の場合、MockBrokerClient を使い data/paper_trading.db に記録
    - PID ファイル: data/execution.pid（デフォルト）
    - 停止: プロジェクト ルート/data/stop_requested.flag が存在すると起動を終了 / 実行中は停止を試みます

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒で上書き可能（例: MONITOR_POLL_INTERVAL=30）
  - 監視は monitoring DB（Settings.sqlite_path）を使用。KABUSYS_ENV に関係なく本番 sqlite_path を使用します
  - 停止フラグ: data/stop_requested.flag を検出するとループを終了します

- .env の対話式作成
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を指定すると警告もエラー扱いになります

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI 機能（ニューススコアリング / レジーム判定）
  - OpenAI API キーが必要: OPENAI_API_KEY 環境変数または関数引数で指定
  - 関数:
    - kabusys.ai.score_news (news_nlp.score_news)
    - kabusys.ai.regime_detector.score_regime
  - CLI ラッパーは提供していませんが、モジュール関数をスクリプトやジョブから呼び出して使用します

- 停止・Kill Switch
  - 監視側（KillSwitch）は条件に応じて data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります
  - 手動停止:
    - data/stop_requested.flag を作成すると run_execution/run_monitoring のループが検出して終了します
  - kill.flag と stop_requested.flag は別扱い:
    - kill.flag: 監視が発行する“業務上の停止”フラグ（ExecutionEngine は起動時に KILL_FLAG_CLEAR_ON_START=1 の場合自動で削除する設定あり）
    - stop_requested.flag: ランタイムループの単純な停止要求

---

## ディレクトリ構成（主要ファイル）

（以下は src/kabusys 以下の主要ファイルを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — Settings クラス・.env 自動ロード
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — ペーパートレード検証レポート
  - utils/
    - __init__.py
    - process_priority.py     — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py       — SQLite テーブル初期化・永続化 API
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py       — （アラート送信ロジック: LINE 等）※実装箇所が続く
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
  - execution/                — ExecutionEngine 関連（OrderManager, OrderRepository, RiskManager など）
  - data/                     — デフォルトの DB/flag/pid ファイル配置（実行時に作成）
    - kabusys.duckdb (DuckDB)
    - monitoring.db (SQLite)
    - paper_trading.db (SQLite, paper_trading 用)

（上記は主要モジュールの概要です。実際のファイル一覧はリポジトリを参照してください）

---

## 重要な挙動・注意点

- 環境分離
  - paper_trading モードでは本番の SQLite を使用せず、デフォルトで data/paper_trading.db を使用して完全に分離されます
- .env の自動読み込み
  - プロジェクトルート（.git または pyproject.toml を探索）にある .env/.env.local を自動で読み込みます
  - テスト等で自動読み込みを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください
- 必須環境変数の管理
  - J-Quants や kabuステーション API の秘密情報は .env に保存し、決して Git にコミットしないでください
- OpenAI
  - news_nlp / regime_detector は OpenAI を利用します。API 呼び出し時の失敗やレート制限はリトライロジックである程度回復しますが、API キーは必須です
- 依存権限
  - process_priority.set_process_priority は OS によって権限が必要な場合があり、psutil の例外が発生した場合は警告を出してスキップします
- DB マイグレーション（軽微）
  - monitoring_db.init_monitoring_db は既存 DB にカラムがない場合の ALTER を実施する簡易マイグレーションを行います

---

## トラブルシューティング（よくある質問）

- 起動しても .env の値が反映されない
  - プロジェクトルートが自動認識されなかった可能性があります。明示的に .env を読み込むか、KABUSYS_DISABLE_AUTO_ENV_LOAD を確認してください
- validate_config で PyYAML が見つからないという警告
  - YAML 検証機能を使う場合は PyYAML をインストールしてください（pip install PyYAML）。インストールされていない場合は YAML ファイルの内容検証をスキップします
- OpenAI 呼び出しで 429 / タイムアウトが出る
  - news_nlp / regime_detector は指数バックオフでリトライしますが、繰り返す場合は API キー／料金枠や呼び出し頻度を見直してください

---

必要があれば README を拡張して以下の内容も追加できます:
- 詳細な設定項目一覧（すべての環境変数と説明）
- ExecutionEngine の動作フロー図、OrderRepository / OrderManager API ドキュメント
- アラート（LINE）設定方法とフォーマット例
- テスト実行方法・ユニットテストの書き方

ご希望があれば上記のいずれかを追加して README を拡張します。