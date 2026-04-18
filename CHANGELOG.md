# Changelog

すべての重要な変更をここに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

なお本 CHANGELOG は提供されたコードベースの内容から推測して作成しています（実際のコミット履歴とは異なる場合があります）。

## [0.1.0] - 2026-04-18

### Added
- 初期リリース: KabuSys 自動売買フレームワークの基本コンポーネントを追加。
- 環境設定 / 設定管理
  - .env 自動読み込み機能を実装（プロジェクトルートの検出: .git または pyproject.toml）。
  - 独自の .env パーサを実装し、`export KEY=val`、クォート内のエスケープ、行内コメントなどに対応。
  - Settings クラスを追加し、環境変数をプロパティ経由で取得（J-Quants / kabuステーション / DB パス / 監視閾値 / 稼働環境など多数の設定を提供）。
  - 環境自動読み込みを無効化するための `KABUSYS_DISABLE_AUTO_ENV_LOAD` フラグをサポート。
  - `PAPER_FILL_MODE`（paper_trading 用の擬似約定モード）をサポート（有効値: "instant", "partial", "never", "reject"）。
  - `PAPER_TRADING_SQLITE_PATH` によるペーパートレード用 DB パス上書きに対応。

- 設定操作用 CLI
  - `config_setup.py`: 対話式ウィザードで .env を初期作成 / 更新する機能を追加。
    - 必須項目（J-Quants トークン、kabu API パスワード等）や任意項目をガイド表示。
    - シークレット項目はマスク表示。保存前確認あり。
  - `validate_config.py`: 起動前に環境変数や config/*.yaml の妥当性を検証する CLI を追加。
    - `--strict` オプションで警告を FAIL 扱いにできる。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パス存在確認（親ディレクトリの存在チェック）、YAML のパース（PyYAML が存在する場合）などを実施。
    - live 環境向けの追加ガード（LINE 通知設定や Kill Switch 設定の警告）を実装。

- 実行 / 監視用エントリポイント
  - `run_execution.py`
    - プロセス優先度を起動時に "high" に設定。
    - KABUSYS_ENV が `paper_trading` の場合は専用（分離された）SQLite（デフォルト: data/paper_trading.db）を使用。
    - BrokerClientFactory によるブローカークライアント生成（モック / 実ブローカーの切替を想定）。
    - ExecutionEngine を用意し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて実行。
    - PID ファイル、停止フラグ（data/execution.pid / data/stop_requested.flag）を扱う制御を実装。停止フラグ検知時に安全に停止。
    - RiskManager のデフォルト構成（最大ポジション比率、利用率、レートリミット、サーキットブレーカー、初期ポートフォリオ値取得など）を設定に含める。
  - `run_monitoring.py`
    - SystemMonitor を初期化してポーリングループを実行（デフォルト間隔 60 秒）。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（不正値はデフォルトにフォールバックし警告を出力）。
    - 監視は環境にかかわらず本番用 `sqlite_path` を使用する（監視テーブル初期化を保証）。
    - 停止フラグ（data/stop_requested.flag）と KeyboardInterrupt による終了をハンドリング。
    - DuckDB 接続を並行して利用（解析用）。

- モニタリング / DB 初期化
  - `monitoring_db.init_monitoring_db` を呼び出し、監視用テーブルの存在を冪等的に保証。

- ロギング / プロセス制御ユーティリティ
  - `utils/logging_setup.py`
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次、30日保持）を設定する共通ユーティリティを追加。
    - `LOG_DIR` / `LOG_LEVEL` / 引数での上書き対応。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - `utils/process_priority.py`
    - Windows / POSIX の差を吸収してプロセス優先度（high/normal/low）を設定する `set_process_priority` を実装。
    - CPU affinity を最初の N コアに固定する `set_cpu_affinity` を提供（アクセス権限や未対応 OS の場合は警告を出してスキップ）。

- ポートフォリオ構築ロジック（純粋関数群）
  - `portfolio/portfolio_builder.py`
    - シグナル選定 (`select_candidates`)、等金額配分 (`calc_equal_weights`)、スコア加重配分 (`calc_score_weights`) を実装。
    - スコア全てが 0 の場合は等金額にフォールバックして警告を出力。
  - `portfolio/risk_adjustment.py`
    - セクター集中上限チェック (`apply_sector_cap`)：既存保有のセクター比率が閾値を超える場合に当該セクターの新規候補を除外。
    - 市場レジームに応じた投下資金乗数 (`calc_regime_multiplier`) を実装（"bull":1.0, "neutral":0.7, "bear":0.3、未知レジームは 1.0 にフォールバック）。
  - `portfolio/position_sizing.py`
    - 各銘柄の発注株数算出 (`calc_position_sizes`) を実装（allocation_method: "risk_based" / "equal" / "score" をサポート）。
    - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap（available_cash 超過時のスケーリング）、cost_buffer（手数料・スリッページ見積り）対応。
    - 価格欠損や単価不正時のスキップやログ出力を実装。

- 解析 / 研究モジュール（スケルトン）
  - `research/factor_research.py`
    - モメンタム、ボラティリティ、リクイディティ、バリュー等のファクター計算を想定したユーティリティ群の実装。DuckDB を用いた prices_daily / raw_financials 参照設計。
    - モメンタム計算関数（calc_momentum）等を含む設計を開始（ファイル途中までの実装が存在）。

- ペーパートレード検証ツール
  - `tools/paper_verification_report.py`
    - ペーパートレード用 SQLite データから検証レポートを生成する CLI を追加。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等を算出。
    - デフォルト閾値を定義し、PASS/FAIL を判定（稼働率 >= 99%, fill >= 90%, send >= 95%, P95 <= 200ms）。
    - 日付範囲オプション `--from` / `--to`、DB パス `--db`（環境変数 PAPER_TRADING_SQLITE_PATH 経由でも指定可）をサポート。
    - P95 計算、各種 NULL / テーブル未存在時のフォールバック処理を実装。

- パッケージ情報
  - `__init__.py` にパッケージバージョン `__version__ = "0.1.0"` を設定。

### Changed
- なし（初期リリース）

### Fixed
- なし（初期リリース）

### Removed
- なし（初期リリース）

### 注意事項 / 互換性
- 監視 (run_monitoring) は KABUSYS_ENV にかかわらず Settings.sqlite_path（本番用監視 DB）を使用します。実行 (run_execution) は paper_trading 環境時に専用の paper_sqlite_path を使用して本番 DB と分離します。
- .env 読み込みはデフォルトで自動実行されますが、テスト等で無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- `KILL_FLAG_CLEAR_ON_START` が本番環境で `1` に設定されていると Kill Switch が自動クリアされるため危険です（validate_config で警告）。
- process priority / CPU affinity の設定は実行環境の権限や OS に依存し、権限不足や未対応プラットフォームでは警告を出して処理をスキップします。

---

（今後のリリースでは各機能に対するユニットテスト、さらに詳細な監視ログ、Strategy / Execution の実装強化、外部サービス連携の拡充などの追記が想定されます。）