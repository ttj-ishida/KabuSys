# Changelog

すべての注目すべき変更を記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

注: 以下の履歴は提供されたコードベースの内容から推測して作成しています。実際のコミット履歴や意図と異なる可能性があります。

## [Unreleased]

- 今後の変更: ドキュメントやテストの追加、factor_research の未完部分の実装、細かなバグ修正やパフォーマンス改善を予定。

## [0.1.0] - 2026-04-19

初回リリース。日本株自動売買システム「KabuSys」の基本コンポーネントを実装。

### Added
- 基本パッケージ定義
  - パッケージメタ: `src/kabusys/__init__.py` にバージョン `0.1.0` を追加。

- 起動スクリプト
  - 実行エンジン起動スクリプト `src/kabusys/run_execution.py`
    - プロセス優先度を高く設定して実行。
    - 環境に応じて paper_trading 用 DB を分離（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）。
    - BrokerClientFactory によるブローカークライアント生成。
    - ExecutionEngine をスレッドで起動し、停止フラグ（data/stop_requested.flag）で安全に停止可能。
    - PID ファイル管理（data/execution.pid）。
  - 監視ループ起動スクリプト `src/kabusys/run_monitoring.py`
    - SystemMonitor を定期ポーリング。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグ検知でループを安全終了。
    - 監視は環境にかかわらず本番用 sqlite_path を使用する設計。

- 設定管理・初期化ツール
  - `src/kabusys/config.py`
    - .env 自動読み込み（プロジェクトルートを検出して .env / .env.local を優先順で読み込み）。
    - .env パースロジックの実装（export 形式, 引用符・エスケープ・インラインコメント対応）。
    - Settings クラスに各種プロパティ（DB パス、KABUSYS_ENV 判定、paper_trading 用設定、閾値等）を提供。
  - 対話式設定ウィザード `src/kabusys/config_setup.py`
    - .env の作成・更新を対話的に支援。
    - デフォルト値、選択肢、シークレット入力対応、保存確認を実装。
  - 設定検証 CLI `src/kabusys/validate_config.py`
    - 必須環境変数の確認、KABUSYS_ENV / LOG_LEVEL の値検証、DB パスや config/*.yaml の存在・パース検査（PyYAML があれば内容検証）。
    - `--strict` オプションで警告をエラー扱いにできる。

- ポートフォリオ構築（純粋関数群） `src/kabusys/portfolio/`
  - 候補選定・重み算出: `portfolio_builder.py`
    - select_candidates: スコア降順、同点は signal_rank でブレーク。
    - calc_equal_weights / calc_score_weights（スコア全0 の場合は等配分にフォールバック）。
  - リスク調整: `risk_adjustment.py`
    - apply_sector_cap: セクターごとの既存エクスポージャーを計算して新規候補を除外するロジック（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）を返す。未知レジームはフォールバックして 1.0。
  - ポジションサイジング: `position_sizing.py`
    - 複数の allocation_method をサポート（risk_based / equal / score）。
    - lot_size（単元株）に合わせた丸め、per-stock 上限・aggregate cap のスケーリング、コストバッファ（手数料・スリッページの見積り）に対応。
    - 利用可能現金を超えた場合はスケールダウンし、残余で端数を lot_unit 単位で配分するロジックを実装。

- ユーティリティ
  - ログ設定 `src/kabusys/utils/logging_setup.py`
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次・30日保持）を追加。
    - 既存ハンドラのクリア、ログディレクトリ自動作成、環境変数 LOG_DIR/LOG_LEVEL の解決順を実装。
  - プロセス優先度/CPU affinity ユーティリティ `src/kabusys/utils/process_priority.py`
    - Windows/Linux/macOS を抽象化してプロセス優先度を設定（high/normal/low）。
    - CPU affinity を最初 N コアに固定する機能を提供。
    - 権限不足や未対応 OS を考慮した安全なフォールバックと警告。

- 監視・レポート・検証ツール
  - Paper Trading 検証レポート生成スクリプト `src/kabusys/tools/paper_verification_report.py`
    - system_status / trade_logs / risk_logs テーブルを参照して稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）等を出力。
    - PASS/FAIL 判定基準（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms など）を実装。
    - 日付フィルタ（--from/--to）と DB パス指定（--db / 環境変数）対応。
  - 監視 DB 初期化フック `monitoring.monitoring_db.init_monitoring_db`（起動スクリプトから呼び出し、冪等に監視テーブルを保証）を起動箇所で利用。

- 研究用モジュール（骨子）
  - ファクター計算モジュール `src/kabusys/research/factor_research.py`
    - Momentum / Value / Volatility / Liquidity 計算の設計と定数（窓長等）を実装。DuckDB 経由で prices_daily / raw_financials を参照する設計。
    - モジュール内にモメンタム計算関数の雛形（calc_momentum）を実装開始（コード断片あり、未完の可能性あり）。

- パッケージのエクスポート
  - `src/kabusys/portfolio/__init__.py` で主要関数をまとめて公開。

### Changed
- ログ出力の取り扱い
  - コンソール出力を stdout に統一（cron/Task Scheduler 等でリダイレクトしやすくするため）。
  - ログハンドラの重複設定を防止するため、既存ハンドラは起動時に一度 flush/close の上で削除。

- .env の自動読み込みポリシー
  - プロジェクトルート検出は .git または pyproject.toml を基準とし、CWD に依存しないよう改善。
  - OS 環境変数を保護する機構（.env 読み込み時に protected set を使用）を実装。

### Fixed
- 環境変数パースの堅牢化
  - 引用符付きの値内でのバックスラッシュエスケープ、インラインコメントの無視、export プレフィックス対応などを強化。
- 監視/実行のリソースクリーンアップ
  - run_monitoring/run_execution の finally 節で SQLite / DuckDB コネクションを確実にクローズ。

### Known issues / Notes
- risk_adjustment.apply_sector_cap 内で price が欠損（0.0）の場合の挙動に TODO コメントあり。将来的に前日終値等のフォールバック実装が必要。
- research/factor_research.py はファイル末尾で計算関数の実装が途中で切れている（未完）。本機能はまだ開発中の可能性あり。
- 一部の外部モジュール（例: PyYAML）が存在しない環境では config ファイルの内容検証をスキップする仕様。依存関係の明示的な管理が推奨される。

### Security
- 機密情報（J-Quants リフレッシュトークン、kabu API パスワードなど）は .env に格納する前提。`.env` を Git にコミットしない旨を config_setup のテンプレートで明記。

## 参考
- 実装ファイル一覧（主なもの）
  - run_monitoring.py, run_execution.py, config.py, config_setup.py, validate_config.py
  - utils/logging_setup.py, utils/process_priority.py
  - portfolio/* (portfolio_builder, risk_adjustment, position_sizing)
  - tools/paper_verification_report.py
  - research/factor_research.py

(以上)