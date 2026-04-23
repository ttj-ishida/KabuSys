# KabuSys

日本株自動売買システムのライブラリ／スクリプト群です。ポートフォリオ構築、発注エンジン、監視、リサーチ（DuckDB ベース）、および AI（OpenAI）を用いたニュースセンチメント / レジーム判定などの機能を含みます。

## 主な概要
- コアは Python モジュール群（src/kabusys）として実装。
- 本番（live）・ペーパートレード（paper_trading）・開発（development）を切り替え可能。
- 監視（Monitoring）と発注（Execution）は別プロセスで起動。監視は Execution の停止シグナル（kill.flag）生成やアラートを担います。
- データ永続化は DuckDB（分析用）と SQLite（監視 / 発注ログ）を使用。ペーパートレードは専用の SQLite を使い本番 DB と分離。

---

## 機能一覧
- 設定管理
  - .env の自動読み込み / 手動ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
- 実行エンジン
  - run_execution: ExecutionEngine 起動スクリプト（本番 / ペーパートレード対応）
  - BrokerClientFactory によりペーパートレード時は MockBrokerClient を使用し、別 DB に記録
- 監視
  - run_monitoring: SystemMonitor ポーリングループ起動（MONITOR_POLL_INTERVAL で間隔変更可）
  - MonitoringEngine：SystemMonitor / TradeMonitor / RiskMonitor を束ねてポーリング・アラート発行
  - KillSwitch：ドローダウン等の条件で data/kill.flag を書き込んで Execution を停止
- ポートフォリオ構築（純粋関数）
  - 候補選定、等金額・スコア重み、セクター制限、レジーム乗数、ポジションサイズ計算等
- リサーチ
  - DuckDB を用いたファクター計算（momentum/value/volatility）、forward returns、IC 計算 等
- AI（OpenAI）
  - news_nlp: ニュース記事を LLM でセンチメント評価して ai_scores に書き込み
  - regime_detector: ETF MA とマクロニュースを合成して市場レジーム判定
- ユーティリティ
  - ロギング設定（TimedRotatingFileHandler など）
  - プロセス優先度 / CPU affinity 設定ユーティリティ
- ツール
  - paper_verification_report: ペーパートレード DB から検証レポートを生成（稼働率・成功率・レイテンシなど）

---

## セットアップ手順（ローカル開発向け）
1. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - 必須（コードから想定）:
     - duckdb
     - psutil
     - openai
   - オプション（config.yaml の検証など）:
     - PyYAML
   - 例:
     - pip install duckdb psutil openai PyYAML

   ※ 実際の requirements.txt が存在する場合はそれを使用してください。

3. プロジェクトルートに移動し、.env を作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - もしくは .env.example を参考に手動で .env を作成してください。

4. 設定検証
   - python -m kabusys.validate_config
   - --strict をつけると警告も失敗扱いになります。

---

## 環境変数（主要）
- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 重要 / よく使う
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
  - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
  - SQLITE_PATH — 監視 DB（monitoring.db）デフォルト: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（data/paper_trading.db）
  - PAPER_FILL_MODE — ペーパートレードの約定振る舞い（instant | partial | never | reject）デフォルト: instant
  - LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - OPENAI_API_KEY — OpenAI API キー（AI モジュールで使用）
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）。デフォルト 60
  - KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag をクリアするか（0/1）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知用（任意）

---

## 使い方（主要コマンド）
- 環境セットアップ（.env 生成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動（Execution）
  - python -m kabusys.run_execution
  - 備考:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db にロギングします（本番 DB と分離）。
    - プロセス優先度を高に設定し、data/stop_requested.flag を監視して安全に停止します。

- 監視プロセス起動（Monitoring）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（例: export MONITOR_POLL_INTERVAL=30）。
  - Monitoring は KABUSYS_ENV にかかわらず本番の sqlite_path を使用します（監視ログを一元管理するため）。

- 停止・強制停止
  - Execution 側の停止要求:
    - data/stop_requested.flag を書き込むと run_execution / run_monitoring が検知して終了します（両スクリプトは同名ファイルを参照）。
  - KillSwitch（自動）:
    - RiskMonitor 等の判定で data/kill.flag が書き込まれると Execution 停止トリガーになります。
  - 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動でクリアされます（本番では注意）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで DB パスを直接指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）。

- AI 関連（プログラム API）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - どちらも api_key 引数を渡すか環境変数 OPENAI_API_KEY を設定してください。

---

## 主要な挙動メモ
- run_monitoring:
  - MONITOR_POLL_INTERVAL（秒）で loop。デフォルト 60 秒。
  - 監視ループは data/stop_requested.flag を検知して終了。
  - Monitoring は常に Settings.sqlite_path（本番用）を使う点に注意。

- run_execution:
  - KABUSYS_ENV=paper_trading の場合は paper_sqlite_path（デフォルト data/paper_trading.db）を使用。
  - BrokerClientFactory により本番/ペーパーモードでブローカークライアントが選択される。
  - ExecutionEngine は別スレッドで実行され、stop flag を検知すると安全に停止する。

- DB 初期化:
  - init_monitoring_db() は冪等で必要なテーブル（system_status / trade_logs / positions / risk_logs / dashboard）を作成する。既存スキーマに対する簡易マイグレーションも行う。

- ロギング:
  - kabusys.utils.logging_setup.setup_logging を使用して stdout と日次ローテーションファイル（logs/<app_name>.log）に出力します。
  - LOG_DIR / LOG_LEVEL 環境変数で挙動を調整可能。

---

## ディレクトリ構成（主要ファイル・概要）
リポジトリの src/kabusys 以下の主要モジュールと役割です（抜粋）。

- kabusys/
  - __init__.py — パッケージ定義
  - config.py — 環境変数 / Settings 管理（自動 .env ロード、必須設定チェック等）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI

- run スクリプト
  - run_execution.py — ExecutionEngine 起動用スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動用スクリプト

- execution/ (発注エンジン関連)
  - broker_factory.py, execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py
  - （発注ロジック・リスク管理・注文管理を含む。詳細は各ファイル参照）

- monitoring/
  - monitoring_db.py — SQLite を用いた監視ログの永続化層
  - system_monitor.py — システム状態・データ鮮度監視
  - trade_monitor.py — 発注／約定の監視（stale orders 等）
  - risk_monitor.py — ドローダウン・ポジション数上限監視
  - kill_switch.py — kill.flag 書き込みユーティリティ
  - monitoring_engine.py — 各 Monitor を束ねる

- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 株数（lot）計算、リスク制限、スケーリング
  - risk_adjustment.py — セクターキャップ・レジーム乗数

- research/
  - factor_research.py — Momentum / Value / Volatility 等のファクター計算（DuckDB）
  - feature_exploration.py — forward returns / IC / 統計サマリー

- ai/
  - news_nlp.py — ニュースを LLM で評価して ai_scores に書込む
  - regime_detector.py — ETF MA とマクロニュースを合成して market_regime を算出

- utils/
  - logging_setup.py — ログ設定ユーティリティ
  - process_priority.py — プロセス優先度 / CPU affinity 設定

- tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成スクリプト

---

## よくある運用注意
- 本番環境（KABUSYS_ENV=live）ではデフォルトの kill flag 自動クリア設定（KILL_FLAG_CLEAR_ON_START）を有効にしないことを推奨します。
- OpenAI API を使用するモジュールを利用する場合は必ず OPENAI_API_KEY を安全に設定してください（.env に格納する場合は Git にコミットしないこと）。
- ペーパートレードは本番 DB と分離されていますが、duckdb 上の分析テーブル等は共有する設計の可能性があるため運用設計を慎重に行ってください。
- run_monitoring は監視 DB（SQLITE_PATH）を参照してレポート / kill.flag の発行を行います。監視 DB のパス設定に注意してください。

---

## サポート・拡張ポイント
- BrokerClient 実装を追加すれば別ブローカーへの対応が可能です。
- position sizing の lot_size を銘柄別にするなどの拡張が設計上想定されています（コメント参照）。
- news_nlp / regime_detector の LLM 呼び出しはリトライや JSON バリデーション等を含む堅牢実装ですが、プロンプトやバッチサイズの調整は運用に応じて行ってください。

---

README に不足している項目（例えば requirements.txt、実行時の systemd / container 化手順、CI 設定等）や、各モジュールの詳細ドキュメント生成が必要であれば指示してください。必要に応じてサンプル .env テンプレートも作成します。