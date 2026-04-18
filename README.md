KabuSys
=======

日本株向けの自動売買 / リサーチ用ライブラリ兼実行フレームワークです。  
このリポジトリには、実行エンジン（ExecutionEngine）、監視コンポーネント、ポートフォリオ構築、ファクター計算、AI を用いたニュースセンチメント評価など、運用に必要な主要機能が含まれます。

主な特徴
-------
- Execution（発注エンジン）
  - 実際のブローカー接続かペーパートレード（分離された SQLite DB）を環境で切り替え可能
  - リスク管理（ポジション上限・ドローダウン等）を内蔵
- Monitoring（監視）
  - システム稼働状況、データ鮮度、注文ログ等のポーリング監視
  - Kill Switch（フラグファイルによる ExecutionEngine 停止）
  - 監視ログは SQLite に永続化
- Portfolio（銘柄選定・配分・数量計算）
  - 候補選定、等金額/スコア加重、リスクベースのポジションサイズ計算
  - セクター上限やレジーム乗数の調整をサポート
- Research（ファクター計算・特徴量探索）
  - Momentum / Volatility / Value 等のファクターを DuckDB 上で計算
  - 将来リターン、IC 計算、統計サマリー等のユーティリティ
- AI（ニュース NLP / レジーム判定）
  - OpenAI（gpt-4o-mini 等）でニュースのセンチメント評価 → ai_scores に格納
  - マクロニュース + ETF の MA を統合して市場レジームを判定
  - API 呼び出しは堅牢化（リトライ、フォールバック）
- ツール
  - ペーパートレード検証レポート生成スクリプトなど

前提 / 必要なライブラリ
-----------------------
推奨 Python バージョン: 3.10+（型注釈とモダンな構文を利用しています）

主な依存:
- duckdb
- psutil
- openai
- （オプション）PyYAML（config/*.yaml の検証に使用）

インストール例（開発向け）
- 仮想環境を作成・有効化
- 必要パッケージをインストール（プロジェクトに requirements ファイルがある場合はそちらを使用）
  - 例:
    pip install duckdb psutil openai PyYAML

セットアップ手順
--------------
1. プロジェクトルートに移動（.git / pyproject.toml を基準に自動検出します）。
2. .env を作成する（対話式ウィザードを推奨）:
   python -m kabusys.config_setup
   - ウィザードは J-Quants トークンや kabu API パスワード等の基本設定を対話式で作成します。
   - .env は絶対にバージョン管理にコミットしないでください。
3. 設定検証:
   python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

主な環境変数（抜粋）
-------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (AI 機能使用時に必要)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト development
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (監視 DB、デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB、デフォルト: data/paper_trading.db)
- LOG_LEVEL (DEBUG/INFO/...)
- LOG_DIR (ログ保存先、デフォルト logs/)
- MONITOR_POLL_INTERVAL (監視ポーリング間隔秒、デフォルト 60)
- KILL_FLAG_CLEAR_ON_START (起動時に kill.flag を自動クリアするか、0/1)

使い方（コマンド）
-----------------
- 対話式 .env 作成
  python -m kabusys.config_setup

- 設定の静的検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- 実行エンジン起動（Execution）
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使用され、ペーパートレード用 DB（PAPER_TRADING_SQLITE_PATH）に注文ログを記録します。
  - 起動時に data/stop_requested.flag があると起動せず終了します。
  - 実行中は data/execution.pid が使用されます（Engine が PID ファイルを管理）。

- 監視ループ起動（Monitoring）
  python -m kabusys.run_monitoring
  - デフォルトのポーリング間隔は 60 秒。MONITOR_POLL_INTERVAL 環境変数で上書き可能（秒）。
  - 監視は常に本番用の sqlite_path を使用（環境にかかわらず）。
  - 停止は project_root/data/stop_requested.flag を作成することで行えます（監視プロセスはフラグ検知後に終了）。

- ペーパートレード検証レポート
  python -m kabusys.tools.paper_verification_report
  - オプション --from / --to（YYYY-MM-DD）で期間指定、--db で DB ファイルパス指定可能。

プログラム的 API（主要）
-----------------------
- kabusys.portfolio
  - select_candidates, calc_equal_weights, calc_score_weights
  - calc_position_sizes
  - apply_sector_cap, calc_regime_multiplier

- kabusys.research
  - calc_momentum, calc_volatility, calc_value
  - calc_forward_returns, calc_ic, factor_summary, rank
  - zscore_normalize（kabusys.data.stats 経由）

- kabusys.ai
  - score_news(conn, target_date, api_key=None)
    - raw_news / news_symbols を用いて銘柄別センチメントを ai_scores に書き込む
  - regime_detector.score_regime(conn, target_date, api_key=None)
    - マクロニュース + ETF MA を使い market_regime テーブルへ書き込む

- 監視 DB ラッパー
  - kabusys.monitoring.monitoring_db.MonitoringDB
    - system_status / trade_logs / risk_logs / positions / dashboard の読み書きユーティリティ

停止・Kill Switch 等の運用
------------------------
- ExecutionEngine を外部から停止させたい場合:
  - KillSwitch による自動発動（監視が判定して data/kill.flag を書き込む）
  - 手動で停止させる場合は project_root/data/stop_requested.flag を作成（run_execution/run_monitoring はこのフラグを検知して終了）
- kill.flag は Settings.kill_flag_path（デフォルト data/kill.flag）で指定されるファイルです。config_setup と validate_config で設定を確認してください。

ログ
---
- 共通のログ初期化ユーティリティ: kabusys.utils.logging_setup.setup_logging(app_name="execution"|"monitoring")
  - stdout（StreamHandler） + 日次ローテート（TimedRotatingFileHandler）で logs/<app_name>.log に出力
  - LOG_DIR / LOG_LEVEL 環境変数で調整可能

ディレクトリ構成（抜粋）
---------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数 / Settings ラッパー
- config_setup.py          — .env 対話式ウィザード
- validate_config.py       — 設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — SystemMonitor 起動スクリプト
- utils/
  - logging_setup.py       — ロギング設定ユーティリティ
  - process_priority.py    — プロセス優先度 / CPU affinity 設定
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
- monitoring/
  - monitoring_db.py
  - system_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - monitoring_engine.py
  - (trade_monitor.py 等の他モジュール)
- tools/
  - paper_verification_report.py
- execution/ (発注関連コンポーネント群、Broker 工場・ExecutionEngine 等)
- data/ (デフォルトの DB ファイルやフラグファイルを置く想定ディレクトリ)

注意事項 / 運用上のヒント
-----------------------
- .env は誤ってコミットしないでください（API キー等の機密情報が含まれます）。
- 本番実行時（KABUSYS_ENV=live）は設定を慎重に確認してください。validate_config はライブ環境向けの追加警告を出します。
- AI 機能（OpenAI）は API キーと課金が必要です。API 呼び出し失敗時はフォールバックやスキップが入るため、完全停止しませんが、得られるデータは不完全になる可能性があります。
- ペーパートレード環境は本番の DB と完全に分離して記録されるよう設計されています（PAPER_TRADING_SQLITE_PATH を使用）。

貢献
----
機能改善・バグ修正は Pull Request を歓迎します。変更を加える場合はテスト追加・既存の設定/スクリプトとの互換性に注意してください。

ライセンス / バージョン
-----------------------
パッケージバージョンは kabusys.__version__ で定義されています（現行: 0.1.0）。

---

README に書ききれない細かな動作や API 仕様は各モジュールの docstring を参照してください。必要であれば、具体的な機能ごとの詳細ドキュメント（例: PortfolioConstruction.md, StrategyModel.md）を別途追加できます。