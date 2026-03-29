# CHANGELOG

すべての注記は Keep a Changelog のガイドラインに準拠します。  
初版リリース(0.1.0) の内容をコードベースから推測して記載しています。

## [Unreleased]
- なし

## [0.1.0] - 2026-03-29
初回公開リリース。日本株自動売買・研究プラットフォームのコア実装を追加。

### Added
- パッケージ基盤
  - kabusys パッケージの初期公開。__version__ = "0.1.0"、主要サブパッケージを __all__ で公開 (data, research, ai, ... のうち data, research, ai などを含む構成)。
- 設定管理
  - 環境変数/設定読み込みモジュール (kabusys.config) を追加。
    - .env / .env.local をプロジェクトルート（.git または pyproject.toml）から自動検出して読み込む自動ロード機能を実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
    - export 付き行、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理などを考慮した .env パース処理を実装。
    - OS 環境変数を保護する protected セット処理および override フラグを備えた読み込み関数を提供。
    - 必須環境変数取得ヘルパー _require と Settings クラスを提供（J-Quants, kabu, Slack, DB パス, ログレベル, env 判定など）。
    - KABUSYS_ENV と LOG_LEVEL の値検証（許容値チェック）を実装。
- AI（自然言語処理 / レジーム判定）
  - ニュース NLP スコアリングモジュール (kabusys.ai.news_nlp)
    - raw_news と news_symbols を集約し、銘柄ごとに記事をまとめて OpenAI（gpt-4o-mini）にバッチ送信してセンチメントスコアを取得する機能を実装。
    - タイムウィンドウ計算 (calc_news_window)、記事収集 (_fetch_articles)、チャンク単位スコア取得 (_score_chunk)、レスポンス検証 (_validate_and_extract)、および ai_scores への置換的書き込み（DELETE → INSERT）を提供。
    - API 呼び出しは JSON mode を使用し、429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフのリトライを実装。
    - レスポンスの厳密なバリデーション、スコアの ±1.0 クリップ、不正データやパース失敗時のフェイルセーフ（ログ出力してスキップ）を採用。
    - DuckDB の executemany に関する互換性問題（空リスト不可）への対策を実装。
  - 市場レジーム判定モジュール (kabusys.ai.regime_detector)
    - ETF 1321（日経225連動）を用いた 200 日移動平均乖離（重み 70%）と、マクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を判定する処理を実装。
    - ma200_ratio 算出、マクロキーワードによるタイトル抽出、OpenAI 呼び出し（独立実装）による macro_sentiment のスコア化、スコア合成、market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を提供。
    - API エラー・パース失敗時は macro_sentiment = 0.0 で継続するフェイルセーフ、retry ロジック、ログ出力を実装。
- データ取得・ETL
  - ETL パイプラインモジュール (kabusys.data.pipeline)
    - ETLResult データクラスを追加。ETL 実行結果（取得数/保存数、品質問題リスト、エラー一覧等）の構造化表現を提供。
    - テーブルの最終日付取得や存在確認などのユーティリティを実装。
  - etl モジュールで ETLResult を再エクスポート (kabusys.data.etl)。
  - カレンダー管理モジュール (kabusys.data.calendar_management)
    - JPX マーケットカレンダーを扱うロジックを追加（market_calendar テーブルを利用）。
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day 等の営業日判定ユーティリティを提供。
    - calendar_update_job による J-Quants API からの差分取得・バックフィル・保存処理を実装。保存は idempotent を意識（ON CONFLICT 相当の上書き想定）。
    - DB 未取得時の曜日ベースフォールバック（週末判定）や最大探索日数による安全策を導入。
- Research（ファクター計算・特徴量探索）
  - kabusys.research パッケージを追加。公開 API として zscore_normalize（data.stats から）や以下をエクスポート:
    - factor_research: calc_momentum, calc_value, calc_volatility（モメンタム／バリュー／ボラティリティ因子の計算）
      - prices_daily / raw_financials を用いた SQL ベースの計算実装。欠損・データ不足時の扱い（None）を定義。
      - ATR, 200日移動平均乖離、各種ホライズンでのリターン等を算出。
    - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank（将来リターン計算、IC 計算、統計サマリー、ランク関数）
      - pandas 等に依存せず標準ライブラリ＋DuckDB SQL で実装。Spearman（ランク相関）計算、統計量算出を提供。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーの取り扱い:
  - 各 AI 関数（score_news, score_regime）は api_key 引数を受け、未指定時は環境変数 OPENAI_API_KEY を参照。未設定時は ValueError を送出して明示的に失敗させる仕様。

### Notes / Implementation Decisions
- ルックアヘッドバイアス対策:
  - score_news, score_regime, 各 research 関数は内部で datetime.today() / date.today() を参照せず、呼び出し側から target_date を受け取る設計。
  - DB クエリは target_date 未満 / 以前などの排他条件を適切に用いて未来データの混入を防止。
- 可用性 / フェイルセーフ:
  - LLM/API 呼び出し失敗時は即座に全体を止めず、ログ出力して安全なデフォルト（例: macro_sentiment=0.0、スコア未取得はスキップ）で継続する方針。
- DuckDB 互換性考慮:
  - executemany に空リストを渡せないバージョン（DuckDB 0.10 等）への対応を実装。
- テスト性:
  - OpenAI 呼び出し点は内部でラップし、unittest.mock.patch による差し替えが可能な設計（_call_openai_api をモジュール内で定義）。

---

その他、実装上の細かな定数・振る舞い（バッチサイズ、リトライ回数、モデル名 gpt-4o-mini、ニュースウィンドウ定義、マクロキーワード一覧、閾値等）はコード内にドキュメントとして明示されています。README やドキュメントにはこれらの設計意図・運用方法（.env.example、OpenAI キーの設定、DB スキーマの準備など）を追記することを推奨します。