# CHANGELOG

すべての重要な変更点を Keep a Changelog の形式に準拠して記載します。内容はリポジトリ内のソースコードから推測して作成しています（実装上の注記や既知の挙動も含む）。

注記:
- 環境変数名・デフォルトパス・挙動はソースコードに基づく推測です。実際の運用では .env 等の設定を確認してください。
- 日付は本ドキュメント作成日（2026-04-13）を用いています。

Unreleased
----------
- （なし）

[0.1.0] - 2026-04-13
--------------------
Added
- 基本パッケージ初期実装（KabuSys v0.1.0）
  - パッケージメタ情報
    - kabusys.__version__ = "0.1.0"

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するコマンドラインエントリポイントを提供。
    - 環境変数 KABUSYS_ENV に応じて paper_trading（テスト）用 DB を切り替え。
    - プロセス優先度を設定（set_process_priority("high")）して実行。
    - SQLite（monitoring / paper_trading 等）および DuckDB への接続を確立・クローズ。
    - 依存コンポーネント（BrokerClientFactory / OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine）を組み立ててセッションを実行。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを提供。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視用 DB は環境に関わらず本番 sqlite_path を使用する設計（ソース注記に明示）。
    - プロセス優先度を設定し、例外時もループ継続するフェイルセーフを実装。

- 設定管理
  - config.Settings
    - .env / .env.local を自動ロード（プロジェクトルートが見つからない場合はスキップ）。
    - 自動ロードを無効化するフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - .env のパース実装：コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ等に対応。
    - 必須環境変数チェック（_require）と各種便利プロパティを提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DB パス等）。
    - 検証ロジック：KABUSYS_ENV（development/paper_trading/live）、LOG_LEVEL、PAPER_FILL_MODE（instant|partial|never|reject）などの値検証。

- 監視・ユーティリティ
  - utils.process_priority
    - Windows / POSIX（Linux/Mac/FreeBSD）差分を吸収してプロセス優先度設定を提供。
    - CPU affinity 設定ユーティリティ（set_cpu_affinity）を提供。
    - 権限不足や未対応 OS の場合は警告してスキップする安全設計。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルのソート（スコア降順、同点は signal_rank 昇順）と上位 N 抽出。
    - calc_equal_weights / calc_score_weights: 等分配・スコア加重配分。スコア合計が 0 の場合は等分配にフォールバック（WARNING）。

  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限チェック（既存保有時価を元に上限超過セクターの新規候補除外）。"unknown" セクターは除外対象外。
    - calc_regime_multiplier: market regime に基づく投下資金乗数（bull=1.0, neutral=0.7, bear=0.3、未知は 1.0 にフォールバックして警告）。

  - portfolio.position_sizing
    - calc_position_sizes: allocation_method（risk_based, equal, score）に応じた発注株数計算。
    - risk_based: 許容リスク率 / 損切り率に基づく株数計算。
    - equal/score: ウェイト（weights）と max_utilization に基づく株数計算。
    - 単元株（lot_size）丸め、1 銘柄上限（max_position_pct）適用、aggregate cap（available_cash 超過時のスケーリング）を実装。
    - スケーリング時は lot_size 単位で余剰配分（端数処理）を行い、再現性を保つため安定ソートを利用。
    - price が欠損または 0 の場合はスキップし、ログにデバッグ出力。

- 研究（Research）モジュール
  - research.factor_research
    - calc_momentum: mom_1m/mom_3m/mom_6m と ma200_dev を DuckDB の prices_daily から算出（ウィンドウ不足時は None）。
    - calc_volatility: ATR20、atr_pct、20日平均売買代金、出来高比率を算出（データ不足時は None）。
    - calc_value: raw_financials と prices_daily を組み合わせて PER/ROE を算出（過去最新の財務レコードを参照）。

  - research.feature_exploration
    - calc_forward_returns: 将来リターン（複数ホライズン）を一度のクエリで取得。horizons 検証。
    - calc_ic: Spearman（ランク相関）に基づく IC 計算（有効レコードが 3 未満の場合は None）。
    - rank: 同順位は平均ランクで扱う安定的ランク付け（丸めによる ties 検出対策あり）。
    - factor_summary: count/mean/std/min/max/median を計算する集計ユーティリティ。

  - research パッケージは zscore_normalize を data.stats から再エクスポート。

- AI ニュース NLP
  - ai.news_nlp
    - raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）で銘柄別センチメントスコアを計算。
    - 日時ウィンドウ計算（JST ベース → UTC に変換）を提供（前日15:00〜当日08:30 JST）。
    - API バッチ処理（バッチ最大 20 銘柄）、トークン肥大化対策（1 銘柄あたり最大記事数・最大文字数でトリム）。
    - 429/ネットワーク/5xx は指数バックオフでリトライ（最大 retry 回数）。
    - レスポンスの厳密な JSON 検証と ±1.0 のスコアクリップ。
    - OpenAI API キーが未設定の場合は ValueError を送出。

- ツール
  - tools.paper_verification_report
    - Paper Trading 用の検証レポート生成スクリプトを提供（CLI）。
    - デフォルト DB パス: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可）。
    - 期間フィルタ（--from / --to）により system_status / trade_logs / risk_logs の指標を集計。
    - 指標: 稼働率（uptime_pct）、注文成功率（fill_rate）、送信率（send_rate）、レイテンシ P95 等。
    - 判定基準（閾値）を定義し PASS/FAIL 判定を出力。
    - DB テーブル欠如時（OperationalError）は安全にハンドルして N/A を返す。

Changed
- （初期リリースのため該当なし）

Fixed
- （初期リリースのため該当なし）

Security
- OpenAI API キーの扱いに注意:
  - score_news() は api_key 引数か環境変数 OPENAI_API_KEY を参照。未設定時は明示的にエラーを出す設計。

Notes / Implementation observations
- デフォルト DB/ファイルパス
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH (monitoring): data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
  - PID_FILE_PATH: data/execution.pid
  - KILL_FLAG_PATH: data/kill.flag

- 環境/設定に関する挙動
  - .env の自動読み込みはプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を探索して行う。プロジェクトルートが見つからない場合は自動ロードをスキップ。
  - OS 環境変数はデフォルトで保護され、.env.local の override は OS 環境変数を上書きしない。
  - MONITOR_POLL_INTERVAL に 0 以下や不正な値を設定した場合は警告ログを出しデフォルト 60 秒にフォールバック。

- フェイルセーフ設計
  - run_monitoring のポーリングループや ai.news_nlp の API 呼び出しでは例外ハンドリング・リトライや局所スキップを行い、全体停止を防止する工夫がある。

今後の提案（任意）
- 単体テスト／統合テスト向けに Settings の自動 env ロード制御を README に明示（KABUSYS_DISABLE_AUTO_ENV_LOAD の利用例）。
- position_sizing の price 欠損時フォールバック（前日終値など）の実装を検討（ソース内に TODO コメントあり）。
- ai.news_nlp の部分的失敗時の永続化ポリシー（部分成功のロールフォワード）や監視・メトリクスの強化。

以上。追加のバージョン履歴（過去バージョンの分割等）や日付調整が必要であれば指示してください。