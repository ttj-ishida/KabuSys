# KabuSys

日本株向け自動売買システムのモジュール群（ライブラリ兼起動スクリプト群）。  
このリポジトリは発注エンジン、監視・アラート、ポートフォリオ構築、リサーチ（ファクター計算）、およびニュース NLP / レジーム判定などのサブモジュールから構成されています。

バージョン: 0.1.0

## 概要
KabuSys は次のような機能を持つコンポーネント群を提供します。

- ExecutionEngine：発注・注文管理・リスク管理を行うエンジン（本番 / ペーパートレード切替対応）
- Monitoring：システム稼働状況、データ鮮度、注文状況、リスク指標を定期的に監視・ログ化し、必要に応じて Kill Switch を発動
- Portfolio Construction：銘柄選定・配分・ポジションサイズ計算等の純粋関数群
- Research：DuckDB 上の時系列データからファクター計算・特徴量探索を行うユーティリティ
- AI モジュール：OpenAI を使ったニュースセンチメント（news_nlp）やマクロ情報との組合せによる市場レジーム判定（regime_detector）
- ユーティリティ群：ログ設定、プロセス優先度設定、設定ウィザード / 検証など

## 主な機能一覧
- 環境切替（development / paper_trading / live）
  - paper_trading では MockBrokerClient を使い、ペーパートレード用 DB（data/paper_trading.db）へ記録
- 監視（system / trade / risk）と Kill Switch（data/kill.flag を書き込んで ExecutionEngine を停止）
- 日次ローテーションのログ出力（デフォルト: logs/<app>.log）
- DuckDB を用いた時系列ファクター計算（mom, vol, value 等）
- OpenAI（gpt-4o-mini 想定）を使ったニュースセンチメント集計とレジーム判定（API キー必要）
- Paper Trading 検証レポート生成ツール

## 必要要件（概略）
- Python 3.9+
- 必要な外部ライブラリ（一例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config ファイル検証を行う場合に推奨）
- SQLite（標準ライブラリの sqlite3 を使用）

具体的なパッケージ管理ファイルが無い場合はローカル環境で次をインストールしてください：

pip install duckdb psutil openai pyyaml

> OpenAI 関連機能を使う場合は環境変数 `OPENAI_API_KEY` を設定してください。

## セットアップ手順（クイックスタート）
1. リポジトリをクローン／配置
2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb psutil openai pyyaml
4. .env の作成（対話式ウィザード）
   - python -m kabusys.config_setup
     - ウィザードは `.env` を生成します。J-Quants や kabu API のパスワードなど必須項目はここで設定します。
5. 設定検証
   - python -m kabusys.validate_config
     - `--strict` を付けると警告も失敗扱いになります。
6. 必要に応じてデータディレクトリ作成
   - data/ ディレクトリは DB やフラグファイル用に必要です（自動作成する処理もありますが、最初に手動で用意しておくと安全です）。

## 環境変数（主なもの）
- KABUSYS_ENV: 実行環境 ("development" | "paper_trading" | "live")（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール使用時必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視 DB）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード時の SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（"DEBUG"/"INFO"/...）
- LOG_DIR: ログ出力ディレクトリ（デフォルト: logs/）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒。デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 本番環境で Kill Switch 自動クリアを行うか（"0"/"1"）

## 使い方（主要コマンド）
- 設定ウィザード
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config [--strict]
- ExecutionEngine（発注エンジン）起動
  - python -m kabusys.run_execution
  - 備考:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して data/paper_trading.db に記録します（本番 DB と分離）。
    - 実行中に data/stop_requested.flag を作成すると安全に停止できます（スクリプトはフラグを検知して停止します）。
    - 実行時に data/execution.pid に PID が保存されます。
- Monitoring（SystemMonitor の簡易起動）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でループ間隔を秒単位で上書きできます（デフォルト 60 秒）。
  - run_monitoring は Monitoring 用 DB（settings.sqlite_path）を使います（環境にかかわらず本番 sqlite_path を使用する設計）。
  - 停止フラグ: data/stop_requested.flag によりループを終了します。
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db
- AI: ニューススコアリング / レジーム判定（プログラム API）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続を受け取り、結果をテーブルへ書き込みます。OPENAI_API_KEY が必要です。

## 停止・Kill Switch
- ExecutionEngine の停止:
  - data/kill.flag に理由を書き込むことで Kill Switch を発動できます（KillSwitch クラスが存在する場合、ExecutionEngine 側で読み取り停止する仕組み）。
  - data/stop_requested.flag を作ると run_execution/run_monitoring のトップレベルループが安全に終了します。
- Kill Switch の自動クリア:
  - 環境変数 `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に kill.flag を削除します（本番では危険）。

## ログ・DB
- ログ:
  - デフォルト: logs/<app_name>.log（日次ローテーション、30日保持）
  - ログディレクトリは LOG_DIR 環境変数または setup_logging の引数で変更可能
- DB:
  - DuckDB（分析用）: DUCKDB_PATH（デフォルト data/kabusys.duckdb）
  - SQLite（監視）: SQLITE_PATH（デフォルト data/monitoring.db）
  - Paper Trading 用 SQLite: PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）

## 開発者向けメモ / 注意点
- Settings クラスは環境変数 / .env を元に設定値を提供します。自動 .env ロードはプロジェクトルート（.git または pyproject.toml を基準）を探索して行います。自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- Monitoring モジュールは SQLite に監視ログを永続化します。init_monitoring_db で必要テーブルを冪等的に作成します。
- OpenAI を叩く処理はリトライ・バックオフやレスポンス検証（JSON 抽出・スコアクリップ）などを備えていますが、API キー・レート制限・料金に注意してください。
- `python -m kabusys.validate_config` は起動前チェックに有用です。PyYAML がない場合は YAML の検証をスキップします（警告）。

## ディレクトリ構成
リポジトリの主要なファイル / 役割は次の通りです（src/kabusys 配下）:

- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数・設定管理（Settings クラス）
  - config_setup.py — .env 対話型ウィザード
  - validate_config.py — 起動前設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading レポート生成スクリプト
  - execution/  (発注エンジン関連モジュール)
    - (BrokerClientFactory, ExecutionEngine, OrderManager, OrderRepository, Reconciler, RiskManager 等)
  - monitoring/
    - monitoring_db.py — 監視用 SQLite 永続化層
    - system_monitor.py — システム監視（CPU/メモリ/ディスク・データ鮮度・プロセス監視）
    - trade_monitor.py — 注文監視（trade_logs ベース）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag の読み書き用ユーティリティ
    - monitoring_engine.py — 各 Monitor を束ねるループ
    - alert_manager.py — （アラート送信の抽象化）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数算出・丸め・キャップ処理
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py — 将来リターン・IC 計算等
  - ai/
    - news_nlp.py — ニュースセンチメント集約（OpenAI 呼び出し含む）
    - regime_detector.py — ETF + マクロニュースでレジーム判定（OpenAI 呼び出し含む）
  - data/  (実行時に使用する DB / フラグファイルを配置する想定)
    - *.db, kill.flag, stop_requested.flag, execution.pid など
  - utils/
    - logging_setup.py — ロギング設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

（注）一部ファイルはここに説明のために抜粋して示しています。実装済みのサブモジュールは execution/* や monitoring/ の内部に多数存在します。

## よくあるトラブルシューティング
- OpenAI 関連関数を呼んでも動かない：
  - 環境変数 `OPENAI_API_KEY` を設定するか、関数へ `api_key` を渡してください。
- config 検証で YAML 検証がスキップされる：
  - PyYAML がインストールされていないと YAML パース検証をスキップします。`pip install pyyaml` を推奨。
- run_monitoring / run_execution がすぐ終了する：
  - data/stop_requested.flag が存在すると起動を辞退して終了します。削除してから再試行してください。

## ライセンス
（この README ではライセンス情報は含めていません。必要に応じて LICENSE ファイルを追加してください。）

---

以上が本コードベースの README.md（日本語）になります。必要であれば、さらに詳細な起動手順（systemd ユニット例や Dockerfile、テストの書き方、CI 設定例）を追加できます。どの項目を詳しく書くか指示をください。