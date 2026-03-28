# CHANGELOG

すべての注目すべき変更点をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

## [0.1.0] - 2026-03-28

最初の公開リリース。日本株自動売買システム KabuSys のコア機能群を実装・公開しました。

### 追加（Added）
- パッケージ基盤
  - パッケージメタ情報を追加（kabusys.__version__ = 0.1.0）。
  - パッケージ外部公開モジュールの __all__ に data, strategy, execution, monitoring を追加。

- 設定 / 環境管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
    - プロジェクトルート検出は __file__ を起点に .git または pyproject.toml を探索して行うため、CWD に依存しない。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - OS の環境変数を保護する protected 機構を実装（.env の上書きを制御）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト用途）。
  - .env パーサーの強化:
    - export KEY=val 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理、コメント行や無効行の無視など。
  - Settings クラスを実装してアプリケーション設定をプロパティで公開。
    - 必須環境変数チェック（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）。
    - デフォルト値の提供（KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, KABUSYS_ENV）。
    - 環境値のバリデーション（KABUSYS_ENV、LOG_LEVEL の許容値検証）。
    - ヘルパープロパティ is_live / is_paper / is_dev を追加。

- データプラットフォーム（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar を用いた営業日判定ロジックを実装。
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days を提供。
      - market_calendar が欠けている場合は曜日ベースのフォールバック（週末を非営業日）を採用。
      - 最大探索日数や健全性チェックを実装して無限ループや異常値を防止。
    - calendar_update_job を実装し、J-Quants API から差分取得して冪等的に保存するバッチ処理を提供。
      - バックフィル・ルックアヘッド・サニティチェックをサポート。
      - jquants_client との連携を想定（fetch/save を利用）。
  - ETL パイプライン（kabusys.data.pipeline / kabusys.data.etl）
    - ETLResult データクラスを実装して ETL 実行結果（取得数・保存数・品質問題・エラー一覧）を集約。
    - 差分取得、バックフィル、品質チェック、冪等保存を想定したユーティリティ実装。
    - DuckDB を使用する前提のヘルパー関数（テーブル存在チェック、最大日付取得など）を実装。
    - kabusys.data.etl で ETLResult を再エクスポート。

- 研究・解析モジュール（kabusys.research）
  - factor_research モジュールを追加（calc_momentum, calc_value, calc_volatility）。
    - モメンタム（1M/3M/6M）、200日移動平均乖離、ATR（20日）、20日平均売買代金・出来高比率などを DuckDB SQL で計算。
    - データ不足時には None を返す設計。
    - DuckDB 内でウィンドウ関数を活用して効率的に計算。
  - feature_exploration モジュールを追加（calc_forward_returns, calc_ic, factor_summary, rank）。
    - 将来リターン計算（任意ホライズン）、Spearman ランク相関（IC）、ファクター統計サマリーを実装。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。
  - kabusys.research パッケージで必要な関数を再エクスポート（および zscore_normalize を data.stats から公開）。

- AI / NLP（kabusys.ai）
  - ニュースセンチメント解析（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約して銘柄別のニュースを作成し、OpenAI の Chat Completions（gpt-4o-mini）を JSON Mode で呼び出して銘柄ごとのセンチメントスコアを取得。
    - チャンク処理（デフォルト BATCH_SIZE=20）、1銘柄あたりの記事数・文字数の上限（MAX_ARTICLES_PER_STOCK / MAX_CHARS_PER_STOCK）でトークン肥大化に対応。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライを実装。
    - レスポンスの厳格なバリデーション処理（JSON 抽出、results 配列、code と score、未知コードの無視、スコアの有限性チェック、±1.0 のクリップ）。
    - 部分失敗に備え、ai_scores テーブルへはスコア取得済み銘柄のみ置換（DELETE → INSERT）して既存データを保護。
    - テスト容易性のため _call_openai_api を patch 可能に設計。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（weight 0.7）とマクロニュースの LLM センチメント（weight 0.3）を組み合わせて日次で市場レジーム（bull/neutral/bear）を算出して market_regime テーブルへ冪等書き込み。
    - マクロニュースは news_nlp.calc_news_window を使って対象ウィンドウを決定し、最大記事数制限・キーワードフィルタリングを実施。
    - OpenAI 呼び出しは専用実装で行い、API エラー時は macro_sentiment=0.0 にフォールバックするフェイルセーフを実装。
    - LLM 呼び出しでは gpt-4o-mini を利用し、JSON レスポンスを期待してパース・クリップを行う。
    - DB 書き込みはトランザクション（BEGIN / DELETE / INSERT / COMMIT）で冪等性を担保。失敗時は ROLLBACK を試行。

### 変更（Changed）
- なし（初期リリース）

### 修正（Fixed）
- なし（初期リリース）

### 注意事項（Notes）
- OpenAI API の利用
  - ai.news_nlp / ai.regime_detector は OpenAI API キー（引数または環境変数 OPENAI_API_KEY）を必要とします。未設定時は ValueError を送出します。
  - gpt-4o-mini と JSON Mode を前提に設計されています。モデルや SDK の変更がある場合はレスポンス処理の更新が必要です。
- データベース
  - DuckDB を主に利用する設計です。ai_scores / prices_daily / raw_news / raw_financials / market_regime / market_calendar 等のテーブルスキーマ前提の処理が多数あります。
- 環境変数（主な必須項目）
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - 既定のファイルパス: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"
- テスト支援
  - _call_openai_api 等はテスト時に patch できるよう設計されています。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動 .env 読み込みを無効化できます。

今後の予定（例）
- strategy / execution / monitoring モジュールの実装拡充（発注ロジック、実行・監視周りの統合）。
- ai モジュールの堅牢化（追加の入力前処理、出力正規化、カバレッジテスト）。
- ETL と品質チェックの詳細レポート化。

--------------------------------------------------------------------------------
この CHANGELOG にはユーザーにとって重要な変更点のみを記載しています。細かな実装変更や内部リファクタは省略しています。