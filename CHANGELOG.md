# Changelog

すべての変更は Keep a Changelog の形式に準拠します。  
このファイルは、リポジトリ内のソースコードから推測される初回リリース相当の機能追加・設計意図をまとめたものです。

## [Unreleased]
- なし（現時点での安定版リリースは v0.1.0）

## [0.1.0] - 2026-04-18

### Added
- 基本パッケージ情報
  - パッケージバージョンを src/kabusys/__init__.py にて `__version__ = "0.1.0"` として定義。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor をポーリングで定期実行する起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止制御用のフラグファイル（data/stop_requested.flag）を検知してループを終了。
    - 監視は環境にかかわらず本番用の sqlite_path を使用して監視テーブルを初期化。
  - run_execution.py
    - ExecutionEngine を起動するスクリプトを追加。
    - `KABUSYS_ENV=paper_trading` 時は paper_trading 用の専用 SQLite（data/paper_trading.db）を利用して本番 DB と分離。
    - ブローカークライアントの生成（BrokerClientFactory）と ExecutionEngine の組み立て・実行（スレッドで実行、停止フラグ検出で停止）。
    - PID ファイル（data/execution.pid）出力を想定。

- 設定関連
  - src/kabusys/config.py
    - Settings クラスを導入し、環境変数経由での設定値取得を統一。
    - .env 自動読み込み（プロジェクトルート検出: .git または pyproject.toml を基準）。読み込み順は OS 環境 > .env.local > .env（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可）。
    - 各種設定プロパティを提供（J-Quants トークン、kabu API、DuckDB/SQLite パス、Paper Trading モードなど）。
    - `PAPER_FILL_MODE` などのバリデーションを実装。
  - src/kabusys/config_setup.py
    - .env の対話式ウィザードを実装。初期 .env の生成 / 既存値更新を支援。
    - 主要な設定項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、LOG_LEVEL、Kill Switch 等）を対象。
  - src/kabusys/validate_config.py
    - 起動前チェック用 CLI を追加。必須環境変数、不正値、config/*.yaml の存在・パース（PyYAML の有無によりスキップ可）、本番環境向けの追加ガードチェックなどを実施。
    - `--strict` オプションで警告も失敗扱いにできる。

- 監視・DB 初期化
  - monitoring.monitoring_db.init_monitoring_db を呼び出して監視テーブルの存在を保証（冪等）。

- ポートフォリオ構築モジュール（純粋関数群）
  - src/kabusys/portfolio/portfolio_builder.py
    - 候補選定（select_candidates）、等配分（calc_equal_weights）、スコア加重（calc_score_weights）を実装。スコア全てが 0 の場合のフォールバック挙動あり。
  - src/kabusys/portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。未知レジーム時のフォールバックやログ出力あり。
  - src/kabusys/portfolio/position_sizing.py
    - position sizing ロジックを実装（allocation_method=`risk_based` / `equal` / `score` に対応）。
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap（available_cash に対するスケーリング）や残差分の配分アルゴリズムを実装。
    - cost_buffer（手数料・スリッページ見積もり）を考慮した保守的なコスト推定を実装。

- ユーティリティ
  - src/kabusys/utils/logging_setup.py
    - 統一的なロギング設定ユーティリティを実装。stdout 出力（StreamHandler）と日次ローテーションのファイル出力（TimedRotatingFileHandler）をルートロガーに設定。LOG_DIR / LOG_LEVEL からの解決、既存ハンドラのクリアなどを行う。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - src/kabusys/utils/process_priority.py
    - Windows / POSIX に対応したプロセス優先度設定ユーティリティ（set_process_priority）および CPU affinity 設定（set_cpu_affinity）を提供。権限不足時に警告を出してスキップする安全策あり。

- Paper Trading サポート / 検証ツール
  - src/kabusys/tools/paper_verification_report.py
    - Paper Trading の検証レポート生成ツールを追加。以下の指標を算出して PASS/FAIL 判定を行う:
      - 稼働率 (uptime_pct)（閾値: 99.0%）
      - 注文成功率（fill_rate）（閾値: 90.0%）
      - 送信率（send_rate）（閾値: 95.0%）
      - P95 レイテンシ（閾値: 200 ms）
    - 指定期間（--from / --to）での SQLite（PAPER_TRADING_SQLITE_PATH / --db）からデータを集計してレポート出力。

- リサーチ（部分実装）
  - src/kabusys/research/factor_research.py
    - モメンタムや MA200 乖離、ATR、ボラティリティ等のファクター計算のための設計と定数を導入。DuckDB 接続を受け取り prices_daily / raw_financials を用いて計算する設計。関数の実装は途中（ファイル末尾で途中切れ・未完了の箇所あり）。

### Changed
- なし（初期リリース）

### Fixed
- なし（初期リリース）

### Notes / Implementation details
- Paper Trading と Live の DB 分離を明示的に実装（Settings.paper_sqlite_path / Settings.is_paper による切替）。
- run_monitoring は Monitoring 用 DB を常に本番 sqlite_path で初期化・接続する設計（コメントに明示）。
- run_execution は BrokerClientFactory を経由してブローカークライアントを切り替える想定（paper_trading 時は MockBrokerClient を利用する設計）。
- ロギングは stdout を優先して出力し、ログファイルの作成に失敗してもサービス停止としない堅牢設計。
- process_priority や CPU affinity の設定は権限や OS により失敗することがあり、その場合は警告ログを出して処理を継続する。

### Known issues / TODO
- research/factor_research.py の関数実装が途中で切れており、完全実装が必要（ファイル末尾の未完了コード参照）。
- position_sizing.calc_position_sizes 内で価格欠損時に前日終値等のフォールバックを使う TODO コメントあり（現状だと price が 0 の場合はその銘柄をスキップしうる）。
- 一部外部ライブラリ（psutil, duckdb, PyYAML 等）の有無に応じたフォールバック処理はあるが、ドキュメントやインストール要件（requirements.txt）で明示する必要あり。
- 実際の ExecutionEngine / Broker 実装や SystemMonitor の詳細は本 CHANGELOG のソースコード一覧に含まれないため、実運用前に統合テストが必要。

---

（本 CHANGELOG はソースコードの内容から推測して作成しています。実際のコミット履歴ではなく、機能スナップショットに基づく初回リリース案です。）