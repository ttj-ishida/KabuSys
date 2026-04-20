# Changelog

すべての著名な変更点はこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠し、安定版リリースはセマンティックバージョニングに従います。

- リリースノートの形式: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

（次回リリースに向けた変更をここに記載します）

## [0.1.0] - 2026-04-20

初回公開リリース。日本株自動売買システム KabuSys のコア機能と運用ユーティリティを含む最初のパッケージ化です。

### Added
- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックし警告を出力。
    - 監視では KABUSYS_ENV にかかわらず本番用 sqlite_path を使用し、monitoring 用テーブルの初期化を行う。
    - stop flag（data/stop_requested.flag）を監視して安全にループを終了。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は MockBrokerClient を利用し、paper_trading 用 DB（data/paper_trading.db）を使用して本番 DB と分離。
    - 起動時にプロセス優先度を "high" に設定し、停止フラグ検知でエンジンを停止。
    - 実行用 PID ファイルの取り扱い（data/execution.pid）を提供。

- 設定・環境管理
  - config.py
    - .env 自動ロード機能を実装（プロジェクトルートを .git または pyproject.toml から探索）。
    - .env の読み込みロジックは export プレフィックス、クォート、エスケープ、インラインコメントなどを適切に扱う堅牢なパーサを実装。
    - 環境変数の必須チェック機能（_require）。
    - 各種設定プロパティを提供（DB パス、PID/kill flag、閾値、PAPER_FILL_MODE の検証など）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。

  - config_setup.py
    - 対話式ウィザードで .env を生成・更新する CLI を追加。
    - J-Quants / kabu ステーション / DB / ログ設定等の入力支援、既存 .env の読み込み・マスク表示、確認後 .env 書き出しを実装。

  - validate_config.py
    - 起動前に .env と config/*.yaml の設定不備を検出する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在確認、YAML パースチェック（PyYAML が存在しない場合はスキップ）を実装。
    - --strict オプションで警告も失敗扱いにできる。

- ポートフォリオ構築（Portfolio）
  - portfolio/portfolio_builder.py
    - 候補選定（スコア降順 + tiebreaker）、等配分・スコア加重配分を実装。
    - スコア合計が 0 の場合は等分配にフォールバックして警告を出力。

  - portfolio/risk_adjustment.py
    - セクター集中制限 (apply_sector_cap) を実装。既存保有のセクター別時価を計算し、閾値超過セクターの新規候補を除外するロジック。
    - 市場レジームに応じた投下資金乗数 (calc_regime_multiplier) を実装（bull/neutral/bear をサポート、未知レジームは 1.0 でフォールバック）。

  - portfolio/position_sizing.py
    - 発注株数決定ロジックを実装（risk_based / equal / score）。
    - 単元株（lot_size）丸め、1銘柄上限・aggregate cap（利用可能現金）に基づくスケーリング、コストバッファ考慮、端数の優先配分アルゴリズムを組み込み。

  - portfolio/__init__.py
    - 上記関数群の公開 API を整備。

- ユーティリティ
  - utils/logging_setup.py
    - 統一的なログ設定ユーティリティを追加。
    - コンソール出力（stdout）用 StreamHandler と 日次ローテーション（TimedRotatingFileHandler）を root ロガーに設定。
    - LOG_LEVEL / LOG_DIR の解決順を定義。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで稼働。
    - 既存ハンドラは再設定時に一旦閉じて削除して二重設定を防止。

  - utils/process_priority.py
    - Windows / POSIX（Linux, macOS, FreeBSD）を吸収するプロセス優先度設定ユーティリティを追加（high/normal/low）。
    - CPU affinity 固定関数 set_cpu_affinity を提供。
    - 権限不足や未対応 OS の場合は警告を出してスキップ。

- 運用ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均/最大/P95）を集計して PASS/FAIL 判定を出力。
    - デフォルト閾値: 稼働率 >= 99%、成功率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200ms。
    - --from/--to/--db オプションで期間・DB を指定可能。P95 計算、欠損データの取扱いに配慮。

- リサーチ
  - research/factor_research.py
    - DuckDB 接続を前提にモメンタム / Value / Volatility / Liquidity といった定量ファクター計算を設計・一部実装（モジュール化されたファクター計算基盤を提供）。
    - 日数定数やスキャン範囲などを定義（MA200、ATR20、各期間の定義）。

- パッケージメタ
  - __init__.py にバージョン 0.1.0 を設定。

### Changed
- （初回リリースのため「追加」が主。変更履歴は今後ここに記載します）

### Fixed
- （初回リリース時点で既知の致命的バグはなし。各モジュールで入力検証と例外処理を強化。）

### Notes / 運用上の重要点
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD が必須。未設定時は起動時にエラーとなる可能性があります（validate_config で事前チェック推奨）。
- 環境切替:
  - KABUSYS_ENV は development / paper_trading / live のみ有効（大文字・小文字混在は許容し小文字で内部比較）。
  - paper_trading モードでは paper 用 SQLite を使用して本番 DB と完全分離します（PAPER_TRADING_SQLITE_PATH で上書き可能）。
- Kill / Stop フラグ:
  - 実行中に停止させたい場合はプロジェクトの data/stop_requested.flag（スクリプト内で参照）を作成してください。run_execution/run_monitoring はこのフラグを監視して安全に終了します。
  - KILL_FLAG_CLEAR_ON_START 設定は本番環境では 0（自動クリアしない）を推奨。
- ログ:
  - デフォルトのログディレクトリは logs/。環境変数 LOG_DIR で変更可能。ディレクトリ作成に失敗するとファイル出力は無効化されコンソール出力のみになります。
- .env オートロード:
  - デフォルトでプロジェクトルートの .env および .env.local を自動ロードします。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- PAPER_FILL_MODE:
  - paper_trading のモック約定モード設定（instant/partial/never/reject）。無効な値は ValueError を発生させます。

---

今後の予定:
- factor_research の完全実装（ファクター計算の SQL 実装続行）
- 戦略（strategy）・データ取得（data）サブパッケージの追加・拡充
- 単体テスト・CI の整備、ドキュメントの拡充

もしこのリリースノートに不足や訂正があればご指示ください。