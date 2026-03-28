# Changelog

すべての重要な変更はこのファイルに記録します。本ファイルは「Keep a Changelog」のフォーマットに準拠します。  
安定性や設計方針、外部依存（OpenAI / J-Quants / DuckDB 等）に関する注意事項も併記しています。

## [Unreleased]
（現在の木は v0.1.0 の初期リリースと整合しています。将来の変更はここに追記してください。）

---

## [0.1.0] - 初回リリース
リリース日: 2026-03-28

初版リリース。日本株自動売買／データ基盤向けのコアライブラリを提供します。主な機能群は以下の通りです。

### Added
- パッケージ基礎
  - kabusys パッケージの初期公開（__version__ = 0.1.0）。
  - public なサブパッケージ・モジュール群を __all__ で定義（data, strategy, execution, monitoring）。

- 環境設定管理（kabusys.config）
  - .env ファイル自動読み込み機構（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - .env と .env.local の読み込み優先度（OS環境変数 > .env.local > .env）。.env.local は override=True。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプション。
  - .env パーサ実装: export KEY=val 形式、シングル/ダブルクォート、エスケープ、インラインコメント処理に対応。
  - 環境変数必須チェック用 _require と Settings クラスを提供。主要プロパティ:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID などの必須キー
    - KABUSYS_API_BASE_URL のデフォルト値、DUCKDB_PATH / SQLITE_PATH のデフォルトパス
    - KABUSYS_ENV（development / paper_trading / live）と LOG_LEVEL 検証
    - is_live / is_paper / is_dev ヘルパー

- データ周り（kabusys.data）
  - ETL パイプライン（kabusys.data.pipeline）
    - 差分取得・バックフィル・品質チェック・idempotent な保存を行う設計。
    - ETLResult データクラスを公開（kabusys.data.etl 経由で再エクスポート）。
    - DuckDB に対する存在チェック・最大日付取得ユーティリティを実装。
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX マーケットカレンダーの夜間更新ジョブ（calendar_update_job）。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日判定ロジック。
    - market_calendar が未取得の場合の曜日ベースフォールバック、DB 登録値優先の一貫した挙動。
    - 最大探索日数制限や健全性チェック、バックフィルの考慮。

- 研究・分析（kabusys.research）
  - factor_research モジュール
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）などを計算。
    - calc_volatility: 20日 ATR（atr_20）、相対ATR（atr_pct）、平均売買代金、出来高比率を計算。
    - calc_value: raw_financials と組み合わせた PER / ROE の算出。
    - DuckDB を用いた SQL＋Python 実装。結果は (date, code) ベースの dict リストで返す。
  - feature_exploration モジュール
    - calc_forward_returns: 指定ホライズンの将来リターンを取得（デフォルト [1,5,21]）。
    - calc_ic: スピアマンのランク相関（IC）計算。3 銘柄未満で None を返す。
    - rank: 同順位は平均ランクにするランク化ユーティリティ（round(v,12) による安定化）。
    - factor_summary: count/mean/std/min/max/median の統計サマリー。

- AI/NLP（kabusys.ai）
  - ニュースセンチメント（kabusys.ai.news_nlp）
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメントを算出。
    - バッチ処理（デフォルト _BATCH_SIZE=20）、1銘柄あたり最大記事数・文字数制限（_MAX_ARTICLES_PER_STOCK=10、_MAX_CHARS_PER_STOCK=3000）。
    - JSON Mode のレスポンスバリデーション、数値変換、±1.0 でクリップ。
    - レート制限・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライ。
    - テスト差し替え用に _call_openai_api を patch できる設計。
    - calc_news_window: target_date に対応するニュース収集ウィンドウ（JST を UTC naive datetime に変換）。
    - score_news API: 成功時に書き込んだ銘柄数を返す。API キーは引数または環境変数 OPENAI_API_KEY。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次判定。
    - マクロキーワードによる raw_news フィルタリング、最大記事数制限、OpenAI 呼び出し、JSON パース、スコア合成、閾値に基づくラベリング。
    - API リトライ戦略、API 失敗時フェイルセーフ（macro_sentiment = 0.0）。
    - スコアとメタ情報を market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT、失敗時は ROLLBACK）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- OpenAI / J-Quants 等の API キーは明示的に環境変数または引数で提供する必要あり（例: OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN）。コード内にハードコーディングは無し。
- .env の読み込み時に OS 環境変数を保護する仕組み（protected set）を導入。

### Notes / Usage / 既知の設計方針
- ルックアヘッドバイアス対策
  - AI / 研究モジュールはいずれも datetime.today() / date.today() を内部で参照しない設計（呼び出し元が target_date を明示する）。クエリは target_date 未満 / 以前等の排他条件を厳守。
- データベース
  - DuckDB を前提としたクエリとトランザクションを利用。executemany に空リストを渡せない DuckDB の挙動を考慮してガードしている。
  - DB 書き込みは可能な限り冪等（DELETE→INSERT、ON CONFLICT 相当）を意識。
- フォールバック／フェイルセーフ
  - カレンダー未取得時は曜日ベースのフォールバック（週末を非営業日）。
  - AI API 呼び出し失敗時は例外を投げずスコアを 0.0 として処理を継続する箇所がある（フェイルセーフ設計）。
- ロギング
  - 各モジュールで詳細な情報・警告・例外ログを出力する（調査・運用向け）。
- テストしやすさ
  - OpenAI 呼び出し部分はモジュール内部の _call_openai_api を unittest.mock.patch できるよう分離してある。
- 環境変数のバリデーション
  - KABUSYS_ENV は {development, paper_trading, live} のみ有効。LOG_LEVEL は標準的な値のみ受け付ける。

### Requirements / 環境
- DuckDB を利用することを前提とした SQL 実装。
- OpenAI Python SDK の利用箇所あり（gpt-4o-mini を想定）。
- J-Quants クライアントとの連携を想定（kabusys.data.jquants_client など）。
- 必須環境変数（例）
  - OPENAI_API_KEY（AI 機能を使う場合）
  - JQUANTS_REFRESH_TOKEN（データ取得）
  - KABU_API_PASSWORD（kabu API 連携）
  - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID（通知機能有効時）

---

将来的なリリースでは、各モジュールごとの改良点（性能改善、API バージョン対応、追加のファクター、より厳密な型注釈や型チェックなど）を本 CHANGELOG に追記します。