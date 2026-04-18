README
=====

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤のサンプル実装です。  
このコードベースは次の主要機能を持ちます:

- 注文実行エンジン（ExecutionEngine） — 本番／ペーパートレード対応
- 監視（Monitoring） — システム状態・注文状況・リスク監視、Kill Switch 連動
- ポートフォリオ構築ロジック — 候補選定、重み計算、ポジションサイズ決定
- リサーチ（Research） — ファクター計算、将来リターン、IC 計算、特徴量解析
- AI モジュール — ニュースを使ったセンチメント評価、レジーム判定（OpenAI）
- ユーティリティ群 — 設定管理、対話式.env ウィザード、ログ設定、プロセス優先度設定
- ツール群 — ペーパートレード検証レポート生成など

主要な設計方針の抜粋：
- 設定は .env または環境変数で管理（自動ロード機構あり）
- paper_trading（ペーパートレード）時は本番 DB と分離された SQLite を使用
- DuckDB を分析用途のローカルデータベースとして利用
- OpenAI 呼び出しは失敗耐性（リトライ／フォールバック）を備える

機能一覧
--------
主な機能（ファイル/モジュール単位）:

- 起動スクリプト
  - src/kabusys/run_execution.py — ExecutionEngine の起動（スレッドで実行、stop フラグ監視）
  - src/kabusys/run_monitoring.py — SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔指定）

- 設定関連
  - src/kabusys/config.py — Settings クラス（環境変数取得・検証・自動 .env 読込）
  - src/kabusys/config_setup.py — 対話式 .env 生成ウィザード
  - src/kabusys/validate_config.py — 起動前の設定検証 CLI

- 監視関連
  - src/kabusys/monitoring/monitoring_db.py — SQLite ベースの永続化層（テーブル初期化・CRUD）
  - src/kabusys/monitoring/system_monitor.py — システム状態・データ鮮度監視
  - src/kabusys/monitoring/trade_monitor.py（存在する想定） — 注文関連の監視
  - src/kabusys/monitoring/risk_monitor.py — ドローダウン・ポジション上限監視
  - src/kabusys/monitoring/kill_switch.py — kill.flag による停止シグナル
  - src/kabusys/monitoring/monitoring_engine.py — 各監視を束ねるエンジン

- Execution / 発注関連（実装ファイルは execution ディレクトリ参照）
  - broker_factory, execution_engine, order_manager, order_repository, reconciler, risk_manager など

- ポートフォリオ構築
  - src/kabusys/portfolio/portfolio_builder.py — 候補選定・重み計算
  - src/kabusys/portfolio/position_sizing.py — 株数算出・制約処理
  - src/kabusys/portfolio/risk_adjustment.py — セクター上限・レジーム乗数

- リサーチ
  - src/kabusys/research/factor_research.py — Momentum/Value/Volatility 等のファクター計算（DuckDB）
  - src/kabusys/research/feature_exploration.py — 将来リターン、IC、統計サマリ

- AI
  - src/kabusys/ai/news_nlp.py — raw_news をまとめて OpenAI に投げ、銘柄ごとのセンチメント算出
  - src/kabusys/ai/regime_detector.py — ETF の MA とマクロニュースで市場レジーム判定

- ユーティリティ
  - src/kabusys/utils/logging_setup.py — 一貫したログ設定（stdout + 日次ローテート）
  - src/kabusys/utils/process_priority.py — プロセス優先度・CPU affinity 設定ユーティリティ

要件
----
推奨環境:
- Python 3.9+
- 必須ライブラリ（一例）:
  - duckdb
  - psutil
  - openai
- 任意 / 解析用:
  - PyYAML（validate_config の YAML 検証に使用。未インストール時は検証が一部スキップされる）
- その他: SQLite は標準ライブラリで利用可能

セットアップ手順
----------------
1. リポジトリをクローンし、作業ディレクトリに移動:
   - git clone ... && cd <repo>

2. 仮想環境を作成して有効化（任意だが推奨）:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール:
   - pip install duckdb psutil openai
   - （オプション）PyYAML を使う場合: pip install pyyaml

   ※ 開発向けに requirements.txt がある場合はそちらを使用してください。

4. .env の準備:
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - あるいはプロジェクトルートに .env を手動で作成。
   - 自動読み込み: src/kabusys/config.py がプロジェクトルート（.git または pyproject.toml の存在箇所）を検出して .env/.env.local を自動で読み込みます。
   - 自動読み込みを無効化する場合:
     - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

5. 設定検証:
   - python -m kabusys.validate_config
   - 警告も FAIL としたい場合: python -m kabusys.validate_config --strict

6. データディレクトリの準備:
   - デフォルトの DB・ログパスはプロジェクト内の data/ と logs/（config で上書き可）
   - 必要に応じてディレクトリを作成（多くは起動時に自動作成される）

基本的な使い方
--------------

環境変数の主要項目（抜粋）
- KABUSYS_ENV: 実行環境（development | paper_trading | live） — デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API 用（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード時の SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/...）
- OPENAI_API_KEY: OpenAI を使う機能で参照

起動 / 実行例
- ExecutionEngine を起動（フォアグラウンド）:
  - python -m kabusys.run_execution
  - 補足: KABUSYS_ENV が paper_trading の場合、MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します。本番/ペーパーで DB を分離しています。

- SystemMonitor を単独で起動（ポーリングループ）:
  - python -m kabusys.run_monitoring
  - ポーリング間隔はデフォルト 60 秒、環境変数 MONITOR_POLL_INTERVAL で上書き可能（例: export MONITOR_POLL_INTERVAL=30）
  - run_monitoring は monitoring 用 DB 接続に常に本番 sqlite_path を使用します（意図的挙動）

- 対話式 .env ウィザード:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - --strict を付けると warning でも exit(1)

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定: --db PATH または 環境変数 PAPER_TRADING_SQLITE_PATH を設定

- AI / リサーチ API の利用（プログラム内から）:
  - ニューススコアリング: from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key=None)
  - レジーム判定: from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key=None)
  - ファクター計算: from kabusys.research import calc_momentum, calc_value, calc_volatility

監視・停止フラグの仕組み
- stop_requested.flag:
  - run_monitoring / run_execution はプロジェクトの data/stop_requested.flag をチェックして起動中のループ／スレッドを終了します（手動で停止用フラグを置く運用に対応）。
- Kill Switch:
  - kill.flag（デフォルト: data/kill.flag）を書き込むことで ExecutionEngine に停止を要求できます（KillSwitch により書き込まれる）。ExecutionEngine は起動時に kill.flag をチェック／必要に応じてクリアする設定があります（KILL_FLAG_CLEAR_ON_START）。

ログ
- ログ設定は kabusys.utils.logging_setup.setup_logging で統一されています。
- 出力先:
  - コンソール (stdout)
  - 日次ローテートファイル: logs/<app_name>.log（デフォルト logs/、30 日保持）
- ログレベルは引数・環境変数 LOG_LEVEL で制御可能

注意点 / 運用上の留意事項
- KABUSYS_ENV=live の場合は設定を慎重に（LINE 通知設定や Kill Switch の自動クリア等に注意）
- OpenAI など外部 API の呼び出しには API キーと課金が必要。API の失敗はフォールバックする設計ですが、想定通りの結果が得られない可能性があります。
- paper_trading は本番 DB と分離する設計（PAPER_TRADING_SQLITE_PATH を使用）
- .env ファイルは絶対にリポジトリにコミットしないでください（config_setup でも注意喚起あり）

ディレクトリ構成
----------------
以下は主要ファイル／ディレクトリの概観（src/kabusys 以下）:

- __init__.py
- config.py                    — 環境変数 / Settings
- config_setup.py              — 対話式 .env ウィザード
- validate_config.py           — 設定検証 CLI
- run_execution.py             — ExecutionEngine 起動スクリプト
- run_monitoring.py            — SystemMonitor 起動スクリプト

- utils/
  - logging_setup.py           — ログ設定ユーティリティ
  - process_priority.py        — プロセス優先度 / CPU affinity

- monitoring/
  - monitoring_db.py           — SQLite テーブル初期化・永続化レイヤ
  - system_monitor.py          — システム状態監視
  - risk_monitor.py            — ドローダウン・ポジション上限監視
  - kill_switch.py             — kill.flag 管理
  - monitoring_engine.py       — 監視エンジン（複数モニタ束ねる）
  - trade_monitor.py           — 注文関連監視（コードベース参照）

- execution/                   — ExecutionEngine 周辺（broker/engine/order 等）
  - broker_factory.py
  - execution_engine.py
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py
  - ...（詳細は各ファイル参照）

- portfolio/
  - portfolio_builder.py       — 候補・重み
  - position_sizing.py         — 株数算出
  - risk_adjustment.py         — セクター上限・レジーム乗数

- research/
  - factor_research.py         — ファクター計算（DuckDB）
  - feature_exploration.py     — 将来リターン・IC・統計

- ai/
  - news_nlp.py                — ニュース NLP スコアリング（OpenAI）
  - regime_detector.py         — レジーム判定（OpenAI）

- tools/
  - paper_verification_report.py — ペーパートレード検証レポート

付録: .env に含める代表的なキー（例）
- KABUSYS_ENV=development
- JQUANTS_REFRESH_TOKEN=your_token_here
- KABU_API_PASSWORD=your_password_here
- KABU_API_BASE_URL=http://localhost:18080/kabusapi
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
- OPENAI_API_KEY=sk-...
- LOG_LEVEL=INFO
- LINE_CHANNEL_ACCESS_TOKEN=
- LINE_USER_ID=
- KILL_FLAG_CLEAR_ON_START=0

最後に
------
この README はコードベース内の主要部分を紹介する簡易ドキュメントです。実際の運用や拡張時は個々のモジュール（特に execution や broker 関連、AI 呼び出し箇所）の実装とコメントを参照してください。追加で「導入手順を systemd ユニット化する方法」や「テストランの手順」などが必要であれば、用途に合わせた追補ドキュメントを作成します。