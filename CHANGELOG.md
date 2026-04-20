Keep a Changelog
================

すべての重要な変更点をここに記載します。This project adheres to "Keep a Changelog" — and is maintained for humans.

Unreleased
----------

（なし）

0.1.0 - 2026-04-20
-----------------

Added
- 初回リリース: KabuSys v0.1.0 を公開しました。
- 実行ランナー
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。プロセス優先度の設定、SQLite / DuckDB 接続、Broker クライアントの生成、OrderManager / RiskManager / Reconciler の組立て、スレッド実行と停止フラグ検出を行います。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。停止フラグを検知して安全に終了します。Monitoring は環境にかかわらず本番の sqlite_path を使用します。
- 環境設定
  - config.py: 環境変数 / .env 自動読み込み、設定値取得用の Settings クラスを導入。多くの設定プロパティ（J-Quants / kabu API トークン、DB パス、PAPER_FILL_MODE、PID／kill フラグパス、閾値など）と簡易バリデーションを提供。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化もサポート。
  - config_setup.py: .env 作成／更新のための対話式ウィザードを追加（.env 出力時に README コメントを付与）。秘密値はマスク表示。
  - validate_config.py: 起動前検証 CLI を追加。必須環境変数や DB パス、config/*.yaml の存在とパース（PyYAML がある場合）をチェック。--strict オプションで警告をエラー扱いにできます。
- Paper Trading 分離
  - run_execution は KABUSYS_ENV=paper_trading の場合に paper_sqlite_path（デフォルト: data/paper_trading.db）を使用し、本番 DB から完全分離して動作する仕組みを導入。BrokerFactory による MockBroker の利用を想定。
  - PAPER_FILL_MODE 環境変数によるペーパートレードの約定モード制御（"instant" / "partial" / "never" / "reject"）を実装。
- ロギング・運用ユーティリティ
  - utils/logging_setup.py: ルートロガー設定ユーティリティを追加。コンソール出力は stdout、ファイル出力は日次ローテーション（TimedRotatingFileHandler）で保管（既定 logs/、30日保持）。既存ハンドラの二重登録を防止します。
  - utils/process_priority.py: プロセス優先度（high/normal/low）と CPU affinity 設定ユーティリティを追加。Windows / POSIX（Linux/macOS/FreeBSD）を吸収する実装で、権限不足などはログ警告でフォールバックします。
- ポートフォリオ構築ライブラリ（純粋関数）
  - portfolio/portfolio_builder.py: シグナル選定（select_candidates）と重み計算（calc_equal_weights, calc_score_weights）を実装。スコア全ゼロ時は等配分にフォールバック。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）を実装。未知レジームはログ警告と共にフォールバック。
  - portfolio/position_sizing.py: 株数算出ロジック（risk_based / equal / score）、単元株丸め、単銘柄および集計上限、cost_buffer による保守的見積り、スケーリングと残余分配ルールを実装。
- 監視・メトリクス
  - monitoring_db 初期化呼び出しを各ランナーで行い、監視テーブルが存在することを保証（冪等）。
- 分析基盤
  - DuckDB を分析用に統合（duckdb_path 設定）。research モジュール向けに DuckDB 接続を受け取る設計。
- 運用ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成ツールを追加。稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）を算出し、閾値（P95 等）に基づき PASS/FAIL を判定。コマンドラインで期間指定可能（--from / --to / --db）。
- パッケージ情報
  - __init__.py にてバージョンを 0.1.0 として定義。

Changed
- （初版のため該当なし）

Fixed
- （初版のため該当なし）

Security
- .env は絶対にリポジトリにコミットしない旨をドキュメント／生成スクリプトのヘッダに明記。

Notes / Implementation details
- stop/kill フラグと pid ファイルを用いて外部からの停止制御をサポート（data/stop_requested.flag, data/execution.pid 等を利用）。
- ログ出力設定は環境変数 LOG_LEVEL / LOG_DIR により上書き可能。
- validate_config は PyYAML がインストールされていない場合、YAML 内容チェックをスキップして警告を出します。
- 一部モジュール（monitoring.system_monitor や execution.Engine 実装など）は本 changelog の対象コードで参照されていますが、今回のリリースでの主要 API と統合ポイントとして扱われています。

今後の予定（案）
- research.factor_research の完成（ファクター計算ロジックの SQL 実装の続き）
- 銘柄別単元サイズのマスタ対応（lot_size の銘柄毎対応）
- より詳細な監視アラート（LINE 通知等）の実装拡充

--- 

この CHANGELOG はコードベースから推測して作成しています。実際のリリースノートとして使用する場合は、必要に応じて差分・追加の修正点を反映してください。