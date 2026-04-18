# CHANGELOG

すべての注目すべき変更点はこのファイルに記載します。
フォーマットは "Keep a Changelog" に準拠しています。
重要: 日付はリポジトリ内のコード内容から推定して付与しています。

最新の変更
------------

### Unreleased
- 今後のリリースで改善予定:
  - research モジュール（factor_research.py）の完全実装の続行（現状一部が切れているため完成・テストを予定）。
  - 単体テストの拡充（特に position sizing / risk adjustment の数値的な境界ケース）。
  - ログ出力・ファイルハンドラ周りのエラー時のリカバリ改善（現在はファイル作成失敗時にコンソールのみで運用）。
  - 一部の TODO（例: 銘柄ごとの lot_size 拡張、価格フォールバック戦略）の実装。

リリース履歴
------------

### [0.1.0] - 2026-04-18 (初回リリース)
Added
- コア機能の実装（日本株自動売買システムの初版）。
  - パッケージメタ情報: `kabusys.__version__ = "0.1.0"`。
- 実行・監視用スクリプト:
  - `run_execution.py`
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV に応じて paper_trading 用 DB を分離（`PAPER_TRADING_SQLITE_PATH` / `settings.is_paper`）。
    - BrokerClientFactory によるブローカークライアント生成。
    - OrderRepository、OrderManager、RiskManager、Reconciler の組み立てと ExecutionEngine の起動（別スレッドで run_session を実行）。
    - 停止フラグ（data/stop_requested.flag）検知による安全停止、PID ファイル書き込みのサポート。
    - 起動時にプロセス優先度を High に設定。
  - `run_monitoring.py`
    - SystemMonitor のポーリングループを起動するスクリプト。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト: 60秒）。不正値はデフォルトにフォールバック。
    - 監視は環境にかかわらず本番用 `sqlite_path` を使用してデータを記録。
    - 停止フラグ（data/stop_requested.flag）検知でループ終了、KeyboardInterrupt に対応。
- 設定・環境管理:
  - `config.py`
    - Settings クラスにより環境変数をラップしてアクセス。
    - 自動 .env ロード機能: プロジェクトルート（.git / pyproject.toml 基準）から `.env` と `.env.local` をロード（OS環境変数は保護）。
    - `.env` パーサは export 形式、クォート文字列、インラインコメントの扱いに対応。
    - 多数の設定プロパティを提供（J-Quants / kabu API / LINE / DB パス / 監視閾値 / 環境判定など）。
    - `paper_fill_mode` の検証（有効値: instant/partial/never/reject）。
  - `config_setup.py`
    - .env 初期作成・更新の対話式ウィザード CLI。
    - デフォルト値やシークレット入力に対応し、最終的に `.env` をテンプレート形式で書き出す機能。
  - `validate_config.py`
    - 起動前の設定検証 CLI。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ確認、config/*.yaml の存在・パース検証（PyYAML がない場合はスキップ）を行う。
    - `--strict` オプションで警告も失敗扱いにできる。
- ポートフォリオ構築モジュール（純粋関数群、DB 参照なし）:
  - `portfolio/portfolio_builder.py`
    - シグナルの選抜 (`select_candidates`) と重み算出 (`calc_equal_weights`, `calc_score_weights`) を実装。
    - スコアが全て 0 の場合は等金額配分へフォールバックし警告。
  - `portfolio/risk_adjustment.py`
    - セクター集中上限適用 (`apply_sector_cap`) — 当日売却予定銘柄を除外する処理、unknown セクターは上限を適用しない。
    - 市場レジームに応じた投下資金乗数 (`calc_regime_multiplier`) — bull/neutral/bear をマップし未知レジームは 1.0 にフォールバック。
  - `portfolio/position_sizing.py`
    - ポジションサイズ決定ロジック (`calc_position_sizes`)。
    - allocation_method による振る舞い: "risk_based"（リスク許容率に基づく）、"equal"/"score"（ウェイトに基づく）。
    - 単元株（lot_size）丸め、1銘柄上限（max_position_pct）や aggregate cap（available_cash）でのスケールダウン、cost_buffer を用いた保守的見積り、残差に基づく追加配分ロジックを実装。
- ユーティリティ:
  - `utils/logging_setup.py`
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）を設定するユーティリティ。
    - LOG_LEVEL / LOG_DIR 解決順の仕様、既存ハンドラのクリア、ログディレクトリ作成失敗時のフォールバック（コンソールのみ）を実装。
  - `utils/process_priority.py`
    - プラットフォーム差を吸収したプロセス優先度設定 (`set_process_priority`)。
    - Windows と POSIX（Linux/Mac/FreeBSD）に対応し、権限不足などは警告でスキップ。
    - CPU affinity 固定用の `set_cpu_affinity` を提供。
- execution/monitoring 周りの初期 DB 保守:
  - `monitoring.monitoring_db.init_monitoring_db` 呼び出しにより、起動時に監視用テーブルの存在を保証（冪等に初期化）。
- Paper Trading 支援ツール:
  - `tools/paper_verification_report.py`
    - ペーパートレードの検証レポート生成 CLI。
    - システム稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、API レイテンシ（avg/max/P95）などをクエリし、閾値と比較して PASS/FAIL 判定を出力。
    - デフォルト DB: `data/paper_trading.db`。`--db` で別パス指定可能。
    - P95 計算ユーティリティと各種フォールバックを実装（テーブル/列が無い場合は N/A で表示）。
- research:
  - `research/factor_research.py`（骨格実装）
    - DuckDB を用いたファクター計算の方針とモメンタム計算の定義（モジュール途中まで実装、設計は明確化）。
- パッケージ初期化:
  - `kabusys/portfolio/__init__.py` に主要関数をエクスポート。

Changed
- N/A（初回リリースのため変更履歴はなし）

Fixed
- N/A（初回リリースのため修正履歴はなし）

Security
- 環境変数自動ロード時に OS 環境変数を保護する仕組みを導入（`.env` の上書き禁止キー集合を保持）。これにより CI/本番環境の既存変数を不用意に上書きしないようにしている。

Notes / 実装上の注記
- 設定の自動読み込みはプロジェクトルートが検出できた場合のみ行われるため、パッケージ配布後やテスト時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動ロードを無効化できる。
- run_monitoring は監視データを本番用 `SQLITE_PATH` に常に書き込む設計（環境に依存しない監視データ収集）。
- run_execution は paper_trading 環境であれば paper 用 SQLite を使用することで発注ロギングを本番と分離している。
- position sizing の aggregate cap スケーリングは lot_size（単元）単位で丸められるため、端数処理により期待どおりの配分にならないケースがある。テストと監視を推奨。
- research モジュールのファイルは途中で切れているため、実際に使用する前に完成実装とテストが必要。

参考: 主な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（必須）
- KABUSYS_ENV (development|paper_trading|live)
- DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH
- LOG_LEVEL, LOG_DIR
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔上書き）
- PAPER_FILL_MODE（paper_trading の fill 挙動）

--- 

この CHANGELOG はコードベースの実装内容から推測して作成しています。実際の変更履歴・リリース日付がある場合はそれに合わせて更新してください。