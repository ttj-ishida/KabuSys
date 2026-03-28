# Changelog

すべての注目すべき変更点を記録します。これは Keep a Changelog の形式に準拠しています。  
リリースポリシー：セマンティックバージョニングに準拠します。

## [0.1.0] - 2026-03-28

### Added
- パッケージ初期リリース。「KabuSys - 日本株自動売買システム」の基本モジュール群を提供。
  - パッケージメタ情報:
    - src/kabusys/__init__.py にて __version__ = "0.1.0"、公開サブパッケージ data, strategy, execution, monitoring を指定。

- 環境変数・設定管理
  - src/kabusys/config.py
    - .env / .env.local の自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml に基づく）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env パーサ実装（export 接頭辞、クォート内のエスケープ、インラインコメント等に対応）。
    - _load_env_file にて override/protected（OS 環境変数の保護）を考慮したロードを実現。
    - Settings クラスを提供し、プロパティ経由で設定を取得:
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
      - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
      - DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（デフォルト data/monitoring.db）
      - KABUSYS_ENV（development/paper_trading/live のバリデーション）、LOG_LEVEL（DEBUG/INFO/...のバリデーション）
      - is_live / is_paper / is_dev の補助プロパティ

- AI（ニュース NLP / レジーム判定）
  - src/kabusys/ai/news_nlp.py
    - raw_news / news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini、JSON mode）へバッチ送信して銘柄単位のセンチメント（ai_score）を算出し ai_scores テーブルへ書き込むフローを実装。
    - タイムウィンドウ計算（JST基準）用の calc_news_window を提供。
    - バッチサイズ、記事数・文字数上限、JSON レスポンスのバリデーション、±1.0 のスコアクリップ、エクスポネンシャルバックオフによる再試行ロジックを実装。
    - API キー注入可能（引数 or 環境変数 OPENAI_API_KEY）。API未設定時は ValueError を送出。
    - 部分成功に配慮した DB 書き込み（取得できたコードのみ DELETE → INSERT）を実装。
    - 公開関数: score_news(conn, target_date, api_key=None) を提供（取得書込銘柄数を返す）。

  - src/kabusys/ai/regime_detector.py
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を組み合わせて日次の市場レジーム（bull/neutral/bear）を判定するスコアリングを実装。
    - マクロキーワードによる raw_news フィルタ、OpenAI（gpt-4o-mini）呼び出し（独自の _call_openai_api 実装）、再試行・エラーハンドリング（ネットワーク/レート/5xx に対するリトライ）を実装。
    - DB 書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で行う。API失敗時は macro_sentiment=0.0 としてフェイルセーフに継続。
    - 公開関数: score_regime(conn, target_date, api_key=None) を提供（成功時 1 を返す）。

- リサーチ（ファクター計算 / 特徴量探索）
  - src/kabusys/research/*
    - factor_research.py: モメンタム（1M/3M/6M、200日MA乖離）、ボラティリティ（20日ATR）、流動性（20日平均売買代金・出来高比率）、バリュー（PER, ROE）を DuckDB 上の prices_daily / raw_financials を元に計算する関数群を提供:
      - calc_momentum(conn, target_date)
      - calc_volatility(conn, target_date)
      - calc_value(conn, target_date)
    - feature_exploration.py: 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク付けユーティリティ（rank）、ファクター統計サマリ（factor_summary）を実装。
    - zscore_normalize は data.stats から再エクスポート。
    - 返り値は (date, code) をキーとした dict のリストで、外部 API へはアクセスしない設計。

- データプラットフォーム関連
  - src/kabusys/data/calendar_management.py
    - market_calendar を元に営業日判定・次/前営業日取得・期間内営業日列挙・SQ日判定・夜間バッチ更新（calendar_update_job）を提供。
    - DB にカレンダー情報が無い場合の曜日ベースのフォールバック、最大探索日数制限（_MAX_SEARCH_DAYS）など堅牢性設計を実装。
    - calendar_update_job は J-Quants クライアント（jquants_client）を用いた差分取得・バックフィル・健全性チェック・save（冪等）を行う。

  - src/kabusys/data/pipeline.py / etl.py
    - ETLResult データクラスを公開（etl.py で再エクスポート）。
    - ETL パイプラインの補助関数群（最終日取得、テーブル存在チェック、トレーディングデイ調整など）を実装。
    - ETLResult は品質チェック結果（quality.QualityIssue）やエラー概要を保持し、to_dict() によりシリアライズ可能。
    - ETL 設計: 差分取得、backfill による後出し修正吸収、品質チェックは収集後に呼び出し元で判断する方式。

- 内部ユーティリティ
  - DuckDB 値の安全な date 変換、SQL の互換性配慮（executemany の空リスト回避等）など。

### Changed
- 初回リリースのため、過去バージョンからの変更はありません。

### Fixed
- 初回リリースのため、バグ修正履歴はありません。

### Removed
- 初回リリースのため、削除項目はありません。

### Security
- OpenAI API キーは関数引数で注入可能で、環境変数 OPENAI_API_KEY を参照する設計。API キー未設定時は明示的にエラーを返す。
- .env 自動ロードの無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）を用意し、テスト等で環境汚染を防止可能。

---

注記:
- 本バージョンでは複数の外部サービス（OpenAI, J-Quants, kabuステーション）が利用されるため、実行環境に応じた環境変数の設定 (.env.example 相当) と DuckDB/SQLite の準備が必要です。
- 多くの関数は「ルックアヘッドバイアス防止」のため datetime.today()/date.today() を直接参照せず、target_date を必須引数として受け取る設計です。