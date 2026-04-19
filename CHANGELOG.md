CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従っています。  
各リリースでは主な追加・変更・修正・既知の問題や TODO を日本語でまとめています。

フォーマット:
- Added: 新機能
- Changed: 変更点（互換性のある改善）
- Fixed: バグ修正
- Deprecated/Removed/Security: 該当する場合に記載

Unreleased
----------
- ドキュメント整備・テスト追加などの小さな改善予定
- research/factor_research の残り実装（calc_momentum の実装途中）を完了する予定
- 単体テストの整備および CI ワークフローの追加予定

[0.1.0] - 2026-04-19
--------------------

Added
- パッケージ初回公開（__version__ = 0.1.0）。
- 起動スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。  
    - KABUSYS_ENV=paper_trading の場合は Paper Trading 用の SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory を用いてブローカクライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - 停止フラグ (data/stop_requested.flag) と PID ファイル (data/execution.pid) に対応し、スレッドベースでエンジンの安全停止を行う。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。  
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用して監視テーブルを初期化。
    - 停止フラグでループ終了、KeyboardInterrupt に対応。
- 設定関連 CLI / ユーティリティ
  - config_setup.py: 対話式 .env 作成・更新ウィザードを追加。シークレット項目はマスク表示、.env の書き出し機能を提供。
  - validate_config.py: 起動前の設定検証ツールを追加。必須環境変数確認、KABUSYS_ENV の妥当性チェック、YAML 設定ファイルの存在とパース検証（PyYAML 利用時）や本番環境向けの追加ガードを実装。--strict モードをサポート。
- 設定読み込み / 管理
  - config.py: .env 自動ロード機能（プロジェクトルート検出ロジックを含む）、環境変数パースロジック（クォート・エスケープ・インラインコメント対応）、Settings クラスを導入。多くの設定プロパティ（DB パス、PID/kill flag、しきい値や PAPER_FILL_MODE 等）を提供。
- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py: StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション）をルートロガーに設定する共通ユーティリティを追加。LOG_DIR/LOG_LEVEL の解決順をサポートし、ファイル作成失敗時はコンソール出力のみで継続。
  - utils/process_priority.py: psutil を用いて Windows/Linux/macOS の差分を吸収するプロセス優先度設定ユーティリティを追加。CPU affinity 設定関数も提供。権限不足時は警告を出して安全にスキップ。
- Portfolio 構築モジュール
  - portfolio/portfolio_builder.py: 候補選定 (select_candidates)、等配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。スコア全 0 の場合は等配分へフォールバックして警告を出す。
  - portfolio/risk_adjustment.py: セクター集中制限適用 (apply_sector_cap)、市場レジームに応じた乗数 (calc_regime_multiplier) を実装。既存保有のセクター別エクスポージャ計算や blocked セクター除外ロジックを提供。
  - portfolio/position_sizing.py: 株数決定ロジック (calc_position_sizes) を実装。risk_based / equal / score の allocation_method に対応し、単元株（lot_size）丸め、max_position_pct / max_utilization による制限、aggregate cap によるスケールダウンと残差処理を行う。
  - portfolio/__init__.py で公開 API を整備。
- Paper Trading 検証レポート
  - tools/paper_verification_report.py: Paper Trading の SQLite ログから運用指標（稼働率、注文成功率、送信率、P95 レイテンシ等）を集計してレポート出力するスクリプトを追加。しきい値に基づく PASS/FAIL 判定を実装。--from/--to/--db オプションをサポート。
- research/factor_research.py: ファクター計算モジュールを追加（モメンタム等の設計と一部実装を含む）。DuckDB を用いて prices_daily / raw_financials を参照する設計。

Changed
- N/A（初回リリースのため、過去の変更履歴はありません）。

Fixed
- N/A（初回リリースのため、過去のバグ修正履歴はありません）。

Known issues / Notes / TODO
- position_sizing.calc_position_sizes:
  - TODO: 将来的に銘柄別 lot_size をサポートするための拡張設計を注記（現状は全銘柄共通の lot_size）。
- risk_adjustment.apply_sector_cap:
  - price が欠損（0.0）の場合にエクスポージャが過少見積りされる可能性がある旨をコメントで明記。将来的にはフォールバック価格（前日終値・取得原価等）を利用することを検討。
- research/factor_research.calc_momentum:
  - ファイル末尾で calc_momentum 実装が途中で終わっている（start_da... で切れている）。完全実装が必要。
- ログディレクトリ作成失敗時:
  - logging_setup はファイルハンドラの作成に失敗した場合、コンソール出力のみで継続する設計。運用時は LOG_DIR の権限やパスを確認のこと。
- .env セキュリティ:
  - config_setup で生成される .env は絶対に Git にコミットしないこと（ヘッダに注意書きあり）。
- 実行ユーザーの権限次第で process_priority / cpu_affinity の設定が失敗する場合がある（警告でスキップ）。

Security
- .env に API トークンやパスワードを格納する設計のため、リポジトリに .env を含めない運用を強く推奨。

参考
- パッケージバージョン: 0.1.0 (src/kabusys/__init__.py)
- 主要 CLI:
  - python -m kabusys.run_execution (Engine 起動)
  - python -m kabusys.run_monitoring (監視ループ起動)
  - python -m kabusys.config_setup (対話式 .env)
  - python -m kabusys.validate_config (設定検証)
  - python -m kabusys.tools.paper_verification_report (Paper Trading レポート)

今後の計画（短期優先度）
- factor_research の完成（全ファクター計算と正規化）
- 単体テストと CI の整備
- ドキュメント（README / 運用手順 / デプロイ手順）の充実
- BrokerClient の抽象化・モックの拡充とペーパートレード検証の自動化

--- 

（この CHANGELOG はコードベースの現在の状態から推測して作成しています。実際のコミット履歴がある場合はそれに基づいた差分に置き換えてください。）