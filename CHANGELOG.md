# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。  
バージョン番号はパッケージ内の __version__（0.1.0）に基づきます。

全般的な注記
- このチェンジログは与えられたコードベースから実装内容を推測して作成しています。実際のコミット履歴ではなく、コードで実装されている機能・振る舞いをまとめたものです。

Unreleased
- （なし）

0.1.0 - 2026-04-19
------------------

Added
- 実行スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - プロセス優先度を高く設定して起動する。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用の専用 SQLite DB を使用し、本番 DB と完全に分離する（PAPER_TRADING_SQLITE_PATH またはデフォルト data/paper_trading.db）。
    - ブローカークライアントを BrokerClientFactory から生成し、OrderRepository、OrderManager、RiskManager、Reconciler 等の依存コンポーネントを組み立てて ExecutionEngine を起動する。
    - 停止フラグ（data/stop_requested.flag）検知により安全に停止するロジックを備える。PID ファイルの取り扱いあり。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバック。
    - Monitoring は環境にかかわらず本番用 sqlite_path を使用して監視テーブルを初期化する。
    - 停止フラグ検出、例外ハンドリング、接続クリーンアップ処理を実装。

- 設定・環境管理
  - config.py: Settings クラスを追加。
    - .env 自動ロード機能（プロジェクトルートの検出: .git または pyproject.toml を探索）。
    - .env のパースは export 句、クォート付き値、エスケープ、インラインコメント等に対応した堅牢な実装。
    - 各種設定プロパティ（J-Quants / kabu API / DB パス / PID, kill flag, thresholds, env/log level 判定など）を提供。
    - 環境種別（development / paper_trading / live）の検証と bool ヘルパー（is_live, is_paper, is_dev）。

  - config_setup.py: 対話式 .env ウィザードを追加。
    - 初期 .env 作成・更新を支援。シークレットはマスクして表示。
    - デフォルト値・選択肢・説明付きの対話プロンプト、保存確認、.env ファイル出力機能を実装。

  - validate_config.py: 設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、LOG_LEVEL、DB パスの親ディレクトリ確認、config/*.yaml の存在確認および PyYAML があればパース検証、live 環境用の追加ガード（LINE 通知設定・KILL_FLAG_CLEAR_ON_START 警告）を実装。
    - --strict オプションで警告を失敗として扱う。

- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py: 候補選定および重み計算（等配分、スコア加重）を追加。
    - select_candidates: スコア降順、同点時は signal_rank でタイブレーク。
    - calc_equal_weights / calc_score_weights: スコアが全て 0 の場合はデフォルトで等配分へフォールバック。
  - portfolio/risk_adjustment.py: セクター集中の上限適用ロジックとレジームに応じた乗数を追加。
    - apply_sector_cap: 既存保有のセクターエクスポージャーから新規候補を除外する仕組み（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: "bull"/"neutral"/"bear" に基づく資金乗数（既定値とフォールバック）を提供。
  - portfolio/position_sizing.py: 発注株数決定ロジックを追加。
    - 複数の allocation_method（"risk_based", "equal", "score"）に対応。
    - lot_size（単元株）丸め、per-position 上限・aggregate cap（available_cash に基づくスケールダウン）、コストバッファ考慮、スケールダウン時の端数処理（fractional remainder による追加配分）を実装。
  - portfolio/__init__.py で主要関数を公開（select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier）。

- ユーティリティ
  - utils/logging_setup.py: 統一ロギング設定ユーティリティを追加。
    - stdout への StreamHandler と、日次ローテート（TimedRotatingFileHandler）でログファイル出力（logs/<app_name>.log）を設定。
    - 既存ハンドラのクリア処理、ログディレクトリ作成失敗時のフォールバック（コンソールのみ）を実装。
    - ログレベル / ログディレクトリの解決順を定義。
  - utils/process_priority.py: クロスプラットフォームなプロセス優先度設定を追加。
    - Windows / POSIX 系（Linux, macOS, FreeBSD）に対応した nice / priority 設定。失敗時は警告を出しスキップ。
    - CPU affinity を最初の N コアに固定する関数 set_cpu_affinity を実装（例外時は警告でスキップ）。

- ツール
  - tools/paper_verification_report.py: Paper Trading 向け検証レポート作成スクリプトを追加。
    - システム稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均 / 最大 / P95）を集計して表示。
    - 閾値をベースに PASS/FAIL 判定を行う（稼働率 99%、成立率 90% などの基準を実装）。
    - --from / --to / --db オプションで期間・DB パスを指定可能。PAPER_TRADING_SQLITE_PATH 環境変数にも対応。

- 研究モジュール（骨格）
  - research/factor_research.py: ファクター計算モジュールの基礎を追加。
    - モメンタム、MA200 乖離、ATR、出来高/流動性などの定数と calc_momentum のインターフェイス骨格を用意（DuckDB 接続を受ける設計）。
    - 実装は DuckDB の prices_daily / raw_financials テーブルを参照する想定。

Changed
- ログ出力の統一化
  - すべての起動スクリプトは setup_logging を呼んで stdout と日次ローテーションログを利用する設計に統一。

- DB 周りの設計方針整理
  - 監視（monitoring）用は環境に依らず本番 sqlite_path を使用して監視テーブルを初期化する設計。
  - 実行（execution）は paper_trading 環境で専用 DB を切り替えることで本番 DB と分離。

Fixed
- .env の読み込み堅牢化
  - export プレフィックス、シングル／ダブルクォート、バックスラッシュエスケープ、行末のコメント処理などに対応し、より堅牢に .env をパースして環境変数をセットするよう改善。

- ロギングのフォールバック
  - ログディレクトリ作成に失敗した場合でもプロセスが停止しないようにファイルハンドラ作成失敗を catch して stdout のみで継続するように実装。

- プロセス優先度設定の安全化
  - 権限不足や非対応プラットフォームでの例外をキャッチし、警告ログを出して処理を継続するように修正。

Known issues / Notes
- research/factor_research.calc_momentum: コードが途中で切れている／骨格のみの状態（詳細実装は未完）。計算ロジックは DuckDB を用いる設計になっているため、実データ・テーブル構成に合わせた実装が必要。
- 一部 TODO コメントあり（例: position_sizing の銘柄別 lot_size 拡張や risk_adjustment の価格フォールバックなど）。
- 実運用環境（KABUSYS_ENV=live）では LINE 通知設定や Kill Switch の運用方針に注意（validate_config で警告を出すガードあり）。

以上。必要であればリリースノートを英語版やセクション分割（実装者向け / 運用者向け）で整形できます。どの程度の粒度で詳細化するか指示ください。