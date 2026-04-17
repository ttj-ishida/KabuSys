# Changelog

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠しています。

すべてのバージョンはセマンティックバージョニングに従います。

## [0.1.0] - 2026-04-17

Added
- 初期リリース: KabuSys パッケージを導入（src/kabusys/__init__.py）。
- 環境設定・読み込み
  - Settings クラスによる環境変数ラッパーを追加（src/kabusys/config.py）。.env/.env.local の自動読み込み機能を提供し、OS 環境変数は保護される（.env.local は上書き可）。
  - .env ファイルの柔軟なパーサを実装（クォート、バックスラッシュエスケープ、インラインコメント処理に対応）。
  - 各種設定値の検証ロジック（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）を備えるプロパティを提供。
- 設定関連 CLI
  - 対話式環境設定ウィザードを追加（src/kabusys/config_setup.py）。.env の初期作成・更新を支援。
  - 設定検証ツールを追加（src/kabusys/validate_config.py）。必須環境変数・パス・config/*.yaml の存在・パースなどをチェック。`--strict` オプションで警告も失敗扱いに。
- 実行・監視ランチャー
  - ExecutionEngine 起動スクリプトを追加（src/kabusys/run_execution.py）。
    - 起動直後にプロセス優先度を "high" に設定。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用の専用 SQLite を使用し、本番 DB と分離。
    - BrokerClientFactory を用いて実際のブローカークライアントまたはモックを選択。OrderRepository、OrderManager、RiskManager、Reconciler を組み立てて ExecutionEngine をスレッドで起動。停止フラグ検知で安全停止。
    - デフォルトの RiskConfig (max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 関連, max_drawdown 等) を設定。
  - SystemMonitor 起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値は警告してデフォルトを使用）。
    - 監視は環境にかかわらず本番 sqlite_path を使用して監視テーブルを初期化。
    - 停止フラグ検知でループを終了。
- ポートフォリオ構築（純粋関数群）
  - 候補選定と重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: スコア降順、同点は signal_rank でタイブレーク。
    - calc_equal_weights / calc_score_weights: スコア合計が 0 の場合は等配分にフォールバック（警告出力）。
  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 既存保有のセクター暴露を計算して新規候補を除外（unknown セクターは除外対象外）。
    - calc_regime_multiplier: 'bull'/'neutral'/'bear' に応じた投下資金乗数を提供。未知レジームはフォールバック（警告）。
  - 株数決定・リスク制限（src/kabusys/portfolio/position_sizing.py）
    - allocation_method に応じた株数計算 ("risk_based", "equal", "score")、単元株（lot_size）丸め、per-position 上限・aggregate cap、cost_buffer を考慮した保守的推定とスケーリング。
    - aggregate cap 超過時のスケールダウンと残余を用いた lot 単位での再配分ロジックを実装。
- 研究用ファクター計算
  - ファクター計算モジュールを追加（src/kabusys/research/factor_research.py）。
    - モメンタム（mom_1m, mom_3m, mom_6m, ma200_dev）やボラティリティ（ATR 等）、流動性指標を DuckDB の prices_daily 等のテーブルから計算する関数を実装。
- ユーティリティ
  - プロセス優先度・CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX の差分を吸収し psutil 経由で優先度/affinity を設定。権限不足や未サポート環境では警告でスキップ。
- Paper Trading 検証ツール
  - ペーパー取引用検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）等を集計し、定義済み閾値と比較して PASS/FAIL を判定。期間指定オプション（--from, --to）あり。
- DB 接続
  - DuckDB を分析用途で利用（各種モジュールが duckdb 接続を受け取る）。
  - 監視テーブル初期化用 init_monitoring_db 呼び出しを各ランチャーで実行（冪等）。

Changed
- 環境ファイル読み込みの優先順位: OS 環境変数 > .env.local > .env（.env.local は override=True により上書き）。
- .env パースの堅牢化: export プレフィックス対応、クォート / エスケープシーケンスの処理、インラインコメント取り扱いを改善。

Fixed
- 環境変数・設定の検出と警告
  - validate_config のチェックで、KABUSYS_ENV=live 時に LINE 通知未設定や KILL_FLAG_CLEAR_ON_START の危険な設定を警告するようにした。

Notes
- 監視（run_monitoring）は明示的に production の sqlite_path を使用する設計（監視データは環境に依らず本番 DB を想定）。
- paper_trading は本番 DB と完全に分離するため、専用の paper_trading SQLite（PAPER_TRADING_SQLITE_PATH）を利用。
- 一部の機能はプラットフォーム権限や外部ライブラリ（psutil, duckdb, PyYAML など）に依存します。利用環境に応じてインストールと権限設定を行ってください。

今後の予定（例）
- 銘柄ごとの lot_size をマスタ化して対応（position_sizing の TODO）。
- apply_sector_cap の価格欠損時フォールバックロジック追加（前日終値や取得原価の使用）。
- factor_research の追加ファクター・最適化とドキュメント整備。

--- 

この CHANGELOG はコードベースから推測して作成しています。実際のリリースノート作成時は差分コミットや PR の説明を元に適宜修正してください。