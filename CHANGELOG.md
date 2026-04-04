# CHANGELOG

すべての重要な変更履歴をここに記録します。フォーマットは「Keep a Changelog」に準拠します。

## [Unreleased]

## [0.1.0] - 2026-04-04

初回リリース — 日本株自動売買／データ基盤のコアライブラリを追加。

### Added
- パッケージ基礎
  - kabusys パッケージ初期化（__version__ = 0.1.0）。公開モジュール: data, strategy, execution, monitoring。
- 設定管理
  - kabusys.config: .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env のパースは export プレフィックス、クォート/エスケープ、インラインコメント等に対応。
    - Settings クラスでアプリケーション設定をプロパティ経由で提供（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、OPENAI 用キーの参照、パス設定、監視閾値、環境値検証など）。
    - KABUSYS_ENV の許容値: development / paper_trading / live。LOG_LEVEL の検証あり。
- AI（自然言語処理）モジュール
  - kabusys.ai.news_nlp.score_news
    - raw_news と news_symbols を元にニュースを銘柄ごとに集約し、OpenAI（gpt-4o-mini、JSON mode）でセンチメントを算出して ai_scores テーブルへ書き込む。
    - タイムウィンドウ（JST 前日 15:00 〜 当日 08:30）を UTC に変換して DB クエリに使用。
    - バッチ処理（1回最大 20 銘柄）、記事数・文字数トリム、リトライ（429/ネットワーク/タイムアウト/5xx）と指数バックオフを実装。
    - レスポンスの厳密なバリデーションとスコアの ±1.0 クリップを行う。
    - API エラー時は該当チャンクをスキップして処理継続（フェイルセーフ）。
    - テスト用に _call_openai_api をパッチ可能（unittest.mock.patch を想定）。
  - kabusys.ai.regime_detector.score_regime
    - ETF 1321（日経225連動型）200日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込み。
    - マクロ記事はキーワードフィルタで抽出、OpenAI 呼び出しは最大リトライ・バックオフ・フォールバック（失敗時 macro_sentiment=0.0）。
    - OpenAI クライアント作成時は api_key 引数または環境変数 OPENAI_API_KEY を利用。
- データプラットフォーム
  - kabusys.data.calendar_management
    - JPX カレンダーの管理、営業日判定（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）、夜間バッチ更新ジョブ（calendar_update_job）を実装。
    - market_calendar が未取得の場合は曜日ベース（土日休）でフォールバック。
    - 最大探索範囲を設定して無限ループを防止。
  - kabusys.data.pipeline / etl / ETLResult
    - ETLResult データクラス（ETL 実行結果の集約）を公開。
    - pipeline モジュール設計に則った差分取得・保存・品質チェックのためのインターフェースを追加。
    - デフォルトのバックフィルやカレンダー先読みの定数を定義。
- 研究用ユーティリティ
  - kabusys.research: 各種ファクター計算や特徴量探索の公開インターフェースを追加。
    - factor_research.calc_momentum / calc_volatility / calc_value
      - モメンタム（1M/3M/6M・MA200乖離）、ボラティリティ（20日ATR、相対ATR、出来高指標）、バリュー（PER・ROE）を DuckDB の prices_daily/raw_financials から計算。
      - データ不足時の None 処理、ログ出力。
    - feature_exploration.calc_forward_returns / calc_ic / factor_summary / rank
      - 将来リターン計算（任意ホライズン）、IC（Spearman ランク相関）、統計サマリー、ランク変換を提供。
    - zscore_normalize は kabusys.data.stats から再エクスポート。
- 共通設計・実装上の注意点（初版の重要な仕様）
  - ルックアヘッドバイアス防止: datetime.today() / date.today() を直接参照せず、すべてのスコア/判定関数は target_date を引数で受ける。
  - DB 書き込みは可能な限り冪等（DELETE → INSERT、BEGIN/COMMIT/ROLLBACK）で実装。
  - DuckDB（duckdb Python 接続）を主要なローカル分析 DB として利用。
  - OpenAI 呼び出しは JSON mode（response_format={"type": "json_object"}）を利用し、レスポンスパースを厳密に行う。
  - 失敗に対するフェイルセーフ: LLM/API の失敗はゼロスコアやスキップで継続する設計。
  - テスト容易性のため、API 呼び出し箇所に差し替え可能なフックを用意。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Security
- 環境変数ロード時に OS 環境変数を上書きしないデフォルト挙動。自動ロード時は既存の OS 環境変数を保護するため protected set を使用し、.env.local の上書きは可能だが OS 環境は保護される設計。
- 必須の機密情報（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、OpenAI API キーなど）は未設定時に明確な例外を投げる（ValueError）。  

### Notes / Migration / Usage
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（必須プロパティとして Settings で取得）
  - OPENAI_API_KEY は AI モジュール（score_news / score_regime）で必須（関数引数で上書き可能）。
- .env の自動ロード:
  - プロジェクトルートは __file__ を起点に .git または pyproject.toml を探索して特定。配布後の実行でも CWD に依存しない。
- OpenAI モデル:
  - デフォルトで gpt-4o-mini を使用し、温度 0、タイムアウト 30 秒を設定。
- テスト時の考慮:
  - _call_openai_api のパッチ（unittest.mock.patch）により外部 API 呼び出しをモック可能。
- 時刻・ウィンドウ:
  - ニュース収集ウィンドウや calendar_update_job の挙動はコード内の定数で定義されているため、必要に応じて調整可能。

---

この CHANGELOG はコードから推測された機能と設計意図を元に作成しています。実際のリリースノートとして利用する場合は、リリース時の差分・コミット履歴・デプロイ手順に応じて追記・修正してください。