# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

通常、変更は以下のカテゴリに分類します:
- Added: 新規機能
- Changed: 変更
- Fixed: バグ修正
- Deprecated: 非推奨
- Removed: 削除
- Security: セキュリティ対応

## [Unreleased]

## [0.1.0] - 2026-04-23
初回公開リリース。

### Added
- 基本アプリケーション情報
  - パッケージバージョンを `__version__ = "0.1.0"` として追加。

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は専用の Paper Trading 用 SQLite（デフォルト: `data/paper_trading.db`）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine をスレッドで実行。
    - 停止フラグ（data/stop_requested.flag）検知により安全に停止。
    - 起動時にプロセス優先度を "high" に設定（process_priority ユーティリティを使用）。

  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプトを追加。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト: 60 秒、無効値は警告してデフォルトにフォールバック）。
    - Monitoring は KABUSYS_ENV に関わらず本番の `sqlite_path` を使用する仕様。
    - 停止フラグ（data/stop_requested.flag）検知によりループを終了。
    - 起動時にプロセス優先度を "high" に設定。

- 設定管理と初期化
  - config.py
    - .env 自動読み込み機能を実装（プロジェクトルートの `.env` / `.env.local` を OS 環境変数を保護して読み込む）。
    - .env パースロジックを強化（export 形式、クォート内のエスケープ、インラインコメントの扱い等）。
    - Settings クラスを提供し、環境変数の型変換、バリデーション、便利なプロパティを実装（例: `duckdb_path`, `sqlite_path`, `paper_sqlite_path`, `paper_fill_mode`, `env`, `is_live`, `is_paper` 等）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化サポート。

  - config_setup.py
    - .env の対話式ウィザードを追加。初期作成・更新を支援。
    - Secret フィールドのマスク表示、デフォルト・選択肢サポート、保存前の確認等を実装。

  - validate_config.py
    - 起動前の設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリチェック、config/*.yaml の存在とパース（PyYAML 利用）検査、本番環境向けの追加ガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の注意喚起）を実装。
    - `--strict` オプションで警告も失敗扱いにできる。

- ロギング・ユーティリティ
  - utils/logging_setup.py
    - 統一的なログ設定ユーティリティを追加。
    - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）でログファイルを出力（デフォルト `logs/`、30日保持）。
    - LOG_LEVEL / LOG_DIR の解決順を実装。既存ハンドラの安全な再設定を実施。
    - ログディレクトリ作成失敗時にはコンソール出力のみで継続する耐障害性を実装。

- プロセス優先度ユーティリティ
  - utils/process_priority.py
    - Windows / POSIX（Linux/macOS/FreeBSD）差分を吸収するプロセス優先度設定を追加。
    - `set_process_priority(level)` により "high"/"normal"/"low" をサポート。アクセス権限や未対応 OS は警告してスキップ。
    - `set_cpu_affinity(cpu_count)` による CPU affinity 設定サポート（例外時は警告でスキップ）。

- Portfolio（銘柄選定・配分・株数決定）
  - portfolio/portfolio_builder.py
    - 候補選定（スコア降順・タイブレーク）、等金額配分、スコア加重配分（スコア全て 0 の場合は等分配へフォールバック）を実装。
  - portfolio/risk_adjustment.py
    - セクター集中上限適用（既存保有のセクター暴露を考慮して新規候補を除外）を実装。unknown セクターは上限適用対象外。
    - レジームに応じた投下資金乗数（bull/neutral/bear）を実装。未知のレジームは警告して 1.0 フォールバック。
  - portfolio/position_sizing.py
    - allocation_method ("risk_based" / "equal" / "score") に基づく株数算出ロジックを実装。
    - 損切り率・リスク許容率・単元株丸め（lot_size）・max_position_pct・max_utilization・cost_buffer を考慮。
    - aggregate cap 超過時のスケールダウンと残余配分ロジックを実装（lot 単位での再配分、端数処理）。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite のログを集計して検証レポートを出力する CLI を追加。
    - システム稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等を算出。
    - デフォルト閾値（稼働率 99%、成功率 90%、送信率 95%、P95 レイテンシ 200 ms）を用いた PASS/FAIL 判定を出力。
    - 日付範囲フィルタ（--from / --to）および `PAPER_TRADING_SQLITE_PATH` / `--db` による DB 指定をサポート。

- 研究 / ファクター計算
  - research/factor_research.py
    - ファクター計算モジュールの骨子を追加（Momentum/Value/Volatility/Liquidity 計算を想定）。
    - Momentum 計算用の定数や calc_momentum の開始実装（prices_daily を想定した設計、DuckDB 接続を受け取る）を含む（部分実装）。

### Changed
- N/A（初回リリースのため該当なし）

### Fixed
- N/A（初回リリースのため該当なし）

### Notes / Implementation details
- DB:
  - DuckDB は分析用（`duckdb_path`）、SQLite は監視・トレードログ用（`sqlite_path` またはペーパートレード専用 `paper_sqlite_path`）として利用する設計。
- 環境変数・挙動上の注意:
  - Monitoring は環境（KABUSYS_ENV）に関わらず常に `sqlite_path` を使用する点に注意。
  - `KILL_FLAG_CLEAR_ON_START` や `KABUSYS_ENV=live` の場合の注意喚起は validate_config で行う。
  - `.env` ファイルは絶対に Git にコミットしない旨を config_setup に明記。
- ロギング:
  - コンソール出力は stdout を使用（cron 等で stdout/stderr を一本化する運用を考慮）。
- 互換性:
  - process_priority は OS 標準の権限に依存するため、実行環境により設定が無効化される可能性あり（警告でフォールバック）。

---

今後の予定（例）
- research/factor_research の完全実装（Value, Volatility, Liquidity の算出と正規化）。
- ExecutionEngine・Monitoring 周りのユニットテスト追加。
- Paper Trading の MockBroker 実装詳細・シミュレーション精度向上。
- config/*.yaml の生成スクリプトとデフォルトテンプレートの整備。

----
（この CHANGELOG はコードベースの現在の内容から推測して生成しています。細かい実装差分は該当ソースを参照してください。）