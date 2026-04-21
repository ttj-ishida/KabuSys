CHANGELOG
=========

すべての重要な変更をこのファイルに記録します。  
形式は "Keep a Changelog" に準拠しています。

Unreleased
----------

- （なし）

0.1.0 - 2026-04-21
------------------

Added
- 基本アプリケーション初期リリース。
- 実行・監視ランナー
  - run_execution: ExecutionEngine を起動する CLI スクリプトを追加。KABUSYS_ENV に応じて paper_trading 用の専用 SQLite（data/paper_trading.db）を使用し、本番 DB と分離して動作。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
  - 両スクリプトとも起動時にプロセス優先度を "high" に設定する処理を追加（utils.process_priority.set_process_priority を利用）。停止は data/stop_requested.flag によるフラグ検出で行う。
- 設定管理
  - config.Settings: 環境変数ベースの設定取得クラスを追加。env 判定（development / paper_trading / live）、データベースパス、PID / kill flag パス、各種しきい値などをプロパティで提供。
  - .env 自動ロード機構を実装: プロジェクトルート（.git または pyproject.toml を基準）を検出し、.env / .env.local を OS 環境変数と衝突しないように読み込む。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env の高度なパースを実装（export プレフィックス、クォート内エスケープ、インラインコメント取り扱いなど）。
  - PAPER_FILL_MODE（paper trading の MockBrokerClient の fill モード）をサポート（instant / partial / never / reject）。
- コンフィグ支援ツール
  - config_setup: 対話式ウィザードで .env を作成・更新する CLI を追加。必須/任意項目のプロンプト、シークレット入力の扱い、確認後のファイル書き出しをサポート。
  - validate_config: .env と config/*.yaml の簡易検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、YAML パース（PyYAML が存在する場合）や本番時ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の警告）を実行。--strict モードで警告を FAIL として扱う。
- ログ
  - utils.logging_setup.setup_logging を提供。stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log、30 日保持）をルートロガーに設定。LOG_DIR/LOG_LEVEL の優先解決、ファイル出力失敗時のフォールバック（コンソールのみ）を実装。stdout を使用するため、cron 等で stdout/stderr を一括リダイレクトする運用との相性を考慮。
- プロセス優先度 / CPU affinity
  - utils.process_priority にて Windows / POSIX の差分を吸収して優先度（high/normal/low）を設定。set_cpu_affinity によりプロセスを先頭 N コアに固定するユーティリティを提供。psutil の権限エラー等は警告でスキップする堅牢化。
- ポートフォリオ構築
  - portfolio.portfolio_builder: BUY シグナルの候補選定（スコア降順・タイブレーク）、等金額配分 calc_equal_weights、スコア加重配分 calc_score_weights（全スコア 0 の場合のフォールバックと警告）を実装。
  - portfolio.risk_adjustment: セクター集中制限 apply_sector_cap（当日売却対象の除外、"unknown" セクターは制限対象外）、市場レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear）を実装。未知レジームは警告を出して 1.0 でフォールバック。
  - portfolio.position_sizing: allocation_method（risk_based / equal / score）に基づく株数算出を実装。損切り・リスクベース計算、単元株（lot_size）で丸め、ポートフォリオ全体の aggregate cap によるスケールダウン、cost_buffer（手数料・スリッページ見積）考慮、残余配分のフェアネス保持（小数残差の順序に基づく追加配分）をサポート。未取得価格や price=0 の扱いはログ出力してスキップする。
  - position_sizing 内に将来的な拡張点として銘柄別 lot_size マップや価格フォールバックの TODO 注記あり。
- 実行検証ツール
  - tools.paper_verification_report: ペーパートレード DB（デフォルト data/paper_trading.db）から期間指定で検証レポートを生成する CLI を追加。システム稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、レイテンシ（平均・最大・P95）を算出し、閾値に基づく PASS/FAIL 判定を出力。P95 計算、日付フィルタ、DB 存在チェック、OperationalError 耐性を備える。
- データ解析
  - research.factor_research: ファクター計算基盤（モメンタム、MA200、ATR、流動性等）を設計・実装開始。DuckDB 接続を受け取り prices_daily / raw_financials を参照して計算する方針。関数群と定数を定義（実装は本ソース内で継続）。
- パッケージ情報
  - パッケージバージョン __version__ = "0.1.0" を設定。

Changed
- N/A（初期リリースのため既存機能の変更はなし）。

Fixed
- N/A（初期リリース）。

Deprecated
- N/A

Removed
- N/A

Security
- 環境変数の自動ロードにおいて OS 環境変数を保護する仕組みを導入（.env/.env.local のロード時に既存の OS 環境変数を上書きしない／保護リストを使用）。機密情報は .env を Git にコミットしないよう README に注意喚起（config_setup でのヘッダにも記載）。

Notes / TODO
- position_sizing と risk_adjustment の中で、「価格が欠損している場合のフォールバック（前日終値や取得原価）」や「銘柄別の lot_size マップ」など将来の改善点がコメントとして残されています。
- research.factor_research は設計と一部定数まで実装済みで、モメンタム計算関数等の続きを今後追加予定。

Contact
- 詳細な実装や設計意図についてはソース内の docstring / コメントを参照してください。質問や変更提案があればリポジトリの issue を作成してください。