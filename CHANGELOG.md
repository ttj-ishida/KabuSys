# CHANGELOG

すべての注目すべき変更を記載します。フォーマットは "Keep a Changelog" に準拠します。  

現在のパッケージバージョン: 0.1.0

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-22
最初の公開リリース。主要な機能追加と CLI ツールを実装しました。

### Added
- パッケージ基盤とバージョン情報を追加
  - src/kabusys/__init__.py に __version__ = "0.1.0" を追加。

- 実行系・監視系ランナーを追加
  - src/kabusys/run_execution.py
    - ExecutionEngine を起動するエントリスクリプト。
    - KABUSYS_ENV=paper_trading 時は Paper Trading 専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント注入。
    - OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine の組み立てとスレッド実行、停止フラグ（data/stop_requested.flag）・PID ファイル管理。
    - RiskManager 初期設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit breaker 等）をデフォルトで設定。
  - src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60 秒）。不正値時はデフォルトにフォールバックして警告ログ出力。
    - 監視は環境に関わらず本番 sqlite_path を使用する設計（監視データは本番に集約）。

- 設定管理・ウィザード・検証 CLI を追加
  - src/kabusys/config.py
    - 環境変数の読み込み・アクセス用 Settings クラスを実装。
    - .env 自動読み込み機能（プロジェクトルートの .env → .env.local の順、OS 環境変数を保護）。
    - 各種設定のプロパティ化（DUCKDB_PATH, SQLITE_PATH, PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH, Kill フラグ設定、閾値など）。
    - 環境値の検証（KABUSYS_ENV, LOG_LEVEL など）とエラー報告。
  - src/kabusys/config_setup.py
    - 対話式 .env 作成・更新ウィザード（CLI）。既存 .env 読み込み、シークレットマスク表示、確認後にファイルを書き出す。
  - src/kabusys/validate_config.py
    - .env と config/*.yaml の起動前検証ツール。--strict オプションで警告も失敗扱いにできる。
    - 必須環境変数チェック、パスの存在確認、PyYAML があれば YAML のパース検証、KABUSYS_ENV=live 向けの追加警告等を実施。

- Paper Trading 検証レポート生成ツールを追加
  - src/kabusys/tools/paper_verification_report.py
    - ペーパートレード DB（デフォルト data/paper_trading.db）から稼働率・注文成功率・送信率・API レイテンシ（P95 等）を集計してレポート出力。
    - 閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）に基づいて PASS/FAIL を判定。
    - --from / --to / --db オプション対応。

- ポートフォリオ構築・サイズ決定・リスク調整ロジック（純粋関数群）を追加
  - src/kabusys/portfolio/portfolio_builder.py
    - シグナル選定（select_candidates）、等配分（calc_equal_weights）、スコア加重（calc_score_weights）。
  - src/kabusys/portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）、市場レジームに応じた乗数（calc_regime_multiplier）。
  - src/kabusys/portfolio/position_sizing.py
    - 発注株数算出ロジック（risk_based / equal / score）。
    - 単元株丸め（lot_size）、per-position 上限・aggregate cap（利用可能現金に合わせたスケーリング）、cost_buffer（手数料・スリッページ考慮）に対応。

- ユーティリティを追加
  - src/kabusys/utils/logging_setup.py
    - ルートロガーの統一セットアップ関数を実装。標準出力（stdout）への StreamHandler と日次ローテーションの TimedRotatingFileHandler を設定。
    - LOG_LEVEL / LOG_DIR の解決順とファイルハンドラのフォールバック（ディレクトリ作成失敗時は stdout のみ）。
    - 既存ハンドラのクリーンアップを行い二重設定を防止。
  - src/kabusys/utils/process_priority.py
    - Windows と POSIX（Linux/Mac 等）両対応でプロセス優先度設定（high/normal/low）を実装。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を追加。
    - 権限不足や未対応 OS の場合は警告ログでスキップ。

- 研究用ファクター計算モジュール（着手）
  - src/kabusys/research/factor_research.py
    - モメンタム等のファクター計算方針と定数を定義。calc_momentum の実装を開始（ファイル末尾で実装途中）。

- パッケージ公開用の __all__ エクスポートを整備
  - src/kabusys/portfolio/__init__.py で主要関数をエクスポート。

### Changed
- ロギング出力先を stdout に統一して強制的に stderr とは分離（logging_setup の方針）。
  - stdout を使うことで cron/task scheduler 等でのリダイレクト運用を想定。

- .env 読み込み挙動を厳密化
  - export プレフィックス対応、クォートやバックスラッシュエスケープ対応、インラインコメント処理などを実装。
  - OS 環境変数を保護する protected オプションを導入し、.env.local の上書きが安全に行えるようにした。

- Execution / Monitoring のデフォルト挙動
  - Monitoring は常に本番 sqlite_path を利用（監視データの一元管理を想定）。
  - Execution は paper_trading モード時に専用 DB を使用（完全分離）。

### Fixed
- 環境変数読み込み時の競合回避
  - .env 自動読み込みでプロジェクトルートが特定できない場合は自動ロードをスキップして安全に振る舞うようにした。

- MONITOR_POLL_INTERVAL の不正値処理
  - 0 以下や整数でない値が渡された場合にデフォルトにフォールバックして警告を出すように修正（time.sleep に渡して例外が出ないように）。

### Internal / Notes
- RiskManager / ExecutionEngine / BrokerClient 等の詳細実装は別モジュール（src/kabusys/execution 以下）に分離されており、ランナーはそれらを組み合わせて起動します。
- paper_verification_report の集計は SQLite のテーブル構造（system_status, trade_logs, risk_logs 等）に依存します。該当テーブルがない場合は安全に N/A を返す実装になっています。
- factor_research モジュールは継続実装中（calc_momentum の続きが必要）。

---

今後の予定例（未実装・案）
- factor_research の完全実装（Momentum / Value / Volatility / Liquidity の各ファクター算出）。
- ブローカークライアントのモック/実装とユニットテスト強化。
- strategies / data モジュールとの統合テストおよび CI 化。

もし特定のファイルや変更点について詳細な説明や別バージョンへの分割（Unreleased → 次リリース）を希望される場合はお知らせください。