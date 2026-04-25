# Changelog

すべての重要な変更点をこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。

全般:
- バージョニングは SemVer に従います。  
- 日付はリリース日を示します。

## [0.1.0] - 2026-04-25

初回リリース。本リリースでは自動売買システム KabuSys のコアユーティリティ、実行/監視ランナー、設定管理、ポートフォリオ構築用関数群、検証/レポート用ツール、研究用ファクターモジュールなどを追加しました。

### 追加 (Added)
- パッケージ初期化
  - パッケージバージョンを `__version__ = "0.1.0"` として導入。

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用の SQLite DB に完全分離して記録する（デフォルト: data/paper_trading.db）。
    - 起動時にプロセス優先度を "high" に設定。
    - stop フラグ（data/stop_requested.flag）がある場合は起動を中止・停止。
    - 実行中の PID 管理用ファイル (data/execution.pid) に対応。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバック。
    - 監視用途の DB 初期化を行う（monitoring テーブルの作成など）。
    - Monitoring は KABUSYS_ENV に関係なく本番用 sqlite_path を使用する点に注意。

- 設定/環境管理
  - config.py
    - 環境変数/設定の取得ラッパー `Settings` を実装。
    - 自動 .env 読み込み:
      - プロジェクトルートを .git または pyproject.toml から探索し、見つかった場合 `.env` → `.env.local` の順で読み込み（既存の OS 環境変数は保護）。
      - 自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。
    - .env 行のパースロジックを強化（export 形式、クォート文字列、インラインコメント、エスケープシーケンス対応）。
    - 各種設定プロパティを提供（例: `duckdb_path`, `sqlite_path`, `paper_sqlite_path`, `paper_fill_mode`, `pid_file_path`, リソース閾値など）。
    - `paper_fill_mode` のバリデーション（"instant"|"partial"|"never"|"reject"）。
    - `env` のバリデーション（development/paper_trading/live）。
  - config_setup.py
    - `.env` を対話式に生成・更新するウィザードを追加。
    - デフォルト値や選択肢を提示し、シークレット項目はマスクして入力。
    - 生成した .env 内容をファイルに書き込むユーティリティ `_write_env` を提供。
  - validate_config.py
    - 起動前に設定不備を検出する CLI（必須環境変数未設定、KABUSYS_ENV の不正、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パースなど）。
    - `--strict` オプションで警告も失敗扱いにできる。
    - PyYAML 未インストール時は警告を出して YAML 内容検証をスキップ。

- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py
    - `setup_logging(app_name, log_dir, level)` を提供。
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次・30 日保持）を設定。既存ハンドラはクリア。
    - ログレベル・ログディレクトリの解決順を定義（引数 > 環境変数 > デフォルト）。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py
    - プラットフォーム差を吸収したプロセス優先度設定 `set_process_priority(level)` を実装（Windows と POSIX(nice) 対応）。
    - CPU affinity 固定用 `set_cpu_affinity(cpu_count)` を提供。
    - パーミッションや未対応環境では警告を出してスキップ。

- ポートフォリオ構築（純関数群）
  - portfolio/portfolio_builder.py
    - `select_candidates`：BUY シグナルをスコア降順でソートして上位 N を返す。
    - `calc_equal_weights`：等金額配分（1/N）。
    - `calc_score_weights`：スコア加重配分（全スコアが 0 の場合は等配分にフォールバック）。
  - portfolio/risk_adjustment.py
    - `apply_sector_cap`：既存保有のセクター露出が閾値を超える場合に同セクターの新規候補を除外。
    - `calc_regime_multiplier`：市場レジームに応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3、未知は警告の上 1.0 フォールバック）。
  - portfolio/position_sizing.py
    - `calc_position_sizes`：複数の配分方式（risk_based / equal / score）に基づき発注株数を決定。
    - 単元株（lot_size）で丸め、1 銘柄上限・aggregate cap（available_cash）を考慮してスケールダウンするロジックを実装。
    - コストバッファ（cost_buffer）を考慮した保守的見積りと、端数処理で優先度に基づく追加配分の実装。

- Paper Trading / 検証ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite（デフォルト data/paper_trading.db）から注文・監視ログを集計して検証レポートを生成。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシなど。
    - P95 計算、期間フィルタ、しきい値（稼働率 99%、Fill 90%、Send 95%、P95 latency 200ms）に基づく PASS/FAIL 判定を出力。

- 研究用ファクター計算（骨組み）
  - research/factor_research.py
    - Momentum, Value, Volatility, Liquidity といったファクター群の計算設計を追加。
    - DuckDB 接続を受け取り prices_daily / raw_financials を参照して計算する方針。
    - 例: `calc_momentum` の骨組み（1M/3M/6M リターン、MA200 乖離率）を実装開始（営業日ベースのウィンドウを想定）。※ファイル末尾が切れているため追加実装の余地あり。

- パッケージエクスポート
  - portfolio モジュールの公開 API を __all__ 経由で定義。

### 変更 (Changed)
- .env 自動読み込みの挙動
  - 起動時に `.env` / `.env.local` を自動で読み込むように（ただし OS 環境変数を優先・保護）。テストや特殊環境では `KABUSYS_DISABLE_AUTO_ENV_LOAD` により無効化可能。

- Logging
  - コンソール出力は stderr ではなく stdout を使用（cron/Task Scheduler でのリダイレクト運用を考慮）。

### 修正 (Fixed)
- env ファイルパーサーの堅牢化
  - export 句、クォート中のエスケープ、インラインコメント処理などをサポートして .env の誤読を減らす。

### 注意事項 / 破壊的変更 (Important / Breaking changes)
- 監視プロセス（run_monitoring）は「環境にかかわらず」本番用 sqlite_path を使用する仕様です（監視データは本番 DB に記録されます）。開発/ペーパートレード環境で監視用 DB を分離したい場合は sqlite_path の値を環境変数で変更してください。
- run_execution は paper_trading の場合、paper 用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用し、本番 DB と完全分離します。ペーパートレード用 DB を指定しないとデフォルト data/paper_trading.db を使用します。
- `paper_fill_mode` に不正な値を設定すると起動時にエラーを投げます（有効値: instant / partial / never / reject）。
- 自動 .env 読み込みは既存の OS 環境変数を上書きしない挙動です。`.env.local` は上書きが可能（ただし OS 環境変数は保護）。

### 未実装 / TODO
- research/factor_research.py の細部（完全なファクター計算）の実装続行が必要（ファイル末尾が不完全）。
- position_sizing の lot_size を銘柄別に拡張するためのマスタ参照機能などの拡張を検討。
- セクターエクスポージャー算出時の価格フォールバック（当日価格欠損時に前日終値などを使用する）について注釈あり。将来的に改善が必要。

---

今後のリリースでは、strategy 実装、ExecutionEngine と各コンポーネントの詳細ロジックの安定化、研究モジュールの完全実装、運用監視機能（アラート/LINE 通知等）の拡充を予定しています。