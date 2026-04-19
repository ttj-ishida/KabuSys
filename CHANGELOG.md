# CHANGELOG

すべての notable な変更を Keep a Changelog 準拠で記載します。  
このファイルはコードベースの現在の状態から推測して作成しています（初期リリース相当）。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-04-19

### 追加 (Added)
- 基本アプリケーションの初期実装を追加。
  - パッケージ名: kabusys
  - バージョン: 0.1.0（src/kabusys/__init__.py）

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、paper_trading 用 SQLite（data/paper_trading.db をデフォルト）に完全分離して記録する実装。
    - 実行中はプロセス優先度を "high" に設定。
    - 停止フラグ (data/stop_requested.flag) と PID ファイル (data/execution.pid) に対応した安全な停止ロジックを実装。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバック。
    - 監視処理は環境にかかわらず本番用 sqlite_path を使用する旨の実装（監視 DB の一貫性確保）。
    - 停止フラグ (data/stop_requested.flag) によるループ停止に対応。
    - DB 接続で SQLite / DuckDB を利用（init_monitoring_db によるテーブル初期化）。

- 設定管理・ツール
  - config.py
    - Settings クラスを実装し、環境変数から設定を取得する API を提供。
    - .env 自動読み込み機能を追加（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - 各種デフォルト値、バリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）を実装。
  - config_setup.py
    - 対話式 .env ウィザードを実装（.env の作成・更新を支援）。
    - シークレットマスク表示、選択肢・デフォルトの取り扱い、.env 書き出し機能を提供。
  - validate_config.py
    - 起動前設定検証 CLI を追加（必須環境変数、KABUSYS_ENV、DB パス、config/*.yaml の存在や YAML パース等をチェック）。
    - --strict オプションで警告をエラー扱いにする機能。

- ログ・プロセスユーティリティ
  - utils/logging_setup.py
    - setup_logging() を実装。ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）を設定。
    - ログ出力先の解決順（引数 > LOG_DIR > デフォルト logs/）、ログレベル解決順（引数 > LOG_LEVEL > INFO）に対応。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を実装。
    - Windows / POSIX (Linux/Mac/FreeBSD) の差分を吸収。権限不足や未対応プラットフォームでは安全にスキップして警告を出力。

- ポートフォリオ構築
  - portfolio/portfolio_builder.py
    - 銘柄選定（select_candidates）および配分重み計算（calc_equal_weights, calc_score_weights）を実装。
    - スコアが全て 0 の場合は等金額フォールバックを実装（警告出力）。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）とレジーム乗数（calc_regime_multiplier）を実装。
    - "unknown" セクターは上限チェックの対象外とする挙動。
    - regime に対して既定のマップを実装（bull/neutral/bear）し、未知値はフォールバック。
  - portfolio/position_sizing.py
    - 各銘柄の発注株数算出ロジックを実装（allocation_method: "risk_based" / "equal" / "score"）。
    - 単元株（lot_size）で丸め、per-stock 上限・aggregate cap（利用可能現金）に基づくスケールダウン処理を実施。
    - cost_buffer を考慮した保守的なコスト見積もりと余剰配分アルゴリズムを実装。
    - 入力データ欠損時にログでスキップする堅牢性を実装。

- 解析・レポート
  - tools/paper_verification_report.py
    - ペーパートレード用検証レポート生成スクリプトを追加。
    - システム稼働率、注文成功率、送信率、P95 レイテンシなどを計算し、基準（閾値）による PASS/FAIL 判定を行う。
    - P95 計算、日付フィルタ、DB 存在チェック、各種欠損データの扱いを実装。
    - デフォルト DB パスは data/paper_trading.db。PAPER_TRADING_SQLITE_PATH 環境変数や --db オプションで上書き可能。

- 研究用（部分実装）
  - research/factor_research.py
    - ファクター計算モジュールを追加（モメンタム / Value / Volatility / Liquidity を想定）。
    - DuckDB を利用し prices_daily / raw_financials を参照する設計。
    - 設計方針・定数と calc_momentum の雛形を含む（処理の一部が途中実装）。

### 変更 (Changed)
- なし（初回リリース相当の追加が中心）

### 修正 (Fixed)
- なし（初期実装）

### 削除 (Removed)
- なし

### 既知の問題 (Known issues)
- research/factor_research.calc_momentum の実装が途中で終わっている箇所が存在（ファイル末尾が途中）。
- apply_sector_cap の price 欠損時にエクスポージャーが過少評価される可能性があり、将来的にフォールバック価格の導入がコメントで示されている。
- set_process_priority / set_cpu_affinity は権限不足や未対応 OS の場合に動作しない可能性があり、その場合は警告を出してスキップする設計。
- monitoring は「環境にかかわらず本番 sqlite_path を使用する」仕様のため、paper_trading と監視 DB の分離を期待する場合は注意が必要（実行エンジンは paper_trading 用 DB に分離されている）。

### 環境変数一覧（主要）
- KABUSYS_ENV (development|paper_trading|live) — 環境種別
- JQUANTS_REFRESH_TOKEN — 必須
- KABU_API_PASSWORD — 必須
- KABU_API_BASE_URL — デフォルト http://localhost:18080/kabusapi
- DUCKDB_PATH — デフォルト data/kabusys.duckdb
- SQLITE_PATH — 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 DB（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE — paper trading の約定モデル（instant|partial|never|reject）
- LOG_LEVEL, LOG_DIR — ログ制御
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト 60）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — .env 自動ロードを無効化するフラグ（任意）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill flag を自動クリアする設定（本番では 0 推奨）

### 使用方法メモ
- 設定検証: python -m kabusys.validate_config
- 設定ウィザード: python -m kabusys.config_setup
- 実行エンジン起動: python -m kabusys.run_execution
- 監視起動: python -m kabusys.run_monitoring
- ペーパートレード検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

---

今後の作業候補（TODO）
- research/factor_research の完実装（calc_momentum の完成、他ファクターの実装）。
- 銘柄別 lot_size 対応（stocks マスタに単元情報を持たせる）。
- price 欠損時のフォールバック価格ロジック導入。
- 監視 DB とペーパートレード DB の取り扱いに関するドキュメント明確化。