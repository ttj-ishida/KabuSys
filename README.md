# KabuSys — 日本株自動売買システム

本リポジトリは、KabuSys と名付けた日本株向け自動売買・分析プラットフォームの一部です。
主に以下を含みます: 実行エンジン起動スクリプト、監視機構、ポートフォリオ構築ロジック、リサーチ（ファクター計算）、AI を使ったニュースセンチメント／レジーム判定、各種ユーティリティ・ツール。

注意: .env（機密情報）を含めて Git にコミットしないでください。

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（主要コマンド・環境変数）
- ディレクトリ構成（主要ファイル説明）
- 運用上の注意点

---

プロジェクト概要
- KabuSys は日本株の自動売買を想定したモジュール群。
- 実行エンジン（注文送信、リスク管理、オーダー管理）と、監視エンジン（プロセス監視・注文監視・リスク監視）、研究用モジュール（ファクター計算、特徴量解析）、AI モジュール（ニュースの NLP スコアリング／市場レジーム判定）等を含む。
- DuckDB / SQLite をデータベースに使用。OpenAI（gpt-4o-mini）をニュース・マクロセンチメントに利用可能（任意）。

主な機能一覧
- ExecutionEngine 起動（run_execution.py）
  - 本番 / ペーパートレード切替（KABUSYS_ENV）
  - Paper Trading 時は専用 SQLite を使用（data/paper_trading.db デフォルト）
  - リスク管理、order manager、reconciler 組み立て
- Monitoring（run_monitoring.py / monitoring package）
  - system_monitor: CPU/メモリ/DISK、データ鮮度、実行プロセス監視
  - trade_monitor: 注文滞留、約定異常価格の検出
  - risk_monitor: ドローダウン・ポジション上限の監視
  - KillSwitch: 条件で kill.flag を作成しエンジン停止をトリガー
  - MonitoringDB: 監視ログの永続化（SQLite）
- Portfolio（portfolio package）
  - 候補選定、等金額／スコア加重、ポジションサイズ計算、セクター制限、レジーム乗数
- Research（research package）
  - ファクター計算（モメンタム・ボラティリティ・バリュー等）
  - 特徴量探索、IC 計算、統計サマリー
- AI（ai package）
  - news_nlp: 銘柄別ニュースを集約して OpenAI に投げ、センチメントスコアを ai_scores テーブルに書込
  - regime_detector: ETF の MA とマクロニュースで日次の市場レジーム判定
- Tools
  - paper_verification_report: ペーパートレード DB から検証レポート生成（稼働率、注文成功率、P95 レイテンシ等）
- ユーティリティ
  - config_setup.py: .env 対話式ウィザード
  - validate_config.py: 起動前の設定検証 CLI
  - process_priority: プラットフォームに依存しないプロセス優先度 / CPU affinity 設定

---

セットアップ手順（開発向け）
1. リポジトリをクローン
   - git clone <repo-url>
2. Python 仮想環境の作成と有効化（推奨）
   - python -m venv .venv
   - Unix/macOS: source .venv/bin/activate
   - Windows: .venv\Scripts\activate
3. 必要パッケージをインストール
   - 必要な主要ライブラリ:
     - duckdb
     - psutil
     - openai（AI 機能を使う場合）
     - PyYAML（validate_config の YAML 検証を行う場合）
   - 例:
     - pip install duckdb psutil openai PyYAML
   - （プロジェクトに requirements.txt がある場合はそれを使用してください）
4. .env を作成
   - 対話式ウィザード: python -m kabusys.config_setup
   - もしくは .env.example を参考に手動作成（必須変数は後述）
5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります
6. DB 初期化
   - run_execution または run_monitoring を起動すると monitoring DB は自動で初期化されます（init_monitoring_db）。

必須環境変数（代表）
- JQUANTS_REFRESH_TOKEN — J-Quants API（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- OPENAI_API_KEY — OpenAI を使う場合（news_nlp / regime_detector）
推奨／その他
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — paper_trading の約定挙動（instant / partial / never / reject）
- LOG_LEVEL — ログレベル（INFO 等）
- KILL_FLAG_CLEAR_ON_START — ExecutionEngine 起動時に kill.flag を自動クリアするか（0/1）

.env 自動読み込み
- デフォルトでプロジェクトルートの .env/.env.local を自動読み込みします。
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 にすると自動ロードを無効化できます。

---

使い方（主要コマンド例）

1) 設定ウィザード（.env 作成）
- python -m kabusys.config_setup

2) 設定検証
- python -m kabusys.validate_config
- strict モード:
  - python -m kabusys.validate_config --strict

3) 実行エンジン起動（ExecutionEngine）
- python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録します（本番 DB と分離）。
  - 実行中は data/execution.pid に PID を書きます。
  - 停止要求: data/stop_requested.flag が存在すると起動を中止または実行中に停止します。

4) 監視ループ起動（Monitoring）
- python -m kabusys.run_monitoring
  - デフォルトのポーリング間隔は 60 秒。環境変数 MONITOR_POLL_INTERVAL で上書き可能（例: MONITOR_POLL_INTERVAL=30）。
  - 監視は Settings.sqlite_path（monitoring DB）を常に使用します（環境に依らず本番パスを参照）。
  - 停止要求: data/stop_requested.flag を作成するとループを終了します。

5) Paper Trading 検証レポート生成
- python -m kabusys.tools.paper_verification_report
- オプション:
  - --from YYYY-MM-DD, --to YYYY-MM-DD
  - --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数が優先される）
- 出力: 標準出力に検証サマリ（稼働率、fill/send rate、P95 レイテンシ等）

重要なフラグファイル
- data/stop_requested.flag
  - run_monitoring / run_execution が存在チェックして処理を終了するための「停止フラグ」。手動で作成/削除して運用できます。
- data/kill.flag
  - KillSwitch が書き込むことで ExecutionEngine に終了シグナルを送る用途（実運用の緊急停止）。生成は冪等。ExecutionEngine 起動設定により起動時に自動クリアできます（KILL_FLAG_CLEAR_ON_START=1）。

AI 機能
- news_nlp.score_news と regime_detector.score_regime が OpenAI を使用します。使用するには OPENAI_API_KEY を設定してください。
- モデル: gpt-4o-mini を想定（コード内定数参照）。
- API 呼び出しはリトライ・バックオフの実装がありますが、API キーやコスト管理は利用者の責任で行ってください。

---

ディレクトリ構成（主要ファイル説明）
- src/kabusys/
  - __init__.py — パッケージ定義（バージョン等）
  - config.py — 環境変数読み込み / Settings クラス（.env 自動ロード、必須チェックなど）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成ツール
  - ai/
    - news_nlp.py — ニュース NLP スコアリング（OpenAI 呼び出し、ai_scores 書込）
    - regime_detector.py — 市場レジーム判定（MA + マクロニュース + OpenAI）
  - monitoring/
    - monitoring_db.py — SQLite 監視 DB 初期化および読み書き API
    - system_monitor.py — システム・データ鮮度監視
    - trade_monitor.py — 注文滞留・約定異常検知
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag の管理
    - monitoring_engine.py — 各 Monitor をまとめて実行するエンジン
    - alert_manager.py — （アラート送信管理: 実装はこのファイルを参照）
  - portfolio/
    - portfolio_builder.py — 候補選定、重み付け
    - position_sizing.py — 発注株数算出、集約キャップ処理
    - risk_adjustment.py — セクター制限、レジーム乗数
  - research/
    - factor_research.py — モメンタム/ボラ/バリュー等のファクター計算（DuckDB 使用）
    - feature_exploration.py — 将来リターン・IC・統計サマリー
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
  - その他: execution/*（注文関連の実装）、data/（実行時に生成されるファイル群）など

（上記は主要なファイルの抜粋です。詳細は各ファイル冒頭の docstring を参照してください。）

---

運用上の注意点
- .env の管理は厳重に行ってください（機密情報が含まれるため Git に commit しない）。
- 本番環境（KABUSYS_ENV=live）の場合は特に LINE 通知設定や Kill Switch 設定を確認してください。validate_config に本番特有の注意が含まれています。
- OpenAI API を利用する機能は費用が発生します。API キーの漏洩に注意してください。
- monitoring は sqlite に稼働ログ・リスクログを書き込みます。ディスク容量やバックアップポリシーを検討してください。
- run_execution/run_monitoring 共にデーモン化、監視（systemd / supervisor 等での運用）を推奨します。実行中は data/execution.pid が保存されます。

---

その他
- コードドキュメント（各モジュールの冒頭 docstring）に設計上の注記や重要な制約（ルックアヘッド防止、冪等性、DuckDB executemany の制約回避など）が記載されています。実装や運用を拡張する際は参照してください。
- テストや CI、requirements.txt、デプロイ手順は本 README 作成時点のコードには含まれていません。必要に応じてプロジェクトのポリシーに合わせて追加してください。

ご不明点や README に追加したい運用手順・例（systemd unit 例や dockerization など）があれば教えてください。必要に応じて追記します。