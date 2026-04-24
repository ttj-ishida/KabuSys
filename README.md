KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤の一部です。  
本リポジトリには、以下の主要機能が含まれます。

- 実行エンジン（ExecutionEngine）: 発注ロジック・リスク管理・発注管理の起動
- 監視コンポーネント（Monitoring）: システム状態／注文／リスクの定常監視と Kill Switch
- ポートフォリオ構築ユーティリティ: 候補選定・重み付け・ポジションサイズ計算・セクター制限
- リサーチ機能: ファクター計算・特徴量解析（DuckDB を使用）
- AI 補助: ニュース NLP（OpenAI）によるセンチメント評価、レジーム判定
- ツール: ペーパートレードの検証レポート生成など
- 設定ユーティリティ: 対話式 .env ウィザード、設定検証 CLI

主な特徴
--------
- 環境分離: KABUSYS_ENV により development / paper_trading / live を切替可能。paper_trading 時は発注をモックして専用 DB（data/paper_trading.db）に記録。
- 設定自動読込: プロジェクトルートの .env/.env.local を読み込み（必要に応じて自動無効化可能）。
- ロギング: stdout + 日次ローテートファイル（logs/<app>.log）。
- DuckDB を利用した高速な時系列・ファクター計算。
- OpenAI（gpt-4o-mini）を使ったニュースセンチメント・レジーム判定（環境変数 OPENAI_API_KEY 必須）。
- 監視機構と Kill Switch により重大リスク時に ExecutionEngine を停止可能。

セットアップ手順
----------------

前提
- Python 3.9+（typing の一部機能が利用されています）
- 必要なパッケージ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（設定検証で利用。未インストール時は YAML 検証をスキップ）
  - （その他、アプリで使用するブローカーライブラリ等）

例（pip）
- 仮想環境作成・有効化後:
  - pip install -r requirements.txt
  - requirements.txt がない場合は上記パッケージを個別にインストールしてください。

初期設定
1. プロジェクトルートに移動（.git または pyproject.toml がある場所が自動検出の基準）。
2. 対話式ウィザードで .env を作成:
   - python -m kabusys.config_setup
   - または手動で .env を作成（.env.example を参照してください）。
3. 設定検証:
   - python -m kabusys.validate_config
   - 警告もエラーとして扱う場合は --strict を付ける（例: python -m kabusys.validate_config --strict）

主要環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 DB（デフォルト: data/paper_trading.db）
- LOG_LEVEL — DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）
- OPENAI_API_KEY — News NLP / Regime Detector を利用する場合必須
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト: 60）
- KILL_FLAG_CLEAR_ON_START — 本番 env での Kill Flag 自動クリア（推奨は 0）

ログ・プロセス制御
- ログ: デフォルト logs/ ディレクトリにアプリごとのログ (例: logs/execution.log, logs/monitoring.log) を出力
- PID ファイル: data/execution.pid（ExecutionEngine の PID）
- Kill フラグ: data/kill.flag（KillSwitch 用）。存在すると ExecutionEngine を停止するトリガ
- Stop フラグ（開発用）: data/stop_requested.flag（run_monitoring/run_execution の停止トリガ）

使い方
------

起動スクリプト（主なもの）
- 監視ループ起動:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で上書き可能（例: export MONITOR_POLL_INTERVAL=30）
  - 監視プロセスは Settings.sqlite_path（デフォルト data/monitoring.db）に接続してログを保存します（monitoring は環境にかかわらず本番 sqlite_path を使用）。
- 実行エンジン起動:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH に記録（本番 DB と分離）。
  - 起動前に data/stop_requested.flag が存在すると起動をスキップします。
- 設定ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config [--strict]

ツール
- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - 環境変数 PAPER_TRADING_SQLITE_PATH でも DB を指定可能。デフォルト data/paper_trading.db。

AI 関連
- ニュース NLP（ai.score_news）:
  - DuckDB 接続と target_date を与えることで raw_news を集計して ai_scores テーブルに書き込みます。
  - OpenAI API キーが必要（OPENAI_API_KEY）。
- レジーム判定（ai.regime_detector.score_regime）:
  - ETF（1321）の MA200 乖離とマクロニュースセンチメントを合成して market_regime テーブルへ書き込みます。
  - OpenAI API キーが必要（OPENAI_API_KEY）。

監視（Monitoring）・Kill Switch の動作概略
- SystemMonitor: CPU/Memory/Disk/プロセス生存確認・株価データ鮮度チェックを実施し system_status に記録
- TradeMonitor: trade_logs を解析して滞留注文・約定異常等を検出（ソースに詳細ロジックあり）
- RiskMonitor: ダッシュボード（portfolio_value 等）を参照してドローダウン・ポジション上限を判定
- KillSwitch: RiskMonitor 等の結果に基づいて data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送る
- MonitoringEngine: 上記監視をまとめて一定間隔で実行し、AlertManager に通知（AlertManager は外部実装を想定）

ディレクトリ構成（抜粋）
----------------------

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings クラス（デフォルト値と検証）
  - config_setup.py
    - 対話式 .env ウィザード（python -m kabusys.config_setup）
  - validate_config.py
    - 起動前設定検証 CLI（python -m kabusys.validate_config）
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプト（paper_trading 用分離対応）
  - ai/
    - __init__.py
    - news_nlp.py
      - raw_news を LLM（OpenAI）に渡して銘柄別センチメントを ai_scores に書き込む
    - regime_detector.py
      - 市場レジーム（bull/neutral/bear）判定と DB 書き込み
  - monitoring/
    - monitoring_db.py
      - monitoring 用 SQLite テーブル定義と MonitoringDB ラッパ
    - system_monitor.py
      - システム状態・データ鮮度監視
    - trade_monitor.py (コードベースに含まれる想定ファイル)
    - risk_monitor.py
      - ドローダウン・ポジション上限監視
    - kill_switch.py
      - data/kill.flag 操作ユーティリティ
    - monitoring_engine.py
      - 各 Monitor を束ねる実行ループ
    - alert_manager.py (実装想定: アラート送信の抽象化)
  - execution/
    - execution_engine.py (起動・セッション実行)
    - broker_factory.py (ブローカークライアント生成)
    - order_manager.py / order_repository.py / reconciler.py / risk_manager.py
  - portfolio/
    - portfolio_builder.py
      - 候補選定・重み付け（等重み / スコア加重）
    - position_sizing.py
      - 株数決定・リスクフォールバック・単元丸め
    - risk_adjustment.py
      - セクター上限・レジーム乗数
  - research/
    - factor_research.py
      - Momentum / Volatility / Value 等のファクター計算（DuckDB）
    - feature_exploration.py
      - 将来リターン計算、IC、統計サマリー
  - tools/
    - paper_verification_report.py
      - ペーパートレードの Pass/Fail 検証レポート生成
  - utils/
    - logging_setup.py
      - 一貫したログ設定ユーティリティ（stdout + 日次ローテート）
    - process_priority.py
      - プロセス優先度 / CPU affinity の設定（Windows / POSIX 対応）
  - data/ (ランタイムで使用することを想定するディレクトリ。DB・フラグファイル等)
    - kill.flag (KillSwitch 用)
    - stop_requested.flag (run_* スクリプトの停止トリガ)
    - execution.pid

注意事項 / 運用上のヒント
-----------------------
- 本番（KABUSYS_ENV=live）では特に LINE 通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）や KILL_FLAG_CLEAR_ON_START の設定を慎重に行ってください。validate_config に live 向けの注意喚起があります。
- .env は決して VCS にコミットしないでください（config_setup.py のヘッダにも注意書きあり）。
- OpenAI API 利用はコスト・レイテンシに注意。news_nlp と regime_detector はリトライ・バックオフを組み込んでいますが、API キーと利用ポリシーの管理を行ってください。
- DuckDB/SQLite ファイルのバックアップとサイズ管理を検討してください（ログ増大によりファイル肥大化の可能性あり）。
- ログディレクトリ作成に失敗した場合はコンソール出力のみになります（logging_setup がフォールバック）。

開発・拡張
-----------
- 新しい監視 / リスクルールは monitoring/ 内で追加できます（RiskMonitor / KillSwitch を活用）。
- ExecutionEngine および BrokerClientFactory を拡張すれば任意の取引先に接続できます（テスト用に MockBrokerClient の仕組みあり）。
- research モジュールは DuckDB に価格・財務データをロードすればオフライン解析に利用可能です。

ライセンス / バージョン
-----------------------
- パッケージバージョンは src/kabusys/__init__.py の __version__ を参照してください（現時点: 0.1.0）。

---
必要であれば、README に含める具体的なコマンド例（systemd 用ユニットファイル例・Dockerfile 例・requirements.txt の推奨リスト）を追加します。どの形式の追加情報が欲しいか教えてください。