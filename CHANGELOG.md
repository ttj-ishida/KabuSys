CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

（なし）

0.1.0 - YYYY-MM-DD
------------------

Added
- 初回リリース（0.1.0）。以下の主要機能・モジュールを追加しました。
  - 実行・監視用起動スクリプト
    - run_execution.py
      - ExecutionEngine 起動スクリプトを提供。
      - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 DB（デフォルト: data/paper_trading.db）と MockBrokerClient を使用して本番 DB と分離。
      - 停止制御に data/stop_requested.flag を利用し、実行中スレッドを安全に停止可能。
      - 実行プロセス用 PID ファイル（data/execution.pid）を利用。
      - 起動時にプロセス優先度を "high" に設定。
    - run_monitoring.py
      - SystemMonitor をポーリングする監視ループ起動スクリプトを提供。
      - ポーリング間隔を MONITOR_POLL_INTERVAL 環境変数で上書き可能（デフォルト: 60 秒）。不正な値はデフォルトへフォールバックし、警告を出力。
      - 監視は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用する設計（監視データの一元管理）。
      - 停止フラグ（data/stop_requested.flag）を検知してループを終了。
      - 起動時にプロセス優先度を "high" に設定。

  - 設定周り
    - config.py
      - .env ファイル自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml）。
      - .env と .env.local の読み込み順序と環境変数上書きルールを実装（OS 環境変数は保護）。
      - .env の行パースを強化（export 形式の対応、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱いを実装）。
      - Settings クラスを実装し、各種設定値をプロパティ経由で取得可能に。
      - 各種設定プロパティを追加:
        - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
        - DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PAPER_FILL_MODE（入力検証あり）
        - PID / KILL フラグパス、kill_flag_clear_on_start、CPU/Memory/Disk 閾値
        - KABUSYS_ENV / LOG_LEVEL の検証ロジック、is_live/is_paper/is_dev ヘルパー
    - config_setup.py
      - 対話式ウィザードで .env の初期作成・更新を支援する CLI を実装。
      - デフォルト値表示、シークレットマスク、選択肢サポート、最終確認・保存機能を提供。

  - 設定検証ツール
    - validate_config.py
      - .env と config/*.yaml の基本的整合性を検証する CLI を実装。
      - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 値チェック、DB パス（親ディレクトリ存在）チェック、YAML ファイルの存在・パースチェック（PyYAML があれば詳細検証）。
      - KABUSYS_ENV=live の際に追加の安全確認（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の危険性）を実行。
      - --strict オプションで警告を FAIL 扱いにできる。

  - ログ・プロセスユーティリティ
    - utils/logging_setup.py
      - StreamHandler（stdout）および TimedRotatingFileHandler（日次・30日保持）をルートロガーに設定するユーティリティを追加。
      - ログレベル / ログディレクトリの解決順を定義。ディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - utils/process_priority.py
      - Windows/Linux/macOS 等の差分を吸収してプロセス優先度（high/normal/low）を設定する関数を実装。
      - CPU affinity を最初の N コアに固定する set_cpu_affinity を追加。
      - 権限不足などで設定に失敗した場合は警告を出力してスキップ。

  - ポートフォリオ構築（純粋関数群）
    - portfolio/portfolio_builder.py
      - select_candidates: BUY シグナルをスコア順にソートして上位 N を選択。
      - calc_equal_weights: 等金額配分を算出。
      - calc_score_weights: スコア加重配分を算出（全スコアが 0 の場合は等金額へフォールバックし WARNING）。
    - portfolio/risk_adjustment.py
      - apply_sector_cap: セクターごとのエクスポージャー上限を超えている場合に候補を除外するロジック（"unknown" セクターは上限不適用）。
      - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を提供（未知レジームはフォールバックで 1.0、警告出力）。
    - portfolio/position_sizing.py
      - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に応じて発注株数を計算。
      - 単元株（lot_size）、max_position_pct、max_utilization、cost_buffer を考慮した aggregate cap スケーリング実装。
      - スケーリング後の残余キャッシュで fractional 残差に基づき lot 単位で追加配分する再現性のあるロジック。

  - Paper Trading 支援ツール
    - tools/paper_verification_report.py
      - Paper Trading の検証レポート生成 CLI を追加。
      - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均・最大・P95）を集計。
      - 各指標に対する閾値判定を実装（稼働率、成立率、送信率、P95 レイテンシ）。
      - P95 計算ロジック、日付フィルタ、DB パス解決（--db オプション / PAPER_TRADING_SQLITE_PATH / デフォルト）を提供。

  - 研究用ファクター計算（スケルトン）
    - research/factor_research.py
      - DuckDB 接続を受け取り、momentum/value/volatility/liquidity 等のファクターを計算するための設計と一部実装（calc_momentum のヘッダや定数群など）を追加。prices_daily / raw_financials を参照する仕様。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- （該当なし）

Notes / 補足
- MONITOR_POLL_INTERVAL 環境変数の値は整数で 1 以上を期待します。不正な値は警告を出してデフォルト（60 秒）にフォールバックします。
- PAPER_FILL_MODE は "instant" / "partial" / "never" / "reject" のいずれかに制限され、無効値は例外になります。
- .env 自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化できます（テスト等で使用）。
- logging_setup はログディレクトリ作成に失敗した場合でもアプリを止めずコンソールログにフォールバックします。
- 実行・監視スクリプトは起動時にプロセス優先度を上げる挙動があります（権限がない場合は警告でスキップ）。

--- 
今後のリリースでは、Strategy / Execution の詳細実装、ファクター計算の完成、ユニットテストの追加、ドキュメントの拡充を予定しています。