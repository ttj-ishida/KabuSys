# CHANGELOG

すべての重要な変更はこのファイルに記載します。本プロジェクトは Keep a Changelog の慣習に沿ってバージョニングしています。  

フォーマット:
- Added: 新機能
- Changed: 既存機能の変更
- Fixed: バグ修正 / 安全性・堅牢性の向上
- Removed / Deprecated: 廃止予定（該当なしの場合は省略）

## [Unreleased]

## [0.1.0] - 2026-04-18
初回リリース。自動売買システム「KabuSys」の基本機能群を実装・提供します。

### Added
- 基本パッケージとバージョン定義
  - src/kabusys/__init__.py にバージョン 0.1.0 を追加。

- 環境設定管理
  - src/kabusys/config.py
    - .env の自動読み込み機能を実装（プロジェクトルートを .git / pyproject.toml から検出）。
    - .env ファイルのパースを強化（export KEY=val 形式、シングル/ダブルクォート、バックスラッシュエスケープ、行末コメント処理をサポート）。
    - OS 環境変数を保護するための override/protected 機構を導入。
    - Settings クラスを実装し、各種環境変数（J-Quants / kabuAPI / DB パス / Paper Trading 設定 / 監視閾値 等）をプロパティで取得・バリデーションする機能を提供。

- 環境設定ウィザード（対話式）
  - src/kabusys/config_setup.py
    - .env の初期作成・更新を支援する対話式ウィザードを実装。
    - シークレット項目のマスク表示や既存値の再利用、確認後ファイル出力をサポート。

- 設定検証 CLI
  - src/kabusys/validate_config.py
    - .env および config/*.yaml（存在する場合）の妥当性検証ツールを実装。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 値検証、DB パスの親ディレクトリ確認、PyYAML が無い場合のスキップ対応、KABUSYS_ENV=live 時の追加警告などを提供。
    - --strict オプションで警告を FAIL 扱いにできる。

- 実行系起動スクリプト
  - src/kabusys/run_execution.py
    - ExecutionEngine 起動スクリプトを実装。
    - KABUSYS_ENV=paper_trading の場合は専用の paper_trading SQLite DB を使用して本番 DB と完全分離。
    - BrokerClientFactory を使ったブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - 実行中は data/stop_requested.flag を監視し、フラグ検知で安全に停止する仕組みを導入。
    - 実行用 pid ファイル制御（data/execution.pid）をサポート。

- 監視系起動スクリプト
  - src/kabusys/run_monitoring.py
    - SystemMonitor をポーリングで実行する起動スクリプトを実装。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値は警告を出してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path を使用する（監視データは本番 DB に記録）。
    - data/stop_requested.flag と KeyboardInterrupt による安全停止処理を実装。

- 監視 DB 初期化ユーティリティ呼び出し
  - 起動スクリプトで init_monitoring_db(sqlite_conn) を呼び、監視用テーブルの存在を保証（冪等性）。

- ロギング設定ユーティリティ
  - src/kabusys/utils/logging_setup.py
    - 共通の logging 設定関数を実装。
    - stdout への StreamHandler と日次ローテートの TimedRotatingFileHandler をルートロガーに設定。
    - LOG_DIR/LOG_LEVEL の解決順と既存ハンドラのクリア、ログディレクトリ作成失敗時のファイル出力スキップを考慮。

- プロセス優先度・CPU アフィニティユーティリティ
  - src/kabusys/utils/process_priority.py
    - Windows / POSIX を抽象化した set_process_priority(level) を実装（"high"/"normal"/"low"）。
    - set_cpu_affinity(cpu_count) でプロセスを先頭 N コアにピン留め可能。
    - 権限不足や未対応 OS に対する安全なフォールバックと警告を実装。

- ポートフォリオ構築モジュール
  - src/kabusys/portfolio/portfolio_builder.py
    - シグナルの選別（スコア降順 + tie-breaker）、等金額配分、スコア重み配分（スコア全0 の場合は等金額にフォールバック）を実装。

  - src/kabusys/portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）を実装。
    - 未知のレジームでのフォールバック挙動を明記し、デバッグログを追加。

  - src/kabusys/portfolio/position_sizing.py
    - allocation_method ("risk_based" / "equal" / "score") に基づく株数算出ロジックを実装。
    - 単元株丸め、1 銘柄上限、aggregate cap（available_cash に合わせたスケーリング）、cost_buffer（スリッページ/手数料見積り）を考慮。
    - スケールダウン時の再配分ロジック（fractional remainder に基づく lot 単位での追加配分）を実装。

  - src/kabusys/portfolio/__init__.py
    - 上記関数群をパッケージとして公開。

- 研究（ファクター）基盤（部分実装）
  - src/kabusys/research/factor_research.py
    - DuckDB 接続を用いたファクター計算基盤を実装（Momentum / MA200 / ATR 等の計算方針・定数を含む）。
    - （ファイルの末尾で計算ロジック実装が途中になっているが、設計方針と定数定義を導入）。

- Paper Trading 検証レポート
  - src/kabusys/tools/paper_verification_report.py
    - Paper Trading 用 SQLite（デフォルト data/paper_trading.db）から集計し、稼働率・注文成功率・送信率・APIレイテンシ等の指標を算出。
    - P95 計算、期間フィルタ、閾値を用いた PASS / FAIL 判定（稼働率 99%、成立率 90% など）を実装。
    - CLI オプション --from/--to/--db を提供。

### Changed
- 起動時のプロセス優先度設定を各起動スクリプト（monitoring / execution）で最初に実行するよう統一。
- 監視用の DB 初期化を各起動スクリプト内で冪等に実行して監視テーブルの存在を保証。

### Fixed / Robustness
- SQLite/duckdb 接続は finally ブロックで確実に close されるようにしてリソースリークを防止（run_monitoring, run_execution）。
- .env パーサを堅牢化（引用符内のエスケープ処理、行末コメント処理、export 形式対応）。
- ログディレクトリ作成失敗時でもコンソール出力（stdout）にフォールバックすることで起動不能にならないように改善。
- process priority / cpu affinity は権限不足や未対応環境で例外を握りつぶしつつ警告を出す安全な実装にした。
- MONITOR_POLL_INTERVAL の不正値に対して警告し、デフォルト値にフォールバックする保護を追加。

### Notes / その他
- 本リリースでは設計文書（PortfolioConstruction.md, StrategyModel.md 等）に沿った実装方針・ TODO コメントが散在します。将来的な改善点（銘柄ごとの lot_size 対応、価格フォールバック戦略、factor_research の完全実装 等）をコードコメントとして残しています。
- 本番運用時の注意点として、KABUSYS_ENV=live の場合は LINE 通知設定や Kill Switch 周りの確認を推奨するチェックを validate_config に実装しています。

---

将来的なリリースでは、以下のような項目の追加・改善を予定しています（例）:
- research.factor_research の完全実装とユニットテストの追加
- ブローカーインターフェースのテスト用モックの拡充
- 個別銘柄の単元情報（lot_size）を反映した position sizing の対応
- config ファイルのより詳細なバリデーション（スキーマ駆動）および自動テスト

（終）