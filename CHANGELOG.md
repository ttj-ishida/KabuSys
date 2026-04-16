CHANGELOG
=========

すべての重要な変更点はここに記載します。本ファイルは Keep a Changelog の慣習に従います。

フォーマット:
- Unreleased — 今後の変更予定
- 各リリースは日付付きで記載

Unreleased
----------
（現時点で未リリースの変更はありません）

0.1.0 - 2026-04-16
-----------------

初回リリース。以下の主要機能と実装を含みます。

Added
- 基本パッケージ情報を追加
  - パッケージバージョンを __version__ = "0.1.0" に設定。
- 環境設定管理
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルート自動検出、OS環境変数優先、.env.local は override=True）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - .env ファイル行パーサを実装（export 形式、シングル/ダブルクォート、エスケープ、インラインコメント処理に対応）。
  - Settings クラスを導入し、各種環境変数へのアクセスをプロパティで提供（DB パス、API トークン、監視閾値など）。未設定の必須変数は ValueError を送出。
  - KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE 等の検証ロジックを追加（有効値チェック、エラー時明示的な例外）。
- 実行・監視の起動スクリプト
  - run_execution.py:
    - ExecutionEngine 起動フローを実装（BrokerClientFactory によるクライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て）。
    - Paper Trading 環境では専用 SQLite（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）を使用して本番 DB から分離。
    - 実行中の停止を制御する stop flag / pid ファイル管理（data/stop_requested.flag, data/execution.pid）。
    - RiskManager の初期設定値（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）をサンプル実装。
  - run_monitoring.py:
    - SystemMonitor を用いたポーリングループを実装（デフォルト 60 秒、MONITOR_POLL_INTERVAL 環境変数で上書き可能）。
    - 監視は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用する旨を明示。
    - 停止フラグ検出で安全にループ終了、例外時はログ出力して次ポーリングへ継続。
    - monitoring DB の初期化（init_monitoring_db）と DuckDB 接続を行う。
- プロセス制御ユーティリティ
  - set_process_priority(level) を実装：Windows / POSIX（Linux/Mac/FreeBSD）差分を吸収して優先度（high/normal/low）を設定。権限不足等は警告ログでスキップ。
  - set_cpu_affinity(cpu_count) を実装：指定コア数にプロセスをピン留め。引数検証と例外ハンドリングを含む。
- ポートフォリオ構築
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルをスコア降順にソートし上位 N を返す（タイブレークに signal_rank を使用）。
    - calc_equal_weights / calc_score_weights: 等配分、スコア正規化配分を実装（スコア合計が 0 の場合は等配分にフォールバックし警告）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中度が閾値を超える場合に当該セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム ("bull"/"neutral"/"bear") に応じた投下資金乗数を返す（未知レジームは1.0でフォールバック）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: risk_based / equal / score の発注量計算を実装。損切り・リスク率に基づく算出、単元株（lot_size）丸め、per-position と aggregate のキャップ、cost_buffer を考慮したスケールダウンと余剰配分ロジックを実装。
    - aggregate スケールダウン時の端数処理（lot_size 単位での残差配分）を実装し再現性を確保。
- リサーチ（ファクター・特徴量）
  - research/factor_research.py:
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離を DuckDB の prices_daily を用いて計算。
    - calc_volatility: 20日 ATR、ATR 比率、20日平均売買代金、出来高比率を計算（true_range の NULL 伝播制御等、データ不足時は None を返す）。
    - calc_value: raw_financials と prices_daily を組み合わせて PER, ROE を計算（target_date 以前の最新財務データを取得）。
  - research/feature_exploration.py:
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを一度のクエリで取得する実装。
    - calc_ic / rank / factor_summary: Spearman（ランク相関）ベースの IC 計算、ランク付け（同順位平均ランク）、統計サマリ（count/mean/std/min/max/median）を実装。外部依存（pandas など）を使わず標準ライブラリのみで実装。
  - research/__init__.py で主要関数と zscore_normalize をエクスポート。
- DuckDB 統合
  - DuckDB 接続を利用して prices_daily / raw_financials / raw_news 系の集計処理を実装する方針を採用。research / ai / tools が DuckDB 接続を受け取り SQL で計算を行う設計。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py:
    - Paper Trading 用の SQLite（デフォルト data/paper_trading.db）から検証指標を集計して CLI 出力するツールを追加。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、リスク却下数、平均/最大/P95 レイテンシなど。
    - P95 計算、日付フィルタ (--from / --to)、--db オプションによる DB パス指定をサポート。
    - 基準（閾値）を定義して PASS/FAIL を判定（稼働率 99%、fill_rate 90%、send_rate 95%、P95 <= 200ms）。
- ニュース NLP（AI）スコアリング（部分実装）
  - ai/news_nlp.py:
    - raw_news を銘柄別に集約し OpenAI API（gpt-4o-mini をデフォルト）にバッチ送信して銘柄別センチメント（-1.0〜1.0）を ai_scores テーブルへ保存する処理を設計・実装。
    - バッチサイズ、記事トリム（最大記事数・最大文字数）、API リトライ（429/5xx/タイムアウトに対する指数バックオフ）、レスポンスバリデーション、スコアクリッピングを実装方針として組み込む。
    - ニュース取得ウィンドウ計算（target_date に対して前日 15:00 JST 〜 当日 08:30 JST 相当の UTC 範囲）を実装。
    - 注意: ファイルの末尾で実装が途中（コード断片で終了）しているため、score_news の続きは未完（部分実装）であることを明記。
- ロギング・エラーハンドリング
  - 各所でログ出力（info/debug/warning/exception）を充実させ、例外時もプロセスを致命的に落とさず継続するフェイルセーフを採用（監視ループなど）。

Changed
- 監視関連の挙動明示化
  - run_monitoring が環境にかかわらず本番 sqlite_path を使う旨を明示（設定方針の変更／注記）。
- DB 初期化の冪等性
  - init_monitoring_db 呼び出しで監視テーブル存在を保証 — 複数回呼び出しても安全な初期化を想定。

Fixed
- （初版につき特定のバグ修正履歴はなし。コード中に注記されている TODO や注意点は未解決の設計上の考慮点として残す。）

Deprecated
- なし

Removed
- なし

Security
- OpenAI API キーは環境変数 OPENAI_API_KEY または score_news の引数で提供する必要がある旨を明確化（未設定時は ValueError）。API キー管理に注意。

Notes / Known issues
- ai/news_nlp.py の score_news 処理が途中で切れており（ファイル末尾でコード断片に終わっている）、完全動作させるには続きの実装・検証が必要です。
- portfolio.position_sizing の価格欠損時の挙動に TODO があり、price が欠損（0.0）だった場合のフォールバックロジックは未実装。将来的には前日終値や取得原価などを使う検討が必要です。
- set_cpu_affinity / set_process_priority は権限やプラットフォーム依存で動作しないケースがあるため、失敗時は警告ログに留めてスキップする実装となっています。
- .env パーサは多くの実用ケースをカバーするよう実装されているが、非常に特殊な .env の書式（複数行クォート等）に対する挙動は未保証。

---

著作・貢献
- 本リリースは基本機能の初期実装をまとめたものです。各モジュール（execution / monitoring / portfolio / research / ai / tools / utils）は今後の追加機能・テスト強化・ドキュメント整備の対象です。