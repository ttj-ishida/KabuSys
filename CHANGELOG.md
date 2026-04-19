# CHANGELOG

すべての非互換な変更はメジャー番号を上げるまでコミットしないこと — Keep a Changelog 準拠で記載。

<!-- Unreleased セクションは今後の変更用 -->
## [Unreleased]

---

## [0.1.0] - 2026-04-19

初回リリース。以下の機能群・ユーティリティを追加しました（コードベースから推測してまとめています）。

### Added
- 実行・監視ランナー
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。起動時にプロセス優先度を設定し、ブローカークライアントを生成してエンジンスレッドをデーモンで実行。停止フラグ検知で安全に停止するロジックを実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグファイルを検知してループ終了。
- 環境設定管理
  - config.py: .env 自動読み込み（.env / .env.local、OS環境変数保護）と環境変数のラッパー Settings クラスを実装。多数の設定プロパティ（DBパス、ログレベル、環境種別、Paper Trading 関連設定、監視閾値など）を提供。必須環境変数取得用の _require 関数あり。
  - config_setup.py: 対話式 .env ウィザードを実装。既存 .env 読み込み、値のマスク表示、選択肢・デフォルト対応、保存機能を提供。
  - validate_config.py: 起動前設定検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスや config/*.yaml の存在・パース確認、live 環境向けガード等を実行。--strict オプションで警告を FAIL 扱いにできる。
- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py: ルートロガー設定ユーティリティを提供。stdout 出力用 StreamHandler と日次ローテーション（TimedRotatingFileHandler、30 日保持）のファイルハンドラを設定。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py: プロセス優先度および CPU affinity 設定ユーティリティを実装。Windows / POSIX を吸収して呼び出し側がプラットフォームを意識せず利用可能。権限不足や未対応プラットフォーム時は警告してスキップ。
- Execution 関連コンポーネント（起動スクリプトから利用される本体は別モジュール）
  - BrokerClientFactory、ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager 等の組み立てロジックを run_execution 内に追加。paper_trading 環境では専用 SQLite（data/paper_trading.db）を使用する形を想定。
  - RiskManager のデフォルト設定値を実装（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker など）および初期ポートフォリオ値を broker.get_available_cash() から取得する流れを追加。
- 監視用 DB 初期化 / SystemMonitor 利用
  - run_monitoring/run_execution 両方で init_monitoring_db を呼び、監視用テーブルの存在を保証（冪等）。
  - 監視は環境にかかわらず本番 sqlite_path を使用する設計（run_monitoring の注記）。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定（select_candidates）、等金額（calc_equal_weights）、スコア加重（calc_score_weights）。スコア全てが 0 の場合に等金額へフォールバックする警告を出す。
  - portfolio/risk_adjustment.py: セクター集中制限 apply_sector_cap、レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear をマップ、未知レジームは警告して 1.0 にフォールバック）。
  - portfolio/position_sizing.py: position sizing ロジックを追加。allocation_method として "risk_based" / "equal" / "score" をサポート。単元株（lot_size）で丸め、per-position と aggregate のキャップ、cost_buffer を考慮したスケーリングと残余配分ロジックを実装。
  - portfolio/__init__.py で主要関数群をエクスポート。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py: ペーパートレード用 SQLite を読み、システム稼働率、注文成功率、送信率、P95 レイテンシ等の指標を算出してレポート出力。閾値を定義して PASS/FAIL を判定する。P95 計算と日付フィルタ、DB 存在チェックを実装。
- 研究用ファクター計算
  - research/factor_research.py: DuckDB 接続を受けて prices_daily / raw_financials を参照し、Momentum / Value / Volatility / Liquidity 等のファクターを計算する設計を追加（関数群の雛形と定数が実装されている）。

### Changed
- 初期設計として、ログ出力は stdout を標準とし、ファイル出力はログディレクトリ作成が成功した場合のみ追加する仕様に統一。
- .env 自動読み込みの挙動: プロジェクトルート判定 (.git または pyproject.toml) に基づき読み込みを行い、環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能にした。OS 環境変数を保護するため .env の上書き時に protected セットを利用する挙動を導入。

### Fixed
- 環境変数パースの堅牢化:
  - config._parse_env_line で export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱い、クォート無し値での # コメント判定（前が空白/タブの場合のみ）に対応。
- run_monitoring の MONITOR_POLL_INTERVAL の値検証を追加。0 以下や数値でない値は警告してデフォルト（60 秒）にフォールバックするように修正。
- utils/process_priority.py で psutil に依存する定数が OS に存在しない場合でもモジュール読み込み時に失敗しないよう getattr フォールバックを適用。権限不足や未実装 API に対しては警告を出して安全にスキップ。

### Notes / Known limitations
- research/factor_research.py はファクター計算の骨組みがあり詳細実装（クエリや全関数の完全実装）は継続作業が必要（ファイル終端が途中で切れている箇所あり）。
- 一部の I/O（DB ファイル作成、ログディレクトリ作成、psutil による優先度変更等）は実行ユーザーの権限や環境に依存するため、運用環境での確認が必要。
- config_setup の生成する .env は秘匿情報を含むため、README 等で Git へのコミット禁止を強調する運用ルールが推奨される。

---

今後のリリースでは以下を想定している（例）:
- factor_research の SQL / DuckDB 実装の完成とユニットテスト追加
- ExecutionEngine / BrokerClient の詳細 API 適合テスト、ペーパートレードのモック挙動強化
- 監視（SystemMonitor）周りのアラート送信（LINE 統合）の実装と監視ルールの拡充

（以上はコードベースから推測した CHANGELOG です。実際のコミット履歴や設計意図に応じて適宜修正してください。）