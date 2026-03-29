# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠しています。  

なお本 CHANGELOG は与えられたソースコードの内容から機能・設計方針を推測して作成しています。

## [Unreleased]

(なし)

## [0.1.0] - 2026-03-29

Initial release — 日本株自動売買 / データプラットフォーム基盤の初期実装。

### Added
- パッケージ基盤
  - kabusys パッケージの公開インターフェースを追加（__version__ = 0.1.0、サブパッケージ data, strategy, execution, monitoring を __all__ に指定）。
- 設定管理
  - kabusys.config: .env ファイルおよび環境変数から設定を読み込む Settings クラスを追加。
    - 自動的にプロジェクトルート（.git または pyproject.toml）を探索して .env/.env.local を読み込む機能を実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
    - .env パーサは export 形式・クォート・エスケープ・行内コメントを考慮した堅牢な実装。
    - 必須キー取得時に未設定なら ValueError を投げる _require() を提供。
    - KABUSYS_ENV（development/paper_trading/live）・LOG_LEVEL のバリデーション機能を備える。
    - データベースパス設定（DUCKDB_PATH / SQLITE_PATH）を Path 型で返すユーティリティを追加。
- AI（ニュースNLP / レジーム判定）
  - kabusys.ai.news_nlp:
    - raw_news と news_symbols を集約して銘柄ごとのニュースを OpenAI（gpt-4o-mini）へ送信し、各銘柄のセンチメント（ai_score）を ai_scores テーブルへ書き込む score_news を実装。
    - 処理はタイムウィンドウ（JST: 前日15:00〜当日08:30）に基づく集計を行い、1チャンク最大20銘柄でバッチ送信。
    - スコアのバリデーション、JSON 抽出（前後の余計なテキストを切り出す耐性）、スコアの ±1.0 クリップ、部分書き換え（DELETE → INSERT）による冪等性確保を実装。
    - ネットワーク/429/タイムアウト/5xx に対する指数バックオフリトライとフェイルセーフ（失敗時は当該チャンクをスキップ）。
    - テスト容易性のため _call_openai_api をモック差し替え可能に設計。
  - kabusys.ai.regime_detector:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を判定する score_regime を実装。
    - prices_daily/raw_news からのデータ取得、macros キーワードでのフィルタ、OpenAI 呼び出し（gpt-4o-mini）、スコア合成、market_regime テーブルへの冪等書き込みを実装。
    - API 呼び出し失敗時は macro_sentiment = 0.0 にフォールバックするフェイルセーフを実装。
    - LLM 呼び出しに対するリトライ／エラーハンドリングを実装。
- データプラットフォーム（Data）
  - kabusys.data.calendar_management:
    - JPX 市場カレンダー取得・更新の夜間バッチ（calendar_update_job）を実装。
    - market_calendar テーブルの有無に応じたフォールバック（曜日ベース）を提供。is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を実装。
    - カレンダー取得はバックフィル（日数指定）と健全性チェックを備え、冪等に保存する設計（jq.fetch_market_calendar / jq.save_market_calendar を呼び出す）。
  - kabusys.data.pipeline / etl / ETLResult:
    - ETL パイプライン用の ETLResult データクラスを公開（kabusys.data.etl で再エクスポート）。
    - 差分更新・バックフィル・品質チェック統合を想定した設計（品質問題は収集して上位で判断する方針）。
    - DuckDB 上での最大日付取得、テーブル存在チェック等のユーティリティを実装。
- Research（因子・特徴量探索）
  - kabusys.research.factor_research:
    - モメンタム（1M/3M/6M リターン、MA200乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金/出来高比）およびバリュー（PER, ROE）を prices_daily / raw_financials から計算する関数群を実装: calc_momentum, calc_volatility, calc_value。
    - DuckDB 上で SQL を用いて効率的に計算。データ不足時は None を返す堅牢な設計。
  - kabusys.research.feature_exploration:
    - 将来リターン計算 calc_forward_returns（任意ホライズン対応、ホライズン上限チェック）。
    - IC（Spearman の ρ）計算 calc_ic（ランク相関）、rank ユーティリティ、factor_summary による統計要約を実装。
    - 標準ライブラリのみでの実装、欠損・有限性チェックを行う。
- 共通・設計方針
  - ルックアヘッドバイアス防止: 各処理は datetime.today()/date.today() を内部参照しないか、引数で target_date を受け取る設計。
  - DuckDB の executemany 空リスト制約への対応（空リストは呼ばないガード）。
  - ロギングを適切に出力（info/debug/warning/exception）、DB トランザクションは BEGIN / COMMIT / ROLLBACK を明示的に扱う冪等書き込み。
  - OpenAI API キーは引数で注入可能。環境変数 OPENAI_API_KEY もサポート。未設定時は ValueError を送出して明示的に扱う。

### Changed
- (初回リリースのため該当なし)

### Fixed
- (初回リリースのため該当なし)

### Security
- API キーや機密情報は環境変数経由で管理する設計（.env 自動ロードは必要に応じて無効化可能）。
- .env 読み込み時に OS 環境変数を上書きしない挙動や protected set による保護を実装。

### Notes
- OpenAI SDK のエラー型（APIError の status_code）差異に対する互換性処理が入っており、5xx 系とそれ以外でリトライ挙動を切り分けています。
- テスト容易性のため、AI モジュールの _call_openai_api 関数を unittest.mock.patch で差し替え可能な設計になっています。
- 実運用では DuckDB と J-Quants / kabu ステーション等の外部サービス接続設定（環境変数）を適切に設定する必要があります。

---

(本 CHANGELOG はソースコードからの推測に基づくため、実際のリリースノートとは差異がある可能性があります。必要に応じて補足・修正してください。)