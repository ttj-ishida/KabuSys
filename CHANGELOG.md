CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
フォーマット: 追加 (Added)、変更 (Changed)、修正 (Fixed)、非推奨 (Deprecated)、削除 (Removed)、セキュリティ (Security)。

Unreleased
----------

（現時点の開発中変更はありません）

[0.1.0] - 2026-03-31
-------------------

Initial release — 日本株自動売買 / データ基盤ライブラリの初版公開。

Added
- パッケージ基盤
  - kabusys パッケージの初期バージョンを追加。バージョンは 0.1.0。
  - __all__ で公開モジュールを定義（data, strategy, execution, monitoring）。
- 設定管理
  - kabusys.config: .env ファイルと環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルートは .git または pyproject.toml を基準に探索（CWD に依存しない）。
    - .env と .env.local を優先度付きで読み込み。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
    - export 形式やクォート／エスケープ、インラインコメントに対応したパーサーを実装。
  - Settings クラスを提供し、主要な環境変数をプロパティ経由で取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL 等
    - 必須変数未設定時は ValueError を送出するヘルパーを実装。
    - env/log level の検証（有効な値集合）を実装。
- AI（NLP）モジュール
  - kabusys.ai.news_nlp
    - raw_news と news_symbols を集計して銘柄ごとのニューステキストを作成し、OpenAI（gpt-4o-mini）の JSON mode を用いて銘柄別センチメント（ai_score）を取得。
    - バッチ処理（最大 20 銘柄/コール）、一銘柄あたりの記事数/文字数上限、レスポンス検証、スコアの ±1.0 クリップを実装。
    - リトライ（429 / ネットワーク断 / タイムアウト / 5xx）を指数バックオフで実施。致命的でない失敗はスキップして継続するフェイルセーフ設計。
    - テスト容易性のため OpenAI 呼び出し箇所は差し替え可能（unittest.mock.patch を想定）。
    - calc_news_window ユーティリティを提供（JST の前日15:00〜当日08:30 を UTC に変換）。
  - kabusys.ai.regime_detector
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次市場レジーム（bull/neutral/bear）を判定、market_regime テーブルへ冪等書き込み。
    - マクロニュース抽出用キーワードと LLM プロンプトを用意。API エラー時は macro_sentiment=0.0 のフォールバック。
    - OpenAI 呼び出しも差し替え可能で、再試行・エラー種別毎のロジックを実装。
    - 設計方針としてルックアヘッドバイアスを防ぐ（datetime.today()/date.today() を直接参照しない）。
- データ基盤（Data）
  - kabusys.data.pipeline / etl / jquants クライアントとの連携インターフェース
    - ETLResult データクラスを公開して、ETL の取得/保存件数、品質チェック結果、エラー一覧を集約。
    - 差分取得、バックフィル、品質チェックの設計方針を実装（ドキュメント化）。
  - kabusys.data.calendar_management
    - market_calendar を利用した営業日判定ユーティリティ群を実装:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - market_calendar 未取得時の曜日ベースのフォールバックを含む一貫した動作。
    - カレンダー夜間バッチ calendar_update_job を実装（J-Quants からの差分取得、バックフィル、健全性チェック、冪等保存）。
    - 最大探索日数等の安全策を実装して無限ループや異常データを防止。
- リサーチ（研究用）モジュール
  - kabusys.research.factor_research
    - モメンタム（1M/3M/6M）、200 日 MA 乖離、ATR(20)、平均売買代金、出来高比などのファクター計算関数を実装（DuckDB を用いた SQL ベース）。
    - calc_momentum, calc_volatility, calc_value を提供。戻り値は date・code 単位の dict リスト。
  - kabusys.research.feature_exploration
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、ランク変換ユーティリティ（rank）、ファクター統計サマリ（factor_summary）を実装。
    - pandas 等外部依存を用いずに純 Python / SQL（DuckDB）で実装。
- DuckDB 互換性／安全性考慮
  - DuckDB 0.10 の executemany の空リスト制約を考慮した実装（空チェックを行う）。
  - DB 書き込みは BEGIN / DELETE / INSERT / COMMIT を用いた冪等処理・トランザクション制御を採用。失敗時は ROLLBACK を試行のうえ例外伝播。

Changed
- （初版のためなし）

Fixed
- （初版のためなし）

Security
- OpenAI API キー等の秘密情報は Settings を通じて環境変数で管理するよう明示。
- .env 自動ロードは環境変数で無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

Notes / 注意事項
- OpenAI 連携
  - OpenAI API（gpt-4o-mini）を利用する機能は、実行時に OPENAI_API_KEY が環境変数または関数引数で必要です。未設定時は ValueError を送出します。
  - LLM 呼び出しは外部 API であり、レート制限やネットワーク障害に対するリトライ／フォールバック設計を施していますが、API 利用量はユーザ負担です。
- ルックアヘッド防止
  - AI スコアリングやレジーム判定は、計算において datetime.today() / date.today() を直接参照しない設計です。必ず target_date を明示的に渡して実行してください。
- DB スキーマ前提
  - 各モジュールは prices_daily, raw_news, news_symbols, ai_scores, market_calendar, raw_financials など特定のテーブル構造を前提とします。実行前にスキーマを用意してください。
- テスト容易性
  - OpenAI 呼び出しや時間依存処理は差し替え可能な内部関数を用意しており、ユニットテストでモックしやすい設計になっています。

ライセンス・貢献
- 本リリースは初期公開版です。今後の改良やバグ修正、機能追加は CHANGELOG に順次記載します。貢献や不具合報告はリポジトリの issue を通じてお願いします。