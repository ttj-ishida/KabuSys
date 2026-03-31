Keep a Changelog 準拠の CHANGELOG.md を以下に作成しました。コードから推測できる主要な機能、API、設計方針や注意点を項目としてまとめています。必要に応じて日付や詳細を調整してください。

CHANGELOG.md
-------------

All notable changes to this project will be documented in this file.

フォーマットについては Keep a Changelog に準拠し、セマンティックバージョニングを使用しています。

Unreleased
----------

（現時点の開発中の変更点があればここに追記）

[0.1.0] - 2026-03-31
--------------------

Added
- パッケージ初回リリース（kabusys v0.1.0）。
- パッケージ公開インターフェース:
  - kabusys.__version__ = "0.1.0"
  - __all__ に data, strategy, execution, monitoring を定義。
- 環境設定管理:
  - kabusys.config モジュールを追加。
  - .env / .env.local の自動読み込み機能（プロジェクトルート自動検出: .git または pyproject.toml）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化サポート。
  - export KEY=val 形式やクォート・エスケープ、行末コメントなどに対応した .env パーサ実装。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DBパス / 環境モードなどのプロパティ経由で設定取得。必須変数未設定時は ValueError を送出。
  - サポートする環境値（development, paper_trading, live）やログレベル検証（DEBUG..CRITICAL）。
- AI（NLP）機能:
  - kabusys.ai.news_nlp:
    - ニュース記事を集約して OpenAI（gpt-4o-mini）でセンチメント評価し、ai_scores テーブルへ書き込む。
    - タイムウィンドウ（前日15:00 JST〜当日08:30 JST）計算ユーティリティ calc_news_window を実装。
    - バッチ化（最大20銘柄）、記事・文字数トリム、リトライ（指数バックオフ）、レスポンス検証（JSON 抽出・バリデーション）を実装。
    - スコアは ±1.0 にクリップ。APIキーは引数または環境変数 OPENAI_API_KEY から取得。API未設定時は ValueError。
  - kabusys.ai.regime_detector:
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して日次レジーム（bull/neutral/bear）判定を実装。
    - OpenAI 呼び出しのリトライ・フォールバック処理を実装（API失敗時は macro_sentiment=0.0）。
    - 計算結果を market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - ルックアヘッドバイアスを避ける設計（datetime.today() を直接参照しない等）。
- リサーチ（因子算出）:
  - kabusys.research モジュール公開:
    - factor_research: calc_momentum, calc_value, calc_volatility を実装。prices_daily / raw_financials テーブルのみ参照。
      - Momentum: 1M/3M/6M リターン、200日MA乖離（データ不足時は None を返す）。
      - Volatility: 20日 ATR・相対ATR・20日平均売買代金・出来高比率等。
      - Value: PER, ROE（raw_financials から最新報告を結合）。
    - feature_exploration: calc_forward_returns（複数ホライズン対応）、calc_ic（Spearman ランク相関）、factor_summary（統計量）、rank（同順位平均ランク）を実装。
    - zscore_normalize は kabusys.data.stats から再エクスポート（公開関数群の組合せ）。
  - 設計方針: DuckDB の SQL と標準ライブラリのみを使用、外部実行環境（発注API等）にはアクセスしない。
- データプラットフォーム（Data）:
  - kabusys.data.calendar_management:
    - market_calendar を基にした営業日判定ユーティリティを実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB に登録がない日については曜日ベース（土日非取引）でフォールバック。最大探索日数で無限ループ防止。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等更新。バックフィル・健全性チェック実装。
  - kabusys.data.pipeline / etl:
    - ETLResult データクラスを公開（取得件数、保存件数、品質問題、エラー等を保持）。
    - ETL パイプライン設計: 差分更新、バックフィル、品質チェック（品質問題は収集して呼び出し元で判断）等の方針を実装。
    - jquants_client 連携を想定した idempotent な保存処理設計。
- 安全性 / ロバストネス:
  - OpenAI 呼び出し部分に対してリトライ・バックオフ、5xx 判定、非致命フォールバック（0.0 やスキップ）を実装。
  - DuckDB への書き込みはトランザクション（BEGIN/COMMIT/ROLLBACK）で保護。ROLLBACK 失敗時のログ保護。
  - JSON レスポンスパース時に余計な前後テキストが混ざるケースを考慮して最外側の {} を抽出する復元処理を実装。
  - DuckDB executemany に対する空リスト制約（DuckDB 0.10）を考慮して条件分岐を実装。
- ドキュメント的コメント:
  - 各モジュールに処理フロー・設計方針・注意点を詳細に記述（ルックアヘッド回避、テストフレンドリーな API キー注入、フォールバック動作等）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- 環境変数の取り扱いに注意。必須となる環境変数（例）:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY
- .env ファイル読み込みはプロジェクトルート検出に基づくため、配布形態・実行環境に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して無効化可能。

Notes / 注意事項
- OpenAI API との連携は gpt-4o-mini を前提にしており、API の仕様変更や rate limit、レスポンス形式に依存します。
- DuckDB のスキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar など）が事前に正しく作成されていることが前提です。
- 時刻・タイムゾーンの扱い:
  - news_nlp では UTC naive datetime を内部で使用（JST→UTC 変換済みのウィンドウを生成）。
  - 全体的に date オブジェクトを使用して timezone の混入を避ける設計。
- ルックアヘッドバイアス回避のため、内部で datetime.today()/date.today() を直接参照しない設計が多用されています。処理の基準日は引数で受け取る方式を採用。

今後の提案（任意）
- テスト用に OpenAI 呼び出しを容易にモックできる公開フックの整備（現在は内部関数を patch する想定）。
- api_key の検証/管理を共通ユーティリティへ集約。
- ETL 実行ログ/監査ログの永続化と UI 表示用の要約 API の追加。

--- 

上記は提供されたコードベースの実装とドキュメント文字列から推測した CHANGELOG です。日付や表現、重要度のカテゴリ付けはプロジェクトの実際のリリースポリシーに合わせて調整してください。必要なら各モジュールごとのより詳細な変更点やサンプルのリリースノート文言も作成できます。