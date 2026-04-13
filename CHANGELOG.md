CHANGELOG
=========

すべての notable な変更はこのファイルに記録します。
フォーマットは「Keep a Changelog」に準拠します。

リリース日付はソースコードから推測可能な現在の状態を基にしています。
---

[Unreleased]
------------

- （現状なし）

[0.1.0] - 2026-04-13
--------------------

Added
- 全体
  - 初期公開リリース。日本株自動売買システム "KabuSys" のコア機能群を追加。
  - パッケージバージョンを __version__ = "0.1.0" として定義。

- 設定管理 (src/kabusys/config.py)
  - .env/.env.local 自動読み込み機能を追加（プロジェクトルートを .git または pyproject.toml から検出）。
  - 読み込み順序: OS環境 > .env.local (上書き) > .env（未設定のキーのみセット）。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を追加。
  - .env パースの強化:
    - export プレフィックス対応、シングル/ダブルクォート内のエスケープ対応、インラインコメント処理。
  - 必須環境変数取得ヘルパー _require() を追加。
  - 各種設定プロパティを提供:
    - JQUANTS_REFRESH_TOKEN, KABU API 関連、LINE Messaging API トークン、
    - DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH
    - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START
    - CPU/MEM/DISK しきい値
    - KABUSYS_ENV (development / paper_trading / live) と LOG_LEVEL バリデーション
    - PAPER_FILL_MODE の検証（instant/partial/never/reject）

- 実行スクリプト
  - ExecutionEngine 起動スクリプト (src/kabusys/run_execution.py)
    - ExecutionEngine の組み立てと起動を行うエントリポイントを追加。
    - KABUSYS_ENV=paper_trading 時は paper_sqlite_path を使用して本番 DB と分離（MockBrokerClient を利用）。
    - ブローカークライアントの Factory（BrokerClientFactory）を利用。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせてエンジンを起動。
    - リソース（SQLite / DuckDB 接続）を finally ブロックで必ずクローズ。
    - プロセス優先度を最初に設定するフローを追加（utils.process_priority.set_process_priority を使用）。
    - RiskManager 用の初期設定値（max_position_pct 等）を明記。

  - SystemMonitor 起動スクリプト (src/kabusys/run_monitoring.py)
    - SystemMonitor のポーリングループ起動エントリポイントを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 0 以下や不正な値はデフォルトにフォールバックし、警告を出力。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計。
    - DuckDB との接続確立、監視 DB 初期化（init_monitoring_db）を実施。
    - KeyboardInterrupt を受けて正常終了するハンドリング。

- 監視 DB 初期化（src/kabusys/monitoring/*）
  - monitoring 用 DB 初期化ロジック（init_monitoring_db）を使用して冪等に監視テーブルを確保（run スクリプトから利用）。

- ユーティリティ (src/kabusys/utils/process_priority.py)
  - プラットフォーム非依存のプロセス優先度設定ユーティリティを追加。
    - Windows 用定数と POSIX (Linux / Darwin / FreeBSD) の nice 値をサポート。
    - set_process_priority(level) による high/normal/low の指定をサポート。
    - set_cpu_affinity(cpu_count) による CPU affinity 固定機能を追加（None で無効化）。
    - 権限不足や未対応プラットフォーム時に警告を出して安全にスキップ。

- ポートフォリオ構築 (src/kabusys/portfolio/*)
  - portfolio_builder:
    - select_candidates: BUY シグナルのスコア降順選択（タイブレークは signal_rank）。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重の重み計算（スコア合計0時は等配分にフォールバック）。
  - risk_adjustment:
    - apply_sector_cap: セクター別上限チェック（既存ポジションのエクスポージャーを考慮して候補を除外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す。
  - position_sizing:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数計算を実装。
    - 単元株（lot_size）、max_position_pct、max_utilization、cost_buffer に対応。
    - aggregate cap に基づくスケールダウンと端数処理（lot_size 単位での再配分ロジック）を実装。
  - これらの関数は純粋関数（DB 参照なし）として設計。

- リサーチ (src/kabusys/research/*)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率を計算（DuckDB の prices_daily を利用）。
    - calc_volatility: ATR20、ATR 比率、平均売買代金、出来高比等を計算。
    - calc_value: EPS/ROE を用いた PER/ROE 計算（raw_financials と prices_daily を結合）。
  - feature_exploration:
    - calc_forward_returns: 将来リターン（複数ホライズン）計算。
    - calc_ic: スピアマンランク相関（IC）計算（record 結合、None 排除、最小サンプル数チェック）。
    - factor_summary / rank: 基本統計量・ランク計算ユーティリティ。
  - DuckDB 接続を受け、SQL を主体に高効率に計算する設計。

- AI ニューススコアリング (src/kabusys/ai/news_nlp.py)
  - raw_news を OpenAI（gpt-4o-mini）でセンチメント評価し、銘柄別に ai_scores テーブルへ書き込む機能を追加。
  - 特徴:
    - ニュースウィンドウ計算（JST ベース → UTC に変換）。calc_news_window を提供。
    - 1 銘柄あたり最大記事数 / 文字数でトリム（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
    - 最大 20 銘柄ずつのバッチ送信（_BATCH_SIZE）。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフ再試行。
    - レスポンスの構造と型のバリデーション、スコアを ±1.0 にクリップ。
    - 部分成功時に既存スコアを守るため、更新対象コードを限定して DELETE→INSERT を実行する設計（executemany の空 params 回避も考慮）。
    - API キー未設定時は明示的なエラーを出す（api_key 引数または環境変数 OPENAI_API_KEY）。

- ツール (src/kabusys/tools/paper_verification_report.py)
  - Paper Trading 用検証レポート生成スクリプトを追加。
    - CLI オプション: --from, --to, --db（PAPER_TRADING_SQLITE_PATH の代替）。
    - 指標:
      - 稼働率 (uptime_pct)、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ
      - リスク却下数（risk_logs）
    - 判定基準（デフォルト閾値を定義）:
      - 稼働率 >= 99.0%
      - 注文成立率 >= 90.0%
      - 送信率 >= 95.0%
      - P95 レイテンシ <= 200 ms
    - P95 計算、日付フィルタ、DB 存在チェック、テーブル欠如時の堅牢性（OperationalError を捕捉してデフォルト値を使用）を実装。

Changed
- ログ・エラー処理
  - 起動スクリプトで基本ログレベル INFO を設定。
  - 例外発生時に詳細な logger.exception によるログ出力を行い、監視ループ等は継続するフェイルセーフ動作を採用。

Fixed
- 環境変数バリデーションの強化:
  - KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE の不正値検出と明示的な例外メッセージを追加。

Notes / Known limitations
- news_nlp の score_news の一部実装はファイル末尾で途切れている（処理の最後の DB 書き込み部分や一部ログメッセージが途中で終わっている可能性あり）。完全な運用のためにはファイル末尾の処理継続・テストが必要。
- position_sizing の price が欠損（0.0）の場合、エクスポージャー等が過少見積りされる旨の TODO コメントあり。将来的に前日終値や取得原価によるフォールバックを検討。
- process_priority の設定は権限不足や未対応 OS の場合はスキップされるため、期待通りに優先度が変更されない可能性がある点に注意。
- DuckDB / SQLite のスキーマや monitoring テーブル定義は別ファイル（monitoring_db 等）に依存。実動作には初期化ロジックとスキーマ整備が必要。

Authors
- KabuSys 開発チーム（コードコメント・設計メモに基づき作成）

---

注: 本 CHANGELOG は提供されたソースコードから推測して作成しました。実際の変更履歴やリリースノートはコミット履歴・リリースマネージャの記録に基づき正式に作成してください。