# Changelog

すべての変更は Keep a Changelog の仕様に準拠して記載しています。  
フォーマット: https://keepachangelog.com/ja/

## [Unreleased]

（現状、未リリースの差分はありません）

## [0.1.0] - 2026-04-18

初回リリース。自動売買システム KabuSys の基本コンポーネント群を実装しました。以下の主要機能・ユーティリティ・CLI を含みます。

### Added
- 実行エントリ / デーモン起動スクリプトを追加
  - run_execution: ExecutionEngine を起動するスクリプトを追加。紙トレード環境 (KABUSYS_ENV=paper_trading) 用に MockBrokerClient を利用し、paper_trading 用 SQLite（data/paper_trading.db）と本番 DB を分離 (src/kabusys/run_execution.py)。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能、停止フラグファイルで安全停止 (src/kabusys/run_monitoring.py)。
- 環境設定 / 検証用 CLI を追加
  - config_setup: 対話式ウィザードで .env を作成・更新する CLI を追加（複数の設定項目、シークレット入力、既存 .env の読み込みをサポート） (src/kabusys/config_setup.py)。
  - validate_config: .env と config/*.yaml の事前検証を行う CLI を追加（必須環境変数チェック、パス検証、YAML パース確認、KABUSYS_ENV による追加ガードなど） (src/kabusys/validate_config.py)。
- 環境変数 / 設定管理を実装
  - Settings クラスで主要設定をプロパティとして提供（DB パス、API トークン、動作環境フラグ、監視しきい値など）。自動でプロジェクトルートの .env/.env.local を読み込む仕組みを実装（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能） (src/kabusys/config.py)。
  - .env パーサーは export プレフィックス、クォート文字、エスケープ、インラインコメント等に対応する堅牢な実装を採用。
- ポートフォリオ構築ロジック（純関数）
  - portfolio_builder: 候補選択および等金額／スコア加重の重み算出関数を実装（スコア全ゼロ時は等金額にフォールバック） (src/kabusys/portfolio/portfolio_builder.py)。
  - risk_adjustment: セクター集中上限を適用する apply_sector_cap と、市況レジームに応じた資金乗数 calc_regime_multiplier を実装（未知レジームはフォールバック） (src/kabusys/portfolio/risk_adjustment.py)。
  - position_sizing: 各銘柄の発注株数計算ロジックを実装（risk_based / equal / score の配分方式、単元株丸め、aggregate cap によるスケーリング、cost_buffer 考慮） (src/kabusys/portfolio/position_sizing.py)。
  - ポートフォリオ API をパッケージとして公開（src/kabusys/portfolio/__init__.py）。
- 実行周りのユーティリティ
  - logging_setup: stdout ストリームハンドラと日次ローテートファイルハンドラ（TimedRotatingFileHandler）をルートロガーに統一設定するユーティリティを実装。ログディレクトリ作成失敗時はファイル出力をスキップする安全設計 (src/kabusys/utils/logging_setup.py)。
  - process_priority: Windows / POSIX の差分を吸収するプロセス優先度設定ユーティリティと CPU affinity 設定を実装。アクセス権限失敗時は警告を出してスキップ (src/kabusys/utils/process_priority.py)。
- 監視関連
  - monitoring DB 初期化処理を統一して呼び出す init_monitoring_db を用意し、実行スクリプトから監視テーブルの存在を保証（冪等） (参照: run_monitoring/run_execution 内で利用)。
  - SystemMonitor を使った定期チェックと停止フラグ処理を実装（run_monitoring）。
- Execution サブシステム（骨格）
  - ExecutionEngine / OrderManager / OrderRepository / Reconciler / RiskManager 等の組み立てと起動フローを実装（run_execution での初期化とスレッド運用の流れを含む）。RiskManager のデフォルト設定例を含む（max_position_pct, max_utilization, rate_limit 等）。
  - 本番と紙トレードで SQLite パスを切り替える仕組みを導入（Settings 経由）。
- Paper Trading 向け検証ツール
  - tools/paper_verification_report: Paper Trading の検証レポートを生成する CLI を追加。システム稼働率、注文成功率・送信率、リスク却下数、API レイテンシ（平均/最大/P95）等を算出し PASS/FAIL を判定。日付レンジ指定や DB パス指定オプションをサポート (src/kabusys/tools/paper_verification_report.py)。
- 研究用ファクター計算（骨格）
  - research/factor_research: DuckDB 接続を受け取り、Momentum / Value / Volatility / Liquidity などのファクターを計算する設計を追加（関数 calc_momentum 等の実装開始。DuckDB の prices_daily / raw_financials を前提）。一部ファイルは続き実装が期待される (src/kabusys/research/factor_research.py)。

### Changed
- パッケージメタ情報
  - バージョンを __version__ = "0.1.0" としてパッケージに明示 (src/kabusys/__init__.py)。

### Fixed
- ロバストネス強化
  - .env 読み込み失敗時に警告を出して続行する実装により、IO エラーで起動が停止しないように改善 (src/kabusys/config.py)。
  - logging_setup: ログディレクトリ作成失敗やファイルハンドラ作成エラー時にコンソール出力のみで継続するようにし、起動時の致命エラーを回避 (src/kabusys/utils/logging_setup.py)。
  - process_priority / set_cpu_affinity: 実行環境依存の例外（AccessDenied 等）をキャッチして警告ログを出すことで、安全にフォールバックするように修正 (src/kabusys/utils/process_priority.py)。

### Documentation
- 各モジュールに docstring とコメントを充実させ、設計上の注記（例: PortfolioConstruction.md の参照箇所、将来の拡張 TODO）を記載。

### Known issues / Notes
- research/factor_research.py はモメンタム計算等の実装が途中で終了している（ファイル末尾が切れている）。今後のリリースで完全実装とテストが必要。
- position_sizing において price の欠損時の扱いに注意（TODO: 前日終値等のフォールバックを検討）。
- validate_config は PyYAML 未インストール時に YAML 検証をスキップするが、YAML の構文検証を確実に行うため PyYAML の導入を推奨。

---

開発・運用に必要な追加タスク（例）
- 単体テスト・CI の整備（特に計算ロジックと DB 操作周り）
- research/factor_research の完成とパフォーマンス検証
- 各種 CLI のマニュアル整備（README、運用手順）
- 本番運用向けにログローテーション設定や権限周りの確認

（以上）