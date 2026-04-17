CHANGELOG
=========

この CHANGELOG は「Keep a Changelog」形式に準拠しています。  
フォーマットや運用ルールの詳細は https://keepachangelog.com/ja/ を参照してください。

Unreleased
----------

（現在のブランチ/次リリース向けの未リリース変更はここに記載します。実装時点では特に未リリースの差分はありません。）

0.1.0 - 2026-04-17
-----------------

初回公開リリース。以下の主要機能・モジュールを追加しました。

Added
- 基本情報
  - パッケージ初期バージョンを設定（kabusys.__version__ = "0.1.0"）。
  - プロジェクトルートの自動検出ロジックを実装（.git / pyproject.toml を基準）。

- 設定管理
  - 環境変数管理モジュールを追加（kabusys.config）。
    - .env / .env.local の自動読み込み（OS環境変数優先、.env.local が上書き）。
    - 複雑な .env パース（export プレフィックス、クォート内エスケープ、インラインコメント処理）を実装。
    - Settings クラスに各種設定プロパティを提供（J-Quants / kabuAPI / DBパス / Paper Trading 設定 / 監視しきい値等）。
    - PAPER_FILL_MODE の検証ロジック（instant/partial/never/reject）。
    - KABUSYS_ENV の検証（development / paper_trading / live）および is_live/is_paper/is_dev 補助プロパティ。

- 設定ユーティリティ CLI
  - 対話的な .env 作成・更新ウィザードを追加（kabusys.config_setup）。
    - 各種設定項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, KILL_FLAG_CLEAR_ON_START など）を対話式に設定可能。
    - 既存 .env の読み込みと値のマスク表示、保存前の確認を実装。
    - .env のテンプレート書き出し（機密値はマスク、.env を絶対に Git にコミットしないよう注記）。

  - 起動前設定検証 CLI を追加（kabusys.validate_config）。
    - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）。
    - KABUSYS_ENV / LOG_LEVEL の妥当性チェック。
    - DB パスの親ディレクトリ存在チェック（警告）。
    - config/*.yaml の存在確認と（PyYAML があれば）パース検証。
    - KABUSYS_ENV=live 時の追加ガード（LINE通知設定や Kill Switch 設定の警告）。
    - --strict オプションで警告も失敗扱いにできる。

- 実行エンジン / 監視
  - 実行エンジン起動スクリプトを追加（kabusys.run_execution）。
    - KABUSYS_ENV=paper_trading の場合、paper_trading 専用 SQLite DB（デフォルト data/paper_trading.db）を使用して本番 DB と完全分離。
    - BrokerClientFactory を使ったブローカークライアント生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine の組み立てとデーモンスレッドでの実行制御。
    - 停止フラグ（data/stop_requested.flag）検知による安全停止処理。
    - 実行中 PID を data/execution.pid に保持する仕組み（Engine 側で使用）。

  - 監視ループ起動スクリプトを追加（kabusys.run_monitoring）。
    - SystemMonitor のポーリングループ実装。既定ポーリング間隔 60 秒（MONITOR_POLL_INTERVAL 環境変数で上書き可能）。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する旨を明確化。
    - 停止フラグ検知でループ終了、例外はログ出力して次回ポーリングまで待機。

  - 監視 DB 初期化ユーティリティを想定した init_monitoring_db 呼び出し（冪等性を想定）。

- ツール
  - Paper Trading 検証レポート生成スクリプトを追加（kabusys.tools.paper_verification_report）。
    - paper_trading の SQLite DB（環境変数 PAPER_TRADING_SQLITE_PATH または --db 指定）から各種指標を集計して標準出力にレポートを出力。
    - 集計指標:
      - システム稼働率（system_status テーブル）: 総ポーリング数 / エラー数 / 稼働率（%）
      - 注文統計（trade_logs）: Created/Filled/Sent カウント、成功率（Filled/Created）、送信率（Sent/Created）
      - リスク却下数（risk_logs）
      - レイテンシ（avg / max / P95）
    - Pass/Fail 判定基準を定義（稼働率 >=99%、fill_rate >=90%、send_rate >=95%、P95 <=200 ms）。
    - 日付フィルタ（--from / --to）対応。欠損テーブルに対する失敗耐性あり。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - kabusys.portfolio モジュールを追加:
    - portfolio_builder:
      - select_candidates: スコア降順・タイブレーク処理で候補選定。
      - calc_equal_weights: 等金額配分。
      - calc_score_weights: スコア正規化配分（全スコア0 の場合は等金額にフォールバック）。
    - risk_adjustment:
      - apply_sector_cap: セクター集中制限ロジック（既存保有のセクター比率に基づき新規候補を除外）。unknown セクターは制限対象外。
      - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear をマップ、未知値は 1.0 でフォールバック）。
    - position_sizing:
      - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") による株数算出、単元株（lot_size）丸め、per-stock 上限や aggregate cap（available_cash）でスケールダウン、cost_buffer を考慮した安全マージン、スケール時の端数処理（残差に基づく追加配分）。

  - すべての関数は副作用なし（純粋関数）で、DB 参照は行わずメモリ内計算のみ。

- 研究用ファクター計算
  - kabusys.research.factor_research を追加:
    - DuckDB 接続を受け取り prices_daily / raw_financials テーブルから各種ファクターを計算。
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離の計算（ウィンドウ行数チェック）。
    - calc_volatility: ATR / 相対ATR / 20日平均売買代金 / 出来高変化率 等の計算基盤（部分実装ファイル断片あり）。
    - DuckDB SQL を用いた効率的なウィンドウ集計と NULL 応答の扱いに配慮。

- ユーティリティ
  - プロセス優先度・CPU affinity 設定ユーティリティを追加（kabusys.utils.process_priority）。
    - set_process_priority(level): Windows / POSIX（Linux, Darwin, FreeBSD）に対応。psutil を利用して nice/priority を設定し、失敗時は警告を出してフォールバック。
    - set_cpu_affinity(cpu_count): 指定コア数で CPU affinity を設定。例外は警告で吸収。
    - run_execution / run_monitoring の起動シーケンスで優先度を "high" に設定する呼び出しが組み込まれている。

Changed
- （初回リリースのため既存変更はなし）

Fixed
- （初回リリースのため修正履歴はなし）
  - 注意: 実装内で非正（<=0）な MONITOR_POLL_INTERVAL や不正な値に対してデフォルトにフォールバックする保護ロジックを導入。

Security
- .env ファイルに関する注意:
  - config_setup により生成される .env は機密情報を含むため絶対に VCS にコミットしない旨を明記。
  - 設定ウィザードでは機密値が表示時にマスクされる（確認画面含む）。

Notes / Migration
- 初回リリースのため移行作業は不要です。新規セットアップ時の推奨手順:
  1. python -m kabusys.config_setup を実行して .env を生成/更新する
  2. python -m kabusys.validate_config で設定を検証する
  3. 実行: python -m kabusys.run_monitoring / python -m kabusys.run_execution
  4. Paper Trading の評価は python -m kabusys.tools.paper_verification_report を使用

- 環境変数の主な名称とデフォルト:
  - KABUSYS_ENV (development | paper_trading | live) — default: development
  - JQUANTS_REFRESH_TOKEN — 必須
  - KABU_API_PASSWORD — 必須
  - DUCKDB_PATH — default: data/kabusys.duckdb
  - SQLITE_PATH — default: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH — default: data/paper_trading.db
  - PAPER_FILL_MODE — default: instant (instant|partial|never|reject)
  - MONITOR_POLL_INTERVAL — default: 60 (秒)

Acknowledgements / References
- 本 CHANGELOG はソースコードの注釈、ドキュメント文字列、および実装の振る舞いから推測して作成しています。実運用時には README とリリースノートに合わせて追記・修正してください。