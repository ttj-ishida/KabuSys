README
======

概要
----
KabuSys は日本株向けの自動売買 / 研究プラットフォーム向けユーティリティ群です。
このリポジトリには、以下のような機能を提供するモジュール群が含まれます。

- Execution Engine 起動スクリプト（本番／ペーパートレード切替対応）
- 監視サブシステム（System / Trade / Risk のモニタリング、Kill Switch）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算・セクター制限）
- リサーチ（ファクター計算、特徴量探索、IC 計算等）
- AI 補助（ニュース NLP による銘柄センチメント、マクロニュースでのレジーム判定）
- 運用ツール（ペーパートレード検証レポート生成など）
- 設定ウィザード・設定検証 CLI

設計上のポイント
- ペーパートレード（KABUSYS_ENV=paper_trading）の場合は MockBroker を使い、本番用 DB と分離して data/paper_trading.db に記録します。
- 監視（Monitoring）は環境に関わらず本番の sqlite_path を利用して監視ログを残します（監視 DB は冪等で初期化されます）。
- OpenAI を用いるモジュールは API キーが必要（環境変数 OPENAI_API_KEY、または関数引数で指定可能）。API エラーはフォールバック処理あり。
- .env の自動ロード機構あり（プロジェクトルートの .env / .env.local）。必要なら自動ロードを無効化できます。

主な機能一覧
--------------
- 実行:
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV により本番 / ペーパートレード切替）
  - run_monitoring.py: SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL で間隔指定可）
- 設定:
  - config_setup.py: 対話式ウィザードで .env を生成 / 更新
  - validate_config.py: .env と config/*.yaml の内容を起動前に検証
- 監視:
  - monitoring_engine.py: 各 Monitor（System/Trade/Risk）を束ねる
  - kill_switch.py: 条件により data/kill.flag を書き込み ExecutionEngine 停止を指示
  - monitoring_db.py: SQLite を用いた監視ログ永続化（スキーマ作成・マイグレーション含む）
- ポートフォリオ:
  - portfolio_builder.py / position_sizing.py / risk_adjustment.py：候補選定、重み計算、株数決定、セクター制御等
- リサーチ:
  - factor_research.py / feature_exploration.py：モメンタム・ボラティリティ・バリュー等のファクター計算、IC・統計サマリ
- AI:
  - news_nlp.py: raw_news を OpenAI でスコアリングして ai_scores に書き込む
  - regime_detector.py: ETF (1321) の MA200 とマクロニュースから市場レジームを判定
- ツール:
  - tools/paper_verification_report.py: ペーパートレード DB を解析して検証レポートを出力

前提条件
-------
- Python 3.10+
- 必須パッケージ（例）:
  - duckdb
  - psutil
  - openai
- 推奨 / 任意:
  - PyYAML（config/*.yaml の検証用。なくても動作するが validate_config の一部がスキップされます）
- その他: SQLite は標準ライブラリで利用可能

セットアップ手順
----------------
1. リポジトリをクローンしてワークディレクトリに移動します。

2. 仮想環境を作成して有効化します（例）:
   - python -m venv .venv
   - source .venv/bin/activate (Linux/macOS)
   - .venv\Scripts\activate (Windows)

3. 必要パッケージをインストールします（requirements.txt が無い場合は手動で）:
   - pip install duckdb psutil openai
   - （オプション）pip install pyyaml

4. .env を用意します:
   - 対話式で作る: python -m kabusys.config_setup
     - ウィザードが .env を作成します（.env は Git にコミットしないでください）
   - あるいは .env.example を参考に手動作成してください。

5. 設定検証:
   - python -m kabusys.validate_config
   - 必要に応じて --strict を付けると警告もエラー扱いになります。

6. data ディレクトリの作成（必要に応じて）:
   - デフォルトパス（.env を使わない場合）:
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db

環境変数（主要なもの）
---------------------
- JQUANTS_REFRESH_TOKEN: (必須) J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD: (必須) kabuステーション API パスワード
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時に必要）
- KABUSYS_ENV: 実行環境（development | paper_trading | live。デフォルト development）
  - paper_trading の場合、ペーパートレード専用 DB を使用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG, INFO, ...）
- KILL_FLAG_CLEAR_ON_START: ExecutionEngine 起動時に kill.flag を自動クリアするか（開発用。0/1）
- MONITOR_POLL_INTERVAL: run_monitoring で監視ループのポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: ペーパートレードの約定挙動（instant | partial | never | reject）

使い方
------
- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード（警告で終了）: python -m kabusys.validate_config --strict

- 実行エンジン起動
  - python -m kabusys.run_execution
  - 特記事項:
    - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、PAPER_TRADING_SQLITE_PATH に書き込みます。
    - 起動前または実行中に data/stop_requested.flag が存在すると起動・ループ実行を停止します。
    - 実行時は data/execution.pid に PID を書きます（設定により変更可）。

- 監視プロセス起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で上書き可能（デフォルト 60 秒）。
  - 監視は monitoring DB（sqlite_path）を使用してログを記録します。
  - run_monitoring は data/stop_requested.flag を検知するとループを終了します。

- Kill Switch（監視側から ExecutionEngine 停止）
  - Kill 条件が満たされると監視側の KillSwitch が data/kill.flag を書き込みます。
  - ExecutionEngine は kill.flag の存在を検出すると停止する挙動を持ちます（Settings.kill_flag_path でパスを変更可）。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動で削除します（本番では推奨しません）。

- ペーパートレード検証レポート（ツール）
  - python -m kabusys.tools.paper_verification_report
  - 範囲指定:
    - --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定:
    - --db PATH（環境変数 PAPER_TRADING_SQLITE_PATH が使えます）

- AI モジュール（プログラム的に利用）
  - news_nlp.score_news(conn, target_date, api_key=None)
    - conn: DuckDB 接続
    - target_date: datetime.date（評価日）
    - api_key: OpenAI API キーを直接渡すことも可能
  - regime_detector.score_regime(conn, target_date, api_key=None)
  - これらを使う際は OPENAI_API_KEY を環境変数に設定するか、api_key を明示して呼び出してください。

プログラム実行例（簡単な shell コマンド）
---------------------------------
- .env を作って検証してから実行:
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config
  - python -m kabusys.run_execution
  - python -m kabusys.run_monitoring

- 監視間隔を 30 秒に変える:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

データ・フラグファイル
--------------------
- data/monitoring.db (デフォルト: SQLITE_PATH)
  - 監視ログ・trade_logs・positions・risk_logs・dashboard 等を保持
- data/kabusys.duckdb (デフォルト: DUCKDB_PATH)
  - prices_daily / raw_financials / raw_news 等の分析データ
- data/paper_trading.db (デフォルト: PAPER_TRADING_SQLITE_PATH)
  - ペーパートレード専用の発注ログ等
- data/execution.pid (デフォルトの PID ファイルパス)
  - 実行エンジンの PID を格納
- data/kill.flag
  - KillSwitch が書き込む停止フラグ（ExecutionEngine はこれを検知して停止）
- data/stop_requested.flag
  - run_monitoring / run_execution の外部停止要求（手動停止等に利用）

ディレクトリ構成
----------------
（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数・設定管理
    - config_setup.py          — 対話式 .env ウィザード
    - validate_config.py       — 設定検証 CLI
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
    - ai/
      - __init__.py
      - news_nlp.py            — ニュース NLP スコアリング
      - regime_detector.py     — 市場レジーム判定
    - monitoring/
      - monitoring_db.py       — SQLite スキーマ / 永続化層
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
      - alert_manager.py       — アラート送信管理（未表示の実装ファイル）
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - factor_research.py
      - feature_exploration.py
    - tools/
      - paper_verification_report.py
    - utils/
      - process_priority.py

開発・運用上の注意
-----------------
- .env ファイルは機密情報（API キー等）を含むため、絶対にバージョン管理に含めないでください。
- KABUSYS_ENV=live のときは特に LINE 通知等の設定を確認し、Kill Switch の自動クリア（KILL_FLAG_CLEAR_ON_START=1）は無効にすることを推奨します。
- OpenAI を用いる処理は API 利用料が発生します。バッチサイズや記事数制限のパラメータを調整してコスト管理してください。
- 監視は定期的に dashboard / risk_logs に書き込みます。監視 DB のバックアップやディスク容量監視を忘れないでください。

サポート／拡張
--------------
- 新しい通知チャネル（Slack / PagerDuty 等）やブローカ実装を追加する場合は、既存の BrokerClientFactory / AlertManager の実装パターンに従って拡張してください。
- DuckDB / SQLite のスキーマ変更は monitoring_db.init_monitoring_db のマイグレーション方針を参考にしてください。

以上。README に記載のない実装の詳細は各モジュール（src/kabusys/ 以下）の docstring を参照してください。