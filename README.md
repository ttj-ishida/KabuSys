# KabuSys

日本株向け自動売買システム（KabuSys）のコードベース README。  
このドキュメントはリポジトリ内の主要コンポーネント、セットアップ手順、実行方法、ディレクトリ構成を日本語でまとめたものです。

---

目次
- プロジェクト概要
- 主な機能一覧
- 前提条件 / インストール
- 環境設定 (.env) の作成
- 設定検証
- 実行方法（監視 / 実行エンジン / レポート等）
- 停止・Kill スイッチ
- ディレクトリ構成（主要ファイルの説明）
- 補足 / 注意事項

---

プロジェクト概要
- KabuSys は日本株の自動売買プラットフォーム向けのモジュール群です。
- 戦略・ポートフォリオ構築、発注エンジン（ExecutionEngine）、監視（Monitoring）、研究（factor/research）、AI を利用したニュースセンチメント評価等を含みます。
- 本リポジトリはライブラリ／CLI 群として設計され、.env による環境変数で挙動を切り替えられます（development / paper_trading / live）。

主な機能一覧
- 設定管理
  - .env の自動読み込み / 対話式ウィザード（config_setup）
  - 起動前の設定検証 CLI（validate_config）
- 実行（Execution）
  - 実際の発注処理を行う ExecutionEngine（本番 API または MockBroker でのペーパートレード）
  - 注文管理、リスク管理、リコンサイル等のコンポーネント
- 監視（Monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor による定期チェック
  - SQLite に監視ログを永続化（monitoring_db）
  - LINE による通知（AlertManager）
  - KillSwitch による安全停止（kill.flag）
- ポートフォリオ構築（純粋関数群）
  - 候補選定、重み付け、ポジションサイジング、セクター制限、レジーム係数 など
- 研究・分析
  - DuckDB を用いたファクター計算（momentum / volatility / value）
  - 特徴量探索／IC 計算等
- AI モジュール
  - ニュース記事を OpenAI でセンチメント評価し ai_scores に格納（news_nlp）
  - マクロ＋ETF 指標で市況レジーム判定（regime_detector）
- ユーティリティ
  - プロセス優先度設定、CPU affinity 設定（psutil 利用）
  - ペーパートレード検証レポート生成ツール（tools）

前提条件 / インストール
- 推奨 Python バージョン: 3.10+
  - （コードは | 型注釈等 Python 3.10+ の構文を使用）
- 主な依存ライブラリ（最低限）
  - duckdb
  - psutil
  - openai
  - requests
  - （任意）PyYAML：config/*.yaml の内容検証を行うときに必要
- インストール例（仮想環境推奨）:
  - python -m venv .venv
  - source .venv/bin/activate
  - pip install --upgrade pip
  - pip install duckdb psutil openai requests pyyaml
  - （requirements.txt が用意されている場合は pip install -r requirements.txt）

環境設定 (.env) の作成
- 対話式ウィザード:
  - python -m kabusys.config_setup
  - 実行すると .env（デフォルト: プロジェクトルート/.env）を生成・更新できます。
- 自動読み込みについて:
  - 起動時にプロジェクトルート（.git や pyproject.toml のあるディレクトリ）を探索して .env を自動読み込みします。
  - 自動ロード無効化: 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- 主要な環境変数（抜粋）
  - KABUSYS_ENV: 実行環境（development / paper_trading / live）
  - JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
  - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
  - OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
  - DUCKDB_PATH: DuckDB ファイルパス（default: data/kabusys.duckdb）
  - SQLITE_PATH: 監視 DB（monitoring.db）パス（default: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（paper_trading.db）
  - LOG_LEVEL, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID など
  - PAPER_FILL_MODE: ペーパートレード時の充足モード（instant/partial/never/reject）
  - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）

設定検証
- 起動前に設定チェックを実行できます:
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit code 1）にできます。

実行方法（主要 CLI）
- 監視ループ起動（SystemMonitor 単体実行スクリプト）
  - python -m kabusys.run_monitoring
  - 説明:
    - ポーリング間隔: 環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可（デフォルト 60 秒）。
    - 監視は Settings.env に関係なく本番の sqlite_path を使用（monitoring DB は共通管理）。
    - 実行時にプロセス優先度を "high" に設定（可能なら）。
    - プロセス停止: プロジェクトルート/data/stop_requested.flag を作成するとループが終了します。
- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 説明:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、データは paper_trading.db に記録（本番 DB と分離）。
    - 実行中はスレッドで run_session を動かします。停止フラグ（data/stop_requested.flag）を検出すると engine.stop() を呼びます。
    - PID ファイル: data/execution.pid を使用（デフォルト）。
- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB パスは環境変数 PAPER_TRADING_SQLITE_PATH（未設定時は data/paper_trading.db）。
- AI 関連（Python API として）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - DuckDB 接続を渡してニュースセンチメントを生成・ai_scores テーブルに書き込みます。
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - マクロニュース＋ETF MA 乖離から日次レジームを判定し market_regime テーブルへ書き込む関数です。
  - いずれも OPENAI_API_KEY が必要（引数で上書き可）。
- 注意: これらの API は DuckDB 接続（duckdb.connect(...)）オブジェクトを受け取る設計です。

停止・Kill スイッチ等
- stop_requested.flag
  - run_monitoring.py / run_execution.py は data/stop_requested.flag の有無をチェックし、存在時に安全終了します（これにより外部から安全に停止可能）。
- kill.flag（KillSwitch）
  - RiskMonitor 等が重大な条件（例：ドローダウン、ポジション過多）を検出した場合、KillSwitch が Settings.kill_flag_path（デフォルト data/kill.flag）へ理由を記載して書き込みます。
  - ExecutionEngine 起動処理や外部監視が kill.flag を検出して発注停止・アラートを行う設計です。
  - KillSwitch.clear() によって kill.flag を削除できます（環境変数 KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動クリアする挙動にできますが、本番では推奨されません）。

ディレクトリ構成（主要ファイルと説明）
- src/kabusys/
  - __init__.py — パッケージ定義（バージョン等）
  - config.py — 環境変数 / Settings 管理。.env 自動読み込みロジックと各種設定プロパティを提供。
  - config_setup.py — 対話式 .env ウィザード（python -m kabusys.config_setup）。
  - validate_config.py — 起動前設定検証 CLI（python -m kabusys.validate_config）。
  - run_monitoring.py — SystemMonitor のポーリングループ起動スクリプト。
  - run_execution.py — ExecutionEngine 起動スクリプト（本番/ペーパー分離）。
  - monitoring/
    - monitoring_db.py — SQLite を使った監視ログ永続化層（スキーマ初期化含む）。
    - system_monitor.py — CPU/メモリ/Disk / データ鮮度 / プロセス監視。
    - trade_monitor.py — 注文滞留・約定価格異常のチェック。
    - risk_monitor.py — ドローダウン・ポジション上限監視。
    - kill_switch.py — kill.flag 書き込みロジック。
    - monitoring_engine.py — 各モニタを束ねる実行エンジン。
    - alert_manager.py — LINE Messaging API 経由の通知ユーティリティ。
  - execution/ (実際の発注系コンポーネント群)
    - order_manager.py, order_repository.py, execution_engine.py, reconciler.py, risk_manager.py, broker_factory.py など
    - （発注/注文記録/リスク管理の中心）
  - portfolio/
    - portfolio_builder.py — 候補選定、重み付け
    - position_sizing.py — 株数計算、上限/単元丸め、aggregate cap
    - risk_adjustment.py — セクターキャップ、レジーム乗数
  - research/
    - factor_research.py — momentum / volatility / value ファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン計算、IC、統計サマリー
  - ai/
    - news_nlp.py — raw_news を OpenAI に投げて銘柄ごとにセンチメント取得 → ai_scores 書き込み
    - regime_detector.py — ETF MA 乖離 + マクロニュースで市場レジーム判定
  - tools/
    - paper_verification_report.py — ペーパートレードログの検証レポート生成
  - utils/
    - process_priority.py — psutil を使ったプロセス優先度 / CPU affinity 設定
  - その他：data/（DB ファイル / flag / pid を置く想定。git 管理除外）

補足 / 注意事項
- DB マイグレーション: monitoring_db.init_monitoring_db(...) は起動時にテーブルと既知のカラム追加を行います（冪等）。既存 DB に対してカラム追加を行う処理が含まれます。
- Paper trading（KABUSYS_ENV=paper_trading）は本番 DB と分離して動作するよう設計されています。PAPER_TRADING_SQLITE_PATH を確認してください。
- OpenAI 呼び出し部分は外部 API に依存するためレート制限・ネットワーク障害に対してリトライとフォールバック処理を備えていますが、APIキーの管理・料金に注意してください。
- .env は機密情報を含むため必ず .gitignore に入れてリポジトリにコミットしないでください（config_setup も同旨をヘルプに出力します）。
- ログレベルや監視閾値は環境変数 / config/*.yaml（プロジェクトにあれば）で調整できます。validate_config で欠損を事前チェックしてください。
- Python の依存バージョンやパッケージはプロジェクトごとに requirements.txt / poetry / pyproject.toml を用意して管理することを推奨します（本リポジトリでは該当ファイルを参照してください）。

必要に応じて README に追記します（例: サンプル .env.example、詳細な ExecutionEngine API ドキュメント、テスト手順、CI 設定等）。追加で欲しいセクションがあれば指定してください。