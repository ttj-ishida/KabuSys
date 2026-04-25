# Changelog

すべての変更は「Keep a Changelog」形式に従い、重要な変更点を分類しています。日付は本コードベースのスナップショットから推測して記載しています。

## [Unreleased]

### Added
- 開発用ユーティリティと運用スクリプトを追加
  - 環境設定ウィザード CLI: `kabusys.config_setup` により対話式で .env を作成・更新可能になりました。
  - 設定検証ツール: `kabusys.validate_config` で .env や config/*.yaml の事前チェックを実行できます（`--strict` オプションあり）。
  - Paper Trading 検証レポート: `kabusys.tools.paper_verification_report` でペーパートレード用 SQLite を集計しレポート出力します。
- 実行系と監視の起動スクリプトを追加
  - `run_execution.py`: ExecutionEngine 起動スクリプト。KABUSYS_ENV=`paper_trading` 時は専用の paper DB を使用し MockBroker を利用して本番 DB から分離します。停止フラグ・PID ファイル管理、スレッドベースの実行制御を実装。
  - `run_monitoring.py`: SystemMonitor ポーリングループ起動。環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き、停止フラグ検知、例外をハンドルして継続実行します。
- 設定管理
  - `kabusys.config.Settings` クラスを追加。.env 自動ロード（.env、.env.local の優先順）、必須値検出、各種設定プロパティ（DB パス、環境種別、Paper Trading の設定など）を提供。
  - .env パーサの改良: export 形式、クォート付き値のバックスラッシュエスケープ、インラインコメントの扱い等に対応。
- ポートフォリオ構築ライブラリを追加（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`: シグナル選定（選定上位 N、同点タイブレーク）、等金額／スコア加重の重み計算。
  - `kabusys.portfolio.position_sizing`: 各銘柄の発注株数計算（risk_based / equal / score）、単元（lot）丸め、aggregate cap によるスケールダウンロジック。
  - `kabusys.portfolio.risk_adjustment`: セクター集中上限適用（当日売却予定の銘柄除外、"unknown" セクターは上限対象外）、市場レジームに応じた投下資金乗数。
- 共通ユーティリティ
  - `kabusys.utils.logging_setup`: stdout ストリームハンドラと日次ローテートのファイルハンドラをルートロガーに設定。既存ハンドラの二重設定防止、ログディレクトリ作成失敗時のフォールバック等を実装。
  - `kabusys.utils.process_priority`: Windows / POSIX を吸収するプロセス優先度設定、CPU affinity 固定ユーティリティを追加（権限不足時は警告してスキップ）。
- 解析 / 研究モジュール（骨組み）
  - `kabusys.research.factor_research`：DuckDB 接続を受け取りファクター計算を行う設計。モメンタム、MA、ATR、出来高等を想定した実装方針を含む。

### Changed
- ログ設定のデフォルトを整備
  - ログ出力先の決定順とデフォルト値（LOG_DIR、logs/）、ログローテーション（30 日保持）を明確化。
  - コンソール出力は stdout を使用（cron / タスクスケジューラ運用を想定）。
- データベース周りの挙動を明確化
  - 監視用起動では環境に関係なく本番用 sqlite_path を使用（監視は本番 DB に対して動かす想定）。
  - 実行エンジン起動時は KABUSYS_ENV=`paper_trading` の場合に専用の paper_sqlite_path を使用して本番 DB と分離。
- 設定ファイルの自動読み込みの安全化
  - プロジェクトルート検出は `.git` または `pyproject.toml` を基準に探索し、見つからない場合は自動ロードをスキップするように変更（パッケージ配布後の安全性向上）。
  - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` により無効化可能（テスト用途）.

### Fixed
- .env パースの堅牢性向上
  - クォート内のバックスラッシュエスケープ、export プレフィックス、インラインコメントの扱いなどで以前起きうる誤解析を回避。
- ログハンドラの二重登録問題を解消
  - setup_logging() が既存ハンドラをフラッシュ・クローズして削除するようになり、複数回呼び出した際の重複出力を防止。
- プロセス優先度設定失敗時のフォールバック
  - 権限不足や未サポート OS でも例外を送出せず警告ログを残してスキップするように改善。

---

## [0.1.0] - 2026-04-25

最初のリリース（スナップショット）。上記の機能群を含む。

### Added
- パッケージの初期公開バージョン
  - 基本設定管理 (`kabusys.config`)、環境作成ウィザード (`kabusys.config_setup`)、設定検証 CLI (`kabusys.validate_config`)。
  - 実行エンジン起動スクリプト (`run_execution.py`)、監視起動スクリプト (`run_monitoring.py`)。
  - ポートフォリオ構築（選定、重み付け、ポジションサイズ計算、セクター制限、レジーム乗数）。
  - 共通ユーティリティ（ロギング設定、プロセス優先度/CPU 固定）。
  - Paper Trading 検証レポートツール。
  - 研究向けファクターモジュール骨組み（DuckDB ベースのファクター計算設計）。

### Changed
- 初期 API と CLI の設計・ドキュメント化（モジュール内 docstring と注釈による導線）。

### Fixed
- （初期リリース向けに内部整備）.env 読み込みとログ設定周りの安定性向上。

---

※ 上記はソースコード内の docstring・実装から推測して作成した変更履歴です。実際のコミット履歴やチケットに基づく厳密なログとは異なる可能性があります。必要であれば、個々のファイル変更（追加・重要な実装ポイント）ごとに詳細な記述を追加します。