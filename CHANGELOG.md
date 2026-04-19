# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
このファイルは、コードベースから推測される主要な追加・変更点をまとめたものです。

※ バージョンや日付はコード内容から推測して付与しています。実際のリリース管理に合わせて調整してください。

## [Unreleased]

### Added
- 実行用と監視用のエントリポイントを追加
  - run_execution: ExecutionEngine を起動するスクリプト（デーモンスレッドでセッションを実行、停止フラグ検出で安全に停止）
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能）
- 環境設定周りのユーティリティ・CLI を追加
  - config_setup: 対話式ウィザードで .env の初期作成・更新を支援
  - validate_config: .env と config/*.yaml の起動前検証 CLI（--strict オプション対応）
- 設定管理モジュールを導入（kabusys.config）
  - .env/.env.local の自動ロード（OS 環境変数を保護）、export プレフィックスやクォート/エスケープ対応のパーサ実装
  - Settings クラスにより環境変数を型安全に取得（DB パス、ログレベル、Paper Trading 用設定、各閾値など）
- ペーパートレード検証用ツールを追加
  - tools/paper_verification_report: Paper Trading の検証レポート生成スクリプト（稼働率・注文成功率・レイテンシ等の指標算出）
- ポートフォリオ構築モジュールを追加（pure functions）
  - portfolio_builder: 候補選定・等金額 / スコア加重の重み計算
  - risk_adjustment: セクター上限適用、レジームに応じた乗数計算（bull/neutral/bear）
  - position_sizing: 各銘柄の発注株数算出（risk-based / equal / score、lot_size、aggregate cap スケールダウンの実装）
- ユーティリティ実装
  - logging_setup: stdout と 日次ローテーション（TimedRotatingFileHandler） を使った統一ログ設定。ログディレクトリ作成失敗時はフォールバック
  - process_priority: psutil を用いたプロセス優先度設定（Windows / POSIX 対応）および CPU affinity 設定
- Data 関連の調査モジュール（研究用）
  - research/factor_research: Momentum 等のファクター計算モジュールの骨子（DuckDB を利用、prices_daily/raw_financials 参照を想定）

### Changed
- Execution / Monitoring の DB 接続設計
  - 監視モジュールは KABUSYS_ENV に依らず本番 sqlite_path を使用する設計
  - Execution は paper_trading 環境の場合に paper 用 SQLite（デフォルト data/paper_trading.db）を使用して本番 DB と完全分離
- ログ設定の挙動を統一
  - 既存ハンドラをクリアして再設定することで二重ログ出力を防止
  - ログレベル・ログディレクトリの解決優先順（引数 > 環境変数 > デフォルト）を明示
- 環境変数読み込みの振る舞い改善
  - .env の自動ロードはプロジェクトルートが特定できる場合のみ行う（.git / pyproject.toml を基準）
  - OS 環境変数を保護するため .env 読み込み時に protected set を用いる

### Fixed
- 環境変数パースの耐性向上
  - _parse_env_line にて export prefix、クォートされた値のバックスラッシュエスケープ対応、インラインコメント扱いの改善を実装
- run_monitoring のポーリング間隔取得で不正値を検出した場合にデフォルトへフォールバックするように（ValueError を回避）
- logging_setup: ログディレクトリ作成やファイルハンドラ作成失敗時に安全にフォールバックし、標準出力のみで継続できるようにした
- process_priority: 未対応 OS や権限不足時に例外を吐かず警告でスキップするよう改善

### Security
- .env を生成する config_setup で明示的に「.env を絶対に Git にコミットしないこと」をドキュメント化

---

## [0.1.0] - 2026-04-19

初回リリース（推定）: 基本的な自動売買フレームワークのコア機能を提供。

### Added
- コアパッケージ構成を追加
  - 起動スクリプト（run_execution, run_monitoring）
  - 設定管理（kabusys.config）と Settings オブジェクト
  - config_setup / validate_config といった CLI ツール
  - ロギング・プロセス制御ユーティリティ（utils.logging_setup, utils.process_priority）
  - ポートフォリオ構築ライブラリ（portfolio.*）
  - Execution 周りの基盤（BrokerFactory, ExecutionEngine, OrderManager, Reconciler, RiskManager の利用を想定）
  - DuckDB / SQLite を組み合わせたデータ保存・分析基盤の利用（Settings で経路指定）
  - ペーパートレードを分離する設計（paper_trading DB, PAPER_FILL_MODE）
  - ペーパートレード検証レポート生成ツール（tools.paper_verification_report）
  - research モジュールの一部（factor_research の骨子）

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

---

補足・注意事項
- 実装から推測したため、実際のリリース履歴やバージョニングはプロジェクト運用方針に合わせて調整してください。
- 本 CHANGELOG はコード中のコメントや API 設計、環境変数、CLI の存在などから推測して作成しています。細かな実装差分や歴史的経緯はソース管理履歴（git log）を参照してください。