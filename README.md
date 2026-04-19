# KabuSys

日本株向け自動売買システムの参照実装（ライブラリ／起動スクリプト群）。

このリポジトリは以下の責務を持つ主要コンポーネントで構成されています：
- 戦略・ポートフォリオ構築（factor / portfolio）
- 発注実行エンジン（ExecutionEngine）
- 監視コンポーネント（System / Trade / Risk Monitor, Kill Switch）
- 研究ユーティリティ（ファクター計算・特徴量解析）
- AI 補助（ニュース NLP によるセンチメント、レジーム判定）
- 運用ユーティリティ（.env ウィザード、設定検証、検証レポート）

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方
- 環境変数（主要）
- ディレクトリ構成（主要ファイル説明）
- 運用上の注意

---

プロジェクト概要
- KabuSys は日本株自動売買のための参照実装です。  
- 戦略で計算したシグナルをもとにポートフォリオを構築し、発注ロジック（注文管理 / リスク管理 / 照合）を通じてブローカーへ発注します。  
- 監視コンポーネントはシステム稼働状況、注文の滞留や約定異常、ドローダウン等を定期チェックし、必要に応じて Kill Switch（data/kill.flag）を書き込んで実行エンジンを停止します。  
- 研究モジュールは DuckDB 上の時系列データを用いてファクター算出や IC 計測などを行います。  
- news_nlp / regime_detector モジュールは OpenAI API（gpt-4o-mini を想定）を用いたセンチメント評価・レジーム判定機能を提供します（APIキーが必要）。

---

機能一覧
- ExecutionEngine 起動スクリプト（run_execution）:
  - 本番 / ペーパートレード切替（KABUSYS_ENV）
  - ブローカー抽象化（BrokerClientFactory）
  - OrderManager / RiskManager / Reconciler を組み合わせた発注実行
  - 停止フラグ（data/stop_requested.flag / data/kill.flag）監視、PID 管理（data/execution.pid）
- Monitoring（run_monitoring）:
  - システム稼働率・CPU/メモリ/Disk 監視
  - データ鮮度チェック（DuckDB）
  - 監視ログの永続化（SQLite `monitoring.db`）
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）
  - 監視は常に本番 sqlite_path を使用（KABUSYS_ENV に依存しない）
- Portfolio モジュール:
  - 候補選定（select_candidates）
  - 等金額 / スコア加重重み（calc_equal_weights, calc_score_weights）
  - セクター集中制限（apply_sector_cap）
  - レジームに応じた投下資金乗数（calc_regime_multiplier）
  - 株数決定・単元丸め・aggregate cap（calc_position_sizes）
- Research（factor_research / feature_exploration）:
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン・IC・統計サマリ
  - DuckDB を用いた SQL+Python 実装（外部 API 依存なし）
- AI（news_nlp / regime_detector）:
  - ニュース集合を LLM に投げ銘柄ごとにセンチメントを算出、ai_scores テーブルへ書き込み
  - レジーム判定は ETF（1321）の MA200 とマクロニュースセンチメントの合成
  - 再試行（指数バックオフ）や部分失敗時のフェイルセーフを実装
- ユーティリティ:
  - .env 対話ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）
  - Paper Trading 検証レポート生成（python -m kabusys.tools.paper_verification_report）

---

セットアップ手順（ローカル使用想定）
1. Python 環境を用意
   - Python 3.10+ を推奨
   - 仮想環境を作成・有効化: python -m venv .venv && source .venv/bin/activate

2. 依存ライブラリをインストール
   - 必要ライブラリ（例）:
     - duckdb
     - psutil
     - openai
     - (任意) PyYAML — config/*.yaml の内容検証に使用
   - 例:
     - pip install duckdb psutil openai pyyaml

   ※ requirements.txt はリポジトリに含めていないため、使用する機能に応じて上記をインストールしてください。

3. 初期設定 (.env)
   - 対話ウィザードで .env を作成:
     - python -m kabusys.config_setup
   - もしくは .env.example（存在する場合）をコピーして編集
   - 重要: JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD は必須

4. 設定検証
   - python -m kabusys.validate_config
   - 問題があれば修正、--strict を付けると警告もエラー扱いになります

5. データディレクトリ作成（必要なら）
   - デフォルトでは data/ と logs/ を使用します。自動作成処理はある程度行われますが権限等で失敗することがあるため事前に作成しておくと安全です:
     - mkdir -p data logs

6. DB 初期化は起動スクリプトが自動で行います（monitoring 用のテーブル作成等）

---

使い方（代表コマンド）
- 実行エンジンを起動（本番 / ペーパーは KABUSYS_ENV で制御）
  - KABUSYS_ENV=development (発注なし)
  - KABUSYS_ENV=paper_trading (MockBroker を使用し data/paper_trading.db を利用)
  - KABUSYS_ENV=live (実際に発注)
  - 実行:
    - python -m kabusys.run_execution
  - 注意:
    - ペーパートレード時は paper_sqlite_path（PAPER_TRADING_SQLITE_PATH）に記録され本番 DB と分離されます

- 監視ループを起動（別プロセスで常駐）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（例: export MONITOR_POLL_INTERVAL=30）
  - 監視は常に Settings.sqlite_path（本番監視 DB）を参照します（KABUSYS_ENV に依存しません）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db（--db で上書き可）

- .env ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict をつけると警告もエラー扱いになり exit code 1 を返す

ログ・DB の既定パス（デフォルト）
- ログ: logs/<app_name>.log（app_name: execution / monitoring 等）
- DuckDB: data/kabusys.duckdb（DUCKDB_PATH 環境変数で上書き可）
- SQLite（監視 DB）: data/monitoring.db（SQLITE_PATH で上書き可）
- Paper Trading SQLite: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可）
- PID / フラグ:
  - data/execution.pid (ExecutionEngine 用 pid ファイル)
  - data/stop_requested.flag（run_* スクリプトが参照）
  - data/kill.flag（KillSwitch が書き込む）

---

主要な環境変数
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABUSYS_ENV — 実行環境: development | paper_trading | live (デフォルト: development)
- OPENAI_API_KEY — OpenAI API を使う機能で必要（news_nlp / regime_detector）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/…）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒。run_monitoring 用）
- PAPER_FILL_MODE — ペーパートレードの約定挙動（instant|partial|never|reject）

詳細は kabusys.config.Settings のプロパティをご参照ください。settings は環境変数の検証・デフォルト解決を行います。

---

ディレクトリ構成（主要ファイルの説明）
- src/kabusys/
  - __init__.py — パッケージ初期化、バージョン
  - config.py — Settings クラス（.env 読み込み・環境変数アクセス）
  - config_setup.py — .env を対話的に作るウィザード
  - validate_config.py — 起動前の設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト（メインエントリ）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - ai/
    - news_nlp.py — ニュースを LLM で評価し ai_scores に書き込むロジック
    - regime_detector.py — レジーム判定（ma200 + マクロセンチメント）
  - monitoring/
    - monitoring_db.py — SQLite に対する永続化レイヤ（テーブル初期化・CRUD）
    - system_monitor.py — CPU/MEM/Disk / データ鮮度 / プロセス PID の監視
    - trade_monitor.py — （注文の滞留・約定異常検出等）※実装ファイルあり
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — 条件に応じて data/kill.flag を書く
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - alert_manager.py — （通知ロジック）※実装ファイルあり
  - execution/
    - execution_engine.py — 実行エンジン本体（セッション管理）
    - broker_factory.py — BrokerClient の生成（実ブローカー / Mock 切替）
    - order_manager.py / order_repository.py / reconciler.py / risk_manager.py — 発注周りの責務分割
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数計算・単元丸め・aggregate cap
    - risk_adjustment.py — セクター制限・レジーム乗数
  - research/
    - factor_research.py — Momentum/Volatility/Value 等のファクター算出（DuckDB）
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - data/ (実行時に使うデータフォルダ; デフォルト: プロジェクトルート/data)
  - logs/ (ログ保存先)

（注）一部ファイルはここで抜粋して紹介しています。実装の詳細は各ファイルの docstring / コメントを参照してください。

---

運用上の注意
- 本番モード（KABUSYS_ENV=live）では十分な確認を行ってください。validate_config はいくつかのガード（LINE 通知設定未設定、KILL_FLAG_CLEAR_ON_START の危険設定等）を警告します。
- Kill Switch（data/kill.flag）は明示的に ExecutionEngine を停止する安全装置です。KILL_FLAG_CLEAR_ON_START を 1 にして本番で自動クリアすることは推奨されません。
- OpenAI API を使う機能は外部依存かつコストが発生します。API キーは安全に管理してください。LLM の応答失敗時はフォールバック動作（0.0 やスキップ）を行いますが、期待する結果が得られない可能性はあります。
- logs/ ディレクトリのパーミッションやマウント先の空き容量を監視してください。ログファイルのローテーションは日次・30 日分保持です。
- DuckDB / SQLite のファイルパスは複数プロセスで共有する場合は注意（同時書き込み等）。設計上、監視 DB とペーパー取引 DB は分離されています。

---

トラブルシュート（よくある項目）
- .env が読み込まれない／自動ロードを無効にしたい:
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを抑制します。
- ログファイルが出力されない:
  - LOG_DIR または log_dir 引数を確認。権限やディレクトリ作成に失敗している場合はコンソール（stdout）にログが出力されます。
- run_monitoring が本番 DB を参照している:
  - 仕様として監視は本番 sqlite_path を参照します（KABUSYS_ENV に依存しない）。開発用に分離したい場合は SQLITE_PATH を変更してください。

---

ライセンス / 貢献
- この README はコードからの抽出説明です。実運用へ移す際は十分なテスト・監査を行ってください。  
- 貢献や Issue は Pull Request を歓迎します。

---

何か特定の操作（起動トラブル、設定例、追加のコマンドラインオプションなど）について詳しいドキュメントが必要であれば教えてください。README を追記して具体的な例やコマンドを追加します。