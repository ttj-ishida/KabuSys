# CHANGELOG

すべての notable な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠し、Semantic Versioning を想定します。

- 既往のバージョン: なし
- 現在バージョン: 0.1.0

## [Unreleased]
（変更なし）

## [0.1.0] - 2026-04-17

初回公開リリース。

### Added
- 基本パッケージ情報
  - パッケージバージョンを src/kabusys/__init__.py にて 0.1.0 として追加。

- 実行エントリ / デーモン類
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔をオーバーライド可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出力。
    - 停止制御はプロジェクトルート/data/stop_requested.flag によるフラグ検知で行う。
    - 監視は環境変数 KABUSYS_ENV に関わらず本番 sqlite_path を使用する（monitoring 用 DB の初期化も実行）。
    - 起動時にプロセス優先度を "high" に設定する（utils.process_priority.set_process_priority を利用）。

  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は専用の paper_trading SQLite DB（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）を利用して実行を制御。
    - BrokerClientFactory を使用したブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立てと ExecutionEngine の起動処理を実装。

- 設定管理 / ユーティリティ
  - config.py
    - .env 自動ロード機能を実装（プロジェクトルートは .git または pyproject.toml を探索して判定）。
    - .env と .env.local の読み込み順序: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - 各種設定プロパティを提供（J-Quants, kabu API, LINE, DuckDB/SQLite パス, Paper Trading モード等）。
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）。
    - env/log_level のバリデーションと is_live/is_paper/is_dev ヘルパー。
    - pid_file_path / kill_flag_path 等の監視関連パス設定。

  - config_setup.py
    - 対話式 .env 作成ウィザードを追加。
    - デフォルト値・選択肢・シークレット入力に対応。既存 .env の読み込み・再利用をサポート。
    - 最終的に .env を安全に書き出す処理を提供。

  - validate_config.py
    - 起動前に .env と config/*.yaml の不備を検出する CLI を追加。
    - 必須/任意環境変数のチェック、KABUSYS_ENV / LOG_LEVEL の妥当性検証、DB パスの親ディレクトリ存在チェック、YAML のパース（PyYAML があれば実行）などを実施。
    - --strict フラグで警告も失敗扱いにできる。

  - utils/process_priority.py
    - プロセス優先度設定ユーティリティを追加。
    - Windows と POSIX（Linux/Mac/BSD）を吸収する実装。アクセス権限がない場合は警告を出してスキップ。
    - set_cpu_affinity によりプロセスを最初の N コアに固定可能（未サポート環境や権限不足時は警告）。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順にソートして上位 N を選択。
    - calc_equal_weights: 等金額配分（1/N）。
    - calc_score_weights: スコア正規化配分（全スコアが0の場合は等配分にフォールバックし警告）。

  - portfolio/risk_adjustment.py
    - apply_sector_cap: 既存保有のセクター比率が閾値を超える場合、新規候補を排除するロジック。sell_codes を渡して当日売却予定銘柄を除外可能。unknown セクターは cap を適用しない。
    - calc_regime_multiplier: market レジームに応じた投下資金乗数を提供（bull=1.0, neutral=0.7, bear=0.3）。未知レジームは 1.0 でフォールバックし警告。

  - portfolio/position_sizing.py
    - calc_position_sizes: weight / candidates / available_cash 等から発注株数を算出する主要ロジックを実装。
      - allocation_method: "risk_based"（リスクベース）、"equal"、"score" をサポート。
      - lot_size（単元株）丸め、max_position_pct、max_utilization、cost_buffer（手数料/スリッページ見積）対応。
      - aggregate cap（合計コストが available_cash を超える場合のスケールダウン）と残余キャッシュを利用した lot 単位での追加割当ロジックを実装。
      - 価格欠損・0 の場合は銘柄をスキップし、デバッグログで通知。

- 研究（ファクター計算）
  - research/factor_research.py
    - DuckDB 接続を受け取り、prices_daily / raw_financials を参照してモメンタム・ボラティリティ等のファクターを計算する関数群を追加。
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev を計算（ウィンドウ不足時は None）。
    - calc_volatility: ATR/avg turnover/volume ratio 等（部分的に採掘中）。（注: ファイルは続きあり。DuckDB SQL を利用する設計）

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成スクリプトを追加。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ 等を算出して PASS/FAIL 判定を出力。
    - デフォルト閾値:
      - 稼働率 >= 99.0%
      - 注文成功率 >= 90.0%
      - 送信率 >= 95.0%
      - P95 レイテンシ <= 200 ms
    - --from / --to / --db オプションをサポート。PAPER_TRADING_SQLITE_PATH 環境変数を尊重。

- DB / 分析
  - DuckDB を分析用に利用する設計を全体で導入（Settings.duckdb_path, duckdb.connect を利用）。

### Changed
- なし（初回リリースのため変更履歴なし）

### Fixed
- なし（初回リリース）

### Deprecated
- なし

### Removed
- なし

### Security
- なし

---

注意 / 備考:
- .env は機密情報を含むため、README 等で Git にコミットしないことを明示しています（config_setup.py にも同旨のコメントあり）。
- run_monitoring は監視 DB に対して本番 sqlite_path を使用するため、監視専用 DB を分離したい場合は運用上の設定（SQLITE_PATH 環境変数）を変更してください。
- process_priority / cpu_affinity の設定は環境依存（OS・権限）で動作しない場合があります。その場合は警告ログが出力され、処理は継続します。
- Paper Trading と本番 DB の分離は意図的な設計です（run_execution は settings.is_paper に応じて別 DB を使用）。

この CHANGELOG はコードベースからの推測に基づいて作成しています。実際のリリースノートとして使用する際は、用途に応じて文言や対象箇所の詳細を調整してください。