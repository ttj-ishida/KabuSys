CHANGELOG
=========

すべての変更は Keep a Changelog の慣例に従って記載しています。
このファイルは主にコードベース（src/kabusys 以下）から推測して作成した初期リリース向けの変更履歴です。

フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------
（現時点では未リリースの変更はありません）

0.1.0 - 2026-04-24
-----------------

Added
- 基本パッケージと初期機能を追加（初期リリース）。
  - パッケージバージョン: 0.1.0 (src/kabusys/__init__.py)
- 実行スクリプト
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV が paper_trading の場合は paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成を組み込み。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine をスレッドとして実行。停止フラグ（data/stop_requested.flag）や PID ファイル（data/execution.pid）をサポート。
  - run_monitoring.py
    - システム監視ループの起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグ（data/stop_requested.flag）検知、例外発生時のログ捕捉、KeyboardInterrupt のハンドリングを実装。
    - 監視は環境にかかわらず production の sqlite_path を使用する仕様。
- 設定管理
  - config.py
    - .env 自動読み込み（プロジェクトルート検出: .git / pyproject.toml を基準）。
    - .env / .env.local の読み込み順と保護（OS 環境変数は上書きされない）。
    - 多数の設定プロパティを提供（J-Quants / kabuAPI / DB パス / paper_trading 設定 / 監視閾値 / 環境種別 等）。
    - PAPER_FILL_MODE の検証、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、パス類は Path に正規化。
  - config_setup.py
    - 対話式ウィザードで .env を初期作成・更新する CLI を追加。
    - J-Quants・kabu パスワード等のシークレット入力やデフォルト値、説明を提供。
    - .env の読み書きロジックを実装（既存値の再利用、マスク表示、保存確認）。
  - validate_config.py
    - 起動前に .env と config/*.yaml の簡易検証を行う CLI を追加。
    - 必須環境変数の存在チェック、KABUSYS_ENV の値チェック、DB パスの親ディレクトリ存在チェック、YAML の存在とパース検証（PyYAML が導入されている場合）。
    - --strict オプションで警告を FAIL 扱いにできる。
- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py
    - StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーに一括設定する関数を追加。
    - ログレベル・ログディレクトリの解決順、既存ハンドラのクリア、ファイル作成失敗時のフォールバック処理を実装。
  - utils/process_priority.py
    - Windows / POSIX に対応したプロセス優先度設定機能を追加（set_process_priority）。
    - CPU affinity を最初 N コアに固定する set_cpu_affinity を提供。
    - 権限不足や未対応 OS は警告ログでスキップ。
- ポートフォリオ構築 (純粋関数群)
  - portfolio/portfolio_builder.py
    - 株選定・重み付けユーティリティを追加。
      - select_candidates（スコア順の候補抽出）
      - calc_equal_weights（等金額配分）
      - calc_score_weights（スコア加重配分、スコア全0時は等金額にフォールバック）
  - portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap を追加（既存保有のセクター比率に基づく候補除外）。
    - 市場レジームに応じた資金乗数 calc_regime_multiplier を追加（bull/neutral/bear に対応、未知はフォールバックで 1.0）。
    - セクター名が不明な銘柄は除外対象にしない設計。
  - portfolio/position_sizing.py
    - 発注株数計算ロジックを追加（risk_based / equal / score の allocation_method に対応）。
    - 単元株（lot_size）で丸め、per-stock 上限・aggregate 上限（available_cash）を考慮したスケーリング処理を実装。
    - cost_buffer を考慮した保守的見積りと残余キャッシュによる再配分ロジックを搭載。
- 研究・ファクター計算
  - research/factor_research.py
    - DuckDB を用いたファクター計算モジュール（モメンタム・MA200乖離・ATR・流動性等）の骨組みを追加。
    - calc_momentum 等の関数を実装予定（ファイル末尾で実装途中の箇所あり）。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - SQLite の paper_trading DB を解析し、稼働率・注文成功率・送信率・レイテンシ等の指標を出力する CLI を追加。
    - 基準値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）を定義し、PASS/FAIL 判定を行う。
    - --from / --to / --db オプションに対応。
- 監視 DB 初期化
  - monitoring/monitoring_db.py（他モジュール参照）
    - 監視用テーブルの初期化処理を idempotent に保障するための init_monitoring_db を各実行スクリプトから呼び出し。

Changed
- 初期リリースのため、過去バージョンからの変更履歴はありません（ベースライン）。

Fixed
- 初期リリースのため、過去バージョンからの修正履歴はありません（ベースライン）。

Known issues / Notes
- 一部実装が TODO/未完成
  - portfolio/risk_adjustment.apply_sector_cap: price が欠損(0.0) の場合のフォールバック価格未実装（将来的に前日終値などを利用する予定）。
  - portfolio/position_sizing: 銘柄ごとの lot_size を将来サポートする想定（現状はグローバル lot_size を使用）。
  - research/factor_research.py はファイル末尾で実装途中の箇所が見られる（calc_momentum の途中で終端）。
- 設計上の注意
  - run_monitoring は「環境にかかわらず」production 用 sqlite_path を使用する挙動が明記されているため、監視データが本番 DB に記録される点に注意してください。
  - run_execution は paper_trading 環境では専用 DB に記録して本番 DB と完全分離する設計。
  - プロセス優先度の調整や CPU affinity の適用は権限や OS に依存し、失敗した場合はログに警告を出してスキップします。
- 環境変数の自動読み込みはプロジェクトルートを検出できない場合スキップされます。テスト環境等で KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して自動読み込みを無効化可能。

Developer / Ops notes
- CLI 実行例:
  - 環境ウィザード: python -m kabusys.config_setup
  - 設定検証:   python -m kabusys.validate_config [--strict]
  - 監視起動:   python -m kabusys.run_monitoring
  - 実行エンジン: python -m kabusys.run_execution
  - Paper レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- 重要な環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（必須）
  - KABUSYS_ENV（development / paper_trading / live）
  - DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH
  - LOG_LEVEL, LOG_DIR
  - PAPER_FILL_MODE（paper_trading の挙動を制御: instant|partial|never|reject）
- ログ:
  - デフォルトで logs/<app_name>.log に日次ローテーションで出力（30日保持）。LOG_DIR で変更可能。

ライセンス / その他
- 本 CHANGELOG はコードベースの内容から推測して作成したものであり、実際のコミット履歴とは一致しない可能性があります。必要に応じて実際の git コミット履歴やリリース手順に合わせて修正してください。