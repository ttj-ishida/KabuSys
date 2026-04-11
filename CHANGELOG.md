Changelog
=========

すべての変更は https://keepachangelog.com/ja/ に準拠します。
このプロジェクトはセマンティックバージョニングを使用します。

[0.1.0] - 2026-04-11
--------------------

Added
- パッケージ初回リリース。メタデータ: kabusys v0.1.0 を導入。
- 設定管理 (kabusys.config)
  - .env / .env.local 自動ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml を探索）。
  - 複雑な .env パースをサポート（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュによるエスケープ）。
  - 環境変数保護（OS 環境変数を上書きしない / override オプション）と自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を導入。
  - Settings クラスを実装し、J-Quants / kabu API キー・DB パス・PID/kill フラグパス・閾値・環境（development, paper_trading, live）などを取得・検証するプロパティを提供。
  - PAPER_FILL_MODE の入力検証（instant/partial/never/reject）。
- 実行スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。BrokerClientFactory を利用してブローカークライアントを選択。
    - Paper trading 環境では paper_trading 用 SQLite DB を使用して本番 DB と分離。
    - RiskConfig によるリスク制約（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を組み込み、ExecutionEngine 起動時に渡す設計。
    - duckdb 接続を受け取りリサーチ系データ（prices_daily 等）利用を想定。
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、0 以下はデフォルトにフォールバック）。
    - 監視処理は環境にかかわらず本番 sqlite_path を使用する仕様。
- 監視 DB 初期化
  - init_monitoring_db を使用して監視用テーブルの冪等初期化を確保（起動時に呼び出し）。
- プロセス制御ユーティリティ (kabusys.utils.process_priority)
  - set_process_priority(level) を実装し、Windows / POSIX（Linux, macOS, FreeBSD）で差分を吸収。
  - set_cpu_affinity(cpu_count) を追加してカレントプロセスの CPU affinity を固定可能（権限不足等は警告でスキップ）。
  - 権限不足や未対応プラットフォームで安全にフォールバックするログを備える。
- ポートフォリオ構築 (kabusys.portfolio)
  - portfolio_builder: 候補選定 select_candidates、等金額 calc_equal_weights、スコア加重 calc_score_weights を追加。スコア合計が 0 の場合は等配分にフォールバックして WARNING を出力。
  - risk_adjustment: apply_sector_cap（セクター集中制限の適用）、calc_regime_multiplier（市場レジームに応じた投下資金乗数）を実装。unknown セクターは制限適用除外、未知レジームはフォールバック。
  - position_sizing: calc_position_sizes により allocation_method ("risk_based", "equal", "score") に従った株数決定を実装。単元株（lot_size）丸め、per-position 上限、aggregate cap（available_cash）に基づくスケーリング、cost_buffer を考慮した保守的見積り、残差を lot 単位で再配分するアルゴリズムを実装。
  - いずれも純粋関数設計（DB 参照なし、メモリ内計算）。
- リサーチ機能 (kabusys.research)
  - factor_research: calc_momentum（1/3/6 ヶ月リターン、MA200 乖離）、calc_volatility（ATR, 相対ATR, 平均売買代金, 出来高比率）、calc_value（PER, ROE）を実装。DuckDB 接続を受け取り SQL で計算。
  - feature_exploration: calc_forward_returns（将来リターン）、calc_ic（スピアマン順位相関による IC）、rank（同順位は平均ランク）、factor_summary（基本統計量）を実装。外部ライブラリに依存せず標準ライブラリのみで実装。
  - research パッケージは zscore_normalize を kabusys.data.stats から再エクスポート。
- AI 機能 (kabusys.ai)
  - news_nlp: ニュース記事を OpenAI（gpt-4o-mini）でセンチメント解析し、銘柄別 ai_scores テーブルへ書き込む機能を実装。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）、記事の銘柄別集約、1 銘柄あたり記事数と文字数トリム、最大 20 銘柄バッチ処理、429/タイムアウト/ネットワーク断/5xx のエクスポネンシャルバックオフによるリトライ、レスポンス検証（JSON 抽出・results 構造検証）、スコア ±1.0 にクリップ、部分失敗時に既存スコアを保護する DELETE → INSERT の冪等書き込み。
    - OpenAI クライアント作成は OpenAI(api_key=...) を使用。API キーは引数または環境変数 OPENAI_API_KEY で解決（未設定時は ValueError）。
  - regime_detector: ETF 1321 の MA200 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次 market_regime ('bull'/'neutral'/'bear') を判定・書き込みする機能を実装。prices_daily クエリは target_date 未満のデータのみを使用するなどルックアヘッドバイアス防止策を採用。API 失敗時は macro_sentiment=0.0 でフォールバック。
- OpenAI 周りの堅牢化
  - レスポンス JSON の前後ノイズ除去（最外側の {} を抽出してパース）や、results のバリデーションを実装。LLM が整数で code を返すケースに備えた正規化等。
  - リトライの上限・バックオフの導入、失敗時のフォールバック動作（部分スコアの安全な書き込み）を実装。
- その他の堅牢化・利便性
  - DuckDB への executemany を実行する際、空パラメータリストに対応するガード（DuckDB 0.10 の制約回避）。
  - 各モジュールでログ出力（INFO/DEBUG/WARNING）を適切に追加。
  - 多くの関数で look-ahead バイアス防止（datetime.today()/date.today() を直接参照しない設計）を採用。

Fixed
- calc_score_weights: 全銘柄のスコア合計が 0.0 の場合に等金額配分にフォールバックするよう実装（WARNING ログを追加）。
- .env パーサー: クォート内のバックスラッシュエスケープやインラインコメント処理の対応を追加して不正な読み込みを減少。
- run_monitoring: MONITOR_POLL_INTERVAL の不正値（0 以下や非整数）を検出してデフォルトにフォールバックする安全策を導入。
- DuckDB 書き込み処理: 空 params に対する executemany 実行を回避して互換性を確保。

Security
- 必須環境変数未設定時に明示的なエラーを返す仕組みを導入（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）。
- OpenAI API キーが未設定の場合、ai モジュールのスコアリング関数は ValueError を送出して安全に中断する。

Notes
- 多くのアルゴリズム（ポートフォリオ構成、ポジションサイズ計算、ファクター計算、特徴量解析）は副作用を持たない純粋関数として実装されており、ユニットテストや再利用を想定した設計になっています。
- Run スクリプトは起動時にプロセス優先度を high に設定しようと試みますが、権限不足や未対応プラットフォームでは警告ログを出して継続します。
- AI 関連処理は API の不安定性を考慮したリトライ・検証・部分書き込み保護を実装しており、API 障害があってもシステム全体の破綻を防ぐ設計です。
- DuckDB はリサーチ・AI 用の時系列テーブル（prices_daily, raw_financials, raw_news, news_symbols, ai_scores, market_regime 等）を前提としており、これらのテーブル構造は別途管理されます。

今後の予定（参考）
- stocks マスターに lot_size を持たせ、銘柄別単元丸めに対応する拡張。
- position_sizing のコスト推定（手数料・スリッページ）をより詳細に扱う実装。
- AI モデルやプロンプトのチューニング、レスポンス検証の強化。

--- 

（注）本 CHANGELOG はリポジトリ内のソースコードからの推測に基づいて作成しています。実際のリリースノートやドキュメントは開発履歴やリリース方針に合わせて調整してください。