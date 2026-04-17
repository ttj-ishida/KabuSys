# Keep a Changelog

すべての重要な変更点をこのファイルに記録します。フォーマットは Keep a Changelog に準拠します。

なお本 CHANGELOG は配布されているソースコードの内容から推測して作成しています。

## [Unreleased]

（現在のソースツリーに対する未リリースの変更はありません。）

## [0.1.0] - 2026-04-17

初回リリース。以下の主要機能・モジュールを実装しています。

### Added
- 基本情報
  - パッケージのバージョンを `__version__ = "0.1.0"` として導入。

- 設定管理
  - Settings クラスによる環境変数ベースの設定管理を実装（kabusys.config）。
  - .env 自動ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - .env の読み込みロジックは export 形式・クォート・コメント等に対応。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - 必須設定の要求ヘルパー（_require）と各種設定プロパティ（DBパス、APIキー、監視閾値、環境判定など）を追加。
  - PAPER_FILL_MODE の有効値チェック（instant/partial/never/reject）。
  - paper_trading 用の別 SQLite パス（PAPER_TRADING_SQLITE_PATH）。

- 環境設定支援ツール
  - 対話式ウィザード `kabusys.config_setup` を実装。`.env` の初期作成・更新を支援し、シークレット値はマスク表示。
  - `.env` ファイルの読み書きロジックを実装。既存値の再利用やオプション項目の扱いをサポート。

- 設定検証 CLI
  - `kabusys.validate_config` による起動前検証ツールを実装。
  - 必須環境変数のチェック、KABUSYS_ENV/LOG_LEVEL 値検証、DBパスの親ディレクトリ存在チェック、config/*.yaml の存在および YAML パース検証（PyYAML がある場合）を実装。
  - `--strict` オプションで警告も失敗扱いにするモードを追加。
  - 本番環境用の追加ガード（LINE 設定未設定や KILL_FLAG_CLEAR_ON_START の警告）を実装。

- 実行エントリ / デーモン化
  - 実行エンジン起動スクリプト `run_execution.py` を実装。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite を使用して本番 DB と分離。
    - BrokerClientFactory 経由でブローカークライアントを生成。
    - OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine の組み立てと起動を行う。
    - デフォルトの RiskManager 設定（max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20）を設定。initial_portfolio_value は broker.get_available_cash() を利用して初期化。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）による停止/起動ガードを実装。
    - スレッドで engine.run_session を実行し、停止フラグで安全停止を行う仕組みを実装。

  - システム監視ポーリングループ起動スクリプト `run_monitoring.py` を実装。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔をオーバーライド可能（デフォルト 60 秒）。不正値時はデフォルトにフォールバックして警告を出す。
    - 監視は環境にかかわらず本番 sqlite_path を使用する旨の仕様。
    - stop フラグ（data/stop_requested.flag）の検出でループを終了。
    - SystemMonitor.check_once() の例外を捕捉して次ポーリングへ継続する耐障害性を確保。
    - 起動時にプロセス優先度を "high" に設定。

- 監視 DB 初期化
  - monitoring_db 初期化関数（init_monitoring_db）を呼び出して、監視用テーブルの存在を保証（冪等）。

- DuckDB 統合
  - DuckDB 接続（duckdb.connect）を分析用途で利用。research/および portfolio 等で利用を想定。

- ユーティリティ
  - プロセス優先度・CPU affinity 設定ユーティリティ（kabusys.utils.process_priority）を実装。
    - Windows と POSIX（Linux/ Darwin/ FreeBSD）を吸収する実装。
    - set_process_priority(level) — "high" / "normal" / "low" をサポート。権限不足や未対応 OS は警告を出してスキップ。
    - set_cpu_affinity(cpu_count) — 最初の N コアに固定。引数検証と例外ハンドリングあり。

- ポートフォリオ構築（純粋関数群）
  - 銘柄選定/重み付け（kabusys.portfolio.portfolio_builder）
    - select_candidates: スコア降順、同点時は signal_rank 昇順のタイブレークで上位 N を選択。
    - calc_equal_weights: 等金額配分（1/N）。
    - calc_score_weights: スコア加重（スコア合計が 0 の場合は等金額にフォールバックし警告）。
  - セクター集中制限・レジーム乗数（kabusys.portfolio.risk_adjustment）
    - apply_sector_cap: 既存保有のセクター比率が閾値を超える場合、新規候補を除外（unknown セクターは無視）。
    - calc_regime_multiplier: レジームラベルに応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3）。未知レジームは 1.0 でフォールバックして警告。
  - 株数決定・リスク制限（kabusys.portfolio.position_sizing）
    - calc_position_sizes:
      - allocation_method による "risk_based" / "equal" / "score" の実装。
      - lot_size（単元）で丸め、1 銘柄上限（max_position_pct）、利用率（max_utilization）、利用可能現金（available_cash）に応じた aggregate cap スケーリングを実装。
      - cost_buffer を使った保守的なコスト見積りと残余キャッシュによる端数配分ロジックを実装。
      - 価格欠損時のスキップやログ出力に配慮。

- リサーチ / ファクター計算
  - factor_research モジュールで以下のファクターを計算するための基盤実装を追加。
    - モメンタム: 1M/3M/6M リターン、200日移動平均乖離率（ma200_dev）。
    - ボラティリティ/流動性: ATR(20)・相対ATR・20日平均売買代金・出来高比率（実装途中のクエリも含む）。
    - DuckDB 上の SQL を用いて窓関数等で計算し、結果を list[dict] で返却する設計。

- ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）を追加。
    - PAPER_TRADING_SQLITE_PATH（または --db）からペーパートレード DB を読み、システム稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均/最大/P95）等の指標を集計。
    - P95 の計算、閾値比較による PASS/FAIL 判定、整形されたレポート出力を実装。
    - デフォルト閾値: 稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms。

- パッケージエクスポート
  - kabusys.portfolio の __all__ を整備して主要関数を外部に公開。

### Changed
- （初回リリースにつき特に無し）

### Fixed
- （初回リリースにつき特に無し）

### Notes / Implementation details
- 多くのモジュールは「DB 参照なし」の純粋関数設計を採用し、テスト容易性を意識した設計になっています（ポートフォリオ関連）。
- run_monitoring/run_execution は stop フラグファイル（data/stop_requested.flag）によりプロセス制御を行います。運用時はこのファイルの扱いに注意してください。
- 環境変数やファイルパスのデフォルトや挙動は Settings クラスと config_setup ウィザードで一貫して扱われます。
- PyYAML 未導入時でも validate_config は YAML 検証をスキップし警告に留めます。

---

将来のリリースでは、テストカバレッジ、エラーハンドリング強化、外部サービスのモック化、銘柄ごとの単元対応などの改善が考えられます。