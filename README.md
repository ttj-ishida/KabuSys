KabuSys — 日本株自動売買システム
================================

このリポジトリは、シンプルで実務寄りな日本株自動売買システムのコア部分をまとめたものです。
モジュールは発注エンジン（Execution）、監視（Monitoring）、ポートフォリオ構築、研究（Research）、AI 補助（ニュース NLP / レジーム判定）などに分かれています。

主な目的
- 自動発注エンジンの実行・管理
- システム稼働監視とアラート/Kill Switch
- ペーパートレード用の分離された検証環境
- DuckDB を使った因子計算／研究用処理
- OpenAI を使ったニュースセンチメント評価（任意）

機能一覧
- Execution（発注エンジン）
  - 設定に応じて実際のブローカーまたはモックを使用（KABUSYS_ENV=paper_trading でモック）
  - 注文管理、リスク管理、整合性チェック（Reconciler）を内蔵
  - Paper Trading は data/paper_trading.db（デフォルト）に記録し本番 DB と分離
- Monitoring（監視）
  - システム CPU / メモリ / ディスク使用率監視
  - 発注ログ（trade_logs）やポジション（positions）などの永続化
  - ドローダウン監視・ポジション上限チェック・Kill Switch (data/kill.flag)
  - monitoring ポーリングループ実行スクリプト（MONITOR_POLL_INTERVAL 環境変数で変更可）
- Research（研究/因子）
  - モメンタム／ボラティリティ／バリュー等のファクター計算（DuckDB 経由）
  - 将来リターン計算、IC（Information Coefficient）や統計要約
- Portfolio（ポートフォリオ構築）
  - 候補選定、重み付け（等金額／スコア加重）、個別銘柄の枚数算出（単元丸め）
  - セクター上限適用、レジーム乗数
- AI（任意）
  - ニュースを OpenAI に送り銘柄別センチメントを ai_scores に保存（gpt-4o-mini を想定）
  - マクロニュース + ETF MA200 乖離から日次の市場レジーム判定
- ツール
  - 設定ウィザード（.env 生成）: python -m kabusys.config_setup
  - 設定検証 CLI: python -m kabusys.validate_config
  - Paper Trading 検証レポート生成スクリプト

必要条件（概略）
- Python 3.9+
- SQLite（標準ライブラリで OK）
- 必要な Python ライブラリ（代表例）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（設定検証 で YAML 検証を有効にする場合）
- インターネット接続（OpenAI を使う場合）、および kabuステーション API に接続する場合は当該 API が稼働していること

セットアップ手順（ローカル）
1. リポジトリをクローン
   - git clone <repository-url>
   - cd <project-root>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  # Windows: .venv\Scripts\activate

3. 依存パッケージをインストール
   - pip install duckdb psutil
   - AI 機能を使う場合: pip install openai
   - 設定検証で YAML を使う場合: pip install PyYAML

   （requirements.txt がある場合は pip install -r requirements.txt を使用してください）

4. .env の作成（対話式ウィザード）
   - python -m kabusys.config_setup
   - ウィザードが .env を作成します（デフォルトはプロジェクトルートの .env）。
   - 主要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
     - OPENAI_API_KEY（AI 機能を使う場合）
   - デフォルト DB パス:
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用）

5. 設定検証（起動前の推奨ステップ）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗（exit code 1）扱いになります。

使い方（主なコマンド）
- 監視ループの起動
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒数で指定（デフォルト 60 秒）
  - python -m kabusys.run_monitoring
  - 監視は常に Settings.sqlite_path（デフォルト data/monitoring.db）を使用します（環境に依らず本番 DB を想定）

- Execution（発注エンジン）の起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します
  - 起動時に data/stop_requested.flag が存在すると起動せず終了します
  - 実行中に data/stop_requested.flag を作るとエンジンは停止します（監視側からの停止要求に使用）

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で別 DB パスを指定可能。環境変数 PAPER_TRADING_SQLITE_PATH でも指定可。

- AI 関連（プログラム経由）
  - kabusys.ai.score_news(conn, target_date, api_key=None)  # OpenAI API キーは引数または OPENAI_API_KEY 環境変数
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

ログ・DB・フラグ
- ログ
  - ログはデフォルトで logs/<app_name>.log（日次ローテーション、30日保持）とコンソールに出力されます。
  - app_name は run スクリプト内で指定（例: "monitoring", "execution"）。

- DB
  - DuckDB: data/kabusys.duckdb（設定で上書き可）
  - SQLite (monitoring): data/monitoring.db（監視用）
  - SQLite (paper trading): data/paper_trading.db（paper_trading 時に分離）

- 停止フラグ / Kill Switch
  - data/stop_requested.flag
    - run_execution/run_monitoring のループを外部から終了させるために使用。作成すると各ループが検出して終了します。
  - data/kill.flag
    - KillSwitch（リスク監視）によって書き込まれると ExecutionEngine に対する停止指示となります。kill.flag の存在は危険を意味します。
  - 起動時のクリア設定
    - KILL_FLAG_CLEAR_ON_START 環境変数が "1" の場合、Execution 起動時に kill.flag を自動でクリアします（本番では 0 を推奨）。

主要モジュール（概略）
- kabusys.config
  - Settings クラス: 環境変数 / .env の読み取りと検証
  - 自動的にプロジェクトルートの .env / .env.local をロード（無効化可）

- kabusys.run_monitoring
  - SystemMonitor のポーリングループ起動スクリプト
  - MONITOR_POLL_INTERVAL で間隔を調整

- kabusys.run_execution
  - ExecutionEngine の起動スクリプト
  - KABUSYS_ENV により paper_trading モードを切替

- kabusys.monitoring
  - monitoring_db: SQLite テーブル定義 & 永続化レイヤ
  - system_monitor / trade_monitor / risk_monitor: 監視ロジック
  - monitoring_engine: モニタ群を束ねる実行エンジン
  - kill_switch / alert_manager: 自動停止・通知管理

- kabusys.execution
  - ExecutionEngine、OrderManager、RiskManager、BrokerClientFactory（実ブローカ or Mock切替） 等（詳細はコード参照）

- kabusys.portfolio
  - 銘柄選定 / 重み計算 / 位置サイズ算出 / リスク適用などの純粋関数

- kabusys.research
  - ファクター計算（momentum/volatility/value）や特徴量探索ユーティリティ

- kabusys.ai
  - news_nlp: ニュースを LLM に送り銘柄別スコアを生成
  - regime_detector: ETF MA200 とマクロニュースで日次レジーム判定

- kabusys.utils
  - logging_setup: ログ初期化ユーティリティ
  - process_priority: プロセス優先度 / CPU affinity 設定ユーティリティ

ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py
  - config.py
  - config_setup.py
  - validate_config.py
  - run_execution.py
  - run_monitoring.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - execution/         # 発注エンジン関連（OrderManager 等）
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - tools/
    - paper_verification_report.py

よくある運用上の注意
- .env は絶対に Git にコミットしないでください（config_setup でも明記されています）。
- 本番環境では KABUSYS_ENV=live、KILL_FLAG_CLEAR_ON_START=0 を推奨します。
- OpenAI を利用する際はレート制限・課金に注意してください。AI モジュールは失敗をフェイルセーフで扱う設計ですが、API キー管理は慎重に行ってください。
- monitoring は本番 sqlite_path を参照します。誤って本番 DB を上書きしないように環境・パスを確認してください。
- process_priority が OS により動作しない場合があります（権限不足など）。ログの警告を確認してください。

開発メモ（参考）
- .env の自動ロードは Settings モジュール内で .git / pyproject.toml を検出して行われます。テスト等で自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB のクエリは大量データを前提に SQL で計算する設計です。分析用途では DuckDB を積極的に利用してください。

フィードバック / 変更
- README ではカバーしきれない細部は各モジュールの docstring を参照してください。特に AI 周り・リスク制御の細かい挙動はコード内コメントを優先してください。

以上で README の概要となります。必要であれば「インストール用の requirements.txt を作る」「起動用 systemd / Supervisor のサンプル」「より詳しい運用手順（デプロイ・バックアップ）」などの追補版を用意します。どれを優先しますか？