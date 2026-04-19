# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/

## [Unreleased]
- 開発中の変更を記載する場所です。

## [0.1.0] - 2026-04-19
初回リリース。KabuSys 自動売買フレームワークのコア機能群を実装しました。主な追加点は以下の通りです。

### Added
- 基本パッケージ構成
  - パッケージ名: `kabusys`、バージョン `0.1.0` を `src/kabusys/__init__.py` に追加。
  - エクスポート: data, strategy, execution, monitoring。

- 起動スクリプト / 実行管理
  - run_execution: `src/kabusys/run_execution.py`
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - 環境に応じて paper_trading 用の専用 SQLite（`data/paper_trading.db`）を使用する仕組みを実装。`BrokerClientFactory` により本番/モックのブローカークライアントを切替。
    - デフォルトでプロセス優先度を "high" に設定（`set_process_priority` を呼出し）。
    - 停止制御: プロジェクト直下 `data/stop_requested.flag` の存在検知で安全に停止。
    - 実行中の PID を `data/execution.pid` に記録。

  - run_monitoring: `src/kabusys/run_monitoring.py`
    - SystemMonitor のポーリングループ起動用スクリプト。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒、無効値はフォールバックしてログ警告）。
    - 監視は環境にかかわらず本番用の SQLite パス（`SQLITE_PATH`）を使用する設計。
    - 停止フラグ `data/stop_requested.flag` によるループ終了、KeyboardInterrupt のハンドリング。

- 設定・環境管理
  - Settings クラス: `src/kabusys/config.py`
    - 環境変数を読み出す集中管理クラスを追加。
    - 自動 .env ロード機能:
      - プロジェクトルートを `.git` または `pyproject.toml` を基準に検出（CWD に依存しない）。
      - 読み込み順序: OS 環境 > .env.local > .env。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
      - .env のパースはクォート、エスケープ、コメントに対応（`export KEY=val` 形式にも対応）。
    - 多数の設定プロパティを提供（DB パス、PID ファイル、閾値、環境判定メソッド等）。
    - Paper Trading 固有設定（`PAPER_FILL_MODE`, `PAPER_TRADING_SQLITE_PATH`）をサポート。

  - 設定ウィザード CLI: `src/kabusys/config_setup.py`
    - 対話式に .env を生成/更新するウィザードを実装。
    - シークレット項目はマスク表示、既存 .env の読み込みと Enter による再利用をサポート。
    - 出力は .env ファイルとして保存するテンプレートを含む。

  - 設定検証ツール: `src/kabusys/validate_config.py`
    - 起動前に .env と `config/*.yaml` の存在・基本妥当性を検証する CLI。
    - 必須環境変数チェック、KABUSYS_ENV 値チェック、ログレベル、DB パスの親ディレクトリ存在チェックを実装。
    - YAML パーサ（PyYAML）が未インストールの場合は該当検証をスキップして警告。
    - `--strict` オプションで警告も失敗扱いにできる。

- ロギング / 実行環境ユーティリティ
  - ログ設定ユーティリティ: `src/kabusys/utils/logging_setup.py`
    - StreamHandler（stdout） と TimedRotatingFileHandler（デフォルト logs/、日次ローテート、30世代保持）をルートロガーに設定。
    - 既存ハンドラをクリアして重複防止、ログレベル解決とログディレクトリの自動作成（失敗時はファイル出力をスキップして stdout のみ継続）。
    - stdout を用いることでタスクランナーからの出力リダイレクトに配慮。

  - プロセス優先度・CPU affinity ユーティリティ: `src/kabusys/utils/process_priority.py`
    - Windows / POSIX の差分を吸収してプロセス優先度をセットする `set_process_priority(level)` 実装。
    - CPU affinity を部分的に固定する `set_cpu_affinity(cpu_count)` を実装。
    - 権限不足や未サポート環境では警告を出して安全にフォールバック。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio_builder: `select_candidates`, `calc_equal_weights`, `calc_score_weights`
    - シグナル選定、等金額 / スコア加重の重み計算を実装。score 全部 0 の場合は等金額にフォールバックして警告。
  - risk_adjustment:
    - `apply_sector_cap`: セクター集中上限チェック（既存保有を考慮し、上限超過セクターの新規候補を除外）。"unknown" セクターは適用除外。
    - `calc_regime_multiplier`: 市場レジーム（bull/neutral/bear）に基づく投下資金乗数を実装。未知レジームは警告して 1.0 フォールバック。
  - position_sizing:
    - `calc_position_sizes`: 複数の割当方式（risk_based / equal / score）に対応した株数計算を実装。
    - 単元株（lot_size）単位で丸め、1 銘柄上限、aggregate cap（available_cash を超える場合のスケーリング）、手数料等を考慮する cost_buffer、残差を lot 単位で再配分するロジックを備える。
    - TODO コメント: 将来の拡張点（銘柄別 lot_size 等）を明示。

- 実行ロジック周辺コンポーネントの接続（コードに記載されている使用例）
  - ExecutionEngine, OrderManager, OrderRepository, Reconciler, RiskManager 等を組み立てる起動フローを実装（run_execution の中でデフォルトパラメータを設定）。
  - RiskConfig のデフォルトパラメータ（例: max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, max_drawdown=0.20 など）を用意している。

- 監視 / レポート
  - 監視 DB の初期化ヘルパ（`init_monitoring_db` を各起動スクリプトで呼出して監視用テーブルの存在を保証）。
  - Paper Trading 検証レポート: `src/kabusys/tools/paper_verification_report.py`
    - ペーパートレード用 SQLite から指標（稼働率 / 注文成功率 / 送信率 / レイテンシ（平均/最大/P95） / リスク却下数）を集計してレポート出力する CLI を実装。
    - P95 の計算実装、閾値による PASS/FAIL 判定を組み込み（閾値はソースで定義）。
    - コマンドライン引数で期間指定（--from / --to）および DB パス指定（--db）に対応。
    - DB が存在しない場合はエラーメッセージを出力。

- リサーチ / ファクター計算（初期実装）
  - `src/kabusys/research/factor_research.py` にてモメンタム等のファクター計算の骨組みを実装。
    - Momentum（1M/3M/6M）、200 日移動平均乖離、ATR、流動性等を計画。
    - DuckDB 接続を受け取り prices_daily / raw_financials テーブルから計算する設計方針。
    - 注: ファイル内に計算の骨子があり、モメンタム計算関数の実装が途中（calc_momentum の続き実装が必要）である旨の記載あり。

### Changed
- （初回リリースのため特になし）

### Fixed
- （初回リリースのため特になし）

### Notes / Implementation details
- .env パーサはシングル/ダブルクォート内のバックスラッシュエスケープやインラインコメントの扱いを考慮しており、従来の簡易パーサより堅牢化されています。
- ログはデフォルトで stdout に出力するようにしており、cron/スケジューラ等からの実行時にログの取り扱いが容易になる設計です。
- プロセス優先度・CPU affinity の設定は権限不足や未対応 OS で安全にスキップします（警告ログ）。
- Paper Trading と Live の DB を厳密に分離することで、シミュレーションと本番データの混在を防止します。

### Known issues / TODO
- research/factor_research.calc_momentum 等に未完の実装箇所があり、完全なファクター計算実装は今後の作業を要します。
- position_sizing 内で価格が欠損（0.0）だった場合のフォールバック（前日終値や取得原価など）の改善が TODO コメントとして残っています。
- 一部の外部依存（psutil, duckdb, PyYAML 等）が必要。環境によっては機能が限定される場合があります。

---

この CHANGELOG は、提供されたソースコードから推測できる機能・設計意図に基づいて作成しています。実際の変更履歴（コミットログ等）と差異がある可能性があります。必要であれば、個々のモジュールごとにより詳細な変更点（関数・引数レベル）を生成します。