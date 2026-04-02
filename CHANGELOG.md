Keep a Changelog
=================
すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトはセマンティックバージョニングに従います。

フォーマット
-----------
各リリースは「Added / Changed / Fixed / Security / Deprecated / Removed / Breakin​g changes」等のセクションでまとめています。

[0.1.0] - 2026-04-02
--------------------
初回リリース。コードベースから推測される主要機能・実装をまとめています。

Added
- パッケージ基本構成
  - kabusys パッケージ初期化（__version__ = 0.1.0、公開モジュール: data, strategy, execution, monitoring）。
- 環境設定・自動 .env ロード
  - 環境変数読み取り・管理モジュールを追加 (kabusys.config)。
  - プロジェクトルート検出ロジックを実装（.git または pyproject.toml を基準）。
  - .env / .env.local の自動ロード（優先順位: OS 環境変数 > .env.local > .env）。自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env パーサは export 構文・シングル/ダブルクォート・エスケープ・インラインコメント対応。
  - Settings クラスを提供し、J-Quants / kabu ステーション / Slack / DB パス /監視閾値 /環境（development/paper_trading/live）等のプロパティを型変換つきで公開。
  - 必須環境変数未設定時に ValueError を送出する _require を提供。
  - デフォルト値（例: KABUS_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH, CPU/MEM 閾値等）を定義。

- AI モジュール（ニュース解析・レジーム判定）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols から銘柄別記事を集約し、OpenAI（gpt-4o-mini）へバッチ送信して銘柄ごとのセンチメント ai_score を算出。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算機能を実装（calc_news_window）。
    - API 呼び出しは JSON Mode を期待し、レスポンスの厳格なバリデーションとスコアクリップ（±1.0）を実装。
    - バッチサイズ、記事数上限、文字数トリム、リトライ（429・ネットワーク・タイムアウト・5xx に対する指数バックオフ）を実装。
    - 部分失敗に備え、スコア取得済みコードのみ ai_scores テーブルへ置換（DELETE → INSERT）する冪等処理を実装。
    - テスト用に _call_openai_api を patch できる設計。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロ経済ニュース LLM センチメント（重み 30%）を組み合わせて日次レジーム（bull/neutral/bear）を判定。
    - prices_daily, raw_news, market_regime テーブルを使用。ma200_ratio 算出、マクロニュース抽出、OpenAI 呼び出し、スコア合成、冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - OpenAI 呼び出しは独立実装でモジュール間の結合を避ける。
    - API 失敗時は macro_sentiment = 0.0 にフォールバックするフェイルセーフ、レスポンスパース失敗や一部 HTTP エラーのリトライ処理を実装。
    - ルックアヘッドバイアスを避けるため内部で date.today()/datetime.today() を参照しない設計。

- データ基盤（kabusys.data）
  - ETL パイプライン（kabusys.data.pipeline）
    - ETLResult データクラスを定義（取得件数、保存件数、品質問題、エラー等を格納）。
    - 差分更新・バックフィル・品質チェックのためのユーティリティを実装（最終取得日の判定、テーブル存在確認等）。
    - J-Quants クライアントとの連携ポイント（jq.*）を想定した設計。
  - ETL の公開インターフェース（kabusys.data.etl）に ETLResult を再エクスポート。
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルを用いた営業日判定ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB データがない場合の曜日ベースのフォールバック実装（土日を非営業日扱い）。
    - カレンダー夜間更新ジョブ（calendar_update_job）を実装：J-Quants から差分取得し冪等保存、バックフィルや健全性チェックを備える。
    - 最大探索日数、バックフィル日数、先読みに関する定数を定義。
  - データ品質チェック連携（quality モジュールを想定）に準備。

- 研究用ツール群（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR, ATR 比率）、Value（PER, ROE）等を DuckDB 上の SQL で実装。
    - 関数: calc_momentum, calc_volatility, calc_value。各関数は (date, code) をキーとする dict のリストを返す。
    - データ不足に対する None ハンドリング、ログ出力あり。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算 (calc_forward_returns)、IC（スピアマン ρ）計算 (calc_ic)、ランク変換 (rank)、統計サマリー (factor_summary) を実装。
    - pandas 等外部依存を避け、純粋 Python + DuckDB で実装。
  - zscore 正規化ユーティリティを kabusys.data.stats から再エクスポート。

- ロギング・エラーハンドリング
  - 各モジュールで詳細な logger.debug/info/warning/exception を追加。DB 書き込みはトランザクション（BEGIN/COMMIT/ROLLBACK）で保護。
  - API 関連はリトライ・バックオフ・非致命的失敗時のフォールバック（0.0 やスキップ）を採用し、全体処理の堅牢性を高める。

Notes / Limitations
- OpenAI
  - gpt-4o-mini（JSON mode）を想定。API キーは引数または環境変数 OPENAI_API_KEY を使用。
  - レスポンスは厳密な JSON を期待するが、余剰テキスト混入時の復元（最外の {} を抽出）に対応する実装あり。
- データベース
  - DuckDB を前提に SQL を記述。executemany の空リストバインドに対する互換性配慮あり（空の場合は呼ばない）。
- 未実装 / TODO（明記）
  - 現フェーズで PBR や配当利回りなどのバリューファクターは未実装（コメントあり）。
  - strategy / execution / monitoring の具体的な実装は本差分では省略（パッケージ定義上は存在を想定）。
- テスト性
  - OpenAI 呼び出しは個別の _call_openai_api をパッチ可能にしてテストを容易にする設計。

Security
- 必須の機密情報（例: OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）は環境変数で提供する必要あり。未設定時は Settings プロパティが例外を送出する箇所があるため注意。
- .env の自動ロード機能は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。

Breaking Changes
- 初回リリースのため該当なし。

参考: 重要な環境変数
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector 用）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン
- KABU_API_PASSWORD: kabu ステーション API 用パスワード
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知用
- DUCKDB_PATH / SQLITE_PATH: データベースファイルのデフォルトパス
- KABUSYS_ENV: development / paper_trading / live
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env 読み込みを無効化するフラグ

今後のリリースで検討する改善点（例）
- strategy / execution / monitoring の具体実装とエンドツーエンド統合テスト
- モデル選択や温度など AI 呼び出しの設定柔軟化
- より詳細な品質チェックルールの追加と自動アラート連携
- ETL の分散化・差分フェッチ戦略の最適化

----- END -----