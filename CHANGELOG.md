# CHANGELOG

すべての注目すべき変更をここに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

全般的な注意
- 本リリースはパッケージの初回公開相当の内容を想定して CHANGELOG を作成しています。コードベースから推測できる機能・設計方針・外部依存・設定項目などをまとめています。

[0.1.0] - 2026-03-29
Added
- パッケージ基盤
  - kabusys パッケージの初期実装を追加。
  - バージョン: 0.1.0（src/kabusys/__init__.py）。
  - パッケージ公開 API として data, strategy, execution, monitoring を __all__ で定義。

- 設定・環境変数管理 (kabusys.config)
  - .env ファイル（.env/.env.local）または OS 環境変数から設定を自動読み込みする実装を追加。
    - 自動ロードはプロジェクトルート（.git または pyproject.toml を探索）を基準に行うため、CWD に依存しない。
    - .env の読み込み順序: OS 環境変数 > .env.local > .env。
    - OS 環境変数を保護するため protected set を用いて上書きを制御。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env のパース挙動は export プレフィクス、シングル/ダブルクォート、エスケープ、インラインコメント等を考慮。
  - Settings クラスを提供（settings インスタンス経由で利用）。
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID を必須として検証。
    - KABUSYS_ENV: development / paper_trading / live の列挙検証を実装。
    - LOG_LEVEL のバリデーション実装。
    - デフォルトの DB パス（DuckDB: data/kabusys.duckdb、SQLite: data/monitoring.db）を設定。

- AI（自然言語処理）機能 (kabusys.ai)
  - ニュースセンチメント（score_news）
    - raw_news と news_symbols をソースに、銘柄ごとのニュースを集約して OpenAI (gpt-4o-mini) に JSON モードで送信し、銘柄毎の ai_score（-1.0～1.0）を ai_scores テーブルに書き込む機能を実装。
    - タイムウィンドウ定義（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window で提供。
    - バッチ送信（最大 20 銘柄 / コール）、1 銘柄当たり記事数と文字数制限（デフォルト: 最大 10 記事、3000 文字）を実装。
    - JSON レスポンスの堅牢なバリデーションとスコアのクリップ（±1.0）。
    - レート制限・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライの実装。API 例外に対してはフェイルセーフでスキップし処理継続。
    - テスト容易性のため _call_openai_api の差し替え（patch）を想定。
    - 部分失敗時にも既存スコアを保護するため、DELETE→INSERT で対象コードのみ置換する冪等的な DB 書き込みを実装。
  - 市場レジーム判定（score_regime）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して market_regime テーブルへ日次で書き込む機能を実装。
    - マクロニュース抽出のためのキーワードセットを実装（日本・米国・グローバルの経済用語を含む）。
    - OpenAI 呼び出しは独立実装でモジュール結合を避け、API の失敗時は macro_sentiment=0.0 にフォールバックするフェイルセーフ設計。
    - レジームスコアの閾値判定（bull/neutral/bear）と、冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
    - API 呼び出しに対するリトライ（指数バックオフ）、および JSON パース失敗の安全処理を実装。

- データプラットフォーム (kabusys.data)
  - カレンダー管理（calendar_management）
    - market_calendar テーブルを利用した営業日判定・探索ユーティリティを提供。
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days を実装。
    - market_calendar が未取得の場合は曜日ベースのフォールバック（土日を非営業日）を採用。
    - 最大探索日数の上限 (_MAX_SEARCH_DAYS) を取り入れ、無限ループを防止。
    - 夜間バッチ更新 job (calendar_update_job) を実装。J-Quants クライアントから差分取得し save_market_calendar で冪等保存。バックフィルと健全性チェックを実施。
  - ETL パイプライン（pipeline, etl）
    - ETLResult データクラスを公開（ETL 実行結果の集約）。
    - 差分取得、IDempotent 保存（jquants_client 経由）、品質チェック（quality モジュール）を想定した ETL 設計方針を実装。
    - テーブル存在チェックや最大日付取得ユーティリティを提供。

- Research（kabusys.research）
  - ファクター計算（factor_research）
    - Momentum（1M/3M/6M、MA200乖離）、Volatility（20日 ATR、相対ATR）、Value（PER、ROE）などの定量ファクターを DuckDB 上で計算する関数を追加。
    - prices_daily / raw_financials のみ参照し、本番取引 API にはアクセスしない設計。
  - 特徴量探索（feature_exploration）
    - 将来リターン計算（calc_forward_returns）を実装（任意ホライズン、デフォルト [1,5,21]）。
    - スピアマンの IC（calc_ic）、ランク変換ユーティリティ（rank）、統計サマリー（factor_summary）を実装。
    - 外部依存（pandas 等）を用いず標準ライブラリで実装。
  - 研究用 API をモジュールトップで再エクスポート（利便性向上）。

- 互換性 / テスト性のための設計上の配慮
  - ルックアヘッドバイアス防止: いずれの機能も datetime.today()/date.today() を直接参照せず、target_date 引数ベースで動作するよう実装。
  - OpenAI 呼び出し等は差し替え可能にし、単体テストでモックできることを想定。
  - DuckDB 0.10 系を考慮した executemany の空リスト回避等の実装上の配慮。

Documentation / Notes
- 必須環境変数（例）
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は Settings 経由で必須設定として扱われる（未設定時は ValueError）。
  - OPENAI_API_KEY は score_news / score_regime の実行に必要（api_key 引数での注入も可能）。
  - KABUSYS_ENV: development / paper_trading / live のいずれか。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を指定すると .env 自動読み込みを無効化。
- デフォルト DB パス
  - DuckDB: data/kabusys.duckdb
  - SQLite (monitoring): data/monitoring.db
- 期待される DuckDB テーブル（主なもの）
  - prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials など。各機能はこれらのテーブル存在を前提に動作する。
- 外部依存
  - openai SDK（OpenAI クライアント）および duckdb を利用。
  - J-Quants クライアントインターフェース（kabusys.data.jquants_client）を想定。

Fixed
- 初期リリースのため該当なし。

Changed
- 初期リリースのため該当なし。

Removed
- 初期リリースのため該当なし。

Security
- 初期リリースのため該当なし。

将来の注記（開発者向け）
- OpenAI モデルや API 呼び出しに関する挙動（モデル名、レスポンス形式、ステータスコードの扱い）は SDK の変更に伴い調整が必要となる可能性があります。APIError 等からの status_code 取得は getattr を用いて安全に扱う実装を行っていますが、将来的に SDK の仕様変更がある場合はテストとレビューを推奨します。
- DuckDB のバージョン互換性により SQL バインド振る舞いが変わるため executemany 周りの挙動に注意してください。

以上。