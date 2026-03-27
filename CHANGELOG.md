# CHANGELOG

すべての注目すべき変更点はここに記録します。本ファイルは Keep a Changelog の形式に準拠しています。

## [0.1.0] - 2026-03-27

初回リリース。日本株自動売買システム「KabuSys」のコアライブラリを公開します。以下はソースコードから推測してまとめた主要な追加機能・設計方針・既知の制約です。

### 追加 (Added)
- パッケージ基礎
  - kabusys パッケージの初期バージョンを追加。パッケージバージョンは 0.1.0。
  - __all__ に data, strategy, execution, monitoring を公開（monitoring は将来的な実装を想定）。

- 設定管理 (kabusys.config)
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - .env パーサを実装（export 形式、シングル/ダブルクォート、エスケープ、インラインコメント処理に対応）。
  - 環境変数上書きルール: OS 環境変数は保護（protected）され .env.local は上書き可能。
  - 自動ロードを無効化するための環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを提供し、J-Quants / kabuAPI / Slack / DB パス / 実行環境（development/paper_trading/live）/ログレベルなどのプロパティを公開。

- AI モジュール (kabusys.ai)
  - news_nlp モジュール: raw_news + news_symbols を集約して OpenAI（gpt-4o-mini）により銘柄別センチメントを算出し ai_scores テーブルへ書き込む機能を実装。
    - バッチ送信（最大 20 銘柄/チャンク）、1銘柄あたりの最大記事数・文字数でトリム、JSON Mode による厳密な出力検証。
    - 429 / ネットワーク / タイムアウト / 5xx に対する指数バックオフリトライ実装。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results キー、型チェック、未知コード無視、数値チェック）。
    - スコアは ±1.0 にクリップ。部分失敗に備え、DB 書き込みは対象コードのみ DELETE→INSERT を行い既存データを保護。
    - テスト用に内部の OpenAI 呼び出しを patch できる設計。

  - regime_detector モジュール: ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込みする機能を実装。
    - MA 計算は target_date 未満のデータのみを使用してルックアヘッドバイアスを排除。
    - マクロニュースはキーワードでフィルタ（日本・米国系の主要キーワード群）。
    - OpenAI 呼び出しは専用の retry / フェイルセーフ（API 失敗時は macro_sentiment=0.0）を備える。
    - DB 書き込みは BEGIN/DELETE/INSERT/COMMIT の冪等処理。失敗時は ROLLBACK を行い上位へ例外を伝播。

- データプラットフォーム (kabusys.data)
  - calendar_management: JPX カレンダー管理（market_calendar）と営業日判定ユーティリティを提供。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を実装。
    - DB にカレンダーがない場合は曜日ベース（土日休み）でフォールバックする仕様。
    - calendar_update_job により J-Quants API から差分取得して market_calendar を冪等保存する処理を実装（バックフィル・健全性チェックを含む）。
  - pipeline / etl: ETL の結果を表す ETLResult を公開。差分取得・保存・品質チェックの設計に対応するための基礎を提供。
    - DuckDB を利用した各種ユーティリティ（テーブル存在確認、最大日付取得等）を実装。
    - ETLResult は品質問題（quality.QualityIssue）とエラーの集約・シリアライズをサポート。
  - ETL 実装は DuckDB 0.10 の制約（executemany が空リストを受け取れない）を考慮した書き込みロジックになっている。

- リサーチ (kabusys.research)
  - factor_research: モメンタム / バリュ― / ボラティリティ / 流動性等のファクター計算機能を実装。
    - calc_momentum, calc_volatility, calc_value を実装。prices_daily, raw_financials 等のテーブルを参照。
    - 計算は SQL と Python の組合せで実行し、(date, code) をキーとする辞書リストを返す設計。
  - feature_exploration: 将来リターン計算、IC（Spearman ρ）、ランク関数、統計サマリー等を実装。
    - calc_forward_returns（任意ホライズン対応）、calc_ic（ランク相関）、rank、factor_summary を提供。
    - pandas 等の外部依存を使わず標準ライブラリと DuckDB のみで実装。

- 外部連携
  - OpenAI クライアント（openai.OpenAI）を利用する形で AI 処理を実装。
  - J-Quants クライアント（kabusys.data.jquants_client）との連携を想定した設計（calendar / ETL / 保存関数の呼び出し）。
  - kabuステーション API、Slack 連携のための環境変数を Settings で管理。

### 変更 (Changed)
- （初回リリースにつき主に新規追加。設計上の重要点を明示）
  - ルックアヘッドバイアス回避: AI / リサーチ系のモジュールは内部で datetime.today()/date.today() を参照せず、必ず引数の target_date を基準に処理する設計。
  - DuckDB に依存する SQL 実装は互換性を考慮し、ROW_NUMBER/LEAD/LAG/ウィンドウ関数を使用。
  - OpenAI の JSON Mode を利用して厳密な機械可読出力を期待するが、応答に付随したノイズが混入する可能性を見越して補正処理を実装（外側の {} 抽出など）。

### 修正 (Fixed)
- フォールバックと耐障害性の強化:
  - AI API 呼び出し失敗時は例外を直接上げるのではなく、フェイルセーフ値（macro_sentiment=0.0 / スコア未取得でスキップ）を使用し、処理の継続を優先する実装。
  - DB 書き込みは部分失敗に備えた設計（対象コードのみ DELETE → INSERT）で既存データの保護を行う。

### セキュリティ (Security)
- 環境変数の保護:
  - OS 環境変数を protected として .env による上書きを防止する仕組みを導入。
  - 必須の機密情報（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY 等）は Settings のプロパティで取得時に未設定なら ValueError を送出して明示する。

### 既知の制約 / 注意事項 (Known issues / Notes)
- OpenAI 依存
  - AI スコアリングは OpenAI API（gpt-4o-mini）に依存。API キーが必要（api_key 引数または環境変数 OPENAI_API_KEY）。
  - API レスポンスの不安定さや制限により、一部の銘柄スコア取得が失敗する可能性がある。失敗時は該当チャンクをスキップし、他の銘柄の結果は保護される設計。
- DuckDB 互換性
  - DuckDB のバージョン差異に起因するバインド振る舞い（リスト型バインドや executemany の空リスト扱い等）を考慮した実装になっているが、稀に環境依存の問題が発生する可能性あり。
- タイムゾーン
  - ニュース集約は JST を基準にし、DB 内の日時は UTC naive の datetime を扱う仕様（calc_news_window にて UTC 換算によるウィンドウを返す）。実運用では DB 保存時のタイムゾーン整合を確認してください。
- テーブル前提
  - 多くの処理が prices_daily, raw_news, news_symbols, raw_financials, ai_scores, market_regime, market_calendar 等のテーブル存在を前提とする。テーブルスキーマや存在確認は呼び出し側で管理する必要があります。
- 未実装項目
  - strategy / execution / monitoring の具象実装は本リリースでは同梱されていない（__all__ に名前はあるが実装は今後追加予定）。

### マイグレーション / 導入手順 (Migration / Installation notes)
- 必要な環境変数（例）
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY は実行環境で設定してください。
- デフォルト DB パス
  - DuckDB: デフォルトは data/kabusys.duckdb（Settings.duckdb_path）
  - SQLite (monitoring): data/monitoring.db（Settings.sqlite_path）
- 自動 .env ロード
  - パッケージはプロジェクトルートを基準に .env/.env.local を自動ロードします。テスト時やカスタム環境で無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- テスト支援
  - OpenAI 呼び出しは内部関数を patch（unittest.mock.patch）してモック可能。

### 開発者メモ (Developer notes)
- テスト容易性を考慮し、AI 呼び出しをラップする内部関数が用意されています（kabusys.ai.news_nlp._call_openai_api, kabusys.ai.regime_detector._call_openai_api）。
- スコア計算・DB 書き込みは冪等性と部分失敗時のデータ保護を重視して設計しています。
- ルックアヘッドバイアス防止のため、すべてのバッチ処理関数は外部から target_date を受け取り、内部で現在日時を参照しません。

---

今後のリリースでは、strategy / execution / monitoring の具象実装、より詳細な品質チェック機能、テストカバレッジ拡充、運用監視機能の追加を予定しています。問題報告やプルリクエストはリポジトリの issue をご利用ください。