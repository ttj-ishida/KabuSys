# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。フォーマットは Keep a Changelog に準拠し、セマンティック バージョニングを使用します。

現在のバージョン
- 0.1.0 — 2026-03-27

---

## [0.1.0] - 2026-03-27

初回リリース。日本株自動売買 / データ基盤のコア機能を提供します。以下の主要機能と設計方針を実装しています。

### 追加 (Added)
- パッケージ基礎
  - kabusys パッケージの初期公開（__version__ = 0.1.0）。
  - パッケージ公開インターフェースに data, strategy, execution, monitoring を含める。

- 環境設定 / 設定管理
  - 環境変数自動ロード機能を実装（.env / .env.local をプロジェクトルート（.git または pyproject.toml）基準で探索）。
    - ロード順序: OS環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサーの実装:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理を考慮。
    - クォートなしの場合、'#' は直前がスペース/タブのときのみコメントとみなす。
  - Settings クラスを実装し主要設定値をプロパティとして提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）、SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（development / paper_trading / live のバリデーション）および LOG_LEVEL のバリデーション
    - is_live / is_paper / is_dev ヘルパー

- AI（ニュース NLP / レジーム判定）
  - kabusys.ai.news_nlp.score_news
    - raw_news と news_symbols を集約し、銘柄ごとに OpenAI（gpt-4o-mini）でセンチメントを算出して ai_scores テーブルへ書き込む。
    - タイムウィンドウ定義（JST）を calc_news_window(target_date) で提供（前日15:00 JST ～ 当日08:30 JST を対象）。
    - バッチ処理（最大 20 銘柄 / API コール）、1銘柄あたりの最大記事数および文字数トリム（デフォルト: 10記事, 3000文字）。
    - JSON Mode レスポンスのバリデーション、スコアの ±1.0 クリップ。
    - レート制限・ネットワーク断・5xx に対する指数バックオフリトライ。
    - API キーは api_key 引数か環境変数 OPENAI_API_KEY で指定可能。未指定時は ValueError。
    - DB 書き込みは冪等: 対象コードのみ DELETE → INSERT（部分失敗時に他コードの既存スコアを保護）。
  - kabusys.ai.regime_detector.score_regime
    - ETF 1321（日経225レバ連動）の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次市場レジーム（bull/neutral/bear）を判定・market_regime テーブルへ保存。
    - ma200_ratio 計算は target_date 未満のデータのみを使用しルックアヘッドバイアスを回避。
    - マクロニュース抽出はニュースタイトルのキーワード検索（多数の国内外マクロキーワードを定義）。
    - OpenAI 呼び出しは独立実装で最大リトライを行い、API 失敗時は macro_sentiment = 0.0 でフォールバック（例外を投げず継続）。
    - 結果はトランザクション（BEGIN / DELETE / INSERT / COMMIT）で冪等に保存。

- データ基盤（Data）
  - calendar_management モジュール
    - JPX カレンダー管理のユーティリティを実装:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days を提供。
    - market_calendar が未取得の場合は曜日ベース（土日非営業日）でフォールバック。
    - 最大探索日数 (_MAX_SEARCH_DAYS) を導入して無限ループを回避。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等に更新（バックフィルと健全性チェックを含む）。
  - pipeline / ETL
    - ETLResult dataclass を公開（kabusys.data.etl で再エクスポート）。
    - pipeline モジュール内で差分取得、保存、品質チェックのためのユーティリティを実装（J-Quants クライアントおよび quality チェックと連携）。
    - DB からの最大日付取得やテーブル存在確認などのヘルパー実装。

- Research（リサーチ）
  - kabusys.research パッケージにファクター計算・特徴量探索を実装・公開:
    - calc_momentum: 1M/3M/6M リターン、200日MA乖離を計算（データ不足時は None）。
    - calc_volatility: 20日 ATR、相対ATR、平均売買代金、出来高比率などを計算。
    - calc_value: raw_financials から EPS/ROE を取得して PER/ROE を算出。
    - calc_forward_returns: 将来リターン（任意の営業日ホライズン）を取得。
    - calc_ic: スピアマンランク相関（IC）計算（NULL/不十分データでの保護）。
    - factor_summary / rank / zscore_normalize（zscore_normalize は kabusys.data.stats から再エクスポート）。
  - いずれも DuckDB 接続のみを使用し外部ライブラリ（pandas 等）に依存しない設計。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 既知の設計上の決定 / 注意点 (Notable Design Decisions)
- ルックアヘッドバイアス対策: score_news / score_regime などの分析系は内部で datetime.today() / date.today() を参照せず、必ず caller が target_date を渡す設計になっています。
- フェイルセーフ: 外部 API (OpenAI 等) の不調時はスコアを 0.0 にフォールバックするなど、例外発生によるパイプライン全体の停止を避ける動作を優先しています（ただし DB 書き込みエラー等は上位へ伝播）。
- DB 書き込みは可能な限り冪等に実装（DELETE→INSERT 等）されており、部分失敗時のデータ保護を行います。
- OpenAI 呼び出しは JSON Mode（response_format={"type":"json_object"}）を使い、レスポンスパースを厳密に検証する実装です。レスポンスに余分なテキストが混入する場合の復元ロジックも含みます。

### 依存関係 / 必要環境
- DuckDB を想定した DB 接続を多用。
- OpenAI API（gpt-4o-mini）を利用。OPENAI_API_KEY を環境変数または関数引数で指定する必要あり。
- J-Quants からのデータ取得用のクライアント（kabusys.data.jquants_client）が呼び出される設計（実際の API クライアント実装/設定が必要）。
- 環境変数必須項目:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - SLACK_BOT_TOKEN
  - SLACK_CHANNEL_ID

### 既知の制限 / TODO
- PBR・配当利回りなどのバリューファクターの一部指標は未実装（コメントで明記）。
- jquants_client の具象実装は環境に依存するため、実稼働前に接続設定やトークンの準備が必要。
- 一部 DuckDB バインドの互換性（executemany に空リスト渡せない等）への対応がコード内に存在し、将来の DuckDB バージョン変更で見直しが必要になる可能性あり。

---

今後のリリースで追加予定の項目（例）
- strategy / execution / monitoring の具体的な取引実行・監視コンポーネントの公開と統合テスト
- モデル評価用のユーティリティ（ウォークフォワードテスト等）
- より詳細な品質チェックルールの追加と自動アラート機能

---

（補足）報告・貢献
- バグ報告・改善提案やパッチは Issue / Pull Request で歓迎します。