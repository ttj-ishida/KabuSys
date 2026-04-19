# Changelog

すべての重要な変更はこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠します。

最新リリース
------------

### [0.1.0] - 2026-04-19

Added
- 初期リリース。KabuSys の基本コンポーネントを実装・公開。
- 起動スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading 時はペーパートレード用 DB を使用（data/paper_trading.db がデフォルト）し、MockBrokerClient を利用する（BrokerClientFactory 経由）。プロセス優先度設定、PID ファイル管理、停止フラグ（data/stop_requested.flag）による安全停止に対応。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔をオーバーライド可能（デフォルト 60 秒）。Monitoring は環境にかかわらず本番 sqlite_path を使用して監視情報を保存。
- 設定管理
  - config.py: Settings クラスを導入。環境変数・.env/.env.local の自動読み込み（プロジェクトルート検出あり、KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化可）、必須値チェック、各種設定プロパティ（DB パス・PID/kill フラグパス・閾値など）を提供。PAPER_FILL_MODE の検証や KABUSYS_ENV / LOG_LEVEL の検証を実装。
  - config_setup.py: .env 作成・更新の対話式ウィザードを追加。シークレット項目のマスク表示、既存 .env の読み込み、最終確認後保存。
  - validate_config.py: 起動前チェック CLI を追加。必須環境変数、KABUSYS_ENV の妥当性、ログレベル、DB パス・config/*.yaml の存在と YAML パース検証（PyYAML が無ければ警告）を行い、--strict モードで警告を FAIL 扱い可能。
- ユーティリティ
  - utils/logging_setup.py: 統一ログ設定ユーティリティを追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）をルートロガーに設定。LOG_DIR/LOG_LEVEL の上書き、ログディレクトリ作成失敗時のファイルハンドラ無効化に対応。
  - utils/process_priority.py: クロスプラットフォームのプロセス優先度設定ユーティリティを追加（Windows の優先度クラス / POSIX の nice 値を吸収）。set_cpu_affinity による CPU ピニング機能も提供。psutil で操作できない場合は警告を出してスキップ。
- Portfolio（ポートフォリオ構築）
  - portfolio/portfolio_builder.py: シグナルの候補選定（スコア降順、タイブレークルール）と等金額・スコア加重の重み計算を実装。スコア全ゼロ時は等金額にフォールバックして警告。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）および市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。unknown セクターはセクター上限の適用対象外、未知レジームはフォールバックして 1.0 を返す（警告）。
  - portfolio/position_sizing.py: position sizing ロジックを実装。allocation_method="risk_based" / "equal" / "score" をサポート。単元株（lot_size）で丸め、per-stock 上限・aggregate cap（available_cash 超過時のスケールダウン）・cost_buffer によるコスト見積を実装。スケールダウン後の端数は残差順に lot 単位で再配分するアルゴリズムを実装。
- モニタリング・検証ツール
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成 CLI を追加。system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）等を集計し、閾値（稼働率 99%, 成立率 90%, 送信率 95%, P95 <= 200ms）に基づいて PASS/FAIL 判定を出力。日付フィルタ（--from / --to）と DB パス指定（--db / 環境変数）に対応。
- research/factor_research.py: DuckDB を使ったファクター計算モジュールの骨格を追加（モメンタム、MA200、ATR、出来高系等の計算方針を実装予定／部分実装）。DuckDB 接続を受け取り prices_daily / raw_financials を参照する設計。

Changed
- .env パーサの強化（config.py 内）
  - export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの扱いを改良。既存 OS 環境変数を保護する protected ロジックを導入し .env.local からの上書きを制御。

Fixed
- 環境変数や設定ファイル検証の堅牢化（validate_config.py）
  - DB パスの親ディレクトリ存在チェックや、PyYAML 未インストール時のフォールバック処理追加。
- ログ出力の二重登録防止（logging_setup.py）
  - 既存ハンドラを一旦 flush/close してから削除することで、複数回 setup_logging を呼んでもハンドラ重複しないように調整。

Security
- シークレット扱いの設定（J-Quants / kabu API パスワード / LINE トークン）を config_setup の UI 上でマスク表示。README 等で .env を Git 管理しないことを明示。

Known issues / Notes
- research/factor_research.py は一部実装が未完（ソース末尾が途中で切れている箇所あり）。ファクター実装は今後のイテレーションで完成予定。
- 一部のファイル I/O や OS 操作は権限不足時に警告を出してスキップする設計だが、運用環境によっては明示的な権限設定が必要。
- 初期リリースのため、API の安定化・追加ユニットテスト・ドキュメント整備が今後の課題。

Misc
- パッケージバージョンを 0.1.0 に設定（src/kabusys/__init__.py）。

未リリース（Unreleased）
- 今後の予定事項（例）
  - factor_research の完成、ユニットテスト追加
  - ExecutionEngine / EngineConfig のエンドツーエンドテスト
  - strategy モジュールの追加とドキュメント化
  - 分析用ダッシュボードの追加

--- 

参考: 重要な環境変数・ファイルパス
- KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, LOG_LEVEL
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
- MONITOR_POLL_INTERVAL (default: 60 秒)
- data/stop_requested.flag（停止フラグ）, data/execution.pid（PID ファイル）
- LOG_DIR（ログ保存先）