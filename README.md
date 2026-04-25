KabuSys — README
=================

概要
----
KabuSys は日本株向けの自動売買 / 研究フレームワークです。  
このコードベースは主に次の役割を持つモジュール群で構成されています。

- 実行エンジン（ExecutionEngine）: 注文送信・リスク管理・オーダー管理を行う。
- 監視（Monitoring）: システム状態、注文状況、リスク指標を定期ポーリングしてログとアラートを出す。
- ポートフォリオ構築（Portfolio）: 候補選定、重み計算、ポジションサイズ計算など。
- リサーチ（Research）: ファクター計算（モメンタム・ボラティリティ・バリュー等）と特徴量解析。
- AI ユーティリティ: ニュースの NLP スコアリングや市場レジーム判定（OpenAI を利用）。
- ツール: ペーパートレード結果の検証レポート生成など。
- 設定管理: .env の対話的作成、起動前の設定検証 CLI。

主な特徴
--------
- 環境分離: KABUSYS_ENV により development / paper_trading / live を切替可能。ペーパートレード時は専用 SQLite DB（data/paper_trading.db）が利用され、本番 DB と分離される設計。
- 監視 & Kill Switch: 稼働率・データ鮮度・ドローダウン・ポジション上限等を監視し、条件を満たすと data/kill.flag を出力して ExecutionEngine を停止可能。
- ロギング: 統一的なログ設定ユーティリティ（コンソール + 日次ローテーションファイル出力）。
- AI 統合: OpenAI（gpt-4o-mini 想定）を使ったニュースセンチメントおよびマクロセンチメント評価機能。
- リサーチ向け DuckDB 連携: prices_daily / raw_financials 等のテーブルを利用し、因子計算や将来リターン評価を行う。
- テストしやすい設計: 純粋関数群（portfolio 等）、DB 初期化や CLI ツールでの冪等性を考慮。

セットアップ手順
----------------
1. Python 仮想環境を作成
   - 例: python -m venv .venv
   - 有効化（OS による）: source .venv/bin/activate など

2. 必要なパッケージをインストール
   - 本プロジェクトでは以下のライブラリが使われます（抜粋）:
     - duckdb
     - psutil
     - openai
     - PyYAML（config ファイル検証を行う場合に必要）
   - インストール例:
     pip install duckdb psutil openai pyyaml

   （requirements.txt がない場合は上記パッケージを個別にインストールしてください）

3. .env の作成
   - 対話式ウィザードを使って .env を生成できます:
     python -m kabusys.config_setup
   - 生成後、設定を検証:
     python -m kabusys.validate_config
     - --strict を付けると警告も失敗扱いになります。

4. データディレクトリ
   - デフォルトでは data/ 以下にファイルを配置します（logs/ はログ出力先）。
   - 必要に応じて .env で DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, LOG_DIR を変更してください。

環境変数（主なもの）
--------------------
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB, デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB, デフォルト: data/paper_trading.db）
- OPENAI_API_KEY（AI 機能を利用する場合に必要）
- LOG_LEVEL（DEBUG/INFO/...、デフォルト: INFO）
- MONITOR_POLL_INTERVAL（監視ループのポーリング間隔（秒）、デフォルト: 60）
- PAPER_FILL_MODE（paper_trading の約定モード: instant|partial|never|reject、デフォルト: instant）

使い方（主要コマンド）
--------------------

- 環境設定ウィザード（.env を生成／更新）
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  （--strict を付けると警告も失敗扱い）

- 監視ループ起動（Monitoring）
  python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書きできます（秒、デフォルト 60）。
  - 監視は Settings が指す sqlite_path（監視 DB）を使ってログを書きます。
  - 停止はプロジェクトルート/data/stop_requested.flag を作成するか、Ctrl+C。

- 実行エンジン起動（ExecutionEngine）
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録します（本番 DB と分離）。
  - 起動時に data/stop_requested.flag が存在する場合は起動せず終了します。
  - 実行中は PID ファイル（デフォルト data/execution.pid）を生成します。
  - 停止には data/stop_requested.flag を作成するか kill.flag 経由の停止判定によりエンジンを終了できます。

- Paper Trading 検証レポート生成ツール
  python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: data/paper_trading.db または環境変数 PAPER_TRADING_SQLITE_PATH

- AI 機能
  - ニュース NLP スコアリング: kabusys.ai.score_news（Python API）を呼ぶ際に OpenAI API キーが必要。
  - 市場レジーム判定: kabusys.ai.regime_detector.score_regime（OpenAI API キーが必要）

内部ユーティリティ
------------------
- ロギング: kabusys.utils.logging_setup.setup_logging(app_name="execution" 等)
  - stdout と logs/<app_name>.log（日次ローテーション）へ出力。
- プロセス優先度: kabusys.utils.process_priority.set_process_priority("high"|"normal"|"low")
- 設定読み込み: kabusys.config.Settings および settings グローバルインスタンス
  - 自動でプロジェクトルートの .env / .env.local を読み込む（無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。

ディレクトリ構成（抜粋）
----------------------
以下は src/kabusys 配下の主なファイル・モジュール構成の要約です。

- kabusys/
  - __init__.py
  - config.py                # 環境変数読み込み・Settings
  - config_setup.py          # .env 対話ウィザード
  - validate_config.py       # 起動前設定検証 CLI
  - run_monitoring.py        # Monitoring ポーリングループ起動スクリプト
  - run_execution.py         # ExecutionEngine 起動スクリプト

  - utils/
    - logging_setup.py       # 共通ログ設定
    - process_priority.py    # プロセス優先度 / CPU affinity
    - __init__.py

  - monitoring/
    - monitoring_db.py       # SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py      # システム状態・データ鮮度監視
    - risk_monitor.py        # ドローダウン・ポジション上限監視
    - kill_switch.py         # kill.flag 管理（Execution 停止トリガー）
    - monitoring_engine.py   # 各 Monitor を束ねるエンジン
    - alert_manager.py       # （アラート送信管理 — 実装参照）
    - trade_monitor.py       # 注文・約定監視（参照あり）

  - execution/
    - (ExecutionEngine, OrderManager, BrokerFactory 等 — 実装ファイル群、注文送信 / リスク管理)

  - portfolio/
    - portfolio_builder.py   # 候補選定・重み計算
    - position_sizing.py     # 株数決定・スケーリング・単元丸め
    - risk_adjustment.py     # セクターキャップ・レジーム乗数
    - __init__.py

  - research/
    - factor_research.py     # momentum / volatility / value 等のファクター計算（DuckDB）
    - feature_exploration.py # 将来リターン・IC・ランク等
    - __init__.py

  - ai/
    - news_nlp.py            # ニュースセンチメント（OpenAI 経由）
    - regime_detector.py     # マクロ+MA によるレジーム判定（OpenAI 経由）
    - __init__.py

  - tools/
    - paper_verification_report.py  # ペーパートレード検証レポート

補足と運用上の注意
------------------
- セキュリティ:
  - .env ファイルは機密情報（APIキー等）を含むため、絶対に Git へコミットしないでください（config_setup でも注意書きあり）。
- 本番運用:
  - KABUSYS_ENV=live 設定時は特に設定を慎重に確認してください（validate_config による警告あり）。
  - KILL_FLAG_CLEAR_ON_START は本番では 0 を推奨します（自動クリアは危険）。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db は安全に複数回呼べるよう設計（冪等）。既存 DB に新カラムがない場合は追加する簡易マイグレーション処理を行います。
- AI 呼び出し:
  - OpenAI API 呼び出しはリトライやフェイルセーフ（タイムアウト・5xx の場合はスキップ or 代替値）を備えていますが、APIキーや料金、レート制限には注意してください。

よくある操作例
--------------
- 監視をデフォルト（60秒間隔）で起動:
  python -m kabusys.run_monitoring

- 監視を 30 秒間隔で起動:
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- 実行エンジン（ペーパートレード）を起動:
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Paper Trading 検証レポート（過去期間）:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

ライセンス・貢献
----------------
本 README はコードベースの説明を目的としており、実際のライセンス情報や貢献手順はリポジトリのトップレベルに置かれた LICENSE / CONTRIBUTING ファイルを参照してください。

---

必要であれば、この README を英語版に翻訳したり、各モジュールの API 使い方サンプル（コード例）を追加したりできます。どの部分を詳しく補完しましょうか？