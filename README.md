KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株向けの自動売買・リサーチ基盤（KabuSys）の一部実装です。  
ここに含まれるモジュールは、戦略・ポートフォリオ構築、発注エンジン（ExecutionEngine）、監視（Monitoring）、AI によるニュース解析などを提供します。

主な目的
- 日次リサーチ（ファクター計算 / 特徴量解析）
- ポートフォリオ構築（候補選定・重み付け・株数算出）
- 発注エンジン（本番／ペーパートレード分離）
- システム監視・Kill Switch（稼働監視・異常検知→発注停止）
- ニュース NLU を用いたセンチメント評価（OpenAI API 利用）
- ペーパートレード検証用レポート生成

機能一覧
- 環境設定ウィザード（.env の対話的生成）: kabusys.config_setup
- 起動前設定検証ツール（.env / config/*.yaml のチェック）: kabusys.validate_config
- ExecutionEngine 起動スクリプト（本番 / ペーパー分離）: run_execution.py
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し data/paper_trading.db を利用
  - 停止は data/stop_requested.flag / data/kill.flag によるフラグ操作で制御
- Monitoring（システム・注文・リスク監視）起動スクリプト: run_monitoring.py
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き可能（デフォルト 60 秒）
  - 監視は常に本番用 sqlite_path を参照して記録（環境に依らず）
- MonitoringDB（SQLite）: system_status、trade_logs、positions、risk_logs、dashboard テーブルの管理と永続化
- Risk モニタ（ドローダウン / ポジション上限監視）と KillSwitch（条件を満たしたら data/kill.flag を書く）
- Portfolio モジュール（選定 / 等分／スコア加重 / リスク調整 / ポジションサイズ算出）
- Research モジュール（ファクター計算: momentum/value/volatility、将来リターン、IC 計算、統計）
- AI モジュール
  - news_nlp: ニュース記事を集約して OpenAI（gpt-4o-mini）でセンチメント評価し ai_scores に書き込む
  - regime_detector: ETF（1321）MA200 とマクロニュースで市場レジーム判定
- tools.paper_verification_report: ペーパートレード DB を読み検証レポートを生成

セットアップ手順（開発／ローカル実行）
1. Python 環境
   - Python 3.9+ を推奨（duckdb / psutil 等を使用）
   - 必要なパッケージ例（pip インストール）:
     - duckdb
     - psutil
     - openai
     - PyYAML（config yaml の検証を行う場合）
   - 例:
     pip install duckdb psutil openai PyYAML

2. プロジェクトルートの検出と .env 自動読み込み
   - モジュールは .git または pyproject.toml を基準にプロジェクトルートを自動検出します。
   - 実行時はデフォルトでプロジェクトルートの .env（および .env.local）を自動読み込みします。
   - 自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

3. 環境変数（必須）
   - JQUANTS_REFRESH_TOKEN（必須）
   - KABU_API_PASSWORD（必須）
   - OPENAI_API_KEY（AI 機能を使う場合、news_nlp/regime_detector に必要）
   - その他（任意／デフォルトあり）:
     - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB, デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB, デフォルト: data/paper_trading.db）
     - LOG_LEVEL（デフォルト: INFO）
     - LOG_DIR（デフォルト: logs/）
     - PAPER_FILL_MODE（paper_trading の MockBroker の fill モード: instant/partial/never/reject）

4. .env の作成（推奨）
   - 対話式ウィザード:
     python -m kabusys.config_setup
   - ウィザードは .env を生成／更新します。生成後は必ず設定検証を行ってください。

5. 設定検証
   - .env と config/*.yaml（存在する場合）をチェック:
     python -m kabusys.validate_config
   - 警告を FAIL とするには --strict を付与:
     python -m kabusys.validate_config --strict

使い方（主要 CLI / スクリプト）
- 監視ループ起動（ロギング設定、プロセス優先度設定含む）:
  python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（例: MONITOR_POLL_INTERVAL=30）
  - 停止: プロジェクトルート/data/stop_requested.flag ファイルを作成すると次回ループで終了

- ExecutionEngine 起動:
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は paper_trading DB（data/paper_trading.db）を使用し、MockBrokerClient が使われます
  - 起動前に data/stop_requested.flag が存在する場合は起動しません
  - 実行中は data/execution.pid が作成されます（PID ファイル）

- ペーパートレード検証レポート生成:
  python -m kabusys.tools.paper_verification_report
  オプション:
    --from YYYY-MM-DD 期間開始日
    --to   YYYY-MM-DD 期間終了日
    --db PATH             DB パス（--db > 環境変数 PAPER_TRADING_SQLITE_PATH > デフォルト）

- AI スコアリング（モジュール呼び出し例）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - どちらも OPENAI_API_KEY を渡すか環境変数で設定してください

ログ
- ログ設定ユーティリティ: kabusys.utils.logging_setup.setup_logging
  - デフォルトで stdout（StreamHandler）と logs/<app_name>.log（TimedRotatingFileHandler、日次、30日保持）を設定
  - LOG_DIR, LOG_LEVEL 環境変数で上書き可能
  - ログディレクトリの作成に失敗した場合はファイル出力をスキップしてコンソールのみで動作

プロセス制御 / フラグファイル
- 停止要求（run_monitoring / run_execution が監視するファイル）:
  - data/stop_requested.flag — 監視ループ・ExecutionEngine が検知して停止
- Kill Switch（自動停止トリガ）:
  - data/kill.flag — KillSwitch により書き込まれ、ExecutionEngine は起動時にこのファイルを確認
  - Settings.kill_flag_clear_on_start が 1 の場合は起動時に自動クリア（本番では 0 推奨）

注意点 / 運用上の留意事項
- run_monitoring は監視ログとして sqlite_path（デフォルト data/monitoring.db）を使用します。Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を用いる設計です。
- run_execution は paper_trading の場合に専用 DB を使い本番 DB と完全分離します。
- OpenAI API を利用する機能は API レート制限やネットワークエラーに対しリトライを実装していますが、API キーの管理には注意してください。
- KABUSYS_ENV=live を設定する場合は設定検証（validate_config）と LINE 通知設定等を十分に確認してください。validate_config は live の場合に特別な警告を出します。
- .env は機密情報を含むので Git にコミットしないでください（config_setup.py の出力にも注意書きあり）。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理（自動 .env 読み込み）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_monitoring.py        — Monitoring ポーリングループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py       — 共通ロギング設定
    - process_priority.py    — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py       — SQLite テーブル初期化・永続化 API
    - monitoring_engine.py   — 各 Monitor を束ねる実行エンジン
    - system_monitor.py      — システム状態 / データ鮮度監視
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — Kill Switch フラグ書き込みロジック
    - (その他: trade_monitor, alert_manager 等のモジュールが連携)
  - execution/               — 発注エンジン関連（BrokerFactory, ExecutionEngine 等）
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み計算
    - position_sizing.py     — 株数算出・リスク制限
    - risk_adjustment.py     — セクター制限・レジーム乗数
  - research/
    - factor_research.py     — モメンタム・ボラティリティ・バリュー等の計算
    - feature_exploration.py — 将来リターン・IC・統計サマリー等
  - ai/
    - news_nlp.py            — ニュース NLP による銘柄別スコア算出
    - regime_detector.py     — 市場レジーム判定（MA200 + マクロセンチメント）
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成スクリプト

サンプル .env（最低限）
- .env.example を参考に設定してください。最低限必要なキー:
  JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
  KABU_API_PASSWORD=your_kabu_api_password
  KABUSYS_ENV=development
  OPENAI_API_KEY=sk-...

よく使うコマンドまとめ
- .env 作成（対話式）:
  python -m kabusys.config_setup
- 設定検証:
  python -m kabusys.validate_config
- 監視起動:
  MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
- Execution 起動:
  python -m kabusys.run_execution
- ペーパー検証レポート:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

最後に
- 本 README はコードベースから抽出した動作仕様の抜粋です。さらに詳細な設計思想や API 仕様、DB スキーマの説明は個別ドキュメント（PortfolioConstruction.md, StrategyModel.md 等）を参照してください。
- この README の内容をプロジェクトの README.md として使用する場合は、実際の運用環境に合わせてパス・コマンド・依存ライブラリの欄を補完してください。