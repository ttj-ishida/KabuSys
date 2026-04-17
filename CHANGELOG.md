# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを使用します。

現在のリリース履歴は下記のとおりです。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-17

初回公開リリース。以下の主要機能・モジュールを実装しました。

### 追加
- 基本パッケージ情報
  - kabusys パッケージ初期バージョンを追加（__version__ = 0.1.0）。

- 設定 / 環境読み込み（kabusys.config）
  - .env / .env.local の自動読み込み機能を追加（プロジェクトルート探索：.git または pyproject.toml）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプションを追加。
  - .env パーサを実装（export 形式、クォート文字列、バックスラッシュエスケープ、行末コメント処理に対応）。
  - 環境変数保護（protected）機構を導入し、上書き制御を可能に。
  - Settings クラスを実装し、各種設定をプロパティ経由で取得可能に：
    - J-Quants / kabu API トークン・パスワード、LINE 設定
    - DUCKDB/SQLite パス、paper trading 用 DB パス、PID/kill フラグパス
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）
    - 環境種別（development / paper_trading / live）とログレベルのバリデーション
    - 監視用 CPU/MEM/DISK の閾値、kill_flag の自動クリアフラグなど

- 実行系: ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）
  - 起動時にプロセス優先度を高（high）へ設定。
  - KABUSYS_ENV=paper_trading の場合、paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
  - BrokerClientFactory によるブローカークライアント生成を呼び出し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
  - 停止フラグ (data/stop_requested.flag) を監視し、安全な停止処理を実装。
  - 実行中の PID を data/execution.pid に記録する想定（pid_file 引数）。

- 監視系: SystemMonitor 起動スクリプト（src/kabusys/run_monitoring.py）
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックし警告ログを出力。
  - 監視は環境に関わらず本番 sqlite_path を使用する設計（監視データは一元化）。
  - stop フラグを検知してループを終了、例外発生時はログ出力後に次ポーリングへ回復。

- ユーティリティ（src/kabusys/utils/process_priority.py）
  - プラットフォーム差分を吸収するプロセス優先度設定ユーティリティを追加。
  - Windows（psutil の優先度クラス）と POSIX（nice 値）に対応。対応 OS 判定・未対応 OS の場合はスキップして警告。
  - 例外（権限不足等）発生時に警告して処理を継続。
  - CPU affinity を最初の N コアに固定する set_cpu_affinity を追加（引数検証あり）。

- ポートフォリオ構築（src/kabusys/portfolio）
  - portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順に並べ上位 N を選択（同点は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights（スコア合計が 0 の場合は等配分にフォールバックし警告）。
  - risk_adjustment:
    - apply_sector_cap: セクター集中制限に基づき候補をフィルタ。sell_codes（当日売却予定）を考慮し、"unknown" セクターは制限対象外。
    - calc_regime_multiplier: market レジームに応じた投下比率 multiplier を返す（bull=1.0, neutral=0.7, bear=0.3）。未知レジームは 1.0 でフォールバックし警告を出力。
  - position_sizing:
    - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") に応じた発注株数計算を実装。
    - 単元株（lot_size）丸め、1 銘柄上限（max_position_pct）、投下合計の aggregate cap（available_cash を越える際のスケールダウン）実装。
    - cost_buffer（手数料・スリッページ見積）を考慮した保守的見積と、残余キャッシュでの端数配分ロジックを提供。

- リサーチ / ファクター計算（src/kabusys/research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離を計算（ウィンドウ不足の場合は None）。
    - calc_volatility: ATR20、相対 ATR、20日平均売買代金、出来高比を計算（欠損データを適切に扱う）。
    - calc_value: raw_financials から最新財務データを取得し PER/ROE を計算（EPS が 0/欠損時は None）。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。horizons の妥当性検証。単一クエリで効率的に取得。
    - calc_ic: スピアマンランク相関（IC）を実装。有効レコードが 3 未満の場合は None。
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）を計算。
    - rank: ties を平均ランクで処理（丸めで ties 判定の安定化）。
  - research パッケージは DuckDB 接続を前提に prices_daily / raw_financials テーブルを参照する設計。

- AI ニュース NLP（src/kabusys/ai/news_nlp.py）
  - raw_news を OpenAI（gpt-4o-mini）へバッチ送信して銘柄ごとの ai_score を生成し ai_scores テーブルへ書き込むロジック（ドキュメントに処理フローを明記）。
  - タイムウィンドウ計算（JST 基準 → UTC 変換）を実装する calc_news_window。
  - バッチサイズ、最大記事数・文字数（トークン肥大対策）、スコアクリップ（±1.0）、リトライ（429/5xx/タイムアウト等、指数バックオフ）やレスポンス検証、部分失敗時の部分置換（DELETE→INSERT）などのフェイルセーフ設計を採用。
  - API キー未設定時に明確な例外を送出。

- ツール（src/kabusys/tools/paper_verification_report.py）
  - Paper Trading 検証レポート生成スクリプトを追加。
  - CLI オプション: --from / --to / --db。
  - デフォルト DB パス: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可）。
  - 指標:
    - 稼働率（uptime）閾値 99.0%
    - 注文成功率（fill_rate）閾値 90.0%
    - 送信率（send_rate）閾値 95.0%
    - P95 レイテンシ閾値 200 ms
  - 各種クエリは system_status / trade_logs / risk_logs を参照し、欠損テーブルに対しては N/A を扱って安全に処理。

### 変更
- （初回リリースのため履歴上の変更点はありません）

### 修正
- （初回リリースのため履歴上の修正点はありません）

注意:
- 本リリースでの DB 操作は SQLite / DuckDB を前提としています。各テーブル（prices_daily, raw_financials, raw_news, news_symbols, ai_scores, system_status, trade_logs, risk_logs 等）のスキーマは本パッケージの想定に従って事前準備する必要があります。
- ai/news_nlp モジュールは OpenAI API を利用する設計のため、実行には有効な API キーとネットワーク接続が必要です。
- 一部の実装（例: ExecutionEngine / BrokerClientFactory / SystemMonitor の内部実装）は本変更ログで言及した起動・組立て方針に従っており、外部依存や具体的な振る舞いはそれぞれのモジュール実装に依存します。

---

作成・リリース日: 2026-04-17