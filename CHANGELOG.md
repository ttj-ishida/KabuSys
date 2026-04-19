Keep a Changelog
=================

すべての重要なリリース変更はこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠します。

フォーマット:
- 変更はカテゴリ別（Added, Changed, Fixed, Deprecated, Removed, Security）で記載
- 日付は ISO 8601 形式

Unreleased
---------

（今後の変更をここに記載）

0.1.0 - 2026-04-19
-----------------

初回公開リリース。システム全体の起動スクリプト、設定管理、検証ツール、ポートフォリオ構築ユーティリティ、監視・検証ツール群などを含む。

Added
- 全体
  - パッケージ初期リリース（kabusys v0.1.0）。
  - パッケージメタ情報を src/kabusys/__init__.py に追加（__version__ = "0.1.0"）。
- 設定・環境
  - Settings クラスによる環境変数ベースの設定管理を追加（src/kabusys/config.py）。
    - J-Quants / kabuステーション / LINE / DB パス / 監視閾値などのプロパティを提供。
    - KABUSYS_ENV, LOG_LEVEL 等のバリデーションを実装。
  - .env 自動ロード機能（プロジェクトルート判定: .git または pyproject.toml）を追加。
    - 読み込み優先順位: OS 環境 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - .envファイル対話式ウィザードを追加（src/kabusys/config_setup.py）。
    - 初期 .env 作成 / 更新を支援。secret 項目はマスク表示。
    - --env-file オプションで保存先指定可能。
- 設定検証
  - 設定検証 CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在とパース（PyYAML があれば内容検証）を実施。
    - --strict オプションで警告も失敗扱いにできる。
    - 本番 (live) 向けガード（LINE トークン未設定や KILL_FLAG_CLEAR_ON_START の危険設定の警告）を実装。
- 起動スクリプト
  - ExecutionEngine 起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite を使用して本番 DB と分離。
    - BrokerClientFactory を介したブローカー選択、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - 停止フラグ (data/stop_requested.flag) 検出で安全に停止。
    - 実行中はデーモンスレッドで engine.run_session を実行し、停止フラグを監視してエンジンを停止。
  - SystemMonitor 起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用して監視テーブルを管理。
    - 停止フラグ (data/stop_requested.flag) 検出でループ終了。
    - check_once() 実行中の例外を捕捉してロギングしループ継続。
- ロギング・プロセス制御ユーティリティ
  - 統一ログ設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - stdout への StreamHandler と日次ローテートファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。
    - LOG_DIR / LOG_LEVEL / 引数で上書き可能。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
  - プロセス優先度・CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows と POSIX（Linux/Mac/FreeBSD）を吸収して nice 値 / priority を設定。
    - set_cpu_affinity による CPU コア数固定をサポート（権限不足等は警告してスキップ）。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - 候補選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates, calc_equal_weights, calc_score_weights を提供。
    - 同点時のタイブレーク規則（score 降順、signal_rank 昇順）実装。
    - スコア全てが 0 の場合のフォールバック警告。
  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap により既存ポジションのセクター比率超過時に新規候補を除外。
    - calc_regime_multiplier により "bull/neutral/bear" に応じた投下資金乗数を返却（未知の値は警告して 1.0 フォールバック）。
  - 株数決定・リスク制限・単元丸め（src/kabusys/portfolio/position_sizing.py）
    - allocation_method に "risk_based"/"equal"/"score" をサポート。
    - lot_size（単元）で丸め、max_position_pct と aggregate cap（available_cash）によるスケーリングを実装。
    - cost_buffer を使った保守的なコスト見積り（スリッページ・手数料考慮）により配分を調整。
    - スケーリング後の残差は fractional remainder を用いて lot 単位で追加配分するアルゴリズムを実装。
- 研究モジュール
  - ファクター計算モジュールの骨格を追加（src/kabusys/research/factor_research.py）。
    - モメンタム / MA / ATR / ボリューム等の計算方針を記述（DuckDB 接続を受けて prices_daily, raw_financials を参照する設計）。
    - P95 等の計算用ユーティリティを実装（ファイル途中で関数が続く想定）。
- ツール
  - Paper Trading 検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - 稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）等を算出して PASS/FAIL を判定するレポートを標準出力に出力。
    - フィルタ期間 (--from / --to)、DB パス (--db) 指定、PAPER_TRADING_SQLITE_PATH 環境変数対応。
    - デフォルト閾値を定義（稼働率 99%、注文成功率 90% 等）。
- その他
  - tools パッケージ初期化ファイルを追加（src/kabusys/tools/__init__.py）。
  - package-level portfolio エクスポートを実装（src/kabusys/portfolio/__init__.py）。

Changed
- 設定読み込みの扱い
  - .env の読み込みロジックが詳細化され、コメント・引用・エスケープ処理を正しく扱うようになった（export KEY=... 形式もサポート）。
  - .env の読み込み時に既存の OS 環境変数を保護する機能（protected set）を追加し、.env.local を override=True で上書き可能にした。

Fixed
- .env パーサに関する堅牢化
  - 引用符あり/なしのケースでインラインコメントやバックスラッシュエスケープを正しく処理するように改善。
- ロギング初期化の二重登録防止
  - setup_logging() が既存ハンドラを flush/close してから再設定するようにして二重出力を防止。

Security
- .env の扱いに関する注意喚起を README 相当の .env 出力ヘッダに明記（.env を絶対に Git にコミットしない旨）。

Notes / Migration
- 起動・運用
  - 監視（run_monitoring）は常に本番用の sqlite_path（SQLITE_PATH）を参照します。テスト用に監視データを分離したい場合は環境変数を適切に設定してください。
  - 実行エンジン（run_execution）は KABUSYS_ENV=paper_trading の場合に paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と完全分離します。
  - 停止フラグ: data/stop_requested.flag を作成すると監視ループ・実行エンジン起動を停止します。kill/停止の運用はこのフラグファイルで制御します。
- 環境変数
  - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD。（validate_config で検出可能）
  - デフォルト:
    - DUCKDB_PATH: data/kabusys.duckdb
    - SQLITE_PATH: data/monitoring.db
    - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
    - LOG_LEVEL: INFO
    - MONITOR_POLL_INTERVAL: 60（run_monitoring 用）
  - PAPER_FILL_MODE の有効値は "instant" / "partial" / "never" / "reject"（Settings でバリデート）。
- ログ
  - デフォルトでは logs/<app_name>.log に日次ローテートで出力。LOG_DIR 環境変数で変更可能。
  - ログディレクトリ作成失敗時はファイル出力を無効化しコンソールのみで継続するため、権限周りの問題で起動が止まることはありません。

開発者向け補足
- プロジェクトルート探索は __file__ を起点に親ディレクトリを走査して .git または pyproject.toml を参照するため、パッケージ配布後でも CWD に依存しない動作を想定しています。
- process_priority は psutil を利用。権限不足や未対応 OS の場合は警告を出して安全にスキップします。

今後の予定（例）
- research.factor_research の完実装（完全なファクター集計ロジックの追加）。
- ExecutionEngine 周りのテスト用モックと CI 連携の強化。
- 各種設定のドキュメント化（config/*.yaml のテンプレート生成スクリプト強化）。

--- 

変更点や追加機能に関して不明点や補足の必要があれば、どの部分について詳しく記載するか指示してください。