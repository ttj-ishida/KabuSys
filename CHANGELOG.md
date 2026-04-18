# Changelog

すべての重要な変更は Keep a Changelog の形式に準拠して記載しています。  
現在のリリース: 0.1.0 — 2026-04-18

## [0.1.0] - 2026-04-18

### Added
- プロジェクト初期版を追加。
  - パッケージメタ情報: `kabusys.__version__ = "0.1.0"` を追加。
- 実行用エントリスクリプトを追加
  - run_execution.py
    - ExecutionEngine の起動スクリプト。プロセス優先度を "high" に設定して起動。
    - 環境に応じて paper_trading 用の専用 SQLite（`data/paper_trading.db` をデフォルト）を使用し、本番 DB と分離。
    - BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler を組み立ててエンジンをスレッドで実行。
    - 停止フラグ（`data/stop_requested.flag`）検出で安全に停止。PID ファイル管理。
    - RiskManager のデフォルト構成（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を定義。
  - run_monitoring.py
    - SystemMonitor ポーリングループを起動するスクリプト。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可（デフォルト 60 秒）。不正な値はデフォルトにフォールバック。
    - 監視用 DB は実行環境にかかわらず本番の sqlite_path（`SQLITE_PATH`）を使用する設計。
    - 停止フラグ（`data/stop_requested.flag`）および KeyboardInterrupt による終了処理を実装。
- 設定・環境管理
  - config.py
    - .env ファイル自動読み込み（プロジェクトルートを .git または pyproject.toml から検出）機能を実装。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
    - `.env` パースの詳細実装：`export` プレフィックス対応、クォート内のエスケープ処理、インラインコメント処理などを正確に実装。
    - 各種設定プロパティを定義（J-Quants / kabu API / LINE / DuckDB/SQLite パス / Paper Trading モード / 監視しきい値 / PID/killswitch 関連 / 環境種別判定等）。
    - `Settings` クラスとグローバル `settings` インスタンスを提供。
  - config_setup.py
    - 対話式ウィザードで .env を生成・更新する CLI を追加。既存 .env 読み込み、シークレットマスク表示、保存前の確認などの機能を提供。
    - デフォルト値、選択肢、説明文を含む対話フローを実装。
- 設定検証 CLI
  - validate_config.py
    - .env と config/*.yaml の不足・不整合を起動前に検出する CLI（`--strict` オプションで警告を FAIL 扱いに可能）。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性チェック、ログレベル確認、DB パス・親ディレクトリ存在チェック、YAML ファイルのパース確認（PyYAML 未インストール時はスキップ）、本番環境向けの追加ガードを実装。
- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次、30 日保持）を設定する統一ユーティリティを追加。
    - ログレベルの解決順（引数 > 環境変数 LOG_LEVEL > デフォルト）やログディレクトリ解決（引数 > LOG_DIR > デフォルト）を実装。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
    - stdout を使用することで cron 等からのリダイレクト運用を想定。
  - utils/process_priority.py
    - Windows / POSIX の差を吸収してプロセス優先度（"high"/"normal"/"low"）を設定するユーティリティを追加。psutil を利用し、AccessDenied 等は警告でスキップ。
    - CPU affinity 設定関数 `set_cpu_affinity` を提供。
- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py
    - シグナルの選定（score 降順、signal_rank によるタイブレーク）`select_candidates`、等金額配分 `calc_equal_weights`、スコア重み配分 `calc_score_weights`（全スコアが 0 の場合は等配分へフォールバック）を実装。
  - portfolio/risk_adjustment.py
    - セクター集中制限を実装する `apply_sector_cap`（既存保有のセクター時価を計算して上限超過セクターの候補除外）。
    - 市場レジームに応じた乗数 `calc_regime_multiplier`（bull/neutral/bear を定義し未定義は警告の上で 1.0 にフォールバック）。
  - portfolio/position_sizing.py
    - 発注株数計算 `calc_position_sizes` を実装（allocation_method: "risk_based" / "equal" / "score"）。
    - risk_based：リスクパーセント・損切り幅から基本株数を計算。
    - equal/score：各銘柄の重みに基づく割当を計算。
    - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap（利用可能現金を超える場合のスケーリング）、cost_buffer（手数料/スリッページ見積）を考慮したスケールダウンロジックを実装。
    - スケーリング時に残差（fractional remainder）に基づく追加配分ロジックを実装し、再現性を保持。
  - portfolio/__init__.py で主要 API を再エクスポート。
- モニタリング DB 初期化連携
  - monitoring.monitoring_db.init_monitoring_db を run_execution/run_monitoring から呼び出して監視テーブルの存在を保証（冪等）。
- DuckDB 統合
  - run_execution/run_monitoring および research/factor_research で DuckDB 接続を使用する設計（`duckdb.connect`）。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH）を解析して検証レポートを生成する CLI を追加。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシなど。
    - デフォルト基準値を定義（稼働率 >= 99%、fill_rate >= 90%、send_rate >= 95%、P95 <= 200 ms）し、PASS/FAIL 判定を出力。
    - 日付フィルタ（--from / --to）、--db オプション対応。DB 存在チェックとエラー耐性あり。
- 研究モジュール（計算アルゴリズム素地）
  - research/factor_research.py
    - モメンタム等のファクター計算の設計と一部実装（定数、関数シグネチャ、P95 等のユーティリティ）を追加。DuckDB を入力とする計算を想定。

### Changed
- （初期リリースのためなし）

### Fixed
- .env パースの堅牢化
  - クォート内のバックスラッシュエスケープと対応する閉じクォート検出、`export KEY=val` 形式、インラインコメントの扱い（クォートなしでは '#' 前の空白でコメントと判断）等を実装し、実運用での .env 設定ミスを軽減。

### Deprecated
- （初期リリースのためなし）

### Removed
- （初期リリースのためなし）

### Security
- .env ファイル生成時の注意喚起を config_setup に追加: ".env は絶対に Git にコミットしないこと" を明記。
- validate_config による本番環境（KABUSYS_ENV=live）向けチェックを追加し、LINE 通知設定や Kill Switch 自動クリア設定等の未設定/危険設定を警告。

---

補足:
- 多くの CLI/ユーティリティは外部ライブラリ（psutil, duckdb, PyYAML 等）に依存します。インストールされていない場合は該当機能が警告やスキップでフォールバックする実装になっています（例: PyYAML 未インストール時は YAML 検証をスキップ）。
- 実運用前に `.env` の設定（必須項目: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）と `validate_config` の実行を推奨します。