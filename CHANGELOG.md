# Changelog

すべての注目すべき変更点はここに記録します。フォーマットは「Keep a Changelog」に準拠します。

なお、本ファイルはソースコードの内容から推測して作成した変更履歴です。実際のコミット履歴とは差異がある場合があります。

## [0.1.0] - 2026-04-19

Initial release

### Added
- 基本アプリケーションエントリポイントを追加
  - run_execution.py: ExecutionEngine 起動スクリプト（スレッドで実行、stop フラグ / pid ファイル対応）。KABUSYS_ENV=paper_trading 時は paper_trading 用 DB を使用する旨を実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。停止フラグ（data/stop_requested.flag）で安全に終了。
- 設定関連
  - config.py: 環境変数/`.env` ロードと Settings クラスを実装。多くの設定プロパティ（DB パス、ログレベル、監視閾値、paper_trading 関連など）と入力検証を提供。
  - config_setup.py: 対話式の .env 作成/更新ウィザードを実装（既存 .env 読み込み、シークレットマスク、保存機能）。
  - validate_config.py: 起動前の設定検証 CLI を実装（必須環境変数 / パスの存在 / YAML ファイルのパース等）。--strict オプションで警告を FAIL 扱いに可能。
- ポートフォリオ構築モジュール（純粋関数群）
  - portfolio/portfolio_builder.py: シグナルの候補選定（select_candidates）と配分重み算出（calc_equal_weights, calc_score_weights）。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）。
  - portfolio/position_sizing.py: 株数決定ロジック（calc_position_sizes）を実装。risk_based / equal / score の割当方式、単元株丸め、aggregate cap によるスケーリング、cost_buffer による保守的見積り等に対応。
- ユーティリティ
  - utils/logging_setup.py: 統一的なロギングセットアップを提供（コンソール stdout と 日次ローテーションファイルハンドラ）。LOG_DIR / LOG_LEVEL の解決ルールを実装し、ファイル出力失敗時はコンソールのみでフォールバック。
  - utils/process_priority.py: クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定と CPU affinity 設定を実装。psutil 不可用/アクセス拒否時は警告でスキップ。
- モニタリング関連
  - monitoring_db と SystemMonitor (呼び出し側 run_monitoring/run_execution から初期化) を使用する起動フローを実装（SQLite / DuckDB 接続）。
- 実行/リスク周り
  - execution 以下に ExecutionEngine/OrderManager/OrderRepository/Reconciler/RiskManager の起動連携を実装（EngineConfig / RiskConfig のデフォルトを提供し、broker factory 経由でブローカークライアントを生成）。
- ツール
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成ツールを実装。稼働率、注文成功率、送信率、P95 レイテンシ、リスク却下数などを算出し PASS/FAIL 判定を行う。--from/--to/--db オプションと環境変数 PAPER_TRADING_SQLITE_PATH に対応。
- リサーチ
  - research/factor_research.py: ファクター計算モジュールの骨格を実装（モメンタム等の定義、DuckDB 経由の計算方針を明示）。

### Changed
- ログ設定のデフォルトを統一
  - 日次ローテーションで 30 日分保持する設定を導入（TimedRotatingFileHandler backupCount=30）。
  - コンソール出力は stdout を使用（cron / タスクスケジューラでの扱いを考慮）。
- .env 自動ロードの挙動
  - プロジェクトルートを .git / pyproject.toml で探索して .env / .env.local を自動読み込み（OS 環境変数は保護）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- Execution 起動時の DB 選択
  - 環境が paper_trading の場合は paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番 DB と完全に分離するように変更。
- 監視ループの挙動
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用（監視データは共通で集約する設計）。
  - MONITOR_POLL_INTERVAL の不正値に対するフォールバックと警告出力を追加。

### Fixed
- .env パーサの堅牢化（config._parse_env_line）
  - export プレフィックス対応、クォートされた値のバックスラッシュエスケープ対応、インラインコメント処理、空行/コメント行無視などを実装して `.env` の多様なフォーマットに対処。
- ロギング設定の堅牢化
  - ログディレクトリ作成失敗時のフォールバック（ファイルハンドラをスキップしてコンソールのみ継続）。既存ハンドラの flush/close 後に再設定することで二重設定を防止。
- process_priority の例外処理強化
  - psutil のプラットフォーム差分に対するフォールバックと AccessDenied/NotImplementedError の捕捉で、安全にスキップするよう改善。
- Execution の安全停止
  - 起動前・実行中ともに stop フラグ（data/stop_requested.flag）を検知して Engine の停止とスレッド終了を確実に行う処理を追加。
- Paper verification report の耐障害性
  - 対象テーブルが存在しない（sqlite3.OperationalError）場合のハンドリングを追加し、存在しない場合は N/A または 0 でレポート可能に。

### Documentation / Developer experience
- config_setup のウィザード導入により、初期セットアップが対話的に可能に（シークレット入力、選択肢、保存前の確認表示）。
- validate_config による起動前チェックで設定不備を事前に検出可能（YAML の無い場合や PyYAML 未インストール時の警告も実装）。
- portfolio モジュールには関数ドキュメンテーションと設計メモ（PortfolioConstruction.md / StrategyModel.md 準拠）を付記。

### Breaking Changes
- なし（初期公開）。ただし監視 DB / 実行 DB の扱い（監視は常に sqlite_path、本番と paper_trading の DB 分離）は運用上の注意点となります。

### Known limitations / Notes
- research/factor_research.py はファクター計算の主要構成を実装しているが、実データテーブル（DuckDB 内の prices_daily / raw_financials）に依存するため、環境にテーブルが存在しない場合は利用不可。
- position_sizing の lot_size は現在グローバル共通の前提（将来的に銘柄別 lot_map への拡張を想定）。
- paper_trading 用 MockBrokerClient の具体実装および monitoring_db / SystemMonitor の内部実装は本ログからは参照のみ（別モジュール実装に依存）。

---

今後の予定（想定）
- ファクターモジュールの完全実装（Momentum / Value / Volatility / Liquidity の出力定義と正規化）。
- テストスイート・CI の追加と自動化（設定検証・ユニットテスト）。
- 単体/統合テストを通した堅牢化とドキュメント整備。