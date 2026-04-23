CHANGELOG
=========

すべての重要な変更点を記録します。本ファイルは "Keep a Changelog" の形式に準拠しています。

フォーマット:
- 変更はセクション (Added, Changed, Fixed, etc.) に分類しています。
- バージョンはパッケージ内の __version__ と合わせています。

[Unreleased]
------------

（現状なし）

0.1.0 - 2026-04-23
------------------

初回リリース

Added
- コア起動スクリプトを追加
  - run_execution.py: ExecutionEngine 起動用スクリプトを追加。KABUSYS_ENV=paper_trading の場合は MockBrokerClient を用い、paper_trading 用の専用 SQLite（data/paper_trading.db をデフォルト）を使用して本番 DB と完全に分離。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する仕様。

- 設定・環境変数管理
  - config.py: .env 自動読み込み機能（プロジェクトルート判定）を実装。.env/.env.local の読み込み順序をサポートし、OS 環境変数の保護（上書き回避）を実装。
  - Settings クラスを提供し、アプリケーション設定（DB パス、API トークン、環境種別、ログレベル、各種閾値 等）をプロパティ経由で取得可能に。

- 設定支援ツール
  - config_setup.py: 対話式ウィザードで .env を初期作成／更新する CLI を追加。シークレットマスク表示やデフォルト値の提示、保存確認を実装。
  - validate_config.py: 起動前チェック CLI を追加。必須環境変数や YAML 設定ファイルの存在・パース検証、KABUSYS_ENV の安全性チェックや本番環境向けガードを実装。--strict オプションで警告を FAIL 扱い可能。

- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py: シグナル選定（select_candidates）・等配分（calc_equal_weights）・スコア重み配分（calc_score_weights）を実装。
  - portfolio/position_sizing.py: 発注株数計算ロジック（risk_based / equal / score）を実装。単元株（lot_size）による丸め、aggregate cap によるスケーリング、cost_buffer を用いた保守的見積りを実装。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）とレジーム乗数（calc_regime_multiplier）を実装。

- 監視・実行共通ユーティリティ
  - utils/logging_setup.py: 統一的なロギング設定ユーティリティを追加。コンソール (stdout) 出力と日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。LOG_LEVEL / LOG_DIR の環境変数に対応し、ファイル書き込み失敗時はコンソールのみで継続。
  - utils/process_priority.py: Windows / POSIX（Linux/Mac/FreeBSD）差分を吸収してプロセス優先度（high/normal/low）および CPU affinity を設定するユーティリティを追加。権限不足時は警告を出してスキップ。

- 運用ツール
  - tools/paper_verification_report.py: Paper Trading 向け検証レポート生成スクリプトを追加。稼働率、注文成功率・送信率、リスク却下数、API レイテンシ（P95 など）を集計して PASS/FAIL を判定。閾値はソース内定義でカスタマイズ可能。--from/--to/--db オプション対応。

- 研究用モジュール（断片実装）
  - research/factor_research.py: ファクター計算基盤（モメンタム、移動平均乖離、ATR、流動性など）を実装するためのモジュールを追加（DuckDB 接続を受け、prices_daily / raw_financials を参照する設計）。モメンタム計算等の関数が含まれる（開発中の箇所あり）。

Changed
- DB 接続の挙動
  - 監視プロセスは KABUSYS_ENV にかかわらず本番用 sqlite_path を使用するよう明示（監視データは本番 DB を参照／記録する前提）。
  - 実行エンジンは paper_trading 環境では専用の paper_sqlite_path を使用して本番 DB と分離。

- 起動時のプロセス設定
  - run_execution/run_monitoring の起動シーケンスで最初に set_process_priority("high") を呼び出してプロセス優先度を上げるように変更（重要なバックグラウンドタスク向け）。

- .env パーサーの強化
  - export KEY=val 形式のサポート、シングル/ダブルクォート内のバックスラッシュエスケープ処理、行内コメントの取り扱いルール（未引用の # はスペース前のみコメントとみなす）などを実装して堅牢性を向上。

- ログ出力
  - StreamHandler は stdout を使用（cron 等から stdout/stderr を一本化してリダイレクトする運用を想定）。ファイルログは日次ローテート・30 日分保持。

Fixed
- calc_score_weights: 全銘柄のスコア合計が 0.0 の場合に等金額配分へフォールバックし、警告ログを出す実装で不正なゼロ除算を回避。
- position_sizing: 単元株（lot_size）丸め、per-position 上限や aggregate cap のスケーリングロジックを整備し、予期せぬ浮動小数点端数処理による過剰発注を防止。残余キャッシュを使って lot 単位で再配分するアルゴリズムを導入。
- apply_sector_cap: "unknown" セクター（マップに存在しない銘柄）をセクター上限適用対象から除外することで、マスタ欠損による不要な除外を防止。
- validate_config: PyYAML 未インストール時に YAML パースチェックをスキップし、警告を出すことで依存性がなくても実行可能に。
- run_execution/run_monitoring: データベース接続（sqlite / duckdb）のクローズを finally ブロックで確実に行うよう改善。

Security
- .env はデフォルトでプロジェクト直下の .env を自動読み込みするが、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動読み込みを無効化できるオプションを追加（テストや安全な起動のため）。

Notes / その他
- PID ファイル・停止フラグ
  - 実行/監視プロセスは data/<name>.pid や data/stop_requested.flag / data/kill.flag 等のファイルによる外部制御（停止リクエスト / Kill Switch）を想定。Settings でパス・振る舞いを設定可能。
- Paper Trading の挙動
  - PAPER_FILL_MODE（instant/partial/never/reject）を環境変数で設定可能。Paper ブローカーの約定挙動を切り替えられる。
- ドキュメント参照
  - ポートフォリオ関連の関数は PortfolioConstruction.md / StrategyModel.md 等の設計ドキュメントに準拠して実装されている（ソース内コメント参照）。

既知の制限 / TODO
- research/factor_research.py は完全実装中の箇所があり、一部の関数が未完成（ソース末尾が途切れる等）。DuckDB テーブル構成に依存するため、実運用前にテーブルのスキーマ確認が必要。
- position_sizing の価格フォールバック（価格が 0.0 の場合の扱い）は TODO コメントとして残っており、前日終値等のフォールバック機構の追加が望ましい。
- 単元（lot_size）の将来拡張: 銘柄別 lot_map を受けるように改善する余地がある。

以上。