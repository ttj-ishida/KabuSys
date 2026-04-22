# Changelog

すべての注目すべき変更点を記録します。  
このファイルは Keep a Changelog の形式に準拠しています。

※コードベースから推測して記載しています。実装上の意図や細部はソースを参照してください。

## [Unreleased]

N/A

## [0.1.0] - 初回リリース (推定)

### Added
- 基本的なアーキテクチャと起動スクリプトを追加
  - run_execution.py: ExecutionEngine 起動用スクリプトを追加。環境に応じて Paper Trading 用 DB を分離し、BrokerClientFactory を使ってブローカークライアントを生成。スレッド上でエンジンを実行し、 data/stop_requested.flag による安全な停止制御、pid ファイル管理を実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。監視は本番用 sqlite_path を環境にかかわらず使用する設計。
- 環境設定・検証のための CLI を追加
  - config_setup.py: .env を対話形式で生成・更新するウィザードを提供。シークレット項目はマスクして表示し、保存前に確認プロンプトを表示。
  - validate_config.py: .env や config/*.yaml の設定を起動前に検証する CLI を追加。必須環境変数やパス、KABUSYS_ENV の妥当性、PyYAML があれば YAML のパース検証を実行。--strict オプションで警告も失敗扱いにできる。
- 設定管理モジュールを追加
  - config.py: .env 自動読み込み（.env/.env.local、OS 環境変数優先、KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化）、クォートや export プレフィックス対応のパーサー、各種設定プロパティ（パス、閾値、Paper Trading 判定等）を提供。PAPER_FILL_MODE の検証なども含む。
- ポートフォリオ構築関連の純粋関数群を追加（DB 非依存）
  - portfolio/portfolio_builder.py: 候補選定（スコア降順）と等金額・スコア加重の重み計算。
  - portfolio/risk_adjustment.py: セクター上限適用ロジック（既存ポジションのセクター露出を計算して候補を除外）および市場レジームに応じた乗数（bull/neutral/bear）を実装。
  - portfolio/position_sizing.py: 各銘柄の発注株数決定（allocation_method = risk_based / equal / score）、lot_size による丸め、aggregate cap によるスケールダウンと端数処理（残差に基づく追加配分）を実装。cost_buffer による保守的見積りを考慮。
- ユーティリティを追加
  - utils/logging_setup.py: ルートロガーの統一セットアップ関数を提供。stdout への StreamHandler と日次ローテート（TimedRotatingFileHandler）でログファイルを出力。LOG_DIR/LOG_LEVEL の解決順、ファイルハンドラ作成失敗時のフォールバックを実装。
  - utils/process_priority.py: psutil を利用したプロセス優先度設定ユーティリティ。Windows/Linux/macOS を吸収する実装、CPU affinity 設定関数も提供。権限不足や未対応 OS では警告を出してスキップする安全設計。
- Paper Trading 向け解析ツールを追加
  - tools/paper_verification_report.py: ペーパートレード用 SQLite DB を解析して稼働率・注文成功率・送信率・レイテンシ（P95 など）を集計し、Pass/Fail 判定を行うレポート生成スクリプトを追加。コマンドライン引数で期間指定や DB パスのオーバーライドが可能。
- research/factor_research.py（ファクター計算モジュール）の基礎を追加
  - DuckDB を使った価格・決算情報ベースのファクター計算方針と定数（モメンタム・MA・ATR 等）を定義。モメンタム計算関数の実装（途中まで含まれる）。

### Changed
- ログポリシー
  - ログの標準出力は stderr ではなく stdout を使用する方針に変更（cron / Task Scheduler でのリダイレクトを考慮）。
  - 日次ローテーション（30日保持）を標準設定として導入。
- DB の取り扱い
  - 監視（monitoring）用は環境にかかわらず本番 sqlite_path を使用する仕様（run_monitoring.py）。
  - 実行（execution）用は KABUSYS_ENV=paper_trading のとき専用の paper_sqlite_path を使用して本番 DB と完全分離する仕様（run_execution.py）。
- .env 読み込みの振る舞い
  - .env/.env.local の読み込み順と上書きルール（OS 環境変数は保護される）を明確化。export プレフィックス、クォート・エスケープ、インラインコメントの扱いをサポート。
- 安全性の強化
  - run_execution.py / run_monitoring.py ともに data/stop_requested.flag を用いた外部からの停止制御をサポート。
  - process_priority の呼び出しは起動直後に行い、失敗してもスクリプト継続できるよう例外をハンドリング。

### Fixed
- 環境変数のパース改善
  - .env パーシングロジックで export 付きやクォート内のバックスラッシュエスケープを正しく扱うようにしたため、特殊文字を含むトークンやコメントの誤認識を防止。
- ログハンドラの重複設定防止
  - setup_logging() で既存ハンドラを flush/close してから削除・再設定するようにし、二重出力やハンドラの重複を防止。
- ポジションサイズ算出の丸め・集約ロジックの堅牢化
  - lot_size 単位の丸め、aggregate cap によるスケーリング、残差分配のロジックを実装し、合計投下資金が available_cash を超えないよう調整。

### Notes / Implementation details
- 多くの機能は外部ライブラリ（psutil / duckdb / PyYAML 等）に依存。存在しない場合は一部機能がスキップまたはフォールバックする実装になっている（例: YAML 検証のスキップ、プロセス優先度設定の警告）。
- Paper Trading 用の挙動（DB 分離、MockBroker の利用、PAPER_FILL_MODE）は環境変数で切り替え可能。デフォルトでは開発モード想定（KABUSYS_ENV=development）。
- 実際のブローカークライアント実装や ExecutionEngine / SystemMonitor の内部処理はこの差分一覧の外にあり、ここでは起動周り・ユーティリティ・純粋関数群の追加・改善に重点を置いている。

---

今後の変更を記録するときはこのファイルを更新してください（Keep a Changelog 準拠）。