# KabuSys

日本株向けの自動売買システム用ユーティリティ群とライブラリ群のコア部分です。  
このリポジトリはトレード実行エンジン、監視（Monitoring）、ポートフォリオ構築、リサーチ（ファクター計算）、
および AI を使ったニュース解析などの共通機能を含みます。

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（コマンド例）
- 環境変数（主なもの）
- 停止・Kill スイッチの扱い
- ディレクトリ構成（主要ファイルの説明）

---

プロジェクト概要
- 自動売買の実行エンジン（ExecutionEngine）とそれを監視する Monitoring コンポーネント群を提供します。
- ペーパートレード（モックブローカー）を使った分離テストが可能です（KABUSYS_ENV=paper_trading）。
- DuckDB / SQLite をデータ基盤としてファクター計算、ニューススコアリング、レジーム判定、監視ログを扱います。
- OpenAI API を用いたニュースの NLP スコアリング、マクロセンチメント評価機能を持ちます（オプション）。

主な機能一覧
- Execution エントリ:
  - run_execution.py: ExecutionEngine を起動（paper_trading 時は MockBroker を使用し、専用 DB を利用）
- Monitoring エントリ:
  - run_monitoring.py: SystemMonitor をポーリングして system_status / trade_logs / risk_logs / dashboard を更新
  - MonitoringEngine: SystemMonitor / TradeMonitor / RiskMonitor をまとめて定期実行し、アラートと KillSwitch を評価
- 設定管理:
  - config_setup.py: 対話式ウィザードで .env を生成／更新
  - validate_config.py: 起動前に .env および config/*.yaml の妥当性チェック
- ポートフォリオ構築:
  - portfolio/*: 候補選定、重み計算、セクター制約、ポジションサイズ決定
- リサーチ:
  - research/*: ファクター計算（momentum/value/volatility）、特徴量探索、IC 計算など（DuckDB を使用）
- AI:
  - ai/news_nlp.py: ニュース記事のセンチメントを OpenAI で評価して ai_scores に格納
  - ai/regime_detector.py: ETF とマクロニュースを合成して市場レジームを判定
- ツール:
  - tools/paper_verification_report.py: ペーパートレード DB を集計して検証レポートを生成
- ユーティリティ:
  - utils/logging_setup.py: 統一的なログ設定（コンソール + 日次ローテートファイル）
  - utils/process_priority.py: プロセス優先度 / CPU affinity 設定（Windows / POSIX を吸収）
- 永続化（監視用）:
  - monitoring/monitoring_db.py: SQLite ベースの監視ログテーブル定義と読み書きユーティリティ

---

セットアップ手順（開発用手順の例）
1. Python と仮想環境
   - 推奨: Python 3.10 以上（ソースで `X | Y` 型注釈を使用）
   - 仮想環境作成:
     - python -m venv .venv
     - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージのインストール（例）
   - pip install duckdb psutil openai
   - PyYAML は validate_config の YAML 検証で任意: pip install PyYAML

   ※ requirements.txt は本リポジトリに付属していないため、実際のプロジェクトでは requirements を用意してください。

3. プロジェクトルートに移動して初期 .env を作成
   - python -m kabusys.config_setup
   - 対話ウィザードが .env を生成します（.env は絶対にコミットしないでください）

4. 設定検証
   - python -m kabusys.validate_config
   - 問題があれば指摘が表示されます。--strict を付けると警告も失敗扱いになります。

5. データディレクトリ・ログディレクトリ
   - デフォルトで以下のパスを使用します（必要なら .env で上書き）
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db
     - ログ: logs/
     - stop フラグなど: data/stop_requested.flag, data/kill.flag, data/execution.pid

---

使い方（主要コマンド）
- 環境変数を整えてから実行してください（.env を用意済み前提）。

1) 設定ウィザード
   - python -m kabusys.config_setup

2) 設定検証
   - python -m kabusys.validate_config
   - 失敗時は exit code 1 を返します（--strict で警告も失敗扱い）

3) Monitoring の起動（デフォルト 60 秒ポーリング）
   - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
   - 停止は data/stop_requested.flag を作成するか Ctrl+C

   補足:
   - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書きできます（正の整数）。
   - run_monitoring は環境に関係なく production 用 sqlite_path を使用して監視 DB を更新します。

4) Execution エンジン起動
   - python -m kabusys.run_execution
   - KABUSYS_ENV=paper_trading にすると MockBroker を使い、data/paper_trading.db を使用します。
   - 起動直後に data/stop_requested.flag が存在する場合は起動を中止します。
   - 実行中に stop フラグが作成されるとエンジンを停止します。

5) Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report
   - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
   - DB 指定: --db PATH（環境変数 PAPER_TRADING_SQLITE_PATH でも指定可）

6) AI 系機能（OpenAI）
   - ai.news_nlp.score_news / ai.regime_detector.score_regime を呼び出す際は OPENAI_API_KEY を設定してください。
   - 例: OPENAI_API_KEY=sk-... python -c "from kabusys.ai.news_nlp import score_news; import duckdb, datetime; conn=duckdb.connect('data/kabusys.duckdb'); score_news(conn, datetime.date(2026,4,1))"

---

主な環境変数（要点）
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 実行環境:
  - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
    - paper_trading: MockBroker を使用し paper_trading DB に記録
- データパス:
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
- ログ:
  - LOG_LEVEL (default: INFO)
  - LOG_DIR (default: logs/)
- AI:
  - OPENAI_API_KEY (news_nlp / regime_detector 用)
- その他:
  - MONITOR_POLL_INTERVAL (run_monitoring 用。秒。デフォルト 60)
  - PAPER_FILL_MODE (paper_trading の約定モード: instant | partial | never | reject)
  - KILL_FLAG_CLEAR_ON_START (本番起動時の kill.flag 自動クリアフラグ 0/1)

サンプル .env（最小）
- .env 例（config_setup で生成可能）:
  - JQUANTS_REFRESH_TOKEN=your_token_here
  - KABU_API_PASSWORD=your_kabu_password
  - KABUSYS_ENV=development
  - DUCKDB_PATH=data/kabusys.duckdb
  - SQLITE_PATH=data/monitoring.db
  - LOG_LEVEL=INFO

停止・Kill スイッチについて
- run_monitoring / run_execution はプロセス間でフラグファイルを使った停止制御を行います。
  - data/stop_requested.flag: 監視ループ／実行ループの外部停止フラグ（存在を検知したら安全に終了）
  - KillSwitch（monitoring/kill_switch.py）は内部判定により data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります。
- ExecutionEngine の PID ファイル:
  - data/execution.pid を使用してプロセス管理を行います。

注意事項・運用メモ
- process_priority の変更は OS 権限が必要な場合があります。psutil による設定は失敗しても警告を出してスキップします。
- DuckDB / SQLite のファイル I/O パスは環境に合わせて .env で変更してください。データディレクトリは事前に作成しておくか、アプリが作成する場合があります。
- OpenAI など外部 API の呼び出しは失敗時にフォールバックする実装が多く含まれていますが、API キーやレート制限には注意してください。
- monitor 系は監視データ（system_status, trade_logs, risk_logs, dashboard）を SQLite に永続化します。DB マイグレーション処理（列追加等）も実装済みです。

ディレクトリ構成（主要ファイルの説明）
- src/kabusys/
  - __init__.py: パッケージ定義
  - config.py: 環境変数・設定の読み込みと Settings クラス
  - config_setup.py: .env を対話式に作るウィザード
  - validate_config.py: 設定検証 CLI
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py: ログ設定ユーティリティ
    - process_priority.py: プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py: SQLite テーブル定義 / 永続化ユーティリティ
    - system_monitor.py: CPU/メモリ/Disk/データ鮮度 / プロセス監視
    - trade_monitor.py: （注文ログ監視。コードはリポジトリの他ファイル参照）
    - risk_monitor.py: ドローダウン・ポジション上限監視
    - monitoring_engine.py: 各モニタを束ねるエンジン
    - kill_switch.py: Kill Flag 書き込みロジック
    - alert_manager.py: （アラート集約と通知。監視内で呼び出し）
  - execution/: ExecutionEngine 関連（broker, order_manager, repo 等）
  - portfolio/: 候補選定、重み計算、リスク調整、ポジションサイズ計算
  - research/: ファクター計算、特徴量探索、統計ユーティリティ
  - ai/
    - news_nlp.py: ニュース NLP スコアリング（OpenAI）
    - regime_detector.py: マクロ + ETF 指標によるレジーム判定（OpenAI）
  - tools/
    - paper_verification_report.py: ペーパートレードの集計・合否判定スクリプト

最後に
- この README はソースコードの公開部分から要点を抜粋してまとめた入門向けガイドです。実運用ではログローテーション、バックアップ、監視アラートの受け取り先（LINE など）の設定、API キーのセキュア保管（Vault 等）を必ず整備してください。
- 具体的な ExecutionEngine の動作やブローカ実装・戦略ロジックは execution/ や strategy 設計ドキュメント（別途）を参照してください。