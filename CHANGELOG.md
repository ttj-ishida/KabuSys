# Changelog

すべての重要な変更をここに記録します。フォーマットは「Keep a Changelog」に準拠しています。

全体的なバージョンはパッケージ定義（kabusys.__version__）に合わせて v0.1.0 を初回リリースとしています（リリース日: 2026-04-23）。

## [Unreleased]


## [0.1.0] - 2026-04-23

### Added
- 基本アプリケーション初期実装を追加
  - パッケージメタ情報: `kabusys.__version__ = "0.1.0"`
- 実行エントリスクリプト
  - `src/kabusys/run_monitoring.py`
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止はプロジェクト内 `data/stop_requested.flag` によるフラグ検知で行う。
    - Monitoring は環境に関係なく本番用 `sqlite_path` を使用して初期化。
    - DuckDB と SQLite の接続確立およびクリーンなクローズ処理を実装。
  - `src/kabusys/run_execution.py`
    - ExecutionEngine 起動スクリプト。
    - `KABUSYS_ENV=paper_trading` の場合は専用の paper trading SQLite（`data/paper_trading.db` デフォルト）を使用し、MockBrokerClient を利用して本番 DB と完全分離。
    - スレッドでエンジン実行、停止フラグ検知により安全に停止。
    - 実行中 PID ファイル管理（`data/execution.pid` など）。
- 設定管理
  - `src/kabusys/config.py`
    - Settings クラスによる環境変数ラッパーを実装（Singleton: `settings`）。
    - .env の自動ロード機構（プロジェクトルート検出: `.git` または `pyproject.toml` を基準）。
    - 自動ロード無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
    - 必須環境変数取得 `_require()` と各種デフォルト値（例: `DUCKDB_PATH`, `SQLITE_PATH`）を提供。
    - Paper Trading 関連設定（`PAPER_FILL_MODE`, `PAPER_TRADING_SQLITE_PATH` 等）、監視閾値、PID/KILL フラグパス等を定義。
- 環境設定支援ツール
  - `src/kabusys/config_setup.py`
    - 対話式ウィザードで `.env` を初期作成/更新する CLI を実装。
    - 各項目の説明表示、秘密値のマスク表示、デフォルト・選択肢サポート。
    - `.env` の書き込みテンプレート（Git へコミットしない旨の注意含む）。
- 設定検証ツール
  - `src/kabusys/validate_config.py`
    - `.env` と `config/*.yaml` の存在・基本検証を行う CLI。
    - 必須環境変数チェック、`KABUSYS_ENV` / `LOG_LEVEL` の妥当性判定、DB パス親ディレクトリ存在チェックを実装。
    - PyYAML が無い場合は YAML 検証をスキップする警告を出す。
    - `--strict` オプションで警告を FAIL 扱いにできる。
- ロギング・プロセスユーティリティ
  - `src/kabusys/utils/logging_setup.py`
    - ルートロガーへ StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテート、30日保持）を設定する共通ユーティリティ。
    - ログレベル／ログディレクトリの解決順をドキュメント化。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - `src/kabusys/utils/process_priority.py`
    - Windows / POSIX を吸収するプロセス優先度設定（`set_process_priority`）と CPU affinity 固定（`set_cpu_affinity`）を提供。
    - アクセス権限不足等の失敗時には警告を出して安全にスキップ。
- Portfolio（銘柄選定〜発注量決定）モジュール
  - `src/kabusys/portfolio/portfolio_builder.py`
    - 候補選定 (`select_candidates`)、等配分 (`calc_equal_weights`)、スコア加重 (`calc_score_weights`) を実装。
    - スコアが全て 0 の場合は等配分へフォールバックし warning を出力。
  - `src/kabusys/portfolio/risk_adjustment.py`
    - セクター集中制限 (`apply_sector_cap`) とマーケットレジームに基づく投下資金乗数 (`calc_regime_multiplier`) を実装。
    - レジーム別の乗数マッピング（bull/neutral/bear）と未知レジーム時のフォールバックを定義。
  - `src/kabusys/portfolio/position_sizing.py`
    - 発注株数算出 (`calc_position_sizes`) の本実装。
    - `risk_based`, `equal`, `score` の配分方式をサポート。
    - lot_size に基づく丸め、最大ポジション上限、aggregate cap（利用可能現金に応じたスケーリング）、手数料/スリッページのバッファ考慮等を実装。
  - `src/kabusys/portfolio/__init__.py`
    - 上記関数をパッケージ API としてエクスポート。
- 研究用ファクター計算
  - `src/kabusys/research/factor_research.py`
    - DuckDB 経由でファクター（Momentum, Value, Volatility, Liquidity）を計算するための骨組み・定数とモメンタム計算機能の実装方針を追加。
    - DuckDB 接続を受けて prices_daily / raw_financials テーブルを参照する設計。
- ペーパートレード検証レポート
  - `src/kabusys/tools/paper_verification_report.py`
    - Paper Trading の検証レポートを生成する CLI。
    - DB（デフォルト: `data/paper_trading.db`）から稼働率、注文成功率、送信率、P95 レイテンシ等を集計し PASS/FAIL を判定。
    - コマンドライン引数 `--from`/`--to`/`--db` に対応。
- 監視 DB 初期化（参照）
  - 各起動スクリプトから `init_monitoring_db` を呼び出し、監視テーブルの存在を保証する（冪等）。
- その他ユーティリティ
  - .env パーサーはクォート、エスケープ、inline コメントの取り扱いをサポート（`config._parse_env_line`）。
  - 環境変数自動ロード優先度: OS 環境 > .env.local > .env（既存の OS 環境を保護する機構あり）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- `.env` を生成する際に「絶対に Git にコミットしないこと」を明記（`config_setup` の出力メッセージ）。

### Notes / Implementation details / Defaults
- デフォルトのポーリング間隔: 60 秒（`MONITOR_POLL_INTERVAL` で上書き可能）。不正値はデフォルトにフォールバックして警告を出す。
- `PAPER_FILL_MODE` の有効値: "instant" | "partial" | "never" | "reject"（不正値は ValueError）。
- ログはデフォルトで logs/ ディレクトリに日次ローテートで保存、30 日分保持。
- `process_priority.set_process_priority("high")` を起動直後に呼ぶ設計により、監視／実行プロセスを優先度高で動作させることを想定。
- Paper Trading と Live の DB は分離（`paper_sqlite_path` と `sqlite_path`）してあり、データ混在を防止。

---

今後の予定（例）
- factor_research のファクター実装（Value / Volatility / Liquidity の具体的 SQL/計算）。
- Strategy / Execution の詳細実装（現在は ExecutionEngine 等の参照があるが、内部ロジックの追加・テストが必要）。
- 単体テスト、CI ワークフロー、ドキュメント整備の強化。

--- 

（本 CHANGELOG はコードベースの内容から推測して作成しています。実際のリリースノートとして利用する際は、実際の変更差分・コミット履歴に基づいて精査・追記してください。）