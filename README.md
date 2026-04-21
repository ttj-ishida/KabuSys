KabuSys — 日本株自動売買システム (コードベース README)
=================================================

概要
----
KabuSys は日本株の自動売買・リサーチ・監視を目的にした Python パッケージ群です。本リポジトリには以下の主要機能が含まれます。
- 発注エンジン（ExecutionEngine）とその起動スクリプト
- 監視（System / Trade / Risk）コンポーネントと監視ループ
- ペーパートレード用の分離DBサポート
- ポートフォリオ構築・ポジションサイズ決定ロジック（純粋関数）
- DuckDB を使ったファクター計算 / リサーチモジュール
- ニュースを LLM（OpenAI）でスコア化する AI モジュール
- 設定ウィザード・設定検証ツール・レポートツール
- ロギング・プロセス優先度設定ユーティリティ等のユーティリティ群

主な機能一覧
------------
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV=paper_trading 時は MockBroker を使用して data/paper_trading.db に記録）
  - run_monitoring.py: SystemMonitor をポーリングして監視ログを記録（MONITOR_POLL_INTERVALで間隔上書き可）
- 設定管理
  - config_setup.py: .env の対話式ウィザードで初期作成/更新
  - validate_config.py: .env と config/*.yaml の起動前検証 CLI（--strict オプションあり）
- 監視 / Kill Switch
  - monitoring/*: system_monitor, trade_monitor, risk_monitor, kill_switch, monitoring_engine, monitoring_db（SQLite）
  - kill.flag を書くことで ExecutionEngine に停止信号を送れる
- 発注・リスク管理（execution パッケージ、起動ロジックは run_execution.py）
- ポートフォリオ構築（portfolio パッケージ）
  - 候補選定、等重/スコア重み、セクター上限、レジーム乗数、株数計算（単元丸め、上限・スケールダウン処理）
- リサーチ（research パッケージ）
  - モメンタム / ボラティリティ / バリュー ファクター計算
  - 将来リターン計算・IC 計算・統計サマリ等
- AI（ai パッケージ）
  - news_nlp.score_news: raw_news をまとめて OpenAI に投げ、ai_scores テーブルへ書き込む
  - regime_detector.score_regime: ETF とマクロニュースを合成して market_regime を算出（OpenAI 使用）
- ツール
  - tools/paper_verification_report.py: ペーパートレード DB の検証レポート生成

セットアップ手順
----------------
前提
- Python 3.10 以上（型ヒントに | 演算子を利用しているため）
- SQLite（標準で付属）
- 任意で DuckDB, OpenAI SDK 等（下記参照）

推奨パッケージ（最低限）
- duckdb
- psutil
- openai
- PyYAML（設定検証で YAML チェックを有効にする場合）

例: pip によるインストール
- まず venv を作成して有効化することを推奨します。
  - python -m venv .venv
  - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
- 必要パッケージをインストール:
  - pip install duckdb psutil openai PyYAML

環境変数 / .env
- 起動前に必須の環境変数を設定する必要があります（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）。
- 対話式で .env を作るには:
  - python -m kabusys.config_setup
- 設定を検証するには:
  - python -m kabusys.validate_config
- 主な環境変数（抜粋）
  - JQUANTS_REFRESH_TOKEN（必須）
  - KABU_API_PASSWORD（必須）
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
    - paper_trading: MockBroker を使用し data/paper_trading.db に記録（本番 DB と分離）
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
  - LOG_LEVEL（デフォルト: INFO）
  - OPENAI_API_KEY（AI 機能を使う場合に必要）
  - MONITOR_POLL_INTERVAL（run_monitoring 用の秒数。デフォルト 60。0以下は無効としてデフォルトに戻る）

注意事項
- .env は決してリポジトリに含めないでください（config_setup のヘッダにも注意喚起あり）。
- KABUSYS_ENV=live の場合は本番運用に関する注意喚起や Kill Switch の設定を必ず確認してください。

使い方（起動例）
----------------
基本的な起動はパッケージモジュールとして実行します。

- ExecutionEngine（発注エンジン）起動
  - python -m kabusys.run_execution
  - paper_trading 環境（ペーパートレード）:
    - KABUSYS_ENV=paper_trading を設定すると MockBrokerClient を使用し、データは data/paper_trading.db に保存されます。

- Monitoring（監視ループ）起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を ENV で上書き: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- 設定ウィザード / 検証
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config
    - --strict を付けると警告も FAIL 扱い（exit code 1）

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH または --db で上書き可）

- ライブラリとしての利用例（コードから）
  - ポートフォリオ関数を使用:
    - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_position_sizes
  - リサーチ:
    - from kabusys.research import calc_momentum, calc_volatility, calc_value
  - AI ニューススコア:
    - from kabusys.ai import score_news
    - score_news(conn, target_date, api_key="...")  （DuckDB 接続を渡す）

ログ・PID・停止フラグ
- ログはデフォルト logs/ ディレクトリへ出力され、日次ローテーション（30日保持）です。ログ設定は kabusys.utils.logging_setup.setup_logging で行われます。
- 実行中プロセスの PID は data/execution.pid（Settings.pid_file_path で指定）などに書き込まれます。
- 停止制御:
  - data/stop_requested.flag : run_monitoring/run_execution の内部ループがこのファイルの存在を見て終了します（手動停止用）。
  - data/kill.flag : KillSwitch が作成（実行停止トリガー）。ExecutionEngine は起動時やループ中にこのフラグを参照して停止します。

ディレクトリ構成（主要ファイル）
----------------------------
以下は src/kabusys 以下の主要ファイル／ディレクトリと簡単な説明です。

- kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数/.env の自動読み込みと Settings クラス（各種設定取得）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - utils/
    - logging_setup.py — 一貫したログ設定（コンソール＋日次ファイル）
    - process_priority.py — プラットフォーム抽象化したプロセス優先度・CPU affinity 設定
  - monitoring/
    - monitoring_db.py — SQLite による監視ログ永続化層（テーブル初期化 / DB 操作）
    - system_monitor.py — CPU/メモリ/ディスク/データ鮮度/プロセス存在監視
    - trade_monitor.py —（存在）注文滞留・価格異常検出（ファイルに断片あり）
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - kill_switch.py — Kill Switch の評価と flag 書き込み
    - monitoring_engine.py — 複数 monitor を束ねるループ（テスト用 run_once / 本番 run）
    - alert_manager.py —（存在）通知管理（LINE など）
  - portfolio/
    - portfolio_builder.py — 候補選定 / ウェイト計算
    - position_sizing.py — 株数算出・スケーリング・単元丸め
    - risk_adjustment.py — セクター上限 / レジーム乗数
  - research/
    - factor_research.py — Momentum/Volatility/Value ファクター計算（DuckDB 使用）
    - feature_exploration.py — 将来リターン計算、IC、統計サマリ
  - ai/
    - news_nlp.py — raw_news を OpenAI に投げて ai_scores を作成（バッチ・リトライ・バリデーション実装）
    - regime_detector.py — ETF + マクロニュースを LLM で評価して market_regime を算出
  - monitoring/*.py, execution/*.py, data/* など — 発注やデータパイプラインの他モジュール（主要ロジック）

開発者向けメモ / 実装上の注意
---------------------------
- Settings は .env 自動ロードを行います（プロジェクトルートは .git または pyproject.toml で検出）。テスト等で自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- run_monitoring は MONITOR_POLL_INTERVAL 環境変数で間隔を変更できます（デフォルト 60 秒）。
- Monitoring は常に本番用 sqlite_path を参照します（監視ログは環境に依存せず本番 DB パスへ格納される設計）。
- run_execution は KABUSYS_ENV=paper_trading の場合、paper_sqlite_path を用いて DB を分離します（data/paper_trading.db がデフォルト）。
- AI 機能は OpenAI SDK（openai）に依存し、API キーの設定が必要です。API 呼び出し部はリトライとレスポンスバリデーションを備えていますが、本番運用時のコスト・レート制限を計画してください。
- ローカル/開発環境でのテストを容易にするため、ペーパートレードモードや監視・停止フラグの仕組みが実装されています。実運用前に validate_config.py を実行して設定を確認してください。

ライセンス / 貢献
-----------------
- この README ではライセンスファイルは言及していません。実際のプロジェクトでは LICENSE ファイルを置き、運用／配布方針を明記してください。
- コントリビューションを行う場合は、ユニットテスト、ドキュメント、設定検証を追加してください。

補足・問い合わせ
-----------------
README に記載のない機能や具体的な API（ExecutionEngine の詳細、OrderRepository、BrokerFactory の実装など）については該当ソースファイルをご参照ください。必要なら README を拡張して使用例や図（アーキテクチャ図、DB スキーマ）を追加します。どの情報が欲しいか教えてください。