# CHANGELOG

すべての重要な変更はこのファイルに記載します。
このプロジェクトでは Keep a Changelog の形式に準拠します。
リリース日付は ISO 8601 形式 (YYYY-MM-DD) です。

## [Unreleased]
- 次回リリースの変更点をここに記載します。

## [0.1.0] - 2026-04-18

### Added
- 初期リリースを追加。
- 実行エントリ・起動スクリプトを追加:
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプト。
    - KABUSYS_ENV=paper_trading の場合に paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory を介してブローカークライアントを構築。
    - OrderRepository, OrderManager, RiskManager, Reconciler を組み合わせて Engine を起動。
    - 停止フラグ (data/stop_requested.flag) と PID ファイル (data/execution.pid) をサポート。停止フラグ検知時は安全にエンジン停止を試みる。
    - 起動時にプロセス優先度を "high" に設定。
  - run_monitoring.py
    - SystemMonitor をポーリングする監視用スクリプト。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。不正値・非正の値はデフォルトにフォールバックして警告を出す。
    - 監視は KABUSYS_ENV に関わらず本番 sqlite_path を使用する設計。
    - 停止フラグ (data/stop_requested.flag) を検出してループ終了。

- 設定・環境管理:
  - config.py
    - Settings クラスを追加。環境変数から設定値を安全に取得（必須値のチェック、列挙型のバリデーションなど）。
    - DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH / PID_FILE_PATH 等のデフォルト値を提供。
    - PAPER_FILL_MODE の検証（"instant"|"partial"|"never"|"reject"）。
    - 環境自動ロード機能: プロジェクトルート（.git または pyproject.toml 基準）を探索して .env/.env.local を読み込み（OS 環境変数は保護）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - settings インスタンスをモジュールレベルで提供。

- 設定補助ツール:
  - config_setup.py
    - .env を対話式に作成・更新するウィザード。
    - シークレット項目はマスク表示、選択肢サポート、保存前の確認を実装。
    - .env にヘッダを付加して「絶対に Git にコミットしないこと」を明記して保存。

  - validate_config.py
    - .env と config/*.yaml の設定検証 CLI。
    - 必須環境変数の未設定検出、プレースホルダ値の検出、KABUSYS_ENV / LOG_LEVEL の検証、DB パスの親ディレクトリ存在チェックを実装。
    - PyYAML が未インストールの場合は YAML 検証をスキップして警告を出す。
    - --strict オプションで警告を FAIL 扱いにできる。

- ユーティリティ:
  - logging_setup.py
    - 統一的なロギング設定ユーティリティを追加。
    - stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler（デフォルト logs/<app_name>.log、30日分保持）をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR / 引数による上書き対応。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - process_priority.py
    - psutil を用いたクロスプラットフォームなプロセス優先度設定、CPU affinity 設定ユーティリティを追加。
    - Windows / POSIX（Linux, Darwin, FreeBSD）に対応し、失敗時は警告でスキップ。

- ポートフォリオ構築モジュール:
  - portfolio/portfolio_builder.py
    - 候補選定 (select_candidates)、等配分 (calc_equal_weights)、スコア加重 (calc_score_weights) を実装。スコア合計が 0 の場合等分配にフォールバック。
  - portfolio/risk_adjustment.py
    - セクター集中制限 (apply_sector_cap)、レジーム乗数 (calc_regime_multiplier) を実装。unknown セクターの扱い、レジームごとの乗数（bull/neutral/bear）を提供。
  - portfolio/position_sizing.py
    - 株数決定ロジックを実装（allocation_method: "risk_based" / "equal" / "score"）。
    - 単元株（lot_size）丸め、per-position 上限・aggregate キャップ、cost_buffer による保守的見積り、available_cash に対するスケーリングと端数配分ロジックを実装。

- 分析 / ツール:
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率（fill）、送信率（send）、P95 レイテンシ等を SQLite から集計して PASS/FAIL 判定（閾値はソース内に定義）。
    - CLI オプションで期間 (--from / --to) / DB パス (--db) を指定可能。

- 研究モジュール（骨格）:
  - research/factor_research.py
    - DuckDB を使ったファクター計算の骨格を追加（モメンタム / MA200 / ATR / ボリューム等を想定）。関数インターフェースと定数を定義（実装継続予定）。

- パッケージ情報:
  - __init__.py にて __version__ = "0.1.0" を設定。

### Fixed
- .env パーサーの堅牢化（config.py）:
  - export KEY=val 形式への対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント取り扱い（クォートあり/なしでの差異）を実装。
  - .env 読み込み時に OS 環境変数を保護（protected set）して .env.local による上書きを正しく扱う。
- run_monitoring.py:
  - MONITOR_POLL_INTERVAL のパース不備（非整数や 0/負値）に対してデフォルト値へフォールバックし、警告を出すように変更。
- logging_setup.py:
  - すでにハンドラが設定されている場合は既存ハンドラを flush/close してから削除。二重ログ出力を防止。
- process_priority.py:
  - psutil のプラットフォーム差分（Windows 固有定数の存在しない場合のフォールバック）を扱うようにして、モジュールロードの互換性を向上。

### Security
- config_setup.py で生成される .env に対して「絶対に Git にコミットしないこと」と明記。
- Settings._require() により必須トークンが未設定の場合に ValueError を投げ、明示的に起動エラーとする（秘密情報の未設定による不注意な起動を防止）。

### Notes
- 本リリースは初期版（0.1.0）です。研究モジュールや一部機能は今後のリリースで拡張・安定化予定です。
- DuckDB / SQLite のスキーマ初期化（init_monitoring_db 等）は各スクリプト内で冪等に呼び出す設計になっており、起動順序に依存しないよう配慮しています。
- 実稼働（KABUSYS_ENV=live）での運用時は validate_config の警告（LINE 通知設定や KILL_FLAG_CLEAR_ON_START 設定）を必ず確認してください。

--- 

（注）この CHANGELOG はソースコードの現状から推測して作成しています。実際のリリースノートとして公開する際は、実装者の確認・補足を推奨します。