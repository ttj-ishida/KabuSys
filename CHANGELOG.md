# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。  
現在のバージョン: 0.1.0

履歴の要約は日本語で記載しています。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-18

Added
- 基本機能
  - パッケージ初期リリース。日本株自動売買システム「KabuSys」の基盤機能を追加。
- 起動スクリプト
  - run_execution: ExecutionEngine を起動するスクリプトを追加。  
    - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、ペーパートレード用の DB（data/paper_trading.db、環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）に記録することで本番 DB と完全分離。  
    - 実行中の停止は data/stop_requested.flag を監視し、フラグ検知でエンジン停止。PID ファイルのパスをサポート。
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。  
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。  
    - 監視は本番用 sqlite_path を使用（環境にかかわらず本番監視 DB を利用）。data/stop_requested.flag による停止検出をサポート。
- 設定・環境管理
  - config.Settings: 環境変数と .env を統合して扱う設定クラスを追加。多数のプロパティを提供（J-Quants / kabu API / DB パス / 監視しきい値 / 実行環境フラグ等）。  
    - PAPER_FILL_MODE（paper_trading 用 fill モード）や PAPER_TRADING_SQLITE_PATH、KILL_FLAG_CLEAR_ON_START などをサポート。  
    - KABUSYS_ENV の値検証やログレベルの検証を備える。
  - .env 自動読み込み: プロジェクトルート（.git または pyproject.toml を基準）を検出し、.env と .env.local を自動で読み込む（OS 環境変数は保護）。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - validate_config CLI: .env と config/*.yaml を起動前に検証するユーティリティを追加。  
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パス親ディレクトリ存在チェック、YAML パース（PyYAML がインストールされている場合）などを報告。  
    - --strict オプションで警告を失敗扱い（exit(1)）にできる。
  - config_setup CLI: 対話式ウィザードで .env を初期作成・更新するツールを追加。秘密値はマスク表示、選択肢・デフォルト値・説明を表示して保存可能。
- ログ・プロセス管理ユーティリティ
  - utils.logging_setup.setup_logging: ルートロガーに StreamHandler（stdout）と日次ローテーションの TimedRotatingFileHandler を設定する共通ユーティリティを追加。LOG_DIR / LOG_LEVEL の優先順位やファイルローテーション（30日保持）等をサポート。ファイル出力が失敗してもコンソール出力で継続。
  - utils.process_priority: プロセス優先度（high/normal/low）を OS を吸収して設定するユーティリティを追加。Windows/Linux/macOS での互換を考慮し、CPU affinity 設定関数も提供。呼び出し元はプラットフォームを意識する必要なし。失敗時は警告ログでスキップ。
- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルをスコア降順でソートし上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等金額配分およびスコア加重配分を提供。全スコアが 0 の場合は等金額へフォールバックして警告出力。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限適用ロジック。既存保有のセクター比率が上限を超えている場合、新規候補を除外（"unknown" セクターは除外対象外）。売却予定銘柄の除外やデバッグログを提供。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投入資金乗数を返す。未知のレジームは 1.0 へフォールバックして警告。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に応じた株数決定ロジックを実装。  
      - 損切り率・risk_pct ベースの risk-based 計算、lot_size（現在は 100）、コストバッファ、aggregate cap のスケールダウンと残差処理（lot 単位での再配分）を備える。
- 研究用ファクタ計算
  - research.factor_research: DuckDB 接続を受け取り prices_daily / raw_financials を参照して Momentum / Value / Volatility / Liquidity 系ファクターを計算するための骨格を追加（モメンタム計算の設計方針・定数を含む）。
- ツール
  - tools.paper_verification_report: ペーパートレード検証レポート生成スクリプトを追加。  
    - system_status / trade_logs / risk_logs などから稼働率、注文成功率、送信率、レイテンシ（P95 等）を集計し PASS/FAIL 判定を出力。閾値はソース内で定義（稼働率 >= 99%、Fill >= 90% 等）。日付フィルタ（--from / --to）および --db オプションをサポート。P95 計算ユーティリティを実装。
- データベース / 分析
  - duckdb の利用を前提とした分析用コネクションを各起動スクリプトで受け渡し。monitoring 用の SQLite テーブル初期化関数（init_monitoring_db）を起動時に呼び出して冪等的にテーブル存在を保証。

Changed
- N/A（初期リリースのため変更履歴なし）

Fixed
- N/A（初期リリースのため修正履歴なし）

Notes / 使用上の注意
- 環境変数による挙動
  - MONITOR_POLL_INTERVAL に不正値（0 以下や非整数）を指定した場合は警告を出しデフォルト 60 秒へフォールバックします。
  - KABUSYS_ENV 値は development / paper_trading / live のいずれかでなければ例外（または validate でエラー）になります。
  - .env 自動ロードはプロジェクトルートが検出できなければスキップされ、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により明示的に無効化可能。
- DB 分離
  - ペーパートレード時は paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番の monitoring.db と分離する設計になっています。
- ログ出力
  - ログは標準出力 (stdout) にも出力されるため、cron 等での実行時にも扱いやすくなっています。ログファイル出力に失敗してもプロセスは継続します（コンソールのみ出力）。
- 権限/プラットフォーム依存
  - process priority / cpu affinity の設定は環境や権限に依存します。設定に失敗した場合は警告でスキップします。

開発者向けヒント / コマンド例
- 設定ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - または --db オプションで DB パスを指定可能

---

（初期リリースにつき後方互換性に関する注意は特にありません。今後のリリースでは API/設定名の変更が発生する可能性があります。）
