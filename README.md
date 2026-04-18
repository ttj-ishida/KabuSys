README
=====

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤です。  
主な目的は「戦略のリサーチ・ファクター計算」「ポートフォリオ構築」「発注エンジン（本番 / ペーパートレード）」「監視・アラート」「AI を使ったニュース評価」などを統合して安全に運用することです。

本リポジトリは純粋関数的なポートフォリオ構築ユーティリティ、DuckDB を用いたリサーチ、SQLite ベースの監視ログ、ExecutionEngine 起動スクリプト、監視ループ、AI（OpenAI）連携モジュール等を含みます。

主な機能
--------
- 環境設定ウィザード（.env を対話的に作成・更新）: kabusys.config_setup
- 設定検証 CLI（.env / config/*.yaml のチェック）: kabusys.validate_config
- ExecutionEngine 起動スクリプト（本番・ペーパートレード切替）: kabusys.run_execution
  - KABUSYS_ENV=paper_trading のとき MockBrokerClient を用い、paper_trading 用 SQLite に記録して本番 DB と分離
- 監視ループ（SystemMonitor をポーリング）: kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数で間隔を変更可能（デフォルト 60 秒）
  - 監視は本番 sqlite_path を使用（環境に依らず）
- 監視永続化層（SQLite ベース）: kabusys.monitoring.monitoring_db
- Risk / Trade / System 各種モニタ・KillSwitch 実装
- Paper Trading 検証レポート生成ツール: kabusys.tools.paper_verification_report
- ファクター計算（Momentum / Volatility / Value 等）: kabusys.research.factor_research
- 特徴量解析ユーティリティ（forward returns, IC, summary 等）: kabusys.research.feature_exploration
- ポートフォリオ構築ユーティリティ
  - 候補選定 / 等重・スコア重み計算: kabusys.portfolio.portfolio_builder
  - ポジションサイズ計算（リスクベース等）: kabusys.portfolio.position_sizing
  - セクター制限やレジーム乗数: kabusys.portfolio.risk_adjustment
- ニュース NLP（OpenAI を使った銘柄センチメント付与）: kabusys.ai.news_nlp
- 市場レジーム判定（ETF MA とマクロニュースを合成して bull/neutral/bear を判定）: kabusys.ai.regime_detector
- 共通ユーティリティ
  - ログ設定: kabusys.utils.logging_setup
  - プロセス優先度 / CPU affinity 設定: kabusys.utils.process_priority
- 設定読み込み: kabusys.config（.env / .env.local の自動ロード機構あり）

セットアップ手順
----------------
前提:
- Python 3.9+ を推奨（duckdb, psutil, openai 等が必要）
- 仮想環境の利用を推奨

1. リポジトリをクローン / ワークツリーに入る
   - 例: git clone ... && cd repo

2. 仮想環境作成 / 有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS)
   - .venv\Scripts\activate     (Windows)

3. 必要パッケージをインストール
   - pip install duckdb psutil openai
   - 検証用に PyYAML があると config/*.yaml の内容検証が可能:
     - pip install pyyaml

4. .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは .env.example を参考に手動作成
   - 自動ロード: デフォルトでプロジェクトルートの .env と .env.local が読み込まれます。
     - 自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

5. 設定検証
   - python -m kabusys.validate_config
   - リスクが高い本番チェックを厳密に行う場合:
     - python -m kabusys.validate_config --strict

6. DB 初期化は起動スクリプトが行います（init_monitoring_db を実行）。必要に応じて data ディレクトリを作成してください。

主要な環境変数（代表例）
------------------------
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（ai モジュールで使用）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring 用）
- PAPER_FILL_MODE: ペーパートレードの約定挙動（instant, partial, never, reject）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（1/0、本番は 0 推奨）

使い方（起動・コマンド例）
-------------------------
- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine を起動（本番またはペーパートレード）
  - python -m kabusys.run_execution
  - 注意: 起動前に stop フラグ（data/stop_requested.flag）があると起動せず終了

- 監視ループを起動
  - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
  - 監視は Settings.sqlite_path（監視 DB）を使用します（env に依存しない）

- Paper Trading 検証レポート出力
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定: --db PATH（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI 関連（プログラムから呼び出す）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - OpenAI API キーが必要（環境変数 OPENAI_API_KEY または引数）

停止・制御
-----------
- 実行中の Monitoring/Execution の停止には以下の仕組みが使われます:
  - プロジェクトルート data/stop_requested.flag を作成すると、run_monitoring / run_execution のループが検知して停止します（スクリプト側でチェック）。
  - KillSwitch は監視ロジックから data/kill.flag を書き込み、ExecutionEngine の停止を誘発します。kill.flag の自動クリア設定は .env の KILL_FLAG_CLEAR_ON_START で制御。

ログ
---
- 共通のログ設定ユーティリティ: kabusys.utils.logging_setup.setup_logging
  - デフォルトで stdout と logs/<app_name>.log に日次ローテーションで出力（30日保持）
  - LOG_DIR 環境変数でログディレクトリを変更可

ディレクトリ構成（主要ファイル）
------------------------------
(src/kabusys 以下の主要モジュール)
- __init__.py
- config.py                       — 環境変数・自動 .env ロード・Settings クラス
- config_setup.py                 — .env 対話式ウィザード
- validate_config.py              — 起動前設定検証 CLI

- run_execution.py                — ExecutionEngine 起動スクリプト（本番 / ペーパートレード分離）
- run_monitoring.py               — SystemMonitor ポーリングループ起動スクリプト

- utils/
  - logging_setup.py               — 共通ロギング設定
  - process_priority.py            — プロセス優先度 / CPU affinity 設定

- monitoring/
  - monitoring_db.py               — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py              — システム状態 / データ鮮度監視
  - trade_monitor.py               — （売買監視ロジック。実装あり）※（ファイル存在）
  - risk_monitor.py                — ドローダウン・ポジション上限監視
  - kill_switch.py                 — kill.flag 書き込みロジック
  - monitoring_engine.py           — 各 Monitor を束ねる

- execution/                       — Execution エンジン関連（BrokerFactory, Engine, OrderManager, Reconciler, RiskManager 等）
  - execution_engine.py
  - broker_factory.py
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py
  （詳細は該当ファイルを参照）

- portfolio/
  - portfolio_builder.py           — 候補選定 / 等重・スコア重み
  - position_sizing.py             — 株数決定・aggregate cap ロジック
  - risk_adjustment.py             — セクターキャップ・レジーム乗数

- research/
  - factor_research.py             — momentum/volatility/value 等の DuckDB ベース計算
  - feature_exploration.py         — 将来リターン / IC / summary 等の解析ユーティリティ
  - __init__.py

- ai/
  - news_nlp.py                    — ニュースを LLM で評価して ai_scores に書き込む（OpenAI）
  - regime_detector.py             — ETF MA + マクロニュースでレジーム判定（OpenAI）
  - __init__.py

- tools/
  - paper_verification_report.py   — Paper Trading の検証レポート生成スクリプト

- monitoring_db / data/
  - data/...                       — デフォルトで使用される DB / PID / flag ファイル (data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db, data/execution.pid, data/kill.flag, data/stop_requested.flag 等)

注意事項・ベストプラクティス
---------------------------
- 本番運用時は KABUSYS_ENV=live を設定し、LINE 等の通知設定を確認してください（validate_config は live の場合に注意喚起を行います）。
- .env ファイルは機密情報を含みます。絶対に Git にコミットしないでください（config_setup でもヘッダにその旨を記載）。
- OpenAI の呼び出しは課金対象です。テスト時はモック／パラメータ走査に注意してください（news_nlp._call_openai_api は unittest.mock.patch で差し替え可能）。
- run_monitoring は監視 DB（Settings.sqlite_path）を環境にかかわらず参照します。監視と実行の DB を明確に分けたい場合は設定を調整してください。
- Paper Trading を完全に本番と分離するため、PAPER_TRADING_SQLITE_PATH を使ってペーパートレード専用 DB を指定します。
- レジーム判定や NLP の呼び出しは外部 API の不安定性を考慮してフェイルセーフ（失敗時に中立化）設計になっていますが、実運用ではログとアラートを欠かさず確認してください。

トラブルシューティング
-----------------------
- validate_config が PyYAML のインポート失敗を警告します → PyYAML をインストールすると config/*.yaml の検証が行えます
- ログファイルが作成されない場合は LOG_DIR 権限やディスク容量を確認してください。logging_setup は失敗時にコンソールログのみで継続します
- psutil の一部機能は権限不足で失敗することがあります（プロセス優先度変更など）。警告ログを確認してください

ライセンス・貢献
----------------
（この README では記載なし。必要に応じてプロジェクトに合わせて追加してください）

以上。プロジェクトの詳細や各モジュールのさらに詳しい使い方はソースコード内のドキュメンテーション（docstring）を参照してください。必要であれば README を拡張してセットアップ例、CI 設定、デプロイ手順などを追加します。