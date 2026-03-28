# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、SemVer を採用します。

なお、以下は提供されたコードベースから推測して作成した変更履歴です。

## [Unreleased]
- 開発中の変更や次リリースでの予定事項を記載します。

## [0.1.0] - 2026-03-28
初回公開リリース。

### 追加
- パッケージ基盤
  - kabusys パッケージの基本構成を追加。バージョンは 0.1.0。
  - __all__ に data, strategy, execution, monitoring を公開するエントリポイントを設定。

- 環境設定・ロード
  - 環境変数管理モジュールを追加（kabusys.config）。
    - .env / .env.local ファイルの自動検出・読み込み機能（プロジェクトルートは .git または pyproject.toml を検索して決定）。
    - export KEY=val 形式、クォート／エスケープ、インラインコメントなどに対応したパーサを実装。
    - OS 環境変数保護（.env の上書き制御）と .env.local による上書き優先処理をサポート。
    - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を追加。
    - 必須環境変数取得時に未設定なら ValueError を送出する Settings クラスを実装。
    - 設定プロパティ例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL。env 値の検証を実装（有効な値集合の検査）。
    - Settings に便利プロパティ is_live / is_paper / is_dev を追加。

- ニュースNLP（AI）
  - kabusys.ai.news_nlp を追加。
    - raw_news / news_symbols を集約し、銘柄ごとにニュースを結合して OpenAI（gpt-4o-mini）でセンチメントを評価。
    - バッチ処理（最大 20 銘柄／コール）、1 銘柄あたりの最大記事数・文字数トリムを実装。
    - JSON mode のレスポンス検証・復元ロジック（前後に余計なテキストが混ざる場合の復元）を実装。
    - リトライ（429、ネットワーク断、タイムアウト、5xx）を指数バックオフで実施。
    - スコアを ±1.0 にクリップ、取得した銘柄のみ ai_scores テーブルへ置換（DELETE → INSERT）して部分失敗時に既存データを保護。
    - テストしやすいように OpenAI 呼び出し箇所を _call_openai_api で抽象化（patch で差し替え可能）。
    - calc_news_window ヘルパーを実装（JST ベースの集計ウィンドウを UTC naive datetime に変換）。

- レジーム判定（AI + テクニカル）
  - kabusys.ai.regime_detector を追加。
    - ETF 1321（日経225 連動）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - LLM 呼び出しは独立実装で、API 失敗時は macro_sentiment=0.0 とするフォールバックを採用（フェイルセーフ）。
    - DuckDB を使用したデータ取得／書き込み（market_regime テーブルへ冪等書き込み: BEGIN/DELETE/INSERT/COMMIT）を実装。
    - API エラーに対するリトライや 5xx 特殊処理を実装。
    - ルックアヘッドバイアスを避ける設計（date.today() を使わず、prices_daily クエリは target_date 未満の排他条件を採用）。

- データプラットフォーム（Data）
  - kabusys.data.pipeline を追加（ETL パイプライン基盤）。
    - ETLResult データクラスを公開（ETL 実行結果、品質チェック結果・エラーの集約）。
    - 差分取得、バックフィル、品質チェックの設計方針を実装。DuckDB を利用。
  - kabusys.data.etl で ETLResult を再エクスポート。
  - kabusys.data.calendar_management を追加。
    - market_calendar テーブルに基づく営業日判定ロジックを実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 未取得時の曜日ベースフォールバック、最大探索日数制限、健全性チェック、夜間バッチ更新 calendar_update_job を実装。
    - J-Quants クライアント（jquants_client）経由での差分取得と保存処理の呼び出しを統合。
    - 日付の扱いはすべて date オブジェクトで統一。

- Research（ファクター計算・特徴探索）
  - kabusys.research パッケージを追加。
    - factor_research: calc_momentum, calc_value, calc_volatility を実装（prices_daily / raw_financials に基づくファクター群）。
      - Momentum: 1M/3M/6M リターン、200 日 MA 乖離（データ不足時は None）。
      - Volatility: 20 日 ATR、相対 ATR、平均売買代金、出来高比など。
      - Value: PER（EPS が 0/欠損時は None）、ROE（最新財務データを結合）。
    - feature_exploration: calc_forward_returns（任意ホライズンの将来リターン）、calc_ic（Spearman ランク相関）、factor_summary（基本統計量）、rank（平均ランク処理）を実装。
    - kabusys.data.stats.zscore_normalize を re-export。

### 変更（設計上・実装上の注意）
- DuckDB 周りの実装で互換性問題や制約に配慮
  - executemany に空リストを渡すと失敗する DuckDB の挙動に対応するため、空チェックを追加。
  - 日付型の取り扱いで互換性を維持するため _to_date 等のユーティリティを実装。

- OpenAI 呼び出し周りの堅牢化
  - APIError の status_code 存在有無を安全に扱うため getattr を使用。
  - JSON 解析失敗時の保守的フォールバック（レスポンスパース失敗は警告ログを出してスコア 0.0 を返すなど）を採用。

- ルックアヘッドバイアス対策
  - AI モジュール・研究モジュールともに内部で datetime.today() / date.today() を直接参照せず、target_date を明示的に受け取る仕様に統一。

### 修正（バグ修正・回避策）
- レスポンスの JSON 解析で前後余計なテキストが混入するケースをハンドリング（最外の {} を抽出して復元）する処理を追加。
- market_regime / ai_scores への書き込みは冪等に行い、例外時は ROLLBACK を試行、ROLLBACK 失敗時は警告ログを出力するように実装。
- raw .env パーサの堅牢化（コメント・クォート・エスケープ処理の改善）。

### 既知の制約・注意事項
- OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY により供給する必要がある。未設定時は ValueError を送出する。
- AI スコアリングは LLM の応答に依存するため、外部 API の可用性により結果が影響を受ける。各所にフェイルセーフ（API 失敗時は 0.0 やスキップ）が実装されているが、運用時には API 制限・コストに注意すること。
- 一部関数は DuckDB に依存した SQL を使用しており、DuckDB バージョンやスキーマ変更時に修正が必要となる場合がある。
- logging のログレベル・出力先は設定（LOG_LEVEL 等）に従う。

---

今後の予定（例）
- strategy / execution / monitoring モジュールの実装（発注・実行ロジック、モニタリング通知）。
- テストカバレッジ拡充と CI 用のモック設定整備（OpenAI 呼び出し等の外部依存をモック化）。
- 性能改善（バッチ処理の並列化や DB クエリ最適化）。