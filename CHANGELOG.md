CHANGELOG
=========

すべての変更は Keep a Changelog の慣例に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

- （なし）

[0.1.0] - 2026-04-22
--------------------

Added
- 初回公開リリース。
- コア起動スクリプト
  - run_execution.py: ExecutionEngine の起動スクリプト。  
    - KABUSYS_ENV=paper_trading 時は専用の paper DB（data/paper_trading.db、環境変数で上書き可）を使用して本番 DB と分離。  
    - BrokerClientFactory を用いたブローカークライアント作成、OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine をスレッドで実行。  
    - data/stop_requested.flag による外部停止フラグ検出とエンジン停止処理を実装。実行時に execution.pid を管理。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。  
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（デフォルト 60 秒、無効値時にフォールバックで警告）。  
    - 監視 DB 初期化（monitoring 用テーブルの冪等初期化）および DuckDB 接続を確立。停止フラグ検出でループを終了。

- 設定・環境管理
  - config.py: 環境変数ラッパー Settings クラスを提供。  
    - .env 自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml 基準）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。  
    - 各種プロパティ（J-Quants / kabu API / LINE / DB パス / PID/KILL フラグパス / thresholds / 環境識別など）を提供。  
    - PAPER_FILL_MODE の妥当性チェック、KABUSYS_ENV / LOG_LEVEL の検証、paper_sqlite_path 等を用意。
  - config_setup.py: 対話式 .env 作成ウィザード。既存 .env 読み込み、シークレット項目のマスク表示、確認後ファイル保存。
  - validate_config.py: 起動前設定検証 CLI。必須環境変数チェック、KABUSYS_ENV 検証、DB パス親ディレクトリチェック、config/*.yaml の存在・パース検証（PyYAML 未導入時は警告）、本番向けガード（LINE 設定や KILL_FLAG_CLEAR_ON_START の注意喚起）を実装。--strict による警告を FAIL 扱いにするモードあり。

- ポートフォリオ構築ライブラリ (pure functions, DB 参照なし)
  - portfolio/portfolio_builder.py: 候補選定・重み計算
    - select_candidates: スコア降順・タイブレークに signal_rank を考慮して上位 N を返す
    - calc_equal_weights / calc_score_weights: 等重配分・スコア加重配分（全スコア 0 の場合は等重にフォールバックして WARNING）
  - portfolio/risk_adjustment.py: セクター集中制限・レジーム乗数
    - apply_sector_cap: 既存保有のセクター比率が上限を超える場合、新規候補を除外（unknown セクターは除外対象外）  
    - calc_regime_multiplier: "bull"/"neutral"/"bear" に対する乗数マップを実装。未知レジームは警告とともに 1.0 フォールバック。
  - portfolio/position_sizing.py: 発注株数計算（allocation_method: "risk_based" / "equal" / "score"）  
    - risk_based: 許容リスク率・損切り率から基準株数を算出、単元株（lot_size）丸め。  
    - equal/score: 各銘柄の重み・利用可能現金・max_utilization を考慮して算出。  
    - aggregate cap: 利用可能現金を超えた場合にスケーリングして lot_size 単位で再配分するロジックを実装。cost_buffer（手数料・スリッページ見積）対応。  
    - TODO / 設計注記: 将来的に銘柄ごとの lot_size 対応やフォールバック価格の導入を想定したコメントあり。

- ユーティリティ
  - utils/logging_setup.py: 統一的ロギング設定ユーティリティ。  
    - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler、30 日保持）をルートロガーに設定。既存ハンドラのクリア、LOG_DIR/LOG_LEVEL 解決順を実装。ファイルハンドラ作成失敗時はコンソールのみで継続。stdout を使用することで cron 等のリダイレクトに対応。
  - utils/process_priority.py: プロセス優先度および CPU affinity 設定ユーティリティ（Windows / POSIX 差分を吸収）。  
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。実行環境での権限不足時に警告でスキップする耐障害性あり。

- データ/検証ツール
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプト。  
    - system_status / trade_logs / risk_logs から稼働率・注文成功率・送信率・リスク却下数・API レイテンシ（avg/max/P95）を集計して人間向けレポートを出力。  
    - デフォルト DB パスは data/paper_trading.db。--from/--to/--db オプション対応。基準値（稼働率・成功率・P95 など）に基づく PASS/FAIL 判定を実装。

- 研究モジュール（部分実装）
  - research/factor_research.py: ファクター計算モジュールの土台を追加（モメンタム等のファクター設計、期間定数、calc_momentum の雛形開始）。DuckDB 接続を受ける設計。実装の続き（コードの末尾で未完）がある旨注記。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Notes / Known limitations
- research/factor_research.py は途中までの実装（calc_momentum の続きが存在せず未完）。今後のリリースで完成予定。
- position_sizing / risk_adjustment にいくつかの TODO コメントあり（銘柄別 lot_size、価格フォールバックなど）。
- .env の自動読み込みはプロジェクトルートの検出に依存するため、配布後や特殊配置時に自動ロードをスキップする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- 本リリースでは各種 config/*.yaml の雛形や外部依存（PyYAML 等）がない環境での挙動は警告で扱う設計です。

開発ヒント
- ログ設定・プロセス優先度設定は各起動スクリプトの冒頭で必ず呼ぶ設計（すでに run_* スクリプトがそれを行っています）。
- Paper Trading と Live の DB 分離・設定検証用 CLI を活用して本番環境での設定ミスを未然に検出してください。

---  
(本 CHANGELOG はソースコードから推測して作成しています。実際のコミット履歴を基にした変更履歴とは異なる場合があります。)