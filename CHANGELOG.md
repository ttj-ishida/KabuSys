# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠して記載しています（日本語）。

## [Unreleased]

### Added
- research/factor_research.py に基礎的なファクター計算モジュールを追加（Momentum / Value / Volatility / Liquidity を想定）。DuckDB 接続を受け取り prices_daily / raw_financials テーブルから計算する設計。ファイルは途中（実装継続中）である旨を明記。
- 各モジュールのログ出力やデバッグ情報を強化（各所で logger を利用）。
- ドキュメント注釈やコメントを追加して設計意図を明確化。

### Changed
- 一部関数での警告メッセージや例外ハンドリングを改善（フォールバック処理や警告ログを追加）。

### Known issues
- research/factor_research.py が途中で終端している（実装継続が必要）。

---

## [0.1.0] - Initial release (リリース日不明)

初回リリース。自動売買システム KabuSys の基盤機能をまとめて追加しました。

### Added
- パッケージエントリポイント・バージョン定義
  - src/kabusys/__init__.py に __version__ = "0.1.0" を追加。

- 起動スクリプト
  - src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境に依存せず本番用 sqlite_path を使用する実装。
    - 停止フラグ（data/stop_requested.flag）検知でループを終了。
  - src/kabusys/run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は Paper Trading 用の MockBrokerClient を利用し、専用 SQLite（data/paper_trading.db など）を使用して本番 DB と分離。
    - 停止フラグ（data/stop_requested.flag）を参照し、フラグ検知時にエンジンを停止。
    - 実行はデーモンスレッドで行い、PID ファイルを管理。

- 設定管理 / .env ユーティリティ
  - src/kabusys/config.py
    - プロジェクトルート自動検出（.git または pyproject.toml を起点）に基づく .env 自動読み込み機能を実装。
    - .env のパースロジックを強化（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応）。
    - Settings クラスで各種環境変数の取得メソッドを提供（DB パス、KABUSYS_ENV/ログレベルの検証、Paper Trading 用設定、監視設定閾値など）。
    - KILL_FLAG_CLEAR_ON_START、PAPER_FILL_MODE 等の専用設定をサポート。
  - src/kabusys/config_setup.py
    - .env の対話的生成・更新ウィザードを追加（項目一覧、マスク入力、既存値読み込み、保存機能）。
  - src/kabusys/validate_config.py
    - 起動前に .env と config/*.yaml の妥当性を検証する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パス親ディレクトリの存在確認、YAML パース検証（PyYAML 未インストール時は警告）などを行う。
    - --strict オプションで警告を FAIL 扱いにできる。

- 実行・監視用ユーティリティ
  - src/kabusys/utils/logging_setup.py
    - 統一ロギング設定ユーティリティを追加。
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーに設定。
    - LOG_DIR/LOG_LEVEL 優先解決、既存ハンドラのクリア処理、ディレクトリ作成エラー時のフォールバックなどを実装。
  - src/kabusys/utils/process_priority.py
    - プラットフォーム差分（Windows / POSIX）を吸収したプロセス優先度設定ユーティリティを追加。
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。権限不足などの失敗は警告でスキップ。

- Execution サブシステム関連（実行時の組み立て）
  - run_execution から使用するコンポーネントの組み立てロジックを準備（BrokerClientFactory、ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager 等の利用を想定）。RiskConfig のデフォルトパラメータを定義し、初期ポートフォリオ値に broker.get_available_cash() を使用。

- 監視用 DB 初期化
  - monitoring_db.init_monitoring_db を呼んで監視テーブルの存在を保証（冪等）。

- Paper Trading 検証ツール
  - src/kabusys/tools/paper_verification_report.py
    - Paper Trading の検証レポート生成ツールを追加。
    - system_status / trade_logs / risk_logs などのテーブルから稼働率、注文成功率、送信率、レイテンシ（avg / max / P95）などを集計。
    - 判定閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）を定義し、PASS/FAIL を判定。
    - コマンドライン引数 --from / --to / --db をサポート。

- ポートフォリオ構築関連（純関数群）
  - src/kabusys/portfolio/portfolio_builder.py
    - シグナルのソートと候補選択 select_candidates。
    - 等金額配分 calc_equal_weights とスコア加重 calc_score_weights（全スコアが 0 の場合は等配分へフォールバック）。
  - src/kabusys/portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap（売却予定銘柄除外処理、unknown セクターは上限適用対象外）。
    - 市場レジームに応じた乗数 calc_regime_multiplier（bull/neutral/bear のマップ、未知レジームは警告して 1.0 にフォールバック）。
  - src/kabusys/portfolio/position_sizing.py
    - 発注株数計算 calc_position_sizes を追加。
    - allocation_method（risk_based / equal / score）に対応し、lot_size（単元）で丸め、max_position_pct や max_utilization、cost_buffer（手数料/スリッページ見積）を考慮した aggregate cap のスケーリング処理を実装。
    - スケーリング後の端数処理で残余キャッシュに応じて lot_size 単位で追加配分するロジックを搭載。

- パッケージ表記
  - src/kabusys/portfolio/__init__.py で上記関数群をエクスポート。

### Changed
- run_monitoring/run_execution 起動時に最初にプロセス優先度を "high" に設定する処理を追加（set_process_priority を呼び出す）。
- ログハンドラの設計を統一し、ログファイル名をアプリ名ベース（例: logs/execution.log, logs/monitoring.log）にした。

### Fixed
- .env 読み込みの失敗時に警告を出して続行するようにし、テストや配布後の挙動を安定化。
- logging_setup でログディレクトリ作成に失敗した場合でもコンソール出力は維持されるように修正。

### Security
- .env ファイルは生成時に Git にコミットしないようドキュメントに明記（config_setup のヘッダコメント）。

### Notes / Implementation details
- MONITOR_POLL_INTERVAL の不正値（0 以下や整数でない値）に対しては警告を出してデフォルト（60 秒）へフォールバックする安全策を実装（run_monitoring._get_poll_interval）。
- Monitoring は KABUSYS_ENV の値にかかわらず本番用 sqlite_path を使用する設計上の決定を明示（run_monitoring）。
- Paper Trading 用 DB は環境変数と Settings.paper_sqlite_path を用いて完全に分離（run_execution）。
- プロセス停止制御はファイルフラグ（data/stop_requested.flag、data/kill.flag など）を用いる設計。
- 一部モジュール（factor_research.py など）は DuckDB を想定した実装で、DuckDB 接続を受け取る API 設計。

---

今後の予定（イメージ）
- factor_research の完成（各ファクターの SQL/計算ロジックの実装完了）。
- Execution / Broker クライアント群のユニットテスト拡充および統合テストの追加。
- エラーハンドリング・監視アラート（LINE 通知など）の実装強化。