Keep a Changelog
=================
すべての可視的な変更を記録します。  
このファイルは Keep a Changelog 準拠の形式で記載されています。  
比較的最近導入された内容を、リリース単位で日本語でまとめています。

フォーマット
-----------
各リリースは次のカテゴリに分けて記載しています: Added, Changed, Fixed, Deprecated, Removed, Security。  
バージョン番号は PEP 440 準拠で管理されています。

Unreleased
----------
（現在の開発ブランチに対する未リリースの変更点があればここに記載します）

0.1.0 - 2026-04-18
-----------------
Added
- 基本アプリケーション構成を追加
  - パッケージの初期バージョンを定義（kabusys.__version__ = "0.1.0"）。
- CLI / 起動スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。プロセス優先度設定、DB接続、ブローカークライアント生成、ExecutionEngine の起動／停止監視機構を実装。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - ストップフラグ（data/stop_requested.flag）検知で安全に停止。
    - 実行用 PID ファイル data/execution.pid を使用。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番の sqlite_path（デフォルト: data/monitoring.db）を使用して初期化。
    - 停止フラグ検知でポーリングループを終了。
- 環境設定・検証ツール
  - config_setup.py: 対話式 .env ウィザードを追加（.env の初期作成・更新を支援）。
    - 入力補助、既存 .env の読み込み、secret 値のマスク表示、保存時確認などを実装。
  - validate_config.py: 起動前の設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パス・config/*.yaml の存在確認、本番時の追加ガード等。
    - --strict オプションで警告をエラー扱いにできる。
- 設定管理
  - config.py: 環境変数読み込み・アクセスラッパーを追加。
    - プロジェクトルート（.git または pyproject.toml）を起点として .env/.env.local を自動ロード（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）。
    - Settings クラスを提供し、各種設定（J-Quants, kabu API, DB パス, PAPER_FILL_MODE, PID/kill flag パス, 閾値等）をプロパティで取得可能。
    - PAPER_FILL_MODE の有効値検証、KABUSYS_ENV の有効値検証、LOG_LEVEL 検証を実装。
- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。
    - stdout StreamHandler と 日次ローテートの TimedRotatingFileHandler（デフォルト logs/、30日保持）をルートロガーに設定。
    - ログレベル・ログディレクトリの解決順を定義。
  - utils/process_priority.py: プロセス優先度（および CPU affinity）設定ユーティリティを追加。
    - Windows と POSIX 系を吸収する実装（psutil を使用）。アクセス権限不足時は警告を出してスキップ。
- Portfolio（ポートフォリオ構築）モジュール
  - portfolio.portfolio_builder.py: 候補選定（select_candidates）と重み計算（calc_equal_weights、calc_score_weights）を追加。
  - portfolio.risk_adjustment.py: セクター集中制限（apply_sector_cap）とレジーム乗数（calc_regime_multiplier）を追加。
  - portfolio.position_sizing.py: 株数算出ロジック（risk_based / equal / score）を追加。単元株（lot_size）丸め、aggregate cap のスケーリング、cost_buffer を考慮した調整等を実装。
  - portfolio.__init__.py で上記関数群を公開。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py を追加。ペーパートレード用 SQLite（環境変数 PAPER_TRADING_SQLITE_PATH）から実績を集計してレポート出力。
    - システム稼働率（uptime）、注文成功率（fill rate）、送信率、API レイテンシ（avg/max/P95）などを計算し、閾値に基づく PASS/FAIL 判定を行う。
    - --from / --to / --db オプションをサポート。
- Research（解析）モジュール（初期実装）
  - research/factor_research.py: ファクター計算の骨子を追加（モメンタム、MA200乖離、ATR、出来高等の指標を DuckDB 上で計算する設計）。
    - 設計方針、定数、calc_momentum の関数シグネチャなどを実装開始（DuckDB 接続を受け取る設計）。
- DB 初期化フック
  - monitoring.monitoring_db.init_monitoring_db を各スクリプトから呼び出して監視テーブルが存在することを保証（冪等に作成）。

Changed
- プロジェクト構成とデフォルトパス
  - データ・ログ関連のデフォルトパスを明示（data/*.db, logs/*.log）。
  - run_execution/run_monitoring が適切な DB（paper_trading と本番）を選択して接続するように整理。
- ロギングの統一
  - setup_logging() により全スクリプトで一貫したログフォーマット・ローテーションを使用するように変更。

Fixed
- 環境読み込みの堅牢化
  - .env パースで export プレフィックス・クォート・インラインコメント等に対応するように改善。
  - .env ファイル読み込み失敗時に警告を出してスキップするように改善。

Deprecated
- （なし）

Removed
- （なし）

Security
- 秘密情報の扱い
  - config_setup の出力ではシークレットはファイルに書かれるが、README 等でも .env は絶対に Git にコミットしない旨を明記（生成ヘッダに注意書きあり）。

Notes / 重要な実行時挙動
- KABUSYS_ENV
  - 有効値: development, paper_trading, live。無効値はエラーを投げる／検出される。
  - paper_trading は本番 DB と分離された SQLite（PAPER_TRADING_SQLITE_PATH）を使う。
- MONITOR_POLL_INTERVAL
  - run_monitoring のポーリング間隔を秒単位で上書き可。1 未満・不正値はデフォルト 60 秒にフォールバック。
- PAPER_FILL_MODE
  - ペーパートレードの約定振る舞いを制御（instant|partial|never|reject）。不正値は ValueError。
- Kill / Stop フラグ
  - data/stop_requested.flag で各起動スクリプトが優雅に停止するよう設計。実行時に stop フラグが既に立っている場合は実行を行わず終了する処理を含む。
- ログ出力
  - デフォルトは logs/<app_name>.log を日次ローテーションで出力（30 日保持）。ログディレクトリ作成に失敗した場合はコンソールのみで出力。
- process priority / CPU affinity
  - set_process_priority("high") が主要スクリプトで呼ばれる。権限不足時は警告して続行。

CLI / 実行例
- 環境ウィザード: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- Paper Trading レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- 実行スクリプト（直接実行可能）
  - python src/kabusys/run_monitoring.py
  - python src/kabusys/run_execution.py

既知の制約 / TODO
- 一部モジュールは設計の骨子のみで、完全な実装（例: research/factor_research の内部処理や一部 execution/* の実装詳細）は別途実装・テストが必要。
- position_sizing の lot_size 固定（現在はグローバル 100 を想定）→ 将来的に銘柄ごとの単元対応を検討。
- apply_sector_cap で price が欠損（0.0）の場合にエクスポージャーが過少見積りされる問題が注記されており、前日終値等のフォールバック導入を検討中。

開発者向け補足
- 自動 .env 読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化でき、テスト時に便利です。
- settings オブジェクトは kabusys.config.settings からインポートして使用できます。
- ロガーの再設定は setup_logging() を呼ぶと既存ハンドラをクリアしてから再設定します（多重ハンドラ防止）。

お問い合わせ / 貢献
-------------------
バグ報告・機能提案・プルリクエストはリポジトリの Issue / PR を利用してください。README に運用上の注意（.env の管理、API トークンの保護など）を追記することを推奨します。