# Changelog

すべての注目すべき変更をこのファイルに記録します。
フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを使用します。

## [Unreleased]

- なし

## [0.1.0] - 2026-04-23

初回公開リリース。以下の主要機能・ユーティリティ群を含みます。

Added
- 基本アプリケーションパッケージを追加
  - kabusys パッケージ本体（__version__ = 0.1.0）。
- 環境設定・ロード
  - .env 自動読み込み機能（プロジェクトルート検出: .git 或いは pyproject.toml）。
  - .env/.env.local の読み込み順・上書きポリシー（OS 環境変数保護）。
  - 高度な .env パーサ実装（export KEY=val 対応、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメント処理）。
  - Settings クラスを通じた環境変数アクセスラッパー（各種デフォルト値・バリデーション含む）。
  - 環境変数の必須チェック関数（_require）。

- 設定支援 CLI
  - config_setup: 対話式ウィザードで .env を新規作成 / 更新する機能。
    - 推奨項目・説明・デフォルト値・シークレットマスク表示付き。
  - validate_config: 起動前検証ツール（必須環境変数、KABUSYS_ENV、ログレベル、DB パス、config/*.yaml の存在と YAML パース等）。
    - --strict オプションで警告も失敗扱いにできる。

- 実行用スクリプト / デーモン系
  - run_execution: ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV=paper_trading の場合は Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）と MockBrokerClient を利用し、本番 DB と分離。
    - プロセス優先度を起動時に設定（set_process_priority("high")）。
    - 停止フラグ（data/stop_requested.flag）監視による安全停止。
    - 実行中の PID を data/execution.pid に保存（Engine 側での pid_file 指定）。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔上書き可能（デフォルト: 60秒）。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する旨の明示。
    - 停止フラグ監視による終了、例外発生時のログ保持と次ポーリング継続。

- 監視関連
  - monitoring DB 初期化ヘルパー（init_monitoring_db）の呼び出しを各スクリプトに統合して冪等性を確保。

- ロギング・運用ユーティリティ
  - logging_setup: 統一ログ設定ユーティリティを追加
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）をルートロガーに設定。
    - LOG_DIR/LOG_LEVEL の解決順と失敗時のフォールバック（ディレクトリ作成失敗時はコンソールのみで継続）。
    - stdout を使用することで外部スケジューラでのリダイレクト取り扱いを考慮。
  - process_priority: プラットフォーム非依存のプロセス優先度設定ユーティリティ
    - Windows / POSIX（Linux, macOS, FreeBSD）を吸収する実装。
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。
    - パーミッション不足や未対応 OS では安全にスキップして警告を出力。

- ポートフォリオ構築ライブラリ（純粋関数群、DB 参照なし）
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルをスコア降順でソートして上位 N を選定（signal_rank によるタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等分配・スコア加重配分。スコア合計が 0 の場合は等分にフォールバック。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中制限ロジック（既存保有のセクター比率が閾値を超えている場合、新規候補を除外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear -> 1.0/0.7/0.3、未知レジームはフォールバック1.0）。
  - portfolio.position_sizing
    - calc_position_sizes: 発注株数算出ロジック（allocation_method: "risk_based" / "equal" / "score"）。
      - 単元株（lot_size）丸め、1銘柄上限・aggregate cap（available_cash）によるスケーリング、cost_buffer を考慮した保守的見積り。
      - 価格欠損ハンドリング（価格未取得銘柄はスキップ）。
      - スケールダウン時の残差処理により再配分を行う実装。

- リサーチ（ファクター計算）
  - research.factor_research（モメンタム等のファクター計算の骨組み）
    - DuckDB 接続を受けて prices_daily / raw_financials を参照し、モメンタム（1M/3M/6M）、MA200 乖離、ATR、流動性等を算出する設計方針を実装開始（calc_momentum 等を含む）。

- ツール
  - tools.paper_verification_report: Paper Trading 用検証レポート生成スクリプト
    - 稼働率、注文成功率（fill rate）、送信率、P95 レイテンシ等を集計し PASS/FAIL 判定を出力。
    - CLI 引数 --from/--to/--db をサポート。PAPER_TRADING_SQLITE_PATH による DB 指定対応。
    - デフォルト閾値を定義（稼働率 99%、fill 90%、send 95%、P95 レイテンシ 200ms）。
    - p95 計算・各種クエリの例外ハンドリング（テーブル未存在時に N/A 扱い）。

Changed
- なし（初回リリースのためすべて追加）

Fixed
- なし（初回リリース）

Notes / 運用上の注意
- 環境変数に依存する設定が多く存在するため、初回起動前に config_setup による .env 作成と validate_config による検証を推奨します。
- run_monitoring は MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を制御できます。不正値（0 以下も含む）はログ警告の上でデフォルト (60 秒) にフォールバックします。
- run_execution は paper_trading モードで paper_trading.db を使い、本番 DB とデータを分離します。実運用時に KABUSYS_ENV=live を設定する際は validate_config の警告に従って LINE 通知などを設定してください。
- process_priority や CPU affinity の設定は権限に依存します。失敗時はログに警告が残り、処理は継続します。

---

今後の予定（例）
- factor_research の完全実装（Volatility / Value / Liquidity ファクターの SQL 実装）
- ExecutionEngine / Broker クライアント群の追加テストとリスク評価の拡張
- 単体テスト・CI 導入、型チェックの強化

-----