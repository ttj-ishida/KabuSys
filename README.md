# KabuSys

日本株自動売買システムの Python コードベース用 README（日本語）

概略、本書はリポジトリ内の主要コンポーネント、セットアップ手順、実行方法、ディレクトリ構成をまとめたドキュメントです。

注意: .env は機密情報を含みます。絶対に Git にコミットしないでください。

---

目次
- プロジェクト概要
- 機能一覧
- 前提条件 / 依存関係
- セットアップ手順
- 環境変数（主なキー）
- 使い方（主要スクリプト / CLI）
- 運用時の注意点
- ディレクトリ構成（主要ファイル説明）

---

プロジェクト概要
- KabuSys は日本株の自動売買プラットフォームのコア部分を提供するリポジトリです。
- 以下のサブシステムを含みます:
  - ExecutionEngine（発注・リスク管理・注文管理）
  - Monitoring（システム稼働・注文・リスク監視、Kill Switch）
  - Research（ファクター算出、特徴量解析）
  - AI 統合（OpenAI を用いたニュースセンチメント / レジーム判定）
  - Portfolio Construction（候補選定、重み算出、ポジションサイズ決定）
  - ユーティリティ（ログ設定、プロセス優先度設定、設定ロード等）
- 開発 / ペーパートレード / 本番（live）を環境変数で切り替え可能。

機能一覧（ハイレベル）
- 発注実行エンジン（本番または paper_trading 用 Mock クライアントの切替）
- 監視ループ（SystemMonitor、TradeMonitor、RiskMonitor を束ねる MonitoringEngine）
- Kill Switch（閾値超過時に data/kill.flag を書き込んで ExecutionEngine を停止）
- Paper Trading 検証レポート生成ツール
- ファクター計算（Momentum / Volatility / Value 等）
- 特徴量探索（将来リターン計算、IC 計算、統計サマリー）
- ニュース NLP（OpenAI を使ったセンチメントスコア算出）
- 市場レジーム判定（MA200 とマクロセンチメントに基づく判定）
- ログ設定ユーティリティ（コンソール + 日次ローテートファイル）
- 環境設定ウィザード、設定検証 CLI

前提条件 / 依存関係（代表）
- Python 3.9+（コードは型ヒント等を利用）
- 外部ライブラリ（少なくとも次をインストールすることを推奨）
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証で任意）
- 標準ライブラリ: sqlite3, logging, threading, datetime 等

（pip 用の requirements.txt はリポジトリに含まれていない想定のため、実行環境で上記をインストールしてください）
例:
  pip install duckdb psutil openai PyYAML

セットアップ手順
1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存ライブラリをインストール
   - pip install duckdb psutil openai PyYAML
4. 環境変数の用意（.env）
   - 対話式ウィザードで作成:
       python -m kabusys.config_setup
   - もしくは .env を手動で作成
   - 例（.env に書く主要キー）:
       JQUANTS_REFRESH_TOKEN=your_token_here
       KABU_API_PASSWORD=your_password_here
       KABUSYS_ENV=development
       DUCKDB_PATH=data/kabusys.duckdb
       SQLITE_PATH=data/monitoring.db
       LOG_LEVEL=INFO
       OPENAI_API_KEY=sk-...
   - .env はデフォルトでプロジェクトルートから自動読み込みされます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化可能）
5. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱い（exit code 1）
6. データディレクトリの作成（ログ・DB の格納）
   - デフォルトでは data/ と logs/ を使用します。config_setup で指定したパスを確認してください。

環境変数（主なもの）
- 必須（運用で必須の例）
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン
  - KABU_API_PASSWORD — kabuステーション API のパスワード
- 実行環境 / ログ
  - KABUSYS_ENV — development | paper_trading | live（デフォルト: development）
  - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
  - LOG_DIR — ログファイル保存ディレクトリ（デフォルト: logs/）
- DB 関連
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- Paper トレード挙動
  - PAPER_FILL_MODE — instant | partial | never | reject（デフォルト: instant）
- Kill Switch / 制御
  - KILL_FLAG_PATH — data/kill.flag のパス（デフォルト）
  - KILL_FLAG_CLEAR_ON_START — 起動時に Kill Flag を自動クリアするか（0/1、本番では 0 推奨）
- Monitoring
  - MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、run_monitoring で上書き。デフォルト 60）
- OpenAI
  - OPENAI_API_KEY — news_nlp / regime_detector で利用（必須の場合は例外）

使い方（主要スクリプト / CLI）
- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup
- 設定検証（起動前に推奨）
  - python -m kabusys.validate_config
  - --strict を付けると警告があると exit(1)
- ExecutionEngine（発注エンジン）起動
  - python -m kabusys.run_execution
  - 動作:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録（本番 DB と分離）
    - 実行中に data/stop_requested.flag が作成されると安全停止
    - 起動時に既存の kill.flag を自動クリアする設定が有効なら clear する（KILL_FLAG_CLEAR_ON_START）
- Monitoring（監視）起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可能（デフォルト 60 秒）
  - 監視は常に本番用 sqlite_path を使って監視ログを書きます（環境に依存せず本番 DB パス）
  - stop flag（data/stop_requested.flag）でループ終了
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - 簡易的な PASS/FAIL 判定（稼働率、成功率、レイテンシ 等）
- Research / AI / その他（モジュール的に利用）
  - kabusys.research.calc_momentum / calc_volatility / calc_value などは DuckDB コネクションを受け取る純粋関数
  - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime は OpenAI API と組み合わせて使う
- ログ設定
  - 各起動スクリプトは最初に kabusys.utils.logging_setup.setup_logging(app_name=...) を呼び出します
  - ログは stdout と logs/<app_name>.log（日次ローテート）へ出力されます

運用時の注意点 / トラブルシューティング
- .env を誤ってコミットしないでください。
- KABUSYS_ENV=live のときは特に注意：実売買が行われます。validate_config の警告を必ず確認してください。
- OpenAI を使う処理（ニュース NLP / レジーム判定）は API エラー時にフェイルセーフ（0.0 等）で続行する設計ですが、API キー未設定だと ValueError で失敗します。
- Monitoring と Execution は stop フラグ（data/stop_requested.flag）や kill.flag（デッドマン）による停止制御を行います。flag の場所は Settings で設定可能です。
- ログディレクトリ作成に失敗した場合、ファイル出力は無効化されコンソールのみになります。権限等を確認してください。
- DuckDB / SQLite のパスは .env で明示すること。Paper Trading は paper_sqlite_path で DB を分離します。

ディレクトリ構成（抜粋 / 主要ファイル）
- src/kabusys/
  - __init__.py — パッケージ定義（__version__ 等）
  - config.py — 環境変数 / 設定管理（.env 自動ロードロジック含む）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前の設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - utils/
    - logging_setup.py — ログ初期化ユーティリティ（stdout + 日次ローテート）
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
  - monitoring/
    - monitoring_db.py — 監視ログ用 SQLite の初期化 & 永続化 API（MonitoringDB）
    - system_monitor.py — システム状態 / データ鮮度監視
    - risk_monitor.py — ドローダウン / ポジション上限を監視
    - trade_monitor.py — （存在を想定、trade 関連監視）
    - monitoring_engine.py — 複数 Monitor を束ねるエンジン & アラート連携
    - kill_switch.py — kill.flag の書き込み / クリア
    - alert_manager.py — （アラート送信管理、LINE 連携等を想定）
  - execution/
    - execution_engine.py — 実際の発注フロー（Engine）
    - broker_factory.py — ブローカークライアント生成（Mock / 実ブローカー切替）
    - order_manager.py / order_repository.py / reconciler.py / risk_manager.py 等（発注・管理・リスク）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み算出
    - position_sizing.py — 株数決定、単元丸め、aggregate cap
    - risk_adjustment.py — セクターキャップ、レジーム乗数
  - research/
    - factor_research.py — モメンタム / ボラティリティ / バリュー等
    - feature_exploration.py — 将来リターン、IC、統計サマリー
  - ai/
    - news_nlp.py — ニュースセンチメント取得（OpenAI）
    - regime_detector.py — 市場レジーム判定（MA200 + マクロセンチメント）
  - data/ （実行時に使用）
    - monitoring.db（デフォルト）
    - paper_trading.db（paper_trading 用）
    - kill.flag, stop_requested.flag, execution.pid などの制御ファイル
  - logs/ （デフォルトログ格納）

補足（実装上のポイント）
- 設計思想:
  - 外部 API 呼び出し（OpenAI 等）に対してはリトライ・フォールバックを備え、不可逆的な失敗を回避する設計
  - DuckDB を分析用途（prices_daily, raw_financials 等）で利用し、Research 系は副作用なしの純粋関数群
  - MonitoringDB（SQLite）は監視ログ専用。init_monitoring_db による冪等な初期化とマイグレーションロジックを持つ
- Paper Trading:
  - KABUSYS_ENV=paper_trading の場合、発注は MockBrokerClient によって行われ、paper_trading 用 SQLite に記録される（本番 DB と完全に分離）
- Kill / Stop 制御:
  - data/kill.flag は ExecutionEngine 停止トリガー。KillSwitch が条件を満たすと書き込む
  - data/stop_requested.flag は run_execution/run_monitoring の外部停止指示（単純な存在チェック）

---

最後に
- まずは python -m kabusys.config_setup で .env を作成し、python -m kabusys.validate_config で検証してから起動してください。
- 本番稼働前には KABUSYS_ENV=live での保護（LINE 通知設定・KILL_FLAG_CLEAR_ON_START=0 等）を必ず確認してください。

必要があれば README に追記したい項目（例: より詳細な実行例、Docker 化手順、unit tests の実行方法、requirements.txt）を教えてください。