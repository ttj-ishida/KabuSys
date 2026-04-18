KabuSys — 日本株自動売買システム
=================================

このリポジトリは日本株向けの自動売買システム群（実行エンジン、監視、ポートフォリオ構築、リサーチ、AI補助など）をまとめたものです。モジュールはできるだけ純粋関数／疎結合に設計されており、ローカル開発からペーパートレード、本番運用まで対応する構成になっています。

主なポイント
- 環境ごとに動作モードを切り替え（KABUSYS_ENV = development / paper_trading / live）
- ExecutionEngine（発注ロジック）は paper_trading 時にモックブローカーを使用して本番 DB と分離
- Monitoring は独立した監視プロセスで稼働し、SQLite に監視ログを保存
- DuckDB を分析・リサーチ用データベースとして利用
- OpenAI を使ったニュースセンチメント（ニュースNLP）やレジーム判定の実装あり（APIキーが必要）
- .env を対話式に作成するウィザードと設定検証ツールあり

機能一覧
- 実行（Execution）
  - ExecutionEngine 起動スクリプト: run_execution.py
  - 発注管理・オーダーリポジトリ・リスク管理（RiskManager）など（execution パッケージ）
  - paper_trading モードでは MockBrokerClient を使用し data/paper_trading.db に記録
- 監視（Monitoring）
  - run_monitoring.py によるポーリング監視ループ
  - SystemMonitor: CPU/メモリ/ディスク・データ鮮度・プロセス生存確認
  - TradeMonitor / RiskMonitor / KillSwitch / MonitoringEngine：監視とアラート、kill.flag 発行
  - 監視ログ永続化（SQLite）: monitoring_db.py
- ポートフォリオ構築（Portfolio）
  - 候補選定、等金額・スコア加重の重み計算、ポジションサイズ計算、セクターキャップ、レジーム乗数
- リサーチ（Research）
  - DuckDB を用いたファクター計算（momentum / value / volatility）や特徴量解析（IC 計算など）
- AI（News NLP / Regime）
  - news_nlp: OpenAI を使ったニュース毎の銘柄センチメント付与（ai_scores テーブル）
  - regime_detector: ETF・ニュースを合成した日次レジーム判定（market_regime テーブル）
- ツール
  - config_setup.py: .env を対話式に作成
  - validate_config.py: .env と config/*.yaml の事前チェック
  - tools/paper_verification_report.py: ペーパートレード検証レポート生成
- ユーティリティ
  - ログ設定（ログローテート対応）：kabusys.utils.logging_setup
  - プロセス優先度設定：kabusys.utils.process_priority

セットアップ手順（開発環境）
- 推奨: 仮想環境を作成して依存をインストールしてください。
  - Python 3.10+ を想定
  - 例:
    - python -m venv .venv
    - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
    - pip install --upgrade pip
    - pip install duckdb psutil openai
    - （YAML 検証を使いたい場合）pip install pyyaml

Environment（必須/主要）
- 必須（runtime に必要）:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 推奨 / 任意:
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
  - LOG_LEVEL（デフォルト: INFO）
  - OPENAI_API_KEY（ニュースNLP / レジーム判定で必要）
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（アラート通知、任意）
- 監視用（特に利用するもの）
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（"1" = クリア、デフォルト "0"）

.env の作成
- 対話式ウィザードで .env を簡単に作成できます。
  - python -m kabusys.config_setup
- 生成した .env を編集して各種トークンやパスを設定してください。
- .env は Git にコミットしないでください（機密情報を含むため）。

設定検証
- .env と config/*.yaml の存在・簡易チェックを行えます。
  - python -m kabusys.validate_config
  - 警告も失敗扱いにする: python -m kabusys.validate_config --strict

実行方法（主なコマンド）
- ExecutionEngine（発注エンジン）起動
  - python -m kabusys.run_execution
  - 動作モードは KABUSYS_ENV に依存します。paper_trading の場合は MockBrokerClient を使用し paper_trading 用 DB に記録します。
  - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
  - 実行中は data/execution.pid に PID を書き込みます（停止時に削除）。
- Monitoring（監視プロセス）起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL でポーリング間隔を調整できます（秒、デフォルト 60）。
  - 監視は Settings.sqlite_path（本番 sqlite_path）を使用して監視ログを永続化します（KABUSYS_ENV に関わらず）。
  - 停止は data/stop_requested.flag を作成することで行えます（監視プロセスが検知して終了）。
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
  - デフォルト DB は data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で上書き可能）
- AI / レジーム関連（ライブラリ関数）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらを CLI から直接呼ぶスクリプトは含まれていませんが、DuckDB 接続を渡して実行できます。

ログ・ファイル
- ログディレクトリ（デフォルト）: logs/
  - 実行時に logs/<app_name>.log が日次ローテーションで出力されます（30 日分保持）
  - ログディレクトリの作成に失敗した場合、コンソール（stdout）のみで出力されます
- データディレクトリ（デフォルト）: data/
  - data/kabusys.duckdb（DuckDB）
  - data/monitoring.db（監視 SQLite DB）
  - data/paper_trading.db（ペーパートレード用 SQLite DB）
  - data/kill.flag（KillSwitch が書き込む停止フラグ）
  - data/stop_requested.flag（手動停止要求フラグ、run_* スクリプトが監視）
  - data/execution.pid（ExecutionEngine の PID ファイル）

重要な設計や挙動（運用上の注意）
- run_monitoring は監視を行うプロセスで、監視ログ（system_status 等）を SQLite に保存します。MONITOR_POLL_INTERVAL で間隔を変更可能です。
- run_execution は ExecutionEngine を別スレッドで起動します。paper_trading モードでは本番 DB と完全分離された PAPER_TRADING_SQLITE_PATH を使います。
- KillSwitch（kabusys.monitoring.kill_switch）はリスク条件（ドローダウン、ポジション上限など）で data/kill.flag を書き、ExecutionEngine 側で検出して停止できます。
- OpenAI を利用するモジュール（news_nlp / regime_detector）は API の失敗に対してフェイルセーフ（スコア 0.0 など）で動作し、リトライやバックオフ実装がありますが、実行には OPENAI_API_KEY が必要です。
- process_priority 設定は set_process_priority("high") 等で起動直後に行われますが、権限不足で失敗する場合があります（ログに警告が出ます）。

ディレクトリ構成（主要ファイル抜粋）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定読み込みロジック（自動 .env ロード含む）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度・CPU affinity 設定ユーティリティ
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（テーブル作成・CRUD）
    - system_monitor.py      — システム状態・データ鮮度監視
    - risk_monitor.py        — ドローダウン / ポジション上限監視
    - kill_switch.py         — kill.flag の書き込み管理
    - monitoring_engine.py   — 各 Monitor を束ねるエンジン
    - (trade_monitor etc.)
  - execution/               — 発注エンジン関連（OrderManager, Repository, RiskManager, Engine など）
  - portfolio/               — ポートフォリオ構築ロジック（選定 / 重み / サイズ / リスク制御）
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/                — DuckDB を使ったファクター計算・特徴量探索
  - ai/
    - news_nlp.py            — ニュースセンチメント（OpenAI）
    - regime_detector.py     — レジーム判定（ETF MA + マクロセンチメント）
  - tools/
    - paper_verification_report.py

トラブルシューティング（よくある項目）
- .env が正しく読み込まれない
  - プロジェクトルートに .env または .env.local を配置してください。
  - 自動ロードを無効化している場合（KABUSYS_DISABLE_AUTO_ENV_LOAD）には手動で環境変数を設定してください。
- ログファイルが作れない
  - logs/ ディレクトリの書き込み権限を確認してください。書き込みできない場合はコンソール出力のみになります。
- OpenAI 呼び出しでエラーが出る
  - OPENAI_API_KEY を正しくセットしてください。ネットワーク・API 利用制限（429）により一時失敗する場合はログにリトライ情報が出ます。
- Execution/Monitoring を停止したい
  - data/stop_requested.flag を作成すると run_execution/run_monitoring が検知して終了します（run_execution では実行スレッド停止を試みます）。
  - KillSwitch は特定のリスク条件で data/kill.flag を書き込み、ExecutionEngine 側が検知して停止します。

開発者向けメモ
- 多くのモジュールは外部 DB 接続（sqlite3 / duckdb）を引数として受け取り純粋に動作するため、ユニットテストが書きやすく設計されています。
- monitoring_db.init_monitoring_db() は冪等でテーブル・インデックスを作成し、既存 DB のマイグレーション（列追加）も行います。
- ロギング設定は一貫して kabusys.utils.logging_setup.setup_logging() を呼ぶことで統一されます。

最後に
- まずは python -m kabusys.config_setup で .env を作成 → python -m kabusys.validate_config で検証 → python -m kabusys.run_monitoring / python -m kabusys.run_execution を順に試すのを推奨します。
- 追加の設定や詳細はコード内の docstring やコメントに記載されています。必要な場合はそちらも参照してください。

もし README に含めてほしい追加のコマンド例や .env のサンプル、運用フロー（デプロイ / systemd 単位の起動例など）があれば教えてください。必要に応じて追記します。