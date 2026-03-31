# Changelog

すべての日付は YYYY-MM-DD 形式です。  
このファイルは Keep a Changelog の形式に準拠しています。  

なお、本 CHANGELOG は配布されているコードベースから機能／振る舞いを推測して作成した初期リリース向けの変更履歴です。

## [Unreleased]

## [0.1.0] - 2026-03-31
初回公開（アルファ）リリース。日本株のデータ取得・ETL・研究（リサーチ）・AI ベースのニュース分析・市場レジーム判定を含む自動売買システム向けユーティリティ群を提供します。

### Added
- 基本パッケージ情報
  - パッケージ名: kabusys、バージョン 0.1.0

- 環境設定 / 設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を追加（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - .env のパース機能を実装（コメント、export 構文、クォート内エスケープ等に対応）。
  - 自動ロードを無効化するための環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - 必須設定の取得ヘルパー _require を提供（未設定時は ValueError を送出）。
  - Settings クラスを公開:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID を必須プロパティとして取得。
    - KABU_API_BASE_URL のデフォルトおよび DUCKDB / SQLITE のデフォルトパスの提供。
    - KABUSYS_ENV の検証（development / paper_trading / live）。
    - LOG_LEVEL の検証（DEBUG, INFO, WARNING, ERROR, CRITICAL）と is_live / is_paper / is_dev のユーティリティ。

- データモジュール（kabusys.data）
  - ETL 用のパイプラインインターフェース ETLResult を公開（kabusys.data.pipeline）。
  - calendar_management:
    - JPX マーケットカレンダー管理ロジック（market_calendar テーブルの参照／更新）。
    - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days 等の営業日判定ユーティリティ。
    - calendar_update_job: J-Quants から差分取得して冪等に保存する夜間バッチ処理。
    - フォールバックとしてカレンダーデータ未取得時は曜日ベース（土日除外）で判定する仕組み。
    - 安全対策（最大探索日数／バックフィル／健全性チェック）を実装。

  - pipeline / etl:
    - 差分更新・保存・品質チェックを想定した ETLResult dataclass と内部ユーティリティ（テーブル存在チェック、最大日付取得等）。
    - ETL 実行結果の辞書化（品質問題のサマリ化）機能を提供。

- 研究（research）モジュール（kabusys.research）
  - factor_research:
    - モメンタム（1M/3M/6M）、200 日 MA 乖離（ma200_dev）計算（calc_momentum）。
    - ボラティリティ / 流動性（20 日 ATR、ATR 比率、平均売買代金、出来高比率）計算（calc_volatility）。
    - バリューファクター（PER, ROE）計算（calc_value）。raw_financials から最新の財務情報を取得。
    - 全て DuckDB 接続を受け取り SQL と Python を組み合わせて計算（外部 API にはアクセスしない）。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns、horizons デフォルト [1,5,21]、引数検証あり）。
    - IC（Information Coefficient、Spearman ρ）計算（calc_ic）。
    - ランク変換ユーティリティ（rank）およびファクター統計サマリ（factor_summary）。

- AI 関連（kabusys.ai）
  - news_nlp:
    - raw_news / news_symbols を集約し、OpenAI（gpt-4o-mini）の JSON Mode を使ってニュースごとのセンチメントを算出して ai_scores テーブルへ保存（score_news）。
    - タイムウィンドウは JST ベース（前日 15:00 ～ 当日 08:30 JST）を UTC に変換して DB クエリに使用。
    - バッチ処理（最大 20 銘柄 / コール）、記事数と文字数のトリム（最大記事数／最大文字数）を実装。
    - レスポンス検証（JSON 抽出、results 配列・型チェック、未知コードの無視、数値チェック）とスコアの ±1.0 クリップ。
    - リトライ・指数バックオフ（RateLimit / ネットワーク / タイムアウト / 5xx）を実装。
    - テスト用に _call_openai_api をモック可能に設計。

  - regime_detector:
    - ETF 1321（日経225 連動 ETF）の 200 日 MA 乖離（重み 70%）とマクロセンチメント（重み 30%）を組み合わせて市場レジーム（bull / neutral / bear）を日次で判定（score_regime）。
    - マクロ記事はニュースからキーワードフィルタ（複数キーワード）で抽出。
    - OpenAI を使ったマクロセンチメント評価（gpt-4o-mini、JSON 出力要求）。
    - フェイルセーフ: API 失敗時は macro_sentiment = 0.0 を採用して処理を続行。
    - DB への書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で実行。
    - ユニットテストで差し替え可能な API 呼び出しフックを用意。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- （特記なし）

---

## 重要な注意事項 / マイグレーション／使用上のヒント
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は Settings により必須（未設定時は ValueError）。
  - OpenAI API の利用関数（score_news, score_regime）は api_key 引数でキー注入可能。api_key を与えない場合は環境変数 OPENAI_API_KEY を参照。未設定時は ValueError を送出。
- 自動 .env ロード:
  - パッケージはプロジェクトルート（.git または pyproject.toml により検出）から .env/.env.local を自動的に読み込みます。テストや特殊環境で自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DB:
  - デフォルトの DuckDB パス: data/kabusys.duckdb（Settings.duckdb_path）
  - DuckDB 0.10 の制約（executemany に空リスト不可）を考慮した実装になっています。
- 時刻・ルックアヘッド対策:
  - 主要な関数（score_news, score_regime 等）は datetime.today()/date.today() を直接参照せず、必ず target_date を引数として与える設計。ルックアヘッドバイアスを防ぐためです。
- 再現性・テスト:
  - OpenAI 呼び出しは内部で _call_openai_api を使うため、ユニットテスト時に patch で差し替える想定です。
- フォールバック・堅牢性:
  - データ不足時（MA 計算に十分な行がない等）は中立値（例: ma200_ratio=1.0）やスコア 0.0 を用いるなどフェイルセーフを採用しています。
- レジーム判定に用いる ETF:
  - 現在はハードコードで ETF コード "1321" を使用します（日本株全体の代理指標としての運用）。

---

フィードバックや追加の履歴要望があれば、どのレベルの詳細（例えば個別コミットごとの差分や設計決定の原本メモ）まで記載するかを指定してください。