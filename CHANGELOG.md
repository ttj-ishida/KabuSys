CHANGELOG
=========

すべての重要な変更を記録します。フォーマットは "Keep a Changelog" に準拠しています。

[0.1.0] - 2026-04-11
-------------------

Added
- 初回リリース: KabuSys v0.1.0 を追加。
- 実行スクリプト
  - run_execution.py
    - ExecutionEngine の起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全に分離して実行。
    - 起動時にプロセス優先度を "high" に設定する処理を導入。
    - BrokerClientFactory 経由でブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - 実行後に SQLite / DuckDB 接続を確実にクローズ。
  - run_monitoring.py
    - SystemMonitor ポーリングループの起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔をオーバーライド可能（デフォルト 60 秒）。不正値（非正整数）はデフォルトにフォールバックして警告ログを出力。
    - 監視処理は環境にかかわらず本番 sqlite_path を使用する設計。
    - 起動時にプロセス優先度を "high" に設定。
    - KeyboardInterrupt を受けてループを正常終了し、リソースを解放するよう実装。

- 設定管理
  - config.py
    - .env 自動ロード機能を実装（プロジェクトルートの .git または pyproject.toml を基準に探索）。
    - .env / .env.local の読み込み順序（OS 環境変数 > .env.local > .env）を実装。OS 環境変数を保護する protected 機構を導入。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - export KEY=val 形式やクォート／エスケープ、インラインコメント（クォートなしで直前が空白またはタブの場合）に対応するパーサ実装。
    - Settings クラス導入: 各種設定プロパティ（DB パス、API トークン、PID/kill flag パス、スレッショルドなど）とバリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）を提供。
    - paper_fill_mode, paper_sqlite_path, kill_flag_* 等のプロパティを追加。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順＋tie-breaker（signal_rank）で選定。
    - calc_equal_weights / calc_score_weights を実装（スコア全体が 0 の場合は等配分にフォールバックして警告）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中の上限チェック（既存保有の時価を計算し、上限を超えるセクターの新規候補を除外）。unknown セクターは上限適用対象外。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数を提供（bull/neutral/bear、未知レジームは 1.0 にフォールバックして警告）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") に応じた発注株数計算を実装。
    - 単元株（lot_size）丸め、1 銘柄上限（max_position_pct）、aggregate cap（available_cash）を考慮。
    - cost_buffer を導入して手数料・スリッページ分を保守的に見積もる。
    - aggregate 超過時にはスケーリングを行い、残差（fractional remainder）に基づいて lot 単位で追加配分するアルゴリズムを実装。
    - 価格欠損時のスキップ、各種ログ出力による堅牢性確保。

- ユーティリティ
  - utils/process_priority.py
    - set_process_priority(level): Windows と POSIX（Linux, Darwin, FreeBSD）を吸収する実装。psutil による優先度設定をサポートし、権限不足や未対応 OS は警告ログ出力してスキップ。
    - set_cpu_affinity(cpu_count): カレントプロセスを最初の N コアに固定する機能を追加（cpu_count=None の場合は何もしない）。権限不足や未対応環境を安全にハンドリング。

- リサーチ / 特徴量・ファクター計算
  - research/factor_research.py
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev を DuckDB の prices_daily から計算するクエリ実装。データ不足時は None を返す。
    - calc_volatility: ATR, atr_pct, avg_turnover, volume_ratio を計算（true_range の NULL 伝播、ウィンドウ行数チェックを考慮）。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を計算（target_date 以前の最新財務データを取得）。
    - 全関数は DuckDB 接続を受け取り外部 API へはアクセスしない設計。
  - research/feature_exploration.py
    - calc_forward_returns: target_date 基準の将来リターン（任意ホライズン）を一括クエリで取得。horizons のバリデーションあり。
    - calc_ic / rank / factor_summary: スピアマン IC 計算（ランク同順位は平均ランク）、基本統計量サマリー（count/mean/std/min/max/median）を純粋 Python 実装で提供。外部ライブラリに依存しない実装。
  - research/__init__.py で主要関数をエクスポート。

- AI 機能
  - ai/news_nlp.py
    - raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）にバッチ送信し、銘柄ごとのセンチメント ai_score を ai_scores テーブルへ書き込む機能を実装。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window で計算し、UTC naive datetime を返す。
    - 銘柄単位で記事を集約、1 チャンク最大 20 銘柄、1 銘柄あたり最大 10 記事／3000 文字でトリム。
    - API 呼び出しは JSON Mode を利用し、429／ネットワーク断／タイムアウト／5xx を対象に指数バックオフでリトライ。その他のエラーはスキップして継続（フェイルセーフ）。
    - レスポンスの堅牢な検証を実装（JSON 抽出、results 型・各要素の shape、コード照合、数値チェック）。スコアは ±1.0 にクリップ。
    - 書き込みは部分失敗に強い設計（対象コードのみ DELETE → INSERT、DuckDB executemany の空リスト制約を考慮）。
    - API キーは引数または環境変数 OPENAI_API_KEY を使用。未設定時は ValueError を送出。

  - ai/regime_detector.py
    - ETF 1321（Nikkei 225 連動型）の MA200 乖離とマクロニュース LLM センチメントを重み付け合成して market_regime（日次）を判定する機能を実装。
    - _calc_ma200_ratio: target_date 未満のみを使用してルックアヘッドを防止。データ不足時は中立（1.0）を返す。
    - マクロ記事抽出はキーワードマッチ（複数キーワード）で行い、最大件数制限を設ける。API 失敗時は macro_sentiment=0.0 で継続。
    - 合成規則: clip(0.7*(ma200_ratio-1)*10 + 0.3*macro_sentiment, -1, 1)（パラメータは定数化）。
    - 書き込みは冪等（BEGIN/DELETE/INSERT/COMMIT）で行う。

Changed
- 設定の自動ロード挙動を明示的に設計（.env/.env.local の読み込み順と保護キー機構）。
- 各種関数で "ルックアヘッドバイアス防止" の方針を採用（datetime.today()/date.today() を直接参照せず、target_date を明示的に受け取る設計に統一）。

Fixed
- MONITOR_POLL_INTERVAL の不正値（0 以下や非整数）を検出してデフォルトにフォールバックし、time.sleep に渡して ValueError が発生するのを防止。
- DuckDB への書き込み（ai_scores など）で executemany に空リストを渡すと失敗する問題に対処（空チェックを行ってから executemany を呼ぶ）。
- OpenAI 応答の JSON パース失敗時に、前後の余計なテキストを丸めて最外の {} を抽出するフォールバックを追加し、稀なフォーマット差異に対して堅牢化。

Security
- API キー取り扱い: OpenAI API キーは引数または環境変数から解決。未設定時は明示的なエラーで早期検出。

Notes / Migration
- 環境変数自動ロードを試験的に無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト環境向け）。
- paper_trading 環境では run_execution が paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用します。運用時は誤って本番 DB を上書きしないよう注意してください。
- OpenAI 連携機能を利用するには OPENAI_API_KEY の設定が必要です。score_news / regime_detector の両機能は API キー未設定時に例外を出します。

その他
- パッケージの __version__ は "0.1.0" に設定されています。