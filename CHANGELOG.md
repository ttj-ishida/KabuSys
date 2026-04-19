CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。
フォーマットは "Keep a Changelog" に準拠しています。

[0.1.0] - 2026-04-19
--------------------

Added
- 初期リリースを追加。
- 実行用エントリスクリプトを追加
  - run_execution.py: ExecutionEngine 起動スクリプトを提供。プロセス優先度を高く設定し、別スレッドでエンジンを起動・監視する。KABUSYS_ENV に応じて paper_trading 用 DB を分離して使用（data/paper_trading.db / 環境変数で上書き可能）。停止は data/stop_requested.flag によるフラグで制御。実行 PID を data/execution.pid に書き出す。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを提供。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視用 DB は環境に依らず本番 sqlite_path を使用する設計。
- 設定・環境管理
  - config.py: 環境変数ラッパー Settings を実装。J-Quants・kabu API 等の必須設定、DB パス、paper_trading 用の設定（PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH）や各種閾値をプロパティで提供。自動 .env 読み込みを実装（プロジェクトルート検出: .git または pyproject.toml を基準）。OS 環境変数は保護される。
  - config_setup.py: 対話式ウィザードで .env の初期作成・更新を支援。複数の項目定義（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、LOG_LEVEL など）を持ち、既存 .env の読み込み・確認・保存が可能。
  - validate_config.py: 起動前の検証 CLI を実装。.env と config/*.yaml のチェックを行い、必須環境変数未設定や本番環境向けのガードを警告/エラー表示。--strict オプションで警告も失敗扱いにできる。
- データベース・分析
  - DuckDB を分析用に統合（duckdb_path 設定）。複数モジュールで DuckDB 接続を受け取り SQL と Python を組み合わせて使用する設計。
- ポートフォリオ構築（純関数群）
  - portfolio/portfolio_builder.py: 候補選定 (select_candidates) と配分ウェイト計算 (calc_equal_weights, calc_score_weights) を実装。スコアが全て 0 の場合は等配分にフォールバックしてログ出力。
  - portfolio/position_sizing.py: position sizing ロジックを実装（risk_based / equal / score の各方式）。単元株（lot_size）丸め、per-position 上限、aggregate cap（利用可能現金に基づくスケーリング）、手数料等を考慮する cost_buffer をサポート。
  - portfolio/risk_adjustment.py: セクター集中制限 (apply_sector_cap) と市場レジームに応じた投下資金乗数 (calc_regime_multiplier) を実装。未知レジームはフォールバックで 1.0 を返し、警告を出力。
- ユーティリティ
  - utils/logging_setup.py: 統一的なロギング初期化ユーティリティを実装。stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler、30日保持）のファイルハンドラをルートロガーに設定。ログレベルとログディレクトリは引数・環境変数で解決。既存ハンドラの二重設定を防止するため再設定時にクリアする。
  - utils/process_priority.py: クロスプラットフォームでのプロセス優先度設定と CPU affinity 設定を提供。Windows と POSIX 系（Linux/Mac/FreeBSD）を吸収し、権限不足などで失敗した場合に警告ログを出す。
- 運用・検証ツール
  - tools/paper_verification_report.py: Paper Trading 検証レポート生成スクリプトを追加。システム稼働率、注文成功率・送信率、リスク却下数、API レイテンシ（平均・最大・P95）を算出。PASS/FAIL の判定閾値を定義（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）。--from / --to / --db オプションをサポート。
- リサーチ
  - research/factor_research.py: ファクター計算モジュール（モメンタム、Value、Volatility、Liquidity 等）の骨組みを実装。DuckDB の prices_daily / raw_financials を参照する前提で設計。モジュールは日付・銘柄ごとの辞書リストを返す仕様。

Changed
- なし（初回リリース）。

Fixed
- なし（初回リリース）。

Notes / 補足
- run_monitoring / run_execution は停止制御に file-based flag (data/stop_requested.flag, data/kill.flag 等) を利用する運用想定となっているため、デプロイ時に data ディレクトリの配置・権限に注意してください。
- .env 自動読み込みはデフォルトで有効。テスト等で無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。OS 環境変数は優先され、.env 読み込み時に保護されます。
- PAPER_FILL_MODE の検証を行い、不正な値が設定された場合は ValueError を投げる（利用者側で正しい設定値を確認してください）。
- logging_setup はログディレクトリ作成に失敗した場合にファイル出力をスキップして stdout のみで継続します。
- process_priority / set_cpu_affinity は権限の関係で失敗する場合があり、その際は警告ログでスキップされます。

開発者向け
- バージョン番号は kabusys.__version__ = "0.1.0" に設定済み。
- 今後の予定（想定）
  - research/factor_research の各ファクター計算の詳細実装完了
  - ExecutionEngine・SystemMonitor 周りの詳しいテストと E2E シナリオの整備
  - 銘柄ごとの単元株情報や価格フォールバックを取り込む拡張

----------------------------------------
この CHANGELOG はリポジトリ内のソースコードから推測して作成した概要です。実際の変更履歴やリリースノートは運用ポリシーに合わせて適宜追記してください。