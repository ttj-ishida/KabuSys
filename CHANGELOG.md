# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
このファイルはコードベースから推測して作成した初期リリース向けの変更履歴です。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-17
初回リリース。自動売買システム KabuSys のコアユーティリティ、起動スクリプト、ポートフォリオ構築ロジック、検証ツール等を追加。

### Added
- 基本情報
  - パッケージバージョンを `__version__ = "0.1.0"` として追加。
  - パッケージ公開用の主要モジュールエクスポートを定義（portfolio, strategy, execution, monitoring）。

- 設定関連
  - Settings クラスによる環境変数/設定管理を追加。
    - .env 自動ロード機能（プロジェクトルートの .env / .env.local を優先読み込み。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）。
    - 必須/任意の設定項目をプロパティとして提供（J-Quants / kabuAPI / DB パス / PAPER_FILL_MODE / KABUSYS_ENV 等）。
    - 環境値検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE のバリデーション）。
  - 対話式設定ウィザード `kabusys.config_setup` を追加。
    - .env の作成・更新を支援。シークレット項目はマスク表示。
    - デフォルト値・選択肢・説明文付きの項目定義を提供。
  - 設定検証 CLI `kabusys.validate_config` を追加。
    - 必須環境変数の存在チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリチェック、config/*.yaml の存在・パース検証（PyYAML がある場合）。
    - `--strict` オプションで警告をエラー扱いにできる。

- 起動スクリプト / ランタイム
  - 監視ループ起動スクリプト `kabusys.run_monitoring` を追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックしログに警告。
    - 監視は KABUSYS_ENV にかかわらず production 用 sqlite_path を使用する仕様（監視データは本番 DB に記録）。
    - 停止フラグファイル（data/stop_requested.flag）検知、例外時のロギング、終了時に DB 接続をクローズ。
  - 実行エンジン起動スクリプト `kabusys.run_execution` を追加。
    - KABUSYS_ENV=paper_trading 時は MockBroker を使用し、paper_trading 専用 SQLite（data/paper_trading.db）に記録して本番 DB と分離。
    - プロセス優先度を起動時に "high" に設定する処理を実行（set_process_priority を使用）。
    - エンジンを別スレッドで起動して停止フラグを監視、停止時にエンジンへ stop() を呼び出す。

- 実行（Execution）関連コンポーネント
  - BrokerClientFactory、ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager の組み立て・起動フローを追加（run_execution で利用）。
  - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を定義し、初期利用可能現金を broker.get_available_cash() から取得して設定。

- 監視（Monitoring）
  - 監視用 DB 初期化ユーティリティ `init_monitoring_db` を呼び出すことで監視テーブルの存在を保証（冪等処理）。

- ポートフォリオ構築（Portfolio）
  - portfolio_builder:
    - 信号のソート/候補選択（select_candidates）。
    - 等金額配分（calc_equal_weights）。
    - スコア加重配分（calc_score_weights）。スコア合計が 0 の場合は等金額にフォールバックして警告を出力。
  - risk_adjustment:
    - セクター集中チェック（apply_sector_cap）：既存保有のセクター比率が閾値を超えている場合に当該セクターの新規候補を除外。
    - レジームに応じた資金乗数（calc_regime_multiplier）：'bull'/'neutral'/'bear' をマッピングし、不明なレジームは警告の上 1.0 にフォールバック。
  - position_sizing:
    - 発注株数計算（calc_position_sizes）：allocation_method により "risk_based" / "equal" / "score" をサポート。
    - 単元株（lot_size）丸め、1 銘柄上限（max_position_pct）、aggregate cap（利用可能現金を超える場合のスケーリング）、cost_buffer を用いた保守的見積りを実装。
    - risk_based モードでは損切り幅 stop_loss_pct と risk_pct に基づく株数算出を行う。
    - スケールダウン時の端数処理（残余現金を用いた lot 単位での追加配分）を実装。

- 研究（Research）
  - factor_research モジュールを追加（DuckDB を使ったファクター計算）。
    - Momentum ファクター計算（1M/3M/6M リターン、MA200 乖離）: calc_momentum。
    - Volatility/流動性ファクター（ATR20、相対 ATR、20日平均売買代金、出来高比など）の算出（calc_volatility、内部 SQL ロジックを使用）。
    - DuckDB 接続を受け価格データ（prices_daily）等を参照して計算。データ不足時は None を返す仕様。

- ユーティリティ
  - process_priority ユーティリティを追加:
    - set_process_priority(level) による Windows / POSIX の差分吸収（psutil を使用）。
    - set_cpu_affinity(cpu_count) による CPU affinity 固定（利用可能なコア数を考慮）。
    - 権限不足や非対応プラットフォームでは警告を出して安全にスキップする設計。

- ツール
  - Paper Trading 検証レポート生成スクリプト `kabusys.tools.paper_verification_report` を追加。
    - PAPER_TRADING_SQLITE_PATH（または --db）で指定した SQLite DB から検証指標を集計（システム稼働率、注文成功率/送信率、リスク却下数、平均/最大/P95 レイテンシ等）。
    - Pass/Fail 基準を定義（稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200 ms）。
    - レポートには期間フィルタ（--from/--to）をサポート。DB が存在しない場合はエラーメッセージを表示。

### Changed
- （初回リリースのため変更履歴はなし。各モジュールは設計方針に基づき堅牢性を考慮して実装）

### Fixed
- （初回リリースのため修正履歴はなし）
- 実装上の堅牢性注記（コード内での例外処理や不正値フォールバックなど）
  - .env パーサーはクォート内のエスケープやインラインコメントを考慮。
  - validate_config は PyYAML 未インストール時に YAML 検証をスキップして警告を出す。
  - MONITOR_POLL_INTERVAL の不正値は警告してデフォルトにフォールバック。
  - process_priority / set_cpu_affinity は権限エラーや未対応機能の際に警告を出して処理をスキップ。

### Deprecated
- なし

### Removed
- なし

### Security
- なし（ただし、.env を絶対にコミットしない旨を config_setup の生成ファイルに明記）

---

注記:
- 本 CHANGELOG は配布されたコードベースの内容から推測して作成しています。内部実装の詳細や外部インタフェースの変更点（過去バージョンとの比較）は手元に差分がないため反映していません。必要があれば、実際のコミット履歴やリリースノートに基づいて更新できます。