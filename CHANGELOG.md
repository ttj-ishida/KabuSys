# CHANGELOG

All notable changes to this project will be documented in this file.

フォーマットは「Keep a Changelog」に準拠しています。
https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

- （現在差分はありません。初回リリースは [0.1.0] を参照してください）

## [0.1.0] - 2026-04-19

Added
- 基本アプリケーション構成と多数のユーティリティ・モジュールを初回実装。
  - パッケージバージョン: `kabusys.__version__ = "0.1.0"`
- 環境変数／設定管理
  - .env 自動ロード機能を実装（プロジェクトルート検出: .git / pyproject.toml を探索）。
  - .env のパース実装を強化:
    - `export KEY=val` 形式対応
    - シングル／ダブルクォート内のバックスラッシュエスケープ処理対応
    - クォート無し行でのインラインコメント処理（コメント前が空白/タブの場合のみ）
  - 自動ロード無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
  - `Settings` クラスを追加し、環境変数から各種設定値（DBパス、APIトークン、閾値、実行環境など）を取得する統一 API を提供。
  - 必須環境変数未設定時に明示的なエラーを投げる `_require()` を実装。
  - Paper Trading 関連設定 (`PAPER_FILL_MODE`, `PAPER_TRADING_SQLITE_PATH`) の読み取りとバリデーションを実装。
- 設定関連 CLI
  - 対話式環境設定ウィザード `kabusys.config_setup` を実装:
    - .env の初期作成／更新を対話で支援。
    - シークレット項目はマスク表示、既存値の再利用をサポート。
  - 設定検証ツール `kabusys.validate_config` を実装:
    - 必須環境変数の存在チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在確認、config/*.yaml の存在・（PyYAML があれば）パース検証を行う。
    - `--strict` オプションで警告を FAIL 扱いにできる。
- 実行系スクリプト
  - 実取引用 ExecutionEngine 起動スクリプト `run_execution.py` を追加:
    - プロセス優先度を"high"に設定。
    - `Settings.is_paper` に応じて paper_trading 用の専用 SQLite DB（デフォルト: `data/paper_trading.db`）を使用し、本番 DB と分離。
    - `BrokerClientFactory` を介してブローカークライアントを生成（paper/live の切り替え想定）。
    - OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine の組み立てと実行スレッド管理を実装。
    - 停止フラグファイル検出による安全停止機構を実装（`data/stop_requested.flag`）。
  - 監視用ポーリングループ起動スクリプト `run_monitoring.py` を追加:
    - 環境変数 `MONITOR_POLL_INTERVAL`（秒）でポーリング間隔を上書き可能（デフォルト 60 秒、0 以下や不正値はデフォルトにフォールバック）。
    - 監視用途の DB 初期化を実行し、Monitoring は環境にかかわらず本番用 `sqlite_path` を使用する設計。
    - 停止フラグ検知による終了、例外時のログ出力と次ポーリング継続を実装。
- モニタリング / DB 初期化
  - 監視テーブルを保証する `init_monitoring_db`（モジュール呼び出し）が組み込まれ、起動時に冪等に実行される想定。
- ロギングユーティリティ
  - `kabusys.utils.logging_setup.setup_logging` を実装:
    - stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler をルートロガーに設定。
    - ログディレクトリの自動作成、作成失敗時にはファイル出力をスキップして stdout のみで継続。
    - 環境変数 `LOG_DIR` / `LOG_LEVEL` を尊重。重複ハンドラ設定を防ぐため既存ハンドラをクリアして再設定する。
- プロセス優先度／CPU affinity ユーティリティ
  - `kabusys.utils.process_priority` を実装:
    - Windows と POSIX(Linux/macOS/FreeBSD) を吸収して `set_process_priority("high"|"normal"|"low")` を提供。権限不足や未実装環境では警告を出して安全にスキップ。
    - `set_cpu_affinity(cpu_count)` により先頭 N コアにピン留め可能（未対応環境では警告）。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`:
    - 候補選定 `select_candidates`（スコア降順、タイブレークに signal_rank）を実装。
    - 等金額配分 `calc_equal_weights` とスコア正規化配分 `calc_score_weights`（スコア全0時は等金額にフォールバック）を実装。
  - `kabusys.portfolio.risk_adjustment`:
    - セクター集中制限 `apply_sector_cap`（既存ポジションからセクター別エクスポージャを計算し、上限超過セクターの新規候補を除外。unknown セクターは除外対象外）を実装。
    - レジーム乗数 `calc_regime_multiplier`（"bull"/"neutral"/"bear" をマップ、未知レジームは警告して 1.0 にフォールバック）を実装。
  - `kabusys.portfolio.position_sizing`:
    - 各銘柄の発注株数算出 `calc_position_sizes` を実装（allocation_method: "risk_based" / "equal" / "score" をサポート）。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（available_cash 超過時のスケールダウンと残差処理）を実装。
    - コストバッファ考慮、価格欠損時のスキップ、現保有との差分計算などの実務的なロジックを導入。
- リサーチ（ファクター計算）下地
  - `kabusys.research.factor_research` にモメンタム／MA／ATR／流動性等のファクター計算設計を実装（DuckDB 接続を受けて prices_daily / raw_financials を参照する方針）。モジュールは関数の骨組みと定数を備える（本スナップショットは実装途上）。
- Paper Trading 検証ツール
  - `kabusys.tools.paper_verification_report` を実装:
    - Paper Trading 用 SQLite（デフォルト: `data/paper_trading.db`）から各種指標（稼働率、注文成功率、送信率、P95レイテンシなど）を集計してレポート出力。
    - しきい値（稼働率 99%、成功率 90% 等）を用いた PASS/FAIL 判定を提供。
    - 日付フィルタ（--from / --to）と `--db` オプションをサポート。
- DB 接続
  - sqlite3（監視・paper）と duckdb を組み合わせた設計。起動スクリプトは両方の接続を確立し、終了時に確実にクローズする。

Changed
- （初回リリースのため過去の変更履歴は無し）

Fixed
- 環境変数パースやログディレクトリ作成等でのエラーを受けて、安全にフォールバックする実装を多数追加（例: 不正な MONITOR_POLL_INTERVAL、ログディレクトリ作成失敗、psutil による優先度設定失敗等で例外ではなく警告で継続）。

Deprecated
- なし

Removed
- なし

Security
- 機密情報（J-Quants / kabu API パスワード等）は .env へ格納する設計。ウィザードではシークレット項目をマスクして表示。

Notes / Known limitations
- `research.factor_research` は骨組みが含まれますが、完全実装は継続作業が必要（ファイル末尾がスナップショットで切れている箇所あり）。
- position sizing 等のロジックは現場向けのデフォルト値（例: lot_size=100, risk_pct=0.005 等）を持ちます。実運用前に設定ファイルやパラメータの調整を推奨します。
- セクターエクスポージャ計算で価格情報が欠損（0.0）の場合、過少評価される可能性がある点は TODO コメントで記載されており、将来的にフォールバック価格を導入する予定です。

-- end --