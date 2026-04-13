CHANGELOG
=========

すべての変更は Keep a Changelog のフォーマットに準拠して記載しています。  
初回リリースの内容はソースコードから推測して記載しています（実装コメント・ドキュメント文字列に基づく）。

Unreleased
----------

-（現在未リリースの変更はありません）

0.1.0 - 初回リリース (推定)
-------------------------

Added
- 基本アーキテクチャ / 実行スクリプトを追加
  - run_execution.py: ExecutionEngine の起動エントリポイントを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite（デフォルト: data/paper_trading.db）を使用し、MockBrokerClient を利用する設計。
    - プロセス優先度を起動時に "high" に設定する呼び出しを追加（utils.process_priority.set_process_priority）。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値時はデフォルトにフォールバック。
    - 監視処理は環境に関わらず本番の sqlite_path を使用する（設計上の注記あり）。

- 設定/環境変数管理
  - kabusys.config.Settings クラスを追加し、環境変数や .env/.env.local の自動読み込み機能を実装。
    - 自動読み込みはプロジェクトルート（.git または pyproject.toml を探索）を基準に実行。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env パーサは export KEY=val、クォート、インラインコメントの取り扱い、エスケープに対応。
    - 多数の設定プロパティを提供（例: JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、PAPER_TRADING_SQLITE_PATH、PID_FILE_PATH、KILL_FLAG_PATH、各種閾値、KABUSYS_ENV 判定等）。
    - KABUSYS_ENV の許容値は development / paper_trading / live。

- ポートフォリオ構築関連（純粋関数群）
  - kabusys.portfolio パッケージを追加（メモリ内計算のみ）。
    - portfolio_builder:
      - select_candidates: BUY シグナルをスコア降順でソートして上位 N を選択。
      - calc_equal_weights: 等金額配分の重みを計算。
      - calc_score_weights: スコア加重配分。全スコアが 0 の場合は等配分にフォールバックし警告を出力。
    - risk_adjustment:
      - apply_sector_cap: セクター集中上限チェック（既存ポジションを考慮し、売却予定は除外）。"unknown" セクターは上限を適用しない。
      - calc_regime_multiplier: 市場レジームに基づく投下資金乗数（bull/neutral/bear のマッピング、未知値は 1.0 でフォールバック）。
    - position_sizing:
      - calc_position_sizes: 重み・候補・利用可能現金等からロット（単元株）丸めを考慮して発注株数を算出。risk_based / equal / score の配分方式をサポート。aggregate cap（available_cash 超過時のスケーリング）や cost_buffer を考慮した割り当て調整を実装。

- リサーチ（ファクター計算・特徴量探索）
  - kabusys.research パッケージを追加。
    - factor_research:
      - calc_momentum: 1M/3M/6M リターン、MA200 乖離率を DuckDB の prices_daily から計算。
      - calc_volatility: ATR20、相対 ATR、20日平均売買代金、出来高比などを計算。
      - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を計算（最新の財務レコードを target_date 以前のものから取得）。
    - feature_exploration:
      - calc_forward_returns: 将来リターン（複数ホライズン）を計算。horizons は検証済みで上限 252 日。
      - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算。十分なデータがない場合は None を返す。
      - factor_summary, rank: ファクター統計サマリと安定したランク付けユーティリティを提供。
    - モジュールの公開 API: calc_momentum, calc_volatility, calc_value, zscore_normalize (data.stats から再エクスポート), calc_forward_returns, calc_ic, factor_summary, rank。

- AI / ニュース NLP
  - kabusys.ai.news_nlp を追加（OpenAI API を用いたニュースセンチメントスコアリング）。
    - raw_news / news_symbols を集約し、銘柄単位にトリム（記事数・文字数上限）してバッチで OpenAI に送信。
    - リトライ・バックオフ（429/ネットワーク/5xx 対応）、レスポンスバリデーション、±1.0 へのクリップ、部分成功時のテーブル置換（安全に DELETE → INSERT）といった耐障害性設計を備える。
    - calc_news_window: JST ベースのニュースウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を UTC naive datetime で計算。
    - OpenAI クライアント（OpenAI パッケージ）を利用。モデルは gpt-4o-mini を想定。
    - API キーは引数または環境変数 OPENAI_API_KEY で指定。

- 監視 / モニタリング関連
  - monitoring DB 初期化のための init_monitoring_db（モジュール参照箇所あり）。
  - run_monitoring / run_execution から sqlite3 / duckdb 接続を確立し、終了時にクローズする処理を追加。

- コマンドラインツール
  - kabusys.tools.paper_verification_report を追加（Paper Trading 検証レポート生成）。
    - --from / --to / --db オプションで期間・DB を指定可能。デフォルト DB は data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH を優先）。
    - 指標:
      - 稼働率 (uptime)／総ポーリング数／エラー数
      - 注文成功率（Filled/Created）
      - 送信率（Sent/Created）
      - リスク却下数
      - レイテンシ（平均 / 最大 / P95）
    - 基準値（PASS/FAIL 判定）:
      - 稼働率 >= 99.0%
      - 注文成立率 >= 90.0%
      - 送信率 >= 95.0%
      - P95 レイテンシ <= 200 ms
    - データ欠損時の安全ハンドリング（OperationalError をキャッチして N/A を返す等）。

- ユーティリティ
  - utils.process_priority:
    - set_process_priority(level): Windows / POSIX（Linux, Darwin, FreeBSD）に対応してプロセス優先度を設定。未対応 OS はスキップし警告出力。
    - set_cpu_affinity(cpu_count): カレントプロセスを最初の N コアに固定。アクセス権限不足等で失敗した場合は警告を出力してスキップ。

Changed
- 初回リリースに伴う設計上の注意追加（ドキュメント内記載）
  - run_monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使用する旨を注記（運用上の注意）。

Fixed
- 入力値の堅牢性向上（不正値へのフォールバック / 処理の安全化）
  - MONITOR_POLL_INTERVAL のパースで不正値（非整数、0 以下等）を検出してデフォルト 60 秒にフォールバックし警告を出力。
  - .env パーサ: export プレフィックス、クォート中のエスケープ、インラインコメントの扱いに対応し環境変数読み込みの堅牢性を向上。
  - calc_score_weights: 全スコアが 0 の場合は等金額配分にフォールバックしてログ警告を出す。
  - news_nlp: API キー未設定時に明確な ValueError を送出。
  - position_sizing: 単元株(lot_size)丸め、価格欠損時のスキップ、aggregate cap 超過時のスケーリングと残差配分ロジックを実装して発注量算出の安定性を改善。
  - research モジュール: 欠損データやデータ不足時に None を返す等の安全策を適用（例: ma200 の行数不足、ATR の行数不足、ホライズン先データ欠損）。

Security
- .env の自動ロードはデフォルトで有効だが、テスト等で無効化できる仕組み（KABUSYS_DISABLE_AUTO_ENV_LOAD）を提供。OS 環境変数は protected として .env の上書きから保護。

Compatibility / Breaking Changes
- run_monitoring の仕様: 監視処理は環境変数 KABUSYS_ENV の値にかかわらず settings.sqlite_path（本番 DB）を使用する設計になっている点に注意。テスト環境で監視を実行する場合は設定を明確に管理する必要がある。
- Settings.env の許容値は固定（development / paper_trading / live）。これ以外を設定すると ValueError が発生する。

Notes / Migration
- 初期リリースのため、設計上の既知の TODO や改良点が各モジュール内コメントに残されています（例: position_sizing の銘柄ごとの lot_size 対応、apply_sector_cap の価格フォールバック戦略など）。
- AI ニューススコアリングは OpenAI API キー（OPENAI_API_KEY）を必要とします。プロダクション運用では API レート制限やコストに留意してください。

以上。追加・修正点の詳細は各ソースファイルの docstring / コメントを参照してください。