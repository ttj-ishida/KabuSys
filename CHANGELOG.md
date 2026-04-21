Keep a Changelog
All notable changes to this project will be documented in this file.

フォーマットは「Keep a Changelog」に準拠しています。次のプレースホルダは使用されています：
- Added: 新機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Security: セキュリティに関する注意点 / 変更

## [0.1.0] - 2026-04-21

初回リリース。日本株自動売買システム "KabuSys" の基本コア機能と運用ユーティリティを実装しました。

### Added
- 基本パッケージ情報
  - パッケージバージョンを公開する __version__ = "0.1.0" を追加。

- 実行スクリプト / ランタイム
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は Paper Trading 用の専用 SQLite（data/paper_trading.db デフォルト）を使用し、MockBrokerClient 経由で実行を分離。
    - プロセス優先度を起動時に "high" に設定。
    - 停止用フラグ（data/stop_requested.flag） / PID ファイル (data/execution.pid) に対応。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用（監視 DB 用）。
    - 停止フラグでループを安全に終了。

- 設定管理
  - config.py:
    - .env 自動読み込み機能（プロジェクトルートは .git / pyproject.toml から検出）。
    - 読み込み優先順位: OS 環境 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動読み込みを無効化可能（テスト等向け）。
    - Settings クラス: 各種設定プロパティを提供（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH, PID/KILL フラグ関連パス, CPU/MEM/DISK 閾値, KABUSYS_ENV / LOG_LEVEL 判定ユーティリティ等）。
    - PAPER_FILL_MODE の検証（"instant" / "partial" / "never" / "reject" のみ有効）。
    - 環境（KABUSYS_ENV）は "development" / "paper_trading" / "live" のみ有効。

- 設定ツール / CLI
  - config_setup.py: 対話式 .env 作成・更新ウィザードを実装。
    - デフォルト値・選択肢表示、シークレット入力のマスク表示、保存前確認などの対話フローを提供。
  - validate_config.py: 設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL 検証、DB パス親ディレクトリチェック、config/*.yaml の存在・パース検証（PyYAML があれば内容検証）等。
    - --strict オプションで警告を失敗扱いにできる。
    - live 環境時のガード（LINE 通知設定・KILL_FLAG_CLEAR_ON_START の警告）を追加。

- 運用ツール
  - tools/paper_verification_report.py:
    - Paper Trading 用 SQLite から統計を集計し検証レポートを出力する CLI を追加。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、レイテンシ（avg/max/P95）など。
    - 閾値を定義して PASS/FAIL を判定（デフォルト閾値: uptime>=99%、fill_rate>=90%、send_rate>=95%、P95<=200ms）。
    - 日付フィルタ (--from / --to) および DB パス指定 (--db) に対応。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルのスコアで選定（同点は signal_rank でタイブレーク）。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア加重配分（全銘柄スコアが 0 の場合は等金額へフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中度チェック（max_sector_pct に基づき新規候補を除外）。
      - sell_codes（当日売却予定）をエクスポージャー計算から除外可能。
      - "unknown" セクターは上限チェックから除外。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数を返す（bull/neutral/bear をサポート、未知は 1.0 で警告とともにフォールバック）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: 複数の配分方法（risk_based / equal / score）に対応した株数計算ロジックを追加。
    - 単元株（lot_size）丸め、1 銘柄上限（max_position_pct）、利用可能現金に対する aggregate cap、cost_buffer による保守的見積もり、スケーリング・再配分ロジックを実装。
    - risk_based ではリスク許容率（risk_pct）と損切り率（stop_loss_pct）に基づきベース株数を計算。

- ロギング・プロセスユーティリティ
  - utils/logging_setup.py:
    - setup_logging 関数を追加。標準出力（stdout）向け StreamHandler と日次ローテーション FileHandler（TimedRotatingFileHandler、30 日分保持）をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR 環境変数、引数経由での解決。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみ継続。
  - utils/process_priority.py:
    - set_process_priority(level) でプラットフォーム差分を吸収してプロセス優先度設定を提供（Windows: HIGH_PRIORITY_CLASS 等、POSIX: nice 値）。
    - set_cpu_affinity(cpu_count) でプロセスの CPU affinity を設定（psutil に依存）。
    - 設定失敗（権限不足等）は警告としてスキップ。

- モニタリング
  - monitoring 初期化呼び出し（init_monitoring_db）を起動処理に組み込み（冪等に監視テーブルを保証）。

- DuckDB 統合
  - DuckDB 接続を必要とする処理（分析/リサーチ）用に duckdb 接続を起動時に確立して渡す構成に対応。

### Changed
- （初回リリースのため履歴上の既存変更はありませんが、以下の設計・挙動を明示）
  - 環境変数の自動ロードをプロジェクトルート検出ベースに変更（CWD に依存しない）。
  - ログは stdout を標準で使用するように設計（cron / scheduler の出力リダイレクトを想定）。

### Fixed
- （該当なし／初回リリース）

### Security
- .env ファイルは .git にコミットしない運用を README/ウィザード内で明示（config_setup が注意文を生成）。
- 必須機密情報（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）は Settings から取得する実装。起動前に validate_config で必須項目チェックを推奨。

### 注意・移行情報 / 運用メモ
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD は必ず設定してください。未設定時は Settings の参照で例外が発生します。
- .env 自動読み込み:
  - デフォルトでプロジェクトルート (.git または pyproject.toml) を基準に .env/.env.local を読み込みます。自動読み込みを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Paper Trading:
  - KABUSYS_ENV=paper_trading の場合、Execution は paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）を使用します。本番データと明確に分離されています。
  - PAPER_FILL_MODE の有効値は "instant" / "partial" / "never" / "reject" のいずれかです。無効値は ValueError となります。
- ログ:
  - デフォルトログディレクトリは logs/。アクセス権などで作成できない場合はファイルローテーションは無効化され、標準出力のみになります。
- 停止フラグ:
  - data/stop_requested.flag（実装上の既定パス）を用いて実行中の監視・エンジンを安全に停止できます。
- validate_config:
  - デプロイ前に python -m kabusys.validate_config を実行して設定を検証することを推奨します。--strict を付けると警告も失敗扱いになります。
- paper_verification_report:
  - Paper Trading 検証レポートはデフォルトで data/paper_trading.db を参照しますが --db オプションや環境変数 PAPER_TRADING_SQLITE_PATH で上書きできます。

もし特定のファイルや関数について詳細なリリースノート（例: 公開 API の例、パラメータの推奨値、想定ユースケース、既知の制限など）を追記希望であれば、対象を指定してください。