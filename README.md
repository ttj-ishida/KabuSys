# KabuSys

日本株向けの自動売買システム（ライブラリ＋起動スクリプト）のリポジトリ。  
この README はコードベースの主要機能・セットアップ・起動方法・ディレクトリ構成を日本語でまとめたものです。

注意: 実際の運用では .env に認証情報や API キーを格納します。.env は絶対に Git にコミ載しないでください。

---

## プロジェクト概要

KabuSys は以下のような機能を持つモジュール群を含みます。

- Execution：発注処理（ExecutionEngine）・注文管理・リスク管理
- Monitoring：システム稼働・データ鮮度・注文状態・リスクを定期監視しアラート／Kill Switch を管理
- Portfolio：銘柄選定・重み付け・株数算出（等金額・スコア重み・リスクベース等）
- Research：DuckDB を利用したファクター計算・特徴量解析（モメンタム、バリュー、ボラティリティ等）
- AI：ニュースのセンチメント（OpenAI）や市場レジーム判定の支援
- Tools：Paper Trading の検証レポート生成などの CLI ツール
- utils：ログ設定、プロセス優先度設定などの共通ユーティリティ

設計方針の例:
- DuckDB / SQLite をローカルに用いてデータ処理・ログ永続化
- 本番（live）とペーパー（paper_trading）を意識した設定切替
- 外部 API 呼び出し（OpenAI 等）は環境変数経由でキーを与える設計
- ルックアヘッドバイアス対策（多数の関数で date.today() 等を直接参照しない）

---

## 機能一覧（主なもの）

- 環境設定ウィザード（.env 生成）: python -m kabusys.config_setup
- 設定検証 CLI（.env / config/*.yaml の簡易チェック）: python -m kabusys.validate_config
- ExecutionEngine 起動スクリプト: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い data/paper_trading.db に記録
  - PID ファイル管理（data/execution.pid 等）
  - 停止フラグ（data/stop_requested.flag）で外部から停止可能
- Monitoring 起動スクリプト: python -m kabusys.run_monitoring
  - 定期ポーリングで SystemMonitor / TradeMonitor / RiskMonitor を実行
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可（デフォルト 60 秒）
  - Monitoring は環境にかかわらず本番用 sqlite_path（data/monitoring.db）を使用
- MonitoringDB（SQLite）スキーマの初期化・マイグレーション機能
- AI モジュール
  - news_nlp.score_news: raw_news を集約して OpenAI へ送り ai_scores テーブルへ保存
  - regime_detector.score_regime: ETF の MA200 やマクロニュースを合成して日次レジーム判定
- Portfolio モジュール（候補選定・重み付け・ポジションサイズ計算・セクター制限）
- Tools
  - paper_verification_report: ペーパートレード結果を評価して PASS/FAIL レポート出力

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - Windows: .venv\Scripts\activate
   - macOS/Linux: source .venv/bin/activate

3. 依存パッケージをインストール  
   （requirements.txt はこのリポジトリに必ず存在するとは限りません。下記は主な依存例）
   - pip install duckdb psutil openai
   - （オプション）PyYAML: pip install pyyaml （validate_config で YAML 検証を行いたい場合）

4. ディレクトリ作成（data / logs）
   - mkdir -p data logs

5. 環境変数の準備
   - 対話式ウィザードで .env を作る（推奨）
     - python -m kabusys.config_setup
   - 必須環境変数（例）
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
   - 推奨・デフォルト例（.env に記述可能）
     - KABUSYS_ENV=development|paper_trading|live (default: development)
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - LOG_LEVEL=INFO
     - OPENAI_API_KEY=（AI 機能を使う場合）
     - KILL_FLAG_CLEAR_ON_START=0（本番では 0 推奨）

6. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い: python -m kabusys.validate_config --strict

---

## 使い方（起動・運用）

基本的にモジュールはパッケージモードで起動します（python -m ...）。

- ExecutionEngine を起動
  - python -m kabusys.run_execution
  - 動作:
    - Settings に従い SQLite / DuckDB に接続
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）を使い、本番 DB とは分離
    - data/stop_requested.flag が存在すると起動を中止または実行中に停止
    - PID ファイルを書き出します（data/execution.pid デフォルト）

- Monitoring を起動（監視ループ）
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を指定可能（例: export MONITOR_POLL_INTERVAL=30）
  - python -m kabusys.run_monitoring
  - 動作:
    - SystemMonitor / TradeMonitor / RiskMonitor をポーリングで呼び出し、MonitoringDB（SQLite）へログを残す
    - kill_switch（デフォルト: data/kill.flag）に基づく ExecutionEngine 停止判定を行い必要に応じてフラグを書き込む
    - 監視は環境にかかわらず Settings.sqlite_path（本番監視 DB）を使う点に注意

- 停止方法
  - 外部から即座に両プロセスを停止したい場合はプロジェクトルートの data/stop_requested.flag を作成します（run_* スクリプトが検知して終了します）
  - Execution を停止させる安全な方法としては Monitoring の Kill Switch が data/kill.flag を書き込み ExecutionEngine が検知して停止する仕組みがあります

- Paper トレード検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH または --db で変更可）

- AI 機能（ライブラリ関数として利用）
  - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - 実行には OPENAI_API_KEY を環境変数か引数で提供すること

---

## 主要環境変数（抜粋）

- 必須
  - JQUANTS_REFRESH_TOKEN : J-Quants API 用トークン
  - KABU_API_PASSWORD : kabuステーション API パスワード

- 実行環境・ログ
  - KABUSYS_ENV : development / paper_trading / live（デフォルト: development）
  - LOG_LEVEL : DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
  - LOG_DIR : ログ保存ディレクトリ（デフォルト: logs/）

- DB パス
  - DUCKDB_PATH : DuckDB ファイル（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH : Monitoring SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH : Paper trading 専用 SQLite（デフォルト: data/paper_trading.db）

- Monitoring / 停止関連
  - MONITOR_POLL_INTERVAL : 監視ポーリング間隔（秒、デフォルト: 60）
  - KILL_FLAG_PATH : kill.flag のパス（デフォルト: data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START : 起動時に kill.flag を自動クリアするなら 1（本番では 0 推奨）

- OpenAI
  - OPENAI_API_KEY : OpenAI API キー（AI 機能利用時）

- 自動 .env ロード無効化
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動で .env を読み込まない（テスト用）

---

## ログ

- ログはデフォルトで stdout とファイル（logs/<app_name>.log）に出力されます。ログは日次ローテートされ 30 日分保持されます。
- ログ設定ユーティリティ: kabusys.utils.logging_setup.setup_logging(app_name="execution")

---

## ディレクトリ構成（主要ファイル・モジュール）

リポジトリ内の主なディレクトリ／ファイル構成（src/kabusys を想定）:

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理（.env 自動読み込み）
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring 起動スクリプト
  - utils/
    - logging_setup.py        — ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py        — Monitoring SQLite スキーマ + DB 操作クラス
    - system_monitor.py       — システム・データ鮮度の監視
    - trade_monitor.py        — (注: 実装ファイルが該当リスト内に存在) 注文滞留・約定異常検出
    - risk_monitor.py         — ドローダウン・保有上限チェック
    - kill_switch.py          — kill.flag の管理
    - monitoring_engine.py    — 各 Monitor を束ねるエンジン
    - alert_manager.py        — アラート送信管理（LINE 等）（該当実装があれば）
  - execution/
    - execution_engine.py     — 実行エンジン本体（EngineConfig 等）
    - broker_factory.py       — ブローカークライアントの生成
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py             — ニュース NLP（OpenAI）
    - regime_detector.py      — 市場レジーム判定
  - tools/
    - paper_verification_report.py — Paper Trading レポート生成

（上記は実際のファイルの一部を抜粋・要約しています。より詳細な実装はソースツリーを参照してください）

---

## 運用上の注意点

- 本番環境（KABUSYS_ENV=live）では kill.flag / KILL_FLAG_CLEAR_ON_START の設定には特に注意してください。自動クリアを有効にすると Kill Switch が無効化される危険があります（本番は 0 推奨）。
- Monitoring は本番 monitoring DB（SQLITE_PATH）を使用するため、ロールアウト・テスト時は DB パスを明示的に切り替えてください（PAPER_TRADING_SQLITE_PATH を活用）。
- OpenAI の利用はコストとレイテンシが発生します。API エラー時はフェイルセーフでスコアをスキップまたは 0.0 にフォールバックする設計がされていますが、実運用前に十分テストしてください。
- ログディレクトリ・DB ファイルの権限やディスク容量には注意してください（ディスク使用率監視を有効にするなど）。

---

## よく使うコマンド例

- .env を対話作成:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Execution 起動:
  - python -m kabusys.run_execution

- Monitoring 起動（ポーリング間隔 30 秒に変更）:
  - export MONITOR_POLL_INTERVAL=30
  - python -m kabusys.run_monitoring

- Paper トレード検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - または DB を指定: python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

---

もし README に追加してほしい情報（例: 各構成ファイルの具体的な設定例、CI の設定、デプロイ手順、単体テストの実行方法など）があれば教えてください。必要に応じて追記します。