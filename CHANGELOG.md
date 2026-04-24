CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

[Unreleased]
------------

- （なし）

[0.1.0] - 2026-04-24
-------------------

Added
- 基本アプリケーション骨格を追加。
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` としてリリース。
- 起動スクリプト
  - run_execution.py: ExecutionEngine 起動用スクリプトを追加。
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV が `paper_trading` の場合は paper 専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - 停止用フラグファイル（data/stop_requested.flag）および PID ファイル（data/execution.pid）を監視して安全に停止可能。
    - BrokerClientFactory を経由してブローカークライアントを生成（paper_trading では MockBrokerClient を利用する想定）。
    - ExecutionEngine をデーモンスレッドで実行し、停止フラグ検知時にエンジンを停止する仕組みを実装。
  - run_monitoring.py: システム監視ループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番の sqlite_path を使用して監視データを格納。
    - 停止フラグ（data/stop_requested.flag）検知によりループを終了。
    - SQLite / DuckDB 接続の初期化とクローズ処理を実装。
- 設定管理
  - config.py: 環境変数・設定読み込みモジュールを追加。
    - プロジェクトルート（.git または pyproject.toml を基準）を自動検出し、.env と .env.local をロード（OS 環境変数優先、.env.local は上書き可）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env パーサは export プレフィックス、クォート／エスケープ、インラインコメントに対応。
    - Settings クラスを提供し、J-Quants / kabu ステーション / DB / 監視閾値 / 環境種別 等のプロパティを明示的に取得・検証可能に。
    - PAPER_FILL_MODE の有効値チェック、KABUSYS_ENV / LOG_LEVEL の検証などを実装。
    - settings = Settings() のシングルトンをエクスポート。
- 設定ユーティリティ
  - config_setup.py: 対話式 .env 作成・更新ウィザードを追加。
    - 複数項目（環境、API トークン、DB パス、ログレベル、Kill Switch 設定等）を対話的に入力し .env を生成/更新。
    - 既存 .env の読み込み、シークレット項目のマスク表示、保存確認などをサポート。
  - validate_config.py: 起動前チェック用 CLI を追加。
    - 必須環境変数の存在チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パス親ディレクトリの存在確認、config/*.yaml の存在確認（PyYAML があればパース検証）などを実行。
    - --strict オプションで警告を FAIL 扱いにできる。
- ロギング/プロセス管理ユーティリティ
  - utils/logging_setup.py: 統一ログ設定ユーティリティを追加。
    - stdout への StreamHandler と 日次ローテーション（TimedRotatingFileHandler）を使ったファイル出力（logs/<app_name>.log、30 日分保持）をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR の解決順を実装。ログディレクトリ作成に失敗した場合はファイルハンドラをスキップして stdout のみで動作。
  - utils/process_priority.py: プロセス優先度と CPU affinity の設定ユーティリティを追加。
    - Windows と POSIX（Linux/Mac/FreeBSD）の差分を吸収して set_process_priority("high"|"normal"|"low") を提供。
    - set_cpu_affinity(n) により最初の n コアに固定する機能を追加。アクセス権限や未対応 OS では警告を出してスキップ。
- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順で選定（signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重配分を実装。全スコアが 0 の場合は等配分にフォールバックして警告。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: 既存保有のセクター比率が上限を超える場合に当該セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム ("bull","neutral","bear") に応じた投下資金乗数を返却し、未知レジームは 1.0 でフォールバック（警告）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（"risk_based"/"equal"/"score"）に応じて銘柄ごとの発注株数を計算。
      - risk_based: 許容リスク（risk_pct）と stop_loss_pct を用いた逆算式で株数を決定。
      - lot_size 単位で丸め、max_position_pct（1銘柄上限）を考慮。
      - aggregate cap（available_cash）を超える場合はスケーリングし、端数は fractional 残差の大きい順に lot_size 単位で追加配分する仕組みを実装。
      - cost_buffer によりコスト見積りを保守的に扱える。
  - portfolio/__init__.py で主要関数をエクスポート。
- 研究・ファクター計算
  - research/factor_research.py: ファクター計算モジュール（モメンタム／MA200乖離／ATR 等）を追加（設計方針と定数、calc_momentum の実装開始）。DuckDB 経由で prices_daily / raw_financials を参照する設計。※ファイル末尾は途中（calc_momentum の実装継続）であることが示唆される。
- ツール
  - tools/paper_verification_report.py: Paper Trading 検証レポート生成スクリプトを追加。
    - SQLite（デフォルト: data/paper_trading.db）を読み、稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを集計してレポート出力。
    - デフォルト閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）に基づく PASS/FAIL 判定を実装。
    - --from / --to / --db オプションをサポート。
- データベース初期化支援
  - monitoring.monitoring_db.init_monitoring_db を利用して、起動スクリプトから監視用テーブルの存在を保証（冪等）する呼び出しを追加（monitoring と execution 両方で実行）。
- その他
  - ストップ／キルフラグや PID ファイル、ログ出力などの運用上のインフラを整備。
  - 多くのモジュールでエラー時にログ出力して安全にフォールバックする実装（警告や例外ハンドリング）を採用。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Security
- 初回リリースのため該当なし。

Notes / 備考
- .env ファイルは絶対にリポジトリにコミットしないことを README 等で強く明記する（config_setup.py で警告文を含めて出力済み）。
- research/factor_research.py の実装は一部未完（calc_momentum の続き）であるため、今後の追加実装でファクター計算ロジックを完成させる必要があります。
- 実運用での監視・発注は外部ブローカーや API へのアクセスを伴うため、環境変数や LINE 通知設定等を本番用途に合わせて慎重に設定してください（validate_config のガードあり）。