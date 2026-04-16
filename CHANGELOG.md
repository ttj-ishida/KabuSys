CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠しています（セマンティックバージョニングに従ってください）。

Unreleased
----------

- なし

0.1.0 - 2026-04-16
------------------

初回リリース。以下の主要機能・モジュールを実装しています。

Added
- 基本情報
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として公開。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ実装。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き（デフォルト 60 秒、無効値はログを出しデフォルトにフォールバック）。
    - 停止制御ファイル（data/stop_requested.flag）検知による優雅な終了。
    - 監視用 DB は環境にかかわらず本番用 sqlite_path を使用する設計。
    - DuckDB 接続の確立、監視 DB テーブル初期化を行う。
    - プロセス優先度を高優先度に設定する処理を最初に実行。

  - run_execution.py
    - ExecutionEngine 起動スクリプト。
    - `KABUSYS_ENV=paper_trading` の場合は paper_trading 専用 SQLite（data/paper_trading.db）を使用して本番 DB から分離。
    - BrokerClientFactory 経由でブローカークライアントを生成（paper/live に応じた実装を利用）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine をスレッドで実行。
    - 停止フラグ（data/stop_requested.flag）検知でエンジン停止。PID ファイル出力に対応。

- 設定管理
  - config.py
    - .env / .env.local の自動読み込み（プロジェクトルートの探索: .git または pyproject.toml を基準）。
    - 自動読み込みを無効化する環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
    - 独自の .env パーサ実装（export 対応、クォート内のバックスラッシュエスケープ、コメント処理など）。
    - Settings クラスを導入し、各種設定（API トークン・DB パス・監視閾値・環境モード等）をプロパティ経由で取得。
    - PAPER_FILL_MODE のバリデーション（"instant"|"partial"|"never"|"reject"）とエラー通知。
    - 環境 (KABUSYS_ENV) のバリデーション（development/paper_trading/live）。

- モニタリング DB 初期化
  - monitoring_db.init_monitoring_db を各起動スクリプトから呼び出し、監視用テーブルの存在を保証（冪等）。

- ユーティリティ
  - utils/process_priority.py
    - プラットフォームを吸収したプロセス優先度設定ユーティリティ（Windows と POSIX の差分を隠蔽）。
    - `set_process_priority(level)`（"high"|"normal"|"low"）を提供。権限不足や未対応 OS では警告を出してスキップ。
    - `set_cpu_affinity(cpu_count)` を追加（任意で最初の N コアへ固定）。失敗時は警告でスキップ。

- Portfolio（銘柄選定・配分・サイズ計算）
  - portfolio.portfolio_builder
    - BUY シグナルから候補選定（スコア降順、signal_rank を tiebreak）select_candidates。
    - 等金額配分 calc_equal_weights。
    - スコア比率配分 calc_score_weights（全スコアが 0 の場合は等分配へフォールバックし WARNING を出力）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限を評価し、超過セクターの新規候補を除外（"unknown" セクターは適用除外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金倍率（bull/neutral/bear）を提供。未知レジームは警告後 1.0 でフォールバック。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method ("risk_based"/"equal"/"score") による建玉算出、単元株（lot_size）丸め、per-stock 上限・aggregate cap、cost_buffer を考慮したスケーリング・端数処理を実装。
    - risk_based では損切り幅とリスク許容率から株数を算出。価格未取得時はスキップ。

- 研究・factor 計算
  - research.factor_research
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離（MA200）を DuckDB の prices_daily から計算。データ不足は None。
    - calc_volatility: ATR(20), ATR 比率, 20日平均売買代金, 出来高比を計算。true_range の NULL 伝播を正しく扱う実装。
    - calc_value: raw_financials から最新財務データを取得し PER/ROE を算出（EPS が 0/欠損の場合は None）。
  - research.feature_exploration
    - calc_forward_returns: 指定ホライズン (デフォルト [1,5,21]) の将来リターンを一度のクエリで取得、ホライズン検証（1〜252 日）を実施。
    - calc_ic: Spearman ランク相関（Information Coefficient）を実装（有効レコードが 3 未満なら None）。
    - rank, factor_summary: ランク付け・基本統計量（count/mean/std/min/max/median）を提供。
  - research.__init__ で外部公開 API を整備（zscore_normalize も re-export）。

- AI ニュース NLP
  - ai/news_nlp.py
    - raw_news を集約し OpenAI（gpt-4o-mini）で各銘柄のセンチメント (-1.0〜1.0) を取得して ai_scores に書き込む処理を実装。
    - バッチ上限（_BATCH_SIZE=20）、1銘柄あたりの記事/文字数制限、JSON Mode 出力の厳密バリデーション、スコアクリップ（±1.0）。
    - 429/ネットワーク/5xx に対する指数バックオフリトライ（上限 _MAX_RETRIES）。
    - タイムウィンドウ計算（target_date を基準に前日 15:00 JST ～ 当日 08:30 JST を UTC で扱う calc_news_window）。
    - API キーが未設定の場合は ValueError。部分失敗時に既存スコア保護のため対象コードのみを置換する戦略（DELETE→INSERT）を採用。
    - 実装はフェイルセーフを重視し、API 失敗で完全停止しない設計。

- CLI ツール
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成スクリプト（CLI）。
    - 対象 DB をコマンドライン引数または環境変数 `PAPER_TRADING_SQLITE_PATH` で指定可能（デフォルト data/paper_trading.db）。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ、リスク却下数 等。
    - Pass/Fail 判定を実装（しきい値はファイル内定数で定義）。欠損データやテーブル未存在時は N/A / 0 を返すなど堅牢に実装。
    - P95 計算関数、日付フィルタ組立て関数を提供。

Changed
- なし（初回リリースのため変更履歴は全て追加として扱う）。

Fixed
- なし（初回リリース）。

Deprecated
- なし。

Removed
- なし。

Security
- OpenAI API キー等の機密情報は環境変数経由で取得するよう設計。README/.env.example の整備を想定（ファイル内の _require 関数は未設定時に明示的なエラーを投げる）。

Notes / Implementation details / Known limitations
- .env 自動読み込みはプロジェクトルート検出に依存する（.git または pyproject.toml）。配布後にプロジェクトルートが特定できない環境では自動ロードをスキップする。
- process_priority, set_cpu_affinity は権限不足や未対応プラットフォームで例外を握り潰して警告を出す設計（安全第一）。
- portfolio の価格参照で price が欠損（0.0）の場合、エクスポージャー・サイズ計算が不正確になる可能性があり、将来的にフォールバック価格（前日終値等）の利用を検討する旨の TODO が残る。
- ai/news_nlp.py は大規模な API 呼び出しを伴うため、実運用時はレートリミットやコストの監視が必要。API レスポンスの堅牢なバリデーションを行うが、外部 API 仕様変更時は調整が必要。
- research モジュールは DuckDB 上の prices_daily/raw_financials テーブルに依存。これらのスキーマに変更があった場合、クエリの修正が必要。

作者
- kabusys 開発チーム

（以降のリリースでは Breaking Changes / Added / Changed / Fixed を明確に分けて追記してください。）