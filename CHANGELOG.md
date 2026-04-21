# Changelog

すべての注目すべき変更はここに記録します。  
このファイルは Keep a Changelog の形式に準拠します。  

最新変更: 2026-04-21

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-21

### Added
- 基本パッケージ情報を追加
  - パッケージバージョンを `src/kabusys/__init__.py` にて `__version__ = "0.1.0"` として設定。

- 環境設定・読み込み
  - プロジェクトルート検出機能を実装（.git または pyproject.toml を基準）。CWD に依存しない `.env` 自動ロードをサポート。
  - `.env` と `.env.local` の自動読み込み機能を追加。既存の OS 環境変数を保護する仕組みを実装。
  - `KABUSYS_DISABLE_AUTO_ENV_LOAD` 環境変数で自動ロードを無効化可能。
  - `.env` のパース機能を強化：`export KEY=val` 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いをサポート。

- Settings クラス（環境設定 API）
  - `src/kabusys/config.py` に `Settings` クラスを追加し、アプリケーション設定（API トークン、DB パス、ログレベル、監視閾値、環境種別など）をプロパティ経由で取得可能に。
  - Paper Trading 関連設定を追加（`paper_sqlite_path`, `paper_fill_mode` 等）。
  - 環境名・ログレベル等のバリデーションを実装（無効値検出時は例外を投げる）。

- 設定関連 CLI
  - 対話式 `.env` ウィザード `src/kabusys/config_setup.py` を追加。`.env` の初期作成・更新を支援。
  - 設定検証ツール `src/kabusys/validate_config.py` を追加。必須環境変数や config/*.yaml の存在・簡易パース検証を行う。`--strict` オプションで警告を失敗扱いにできる。

- ログ・プロセスユーティリティ
  - 共通ログ設定 `src/kabusys/utils/logging_setup.py` を実装。stdout への StreamHandler と日次ローテーションファイル（TimedRotatingFileHandler）をルートロガーへ設定する。ログディレクトリ解決順（引数 > LOG_DIR 環境変数 > デフォルト）を実装。
  - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続するフォールバックを実装。
  - プロセス優先度・CPU affinity 管理ユーティリティ `src/kabusys/utils/process_priority.py` を追加。Windows / POSIX（Linux/Mac/FreeBSD）を吸収し、`set_process_priority` と `set_cpu_affinity` を提供。権限不足や未対応 OS の場合は警告を出してスキップする。

- 実行・監視スクリプト
  - ExecutionEngine 起動スクリプト `src/kabusys/run_execution.py` を追加。起動時にプロセス優先度を設定し、Paper Trading 環境では専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と完全分離する。
  - SystemMonitor 起動スクリプト `src/kabusys/run_monitoring.py` を追加。`MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番の sqlite_path を使用する設計。
  - 起動スクリプトは停止フラグ（data/stop_requested.flag 等）と PID ファイルの扱いをサポートし、安全にスレッド／プロセス終了を行う。

- Execution コンポーネント（起動設定）
  - Execution の依存コンポーネントを組み立てるロジックを追加（BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine の連携）。`RiskConfig`・`EngineConfig` の初期パラメータを定義。
  - Paper trading の場合 Broker の Mock 実装を利用し、初期資金取得等を行う設計。

- ポートフォリオ構築ライブラリ
  - 銘柄選定・配分重み計算モジュール `src/kabusys/portfolio/portfolio_builder.py` を追加（候補選定、等金額・スコア加重を実装）。
  - セクター集中制限・レジーム乗数を扱う `src/kabusys/portfolio/risk_adjustment.py` を追加（セクター上限除外、レジームに応じた乗数）。
  - 株数決定・リスク制限・単元丸めを実装する `src/kabusys/portfolio/position_sizing.py` を追加。以下の特徴を実装：
    - allocation_method による分岐（"risk_based", "equal", "score"）。
    - 単元（lot_size）での丸め処理。
    - ポジション上限（max_position_pct）・最大投下率（max_utilization）・コストバッファ (cost_buffer) を考慮した aggregate cap のスケーリング。
    - スケールダウン後の残差分配ロジック（端数を大きい順に lot 単位で追加配分）。
    - 価格欠損時のスキップやログ出力。

- Paper Trading 検証レポート
  - `src/kabusys/tools/paper_verification_report.py` を追加。紙トレード用 SQLite（PAPER_TRADING_SQLITE_PATH）から各種指標（稼働率、注文成功率、送信率、P95 レイテンシ等）を集計し CLI でレポート出力。閾値を定義して PASS/FAIL 判定を行う。P95 計算や日付フィルタ (--from/--to)、DB パス指定 (--db) をサポート。

- Research（ファクター計算）ベース
  - `src/kabusys/research/factor_research.py` を追加。DuckDB 接続を受けてモメンタム・ボラティリティ等のファクターを計算する設計。モメンタム計算のための定数と関数骨格を実装（ファイルは途中までの実装）。

### Changed
- ロギングの標準出力先を stderr から stdout に統一（cron 等でリダイレクトしやすくするため）。
- ログハンドラの再設定時は既存ハンドラを flush/close してから削除するようにし、二重登録を防止。
- init_monitoring_db を Execution 起動時にも呼び出すようにして、監視テーブルが存在することを保証（冪等処理）。

### Fixed
- MONITOR_POLL_INTERVAL の不正値（非整数・0 以下）に対してデフォルト（60 秒）にフォールバックし、警告ログを出力するようにした（time.sleep に渡して ValueError になるのを回避）。
- プロセス優先度設定で権限不足や未実装ケースが発生した際にクラッシュしないよう例外を捕捉し、警告でスキップするようにした。
- ログディレクトリ作成やファイルハンドラ作成に失敗した場合に、システムが落ちず標準出力のみで継続するフォールバックを追加。
- .env 読み込み時、OS 環境変数を上書きしない保護機構（protected keys）を導入。

### Documentation / CLI
- 設定ウィザードと検証ツールに利用上のヘルプや使用例を追加。`config_setup` は対話式で .env を生成／更新し、保存前に確認ダイアログを表示する。
- validate_config は PyYAML 未インストール時に YAML 検証をスキップして警告を出すようにした。

### Notes / Implementation details
- 監視（SystemMonitor）は停止フラグファイル（data/stop_requested.flag）を監視してループを終了する設計。MONITOR_POLL_INTERVAL でポーリング間隔を制御可能。
- ExecutionEngine は別スレッドでセッションを実行し、停止フラグ検出時に安全に engine.stop() を呼び出す制御を実装。
- Paper Trading は本番 DB と完全分離される設計で、実運用リスクを低減。
- 一部モジュール（例: factor_research）はまだ実装途中の箇所が含まれるため、将来的な拡張やテストが必要。

---

注: 本 CHANGELOG は与えられたコードベースからの推測に基づき作成しています。実際のコミット履歴やリリースノートと差異がある可能性があります。必要であれば各モジュールの変更点をさらに細かく分割してバージョン履歴を作成します。