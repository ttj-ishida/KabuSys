CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
日付はリリース日（このコードベースが作成された想定日）を用いています。

フォーマット:
- [Unreleased] — 今後の変更
- [0.1.0] — 初回リリース（初期実装）

[Unreleased]
------------
- なし（初回リリース）

[0.1.0] - 2026-04-16
-------------------
Added
-----
- 全体
  - プロジェクト初期実装を追加。パッケージ名は kabusys、バージョン 0.1.0。
  - パッケージの公開 API として主要モジュールをエクスポート（portfolio, research, tools, execution, monitoring 等）。

- 設定 / 環境変数読み込み（src/kabusys/config.py）
  - .env / .env.local を自動読み込みする仕組みを実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - 読み込みの優先度: OS 環境変数 > .env.local > .env。テスト用に自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD オプションを提供。
  - .env パーサを実装。export プレフィックス、クォート文字列、バックスラッシュエスケープ、インラインコメントの扱いに対応。
  - 必須環境変数チェック用の _require、各種設定プロパティ（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、PID/kill フラグパス、監視閾値、ログレベル、環境モード等）を実装。
  - PAPER_FILL_MODE の検証（instant/partial/never/reject）と PAPER_TRADING_SQLITE_PATH のサポート。

- 実行スクリプト
  - 実行エンジン起動スクリプト run_execution.py を追加。
    - KABUSYS_ENV が paper_trading の場合は paper_trading 用 SQLite を分離して使用（デフォルト: data/paper_trading.db）。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler 組み立て、ExecutionEngine の起動ロジックを実装。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）を利用した安全停止をサポート。
  - 監視ループ起動スクリプト run_monitoring.py を追加。
    - SystemMonitor の初期化とポーリングループ。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計。
    - stop flag によりループを終了する仕組みを実装。

- 監視 DB 初期化
  - monitoring 用の DB 初期化ユーティリティを組み込む（init_monitoring_db を両スクリプトで呼び出し、監視テーブルの存在を保証）。

- プロセス優先度・CPU 固定ユーティリティ（src/kabusys/utils/process_priority.py）
  - set_process_priority(level) と set_cpu_affinity(cpu_count) を実装。
  - Windows / POSIX (Linux, macOS, FreeBSD) に対する差分吸収とエラーハンドリング（権限不足などを警告として扱う）を実装。

- Portfolio コンポーネント（src/kabusys/portfolio/*）
  - 銘柄選定・配分（portfolio_builder.py）
    - select_candidates: スコア降順で上位 N を選択。タイブレークは signal_rank。
    - calc_equal_weights / calc_score_weights: 等金額配分、スコア加重配分。スコア合計が 0 の場合は等分配にフォールバック（警告ログ）。
  - リスク調整（risk_adjustment.py）
    - apply_sector_cap: 既存保有のセクター比率が上限を超える場合に当該セクターの新規候補を除外。unknown セクターはセクター上限の対象外（除外しない）。
    - calc_regime_multiplier: 市場レジームに基づく投下資金乗数（bull/neutral/bear）を実装。未知レジームは 1.0 でフォールバックし警告出力。
  - ポジションサイジング（position_sizing.py）
    - calc_position_sizes: risk_based / equal / score の allocation_method に対応した株数決定を実装。
    - 単元株（lot_size）丸め、1 銘柄上限（max_position_pct）、総投下上限（max_utilization）や cost_buffer を加味した aggregate cap（スケーリング）処理を実装。
    - 価格欠損時のスキップ、利用可能資金超過時のスケールダウンと残差処理（lot 単位での再配分）を実装。

- リサーチ / ファクター計算（src/kabusys/research/*）
  - factor_research.py
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離を DuckDB 上で算出。データ不足時の None 処理。
    - calc_volatility: ATR(20), 相対 ATR, 20 日平均売買代金・出来高比率を計算。true_range の NULL 伝搬制御による厳密な扱い。
    - calc_value: raw_financials から最新の財務データを結合して PER / ROE を計算（EPS が 0/NULL の場合は None）。
  - feature_exploration.py
    - calc_forward_returns: 複数ホライズン（デフォルト: 1,5,21 営業日）に対する将来リターン計算を実装。horizons の入力検証あり。
    - calc_ic: スピアマンのランク相関による IC 計算（同順位は平均ランク処理、3 レコード未満は None）。
    - factor_summary / rank: 基本統計量、ランク化ユーティリティを実装。
  - research/__init__.py で必要関数をエクスポート。
  - 実装方針として DuckDB を用い、外部ライブラリ（pandas 等）に依存しない純粋 Python + SQL 実装。

- AI ニュース NLP（src/kabusys/ai/news_nlp.py、未完）
  - OpenAI（gpt-4o-mini）を用いたニュースセンチメントスコアリングの設計と実装（バッチ処理、JSON Mode、スコアクリッピング、リトライ／バックオフ制御、トークン肥大化対策）。
  - タイムウィンドウの計算（target_date に対する前日 15:00 JST 〜 当日 08:30 JST 相当の UTC 範囲）。
  - API キー解決ロジック（api_key 引数 or 環境変数 OPENAI_API_KEY）。未設定時は ValueError。
  - 実装ファイルは途中で切れており、_fetch_articles 等の内部実装は継続が必要（現状で部分的に機能）。

- ツール（src/kabusys/tools/paper_verification_report.py）
  - Paper Trading 検証レポート生成スクリプトを実装。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率、リスク却下数、レイテンシ（avg/max/P95）。
    - パス/フィルタ: --from / --to（YYYY-MM-DD）、--db で SQLite パス指定可能。PAPER_TRADING_SQLITE_PATH 環境変数と連携。
    - P95 計算、欠損データの安全処理、基準値（閾値）を定義して PASS/FAIL を判定。
    - DB が存在しない場合はエラーメッセージを表示して終了。

Changed
-------
- なし（初回リリース）

Fixed
-----
- なし（初回リリース）

Deprecated
----------
- なし（初回リリース）

Removed
-------
- なし（初回リリース）

Security
--------
- OpenAI の API キーを環境変数で管理する想定。キー未設定時は明示的にエラーを出すように実装。

Migration notes / 運用上の注意
----------------------------
- 環境モード
  - KABUSYS_ENV は development / paper_trading / live のいずれかを指定。無効な値は ValueError。
  - paper_trading モードでは発注系は専用の paper DB（PAPER_TRADING_SQLITE_PATH）へ記録され、本番 DB と完全に分離される。
  - 監視 (run_monitoring) は environment に依存せず settings.sqlite_path（本番用）を使用する仕様。

- DB
  - デフォルトの SQLite ファイルパス:
    - 監視: data/monitoring.db
    - paper_trading: data/paper_trading.db
  - DuckDB のデフォルトパス: data/kabusys.duckdb
  - init_monitoring_db() を起動時に呼び出して監視テーブルの存在を保証する。

- プロセス制御
  - 実行/監視プロセスは起動時に set_process_priority("high") を呼び出す。OS や権限により設定できない場合は警告を出す。
  - 停止フラグ: data/stop_requested.flag（存在を検知して安全停止）。
  - 実行エンジンの PID は data/execution.pid に書き込まれる想定。

- 環境変数の自動ロード
  - プロジェクトルートが特定できれば .env/.env.local を自動的に読み込む。
  - OS 側の既存環境変数は保護され、.env.local の override は行われるが OS の変数は上書きされない。
  - 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

- MONITOR_POLL_INTERVAL
  - run_monitoring で MONITOR_POLL_INTERVAL を環境変数で上書き可。1 秒未満や不正値はデフォルト 60 秒へフォールバック。

- AI ニュース NLP
  - 実装はリトライやレスポンス検証、部分更新（対象 code のみ置換して他の既存スコアを保護）などを考慮した堅牢設計だが、ファイルが途中で切れているため _fetch_articles 等の処理は未完。実運用前に該当箇所を完成させる必要あり。

今後の TODO / 改善案
-------------------
- ai/news_nlp.py の残り実装（記事取得・バッチ送信・レスポンス統合ロジック）を完成させる。
- エラーハンドリングの一貫性向上（各モジュールでの例外種類やログレベルの統一）。
- position_sizing の lot_size を銘柄別にサポートする拡張（stocks マスタの導入）。
- セクター暴露計算における price 欠損時のフォールバック（前日終値や取得原価を利用）を導入。
- テストの充実（ユニット/統合テスト、特に DuckDB クエリ周りと risk / sizing ロジック）。

署名
----
この CHANGELOG は提供されたソースコードから推測して作成しています。実際のコミット履歴やチケットに紐づく詳細な変更ログはプロジェクトの VCS 履歴（git log 等）を参照してください。