CHANGELOG
=========

すべての注目すべき変更を記録します。本ファイルは「Keep a Changelog」準拠の形式で記述しています。

準拠ルール:
- 変更は大カテゴリ（Added / Changed / Fixed / etc.）ごとに整理しています。
- 日付はコミット／リリース時点での想定日を記載しています（コード内容から推測）。

Unreleased
----------
- 現時点で未リリースの変更はありません。

[0.1.0] - 2026-04-13
--------------------

Added
- 全体
  - 初期公開リリース。プロジェクトの骨格と主要機能を実装。
  - パッケージバージョンを __version__ = "0.1.0" として定義 (src/kabusys/__init__.py)。

- 設定 / 環境変数ロード (src/kabusys/config.py)
  - プロジェクトルートを .git または pyproject.toml から自動検出し、.env / .env.local を自動読み込みする機能を実装。OS環境変数の上書きを制御する仕組みを提供。
  - .env パーサを実装。以下に対応:
    - export KEY=val 形式のサポート
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - クォートなしの行でのコメント（#）処理（直前が空白/タブの場合のみコメントと扱う）
  - 設定アクセス用 Settings クラスを実装。J-Quants / kabu API / LINE / DB / 監視設定 / システム設定等のプロパティを提供。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化フラグを追加。
  - 設定値検証（例: KABUSYS_ENV の許容値、PAPER_FILL_MODE の検証、LOG_LEVEL 検証など）を実装。

- 実行用スクリプト
  - run_execution.py（src/kabusys/run_execution.py）
    - ExecutionEngine を起動するエントリポイントを実装。Broker クライアントのファクトリ経由生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine の run_session 呼び出しを行う。
    - paper_trading 環境では paper 用専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と完全分離。
    - 起動時にプロセス優先度を "high" に設定する処理を追加（utils/process_priority を利用）。
  - run_monitoring.py（src/kabusys/run_monitoring.py）
    - SystemMonitor のポーリングループ起動スクリプトを実装。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計。
    - DuckDB と SQLite の接続確立・クリーンアップを行う。

- 監視 DB 初期化ユーティリティ
  - init_monitoring_db を参照して監視テーブルが存在することを保証（冪等）する処理を run 系スクリプトで呼び出し。

- Utils: プロセス優先度 / CPU affinity (src/kabusys/utils/process_priority.py)
  - set_process_priority(level) を実装。Windows / POSIX (Linux/Mac/FreeBSD) の差を吸収して優先度を設定。失敗時は警告してスキップ。
  - set_cpu_affinity(cpu_count) を実装。利用可能なコア数より多く指定された場合の挙動やエラー処理を実装。
  - 権限不足や非対応環境に対する例外ハンドリングを追加。

- ポートフォリオ構築モジュール (src/kabusys/portfolio/)
  - portfolio_builder.py
    - select_candidates: BUY シグナルのスコア降順ソートと上位選出。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分の純粋関数を実装。スコア合計が 0 の場合は等配分にフォールバックし警告ログを出力。
  - risk_adjustment.py
    - apply_sector_cap: セクター集中リスクを評価して、新規候補のフィルタリングを行う機能を実装（"unknown" セクターは上限適用除外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数を返す（"bull"/"neutral"/"bear" に対応、未知は 1.0 でフォールバック）。
  - position_sizing.py
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づく発注株数計算を実装。損切り率・リスク率に基づく risk-based、単元（lot_size）丸め、per-position 上限と aggregate cap（利用可能現金でスケールダウン）、cost_buffer を使った保守的見積り、残差処理（lot 単位で割当て）を実装。

- 研究（Research）モジュール (src/kabusys/research/)
  - factor_research.py
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離率を DuckDB の prices_daily から計算。
    - calc_volatility: 20日 ATR、ATR 比率、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials と prices_daily を組み合わせ、PER / ROE を算出（EPS 欠損時は None）。
    - 全関数は DuckDB 接続を受け取り、SQL ウィンドウ関数を活用して効率的に計算。
  - feature_exploration.py
    - calc_forward_returns: 複数ホライズン（デフォルト 1,5,21）の将来リターンを一括取得するクエリを実装。horizons のバリデーションあり。
    - calc_ic: Spearman ランク相関（IC）をファクター値と将来リターンから計算。データ不足（<3 件）や ties への対応あり。
    - rank / factor_summary: ランク化および基本統計量（count/mean/std/min/max/median）を計算するユーティリティを実装。
  - research パッケージから主要関数を外部公開（zscore_normalize は外部モジュールから取り込み）。

- AI / ニュース NLP (src/kabusys/ai/news_nlp.py)
  - raw_news を OpenAI（gpt-4o-mini）でバッチセンチメント評価して ai_scores に書き込む処理を実装（score_news）。
  - ニュース収集ウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window として実装。
  - バッチサイズ、最大記事数・文字数、スコアクリップ、リトライ方針（429/ネットワーク/5xx に対する指数バックオフ）等を設計方針として盛り込む。
  - 出力 JSON のバリデーションと部分更新（成功した code のみ置換する DELETE/INSERT 戦略）を採用し、部分失敗時のデータ保護を考慮。

- ツール (src/kabusys/tools/paper_verification_report.py)
  - Paper Trading 用の検証レポート生成スクリプトを実装。コマンドライン引数 --from / --to / --db をサポート。
  - system_status / trade_logs / risk_logs を参照して稼働率・注文成功率・送信率・リスク却下数・レイテンシ（平均・最大・P95）を算出。
  - P95 の計算、閾値（稼働率 99%、成功率 90%、送信率 95%、P95 レイテンシ 200ms）に基づく PASS/FAIL 判定を実装。
  - DB が存在しない場合のエラーメッセージ出力や、テーブル未存在時の例外ハンドリングを実装。

- DB / クエリ基盤
  - DuckDB を分析用 DB として採用し、prices_daily / raw_financials 等を参照する処理を多数実装。
  - SQLite は監視データ・注文ログ・paper_trading 用データ保存に使用。

Changed
- none （初期リリースのため該当項目なし）

Fixed
- none （初期リリースのため該当項目なし）

Notes / Implementation details (設計上の重要点・既知の制約)
- .env パーサは多くのケースに対応しているが、極端に複雑なシンタックス（ネストしたクォートなど）は想定外。
- position_sizing の price 欠損時の挙動は現状「価格がない銘柄はスキップ」で、将来的に前日終値や取得原価でのフォールバックを検討する旨をコメントで残している。
- news_nlp の API キーは環境変数 OPENAI_API_KEY または score_news の引数から供給する必要あり。未設定時は ValueError を送出する。
- run_monitoring は監視用途で常に本番用 sqlite_path を使用する設計になっている点に注意。
- process_priority や CPU affinity は権限・プラットフォームによって失敗する可能性があるため、失敗時はログを出してスキップする保護を組み込んでいる。

License
-------
- ライセンス情報はソース内に含まれていません。配布時は適切なライセンスを付与してください。