CHANGELOG
=========

すべての重要な変更をこのファイルに記録します。  
このファイルは "Keep a Changelog" のスタイルに準拠しています。

フォーマット:
- Unreleased: 今後の変更（現時点では空にしておきます）
- 各リリースは日付付きで「Added / Changed / Fixed / Removed / Security」に分類しています。

Unreleased
----------

- なし

[0.1.0] - 2026-04-19
--------------------

Added
- 実行用スクリプトを追加
  - run_execution.py: ExecutionEngine を起動する CLI スクリプトを提供。
    - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用して paper_trading 用の SQLite（デフォルト: data/paper_trading.db）と分離して動作する。
    - 起動時にプロセス優先度を "high" に設定する仕組みを導入。
    - 停止フラグ (data/stop_requested.flag) と PID ファイル (data/execution.pid) を使用して外部から安全に停止可能。
- 監視用スクリプトを追加
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを提供。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視用 DB（monitoring）は実行環境に関係なく本番の sqlite_path を使用する挙動を明示。
    - 停止フラグ検知によるループ終了、例外発生時のログ出力を実装。
- 設定管理と初期化ツール
  - config.py: 環境変数ラッパー Settings を実装。.env の自動読み込み（プロジェクトルート検出による）や値検証を含む。
    - .env の自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して抑止可能。
    - PAPER_FILL_MODE 等の特定キーのバリデーションや、各種パス（DUCKDB_PATH/SQLITE_PATH 等）を Path 型で提供。
  - config_setup.py: 対話式ウィザードで .env を作成／更新する CLI を追加。
    - シークレット入力のマスク、デフォルト値提示、保存前の確認などを実装。
  - validate_config.py: 起動前の設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリチェック、config/*.yaml の存在とパース検証（PyYAML 利用時）を実装。
    - --strict オプションで警告を失敗扱いにできる。
- ポートフォリオ構築ライブラリを追加 (kabusys.portfolio)
  - portfolio_builder.py
    - select_candidates: スコア降順での銘柄選定（同点時は signal_rank を用いたタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額配分およびスコア加重配分。スコア合計が 0 の場合は等配分にフォールバック。
  - risk_adjustment.py
    - apply_sector_cap: セクター集中上限 (max_sector_pct) を超えるセクターの新規候補除外ロジックを実装。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を実装（未知レジームはフォールバック）。
  - position_sizing.py
    - calc_position_sizes: 複数の配分方式 ("risk_based", "equal", "score") に対応した発注株数算出ロジックを提供。
    - 単元株丸め、per-position 上限・aggregate cap（available_cash に基づくスケーリング）、cost_buffer を用いた保守的コスト見積りを実装。
- ユーティリティ
  - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。
    - コンソール出力は stdout を使用、日次ローテーション（TimedRotatingFileHandler）でログファイルを保存（デフォルト logs/、30日分保持）。
    - 既存ハンドラのクリア処理やログディレクトリ作成のフォールバック処理を実装。
  - utils/process_priority.py: プロセス優先度と CPU affinity 設定ユーティリティを追加。
    - Windows / POSIX の差分を吸収して set_process_priority(level) を提供（"high"/"normal"/"low"）。
    - set_cpu_affinity(cpu_count) で最初の N コアにピン留め（未対応 OS / 権限不足時は警告ログでスキップ）。
- 開発者向けツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等を集計・判定（閾値を定義して PASS/FAIL 判定）。
    - --from / --to / --db オプションで期間・DB を指定可能。
- リサーチモジュール（下地）
  - research/factor_research.py: ファクター計算モジュールの骨組みを追加（Momentum/Value/Volatility/Liquidity 指標の実装方針と定数を含む）。DuckDB を利用する設計。

Changed
- 環境変数読み込みの改善（config.py）
  - .env のパースを強化：export プレフィックス対応、クォートされた値のバックスラッシュエスケープ対応、インラインコメントの扱い等を実装。
  - 自動ロード順序を OS 環境変数 > .env.local > .env に明確化。OS 環境変数は保護され上書きされない。
- run_monitoring/run_execution の DB 接続ロジック明確化
  - 監視側は常に sqlite_path（monitoring DB）を使用する（環境に依らない）。
  - 実行側は paper_trading 環境時に専用 paper_sqlite_path を利用して本番 DB と分離。

Fixed
- process_priority の実行時例外をハンドリング
  - 権限不足やプラットフォーム差異でのエラー（psutil.AccessDenied 等）をキャッチして警告を出すように変更し、起動阻害を防止。
- logging_setup のディレクトリ作成失敗時のフェイルセーフ
  - ログディレクトリ作成に失敗してもコンソール出力のみで継続するように実装。

Removed
- なし

Security
- なし

Notes / その他
- 設定関連の必須キー（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）や本番運用時の注意点（KILL_FLAG_CLEAR_ON_START の扱い、LINE 通知設定の確認など）は validate_config で起動前にチェック可能。
- 一部モジュール（例: research/factor_research.py）は実装途中の部分があり、関数の完全実装は今後のリリースで追加予定。

開発者向け
- package のバージョンは __init__.py にて 0.1.0 に設定されています。今後の変更は Unreleased セクションに順次記録してください。