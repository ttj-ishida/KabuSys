# Changelog

すべての変更は Keep a Changelog の形式に従い、SemVer を採用します。  
日付はリリース日を示します。

## [0.1.0] - 2026-04-23

### 追加
- 初回の公開リリース。KabuSys 自動売買フレームワークの基本機能を実装。
- 実行/監視ランナー
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。KABUSYS_ENV に応じて paper_trading 用の専用 SQLite（data/paper_trading.db）を使い、MockBrokerClient を切り替え可能。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は本番 sqlite_path を使用。
  - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）による外部制御に対応。
- 環境設定・検証
  - config_setup.py: .env を対話式に作成/更新するウィザードを追加（秘密値のマスク、既存値の再利用）。
  - validate_config.py: 起動前に .env と config/*.yaml の基本的な妥当性をチェックする CLI を追加（--strict オプションあり）。
  - config.py: 環境変数の自動読み込み（.env / .env.local）と Settings クラスを実装。必須値チェックやPaper/Live/Dev 切替、各種パス・閾値を提供。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定（スコア降順）、等金額配分、スコア加重配分を実装。
  - portfolio/position_sizing.py: 複数の配分方式（risk_based / equal / score）に基づく株数算出、単元株（lot_size）での丸め、aggregate cap（利用可能現金に基づくスケーリング）を実装。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を追加。
  - portfolio/__init__.py: 主要 API をエクスポート。
- 実行ロジック周辺コンポーネント
  - run_execution が利用する OrderRepository / OrderManager / RiskManager / Reconciler 等の呼び出し側を想定した起動処理を実装（依存コンポーネントの組み立てと ExecutionEngine の起動制御）。
- ユーティリティ
  - utils/logging_setup.py: ルートロガーへ StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション）を設定する統一的なロギングセットアップを追加。ログディレクトリ作成に失敗した場合はファイル出力をスキップ。
  - utils/process_priority.py: Windows/Linux（POSIX）間の差分を吸収するプロセス優先度設定ユーティリティ（set_process_priority）と CPU affinity 設定（set_cpu_affinity）を追加。権限不足時は警告を出してスキップ。
- 監視 DB 初期化
  - monitoring/monitoring_db.py（起動時に init_monitoring_db を呼び出すことで監視用テーブルの存在を保証する仕組みを想定）。
- 分析・検証ツール
  - tools/paper_verification_report.py: Paper Trading 用 SQLite を読み、稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）やリスク却下数などを集計して検証レポートを生成する CLI を追加。合否判定の閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）を設定。
- リサーチ基盤（部分実装）
  - research/factor_research.py: DuckDB を使ったファクター計算モジュールを追加（モメンタム、移動平均乖離、ATR、出来高系などを想定）。モジュールは DuckDB の prices_daily / raw_financials を参照する設計。現状一部実装が途中（ファイル末尾が未完）。

### 変更
- なし（初回リリースのため既存機能の変更はなし）。

### 修正
- なし（初回リリース）。

### 既知の問題 / 注意点
- research/factor_research.py はファイル末尾で処理が途中になっている（未完）。追加の実装が必要。
- position_sizing、risk_adjustment の一部処理（price 欠損時のフォールバックなど）に TODO コメントあり。実運用では過去終値や取得原価によるフォールバック等の追加を推奨。
- process_priority や CPU affinity の設定は権限に依存し、失敗時は警告を出してスキップする設計。
- .env は絶対に Git にコミットしないこと。config_setup が生成する .env の取り扱いに注意。
- monitoring は常に本番向け sqlite_path を参照する設計になっているため、開発環境での取り扱いに注意。

### ドキュメント / コメント
- 各モジュールに詳細な docstring と使用例/注意事項を追加。CLI スクリプトは使い方コメントを先頭に記載。

---

今後の予定（例）
- research/factor_research の完成とユニットテスト整備
- ExecutionEngine / BrokerClient のモック/実装分離テストの強化
- config と YAML 設定のより詳細な検証ルール追加
- ロギング周りのテストと Windows 環境での動作確認

※ 本 CHANGELOG はコードの内容から推測して作成したものであり、実際のコミット履歴とは異なる可能性があります。