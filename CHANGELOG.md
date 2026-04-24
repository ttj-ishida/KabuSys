# CHANGELOG

すべての注目すべき変更点を記録します。フォーマットは「Keep a Changelog」に準拠します。  
link: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

- （なし）

## [0.1.0] - 2026-04-24

初回リリース。日本株自動売買システム KabuSys のコアユーティリティと実行/監視スクリプトの初期実装を追加。

### Added
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として追加。

- 環境設定・読み込み
  - `.env` 自動読み込み機能を実装（プロジェクトルートを `.git` または `pyproject.toml` で検出）。
  - `.env` ファイルのパース機能を実装（`export KEY=val`、クォート、エスケープ、コメント処理に対応）。
  - `kabusys.config.Settings` による環境変数取得ラッパーを実装（各種設定プロパティ・検証を含む）。
  - 必須値未設定時に明示的なエラーを出す `_require()` を実装。
  - PAPER_TRADING 用の各種パスと動作モード（`PAPER_FILL_MODE` 等）をサポート。

- 設定ウィザード CLI
  - `kabusys.config_setup` に対話式ウィザードを実装し、`.env` の作成/更新を支援。
  - 入力のマスキングやデフォルト値提示、保存確認を実装。

- 設定検証 CLI
  - `kabusys.validate_config` を実装。`.env` や `config/*.yaml` の存在・基本的妥当性をチェック。
  - `--strict` オプションにより警告も失敗扱いにできる。
  - PyYAML が未インストールの場合は YAML 内容検証をスキップし、警告を表示する。

- 実行/監視エントリポイント
  - `run_execution.py`：ExecutionEngine 起動用スクリプトを追加。
    - 起動時にプロセス優先度を "high" に設定。
    - 環境が `paper_trading` の場合は paper 用 SQLite（`data/paper_trading.db` デフォルト）を使用し、本番 DB と分離。
    - Broker クライアントの生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て、Engine の起動ループを実装。
    - 停止フラグ（data/stop_requested.flag）検出で安全に停止。
    - PID ファイルパス制御（`data/execution.pid` デフォルト）。
  - `run_monitoring.py`：SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境にかかわらず本番の sqlite_path を監視 DB として使用（監視は本番向け設定で動作）。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔の上書きをサポート（不正値はデフォルト 60 秒へフォールバック）。
    - 停止フラグ検出でループを終了、KeyboardInterrupt による終了処理を実装。
    - duckdb 接続を併用。

- 監視 DB 初期化
  - `monitoring.monitoring_db.init_monitoring_db` を呼び出して monitoring 用テーブルを冪等的に準備する処理を実装（起動スクリプトで利用）。

- ログ基盤
  - `kabusys.utils.logging_setup.setup_logging` を実装。
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）を設定。
    - ログレベル・ログディレクトリは引数 / 環境変数 / デフォルトで解決。
    - ログディレクトリ作成失敗時はファイル出力をスキップし、コンソール出力のみで継続。
    - stdout を利用することでジョブスケジューラ等とのログリダイレクト運用を想定。

- プロセス優先度・CPU 固定ユーティリティ
  - `kabusys.utils.process_priority` を実装。
    - Windows / POSIX（Linux, macOS, FreeBSD）での優先度設定（nice / Windows priority）を抽象化。
    - CPU affinity 固定（最初の N コアに固定）機能を実装。
    - 権限不足や未対応 OS 時に警告でフォールバック。

- ポートフォリオ構築ユーティリティ
  - `kabusys.portfolio.portfolio_builder`：
    - 候補選定（スコア降順 + tie-breaker）、等加重・スコア加重の重み計算を実装（スコアが全て 0 の場合は等配分にフォールバック）。
  - `kabusys.portfolio.risk_adjustment`：
    - セクター集中上限（apply_sector_cap）を実装。既存ポジションのセクター別エクスポージャーを計算し、上限を超えるセクターの新規候補を除外。
    - レジームに応じた乗数（calc_regime_multiplier）を実装（bull/neutral/bear をマッピング、未知は 1.0 にフォールバック）。
  - `kabusys.portfolio.position_sizing`：
    - risk_based, equal, score の配分方式に対応した株数決定ロジックを実装。
    - 単元株（lot_size）丸め、1銘柄上限・aggregate cap スケーリング、コストバッファ反映、残余キャッシュを利用した端数配分ロジックを実装。

- 解析 / 研究用ツール
  - `kabusys.research.factor_research`（一部実装）：DuckDB からのデータ参照でモメンタム等のファクターを計算するための枠組みを追加（モメンタム期間・ATR 等の定数を定義、calc_momentum の雛形あり）。
  - `kabusys.tools.paper_verification_report`：
    - ペーパートレード用 DB を解析して稼働率・注文成功率・送信率・レイテンシ（P95）等を集計し、基準値（PASS/FAIL）判定を行うレポート生成 CLI を実装。
    - P95 の計算、NULL/データ欠損時のハンドリング、期間フィルタ（ISO8601 UTC）対応を実装。
    - デフォルト DB パスは `data/paper_trading.db`、`--db` / 環境変数で上書き可能。

- その他ユーティリティ
  - 各種 CLI スクリプトのヘルプ・引数処理を実装。
  - 停止フラグ（data/stop_requested.flag）や kill スイッチ関連の設定（KILL_FLAG_CLEAR_ON_START）等、運用を考慮した安全機構を導入。

### Changed
- （初回リリースのため該当なし）

### Fixed
- 環境変数パーサーの改善点
  - クォートあり値のエスケープ処理、行内コメント処理、`export` プレフィックス対応などを実装し、より堅牢に .env を読み込めるよう改善。

- ログ出力の安定化
  - 既存ハンドラの flush/close 後にルートロガー設定を上書きすることで多重ハンドラ登録を回避。

### Deprecated
- （なし）

### Removed
- （なし）

### Security
- （なし）

---

注記:
- 実装の多くは純粋関数または起動スクリプト中心で、外部のブローカークライアント・ExecutionEngine・SystemMonitor 等の詳細実装（別モジュール）に依存しています。  
- Paper Trading と Live（本番）データは分離される設計になっており、ペーパーモード時は専用の SQLite を利用することで本番 DB への影響を避けます。