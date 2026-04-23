# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に準拠して記載しています。  
このファイルはリポジトリ内の現行コードベースから推測して作成した初期リリース向けの変更履歴です。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-23

初回リリース。システム全体の起動スクリプト、設定管理、監視・実行エンジンの補助ユーティリティ、ポートフォリオ構築ロジック、Paper Trading 検証ツールなどの主要機能を追加。

### Added
- 起動スクリプトを追加
  - run_execution.py
    - ExecutionEngine 起動用スクリプト。
    - KABUSYS_ENV=paper_trading 時は専用の paper_trading DB（data/paper_trading.db をデフォルト）を使用し、本番 DB と分離。
    - 停止フラグ（data/stop_requested.flag）および PID ファイル（data/execution.pid）に対応。
    - スレッドでエンジンをデーモン実行し、停止フラグ検知でエンジン停止を行う。
    - プロセス優先度を高（"high"）に設定して起動。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動用スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用 sqlite_path を使用する（monitoring 用 DB 初期化を実行）。
    - 停止フラグ（data/stop_requested.flag）検知でループを終了。
- 設定管理
  - config.py
    - .env 自動読み込み機能（プロジェクトルート判定: .git または pyproject.toml）。
    - .env / .env.local の読み込み優先度・保護（OS 環境変数の上書きを防ぐ）に対応。
    - .env 行パーサを実装（export プレフィックス、シングル / ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いに対応）。
    - Settings クラスを実装。主要環境変数の取得とバリデーションを提供（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）。
    - PAPER_FILL_MODE の有効値チェック（instant/partial/never/reject）。
    - kill_flag_clear_on_start 等の設定を提供。
- 設定補助ツール
  - config_setup.py
    - 対話式ウィザードで .env の初期作成・更新を支援。
    - よく使う設定項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DB パス, LOG_LEVEL 等）を対話形式で編集・保存可能。
    - 既存 .env 読み込み、シークレット値のマスク、保存確認を実施。
- 設定検証ツール
  - validate_config.py
    - 起動前に必須環境変数や設定ファイル（config/*.yaml）の存在・基本整合性を検証する CLI。
    - --strict オプションで警告を失敗として扱う。
    - PyYAML が未インストールの場合は YAML 検証をスキップして警告出力。
    - 本番用ガード（KABUSYS_ENV=live 時の追加チェック）を実装。
- Paper Trading 検証レポートツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）から稼働率、注文成功率、送信率、レイテンシ等を集計しレポートを出力。
    - P95 計算、各種閾値（稼働率 99%、成功率 90% 等）に基づく PASS/FAIL 判定を実装。
    - --from/--to/--db オプション対応。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順（同点時は signal_rank 昇順）で候補選定。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア比率で配分（全スコア 0 の場合は等配分にフォールバックし WARNING）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限（max_sector_pct）に基づき新規候補を除外。unknown セクターは上限適用除外。
    - calc_regime_multiplier: レジーム（bull/neutral/bear）に応じた資金乗数を返す（未知レジームは警告して 1.0 にフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づき発注株数を計算。単元株（lot_size）で丸め、aggregate cap によりスケールダウン。cost_buffer を考慮。
    - 現在の実装は全銘柄共通の lot_size を仮定（将来的に銘柄別ロット対応の TODOあり）。
- ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日分保持）を設定する共通ユーティリティ。
    - ログレベル解決順（引数 > 環境変数 LOG_LEVEL > デフォルト INFO）。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみで継続。
    - stdout を使う設計（cron 等で stdout/stderr を統合する運用を想定）。
  - utils/process_priority.py
    - プロセス優先度設定（set_process_priority）と CPU affinity（set_cpu_affinity）を提供。
    - Windows と POSIX(Linux, Darwin, FreeBSD) の差分を吸収（Windows の優先度定数は getattr によるフォールバック）。
    - 権限不足や未実装 API には警告でフォールバック。
- その他
  - パッケージメタ情報: __init__.py に __version__ = "0.1.0" を設定。
  - research/factor_research.py の基礎実装を追加（モメンタム・ボラティリティ等のファクター計算方針と定数）。（注: calc_momentum の実装はファイル末尾で途切れが見られるため未完の可能性あり）

### Changed
- （初回リリースにつき該当なし）

### Fixed
- （初回リリースにつき該当なし）

### Deprecated
- （なし）

### Removed
- （なし）

### Security
- 環境変数読み込みにおいて OS 環境変数を保護する仕組みを導入（.env の上書きに際して protected set を使用）。

## Known issues / TODO
- research/factor_research.py の calc_momentum 関数が途中で切れている（ファイル末尾で "start_da" のような断片があり、実装が未完の疑い）。詳細なファクター計算ロジックは要確認・補完。
- portfolio/risk_adjustment.py の apply_sector_cap 内で price が 0.0 の場合にエクスポージャーが過少見積りされる旨の TODO コメントあり。前日終値等のフォールバック実装が望ましい。
- position_sizing.calc_position_sizes は現状全銘柄共通の lot_size を仮定しており、銘柄別単元対応は将来の拡張予定（TODO コメントあり）。
- ログディレクトリ作成・ファイルハンドラ生成に失敗した場合はコンソールのみで継続する設計。運用時は権限やパス設定を確認すること。
- run_monitoring は「監視は環境にかかわらず本番 sqlite_path を使用する」とドキュメントにあるため、環境設定に注意（意図的な設計か確認が必要な箇所）。

---

以降のリリースでは、上記の未完了部分の完成、ユニットテストの追加、config/duckdb/sqlite 周りの運用上の堅牢化（例: DB マイグレーション、ファイルロック等）や、各モジュールの API 安定化・ドキュメント整備を予定してください。