# CHANGELOG

すべての notable な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

なお、このリリースはリポジトリ内のソースコードから推測して作成した初版リリースノートです。

## [0.1.0] - 2026-03-27

初回公開リリース。

### 追加 (Added)
- パッケージ基盤
  - パッケージのエントリポイントを追加（kabusys/__init__.py、__version__ = "0.1.0"）。
  - モジュール構成: data, strategy, execution, monitoring を公開。

- 環境設定管理 (kabusys.config)
  - .env ファイルと環境変数の自動読み込み機能を実装。
    - プロジェクトルートを .git または pyproject.toml から自動検出して .env / .env.local を読み込む。
    - 読み込み順序: OS 環境 > .env.local（上書き）> .env（未設定のみ設定）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能（テスト向け）。
  - .env パーサーは下記をサポート/考慮:
    - コメント行、先頭に `export ` を付けた形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの取り扱い。
  - Settings クラスを提供し、明示的な必須環境変数の取得メソッドを公開（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID 等）。
  - デフォルト値を含む設定: KABU_API_BASE_URL、DUCKDB_PATH（data/kabusys.duckdb）、SQLITE_PATH（data/monitoring.db）等。
  - KABUSYS_ENV と LOG_LEVEL の検証（許容値のバリデーション）を実装。

- AI 関連 (kabusys.ai)
  - ニュースセンチメント解析: news_nlp.score_news
    - raw_news と news_symbols から記事を集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄ごとのセンチメント（-1.0〜1.0）を算出し ai_scores テーブルへ書き込む。
    - 処理の特徴:
      - JST で前日 15:00 〜 当日 08:30 のウィンドウを UTC に変換して利用（calc_news_window）。
      - 1銘柄あたり記事上限（_MAX_ARTICLES_PER_STOCK）、文字数上限（_MAX_CHARS_PER_STOCK）でトリム。
      - 最大バッチサイズ: 20 銘柄 / API コール。
      - 429、ネットワーク断、タイムアウト、5xx に対する指数バックオフリトライを実装。
      - レスポンスの厳密なバリデーション（JSON 抽出、results 配列、code/scoreの整合性、数値チェック、既知コードのフィルタリング）。
      - スコアは ±1.0 にクリップ。
      - DuckDB の executemany に関する互換性を考慮し、空パラメータを送らないガードを実装。
      - API 呼び出しは差し替え可能（テスト用に _call_openai_api をモック可能）。
  - 市場レジーム判定: regime_detector.score_regime
    - ETF 1321（Nikkei 225 連動 ETF）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出。
    - 設計上の留意点:
      - ルックアヘッドバイアス防止（datetime.today()/date.today() を参照しない、prices_daily の date < target_date）を徹底。
      - LLM（OpenAI）呼び出しに対するリトライと 5xx の扱いを実装。最終的に失敗した場合は macro_sentiment=0.0 をフェイルセーフとして使用。
      - レジーム結果は market_regime テーブルへ冪等に保存（BEGIN / DELETE / INSERT / COMMIT）。
    - 使用モデル: gpt-4o-mini（デフォルト）、リトライ回数やバックオフの定数を内部で定義。

- データ処理・ETL (kabusys.data)
  - ETL 結果を表すデータクラス ETLResult を公開（kabusys.data.pipeline）。
    - ETL の取得数/保存数、品質チェック結果、エラー情報を保持。has_errors / has_quality_errors / to_dict を提供。
  - pipeline モジュールに ETL ユーティリティ（差分取得、品質チェック、バックフィル、calendar の先読み等）の基盤を実装。
    - 最小データ日やカレンダー先読み、デフォルトバックフィル日数などの定義。
    - DuckDB 上での最大日付取得やテーブル存在確認ユーティリティを実装。
  - カレンダー管理: calendar_management
    - market_calendar を用いた営業日判定・探索ロジックを提供:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - DB にカレンダー情報が無い場合のフォールバックを実装（曜日ベースで土日を非営業日扱い）。
    - calendar_update_job により J-Quants API から差分取得して market_calendar を冪等保存（fetch + save のワークフロー）。
    - バックフィル / 健全性チェック（将来日付の異常検出）を実装。
  - jquants_client を介した外部 API 連携を想定（実装参照箇所あり、クライアント実装は別ファイル）。

- 研究用ユーティリティ (kabusys.research)
  - ファクター計算・探索関係を実装:
    - calc_momentum, calc_value, calc_volatility（ファクター群）
      - Momentum: 1M/3M/6M リターン、MA200乖離（不足時 None）。
      - Volatility: 20日 ATR、相対 ATR、平均売買代金、出来高比率。
      - Value: PER（EPS が 0/欠損なら None）、ROE（raw_financials から取得）等。
    - feature_exploration: calc_forward_returns（任意ホライズン）、calc_ic（Spearman ランク相関）、factor_summary、rank
    - zscore_normalize を data.stats から再エクスポート。
  - 実装方針:
    - DuckDB と SQL を中心に実装。外部ライブラリ（pandas 等）に依存しない。
    - ルックアヘッドバイアス防止を重視（datetime.today() を参照しない）。
    - 戻りは (date, code) をキーとした辞書リスト形式。

### 変更 (Changed)
- （初回リリースにつき該当なし）

### 修正 (Fixed)
- （初回リリースにつき該当なし）
- 実装上の堅牢性として以下を取り入れ:
  - OpenAI レスポンスの JSON 抽出処理を堅牢化（余分な前後テキストが混入する場合に最外の {} を抽出して復元）。
  - API 呼び出し失敗時のフェイルセーフ（ニュースとレジーム判定で macro_sentiment=0.0 や空スコア扱いで継続）。
  - DuckDB の executemany における空リストバインド制約に対応するガード。

### セキュリティ (Security)
- OpenAI API キー（OPENAI_API_KEY）を使用するため、外部サービスとの通信に関する秘密情報の管理に注意が必要。
- 環境変数の自動読み込みを行うが、OS 環境変数はデフォルトで保護（.env による上書き時に保護される）される仕組みを実装。

### 既知の注意点 / マイグレーションノート (Notes)
- 環境変数の必須項目を正しく設定してください（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY）。未設定の場合は Settings のプロパティで ValueError を送出します。
- .env の自動ロードはプロジェクトルートの検出に依存します（.git または pyproject.toml が存在するディレクトリ）。
  - 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時に有用）。
- OpenAI 呼び出しは内部で retry/backoff を実装していますが、API 使用料やレートリミットに注意してください。
- DuckDB による executemany の空リスト問題に対処したため、古い DuckDB の挙動との差異に留意してください（実行前にテーブルが存在するかチェックする実装あり）。
- 日付処理は全て date 型で統一され、タイムゾーン混入を避ける設計（ニュースウィンドウは UTC naive datetime を内部で扱う）。
- テスト/モックの容易性のため、OpenAI 呼び出し部は内部関数（_kabusys.ai.*._call_openai_api）で定義されており、unittest.mock.patch による差し替えが想定されています。

今後の予定（例）
- strategy / execution / monitoring の具体実装（本リリースではエントリのみ公開）。
- 機械学習モデルの改良、LLM プロンプトの調整、追加の品質チェックや監視機能の追加。

--- 

（上記は現行コードベースを基に推測して作成した CHANGELOG です。実際のリリースノートはプロジェクトの意図に合わせて編集してください。）