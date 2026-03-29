# CHANGELOG

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。

なお、本ログはリポジトリ内のコードから機能・設計意図を推測して作成しています。

## [0.1.0] - 2026-03-29

初回リリース（推定）。以下の機能群を追加しました。

### 追加 (Added)
- パッケージ基盤
  - パッケージメタ情報を追加（kabusys.__version__ = 0.1.0）。
  - パッケージ公開 API: data, strategy, execution, monitoring を __all__ に追加。

- 設定・環境変数管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを追加。
  - 自動 .env ロード機能を実装（プロジェクトルートを .git または pyproject.toml から探索）。環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサ実装:
    - 空行・コメント行・`export KEY=val` 形式に対応。
    - シングル/ダブルクォート、バックスラッシュによるエスケープ処理、インラインコメント処理をサポート。
  - .env 読み込み時の上書き制御（`.env` と `.env.local` の優先度）および OS 環境変数保護機能を提供。
  - Settings に主要設定プロパティを実装:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH
    - KABUSYS_ENV（development / paper_trading / live のバリデーション）、LOG_LEVEL（DEBUG/INFO/... のバリデーション）
    - ヘルパー is_live / is_paper / is_dev

- データ関連 (kabusys.data)
  - ETL 用の公開型 ETLResult（pipeline.ETLResult）を再エクスポート。
  - ETL パイプライン（kabusys.data.pipeline）:
    - 差分取得・バックフィル・品質チェックの設計に基づく ETLResult dataclass を追加。
    - DuckDB を使った最終日付取得ユーティリティなどを実装。
    - ETL 実行結果の to_dict()（品質問題のシリアライズ）を提供。
  - マーケットカレンダー管理（kabusys.data.calendar_management）:
    - market_calendar テーブルを使った営業日/SQ判定ロジックを実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を追加。
    - calendar_update_job: J-Quants API から差分取得し冪等的に保存する夜間ジョブを実装。バックフィル・健全性チェックを含む。
    - DB未取得時は曜日ベース（平日）のフォールバックを行う設計。
    - 探索上限（_MAX_SEARCH_DAYS=60）などループ防止策を導入。

- AI・NLP（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）:
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini、JSON mode）でセンチメントスコアを算出して ai_scores に書き込む処理を実装。
    - タイムウィンドウ（前日15:00 JST～当日08:30 JST）を calc_news_window で計算。
    - バッチ処理（1回あたり最大20銘柄）、1銘柄当たりの最大記事数/文字数制限（データ肥大対策）を導入。
    - レスポンスのバリデーション（JSON 抽出、results 配列、code と score の検査）を実装し、不正レスポンスはスキップするフェイルセーフ設計。
    - API の429/ネットワーク断/タイムアウト/5xx に対する指数バックオフによるリトライを実装。
    - DuckDB への書き込みは部分失敗時に既存データを保護するため、書き込み対象コードのみ DELETE → INSERT で置換。
    - テスト容易性のため _call_openai_api を差し替え可能（unittest.mock.patch を想定）。
  - 市場レジーム判定（kabusys.ai.regime_detector）:
    - ETF 1321 の200日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - マクロニュースは news_nlp.calc_news_window を用いて抽出し、OpenAI（gpt-4o-mini）で評価。記事が無ければ LLM 呼び出しを行わず macro_sentiment=0.0 を採用。
    - スコア合成後、market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - LLM 呼び出しに対してリトライとフェイルセーフ（最終的に 0.0 フォールバック）を実装。
    - lookahead バイアスを防ぐため、datetime.today()/date.today() を直接参照せず、target_date を引数で指定する設計。

- リサーチ（kabusys.research）
  - factor_research:
    - モメンタム、ボラティリティ、バリュー等の定量ファクター計算関数を実装（calc_momentum, calc_volatility, calc_value）。
    - DuckDB の prices_daily / raw_financials テーブルを用いて SQL ベースで計算を行う設計（本番の発注や外部 API 呼び出しは行わない）。
    - 各関数は (date, code) をキーとする dict のリストを返す。
  - feature_exploration:
    - 将来リターン計算 calc_forward_returns（任意ホライズンに対応）、IC（calc_ic）やランク変換（rank）、統計サマリー（factor_summary）を実装。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。
  - 研究用ユーティリティをパッケージレベルで再エクスポート。

### 変更 (Changed)
- （初回リリースにつき該当なし）

### 修正 (Fixed)
- （初回リリースにつき該当なし）

### 注意事項 / マイグレーション (Notes)
- 必須環境変数:
  - OPENAI_API_KEY（AI モジュールを使用する場合）
  - JQUANTS_REFRESH_TOKEN（データ ETL 用）
  - KABU_API_PASSWORD（kabu API 使用時）
  - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID（Slack 通知を使用する場合）
- .env 自動読み込み:
  - パッケージインポート時にプロジェクトルート（.git または pyproject.toml）を基に .env / .env.local を自動ロードします。テストなどで無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB テーブル前提:
  - 多くの処理（news_nlp, regime_detector, research, calendar）は DuckDB の特定テーブル（prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials など）を参照します。実行前に対応テーブルの準備が必要です。
- Lookahead バイアス対策:
  - AI/スコア算出系の関数はいずれも target_date を外部から渡す設計で、datetime.today()/date.today() を関数内部で用いないようにしています。運用時は target_date を適切に指定してください。
- テスト容易性:
  - OpenAI 呼び出しを行う内部関数（_call_openai_api 等）は unittest.mock.patch による差し替えを前提に実装されています。

### セキュリティ (Security)
- API キー等の機密情報は .env または OS 環境変数で管理してください。Settings は未設定時に ValueError を投げて明示的に失敗するようになっています。

---

今後のリリースでは、バグ修正、パフォーマンス改善、外部 API（J-Quants / kabu）用の認証フロー強化、そしてテストカバレッジの拡張を予定しています。