CHANGELOG
=========

すべての変更は「Keep a Changelog」フォーマットに準拠して記載しています。  
バージョン番号はパッケージ内の __version__ を参考にしています。

[Unreleased]
------------

（現在の提供ソースは v0.1.0 に対応するため、未リリース変更はありません。）

0.1.0 - 初期リリース
-------------------

リリース日: 未設定

Added
- 基本アーキテクチャ・起動スクリプトを追加
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はログ警告のうえデフォルトにフォールバック。
    - 停止はプロジェクト直下の data/stop_requested.flag を検知して終了。
    - 監視（monitoring）用 DB 初期化を行い、DuckDB も併用している。
    - プロセス優先度を起動直後に "high" に設定する処理を実行。
    - 監視は環境（KABUSYS_ENV）にかかわらず本番 sqlite_path を使用することが明示されている。
  - run_execution.py
    - ExecutionEngine 起動スクリプト。
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を利用して paper_trading 用 DB（data/paper_trading.db をデフォルト）に記録し、本番 DB と完全分離。
    - Engine の PID ファイルを data/execution.pid に書き、停止フラグで安全に停止できる仕組み。
    - Execution に必要な依存コンポーネント（BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine）を組み立てて起動する。
    - RiskManager に対するデフォルト設定値（max_position_pct、max_utilization、rate_limit_per_sec、circuit_breaker 等）を設定。

- 設定・環境変数管理
  - config.py
    - プロジェクトルート検出（.git または pyproject.toml）を行い、.env / .env.local の自動読み込みを実装（OS 環境変数を保護する仕組みあり）。自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env のパースロジック強化（export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、インラインコメント処理）。
    - Settings クラスを提供し、主要な環境変数をプロパティとして取得（バリデーション付き）。
    - 主要な設定項目:
      - データベース: SQLITE_PATH（data/monitoring.db）、DUCKDB_PATH（data/kabusys.duckdb）、PAPER_TRADING_SQLITE_PATH（data/paper_trading.db）
      - PAPER_FILL_MODE（instant|partial|never|reject、不正値は例外）
      - 監視関連: PID_FILE_PATH、KILL_FLAG_PATH、閾値（CPU/MEM/DISK）
      - KABUSYS_ENV の有効値: development, paper_trading, live（不正値は例外）
      - LOG_LEVEL の検証

- ポートフォリオ構築モジュール
  - kabusys.portfolio
    - portfolio_builder.py
      - select_candidates: スコア降順・タイブレークロジックを実装。
      - calc_equal_weights / calc_score_weights: 等重・スコア加重配分（スコア合計が 0 の場合は等重にフォールバック）。
    - risk_adjustment.py
      - apply_sector_cap: セクター集中上限チェック（既存保有と当日売却予定を考慮）を実装。unknown セクターは制約対象外。
      - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数（フォールバックロジックあり）。
    - position_sizing.py
      - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく株数計算。単元株（lot_size）丸め、max_position_pct、max_utilization、cost_buffer による集計上限のスケールダウンに対応。
      - aggregate cap（投下合計が available_cash を超えた場合のスケーリング）や端数処理ロジックを実装。

- リサーチ（ファクター計算・探索）モジュール
  - kabusys.research.factor_research
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離率の算出（DuckDB で SQL ベース）。
    - calc_volatility: 20 日 ATR、相対 ATR、平均売買代金、出来高比率を実装（true_range の NULL 伝播を慎重に扱う）。
    - calc_value: raw_financials を参照して PER / ROE を計算（対象日以前の最新報告を取得）。
  - kabusys.research.feature_exploration
    - calc_forward_returns: 複数ホライズンの将来リターンを一括で取得（LEAD を使用）。
    - calc_ic: スピアマンランク相関（IC）を実装（None・データ不足時の保護）。
    - factor_summary / rank: 基本統計量計算、ランク付けユーティリティを実装。
  - research パッケージの __all__ を整備（zscore_normalize を data.stats から再エクスポート）。

- ニュース NLP（AI）モジュール
  - kabusys.ai.news_nlp
    - raw_news と news_symbols から銘柄別に記事を集約し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメント（-1.0〜1.0）を算出、ai_scores テーブルへ書き込む処理を実装。
    - バッチサイズ、トークン肥大化対策（記事数上限・文字数上限）、バッチごとの最大銘柄数制限を導入。
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライを実装（上限あり）。
    - 出力検証、スコアのクリップ ±1.0、部分更新（DELETE→INSERT のスキーマ）で部分失敗時の保護を実装。
    - calc_news_window ヘルパー（JST ベース時間ウィンドウの UTC 変換）を提供。
    - 注意: OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY で指定する必要がある（未設定時は ValueError）。

- ユーティリティ
  - utils.process_priority
    - set_process_priority(level): Windows / POSIX（Linux, Darwin, FreeBSD）を吸収してプロセス優先度を設定。アクセス権限不足や未サポート環境では警告ログを出力してスキップ。
    - set_cpu_affinity(cpu_count): 最初の N コアにピン留めする機能（エラー時は警告してスキップ）。
    - 例外（AccessDenied など）を捕捉して安全に動作するように実装。

- ツール
  - kabusys.tools.paper_verification_report
    - Paper Trading の検証レポート生成スクリプトを追加。
    - system_status, trade_logs, risk_logs からシステム稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均・最大・P95）を計算し、PASS/FAIL を判定する基準値を定義。
    - コマンドライン引数 --from / --to / --db に対応。
    - DB 存在チェック、SQLite の OperationalError に対する回復処理を実装。

Changed
- .env 読み込みの振る舞い
  - OS 環境変数を保護するための protected キーセットを導入。.env.local は .env より優先して上書き（ただし OS 環境変数は上書きしない）。
- モニタリングの DB 接続
  - 監視プロセスは KABUSYS_ENV にかかわらず「本番の sqlite_path」を使用する設計（意図的な分離方針）。

Fixed
- .env のパース挙動改善
  - クォート内でのバックスラッシュエスケープ処理や、クォートなし時のインラインコメント判定（'#' 前の空白のみをコメント扱い）など、より実用的なパーサに改善。
- DuckDB 用クエリの NULL/カウント処理
  - true_range / ATR の計算で NULL の伝播を正しく扱い、カウント条件（十分なウィンドウ行数）で None を返すように修正。

Security
- OpenAI API キー取り扱い
  - ai.news_nlp は明示的に API キー（api_key 引数または OPENAI_API_KEY 環境変数）を要求。未設定時は例外を投げる安全設計。

Notes / Migration
- 必須環境変数
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD は Settings 経由で必須となるため、環境に設定してください（未設定時は ValueError）。
- KABUSYS_ENV
  - 有効な値: development, paper_trading, live。paper_trading を選択すると発注は MockBroker を使い paper_trading 専用 DB に記録します。
- PAPER_FILL_MODE
  - 有効値: "instant" | "partial" | "never" | "reject"。不正値は起動時に例外となります。
- MONITOR_POLL_INTERVAL
  - MONITOR_POLL_INTERVAL を 0 以下や非整数にするとデフォルト 60 秒にフォールバックし、ログに警告が出ます。
- 停止フラグ / PID ファイル
  - stop_requested.flag や data/execution.pid 等のファイルで外部からの起動/停止制御を行います。環境に合わせてパスを調整可能です（Settings のプロパティ参照）。

既知の TODO / 制限
- position_sizing.calc_position_sizes の価格欠損（price が 0 の場合）は現状でスキップしており、将来的に前日終値や取得原価を使うフォールバックを検討。
- 単元株 lot_size は現状一律。将来的に銘柄別 lot_map を受け取る拡張予定。
- ai.news_nlp の残り実装（記事フェッチ関係の続き部分）がソース末尾で途中になっている箇所がある（fetch 以降の処理は引き続き実装が必要）。

参考
- パッケージバージョン: __version__ = "0.1.0"