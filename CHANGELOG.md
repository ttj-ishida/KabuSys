CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

- （なし）

[0.1.0] - 2026-04-20
--------------------

Added
- 起動スクリプトを追加
  - run_execution.py: ExecutionEngine を起動するメインスクリプトを追加。KABUSYS_ENV により paper_trading 環境時は専用の MockBrokerClient と paper_trading 用 SQLite DB を使用する。停止フラグ（data/stop_requested.flag）を監視し、実行中スレッドを安全に停止する仕組みを搭載。実行 PID を data/execution.pid に書き込む想定。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視用 DB は環境にかかわらず本番 sqlite_path を使用。

- 設定管理・自動ロード
  - config.py: 環境変数・設定管理クラス Settings を追加。.env 自動読み込み機能を実装（プロジェクトルートの判定: .git または pyproject.toml を探索）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動読み込みを無効化可能。複数の設定プロパティ（J-Quants、kabu API、DB パス、監視閾値など）を定義。
  - .env の読み取りロジックを堅牢化（export プレフィックス対応、シングル/ダブルクォート内のエスケープ、行末コメントの取り扱いなど）。

- 設定支援ツール
  - config_setup.py: 対話式ウィザードで .env を初期作成・更新する CLI を追加。項目定義（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、LOG_LEVEL、KILL_FLAG_CLEAR_ON_START など）を含む。既存の .env を読み込み、シークレットはマスク表示して保存可能。
  - validate_config.py: .env と config/*.yaml の基本的な検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、YAML ファイルの存在および PyYAML が利用可能ならパース検証、live 環境時の追加警告を実装。--strict オプションで警告をエラー扱いにできる。

- ロギング / プロセス管理ユーティリティ
  - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）をルートロガーに設定。既存ハンドラのクリーンアップ、ログレベル/ディレクトリの解決順を実装。ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみで継続。
  - utils/process_priority.py: クロスプラットフォームなプロセス優先度設定ユーティリティを追加。Windows と POSIX（Linux/Mac 等）に対応。psutil を用いて優先度設定および CPU affinity 設定（set_cpu_affinity）を提供。権限不足や非対応 OS の場合は警告を出してスキップ。

- ポートフォリオ構築関連の純粋関数群（DB 参照なし）
  - portfolio/portfolio_builder.py: 候補選定 (select_candidates)、等配分 (calc_equal_weights)、スコア加重 (calc_score_weights) を実装。スコアが全て 0 の場合は等配分にフォールバックする挙動を持つ。
  - portfolio/risk_adjustment.py: セクター集中制限を実装する apply_sector_cap、レジームに応じた資金乗数を返す calc_regime_multiplier を実装。regime に対する multiplier マップ（bull=1.0, neutral=0.7, bear=0.3）を定義し、未知の値は警告して 1.0 にフォールバック。
  - portfolio/position_sizing.py: 発注株数計算 calc_position_sizes を実装。allocation_method に応じて risk_based / equal / score を扱い、lot_size（単元）で丸め、portfolio レベルの aggregate cap（available_cash）に基づくスケールダウン処理、cost_buffer を用いた保守的コスト見積り、残余の端数処理（lot 単位での再配分）等を実装。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py: Paper Trading 用 SQLite DB を読み取り、稼働率（uptime）、注文成功率（fill rate）、送信率、P95 レイテンシ等を集計してレポートを出力する CLI を追加。期間指定 (--from / --to) と DB パス指定 (--db / 環境変数 PAPER_TRADING_SQLITE_PATH) をサポート。基準値（稼働率 99%、fill 90%、send 95%、P95 200 ms）で PASS/FAIL 判定を行う。

- 研究用ファクター計算基盤（初期実装）
  - research/factor_research.py: DuckDB 接続を受けてファクター（Momentum / Value / Volatility / Liquidity）を計算するためのモジュールを追加。モメンタム計算のための定数・API（calc_momentum）を導入。設計方針として DuckDB の prices_daily / raw_financials テーブルのみ参照することを明記。実装は作業途中の部分が含まれる（メモ: モジュール末尾に処理継続箇所あり）。

Changed
- パッケージ初期化
  - __init__.py にバージョン情報 __version__ = "0.1.0" を追加し、公開サブパッケージ名を __all__ に設定。

- ログ出力の一貫化
  - 全起動スクリプトおよび主要モジュールから setup_logging を使う想定になっており、一貫したフォーマット・ファイル出力設計に合わせた。

Fixed
- 環境変数パースの堅牢化
  - config._parse_env_line においてクォート内のバックスラッシュエスケープ処理や行内コメントの扱いを改善。export KEY=val 形式にも対応。

Notes / Known issues
- research/factor_research.py はモメンタム計算関数の実装途中でファイル末尾が切れている（開発中）。本格運用前に完全実装とテストが必要。
- process_priority の実行は権限やプラットフォームに依存するため、設定に失敗するケースはログで警告し、安全にスキップする実装となっている。
- Paper Trading と Live の DB は明示的に分離（paper_trading 用 DB パスを使用）されるが、運用上の注意（.env の設定や DB バックアップなど）はドキュメントで追記推奨。

Migration notes
- .env の自動読み込みはデフォルトで有効。テストや CI で自動読み込みを抑制したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Paper Trading を実行する際は KABUSYS_ENV=paper_trading を設定し、PAPER_TRADING_SQLITE_PATH が必要に応じて上書き可能です。
- ログ出力ディレクトリを変更したい場合は環境変数 LOG_DIR を設定してください。ログレベルは LOG_LEVEL または setup_logging の引数で制御できます。

----