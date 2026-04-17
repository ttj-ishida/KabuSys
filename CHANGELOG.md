# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
このリリースでは初期機能群を実装しました。

なおバージョンはパッケージメタ情報 (kabusys.__version__) に従い 0.1.0 としています。

## [Unreleased]

## [0.1.0] - 2026-04-17

Added
- 初期リリース。以下の主要コンポーネントと CLI/ユーティリティを追加。
  - 環境設定 / 読み込み
    - kabusys.config
      - .env 自動読み込み機能（プロジェクトルートを .git または pyproject.toml で検出）。
      - .env/.env.local の読み込み順と上書き保護（OS 環境変数保護）。
      - 複雑な行解析に対応した .env パーサ（export 形式、クォート、インラインコメント、エスケープ対応）。
      - Settings クラスを提供し、環境依存の設定（DB パス、API トークン、KABUSYS_ENV、ログレベル、監視閾値等）をプロパティ経由で取得。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
    - kabusys.config_setup
      - インタラクティブな .env 生成ウィザード（対話式入力、シークレットマスキング、保存）。
      - デフォルト値の提示と既存 .env の読み込み・再利用。
      - 保存時に .env テンプレートヘッダを付与（Git コミット禁止の注意喚起）。
  - 設定検証 CLI
    - kabusys.validate_config
      - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性確認、DB パスの親ディレクトリチェック、config/*.yaml の存在確認。
      - PyYAML 未導入時は YAML 検証をスキップして警告。
      - --strict オプションで警告を FAIL として扱うモードを提供。
      - CLI から実行してエラー/警告/情報を出力可能（exit code に反映）。
  - 実行系起動スクリプト
    - run_monitoring.py
      - SystemMonitor のポーリングループ起動スクリプト。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告出力。
      - 起動時にプロセス優先度を "high" に設定（utils の set_process_priority を使用）。
      - 監視用 DB は実行環境にかかわらず production の sqlite_path を使用する設計。
      - 停止判定はプロジェクト直下 data/stop_requested.flag による（ファイル存在検査）。
    - run_execution.py
      - ExecutionEngine 起動スクリプト。
      - KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）に完全分離して MockBrokerClient を使用する設計。
      - 起動時にプロセス優先度を "high" に設定。
      - Engine はスレッドで実行し、stop flag を検知したらエンジン側の stop() を呼んで安全終了を図る。
      - PID ファイルの書き出し先をサポート（デフォルト data/execution.pid）。
  - 監視 DB 初期化ヘルパー呼び出し（init_monitoring_db）を両スクリプトで起動前に実行して監視テーブルの存在を保証（冪等）。
  - ユーティリティ
    - kabusys.utils.process_priority
      - set_process_priority(level) — Windows / POSIX を吸収してプロセス優先度を設定（"high" / "normal" / "low"）。
      - set_cpu_affinity(cpu_count) — 指定コア数への CPU affinity 固定（非対応環境では警告を出してスキップ）。
      - アクセス権限不足や未実装環境への耐性を実装（警告でフォールバック）。
  - ポートフォリオ構築（純粋関数）
    - kabusys.portfolio.portfolio_builder
      - select_candidates — スコア降順で上位 N を選出（同点は signal_rank でタイブレーク）。
      - calc_equal_weights / calc_score_weights — 等配分・スコア加重（スコア全 0 の場合は等配分にフォールバックして警告）。
    - kabusys.portfolio.risk_adjustment
      - apply_sector_cap — 既存保有のセクター別エクスポージャに基づき新規候補を除外（"unknown" セクターは制限対象外）。sell_codes を除外してエクスポージャ計算可能。
      - calc_regime_multiplier — レジーム ("bull", "neutral", "bear") に基づく投下資金乗数（未知は 1.0 でフォールバックし警告）。
    - kabusys.portfolio.position_sizing
      - calc_position_sizes — allocation_method("risk_based" / "equal" / "score") に応じて発注株数を計算。
      - 単元株（lot_size）で丸め、per-stock cap と aggregate cap を適用。aggregate cap 超過時はスケーリングと端数扱いでの追加配分ロジックを備える。
      - cost_buffer（手数料・スリッページの保守的見積り）を考慮。
  - リサーチ / ファクター計算
    - kabusys.research.factor_research
      - DuckDB を用いた定量ファクター計算（prices_daily / raw_financials を参照）。
      - モメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（ATR20）、流動性指標等を計算する関数を実装。
      - データ不足時の None の取り扱いを定義。
  - ツール
    - kabusys.tools.paper_verification_report
      - Paper Trading の検証レポート生成 CLI。
      - データベース（PAPER_TRADING_SQLITE_PATH / --db）から期間フィルタをかけてシステム稼働率、注文成功率、送信率、レイテンシ (avg/max/P95) などを集計・判定。
      - 閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms 等）を用いた PASS/FAIL 判定を行う。
      - DB のテーブル欠如やデータ不足に対して耐性を持つ実装（OperationalError をキャッチして N/A 扱い）。
  - パッケージ情報
    - kabusys.__version__ を 0.1.0 に設定。

Changed
- （初リリースのため該当なし）

Fixed
- （初リリースのため該当なし）

Notes / Usage highlights
- 環境変数の主なキーとデフォルト値について
  - KABUSYS_ENV: "development" | "paper_trading" | "live"（デフォルト "development"）。無効値は ValueError を発生。
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用に DB を分離）
  - MONITOR_POLL_INTERVAL: 監視ポーリング秒数（run_monitoring 用、デフォルト 60）
  - PAPER_FILL_MODE: paper_trading 時の MockBroker の fill モード ("instant"|"partial"|"never"|"reject")。無効値は ValueError。
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill flag を自動クリアするか（本番では 0 推奨）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env 読み込みを無効化する（テスト等で使用）。
- run_execution / run_monitoring はそれぞれ data/stop_requested.flag を監視して安全終了する設計。
- Process priority / CPU affinity の設定は環境によっては権限不足で失敗する可能性があり、その場合は警告を出して続行します。

開発者向け備考
- .env やシークレットは絶対にリポジトリにコミットしないでください（config_setup のヘッダにも注記あり）。
- DuckDB / prices_daily テーブル等はファクター計算で期待されるスキーマを満たす必要があります（config/*.yaml 生成用スクリプト等で初期設定を行ってください）。
- 将来的な拡張メモ（コード内注釈）
  - position_sizing の lot_size を銘柄別に対応する案（stocks マスタ拡張）。
  - apply_sector_cap の価格欠損時フォールバック（前日終値や取得原価の使用）。

ライセンス
- 本リリースに含まれるコードはプロジェクト内のライセンスに従います（リポジトリの LICENSE を参照してください）。