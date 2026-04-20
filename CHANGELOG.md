CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" (https://keepachangelog.com/ja/).
バージョンは semver に従います。

Unreleased
----------

（なし）

0.1.0 - 2026-04-20
------------------

初期リリース。以下の主要機能・ユーティリティ・CLI を実装しています。

Added
- 全体
  - パッケージ初期版を公開。バージョンは __version__ = "0.1.0"。
- 起動スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止はプロジェクト直下 data/stop_requested.flag を作成して行う。
    - Monitoring は KABUSYS_ENV に依らず本番 sqlite_path を使用する仕様。
  - run_execution.py: ExecutionEngine（トレード実行エンジン）起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は専用のペーパートレード用 SQLite（デフォルト data/paper_trading.db）を使用し、本番 DB と分離。
    - 起動前に停止フラグ（data/stop_requested.flag）をチェックし、存在する場合は起動せず終了。
    - 実行中は別スレッドでエンジンを実行し、停止フラグ検知で安全に停止する。
- 設定関連
  - config.py: 環境変数読み込み・設定管理を実装。
    - プロジェクトルート（.git または pyproject.toml）を自動検出し、.env/.env.local を自動読み込み（OS 環境変数が優先）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能。
    - .env パース機能はシングル／ダブルクォート、エスケープ、行内コメントなどを考慮。
    - Settings クラスで各種設定値をプロパティとして提供（例: duckdb_path, sqlite_path, paper_sqlite_path, pid_file_path, kill_flag_path, CPU/MEM/DISK 閾値など）。
    - PAPER_FILL_MODE の検証（instant/partial/never/reject）。
    - KABUSYS_ENV の検証（development/paper_trading/live）と log level の検証。
  - config_setup.py: 対話式 .env 作成ウィザードを実装。
    - 初期値・説明付きプロンプト、既存 .env の読み込み、保存時の注意喚起（.env を Git に含めないこと）を提供。
- 設定検証 CLI
  - validate_config.py: .env と config/*.yaml の簡易検証ツールを追加。
    - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）。
    - KABUSYS_ENV / LOG_LEVEL / DB パスの簡易チェック、config/*.yaml の存在確認と YAML パース（PyYAML が未インストールなら警告してスキップ）。
    - KABUSYS_ENV=live 向けの追加ガード（LINE 設定未設定や KILL_FLAG_CLEAR_ON_START の危険設定を警告）。
    - --strict オプションで警告も失敗扱いにできる。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルをスコア降順で選択（タイブレークは signal_rank）。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア比例配分。全銘柄スコアが 0 の場合は等配分にフォールバック（警告）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中上限（max_sector_pct）を超える場合に新規候補を除外。unknown セクターは除外対象にしない。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3）。未知レジームは 1.0 でフォールバック（警告）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: 単元株丸め、リスクベース/等分/スコアベースの発注株数計算を実装。
      - risk_based: risk_pct, stop_loss_pct に基づく許容リスクから株数算出。
      - equal/score: weight に基づく割当て、per-position と aggregate の上限考慮。
      - lot_size（単元）で切り下げ、コストバッファ（cost_buffer）を考慮した保守的見積り。
      - aggregate cap を超える場合はスケーリングと端数処理（lot 単位で残差を最大順に配分）を行う。
- ユーティリティ
  - utils/logging_setup.py:
    - 統一ロギング設定ユーティリティを追加。
    - stdout への StreamHandler、日次ローテーション（TimedRotatingFileHandler）でログ出力。ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみ継続。
    - ログレベルとログディレクトリの解決順を明記（引数 > 環境変数 > デフォルト）。
  - utils/process_priority.py:
    - プラットフォーム差分を吸収するプロセス優先度設定、CPU affinity 設定ユーティリティを追加。
    - Windows（psutil の優先度定数）と POSIX（nice 値）に対応。設定失敗時は警告でスキップ。
- ペーパートレード検証ツール
  - tools/paper_verification_report.py:
    - ペーパートレード用 SQLite（デフォルト data/paper_trading.db）から稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）などの指標を集計してレポート出力。
    - 閾値を定義して PASS/FAIL 判定を行う（稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 <= 200ms）。
    - 日付フィルタ（--from / --to）と --db オプションに対応。
- リサーチ（計算基盤の一部）
  - research/factor_research.py:
    - モメンタムや ATR 等のファクター計算の基礎を実装（設計・定数が定義され、一部実装がある）。DuckDB 接続を受けて prices_daily / raw_financials を参照する想定。
- DB 初期化 / 監視周り
  - monitoring.monitoring_db.init_monitoring_db の呼び出しを各起動スクリプトで行い、監視テーブルが存在することを冪等的に保証。
  - duckdb 接続をデフォルトで使用（duckdb_path 設定）。

Changed
- なし（初回公開のためすべて追加）

Fixed
- なし（初回公開）

Removed
- なし

Deprecated
- なし

Security
- なし

Notes / Implementation details & behavior
- .env 自動読み込みは OS 環境変数を上書きしない（既存キーは保護）。.env.local は .env の上書きとして扱い、OS 環境変数は常に優先される。
- run_monitoring はモニタリング用 DB として常に Settings.sqlite_path を使用する（環境に依存しない）。run_execution は is_paper 判定により paper_sqlite_path を使用して発注ログ等を分離する。
- ログは stdout に出力されるので、cron や Task Scheduler での起動時にもログをリダイレクトしやすい設計。
- process_priority および CPU affinity の設定は実行環境によっては権限不足で失敗する可能性があり、その場合は警告を出して処理を継続する。

Known issues / TODO（今後の課題）
- portfolio.position_sizing.calc_position_sizes:
  - price の欠損（0.0）の場合にエクスポージャーが過少見積りされる可能性がある旨の TODO コメントあり（前日終値や取得原価でのフォールバックを検討）。
  - 将来的に銘柄別 lot_size を導入するための拡張を想定している。
- research/factor_research.py:
  - ファイルの実装が途中（コード末尾が未完）で、完全なファクター計算の実装が必要。
- config/*.yaml の内容検証は PyYAML が必要（未インストールならスキップして警告）。

開発者向けメモ
- 開発・テストで自動 .env 読み込みを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- デバッグや詳細ログを確認するには LOG_LEVEL を環境変数または .env で設定してください（DEBUG/INFO/...）。

--------------------------------
この CHANGELOG はコードベースの現状から推測して作成しています。実際のリリースノートとして用いる場合は、運用上の重要な変更点・互換性情報を併せて確認・追記してください。