KabuSys — 日本株自動売買システム (README)
=========================================

概要
----
KabuSys は日本株向けの自動売買・調査・監視コンポーネント群を含む Python パッケージです。
主な目的は「発注実行（ExecutionEngine）」「実行監視（Monitoring）」「ファクター計算／リサーチ」「ペーパートレード検証」「ニュース NLP によるセンチメント評価」などを提供することです。  
各機能はモジュール化されており、設定は .env（もしくは環境変数）で行います。ペーパートレード時は本番 DB と分離された専用 SQLite を使用します。

機能一覧
--------
- 実行エンジン起動スクリプト（run_execution）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を利用し、data/paper_trading.db に記録
  - プロセス優先度設定・PID ファイル管理・停止フラグ検知
- 監視ループ起動スクリプト（run_monitoring）
  - システム・取引・リスク監視をポーリングで実行
  - MONITOR_POLL_INTERVAL でポーリング間隔変更可能（デフォルト 60 秒）
- 設定ウィザード（config_setup）
  - 対話式で .env を生成・更新
- 設定検証 CLI（validate_config）
  - .env / config/*.yaml / 必須環境変数等のチェック（--strict オプションあり）
- ペーパートレード検証レポート（tools/paper_verification_report）
  - paper_trading DB から稼働率・注文成功率・レイテンシ等を集計してレポート出力
- ポートフォリオ構築ユーティリティ（portfolio）
  - 候補選定・重み計算・ポジションサイズ決定・セクターキャップ適用等
- リサーチ（research）
  - モメンタム・ボラティリティ・バリュー等のファクター計算、IC 計算など（DuckDB 使用）
- AI 関連（ai）
  - news_nlp: OpenAI を用いたニュースセンチメント評価と ai_scores テーブルへの書き込み
  - regime_detector: ETF とマクロ記事を組み合わせた市場レジーム判定
- ユーティリティ
  - ロギング設定、プロセス優先度/CPU affinity 管理、監視 DB ラッパー等

必要条件 / 依存パッケージ
-----------------------
（プロジェクトに requirements.txt は含まれていません。最低限の推奨パッケージ例を示します）
- Python 3.9+
- duckdb
- psutil
- openai (AI モジュールを使う場合)
- PyYAML（config/*.yaml の構文チェックを行いたい場合）
- sqlite3 は標準ライブラリで利用

セットアップ手順
--------------
1. リポジトリをクローンし、仮想環境を作成・有効化します（例）:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストールします（例）:
   - pip install duckdb psutil openai pyyaml

   ※ 開発・運用に応じて追加パッケージをインストールしてください。

3. .env を作成します（2 通りの方法）:
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - 手動で作成:
     - プロジェクトルートに .env を置く（.env.example を参考にすることを推奨）
   - 自動ロード:
     - config.py がプロジェクトルート（.git または pyproject.toml を基準）から .env/.env.local を自動ロードします。
     - 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

4. 設定検証:
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit(1)）になります。

主要な環境変数とデフォルト
--------------------------
（主なもののみ抜粋）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）。デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabuステーション API ベース URL（デフォルト http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視 DB。デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレードでの約定挙動（instant / partial / never / reject。デフォルト instant）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト INFO）
- PID_FILE_PATH: Execution の PID ファイル（デフォルト data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリア（0/1、デフォルト 0。本番では 0 推奨）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、run_monitoring で使用。デフォルト 60）

使い方（実行例）
----------------
- 実行エンジンを起動（本番 / ペーパーの設定は KABUSYS_ENV に依存）:
  - python -m kabusys.run_execution

  特記:
  - 起動時に data/stop_requested.flag が既に存在する場合は起動せず終了します。
  - 実行中に data/stop_requested.flag を作成すると安全に停止します（フラグ検知で engine.stop() を呼ぶ）。

- 監視ループを起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒で上書きできます。
    - 監視は本番 sqlite_path を使って永続化されます（環境に依らず同じパスを使用）。

- 設定ウィザード:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ペーパートレード検証レポート生成:
  - python -m kabusys.tools.paper_verification_report
  - 範囲指定例: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を明示する場合: --db PATH （環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI モジュール（ニュース／レジーム判定）
  - OpenAI を利用するため OPENAI_API_KEY の設定が必要:
    - news_nlp.score_news / regime_detector.score_regime は OpenAI API キーを参照して動作します。
  - 例: Python スクリプトから kabusys.ai.score_news を呼ぶ際に api_key を渡すか、環境変数を設定してください。

運用・停止・ログ
----------------
- 停止フラグ:
  - data/stop_requested.flag: run_execution/run_monitoring がループ内でポーリングして検知する停止フラグ（外部で作成すれば安全停止）。
  - data/kill.flag: KillSwitch により作成されるフラグ。ExecutionEngine に停止シグナルを送る（Execution はこのフラグの存在を確認して停止する設計）。
  - kill.flag を自動でクリアしたい場合は KILL_FLAG_CLEAR_ON_START=1 を設定できるが、本番では危険なので推奨しません。
  - 手動でクリアするにはファイルを削除してください（例: rm data/kill.flag）。

- PID ファイル:
  - data/execution.pid など。スクリプトは起動時に PID ファイルを扱うためログや監視に利用できます。

- ログ:
  - logs/<app_name>.log に日次ローテーションで出力（デフォルト logs/ ディレクトリ）。
  - setup_logging ユーティリティで一貫したログ設定を行っています。
  - LOG_DIR 環境変数でログ出力先を変更可能。

ディレクトリ構成（主要ファイル）
------------------------------
以下は本リポジトリの主要モジュールと役割の抜粋（コードベースに基づく）:

- src/kabusys/
  - __init__.py
  - config.py
    - Settings クラス: 環境変数のラップ、デフォルト値・検証を提供
  - config_setup.py
    - .env の対話式生成ウィザード
  - validate_config.py
    - 起動前に設定不備を検出する CLI
  - run_execution.py
    - ExecutionEngine の起動スクリプト（プロセス優先度・DB 接続・スレッド実行・停止フラグ管理）
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト
  - monitoring/
    - monitoring_db.py: SQLite ベースの永続化層（テーブル初期化 / CRUD）
    - system_monitor.py: システム／データ鮮度監視
    - trade_monitor.py: （取引監視、ソースに実装あり）
    - risk_monitor.py: ドローダウン・ポジション数監視
    - monitoring_engine.py: 各モニタを束ねる実行エンジン
    - kill_switch.py: kill.flag 操作ユーティリティ
    - alert_manager.py: （アラート送信のハンドラ）
  - execution/
    - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py
      - Execution の中核・注文管理・リスク判定・ブローカークライアント生成など
  - portfolio/
    - portfolio_builder.py, position_sizing.py, risk_adjustment.py
      - 候補選定、重み算出、株数決定、セクター制限・レジーム乗数
  - research/
    - factor_research.py, feature_exploration.py
      - DuckDB を用いたファクター計算・IC・統計サマリー等
  - ai/
    - news_nlp.py: ニュースを LLM でスコアリングして ai_scores に書き込む
    - regime_detector.py: ETF とマクロニュースで市場レジームを判定
  - tools/
    - paper_verification_report.py: ペーパートレードの検証レポート生成
  - utils/
    - logging_setup.py: ログの一括設定（コンソール + 日次ファイルローテ）
    - process_priority.py: プロセス優先度 / CPU affinity 設定ユーティリティ

運用上の注意
------------
- 本番（KABUSYS_ENV=live）では設定内容を慎重に確認してください（validate_config の live ガードあり）。
- kill.flag や KILL_FLAG_CLEAR_ON_START の扱いは慎重に：自動クリア設定は本番では危険です。
- ペーパートレードは本番 DB と分離されています（PAPER_TRADING_SQLITE_PATH）。
- AI モジュールを使う場合は API の利用上限や料金に注意してください。API エラー時はフェイルセーフで継続する実装が多く含まれますが、運用方針を定めてください。
- DuckDB / SQLite ファイルの配置先は設定次第で変更可能です（環境変数 DUCKDB_PATH / SQLITE_PATH 等）。

開発者向けメモ
--------------
- config.py はプロジェクトルートを __file__ から探索して .env/.env.local を自動読み込みします（CWD に依存しない）。
- monitoring_db.init_monitoring_db は既存 DB に対して安全にマイグレーション（列追加）を行います。
- テスト時には外部 API 呼び出し（OpenAI・kabu API 等）をモックすることを想定した実装がされています（テストフレームワークで patch 可能）。

問い合わせ・貢献
----------------
バグ報告や改善提案は Issue を立ててください。Pull Request には動作確認と可能であればユニットテストを付加してください。

---

この README は現行のコードベース（主要モジュール）に基づき作成しています。実際の運用前に python -m kabusys.validate_config で設定を確認し、必要なパッケージや API キーが揃っていることを確認してください。