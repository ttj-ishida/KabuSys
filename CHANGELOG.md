CHANGELOG
=========

このファイルは「Keep a Changelog」形式に準拠しています。  
リリースノートは主にコードベースから推測して作成しています。

## [0.1.0] - 2026-04-18

初回リリース。KabuSys のコア機能群（設定管理・起動スクリプト・運用ユーティリティ・ポートフォリオ構築ロジック・ペーパートレード検証ツール等）を追加。

### Added
- 設定管理
  - Settings クラスを追加。環境変数経由でアプリケーション設定を提供（例: KABUSYS_ENV, LOG_LEVEL, DUCKDB_PATH, SQLITE_PATH, PAPER_FILL_MODE 等）。
  - 自動 .env ロード機構を実装（プロジェクトルートの検出: .git または pyproject.toml を基準）。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化対応。
  - .env パーサを独自実装。export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント等に対応。

- 環境設定ウィザード
  - config_setup CLI を追加（python -m kabusys.config_setup）。
  - 対話式で .env を初期作成・更新可能。トークン等はマスク表示、デフォルト値・選択肢をサポート。

- 設定検証ツール
  - validate_config CLI を追加（python -m kabusys.validate_config）。
  - 必須環境変数のチェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリチェック、config/*.yaml の存在・パースチェック（PyYAML があれば詳細検証）、本番環境向けガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の確認）を実施。
  - --strict オプションで警告をエラー扱いにできる。

- 起動スクリプト
  - run_execution 起動スクリプトを追加（python -m kabusys.run_execution）。
    - ExecutionEngine の組み立てと起動。BrokerClientFactory を介して環境に応じたブローカークライアント（paper_trading 時は MockBrokerClient）を選択。
    - paper_trading 環境では専用の SQLite（デフォルト data/paper_trading.db）を使用して本番 DB と完全分離。
    - RiskManager（デフォルト RiskConfig を含む）、OrderManager、OrderRepository、Reconciler、PID ファイル、停止フラグ検出による安全停止を提供。
  - run_monitoring 起動スクリプトを追加（python -m kabusys.run_monitoring）。
    - SystemMonitor のポーリングループを提供。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境に依らず本番 sqlite_path を使用して監視テーブルを永続化。
    - 停止フラグ（data/stop_requested.flag）による安全終了、例外保護ログ、SQLite / DuckDB のクローズ処理を実装。

- 監視 DB 初期化
  - init_monitoring_db を利用して監視テーブルの存在を保証（冪等的に初期化）。

- 分析用 DB 統合
  - DuckDB を分析バックエンドとして接続する処理を追加（duckdb_path）。各種モジュールから DuckDB 接続を受け取る設計。

- ロギング / プロセス管理ユーティリティ
  - utils.logging_setup: 共通ログ設定（stdout StreamHandler + 日次ローテートの TimedRotatingFileHandler、ログディレクトリ自動作成、ログレベル解決）を提供。
  - utils.process_priority: psutil を用いたプロセス優先度設定（Windows / POSIX の差分吸収）、CPU affinity 設定ユーティリティを追加。起動時にプロセス優先度を "high" に設定する呼び出しを組み込み。

- ポートフォリオ構築ロジック（純粋関数）
  - portfolio.portfolio_builder: 信号の候補選定（select_candidates）、等重配分（calc_equal_weights）、スコア重み配分（calc_score_weights）を実装。スコア全0時は等分にフォールバックして警告を出す。
  - portfolio.risk_adjustment: セクター集中制限適用（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。未知レジームはフォールバックで警告。
  - portfolio.position_sizing: 株数決定ロジック（calc_position_sizes）を実装。allocation_method に "risk_based", "equal", "score" をサポート。単元株丸め、1銘柄上限・合計投下上限（aggregate cap）を考慮したスケーリング処理、手数料やスリッページのバッファ（cost_buffer）を考慮した保守的計算を実装。

- ペーパートレード検証ツール
  - tools.paper_verification_report: ペーパートレード用 SQLite から稼働率、注文成功率、送信率、P95 レイテンシ等を集計してレポート出力。閾値に基づく PASS/FAIL 判定を出力。

- リサーチ（ファクター計算）骨組み
  - research.factor_research にファクター計算基盤（モメンタム、MA200 乖離、ATR、流動性指標などの設計と定数）を追加。DuckDB 接続を受け取り SQL/Python で計算する設計を採用。
  - calc_momentum 等の関数スケルトンを追加（将来的な実装を想定）。

### Changed
- なし（初回リリースのため該当なし）

### Fixed
- なし（初回リリースのため該当なし）

### Notes / Known issues / TODO
- portfolio.position_sizing 内で price が欠損（0.0）の場合にエクスポージャーが過少見積りされる旨の TODO コメントが存在。将来的に前日終値や取得原価をフォールバック価格として利用することが検討されている。
- research.factor_research の calc_momentum 実装が途中で切れている（このリリースでは骨組みのみ）。ファクター計算の完全実装は今後のリリースで追加予定。
- 一部のユーティリティ（init_monitoring_db、SystemMonitor、ExecutionEngine 等）の詳細実装はこの差分に含まれるファイルからは参照のみで、実装ファイルは別途存在することを想定。
- ログディレクトリの作成に失敗した場合はファイルハンドラをスキップしてコンソール出力のみで継続する仕様。

### Developers / Ops
- 実行方法（例）
  - 環境設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config [--strict]
  - Execution 起動: python -m kabusys.run_execution
  - Monitoring 起動: python -m kabusys.run_monitoring
  - Paper 検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

- 重要な環境変数（主なもの）
  - JQUANTS_REFRESH_TOKEN（必須）
  - KABU_API_PASSWORD（必須）
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading 時の挙動）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB）
  - DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, LOG_DIR, KILL_FLAG_CLEAR_ON_START 等

---

特記事項やリリース内容の補足が必要であればお知らせください。必要に応じて、各モジュールごとの詳細な変更ログ（関数一覧・引数説明・既知の挙動や制約）も作成できます。