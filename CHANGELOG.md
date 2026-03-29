# CHANGELOG

すべての重要な変更点をこのファイルに記載します。  
フォーマットは Keep a Changelog に準拠しており、セマンティックバージョニングに従います。

## [0.1.0] - 2026-03-29

初回公開リリース。

### 追加 (Added)
- パッケージ基盤
  - パッケージメタ情報を追加（kabusys.__version__ = "0.1.0"）。
  - top-level のエクスポートを定義（data, strategy, execution, monitoring）。

- 設定/環境変数管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
    - 自動ロード順序: OS 環境変数 > .env.local > .env
    - プロジェクトルート検出: __file__ の親階層を .git または pyproject.toml で探索（CWD に依存しない）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env パーサは export KEY=val 形式、クォート内のバックスラッシュエスケープ、インラインコメント対応などに対応。
  - Settings クラスを提供し、以下の設定プロパティを公開：
    - jquants_refresh_token (JQUANTS_REFRESH_TOKEN)
    - kabu_api_password (KABU_API_PASSWORD)
    - kabu_api_base_url (KABU_API_BASE_URL, デフォルト http://localhost:18080/kabusapi)
    - slack_bot_token (SLACK_BOT_TOKEN)
    - slack_channel_id (SLACK_CHANNEL_ID)
    - duckdb_path (DUCKDB_PATH, デフォルト data/kabusys.duckdb)
    - sqlite_path (SQLITE_PATH, デフォルト data/monitoring.db)
    - env (KABUSYS_ENV: development | paper_trading | live)
    - log_level (LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL)
    - is_live / is_paper / is_dev 判定ヘルパー
  - 必須設定未提供時は明確な ValueError を送出する実装。

- AI（自然言語処理）機能（kabusys.ai）
  - ニュースセンチメントスコアリング（kabusys.ai.news_nlp.score_news）
    - raw_news と news_symbols から銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）の JSON モードでセンチメントを取得して ai_scores テーブルに書き込む。
    - タイムウィンドウ（JST 前日15:00～当日08:30）を calc_news_window() で正確に計算（UTC naive datetime を返す）。
    - バッチ処理（デフォルト 20 銘柄/リクエスト）、記事数/文字数トリム、JSON レスポンスの厳密バリデーション、スコアクリッピング（±1.0）。
    - エラー耐性: 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ、API 以外の失敗はスキップして継続するフェイルセーフ設計。
    - テスト時に _call_openai_api をパッチ差し替え可能。
  - 市場レジーム判定（kabusys.ai.regime_detector.score_regime）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロセンチメント（重み 30%）を合成して日次でレジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込みを行う。
    - マクロニュース抽出は news_nlp.calc_news_window と raw_news からキーワードでフィルタ。
    - OpenAI 呼び出しは JSON 出力を期待し、API の再試行・ステータス別ハンドリングとフェイルセーフ（失敗時 macro_sentiment=0.0）を実装。
    - ルックアヘッドバイアス対策: date 引数ベースで処理し、DB クエリは target_date 未満の排他条件を守る。

- データプラットフォーム（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar を用いた営業日判定と補助関数を実装:
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days
    - market_calendar が未取得時は曜日ベース（土日除外）でフォールバック。
    - 夜間バッチ更新 job: calendar_update_job() を実装し、J-Quants クライアント経由で差分取得→保存（バックフィル・健全性チェックあり）。
    - 最大探索日数やバックフィル日数等の安全策を導入（_MAX_SEARCH_DAYS, _BACKFILL_DAYS, _SANITY_MAX_FUTURE_DAYS 等）。
  - ETL パイプライン（kabusys.data.pipeline, kabusys.data.etl）
    - ETLResult データクラスを実装（ETL 実行の取得件数・保存件数・品質問題・エラーの集約）。
    - 差分更新、バックフィル、品質チェックフック（quality モジュールとの連携）を想定したユーティリティを用意。
    - 内部ユーティリティ: テーブル存在チェック、最大日付取得等を実装。
    - kabusys.data.etl は pipeline.ETLResult を再エクスポート。

- リサーチ／ファクター解析（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離などを計算（prices_daily に対する SQL 実装）。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算。
    - calc_value: 最新の raw_financials を用いて PER/ROE を計算（target_date 以前の最新レコードを参照）。
    - 設計上、外部 API にはアクセスせず DuckDB 上の SQL と Python の組合せで計算。
  - 特徴量探索（kabusys.research.feature_exploration）
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括 SQL クエリで計算。
    - calc_ic: ファクター値と将来リターンのスピアマン順位相関（IC）を計算（有効レコードが 3 未満の場合 None）。
    - rank: 同順位は平均ランクにするランク変換（浮動小数の丸め対策あり）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を算出。
    - pandas 等の外部依存を避け、標準ライブラリ + DuckDB で実装。

### 変更 (Changed)
- 初回リリースのためなし。

### 修正 (Fixed)
- 初回リリースのためなし。

### 削除 (Removed)
- 初回リリースのためなし。

### セキュリティ (Security)
- 初回リリースのためなし。

---

## 仕様・注意事項（重要）
- OpenAI API
  - news_nlp と regime_detector は OpenAI（gpt-4o-mini）を前提としており、API キーは引数で注入可能（api_key）または環境変数 OPENAI_API_KEY を使用。
  - API 呼び出しは JSON モードを期待しており、レスポンスの厳密な検証を行う。テスト時は内部の _call_openai_api をモックしてテスト可能。
- データベース接続
  - 多くの関数は duckdb.DuckDBPyConnection を直接受け取る（prices_daily, raw_news, ai_scores, market_regime, raw_financials, news_symbols 等のテーブルが必要）。
  - DuckDB のバージョン依存（executemany の空リスト制約など）を考慮した実装上の注意がある。
- ルックアヘッドバイアス対策
  - 日付関連処理（ニュースウィンドウ、ファクター計算、レジーム判定等）はすべて target_date 引数ベースで実行し、内部で datetime.today()/date.today() を参照しないよう設計されている（検証・バックテスト用途に配慮）。
- .env 自動ロード
  - 自動的にプロジェクトルートの .env / .env.local を読み込むが、テストなどで無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定する。

## 既知の制限 / 今後の改善候補
- news_nlp の出力フォーマットに強く依存しているため、LLM の挙動変化やモデル差替えに伴う調整が必要になる可能性がある。
- 一部の SQL は DuckDB のウィンドウ関数に依存しており、大規模データセットでのパフォーマンス評価・最適化の余地あり。
- ETL の品質チェック（quality モジュール）や jquants_client 実装は呼び出し元への依存を前提としており、エラー分類や通知機能の拡充が今後の課題。

---

もし特定モジュールや関数（例: score_news の入出力仕様、calc_news_window の具体例、Settings の動作）の詳細をCHANGELOG に追記してほしい場合は、どの情報を追記するか教えてください。