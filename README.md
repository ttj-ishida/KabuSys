# KabuSys

日本株向け自動売買システムのコアライブラリ群。戦略のファクター計算、ポートフォリオ構築、注文実行、監視、AI ベースのニュースセンチメント評価などを含むモジュール群です。

> 注意: .env ファイルは機密情報（API トークン等）を含みます。絶対にリポジトリにコミットしないでください。

---

目次
- プロジェクト概要
- 主な機能一覧
- 前提条件
- セットアップ手順
- 使い方（主要スクリプト / CLI）
- 環境変数一覧（主なもの）
- プロジェクト構成（ディレクトリ）

---

プロジェクト概要
- KabuSys は日本株の自動売買を支援するライブラリ／実行環境です。
- ファクター計算、シグナル生成やポートフォリオ構築、注文サイズ計算、注文管理、リスク監視、監視エンジン、LINE による通知、OpenAI を用いたニュース NLP（センチメント評価）などを含みます。
- DB は分析用に DuckDB、監視・発注ログ用に SQLite を使用します。Paper Trading（ペーパートレード）モードでは本番発注 DB とは完全に分離された専用 SQLite を利用します。

---

主な機能一覧
- research:
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算・IC 計測・特徴量サマリ
- portfolio:
  - 候補選定、等配分／スコア配分、ポジションサイズ計算、セクターキャップ、レジーム乗数
- execution（エンジン群）:
  - BrokerClientFactory 経由で実際のブローカークライアント or Mock（paper_trading）
  - ExecutionEngine による注文実行／リコンシリエーション／リスク管理
- monitoring:
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねた MonitoringEngine
  - 監視ログ（system_status, trade_logs, risk_logs, positions, dashboard）を SQLite に永続化
  - KillSwitch による安全停止（kill.flag）
  - LINE 通知（AlertManager）
- ai:
  - news_nlp: OpenAI を用いた銘柄別ニュースセンチメントスコア取得・ai_scores への書込
  - regime_detector: ETF とマクロニュースで日次の市場レジーム判定
- tools:
  - paper_verification_report: ペーパートレード結果の検証レポート生成
- 設定管理:
  - .env の自動ローディング（プロジェクトルートを探索）
  - config_setup.py による対話的 .env 生成ウィザード
  - validate_config.py による起動前検証 CLI

---

前提条件
- Python 3.10 以上（typing における | 演算子などを使用）
- 必要なパッケージ（例）
  - duckdb
  - psutil
  - requests
  - openai
  - PyYAML（config の YAML 検証を行う場合に推奨）
- OS 標準のネットワーク／ファイルアクセス権限（プロセス優先度や PID 操作に関連）

インストール（例）
- 仮想環境作成・有効化
  - python -m venv .venv
  - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
- 必要パッケージをインストール
  - pip install duckdb psutil requests openai PyYAML

※ 実際の requirements.txt / setup.cfg があればそちらを利用してください。

---

セットアップ手順（初期導入）
1. リポジトリをチェックアウト
2. Python 仮想環境を作成・有効化、依存パッケージをインストール
3. プロジェクトルートに data ディレクトリを作成（必要なら自動作成されますが事前作成しておくと安心）
   - mkdir -p data
4. .env を作成
   - 対話式ウィザード: python -m kabusys.config_setup
   - もしくは .env.example を参考に手動で作成
   - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
   - AI 機能を使う場合: OPENAI_API_KEY
5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告も FAIL 扱いにする: python -m kabusys.validate_config --strict
6. DB 初期化
   - 実行スクリプト（run_monitoring/run_execution）実行時に必要テーブルが自動作成されます（init_monitoring_db が冪等で実行されます）。
7. 必要に応じて DuckDB の prices_daily / raw_financials 等のテーブルを準備してください（分析 / research 用）。

---

使い方（主要スクリプト / CLI）
- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - オプション: --strict（警告も異常扱い）
- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き（デフォルト 60 秒）
  - 監視は KABUSYS_ENV に関わらず本番 sqlite_path を使用します（監視は常時本番 DB を監視する意図）
  - 停止: data/stop_requested.flag を作成すると監視ループは次回ポーリングで終了
- 実行エンジン起動（Execution）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を利用し data/paper_trading.db に記録して本番 DB と分離
  - 実行中は data/execution.pid に PID が書かれ、SystemMonitor はこの PID を監視してプロセス稼働を確認
  - 停止: data/stop_requested.flag を作成すると次回チェックでエンジン停止をトリガー
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - --db を省略すると環境変数 PAPER_TRADING_SQLITE_PATH またはデフォルト data/paper_trading.db を参照
- AI 系（プログラム経由で利用）
  - kabusys.ai.score_news(conn, target_date, api_key=None)  — OpenAI API キー（引数または OPENAI_API_KEY 環境変数）必須
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

注意点
- run_monitoring / run_execution は set_process_priority("high") を呼び出してプロセス優先度を上げようとします。権限により失敗する場合は警告が出ますが処理は継続します。
- stop フラグファイル:
  - data/stop_requested.flag: run_monitoring/run_execution の終了要求に利用
  - data/kill.flag: KillSwitch により作成されると ExecutionEngine に安全停止を要求
  - data/execution.pid: 実行エンジンの PID（SystemMonitor が参照）
- Paper Trading は本番 DB と分離されます（設定により PAPER_TRADING_SQLITE_PATH でパスを指定可能）。

---

環境変数（主なもの）
- 必須
  - JQUANTS_REFRESH_TOKEN: J-Quants API リフレッシュトークン
  - KABU_API_PASSWORD: kabuステーション API パスワード
- 動作モード
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DB パス
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: monitoring DB（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: paper trading 用 SQLite（デフォルト: data/paper_trading.db）
- ロギング / 実行
  - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）
  - PID_FILE_PATH: 実行エンジンの PID ファイルパス（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（"1" でクリア、開発用。デフォルト 0）
- Paper Trading 動作
  - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）
- AI
  - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）
- 監視
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒。デフォルト 60）
- LINE 通知（任意）
  - LINE_CHANNEL_ACCESS_TOKEN
  - LINE_USER_ID

---

注意すべき実装上のポイント（短評）
- .env 自動読み込み: プロジェクトルート（.git または pyproject.toml）を探索して .env/.env.local を読み込みます。テスト等で自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- Monitoring は環境にかかわらず production sqlite_path を参照します（監視対象は本番 DB を想定）。
- Paper Trading は DB を分離し、MockBroker を使って発注のシミュレーションを行います（本番口座には発注しません）。
- AI 関連では OpenAI の JSON mode を想定した応答パースとエラーハンドリング（リトライ・バックオフ）を実装済みです。

---

ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数/設定管理、自動 .env ロード
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 起動前検証 CLI
  - run_monitoring.py         — Monitoring ポーリングループ起動スクリプト
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - utils/
    - process_priority.py     — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py        — SQLite 永続化層（テーブル作成 / CRUD）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - alert_manager.py
    - kill_switch.py
    - monitoring_engine.py
  - execution/                — (注文実行関連。BrokerFactory / Engine / OrderManager 等)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - tools/
    - paper_verification_report.py

（実際のファイル・サブパッケージは上記以外にも存在する場合があります。ここでは主要なモジュールを抜粋しています。）

---

トラブルシューティング / よくある質問
- Q: .env を作ったけど validate_config でエラーが出る
  - A: 必須の環境変数（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD）を再確認してください。プレースホルダ値（*_here や your_value）をそのまま使うと警告／エラーになります。
- Q: run_monitoring で権限エラー（プロセス優先度設定）
  - A: set_process_priority は権限が必要になる場合があります。警告が出ても動作は継続します。必要なら sudo で権限を与えるか、環境に応じてスキップしてください。
- Q: AI 機能を使うときに API エラーが発生する
  - A: OPENAI_API_KEY の設定を確認。ネットワーク断や 429/5xx は内部でリトライしますが、上限を超えるとスキップされます。

---

貢献 / 開発
- コードはモジュールごとに責務が分かれています。ユニットテストはモジュール単位で run_once / pure function を活用してテストしやすい設計です。
- 新しい戦略やブローカープラグインを実装する場合は、既存のインターフェース（BrokerClientFactory, ExecutionEngine, OrderRepository など）に従うことを推奨します。

---

最後に
- 本 README はリポジトリ内の主要スクリプトとモジュールから抽出した情報をまとめたものです。詳細な設計書（PortfolioConstruction.md, StrategyModel.md 等）がプロジェクトに含まれている場合は、そちらも参照してください。必要であれば README にサンプル .env テンプレートや起動例を追記します。希望があれば教えてください。