KEEP A CHANGELOG
=================

すべての注目すべき変更点を記録します。  
このファイルは Keep a Changelog の慣習に従って作成されています。

フォーマット
-----------
各リリースには少なくとも以下のカテゴリを用います: Added, Changed, Fixed, Deprecated, Removed, Security。

2026-04-25 — 0.1.0
------------------
最初の公開リリース（推測）。コードベースから判別できる主要な機能と改善点をまとめています。

Added
- 基本アプリケーションバージョンを導入（__version__ = "0.1.0"）。
- 実行スクリプト:
  - run_monitoring.py: SystemMonitor のポーリングループを起動するスクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。プロジェクト内 data/stop_requested.flag による停止検知を実装。監視は環境設定にかかわらず本番用 sqlite_path を使用する。
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB（data/paper_trading.db）と MockBrokerClient を利用して本番 DB と分離。停止フラグ・PID ファイル管理・デーモンスレッドでの実行／停止制御を実装。
- 設定管理:
  - Settings クラス（kabusys.config）を追加。環境変数から各種設定（API トークン、DB パス、各種しきい値、環境種別など）を安全に取得するプロパティ群を提供。
  - 自動 .env ロード機能を実装（プロジェクトルートの検出: .git または pyproject.toml を起点）。環境変数保護（OS 環境変数の上書き防止）に対応。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動読み込みを無効化可能。
  - PAPER_FILL_MODE のバリデーションを実装（instant/partial/never/reject のみ許容）。
- 設定支援 CLI:
  - config_setup.py: 対話式ウィザードを追加し .env の初期作成・更新を支援。機密値はマスク表示、生成した .env を保存する際の注意書きを出力。
  - validate_config.py: 起動前チェック用 CLI を追加。必須環境変数の存在確認、KABUSYS_ENV や LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ確認、config/*.yaml の存在・簡易パース（PyYAML が存在する場合）を実行。--strict オプションで警告をエラー扱いにできる。
- ロギングユーティリティ:
  - utils/logging_setup.py: 共通ログ設定を追加。コンソール出力は stdout を使用し、日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）でログを logs/<app_name>.log に出力（30 日保持）。既存ハンドラをクリアして二重出力を防止。
- プロセス制御ユーティリティ:
  - utils/process_priority.py: set_process_priority と set_cpu_affinity を実装。Windows/Linux/macOS 等での差分を吸収（psutil を利用）。権限不足時は警告を出してスキップする安全設計。
- ポートフォリオ構築モジュール:
  - portfolio/portfolio_builder.py: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコアが全て 0 の場合は等金額配分へフォールバック。
  - portfolio/risk_adjustment.py: セクター集中制限を適用する apply_sector_cap と市場レジームに応じた乗数 calc_regime_multiplier を実装（regime: bull/neutral/bear）。
  - portfolio/position_sizing.py: 株数決定アルゴリズムを実装。risk_based / equal / score の割当方式に対応。lot_size（単元）丸め、1 銘柄上限、aggregate cap（available_cash によるスケールダウン）、cost_buffer を用いた保守的見積り、端数処理のための再配分ロジックを備える。
- ツール:
  - tools/paper_verification_report.py: ペーパートレード用検証レポート生成スクリプトを追加。PAPER_TRADING_SQLITE_PATH（または --db）からデータを集計し、稼働率・注文成功率・送信率・P95 レイテンシ等を評価して PASS/FAIL 判定を行う。既定の基準値（稼働率 99% 等）を使用。
- 研究用モジュール（草案）:
  - research/factor_research.py: DuckDB を利用したファクター計算（モメンタム、移動平均乖離、ATR、流動性等）の設計と一部実装を追加（ファイル末尾が切れているため一部継続実装が想定される）。

Changed
- 監視／実行スクリプトで共通の監視 DB 初期化関数 init_monitoring_db を呼ぶようにして、監視テーブルが存在することを保証（冪等化）。
- ログハンドラは既存のハンドラを明示的に flush/close してから再設定することで二重出力を防止する設計へ変更。
- 標準出力を stdout に統一（StreamHandler）し、cron 等でのリダイレクト運用を想定。

Fixed
- 環境変数や CLI オプションの不正値に対して安全にフォールバックする挙動を追加:
  - MONITOR_POLL_INTERVAL が不正（0 以下・非整数）の場合は警告を出してデフォルト値（60 秒）にフォールバック。
  - PAPER_FILL_MODE の不正値は ValueError を投げて早期検出。
  - Settings.env / LOG_LEVEL の不正値は明確なエラーメッセージを投げるように改善。
- process_priority / set_cpu_affinity は権限・未対応 OS のケースで例外を捕捉しログ出力に留めることで起動失敗を防止。

Security
- .env 作成ウィザードに「.env を絶対に Git にコミットしないこと」の注意を明記。
- 自動 .env 読み込み時に OS 環境変数を保護する仕組み（protected set）を導入。既存の OS 環境変数は override されない。

Known limitations / Notes (推測)
- research/factor_research.py は途中（ファイル末尾が切れている）に見えるため、ファクター計算の完全実装は継続作業が必要。
- position_sizing の注記にあるように、銘柄ごとの単元（lot_size）を銘柄別に設定する拡張や価格欠損時のフォールバック（前日終値等）は将来対応予定。
- YAML 設定ファイルの検証は PyYAML がインストールされている場合のみ実施。環境により警告が出る可能性あり。

Credits
-------
この CHANGELOG はコードベースから推測して作成したものであり、実際の変更履歴やリリースノートはリポジトリのコミット履歴やプロジェクトチームの記録を参照してください。