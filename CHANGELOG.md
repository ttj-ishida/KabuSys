# CHANGELOG

すべての重要な変更点を Keep a Changelog 準拠で記載します。  
初期リリースとして、v0.1.0 をリリースしました。

All notable changes to this project will be documented in this file.

## [Unreleased]

## [0.1.0] - 2026-04-25
### Added
- 基本的なアプリケーション構成と起動スクリプトを追加
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプト。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離して動作。
    - BrokerClientFactory でブローカークライアントを生成（モック/実ブローカーを環境に応じて切替）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立ててスレッドでエンジンを実行。data/stop_requested.flag により安全に停止可能。
    - 起動時にプロセス優先度を "high" に設定（utils.process_priority を使用）。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、不正値はデフォルトへフォールバック）。
    - 監視は環境にかかわらず監視用の sqlite_path（デフォルト: data/monitoring.db）を使用して DB 初期化を行う。
    - 停止フラグ（data/stop_requested.flag）検知によるループ終了、例外発生時のログ出力とループ継続処理を実装。
  - config.py
    - 環境変数読み込み / 設定管理モジュール。
    - プロジェクトルート自動検出（.git または pyproject.toml を探索）に基づき .env/.env.local を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - .env のパースは export 形式やクォート付き値、インラインコメントに対応する堅牢な実装。
    - Settings クラスを提供し、環境変数へのアクセスをラップ。各種プロパティ（DBパス、PID/kill flag path、閾値、PAPER_FILL_MODE の検証など）を提供。
    - KABUSYS_ENV / LOG_LEVEL 等の検証と便利メソッド（is_live / is_paper / is_dev）を実装。
  - config_setup.py
    - .env の対話式ウィザード。初期作成・更新を支援。
    - セクション化されたテンプレート出力と秘匿表示（パスワード/トークンはマスク）を実装。保存前の確認プロンプトあり。
    - .env の書き込みは Git 管理禁止の注意を含むヘッダー付きで出力。
  - validate_config.py
    - 起動前の設定検証 CLI。
    - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）、KABUSYS_ENV 値検証、DB パス存在確認、config/*.yaml の存在と YAML パースチェック（PyYAML がない場合はスキップ）など。
    - --strict オプションで警告を失敗扱いにできる。
  - tools/paper_verification_report.py
    - ペーパートレード用検証レポート生成スクリプト。
    - system_status / trade_logs / risk_logs テーブルを参照し、稼働率、注文成功率、送信率、P95 レイテンシ等を算出して PASS/FAIL 判定を出力。
    - デフォルト基準値（稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 <= 200ms）を定義。
    - --from / --to / --db オプションをサポート。
  - utils/logging_setup.py
    - 全アプリケーションで共通利用できるロギング設定ユーティリティ。
    - stdout に StreamHandler、さらに日次ローテーション（TimedRotatingFileHandler）でログファイルを出力（logs/<app_name>.log、30 日分保持）。ログディレクトリ作成に失敗した場合はコンソール出力のみで継続。
    - 既存ハンドラをクリアしてから再設定することで二重出力を防止。
  - utils/process_priority.py
    - Windows / POSIX（Linux/Mac/FreeBSD）を吸収したプロセス優先度設定ユーティリティ。
    - psutil を用いて nice / Windows 優先度クラスを設定。アクセス権限がない場合は警告を出してスキップ。
    - CPU affinity 設定関数 set_cpu_affinity を提供。
  - portfolio パッケージ（純粋関数群: DB 参照無し）
    - portfolio_builder.py
      - select_candidates: スコア順ソートと上位 N 抜粋。
      - calc_equal_weights / calc_score_weights: 重み付けロジック。スコア合計が 0 の場合は等配分にフォールバックし警告。
    - risk_adjustment.py
      - apply_sector_cap: セクター集中による候補除外ロジック。既存保有時価を計算し max_sector_pct を超えるセクターを除外（unknown セクターは上限適用除外）。
      - calc_regime_multiplier: market regime に対する投下資金乗数（bull=1.0, neutral=0.7, bear=0.3、未知は 1.0 でフォールバック）。
    - position_sizing.py
      - calc_position_sizes: allocation_method ごとの発注株数計算（risk_based / equal / score）。
      - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（利用可能現金を超える場合のスケーリング）、cost_buffer による保守的見積り、残差を用いた追加配分ロジックを実装。
  - research/factor_research.py（部分実装）
    - DuckDB を用いたファクター計算基盤（Momentum / Value / Volatility / Liquidity を想定）。設計方針・定数を追加。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Deprecated
- 初回リリースのため該当なし。

### Removed
- 初回リリースのため該当なし。

### Security
- 初回リリースのため該当なし。

---

注記:
- パッケージバージョンは src/kabusys/__init__.py の __version__ = "0.1.0" に合わせています。
- .env 自動ロードはプロジェクトルートが特定できない場合はスキップされます（パッケージ配布後の安全性を考慮）。
- 実運用での本番設定（KABUSYS_ENV=live）では LINE 通知設定や Kill Switch の扱いに注意する旨のガードチェックが validate_config に実装されています。