# Changelog

すべての変更は「Keep a Changelog」仕様に準拠します。  
なお本リリースはパッケージ内の実装内容から推測して作成した初回リリース向けのまとめです。

※ バージョン: 0.1.0 — 2026-03-28

## [Unreleased]

なし。

## [0.1.0] - 2026-03-28

### Added
- パッケージ初期導入
  - kabusys パッケージ初期バージョンを追加。パッケージバージョンは `kabusys.__version__ == "0.1.0"`。

- 環境設定・初期化
  - kabusys.config: .env ファイルおよび環境変数から設定を読み込むユーティリティを追加。
    - プロジェクトルート検出ロジック（.git または pyproject.toml を基準）により、CWDに依存せず自動で .env/.env.local をロード。
    - .env パーサは `export KEY=val` 形式、シングル/ダブルクォート、バックスラッシュエスケープ、行末コメントの扱い等に対応。
    - 読み込み順序: OS 環境変数 > .env.local > .env。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動読み込みを無効化可能。
    - Settings クラスを提供し、`kabusys.config.settings` を通じて設定値を取得可能（必須項目は取得時に検証して ValueError を送出）。
    - 環境変数のデフォルト値例: `KABUSYS_ENV`（development/paper_trading/live）、`LOG_LEVEL`（DEBUG/INFO/...）、`DUCKDB_PATH`/`SQLITE_PATH` のデフォルトパス。

- データプラットフォーム（DuckDB ベース）
  - kabusys.data.pipeline: ETL パイプラインの基盤を実装。
    - 差分取得、バックフィル、品質チェック、冪等保存の方針を実装（ETLResult データクラスを公開）。
  - kabusys.data.etl: `ETLResult` を再エクスポート。
  - kabusys.data.calendar_management: JPX（市場）カレンダー管理と営業日ロジックを実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day といったユーティリティを提供。
    - market_calendar が未取得の場合は曜日ベース（土日除外）でフォールバック。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等更新するジョブ（バックフィルや健全性チェック含む）。
  - 内部的に DuckDB を用いる設計。テーブル存在確認や日付変換のユーティリティを実装。

- リサーチ（ファクター計算 / 特徴量探索）
  - kabusys.research.factor_research: モメンタム / ボラティリティ / バリュー系ファクター計算を追加。
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）等を計算。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率等を計算。
    - calc_value: 最新の raw_financials と株価を組み合わせて PER / ROE を計算（EPS が 0/欠損時は None）。
    - DuckDB のウィンドウ関数を活用する SQL ベースの実装。
  - kabusys.research.feature_exploration: 将来リターン計算・IC（Information Coefficient）・統計サマリー等を追加。
    - calc_forward_returns: 指定ホライズン（例: 1,5,21 営業日）先のリターンを一度のクエリで取得。
    - calc_ic / rank / factor_summary: スピアマンランク相関（IC）計算、ランク変換、基本統計量計算を提供。
  - kabusys.research.__init__ で主要関数を公開（zscore_normalize は kabusys.data.stats から再利用）。

- AI（ニュース NLP / レジーム判定）
  - kabusys.ai.news_nlp: ニュース記事を OpenAI（gpt-4o-mini）でセンチメント解析し、銘柄ごとのスコアを ai_scores テーブルへ書き込む機能を実装。
    - タイムウィンドウ計算（JST基準→UTC換算、前日15:00〜当日08:30）を提供（calc_news_window）。
    - raw_news と news_symbols から銘柄ごとに記事を集約し、バッチ（最大 20 銘柄）で API 呼び出し。
    - 1 銘柄当たり最大記事数 / 最大文字数でトリム（トークン肥大化対策）。
    - JSON mode を用いた出力想定のバリデーション処理（JSON 抽出処理、結果フォーマット検証、数値変換、スコアの ±1.0 クリップ）。
    - レート制限（429）・ネットワーク断・タイムアウト・5xx に対する指数バックオフによるリトライ処理。
    - API 呼び出し部分はテスト容易性を考慮して差し替え可能（_call_openai_api を patch 可能）。
    - 書き込みは部分失敗に対して既存スコアを保護する（該当コードのみ DELETE → INSERT）。
    - パブリック API: `score_news(conn, target_date, api_key=None)`（戻り値は書き込んだ銘柄数）。kabusys.ai.__init__ では score_news を公開。
  - kabusys.ai.regime_detector: 日次の市場レジーム判定ロジックを実装（ETF 1321 の 200 日 MA 乖離 + マクロニュースの LLM センチメントを合成）。
    - _calc_ma200_ratio: ルックアヘッドを防ぐため target_date 未満のデータのみ使用。
    - _fetch_macro_news: マクロキーワードで raw_news をフィルタ（最大 20 件）。
    - _score_macro: OpenAI 呼び出し（gpt-4o-mini）で JSON レスポンスから macro_sentiment を抽出、エラー時は 0.0 にフォールバック。
    - 合成スコア = 0.7 * ma_component + 0.3 * macro_component を clip して regime_label を判定（bull/neutral/bear）。
    - market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）。
    - パブリック API: `score_regime(conn, target_date, api_key=None)`（成功時に 1 を返す、API キー未設定時は ValueError）。

- パッケージ公開インターフェース
  - kabusys.ai.__init__ で score_news を公開。
  - kabusys.research.__init__ で主要リサーチ関数を公開。
  - kabusys.data.etl で ETLResult を再公開。
  - top-level package の __all__ に ["data", "strategy", "execution", "monitoring"] を定義（将来的なサブパッケージ公開を想定）。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Security
- 初回リリースのため該当なし。

---

## デプロイ / 運用上の注意（要点）
- 必須環境変数
  - JQUANTS_REFRESH_TOKEN（J-Quants 用）, KABU_API_PASSWORD（kabu API）, SLACK_BOT_TOKEN / SLACK_CHANNEL_ID（Slack 通知）
  - OpenAI を利用する機能（score_news / score_regime）を呼ぶ場合は OPENAI_API_KEY が必要（api_key 引数で注入可）。
- .env 自動読み込み
  - デフォルトでプロジェクトルートの .env と .env.local を自動読み込みします。CI やテストで自動読み込みを止めたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- ログレベル / 環境
  - KABUSYS_ENV は "development" / "paper_trading" / "live" のいずれか。LOG_LEVEL は標準的なログレベル名（DEBUG 〜 CRITICAL）。
- DuckDB / SQLite のデフォルトパス
  - DUCKDB_PATH デフォルト: data/kabusys.duckdb
  - SQLITE_PATH デフォルト: data/monitoring.db
- ルックアヘッドバイアスの防止
  - AI / リサーチ / ETL の各処理は内部で datetime.today()/date.today() を直接参照せず、呼び出し元から target_date を明示的に渡す設計（バックテスト等でのリークを防止）。
- テスト容易性
  - OpenAI 呼び出しは内部で _call_openai_api を経由しており、ユニットテストでは patch により差し替え可能。

---

## 既知の制限 / 今後の改善候補
- kabusys.ai.__init__ では現時点で score_news を公開しているが、regime_detector の score_regime は明示的に __all__ に含めていない（将来的な公開検討）。
- raw_financials に基づく PBR・配当利回り等はまだ未実装（calc_value に注記あり）。
- DuckDB バージョン依存（executemany の挙動等）があるため、運用環境では想定バージョンでの動作確認を推奨。

---

作成: kabusys 0.1.0 のコードベースに基づく CHANGELOG（推測により記載）。必要であれば変更点を細分化してマージリクエスト単位やファイル単位での詳細な説明も作成します。