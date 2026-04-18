# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

なお、記載内容は提示されたコードベースから推測して作成しています。

## [0.1.0] - 2026-04-18
初回リリース。

### 追加
- 基本パッケージ構成を追加（kabusys）。
  - パッケージバージョン: 0.1.0
- 実行用スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV によって paper_trading 用 DB と MockBrokerClient を使用可能。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止制御用のフラグファイル（data/stop_requested.flag）と PID ファイル（data/execution.pid）に対応。
    - スレッドでエンジンを実行し、停止フラグ検知で安全に停止する仕組み。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用の sqlite_path を使用する設計。
    - 停止フラグ検知でループ終了、KeyboardInterrupt に対応。
- 環境設定・検証ツール
  - config_setup.py
    - 対話式ウィザードで .env を初期作成・更新。
    - J-Quants / kabu API / DB パス / ログレベル / Kill Switch 等の主要設定をサポート。
  - validate_config.py
    - .env と config/*.yaml の設定検証 CLI。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリチェック、YAML のパース検査（PyYAML 未インストール時は警告）などを実施。
    - --strict オプションで警告を FAIL 扱いにできる。
- 環境変数読み込み・設定管理
  - config.py
    - 自動でプロジェクトルート（.git または pyproject.toml）を探索して .env/.env.local を読み込む自動ロード機能（無効化可能: KABUSYS_DISABLE_AUTO_ENV_LOAD）。
    - 高機能な .env パーサを実装（export プレフィックス対応、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの取り扱い）。
    - Settings クラスを提供し、主要設定（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PID/KILL フラグパス、閾値など）をプロパティ経由で取得可能。
    - 環境 (development/paper_trading/live) やログレベルの妥当性検査を実装。
    - PAPER_FILL_MODE の妥当性チェック（instant/partial/never/reject）。
- ロギング・プロセスユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション、30 日分保持）を設定するユーティリティ。
    - LOG_DIR/LOG_LEVEL 環境変数または引数で設定可能。ログディレクトリ作成失敗時はコンソール出力のみで継続。
  - utils/process_priority.py
    - Windows / POSIX（Linux/Mac 等）を吸収してプロセス優先度（high/normal/low）を設定するユーティリティ。
    - psutil を用いて nice 値 / Windows 優先度クラスを設定。アクセス権限や未対応環境では警告出力して安全にスキップ。
    - CPU affinity を最初の N コアに固定する機能も提供（サポート環境のみ、例外時は警告）。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順にソートして上位 N を選択。
    - calc_equal_weights, calc_score_weights: 等配分およびスコア加重配分（スコア全て 0 の場合は等配分にフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター別上限を適用して候補を除外するロジック（unknown セクターは除外対象外）。当日売却予定銘柄をエクスポージャー計算から除外可能。
    - calc_regime_multiplier: market regime に基づく投下資金乗数を返す（bull/neutral/bear、未知レジームは 1.0 でフォールバックし警告）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method に応じた発注株数計算を提供（risk_based / equal / score）。
    - 単元株（lot_size）で丸め、1 銘柄上限（max_position_pct）、投下資金上限（max_utilization）を考慮。
    - aggregate cap 超過時はスケーリングして残余キャッシュで端数を lot 単位で配分するアルゴリズムを実装。
    - 価格欠損時のスキップやログ出力、cost_buffer による保守的見積もりをサポート。
- 計測・検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプト。
    - システム稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均/最大/P95）を SQLite DB（デフォルト: data/paper_trading.db）から集計。
    - コマンドラインで期間指定 (--from / --to) と DB パス (--db) を指定可能。
    - デフォルトの合格基準（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）を定義し PASS/FAIL を判定。
- リサーチ（ファクター計算）基盤
  - research/factor_research.py（骨組み）
    - DuckDB 接続を受け取り prices_daily / raw_financials テーブルを基にモメンタム / Value / Volatility / Liquidity 系ファクターを計算する設計。モジュール内に定数と calc_momentum の仕様を含む（実装は継続的に拡張される想定）。

### 変更
- なし（初回リリースのため該当なし）。

### 修正
- なし（初回リリースのため該当なし）。

### 注意事項 / 設計上の備考
- run_monitoring は MONITOR_POLL_INTERVAL が無効値（0 以下や非整数）の場合にデフォルト（60 秒）へフォールバックする挙動がある。
- config.py の .env 自動ロードはプロジェクトルート検出に依存する（.git または pyproject.toml）。自動ロードを無効にする環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
- validate_config は PyYAML が未インストールの場合、YAML 内容検証をスキップして警告を出す。
- ExecutionEngine / RiskManager 等の詳細な動作は実装内部に依存し、本 CHANGELOG は公開 API と起動スクリプト周りの挙動にフォーカスしています。
- 一部関数（research.calc_momentum など）はコメント内で詳細仕様を記載しているが、実装が継続中（ファイル末尾が切れている可能性があります）。運用前に該当箇所の完成度を確認してください。

---

今後のリリースでは各モジュールの個別改善（例: ロギングの改良、position sizing の拡張、factor 計算の完成、単体テスト追加等）を予定しています。