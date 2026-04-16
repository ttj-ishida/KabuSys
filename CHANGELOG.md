CHANGELOG
=========

すべての変更は Keep a Changelog（https://keepachangelog.com/）の形式に準拠して記載しています。  
主にコードベースの初期リリース相当の追加と各種実装の概要をまとめています（コードから推測して作成）。

Unreleased
----------
- なし

[0.1.0] - 2026-04-16
--------------------
Added
- コア: KabuSys 初期実装を追加。
  - パッケージバージョンを 0.1.0 に設定（src/kabusys/__init__.py）。
- 設定管理（src/kabusys/config.py）
  - .env 自動ロード機能を追加（プロジェクトルートを .git または pyproject.toml から検出して .env / .env.local を読み込み）。KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可。
  - .env のパースを強化（export 形式、クォート・エスケープ、インラインコメントの扱い、保護付きキーによる上書き制御）。
  - 各種設定プロパティを提供（例: DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH 等）。
  - 環境変数のバリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）。不正値は明確な例外で通知。
- 実行スクリプト
  - 実行用: src/kabusys/run_execution.py
    - ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite を使用して実行を本番 DB から分離。
    - BrokerClientFactory を介したブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を実行。
    - デフォルト RiskConfig を実装（max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20）。初期ポートフォリオ値は broker.get_available_cash() から取得。
    - execution.pid / stop_requested.flag による起動・停止制御、スレッドでのエンジン実行と安全なシャットダウン処理を実装。
  - 監視用: src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔の上書き（デフォルト 60 秒）。0 以下や無効値はデフォルトにフォールバックして警告出力。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計。
    - プロセス優先度を起動時に "high" に設定する呼び出しを追加。
- 監視 DB 初期化ユーティリティ（init_monitoring_db の呼び出しを起動時に行い監視テーブルの存在を冪等に保証）。
- ポートフォリオ構築（src/kabusys/portfolio/）
  - 候補選定と重み付け: select_candidates, calc_equal_weights, calc_score_weights（スコア全て 0 の場合は等配分へフォールバック）。
  - セクター集中制限・レジーム乗数: apply_sector_cap, calc_regime_multiplier（"bull"/"neutral"/"bear" のマッピング、未知レジームは警告して 1.0 でフォールバック）。
  - ポジションサイズ算出: calc_position_sizes
    - risk_based / equal / score の割当方式に対応。
    - 単元株（lot_size）丸め、1銘柄上限・合計投下上限（available_cash）を考慮したスケーリング・再配分ロジックを実装。
    - cost_buffer による手数料・スリッページ見積り、価格欠損時のスキップ等の防御的実装。
- リサーチ（src/kabusys/research/）
  - ファクター計算: calc_momentum, calc_volatility, calc_value（DuckDB を用いた prices_daily / raw_financials のクエリ実装）。
  - 研究用ユーティリティ: calc_forward_returns, calc_ic（Spearman ランク相関）、factor_summary, rank。外部ライブラリに依存せず標準ライブラリのみで実装。
- ツール（src/kabusys/tools/paper_verification_report.py）
  - Paper Trading 検証レポート生成スクリプトを追加。稼働率・注文成功率・送信率・P95 レイテンシなどを算出し PASS/FAIL を判定。
  - DB が存在しない場合やテーブル欠損時の例外処理を実装。
- AI ニュース NLP（src/kabusys/ai/news_nlp.py）
  - raw_news を OpenAI（gpt-4o-mini）でスコアリングするモジュールを追加（ニュースウィンドウ計算、API バッチ送信設計、スコアのクリップ等の方針と定数を定義）。
  - API キー未設定時は明示的にエラーを出すバリデーションを実装。
  - （備考）コードはスコア処理の途中まで実装されている（fetch/送信/書き込みのフローは設計済み、実装継続想定）。
- ユーティリティ（src/kabusys/utils/process_priority.py）
  - プロセス優先度設定（Windows / POSIX を吸収）、CPU affinity 設定ユーティリティを追加。権限不足や未サポート環境では警告してスキップするよう堅牢化。

Changed
- 監視の挙動
  - 監視プロセスは KABUSYS_ENV に依存せず production の sqlite_path を参照する（run_monitoring の仕様説明）。Paper トレード DB との明確な分離を意図した設計。
- 起動時のプロセス優先度をデフォルトで "high" に設定するように変更（run_execution / run_monitoring）。
- .env 読み込みの優先度:
  - OS 環境変数 > .env.local > .env の順で適用し、既存 OS 環境は protected として上書きされないように変更。

Fixed
- 設定パーサの堅牢化（config._parse_env_line）
  - クォート内のバックスラッシュエスケープ、export 形式、インラインコメントの取り扱い改善により .env の誤解釈を低減。
- MONITOR_POLL_INTERVAL の不正値処理（run_monitoring._get_poll_interval）
  - 0 や負の数、非数が設定されている場合に警告を出しデフォルトへフォールバックして ValueError を回避。
- Research / Tools / SQL クエリでの欠損データ対応
  - テーブルやカラムが存在しないケース（OperationalError）を捕捉してレポート生成や集計が部分的に失敗してもクラッシュしないように実装。

Security
- なし（今回の差分からは特別なセキュリティ修正は検出できません）。ただし、OpenAI API キー等の機密情報は環境変数で管理する設計。

Notes / Upgrade
- 新規 / 重要な環境変数:
  - KABUSYS_ENV (development|paper_trading|live)
  - MONITOR_POLL_INTERVAL (監視ポーリング間隔, 秒)
  - KABUSYS_DISABLE_AUTO_ENV_LOAD (1 で .env の自動読み込みを無効化)
  - PAPER_FILL_MODE (instant|partial|never|reject)
  - PAPER_TRADING_SQLITE_PATH (paper trading 用 DB パス)
  - DUCKDB_PATH / SQLITE_PATH / LOG_LEVEL / PID_FILE_PATH / KILL_FLAG_PATH 等
- 注意点:
  - run_monitoring は常に production 用 SQLITE_PATH を使います。テスト用途で監視を分離したい場合は環境変数で SQLITE_PATH を変更してください。
  - paper_trading を使うと実行エンジンは paper_trading 用 DB を使用します（本番 DB との完全分離を目的）。
  - AI ニュース NLP は API 連携の実装途中の箇所が存在するため、本番運用前に完全実装とテストが必要です。

Acknowledgments
- 各モジュールは外部 API（ブローカー / OpenAI）への直接接続を想定しています。テストや CI ではモック化する設計を推奨します。

----