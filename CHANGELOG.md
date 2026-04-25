# Changelog

すべての著名な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠し、セマンティックバージョニングを採用します。

## [0.1.0] - 2026-04-25

### Added
- 初回リリース: KabuSys のコアユーティリティと CLI、ポートフォリオ構築ロジック、モニタリング / 実行用ランチャースクリプトを追加。
- CLI / スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV=paper_trading の場合はペーパートレード用の専用 SQLite（data/paper_trading.db をデフォルト）を使用する分離設計。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine のスレッド起動と停止フラグ（data/stop_requested.flag）による安全停止処理。
    - 起動時にプロセス優先度を "high" に設定し、PID ファイルを管理。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値はデフォルトにフォールバック）。
    - 監視用 DB 初期化（init_monitoring_db 呼び出し）、DuckDB 接続、停止フラグ検出による終了処理。
  - validate_config.py: 起動前の設定検証ツール（.env と config/*.yaml の存在・簡易パース・環境変数チェック）。
    - --strict オプションで警告をエラー扱いにできる。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ確認、YAML の簡易パース（PyYAML がインストールされている場合）等を実施。
  - config_setup.py: 対話式環境設定ウィザード（.env の初期作成・更新を支援）。
    - よく使う設定項目を対話的に入力・確認して .env を生成する機能。
  - tools/paper_verification_report.py: ペーパートレード用検証レポート生成スクリプト。
    - system_status / trade_logs / risk_logs を参照して稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを集計し PASS/FAIL 判定を出力。
    - 日付範囲フィルタ（--from / --to）、DB パス指定（--db / 環境変数）に対応。
- 設定管理
  - config.py:
    - .env の自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - .env / .env.local の優先度処理（.env.local が上書き）。
    - 高度な .env パーサ: export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理などに対応。
    - Settings クラスを提供し、環境固有のプロパティ（env, is_live, is_paper, is_dev）、DB パス、paper_trading 用パスや fill mode、監視閾値、PID / kill flag パスなどをプロパティで取得可能。妥当性チェック（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE の検証）を含む。
- ポートフォリオ構築ライブラリ（kabusys.portfolio）
  - portfolio_builder.py:
    - select_candidates: BUY シグナルをスコア降順で上位 N 件選択。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分（全スコアが 0 の場合は等金額にフォールバック）。
  - risk_adjustment.py:
    - apply_sector_cap: セクター集中上限を適用して候補をフィルタ（"unknown" セクターは制限適用しない）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（未知レジームは警告ログと共に 1.0 フォールバック）。
  - position_sizing.py:
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づき各銘柄の発注株数を計算。リスクベース算出、単元株丸め（lot_size）、1 銘柄上限・aggregate cap、cost_buffer（手数料・スリッページ見積り）を考慮したスケーリングロジックを実装。
- ユーティリティ
  - utils/logging_setup.py:
    - 共通のログ設定ユーティリティを提供。StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション・30日保持）をルートロガーに設定。
    - LOG_DIR / LOG_LEVEL の解決順を定義し、ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
  - utils/process_priority.py:
    - プラットフォーム差分を吸収するプロセス優先度設定ユーティリティ（Windows の priority class / POSIX の nice 値に対応）。
    - set_cpu_affinity: カレントプロセスを最初の N コアに固定する機能（オプション）。
- DB / 分析
  - DuckDB 統合: 実行エンジン・モニタリングスクリプトで DuckDB 接続を使用する設計になっている（Settings.duckdb_path）。
  - 監視 DB 初期化呼び出し（init_monitoring_db）を run_monitoring / run_execution で行い、監視テーブルが存在することを保証（冪等）。
- パッケージ情報
  - __init__.py にてパッケージバージョンを 0.1.0 として定義。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Notes / Implementation details
- 停止フラグ / Kill Switch:
  - run_execution / run_monitoring はプロジェクト内の data/stop_requested.flag を監視し、ファイルが存在することで安全に停止する設計。run_execution は起動前にフラグが既に立っている場合は起動を中止する。
  - Settings で kill_flag_clear_on_start をサポートし、本番での誤設定に関する警告を validate_config に含めている。
- ペーパートレード分離:
  - paper_trading 環境ではブローカークライアントを MockBrokerClient（ファクトリ経由）に差し替え、SQLite DB を分離することで本番 DB との混同を避ける設計。
- ロギング:
  - ログは標準出力（stdout）へ出力する仕様（cron / Task Scheduler でのリダイレクト運用を想定）。ファイル出力は logs/<app_name>.log に日次ローテーションで保持される。
- research/factor_research.py:
  - ファクター計算モジュール（モメンタム・バリュー・ボラティリティ等）の骨格を追加。DuckDB を使用して prices_daily / raw_financials を参照する想定。ファイル末尾が途中で切れており（実装継続必要）、momentum 計算の実装が途中で終わっている点に注意。

### Known limitations / TODO
- research/factor_research.py が未完（momentum 関数等の完全実装が必要）。
- position_sizing の lot_size は全銘柄共通に固められている（将来的には銘柄別 lot_map への拡張を検討）。
- apply_sector_cap の価格欠損時のフォールバックロジック（注記あり）を改善する余地あり（前日終値や取得原価などの利用検討）。
- logging_setup はログディレクトリ作成失敗時にファイル出力を諦める挙動だが、より詳細なエラー通知/リトライ方針は今後の改善候補。

---

この CHANGELOG はコードベースから推測して作成しています。実際のコミット履歴や設計ドキュメントに基づいて調整してください。