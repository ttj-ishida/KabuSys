# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記述しています。  

なお、本リリース情報は提供されたコードベースから推測して作成しています（実装ファイル・挙動の要約）。

## [Unreleased]

### Added
- なし（次回リリースに向けた未反映の変更点があればここに記載）

---

## [0.1.0] - 2026-04-23

最初の公開リリース。主要な機能群（設定管理、実行/監視ランナー、ポートフォリオ構築、ユーティリティ、分析・検証ツール）を実装。

### Added
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として定義（src/kabusys/__init__.py）。

- 環境・設定管理
  - .env ファイルの自動読み込み機能（プロジェクトルートの検出、.env / .env.local の読み取り、OS 環境変数の保護）を実装（src/kabusys/config.py）。
  - .env ファイルの対話式ウィザード（作成・更新）を提供（src/kabusys/config_setup.py）。対話で主要設定を入力し .env を生成できる。
  - Settings クラスによりアプリケーション設定値（J-Quants / kabuAPI / DB パス / Paper Trading 設定 / 監視閾値 / 環境種別 等）を型付きプロパティとして提供（src/kabusys/config.py）。
  - 環境変数のパースはシングル・ダブルクォート、エスケープ、インラインコメントなどに配慮（config._parse_env_line）。

- 設定検証 CLI
  - 起動前に .env や config/*.yaml の不備を検出する CLI を提供（src/kabusys/validate_config.py）。
  - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パス存在チェック、YAML パース（PyYAML がない場合はスキップ）、本番環境に対する追加警告等を実装。
  - --strict オプションで警告も失敗扱いにできる。

- 実行・監視ランナー
  - ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 DB を使用し、MockBroker 経由でペーパートレードを分離して実行。
    - 起動時にプロセス優先度を "high" に設定。
    - Broker クライアント作成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て、ExecutionEngine の起動と停止フラグ処理を含む。
    - 停止フラグ（data/stop_requested.flag）による安全な終了制御と execution.pid の取り扱い。
  - SystemMonitor 起動スクリプト（src/kabusys/run_monitoring.py）
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用 sqlite_path を使う（監視 DB の初期化含む）。
    - 停止フラグ検知でループを終了、例外発生時もログを残して次回ポーリングに継続。

- ポートフォリオ構築モジュール（純粋関数群）
  - 銘柄選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates（スコア降順で上位 N を選択）
    - calc_equal_weights（等金額配分）
    - calc_score_weights（スコア正規化分配、全スコア 0 の場合に等配分へフォールバック）
  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap（既存ポジションを考慮してセクター上限を超える候補を除外）
    - calc_regime_multiplier（'bull'/'neutral'/'bear' に基づく投下資金乗数、未知のレジームはフォールバック）
  - 株数決定・リスク制限・単元丸め（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes（allocation_method 'risk_based'/'equal'/'score' に対応、lot_size 単位で丸め、aggregate cap によるスケーリング・端数配分を実装）

- 解析・検証ツール
  - Paper Trading 検証レポート生成スクリプト（src/kabusys/tools/paper_verification_report.py）
    - ペーパートレード用 SQLite（環境変数 PAPER_TRADING_SQLITE_PATH 或いは引数 --db 指定）から各種指標を取得してレポート（稼働率・注文成功率・送信率・レイテンシ等）を出力。
    - PASS/FAIL 判定基準（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200 ms）を実装。
    - 日付フィルタ（--from/--to）対応。

- ユーティリティ
  - ロギング初期化ユーティリティ（src/kabusys/utils/logging_setup.py）
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）をルートロガーに設定。ログレベル/ログディレクトリの解決ロジックを提供。
    - 既存ハンドラのクリーンアップを行い二重登録を防止。
  - プロセス優先度 / CPU affinity 設定（src/kabusys/utils/process_priority.py）
    - Windows/Linux/Mac 等の差分を吸収し、nice() や psutil の優先度定数を用いて優先度設定を実施。失敗時は警告でスキップ。

- 研究用ファクター計算の土台
  - ファクター計算モジュール（src/kabusys/research/factor_research.py）の骨組みを追加（モメンタム・MA200・ATR・流動性等の指標を計算する設計、DuckDB 経由での prices_daily/raw_financials 参照を想定）。※ファイルは途中まで実装（スニペットの続きがある想定）。

### Changed
- 初回リリースのため該当なし（ベース実装の追加のみ）

### Fixed
- 初回リリースのため該当なし

### Security
- 環境変数読み込みにおいて OS 環境変数を保護する仕組みを導入（config.py の protected set）。これにより .env.local 等で OS 環境変数が誤って上書きされるのを防止。

### Notes / Implementation Details
- Paper Trading と Live の DB 分離:
  - ペーパートレード時は settings.paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番 DB と完全分離する設計。
- Logging:
  - ログファイル作成に失敗した場合はコンソール出力のみで継続するフェールセーフを備える。
- Process Priority:
  - 権限不足や未対応 OS の場合は安全にスキップして警告を出力する。
- 設計方針:
  - ポートフォリオ/リスク/サイズ計算は DB 参照や外部 API を行わない純粋関数として実装し、テスト容易性と再現性を重視。

---

今後の改善候補（参考）
- factor_research の完全実装（duckdb SQL と集計ロジックの完了）
- 詳細なユニットテストと CI 設定
- 銘柄別に単元（lot_size）を持たせる拡張（コメントに TODO）
- ログやメトリクスの外部送信（Prometheus / Datadog 等）連携
- ExecutionEngine / Broker クライアントのエラー・遅延対策の強化

---

参照:
- 主な実装ファイル: src/kabusys/{config.py,config_setup.py,validate_config.py,run_execution.py,run_monitoring.py,portfolio/*,utils/*,tools/paper_verification_report.py,research/factor_research.py}