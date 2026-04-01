# Changelog

すべての重要な変更はこのファイルに記録します。本ファイルは「Keep a Changelog」規約に準拠しています。  
フォーマット: [Unreleased] / バージョン見出し（YYYY-MM-DD） → セクションは Added / Changed / Fixed / Removed / Security 等。

--------------------------------------------------------------------

## [Unreleased]

（現在の開発中の変更はここに記載してください）

--------------------------------------------------------------------

## [0.1.0] - 2026-04-01

初回公開リリース。日本株自動売買システムのコアライブラリを実装。

### Added
- パッケージ基盤
  - パッケージ名: kabusys、バージョン: 0.1.0 を追加。
  - パッケージの公開 API として data, strategy, execution, monitoring を __all__ で定義。

- 設定 / 環境変数管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込むユーティリティを実装。
  - プロジェクトルート検出: .git または pyproject.toml を基準に自動検出する _find_project_root() を実装。
  - .env パーサ: export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメントの取り扱いなどを考慮した _parse_env_line() を実装。
  - .env 自動読み込み: OS 環境変数 > .env.local > .env の優先順位で自動ロード。テスト等のため KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB / 監視 / システム設定など主要設定値をプロパティ経由で取得可能に（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, DUCKDB_PATH 等）。
  - 設定値検証: KABUSYS_ENV の許容値チェック（development / paper_trading / live）、LOG_LEVEL の検証。

- AI 関連機能 (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - raw_news と news_symbols から銘柄毎に記事を集約し、OpenAI（gpt-4o-mini の JSON Mode）でセンチメントを取得して ai_scores テーブルへ保存。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window() で提供。
    - バッチ処理: 最大 _BATCH_SIZE=20 銘柄/回、1銘柄当たり最大記事数と文字数でトリム（_MAX_ARTICLES_PER_STOCK=10, _MAX_CHARS_PER_STOCK=3000）。
    - 再試行戦略: 429/ネットワーク断/タイムアウト/5xx を対象に指数バックオフ（最大リトライ回数 _MAX_RETRIES）。
    - レスポンスの厳密なバリデーション実装（JSONパースの復元ロジック、results 配列構造検証、未知コードの無視、数値チェック、スコアの ±1.0 クリップ）。
    - DB 書き込みは部分冪等: 取得済みコードのみ DELETE → INSERT（DuckDB executemany の互換性に配慮）。
    - API 呼び出し部分はテスト差し替えしやすい形で実装（_call_openai_api は patch 可能）。

  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321（225連動型）200日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を算出。
    - ma200_ratio 計算は target_date 未満のデータのみを使用しルックアヘッドを防止。
    - マクロ記事抽出はキーワード _MACRO_KEYWORDS によるフィルタリング、最大記事数制限。
    - OpenAI 呼び出しは独立実装、リトライ・エラーハンドリング、失敗時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。
    - 計算結果は market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）。

- データプラットフォーム機能 (kabusys.data)
  - カレンダー管理 (kabusys.data.calendar_management)
    - JPX カレンダー用の夜間更新ジョブ calendar_update_job() を実装（J-Quants クライアント経由で差分取得 → 保存）。
    - 営業日判定ユーティリティ: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - market_calendar が未取得の場合は曜日ベース（土日を非営業日）でフォールバックする一貫した挙動。
    - 最大探索範囲（_MAX_SEARCH_DAYS）やバックフィル等の安全措置を実装。

  - ETL / パイプライン (kabusys.data.pipeline, kabusys.data.etl)
    - ETLResult データクラスを定義し、ETL の取得数／保存数／品質問題／エラー情報を収集できるようにした。
    - pipeline モジュールに基づく差分取得・バックフィル・品質チェック方針を実装（概要 API）。
    - jquants_client との連携を前提とした差分取得・idempotent 保存を想定。

- 研究用モジュール (kabusys.research)
  - factor_research
    - モメンタム（1M/3M/6M）、200日移動平均乖離、ATR(20)、20日平均売買代金・出来高比率、PER/ROE（raw_financials ベース）等のファクター計算関数を実装（calc_momentum, calc_volatility, calc_value）。
    - DuckDB を用いた SQL 組合せで計算し、(date, code) ベースの結果リストを返す設計。
  - feature_exploration
    - 将来リターン計算 calc_forward_returns（任意ホライズン対応）、IC（Information Coefficient）計算 calc_ic（Spearman ランク相関）、ランク変換 rank、ファクター統計 summary を提供。
    - 外部ライブラリ非依存で実装（標準ライブラリのみ）。

### Changed
- n/a（初回リリースのため変更履歴なし）

### Fixed
- n/a（初回リリースのため修正履歴なし）

### Removed
- n/a

### Notes / 実装上の重要事項・制約
- OpenAI 統合
  - news_nlp / regime_detector ともに OpenAI（gpt-4o-mini）を使用。API キーは引数で渡すか OPENAI_API_KEY 環境変数を使用する必要あり。キー未設定時は ValueError を送出する。
  - レスポンスは JSON Mode を期待するが、JSON パース時の冗長なテキスト混入に対する復元処理を実装している。
- フェイルセーフ設計
  - LLM/API エラーやパース失敗は例外を破壊的に投げず、スコアを 0.0 にフォールバックする等、パイプライン継続を優先する設計。
- ルックアヘッドバイアス対策
  - 各モジュール（news / regime / research 等）は datetime.today() / date.today() を内部で参照せず、必ず target_date を入力として受ける設計。
- DuckDB 互換性
  - executemany の空リストバインド等、DuckDB の既知の挙動に配慮した実装（空リスト実行回避等）。
- 設定自動読み込み
  - パッケージインポート時にプロジェクトルートを特定できれば .env / .env.local を自動読み込みする。不要な場合は KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。

--------------------------------------------------------------------

将来のリリースでは以下を想定:
- strategy / execution / monitoring の実用的な実装とテスト、運用向け安全装置（注文ラッパー、送信レート制御等）の追加
- 追加ユニットテスト、エンドツーエンドの ETL/AI 統合テスト
- ドキュメント・運用ガイド、サンプル .env.example の同梱

--------------------------------------------------------------------