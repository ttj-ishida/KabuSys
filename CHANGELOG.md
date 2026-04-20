# Changelog

すべての重要な変更点をここに記録します。フォーマットは「Keep a Changelog」に準拠します。

リリース日はリポジトリ内のコード状態から推定しています。

## [0.1.0] - 2026-04-20

### Added
- 全体
  - 初期パブリッシュ相当の機能群を追加。パッケージバージョンは `__version__ = "0.1.0"`。
  - パッケージ公開時のエクスポートを整理（kabusys パッケージの主要モジュールを __all__ で公開）。

- 起動スクリプト / 実行環境
  - run_execution.py：ExecutionEngine の起動スクリプトを追加。
    - KABUSYS_ENV に応じて paper_trading 用 DB を分離（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）。
    - BrokerClientFactory を用いてブローカークライアントを生成。
    - ExecutionEngine を別スレッドで実行し、data/stop_requested.flag による外部停止検知、実行中の安全停止処理（engine.stop）を実装。
    - PID ファイル管理（data/execution.pid）をサポート。
  - run_monitoring.py：SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグ (data/stop_requested.flag) を検知してループを終了。
    - monitoring 用テーブルの初期化（init_monitoring_db）と sqlite / duckdb 接続を行い確実にクローズする。

- 設定 / 環境変数
  - config.py：Settings クラスを追加。
    - .env 自動ロード機能（プロジェクトルート検出: `.git` または `pyproject.toml` を基準）。
    - `.env` / `.env.local` 読み込み順と OS 環境変数の保護（既存 OS 環境変数は上書きされない）。
    - `.env` 行パーサ（クォート付き値、export プレフィックス、インラインコメント処理など）を実装。
    - 多数の設定プロパティを提供（J-Quants / kabu API / DB パス / モニタリング閾値 / 環境判定等）。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD` による自動ロード無効化オプションを提供。

- 設定ユーティリティ / CLI
  - config_setup.py：対話式 `.env` ウィザードを追加。
    - .env の読み取り・既存値再利用、秘密値マスク、書き込みテンプレートを提供。
    - `.env` ファイルの安全な生成を促すメッセージを出力。
  - validate_config.py：起動前の設定検証ツールを追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL 検証、DB パスや config/*.yaml の存在・パースチェック（PyYAML が無ければ警告）。
    - `--strict` フラグで警告を FAIL 扱いにできる。
    - 本番（live）環境向けの追加ガード（LINE 通知設定・KILL_FLAG_CLEAR_ON_START の警告など）。

- ロギング / プロセス制御
  - utils/logging_setup.py：統一ログ設定ユーティリティを追加。
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）を設定。
    - 既存ハンドラをクリアして二重設定を防止。
    - LOG_LEVEL / LOG_DIR の解決ロジックと、ログディレクトリ作成失敗時のフォールバック（コンソールのみ）を実装。
  - utils/process_priority.py：クロスプラットフォームのプロセス優先度設定ユーティリティを追加。
    - Windows と POSIX（Linux, macOS 等）に対応して nice / priority を設定。権限不足時は警告を出してスキップ。
    - set_cpu_affinity によりプロセスの CPU affinity を固定するヘルパを提供（利用可能なコア数に基づき安全に処理）。

- ポートフォリオ構築（純関数群）
  - portfolio/portfolio_builder.py：
    - select_candidates（スコア降順で上位 N を選択）。
    - calc_equal_weights（等金額配分）。
    - calc_score_weights（スコア比率配分、全スコアが 0 の場合は等金額にフォールバックして警告）。
  - portfolio/risk_adjustment.py：
    - apply_sector_cap（既存保有のセクター比率が上限を超える場合に新規候補を除外。unknown セクターは除外しない）。
    - calc_regime_multiplier（market レジームに応じた投下資金乗数を返す。未知のレジームはフォールバックで 1.0）。
    - セクター上限計算で当日売却予定銘柄をエクスポージャー計算から除外する機能を提供。
  - portfolio/position_sizing.py：
    - calc_position_sizes（allocation_method に応じた株数計算）。
    - risk_based / equal / score の各方式に対応。単元株（lot_size）で丸め、per-stock 上限・aggregate 上限を考慮。
    - cost_buffer（手数料・スリッページの推定）を考慮した保守的見積りと、available_cash を超える場合のスケーリング（残差処理で公平に再配分）を実装。

- リサーチ / ツール
  - research/factor_research.py：ファクター計算モジュールを追加（Momentum / Value / Volatility / Liquidity を想定）。
    - DuckDB 接続を受け prices_daily / raw_financials を参照して計算する設計（関数や定数を定義）。
    - （注）ファイル末尾が途中で切れているため一部未完の可能性あり。
  - tools/paper_verification_report.py：Paper Trading 検証レポート生成ツールを追加。
    - paper_trading DB（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）から稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを集計して判定（PASS/FAIL）。
    - P95 計算、日付フィルタ（--from / --to）対応、閾値を定義して自動判定。

### Changed / Improved
- ロギング初期化時に既存ハンドラを安全に flush/close してから削除するようにして、二重ログ出力を防止。
- logging_setup: ファイル出力が失敗した場合でも StreamHandler は継続するようフォールバックを明確化。
- config の自動ロード処理:
  - OS 環境変数を保護する仕組み（.env.local の上書き時でも OS 環境変数は保護）。
  - export プレフィックスやクォート付き値、インラインコメント等を正しく扱うようパーサを強化。
- run_monitoring / run_execution:
  - DB 接続（sqlite / duckdb）は finally ブロックで確実に close する実装に変更。
  - run_execution は paper_trading 環境で mock ブローカーを利用し DB を完全分離する方針を採用。
- validate_config:
  - config/*.yaml の存在チェックと PyYAML 未インストール時の挙動（警告）を追加。
  - live 環境向けのガード（LINE の未設定、KILL_FLAG_CLEAR_ON_START の危険設定）を追加。
- position_sizing:
  - 投下総額が available_cash を超えた場合のスケーリングと端数処理（lot 単位での再配分）を実装し、より保守的で再現性のある割当を行うよう改善。

### Fixed
- MONITOR_POLL_INTERVAL の不正な値（0 以下や非整数）を検出してログに警告し、デフォルト 60 秒へフォールバックするように修正。
- process_priority / set_cpu_affinity は権限不足や未対応 OS で例外を握りつぶすのではなく警告を出して安全にスキップするように修正。
- .env パースの不具合対応:
  - クォート内のバックスラッシュエスケープ処理対応。
  - インラインコメントを含む非クォート値の扱いの改良。
- paper_verification_report:
  - データが存在しない場合（テーブル未作成やレコード無し）に例外を吐かず N/A 表示やゼロ扱いで出力を続けるように堅牢化。

### Known issues / TODO
- portfolio/risk_adjustment.apply_sector_cap:
  - price が欠損（0.0）の場合にエクスポージャーが過少見積りとなる問題を TODO コメントで認識。将来的に前日終値や取得原価などのフォールバック価格を導入予定。
- research/factor_research.py の末尾が途中で切れており、実装が未完に見える部分があるため要確認（関数の続き・テスト追加が必要）。
- ExecutionEngine / BrokerClient の具体実装（API インターフェイス、MockBrokerClient の挙動）はこの差分からは見えないため、統合テストが必要。
- 一部の機能（例: 銘柄別 lot_size の可変化など）は TODO としてコメントに残されている。将来的な拡張を想定。

---

上記はソースコードから推測可能な変更点・機能をまとめたものです。差分や追加コミットがある場合は該当箇所を追記してください。