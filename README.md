KabuSys — README
=================

概要
----
KabuSys は「日本株自動売買システム」のコアライブラリ群です。シグナル生成・ポートフォリオ構築・発注エンジン・監視・レポート・研究ユーティリティなどを含むモジュール式の実装で、実運用（live）とペーパートレード（paper_trading）を分離して扱える設計になっています。

主な設計方針
- 環境変数/.env による設定管理（config_setup によるウィザードあり）
- 実行コードと監視コードは別プロセスで運用（stop/kill フラグで制御）
- DuckDB／SQLite をデータ層として使用（分析用・監視用に分離）
- OpenAI を用いたニュース NLP / レジーム判定機能を提供（任意）

機能一覧
- 環境設定ウィザード（python -m kabusys.config_setup）
- 設定検証 CLI（python -m kabusys.validate_config）
- ExecutionEngine（発注エンジン）の起動スクリプト（run_execution）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し paper_trading DB に記録
- 監視用ループ（run_monitoring）
  - システム状態、注文滞留、リスク（ドローダウン/ポジション上限）監視
  - Kill Switch（条件に応じて data/kill.flag を書き込み ExecutionEngine を停止）
- 監視 DB（SQLite）操作ヘルパー（monitoring_db）
- ポートフォリオ構築モジュール（候補選定、重み算出、ポジションサイズ計算、セクター制限）
- 研究用モジュール（ファクター計算／特徴量解析・IC 計算）
- AI モジュール（news_nlp: ニュースセンチメント、regime_detector: 市場レジーム判定）
- 各種ユーティリティ（ログ設定、プロセス優先度設定など）
- ツール: Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）

前提条件
- Python 3.10+
- 推奨パッケージ（代表例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証時に必要／任意）
- (任意) OpenAI API を利用する場合は OPENAI_API_KEY を設定

セットアップ手順
1. リポジトリをクローン／配置
2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 依存ライブラリをインストール
   - pip install duckdb psutil openai pyyaml
   - （requirements.txt がある場合は pip install -r requirements.txt）
4. data/ と logs/ ディレクトリを作成（スクリプトが自動作成することもありますが、手動で作ると権限問題を防げます）
   - mkdir -p data logs
5. 初期設定（.env）の作成
   - python -m kabusys.config_setup
   - 対話式で必須項目（J-Quants トークン、kabu API パスワード など）を入力して .env を生成
6. 設定検証（推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いで終了コード 1 を返します

主な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- LOG_LEVEL（デフォルト: INFO）
- OPENAI_API_KEY（AI 機能を使う際に必要）

使い方（主なコマンド）
- 環境設定ウィザード
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
- ExecutionEngine 起動（発注エンジン）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading に設定すると MockBroker に切り替わり data/paper_trading.db を使用
  - 起動時に data/stop_requested.flag が存在すると起動しません
- Monitoring 起動（監視ループ）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL=30 等でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）
  - 監視は本番 sqlite_path を環境にかかわらず使用（監視データは本番 DB に記録）
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで DB を指定可能（環境変数 PAPER_TRADING_SQLITE_PATH と併用可）
- AI 機能（ニュース NLP / レジーム判定）
  - 使用例: kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime を呼び出し。OpenAI API キーが必要。

挙動・運用に関する注意
- run_execution は PID ファイル（data/execution.pid）や stop/kill フラグ（data/stop_requested.flag, data/kill.flag）でプロセス制御します。
- run_monitoring は監視ループを回し、MonitoringEngine が SystemMonitor / TradeMonitor / RiskMonitor を呼び出してアラート判定や Kill Switch 書き込みを行います。
- ログは logs/<app_name>.log に日次ローテーションで出力されます（logs ディレクトリを作成してください）。
- .env は機密情報を含むため絶対にリポジトリにコミットしないでください。

ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/.env 読み込み・Settings 定義
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - monitoring/
    - monitoring_db.py       — SQLite による監視ログ永続化層
    - system_monitor.py      — システム状態・データ鮮度監視
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - trade_monitor.py       — （注文監視ロジック）
    - monitoring_engine.py   — 各 Monitor を束ねる
    - kill_switch.py         — kill.flag 書き込みロジック
    - alert_manager.py       — （アラート送信管理）
  - execution/               — 発注エンジン・オーダー管理関連
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み計算
    - position_sizing.py     — 株数決定ロジック
    - risk_adjustment.py     — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py     — Momentum/Value/Volatility 等のファクター計算
    - feature_exploration.py — IC / forward returns / 統計サマリー
  - ai/
    - news_nlp.py            — ニュースセンチメント（OpenAI）
    - regime_detector.py     — 市場レジーム判定（OpenAI + ma200）
  - tools/
    - paper_verification_report.py — Paper Trading レポート生成ツール
  - utils/
    - logging_setup.py       — 統一ログ設定
    - process_priority.py    — プロセス優先度 / CPU affinity 設定

実運用上の推奨ワークフロー（例）
1. python -m kabusys.config_setup で .env を作成
2. python -m kabusys.validate_config で設定をチェック
3. （必要なら）Paper DB や DuckDB を初期化 / データ投入
4. 監視プロセスを起動: python -m kabusys.run_monitoring
5. Execution エンジンを起動: python -m kabusys.run_execution
6. 監視・アラート・ログを確認しつつ運用

トラブルシューティング / 補足
- PyYAML 未インストール時、validate_config は YAML 検証をスキップして警告を出します。
- OpenAI API 使用時は API エラー（429/5xx/接続断）に対して指数バックオフ・リトライ実装がありますが、環境変数 OPENAI_API_KEY の設定は必須です。
- ログディレクトリ作成に失敗した場合はコンソール出力のみで継続します（ファイル出力は無効化）。
- .env 自動ロードはプロジェクトルート（.git または pyproject.toml を基準）を自動判定して行われます。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ライセンス / バージョン
- パッケージバージョンは src/kabusys/__init__.py の __version__ を参照してください（現在 0.1.0）。

以上が簡易 README です。必要であれば各サブモジュール（ExecutionEngine の起動オプション、TradeMonitor の詳細、AI モデルプロンプト等）についての詳細説明やコマンド例を追記します。どの項目を詳述しましょうか？