KEEP A CHANGELOG 準拠 — 変更履歴 (日本語)
====================================

フォーマット: Keep a Changelog (https://keepachangelog.com/ja/1.0.0/)

Unreleased
----------
（なし）

[0.1.0] - 2026-04-17
-------------------

Added
- パッケージ初期リリース: kabusys v0.1.0
  - __version__ を 0.1.0 に設定 (src/kabusys/__init__.py)。

- 起動スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグファイル data/stop_requested.flag を検知して安全にループ終了。
    - 常に本番用 sqlite_path を監視 DB に使用する設計。
    - プロセス優先度を高（"high"）に設定して開始。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時に paper_trading 用 SQLite（data/paper_trading.db）を使用して本番 DB と完全分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組立て。
    - エンジンはスレッドで実行、停止フラグで安全に停止。PID ファイル管理。

- 設定・環境読み込み
  - config.py: Settings クラスを実装。
    - .env 自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - .env / .env.local の読み込み順と OS 環境変数保護（上書き防止）を実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
    - .env のパースが強化（export 句対応、クォート内のエスケープ、インラインコメント処理等）。
    - 各種環境設定プロパティを提供（J-Quants, kabuAPI, LINE, DB パス, PID/kill フラグパス, 監視閾値等）。
    - PAPER_FILL_MODE の検証（instant/partial/never/reject）。
    - KABUSYS_ENV の検証（development / paper_trading / live）。

- ポートフォリオ構築（純粋関数群）
  - portfolio_builder.py
    - select_candidates: BUY シグナルのスコア順ソート・上位 N 選出。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア正規化配分（ゼロスコア時は warning と等金額フォールバック）。
  - risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェック（既存保有のセクター時価比率に応じて新規候補を除外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す。
  - position_sizing.py
    - calc_position_sizes: risk_based / equal / score の割当方式に対応。単元株（lot_size）丸め、per-stock 上限・aggregate cap (available_cash)、cost_buffer による保守的見積りとスケーリングアルゴリズムを実装。

- 研究・ファクタ計算
  - research/factor_research.py
    - calc_momentum: mom_1m/mom_3m/mom_6m と MA200 乖離率を DuckDB の prices_daily から計算。
    - calc_volatility: ATR(20), ATR 比率、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials と prices_daily を組み合わせて PER/ROE を計算。
    - データ不足に対する安全な None フォールバックを実装。
  - research/feature_exploration.py
    - calc_forward_returns: 複数ホライズン（デフォルト 1,5,21）の将来リターンを一括取得。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。利用可能レコードが 3 未満なら None。
    - rank / factor_summary: ランク付け・基本統計量集計を標準ライブラリのみで実装。
  - research/__init__.py にエクスポートを整備（zscore_normalize を data.stats から再エクスポート）。

- AI ニュース NLP（下準備・主要機能）
  - ai/news_nlp.py
    - ニュース収集ウィンドウ計算 (calc_news_window) を追加（JST ベースのウィンドウを UTC naive datetime で返却）。
    - score_news の設計方針と一部実装を追加（OpenAI API を用いた銘柄別センチメント集約・バッチ送信・リトライ・レスポンス検証・スコアクリップ等。関数内で API キー解決・例外ハンドリングを行う）。
    - バッチサイズ、モデル(gpt-4o-mini)、スコアクリップ、トークン肥大対策等の定数化。

- ユーティリティ
  - utils/process_priority.py
    - set_process_priority(level): Windows / POSIX を吸収するプロセス優先度設定ユーティリティ（psutil 利用）。
    - set_cpu_affinity(cpu_count): 指定コア数にプロセスをピン留めする機能（アクセス権限等の失敗時は警告でスキップ）。
    - 不正パラメータや権限不足に対する適切な例外・警告処理を追加。

- 運用ツール
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成ツールを追加。
    - システム稼働率、注文成功率、送信率、リスク却下数、レイテンシ (avg/max/P95) を DB から集計して CLI で出力。
    - 閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200 ms）と Pass/Fail 判定を実装。
    - --from / --to / --db CLI オプションを提供。PAPER_TRADING_SQLITE_PATH 環境変数を利用可能。

Changed
- 設計上の注意点・挙動明示
  - run_monitoring: 監視プロセスは KABUSYS_ENV にかかわらず本番 sqlite_path を使用する（監視データを本番 DB で一元管理する意図）。
  - .env の自動読み込みはプロジェクトルートが特定できない場合にスキップされるように変更（配布後の CWD 非依存性を確保）。

Fixed
- 耐障害性の改善
  - 各種集計/計算関数はデータ不足時に安全に None を返す/空リストを扱うように実装（例: p95 計算、factor_summary、calc_ic、trade_logs のクエリ等）。
  - 環境変数の数値パース失敗時にデフォルトにフォールバックして警告を出すように改善（MONITOR_POLL_INTERVAL の扱い等）。
  - psutil を使った優先度/affinity 設定でアクセス拒否・未実装例外を捕捉してスキップし、ログ出力するようにした。

Deprecated
- なし

Removed
- なし

Security
- OPENAI_API_KEY の取り扱いは明示（score_news の api_key 引数または環境変数に依存）。API キー未設定時は ValueError を送出して明示的に失敗。

補足
- 多くの機能は DuckDB / SQLite のテーブル（prices_daily / raw_financials / trade_logs / system_status / raw_news / news_symbols / ai_scores 等）を前提としています。これらのスキーマ／初期化は monitoring_db / SystemMonitor / ExecutionEngine 等の別モジュールで扱われる設計です（当リリースで参照のみ）。
- ai/news_nlp.py は主要な処理フローを記述していますが、ファイル末尾でトランケーションが見られる箇所があるため、完全実装は継続作業がある可能性があります。

今後の予定（例）
- ai/news_nlp の完全実装とテストカバレッジ拡充
- SystemMonitor / monitoring_db / ExecutionEngine 周りの統合テスト
- 単体テストと CI の導入、ドキュメント（API レファレンス・運用手順）の整備

------------------------------------
この CHANGELOG はコード内のドキュメント・実装から推測して作成しています。必要であればリリース日・文言の修正や項目の追加を行います。