# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に準拠して記載しています。

注意: ここに記載した項目は提供されたコードベースから推測してまとめた初回リリース向けの変更履歴です。

## [0.1.0] - 2026-04-17

### Added
- 全体
  - 初期リリース。日本株自動売買システム「KabuSys」のコアモジュール群を追加。
  - パッケージバージョンを `__version__ = "0.1.0"` として設定。

- 設定・環境関連
  - Settings クラス（kabusys.config）を追加。環境変数をラップしてアクセスするユーティリティを提供。
    - 自動的にプロジェクトルートの `.env` / `.env.local` を読み込み（ただし `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。
    - 各種設定プロパティを用意（J-Quants、kabuステーション、LINE、DuckDB/SQLite パス、監視閾値、環境判定など）。
    - `paper_fill_mode`（"instant"|"partial"|"never"|"reject"）などの検証を行う。
  - 設定ウィザード CLI（kabusys.config_setup）を追加。
    - 対話式で `.env` を作成/更新するユーティリティ。既存値の再利用やシークレットのマスク表示に対応。
  - 設定検証 CLI（kabusys.validate_config）を追加。
    - 必須環境変数の存在チェック、KABUSYS_ENV 値の妥当性、DB パスや config/*.yaml の存在/パース検証、production 向けガードなどを実行。
    - `--strict` オプションで警告も失敗扱いにできる。

- 実行エンジン関連
  - ExecutionEngine 起動スクリプト（kabusys.run_execution）を追加。
    - 起動時にプロセス優先度を高く設定（utils.process_priority）。
    - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用し、Paper Trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を利用して本番 DB と分離。
    - ブローカークライアントの生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て、ExecutionEngine の起動・停止制御（stop flag / PIDファイル管理、デーモンスレッド）を行う。
    - RiskManager の初期設定値（例: max_position_pct=0.20, max_utilization=0.80 等）をサンプルで設定。

- 監視関連
  - SystemMonitor 起動スクリプト（kabusys.run_monitoring）を追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒、1 秒以上で検証）。
    - 監視は起動環境にかかわらず本番の sqlite_path を使用して監視データを記録。
    - 停止フラグ（data/stop_requested.flag）による安全停止に対応。
    - 起動時にプロセス優先度を高く設定し、SQLite / DuckDB の接続初期化を行う。

- ポートフォリオ構築（純関数群）
  - portfolio モジュールを追加（kabusys.portfolio）。
    - portfolio_builder:
      - select_candidates: BUY シグナルをスコア降順・タイブレークでソートして上位 N を選定。
      - calc_equal_weights: 等金額配分を計算。
      - calc_score_weights: スコア加重配分を計算（全スコアが 0 の場合は等分配にフォールバック）。
    - risk_adjustment:
      - apply_sector_cap: セクター集中上限(max_sector_pct) に基づき候補をフィルタリング（"unknown" セクターは除外対象外）。
      - calc_regime_multiplier: 市場レジーム（"bull"/"neutral"/"bear"）に応じた投下資金乗数を提供（デフォルトフォールバックあり）。
    - position_sizing:
      - calc_position_sizes: 等配分／スコア配分／リスクベース配分（risk_based）に対応した株数算出。
      - 単元株（lot_size）丸め、per-stock 上限・aggregate 上限、コストバッファを考慮したスケーリング処理を実装。
      - リスクベース配分では stop_loss_pct と risk_pct に基づくサイズ決定を行う。
  - ポートフォリオモジュールは DB 参照なしの純関数として設計されており、ユニットテストが容易。

- 研究・ファクター計算
  - research/factor_research を追加。
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率（MA200）を DuckDB の prices_daily テーブルを用いて計算。
    - calc_volatility: ATR20、相対 ATR、20日平均売買代金、出来高比などのボラティリティ/流動性指標を計算（prices_daily ベース）。
    - 設計方針により DuckDB 接続を受け取り SQL と Python で効率的に集計。出力は (date, code) 単位の dict リスト。

- ユーティリティ
  - utils/process_priority を追加。
    - Windows と POSIX（Linux/macOS 等）を吸収するプロセス優先度設定（high/normal/low）。
    - CPU affinity 設定関数 set_cpu_affinity（最初の N コアに固定）を提供。
    - 権限不足や未対応プラットフォームでは警告を出して安全にフォールバック。

- ツール
  - tools/paper_verification_report を追加。
    - Paper Trading の検証レポート生成スクリプト（コマンドライン実行可能）。
    - 指標:
      - 稼働率（uptime）閾値 99.0%
      - 注文成功率（fill_rate）閾値 90.0%
      - 送信率（send_rate）閾値 95.0%
      - P95 レイテンシ閾値 200 ms
    - DB（PAPER_TRADING_SQLITE_PATH / --db）から system_status / trade_logs / risk_logs を参照して指標を集計・判定（PASS/FAIL）を出力。
    - P95 はサンプルから算出する実装を含む。データ不足に対しては N/A を返す。

- その他
  - monitoring_db の初期化呼び出し参照（init_monitoring_db）を各起動スクリプトで行い、監視テーブルの存在を保証（冪等）。
  - ストップフラグ・PID ファイル等の運用用ファイルパスを統一的に扱う設計。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Notes / Migration
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD は必ず設定する必要があります。validate_config で事前検証を推奨します。
- 環境判定:
  - KABUSYS_ENV は "development" / "paper_trading" / "live" のいずれかを指定してください。`live` 設定時は追加の警告チェックがあります。
- Paper Trading:
  - paper_trading 環境では本番の SQLite を上書きせず、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用するため本番データと完全に分離されます。
- MONITOR_POLL_INTERVAL:
  - run_monitoring にて MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能。ただし 1 秒未満や不正値は 60 秒（デフォルト）にフォールバックします。

もしリリースノートをさらに細かく（ファイル別の変更点や既知の制限・TODO）に分けたい場合は、その旨を教えてください。各関数の引数や既知の挙動（例: price が欠損のときの影響など）をより詳細に追記できます。