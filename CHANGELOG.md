# Changelog

すべての重要な変更を記録します。本ファイルは「Keep a Changelog」形式に準拠しています。バージョン番号は semantic versioning を想定しています。

注: 以下の履歴は提示されたソースコードから機能・変更点を推測して作成したものです。

## [Unreleased]

（現時点で未リリースの変更はありません）

## [0.1.0] - 2026-04-19

### Added（追加）
- 初期リリースとして以下の主要コンポーネントを実装・追加。
  - 実行用スクリプト
    - run_execution.py: ExecutionEngine を起動する CLI スクリプト。バックグラウンドスレッドでエンジンを実行し、停止フラグ検知で安全に停止可能。
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL によりポーリング間隔をオーバーライド可能（デフォルト 60 秒）。
  - 設定関連
    - config.py: 環境変数／.env 読み込みと Settings クラスを提供。プロジェクトルートを自動検出して .env/.env.local を読み込む（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - config_setup.py: .env を対話式に生成・更新するウィザード CLI。
    - validate_config.py: 起動前に .env と config/*.yaml の妥当性をチェックする検証ツール（--strict オプションで警告を FAIL 扱いにできる）。
  - データベース / 永続化
    - SQLite と DuckDB の併用を前提とした接続処理を各スクリプトで実装。監視（monitoring）は環境に依らず本番用 sqlite_path を使用する設計。ペーパートレード時は paper_sqlite_path（data/paper_trading.db）を使用して本番 DB と分離。
  - ポートフォリオ構築（純粋関数群）
    - portfolio.portfolio_builder: 候補選定（select_candidates）、等重配分（calc_equal_weights）、スコア加重配分（calc_score_weights）。
    - portfolio.risk_adjustment: セクター集中上限適用（apply_sector_cap）、レジームに応じた投資乗数（calc_regime_multiplier）。
    - portfolio.position_sizing: 発注株数算出（calc_position_sizes） — リスクベース・等分配・スコアベースの各方式をサポート。単元（lot_size）丸め、aggregate cap によるスケーリング、コストバッファ対応。
  - リサーチ / ファクター計算
    - research.factor_research: Momentum 等のファクター計算モジュール骨子（DuckDB 接続を受け取り prices_daily / raw_financials を参照して計算）。
  - ユーティリティ
    - utils.logging_setup: 共通ログ設定ユーティリティ。stdout 出力（StreamHandler）と日次ローテートのファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。ログディレクトリ作成失敗時はファイル出力を安全にスキップ。
    - utils.process_priority: psutil を利用したプロセス優先度（Windows / POSIX 対応）と CPU affinity 設定ユーティリティ。設定失敗時は警告を出してフォールバック。
  - Execution / Monitoring 連携
    - Execution 側で BrokerClientFactory を利用してブローカークライアントを生成。RiskManager、OrderManager、Reconciler、ExecutionEngine を組み合わせる起動フローを実装。
  - ツール
    - tools.paper_verification_report: Paper Trading 用検証レポート生成スクリプト。稼働率、注文成功率、送信率、レイテンシ（P95 など）を集計して PASS/FAIL 判定を出力。PAPER_TRADING_SQLITE_PATH 環境変数または --db オプションで DB 指定可能。

### Changed（仕様・設計上の注記）
- .env パーサーの挙動を細かく扱う実装:
  - export プレフィックスのサポート、シングル／ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント判定ロジックを実装。既存 OS 環境変数は保護され、.env.local は .env を上書きする。
- ロギング
  - ログの出力先は stdout を標準とし、ファイル出力は日次ローテーション（30日保持）。ログディレクトリ作成に失敗した場合でも stdout のみで継続する堅牢な実装。
- プロセス優先度設定
  - 起動直後に set_process_priority("high") を呼び出し、可能な範囲でプロセス優先度を上げる設計（アクセス権限がない場合は警告でスキップ）。
- 実運用ガード
  - validate_config は本番（KABUSYS_ENV=live）用の追加チェック（LINE トークン未設定や Kill Switch の自動クリア設定など）を実施する設計。
- Paper Trading 分離
  - KABUSYS_ENV=paper_trading の場合、MockBroker を使って paper_trading.db に記録することで、本番 DB と完全分離する仕様。

### Fixed（実装上の注意・防御的実装）
- position_sizing, risk_adjustment 等で価格が欠損（0 または None）の場合にスキップするような防御的コードを実装。価格欠損時に過少評価や例外を引き起こさないように配慮。
- run_monitoring のポーリング間隔設定で不正な環境変数値（0以下や非数）が与えられた場合にデフォルトへフォールバックするロジックを追加（警告ログを出力）。

### Security（セキュリティ）
- .env ファイルに関する注意書き（.env を絶対に Git にコミットしない）を config_setup の出力テンプレートに明記。
- シークレット値（J-Quants トークン、kabu API パスワード、LINE トークン）はウィザードでマスクして扱う形に配慮。

---

開発者向け注釈:
- 上記はコードベースから推測した機能一覧と設計意図のまとめです。外部モジュール（BrokerClientFactory や ExecutionEngine の内部実装、monitoring/system_monitor 等）の具体的挙動はこのスナップショットからは推測の域を出ません。実際の動作・運用手順は該当モジュールの実装やドキュメントを参照してください。