# KabuSys — 日本株自動売買システム（README）

このリポジトリは日本株の自動売買・リサーチ・監視を目的としたモジュール群です。コアは発注エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、ファクター計算、AI を使ったニュース NLP / レジーム判定などで構成されています。

以下はこのコードベースの概要、主な機能、セットアップ手順、使い方、ディレクトリ構成の説明です。

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方
- 環境変数（主要なもの）
- ディレクトリ構成
- 備考 / 運用上の注意

---

プロジェクト概要
- KabuSys は日本株を対象とした自動売買システムのライブラリ／実行コンポーネント群です。
- 発注ロジック（ExecutionEngine）と監視（Monitoring）が分離されており、ペーパートレード用の完全分離 DB を用いたテスト運用が可能です。
- DuckDB を解析・研究用データベースとして利用し、SQLite を監視・トレードログ等の永続化に使用します。
- ニュースセンチメントやマクロ情報を LLM（OpenAI）で評価する機能を持ち、レジーム判定や銘柄ごとの AI スコアを生成できます。
- ロギング、プロセス優先度設定、Kill Switch（停止フラグ）、各種検証/セットアップ用 CLI を備えています。

---

主な機能一覧
- 実行エンジン起動スクリプト（run_execution.py）
  - KABUSYS_ENV による本番 / ペーパートレード切替
  - paper_trading では MockBrokerClient を利用し data/paper_trading.db に記録
  - リスク管理（RiskManager）、注文管理、リコンシリエーション等を統合
- 監視ポーリングループ（run_monitoring.py）
  - SystemMonitor / TradeMonitor / RiskMonitor を用いた定期監視
  - MONITOR_POLL_INTERVAL でポーリング間隔を制御（デフォルト 60 秒）
  - 停止フラグ / stop_requested.flag による安全停止
- 環境設定ウィザード（config_setup.py）
  - .env の初期作成・更新を対話的に支援
- 設定検証 CLI（validate_config.py）
  - .env や config/*.yaml の基本チェック（--strict オプションあり）
- Paper Trading 検証レポート（tools/paper_verification_report.py）
  - ペーパートレード DB を集計し通過基準（稼働率・成功率・レイテンシ等）を判定
- ポートフォリオ構築（kabusys.portfolio）
  - 候補選定、重み計算（等金額 / スコア加重）、ポジションサイズ算出、セクター上限適用、レジーム乗数
- リサーチ（kabusys.research）
  - ファクター計算（モメンタム・バリュー・ボラティリティ）、将来リターン、IC 計算、統計サマリ
- AI 関連（kabusys.ai）
  - news_nlp: raw_news を集約して OpenAI に投げ、銘柄ごとの ai_score を生成
  - regime_detector: ETF（1321）MA200 とマクロニュースを組み合わせて市場レジーム判定
- 監視 DB 層（kabusys.monitoring.monitoring_db）
  - system_status, trade_logs, positions, risk_logs, dashboard テーブルの作成・操作関数
- ユーティリティ
  - logging_setup: 日次ローテーション付きログ設定
  - process_priority: プロセス優先度 / CPU affinity の設定

---

セットアップ手順（開発 / 実行環境の一例）
1. リポジトリを取得
   - git clone ...（リポジトリ URL）
2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 依存パッケージをインストール
   - 参考パッケージ:
     - duckdb
     - psutil
     - openai
     - PyYAML（validate_config の YAML 検証で使用）
   - 例:
     - pip install duckdb psutil openai PyYAML
   - SQLite は標準ライブラリに含まれます。
4. .env を作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - もしくは .env.example を参考に手動作成
   - 自動ロード:
     - ルート（.git または pyproject.toml）を基に .env/.env.local が自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
5. 設定検証（必須項目があるか確認）
   - python -m kabusys.validate_config
   - 問題があれば --strict で警告も Fail として扱えます。
6. データディレクトリの作成（必要に応じて）
   - デフォルトは data/ 下に DB や PID/flag ファイルを作成します。logs/ ディレクトリもログ出力量に応じて生成されます。

---

主要な環境変数（抜粋）
- 必須（運用時）
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 実行環境制御
  - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
  - PAPER_FILL_MODE — paper_trading 時の MockBroker の fill 動作（instant|partial|never|reject）
- DB / ファイルパス
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — monitoring SQLite パス（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
  - PID_FILE_PATH, KILL_FLAG_PATH — 各種ファイルパス
- OpenAI / 通知
  - OPENAI_API_KEY — OpenAI API キー（news_nlp, regime_detector 等）
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知（任意）
- ログ / 動作制御
  - LOG_LEVEL — ログレベル（DEBUG/INFO/...）
  - LOG_DIR — ログの保存ディレクトリ
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
- その他
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 — 自動 .env 読み込みを無効化（テスト用）

例（.env の最小）:
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
OPENAI_API_KEY=sk-...

---

使い方（主要なコマンド）
- 環境作成ウィザード（.env 作成）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - strict モード: python -m kabusys.validate_config --strict
- 実行エンジン起動（Execution）
  - python -m kabusys.run_execution
  - 注意: KABUSYS_ENV=paper_trading の場合は paper_trading DB に完全分離して記録されます。
  - stop: プロセスを直接終了するか、監視側の kill.flag を使って安全停止できます（data/kill.flag を書き込み）。
- 監視ループ起動（Monitoring）
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL を環境変数で上書き可能（秒）。不正な値はデフォルト 60 秒にフォールバック。
  - 監視は常に production（本番）用の sqlite_path を使用（環境に関係なく monitoring 用 DB は本番パス）。
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間を指定: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-10
  - DB 指定: --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数より優先）
- 監視・停止フラグについて
  - stop_requested.flag（run_monitoring / run_execution が監視している停止フラグ）はプロジェクトの data/ 配下に置かれており、存在するとループが終了します。
  - KillSwitch は条件を満たすと data/kill.flag を書き込んで ExecutionEngine に停止命令を出します（冪等に書き込み）。

ログ
- ログはデフォルトで logs/ に出力され、日次ローテーションで 30 日分保持されます（kabusys.utils.logging_setup による）。
- コンソール出力は stdout に出力されます（cron / Task Scheduler での取り扱いを想定）。

---

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py — 環境変数読み込み・Settings 定義（自動 .env 読み込みロジック含む）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前の設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py — SQLite 永続化層（テーブル作成 + 操作用クラス）
    - monitoring_engine.py — 各 Monitor を束ねるポーリングエンジン
    - system_monitor.py — システム状態 / データ鮮度チェック
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - trade_monitor.py — （トレード監視、滞留注文等 — 実装参照）
    - kill_switch.py — 停止フラグ書き込み用ユーティリティ
    - alert_manager.py — （通知管理）
  - execution/
    - execution_engine.py — ExecutionEngine 本体（起動 / run_session 等）
    - broker_factory.py — ブローカークライアント生成（Mock / 実ブローカー）
    - order_manager.py — 注文管理
    - order_repository.py — 注文履歴リポジトリ
    - reconciler.py — 注文整合処理
    - risk_manager.py — 発注前リスクチェック
  - portfolio/
    - portfolio_builder.py — 候補選定・重み付け
    - position_sizing.py — 発注株数計算、集約キャップ処理
    - risk_adjustment.py — セクター上限・レジーム乗数
  - research/
    - factor_research.py — モメンタム / バリュー / ボラティリティ計算（DuckDB）
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - ai/
    - news_nlp.py — raw_news を LLM に投げて ai_scores を生成
    - regime_detector.py — ETF MA + マクロニュースでレジーム判定
  - tools/
    - paper_verification_report.py — Paper Trading レポート生成
  - data/ （ランタイムで作成される想定）
    - *.db, *.pid, kill.flag, stop_requested.flag など

（注）実際のファイルはリポジトリを確認してください。ここでは主なファイルと役割を抜粋しています。

---

運用上の注意 / ベストプラクティス
- 本番環境（KABUSYS_ENV=live）では .env に機密情報を平文で置くため、Git 等に絶対にコミットしないこと。
- validate_config で設定チェックを行い、特に live のときは通知先（LINE 等）や kill_flag 設定を確認してください。
- run_execution は停止フラグや PID ファイルを利用しているため、監視プロセスと連携して安全に停止・再起動を行ってください。
- OpenAI を使う処理（news_nlp, regime_detector）は API キーとコスト管理に注意。失敗時はフェイルセーフ（スコア 0 など）になる実装です。
- DuckDB のデータは分析用に大きくなる可能性があるため保管場所やバックアップを検討してください。
- psutil によるプロセス優先度設定は権限が必要になる場合があります。実行ユーザーの権限と OS を確認してください。

---

追加情報 / トラブルシューティング
- PyYAML がインストールされていない場合、validate_config は YAML の中身検証をスキップします（ワーニングが出ます）。検証を機能させるには PyYAML をインストールしてください。
- run_monitoring は MONITOR_POLL_INTERVAL が不正（0 や負数・非整数）の場合はデフォルト 60 秒にフォールバックします。
- Paper Trading と本番 DB は分離されています。paper_trading 用 DB のパスは PAPER_TRADING_SQLITE_PATH で指定可能です。

---

この README はコードリーディングから生成しています。より詳細な仕様（StrategyModel.md、PortfolioConstruction.md 等）がリポジトリ内にある場合は合わせて参照してください。質問やドキュメントの追補を希望される箇所があれば教えてください。