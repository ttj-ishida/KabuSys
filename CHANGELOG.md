CHANGELOG
=========

すべての変更は Keep a Changelog (https://keepachangelog.com/ja/) に準拠して記載しています。

フォーマット:
- 変更はセマンティックバージョニングに従っています。
- 日付はリリース日を示します。

Unreleased
----------

（現在未リリースの変更はありません。）

[0.1.0] - 2026-04-13
-------------------

Added
- 初回リリース。KabuSys のコア機能群を追加。
  - パッケージメタ情報
    - パッケージバージョンを __version__ = "0.1.0" として定義。
  - 設定管理（kabusys.config）
    - .env / .env.local 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml で探索）。
    - 環境変数パーサ（クォート、エスケープ、コメント処理）を実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
    - Settings クラスを追加し、各種設定（J-Quants / kabu / LINE / DB パス /監視閾値 / PID/KILL フラグ等）をプロパティで提供。
    - 入力検証を実装（KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE の妥当性チェック）。
  - 実行スクリプト
    - run_execution.py
      - ExecutionEngine 起動エントリポイントを追加。
      - KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用し、本番 DB と完全分離。
      - BrokerClientFactory に基づくブローカークライアント注入、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、EngineConfig によるセッション実行を実装。
      - duckdb をデータ処理用に接続。
      - 起動時にプロセス優先度を "high" に設定（utils.process_priority 経由）。
    - run_monitoring.py
      - SystemMonitor のポーリングループ起動スクリプトを追加。
      - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックし警告を出力。
      - 監視は環境にかかわらず本番 sqlite_path を使用して DB 初期化を行う（init_monitoring_db）。
      - duckdb 接続を併用。
      - 起動時にプロセス優先度を "high" に設定。
  - 監視周り
    - monitoring テーブル初期化ユーティリティ（init_monitoring_db）を使用して監視テーブルの冪等初期化を行う（起動時に保証）。
  - ポートフォリオ構築（kabusys.portfolio）
    - portfolio_builder:
      - select_candidates：BUY シグナルをスコア降順かつ signal_rank でタイブレークして候補選定。
      - calc_equal_weights / calc_score_weights：等金額配分およびスコア比率配分（スコア合計が 0 の場合は等金額にフォールバック）を実装。
    - risk_adjustment:
      - apply_sector_cap：セクター集中上限チェック（既存ポジションのセクター比率が閾値を超える場合、新規候補を除外）。"unknown" セクターは上限除外対象外。
      - calc_regime_multiplier：市場レジーム（"bull"/"neutral"/"bear"）に応じた投下資金乗数を返却。未知のレジームは警告の上 1.0 でフォールバック。
    - position_sizing:
      - calc_position_sizes：allocation_method（"risk_based" / "equal" / "score"）に基づく株数決定ロジックを実装。
      - 単元（lot_size）丸め、1銘柄上限・aggregate cap（available_cash）でスケーリング、cost_buffer（手数料・スリッページ見積）を考慮した保守的算出。
      - risk_based では stop_loss_pct／risk_pct に基づくリスクベースのサイズ算出。
      - スケーリング時の端数処理（fractional remainder）により残余資金で lot 単位の追加配分を行う。
  - 研究（kabusys.research）
    - factor_research:
      - calc_momentum / calc_volatility / calc_value：DuckDB の prices_daily / raw_financials テーブルを用いたモメンタム・ボラティリティ・バリュー系ファクター計算を実装。データ不足時の None ハンドリング、ウィンドウ長やスキャンバッファを設計に反映。
    - feature_exploration:
      - calc_forward_returns：指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。ホライズン検証と効率的な単一クエリ取得を実装。
      - calc_ic：ファクターと将来リターンの Spearman ランク相関（IC）計算を実装。有効レコードが 3 未満の場合は None を返却。
      - rank / factor_summary：ランク付け（同順位は平均ランク）および統計サマリー（count/mean/std/min/max/median）を実装。浮動少数処理や None 除外を考慮。
    - research パッケージは data.stats.zscore_normalize を再エクスポート。
  - AI / ニュース NLP（kabusys.ai.news_nlp）
    - raw_news を集約して OpenAI（gpt-4o-mini）を用いたセンチメントスコア（-1.0〜1.0）を生成する機能を実装。
    - 設計上の特徴:
      - ニュース収集ウィンドウを JST 基準で定義し、UTC に変換（前日 15:00 JST ～ 当日 08:30 JST の範囲）。
      - 銘柄ごとに記事数と文字数上限を設定してトークン肥大化を防止（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
      - 最大 20 銘柄単位でバッチ送信（_BATCH_SIZE）。
      - 429/ネットワークエラー/5xx などは指数バックオフでリトライ（リトライ上限あり）。
      - レスポンス検証とスコアの ±1.0 クリップ。
      - 書き込み時は対象コードの部分置換（DELETE WHERE date=? AND code=ANY(codes) → INSERT）を行い、部分失敗時にも既存スコアを保護。
      - OpenAI API キーは引数または環境変数 OPENAI_API_KEY から解決。未設定時は ValueError。
  - ユーティリティ（kabusys.utils）
    - process_priority:
      - set_process_priority(level) によるプロセス優先度設定（Windows の priority class、POSIX の nice 値を吸収）。
      - set_cpu_affinity(cpu_count) によるプロセスの CPU affinity 固定（最初の N コア）。
      - 権限不足や未対応環境では警告を出してスキップするフェイルセーフ。
  - ツール（kabusys.tools）
    - paper_verification_report:
      - Paper Trading 用の検証レポート CLI を追加（python -m kabusys.tools.paper_verification_report）。
      - 指標: 稼働率（UPTIME）/注文成功率（Fill Rate）/送信率/レイテンシ（平均/最大/P95）/リスク却下数。
      - デフォルト閾値を定義して PASS/FAIL 判定を行う（閾値はソース内定義）。
      - DB パスは --db オプションまたは env PAPER_TRADING_SQLITE_PATH で指定可能。
  - DB / データ層
    - SQLite（監視 / paper_trading）と DuckDB（時系列・リサーチ処理）を両立させる実行フローを実装。

Changed
- 初回リリースのため基点（既存プロジェクトからの変更はなし）。

Fixed
- 初回リリースのため特記する修正はなし。

Deprecated
- なし。

Removed
- なし。

Security
- OpenAI API キーは環境変数または引数経由で明示的に提供する設計。デフォルトでキーを埋め込まないことを想定。

注意事項 / マイグレーション
- 環境変数の自動ロード:
  - デフォルトでプロジェクトルートの .env / .env.local が自動読み込みされます。自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Paper Trading:
  - paper_trading 環境では SQLite DB を data/paper_trading.db（または PAPER_TRADING_SQLITE_PATH）に分離して動作します。実運用 DB と完全に分離されるため誤操作に注意。
- MONITOR_POLL_INTERVAL:
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で設定可能。1 未満や不正値は無効と見なされデフォルト 60 秒にフォールバックします。
- OpenAI:
  - ai/news_nlp の score_news を実行するには OPENAI_API_KEY の設定が必須です。API 利用に伴うコスト・制限に注意してください。

補足
- 本 CHANGELOG はコードベースから推測できる機能に基づき作成しています。実際のリリースノートとして利用する際は、変更点や導入手順・破壊的変更等を開発チームで確認して追記してください。