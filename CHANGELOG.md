CHANGELOG
=========

すべての注目できる変更はこのファイルに記録します。
このファイルは "Keep a Changelog" の形式に準拠します。
配布・利用する際の互換性や運用上の注意点は各リリースノートを参照してください。

Unreleased
----------
（現在未リリースの変更はここに記載します）

[0.1.0] - 2026-03-28
-------------------

Added
- 初回リリース: kabusys パッケージを追加（バージョン 0.1.0）。
  - パッケージ構成:
    - kabusys.config: 環境変数 / .env ファイル読み込み・設定管理を提供
      - 自動 .env ロード機能（プロジェクトルートの検出: .git または pyproject.toml）
      - .env/.env.local の読み込み順序、OS 環境変数保護（protected set）、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化
      - .env 行パーサーは export 形式・クォート・エスケープ・インラインコメントに対応
      - Settings クラスで必要な設定をプロパティで提供（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL）
      - KABUSYS_ENV / LOG_LEVEL の値検証（許容値チェック）
    - kabusys.ai
      - news_nlp: ニュースのセンチメント解析パイプライン
        - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）に基づく記事集約（銘柄ごと）
        - 1チャンク最大 20 銘柄のバッチ処理、1銘柄あたり記事数・文字数制限（_MAX_ARTICLES_PER_STOCK/_MAX_CHARS_PER_STOCK）
        - OpenAI (gpt-4o-mini) の JSON mode を利用したスコア取得
        - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライ実装
        - レスポンス検証機能（JSON 抽出、results リスト・code/score 検証、スコア ±1.0 クリップ）
        - ai_scores テーブルへの冪等書き換え（該当コードのみ DELETE → INSERT）
        - フェイルセーフ: API 失敗時はスキップして他銘柄は継続
      - regime_detector: 市場レジーム判定
        - ETF 1321 の 200 日移動平均乖離（ウエイト 70%）とニュース由来のマクロセンチメント（ウエイト 30%）を合成して日次で 'bull'/'neutral'/'bear' を判定
        - calc_news_window を使用したニュース窓の取得、ma200_ratio 計算、OpenAI による macro_sentiment 取得
        - OpenAI 呼び出しに対するリトライ・フェイルセーフ（失敗時 macro_sentiment=0.0）
        - market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）
        - look-ahead バイアス防止設計（内部で datetime.today()/date.today() を参照せず、target_date 未満のデータのみを使用）
    - kabusys.data
      - calendar_management: JPX カレンダー管理・営業日判定ロジック
        - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day 実装
        - market_calendar がない場合の曜日ベース（週末除外）フォールバック
        - calendar_update_job: J-Quants からの差分取得 / 冪等保存、バックフィル、健全性チェック
      - pipeline / etl: ETL パイプライン基盤
        - ETLResult データクラスを公開（取得件数、保存件数、品質問題、エラー集約を保持）
        - 差分取得・max date 判定ユーティリティ実装
      - jquants_client との連携を想定した差分取得・保存フロー（モジュール参照・例外ハンドリング）
    - kabusys.research
      - factor_research: ファクター計算（momentum, volatility, value）
        - mom_1m/3m/6m、ma200_dev、atr_20、atr_pct、avg_turnover、volume_ratio、per、roe など
        - DuckDB を用いた SQL ベースの集計（prices_daily / raw_financials のみ参照）
      - feature_exploration: 研究用ユーティリティ
        - calc_forward_returns（任意ホライズン対応・入力検証）
        - calc_ic（スピアマンランク相関）
        - factor_summary（count/mean/std/min/max/median）
        - rank（平均ランクによる tie ハンドリング）
    - 共通: DuckDB を主要なストレージ・照会エンジンとして使用

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）  
- 実装上のフェイルセーフ／堅牢化:
  - OpenAI API 呼び出し失敗時は例外伝播ではなく適切にフォールバック（macro_sentiment=0.0、またはそのチャンクをスキップ）する実装を導入
  - JSON モードでも周辺テキスト混入を考慮したパース復元処理を実装
  - DuckDB executemany の仕様差異（空リスト不可）を考慮したガードを追加

Security
- API キーの扱い:
  - OpenAI API キーは引数で注入可能（api_key 引数）かつ環境変数 OPENAI_API_KEY を使用
  - settings は必須トークンを要求し、未設定時は例外を投げることで明示的に設定の有無を検出

Notes / Breaking changes / Operational notes
- 環境変数（主要）
  - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - 任意 / デフォルトあり: KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）、DUCKDB_PATH（data/kabusys.duckdb）、SQLITE_PATH（data/monitoring.db）
  - 制御: KABUSYS_ENV (development | paper_trading | live)、LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL)
  - 自動 .env ロードを抑制するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定する
- 時刻・ウィンドウ取り扱い:
  - calc_news_window は JST 基準のニュース窓を UTC naive datetime に変換して返す（内部で UTC 対応済みの設計）
  - すべての日付は date オブジェクトで扱い、ルックアヘッドバイアス防止のため関数は target_date を引数として受け取る設計
- データベース操作:
  - ai_scores や market_regime などの書き込みは部分失敗時に既存データを保護するため、対象コードのみを DELETE → INSERT する方式を採用
  - トランザクションは BEGIN/COMMIT/ROLLBACK を明示的に使用
- OpenAI 呼び出し:
  - gpt-4o-mini を想定した JSON mode を利用（response_format={"type": "json_object"}）
  - テスト容易性のため _call_openai_api をモック可能に設計（unittest.mock.patch に対応）
- 依存と互換性:
  - DuckDB に依存（DuckDB のバージョン差異を考慮した実装注意点あり）
  - 外部 API（J-Quants, OpenAI）との疎結合設計で、API 失敗時はログを残して処理を継続する方針

References
- パッケージバージョンは kabusys.__version__ = "0.1.0"
- このリリースのコードは内部設計注釈（コメント）を含み、運用・テストのための注記が各モジュールに記載されています。

--- 
今後のリリースでは以下の改善・追加を予定しています（例）
- 追加ファクター（PBR/配当利回り等）の実装
- 監視 / アラート（Slack通知）連携の実装拡張
- より詳細な品質チェックの自動化と UI/ダッシュボード連携
- 単体テスト・統合テストの充実（CI 設定）