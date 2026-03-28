# Changelog

すべての注目すべき変更点をこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠し、意味のあるバージョン変更のみを記載します。

現在のバージョン: 0.1.0

## [Unreleased]

（次期リリース向けの変更点はここに記載します）

---

## [0.1.0] - 2026-03-28

初回リリース。KabuSys の基本機能を実装しました。以下は実装された主要な機能・設計方針・利用上の注意点の概要です。

### 追加 (Added)
- パッケージ基盤
  - パッケージ初期化: kabusys.__init__ にバージョン "0.1.0" と公開モジュールリスト (data, strategy, execution, monitoring) を追加。

- 設定管理
  - 環境変数・設定読み込みモジュール (kabusys.config)
    - .env / .env.local の自動ロード機能（プロジェクトルートを .git または pyproject.toml を基準に検出）。
    - .env パースロジックを自前実装（export プレフィックス対応、クォート内のエスケープ処理、インラインコメント処理）。
    - .env の上書き挙動: OS 環境変数は保護され、.env.local は .env をオーバーライドする形でロード。
    - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
    - 必須環境変数取得ヘルパー _require、および settings オブジェクトを提供。
    - 設定プロパティ: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV（development, paper_trading, live の検証）、LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）など。
    - ユーティリティプロパティ: is_live/is_paper/is_dev。

- AI モジュール
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - raw_news / news_symbols を用いて銘柄単位に記事を集約し、OpenAI（gpt-4o-mini）を用いてセンチメント評価を実行。
    - バッチ処理（1コールあたり最大 20 銘柄）、1 銘柄あたり記事最大 10 件・最大 3000 文字にトリム。
    - JSON Mode による厳密な JSON 応答を期待し、レスポンスの堅牢なバリデーションを実装。
    - API エラー（429、ネットワーク断、タイムアウト、5xx）に対する指数バックオフによるリトライ実装。
    - スコアは ±1.0 にクリップして ai_scores テーブルへ冪等的に書き込み（DELETE → INSERT）。
    - テスト容易性のため OpenAI 呼び出し関数を差し替え可能（_call_openai_api を patch でモック可能）。
    - calc_news_window ヘルパーを提供（JST ベースのニュース収集ウィンドウ計算）。

  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321（日経225連動型）200 日移動平均乖離（重み 70%）と、マクロニュース由来の LLM センチメント（重み 30%）を合成して日次レジームを判定（bull / neutral / bear）。
    - prices_daily, raw_news, market_regime テーブルを利用し、計算後に market_regime へ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - OpenAI 呼び出しに対するリトライ・フェイルセーフ（API 失敗時は macro_sentiment=0.0）を実装。
    - LLM モデルは gpt-4o-mini を想定。テスト用に _call_openai_api を差し替え可能。

- データ (Data) モジュール
  - カレンダー管理 (kabusys.data.calendar_management)
    - market_calendar テーブルを用いた営業日判定ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 登録値優先、未登録日は曜日ベースでフォールバックする一貫設計。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等的に保存。バックフィル、健全性チェックを実装。

  - ETL パイプライン (kabusys.data.pipeline, kabusys.data.etl)
    - ETL 実行結果を返すデータクラス ETLResult（品質チェック結果、エラー一覧を含む）。
    - 差分更新・バックフィル・品質チェックのためのユーティリティ実装（J-Quants クライアントと quality モジュールを使用）。
    - 内部ユーティリティ: テーブル存在チェック、最大日付取得、ターゲット日の調整など。

- リサーチ（研究）モジュール (kabusys.research)
  - factor_research
    - モメンタム（1M/3M/6M リターン、ma200_dev）、ボラティリティ（20日 ATR / atr_pct）、バリュー（PER、ROE）等のファクター計算関数を提供。
    - DuckDB の SQL（窓関数）を中心に実装し、prices_daily / raw_financials のみ参照。
  - feature_exploration
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、統計サマリー（factor_summary）、ランク変換（rank）などの解析ユーティリティを追加。
  - data.stats の zscore_normalize を再エクスポート。

- ドキュメント的な設計方針
  - 各モジュールにはルックアヘッドバイアス防止の方針を明示（datetime.today()/date.today() を直接参照しない設計）。
  - DuckDB 0.10 の制約（executemany に空リスト渡せない等）への対応を実装している箇所あり。

### 変更 (Changed)
- （初回リリースのため履歴上の変更はありません）

### 修正 (Fixed)
- （初回リリースのため過去バグ修正履歴はありません）

### 既知の注意点 / 利用上のヒント
- 環境変数の必須項目
  - OpenAI を利用する機能（news_nlp, regime_detector）を使う場合は OPENAI_API_KEY を設定するか、各関数の api_key 引数でキーを渡す必要があります。未設定時には ValueError を送出します。
  - J-Quants 関連や kabu ステーション利用に必要な環境変数: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等が settings で必須判定されます。
- .env 自動読み込み
  - パッケージ import 時にプロジェクトルートが検出されると .env/.env.local を自動ロードします。テスト等で無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出しのテスト性
  - テストでは kabusys.ai.news_nlp._call_openai_api や kabusys.ai.regime_detector._call_openai_api を patch して応答を差し替えることで外部 API をモックできます。
- データベースのデフォルトパス
  - DUCKDB_PATH デフォルト: data/kabusys.duckdb
  - SQLITE_PATH デフォルト: data/monitoring.db
- ログレベル・環境チェック
  - KABUSYS_ENV は development / paper_trading / live のいずれかのみ有効です。LOG_LEVEL は標準的なログレベル名のみ受け付けます。

### セキュリティ
- 機密情報（API キー等）は OS 環境変数優先で保護され、.env ファイルによる上書きは OS 環境変数が保護される仕組みを導入しています。

---

今後の予定（例）
- モデルパラメータやバッチサイズの調整オプション化
- より細かな品質チェックルールの追加
- ETL の並列化・再実行性向上
- strategy / execution / monitoring モジュールの実装とドキュメント拡充

※ 本 CHANGELOG はコードベース（src/ 以下）から実装内容を推測して作成しています。実際のリリースノート作成時は運用・プロダクト面の補足を適宜追加してください。