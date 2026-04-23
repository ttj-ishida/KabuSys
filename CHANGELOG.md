# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]
- （なし）

## [0.1.0] - 2026-04-23
初回リリース。日本株自動売買フレームワーク「KabuSys」の基本コンポーネントを実装しました。

### Added
- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60秒）。
    - 停止フラグ（data/stop_requested.flag）検知による安全停止処理を実装。
    - 監視は常に production 用の SQLite パス（Settings.sqlite_path）を使用する設計。
    - duckdb と sqlite の接続初期化および監視 DB テーブル初期化を行う。
    - プロセス優先度を高 (high) に設定する処理を追加。
  - run_execution.py
    - ExecutionEngine（取引実行）の起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合はペーパートレード用の MockBrokerClient を利用し、専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル管理（data/execution.pid）に対応。
    - スレッド実行によるエンジン起動／停止監視を実装。
    - プロセス優先度を高 (high) に設定する処理を追加。

- 設定管理
  - config.py
    - .env / .env.local の自動読み込み機能（OS 環境変数を保護）を実装。`KABUSYS_DISABLE_AUTO_ENV_LOAD` による自動ロード無効化をサポート。
    - .env の行パーサを実装（コメント、引用符、export 形式、エスケープ対応）。
    - Settings クラスを追加し、J-Quants トークン、kabuAPI パスワード、DB パス、ペーパートレード設定、監視閾値、環境 (development/paper_trading/live) など多数のプロパティを提供。値のバリデーションを含む。
  - validate_config.py
    - 起動前に .env と config/*.yaml の整合性をチェックする CLI を追加（--strict オプションで警告を失敗扱いにできる）。
    - 必須環境変数チェック、パス存在チェック（親ディレクトリ）、YAML パースチェック（PyYAML がインストールされている場合）、本番環境向けの追加警告を実装。
  - config_setup.py
    - 対話式ウィザードで .env を初期作成／更新する CLI を追加。項目のデフォルト・選択肢・マスク表示（シークレット）に対応。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - 銘柄候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア重み配分（calc_score_weights）を実装。
  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を追加（既存保有のセクター比率に基づき新規候補を除外）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear のマッピング、未知レジームはフォールバック）。
  - portfolio/position_sizing.py
    - 発注株数算出ロジック calc_position_sizes を実装。
    - risk_based / equal / score の配分方式に対応。単元株（lot_size）、手数料・スリッページを考慮する cost_buffer、aggregate cap によるスケーリング、端数処理（lot_size 単位での切り捨て／再配分）などを実装。

- 実行関連コンポーネント（組み立て用の名前空間）
  - kabusys.portfolio パッケージエクスポートを追加（主要関数をトップレベルで利用可能に）。

- ユーティリティ
  - utils/logging_setup.py
    - setup_logging 関数を追加。stdout 出力用 StreamHandler と日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log）をルートロガーに設定。ログディレクトリ作成失敗時はファイル出力をスキップして警告を表示。
    - ログレベルとログディレクトリの解決順序を文書化（引数 > 環境変数 > デフォルト）。
  - utils/process_priority.py
    - set_process_priority(level) を追加。Windows / POSIX（Linux, macOS等）差分を吸収してプロセス優先度を設定。失敗時は警告を出してスキップ。
    - set_cpu_affinity(cpu_count) を追加（指定がなければ動作しない）。権限不足や未サポート OS の場合は警告でスキップ。

- ツール
  - tools/paper_verification_report.py
    - ペーパートレード SQLite DB を解析して検証レポートを生成する CLI を追加。
    - システム稼働率、注文成功率（fill rate）、送信率（send rate）、リスク却下数、API レイテンシ（avg/max/P95）などを集計し、閾値に基づく PASS/FAIL 判定を出力。
    - P95 計算、日付フィルタ（--from / --to）、DB パスの指定（--db または環境変数 PAPER_TRADING_SQLITE_PATH）に対応。

- リサーチ（スキャフォールド）
  - research/factor_research.py
    - ファクター計算モジュールの骨組みを追加（モメンタム、ボラティリティ、バリュー等の計算方針と定数を定義）。DuckDB を利用して prices_daily / raw_financials テーブルから計算する設計。
    - モメンタム計算（calc_momentum）等の実装を着手（ファイル末尾が一部未完の状態）。

- パッケージ情報
  - __init__.py にてパッケージ名とバージョンを定義（__version__ = "0.1.0"）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- （初回リリースのため該当なし）

---

注記:
- 一部モジュール（research/factor_research.py）は実装途中でファイル末尾が切れているため、今後のリリースでファクター計算の完成およびユニットテスト追加を予定しています。
- .env ファイルは機密情報を含むため、README・ドキュメントで明示している通り Git 管理に含めないでください（config_setup.py のヘッダにも注意書きあり）。