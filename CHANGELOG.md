CHANGELOG
=========

すべての変更は Keep a Changelog のスタイルに従って記載しています。
このファイルはリポジトリの現状のコードベースから推測して作成した変更履歴です。

フォーマット:
- Unreleased は将来の変更用のプレースホルダです。
- 各リリースは主要な変更カテゴリ（Added / Changed / Fixed / Removed / Security）で整理しています。

Unreleased
----------

- なし

0.1.0 - 2026-04-23
------------------

Added
- 基本アプリケーションバージョンを導入
  - パッケージ版情報: __version__ = "0.1.0" を設定。

- 実行用スクリプト
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は専用の paper_trading DB（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全に分離。
    - BrokerClientFactory を用いてブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - 起動時にプロセス優先度を "high" に設定。停止フラグ (data/stop_requested.flag) を検知すると安全に停止する。
    - PID ファイル (data/execution.pid) を利用。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト: 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番の sqlite_path を使用して監視テーブルを初期化。
    - 停止フラグ (data/stop_requested.flag) を検知してループを終了。
    - プロセス優先度を "high" に設定。

- 設定管理・検証・ウィザード
  - config.py
    - .env 自動ロード機能を導入（.env, .env.local の順でロード。OS 環境変数は保護）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
    - .env パースは export プレフィックス、クォート、エスケープ、インラインコメント等を考慮する堅牢な実装。
    - Settings クラスを導入し、主要な設定値（DB パス、API トークン、LINE 設定、監視閾値、環境判定など）をプロパティ経由で提供。
    - Paper Trading 向けの設定（paper_sqlite_path、paper_fill_mode）をサポート。
    - 環境値のバリデーション（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等）。

  - validate_config.py
    - .env と config/*.yaml を起動前に検証する CLI を追加。
    - 必須環境変数の存在チェック、KABUSYS_ENV や LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、YAML のパースチェック（PyYAML が存在する場合）、本番環境向けの追加ガード等を実装。
    - --strict オプションで警告を FAIL 扱いにできる。

  - config_setup.py
    - .env の初期作成・更新を対話式で支援するウィザードを追加。
    - J-Quants / kabu API トークン等の必須項目、ログディレクトリや DB パスなど主要項目のプロンプトと .env への書き込みを提供。
    - 既存 .env の読み込み＆既存値の再利用、シークレットのマスク表示に対応。

- ログ・プロセスユーティリティ
  - utils/logging_setup.py
    - 統一的なログ設定ユーティリティを追加。
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、既定 30 日分保持）をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR 等の環境変数または引数で挙動を変更可能。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。

  - utils/process_priority.py
    - プロセス優先度設定ユーティリティを追加。
    - Windows（psutil の優先度定数）および POSIX（nice 値）を吸収し、呼び出し元はプラットフォームを意識せず使用可能。
    - set_process_priority(level)（high/normal/low）と set_cpu_affinity(cpu_count) を提供。
    - 実行権限不足や未対応 OS の場合は警告を出して安全にスキップ。

- ポートフォリオ構築モジュール（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定（select_candidates: スコア降順、タイブレークは signal_rank）を実装。
    - 等金額配分（calc_equal_weights）とスコア加重配分（calc_score_weights）。全銘柄スコアが 0 の場合は等分にフォールバックして警告出力。

  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）を実装。既存ポジションのセクター比率が上限を超える場合に当該セクターの新規候補を排除（"unknown" セクターは除外しない）。
    - 市場レジームに応じた乗数（calc_regime_multiplier）を実装（bull:1.0, neutral:0.7, bear:0.3）。未知レジームは 1.0 にフォールバックして警告。

  - portfolio/position_sizing.py
    - 株数決定ロジック（calc_position_sizes）を実装。
    - allocation_method に "risk_based", "equal", "score" をサポート。
    - lot_size（単元株）を考慮した丸め、1 銘柄上限（max_position_pct）、投下資金上限（max_utilization）、cost_buffer を考慮した aggregate cap とスケールダウン・端数処理を実装。
    - 価格欠損時のスキップやログ出力など堅牢性を考慮。

- 解析・ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、P95 レイテンシ等を集計して PASS/FAIL 判定を出力。
    - 既定の基準値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）を設定。
    - --from / --to / --db オプションで期間・データベースを指定可能。

- リサーチ（ファクター計算）基礎
  - research/factor_research.py（部分実装）
    - Momentum（1M/3M/6M・MA200乖離率）、Volatility（ATR）、Liquidity、Value（raw_financials 由来）等の計算を行う設計を導入。
    - DuckDB 接続を受けて prices_daily / raw_financials を参照する方針で、結果は (date, code) をキーとする dict リストで返す設計。
    - モメンタム計算（calc_momentum）の実装開始（ファイル末尾が切れているため実装途中）。

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Notes / 実装上の注意点
- .env 自動読み込みはデフォルトで有効。テスト等で無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- run_monitoring は監視 DB として Settings.sqlite_path（本番用）を使用する設計です。環境に依らず監視情報を本番 DB に記録することに留意してください。
- run_execution は paper_trading 環境時に paper_sqlite_path を使い本番 DB と分離します。
- process_priority / CPU affinity の設定は権限や OS に依存して失敗する可能性があります。その場合はログに警告を出して続行します。
- research/factor_research.py は実装途中のため、現在はモメンタム計算の途中でファイルが終端しています。完成に向けた追加実装が必要です。

今後の TODO（コードから推測）
- research/factor_research の残り実装（ファクター群の完全実装と Z スコア正規化との統合）。
- 銘柄別 lot_size のサポート（将来的にマスタから取得する形への拡張）。
- position_sizing のコスト見積り（手数料・スリッページ）の更なる整備。
- モニタリング・実行の E2E テストとリリース時の運用ドキュメント整備。

ライセンスやセキュリティ修正等はこのリリースからは判明していません。必要に応じて実際の変更履歴を追記してください。