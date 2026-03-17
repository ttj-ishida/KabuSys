# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に従い、セマンティックバージョニングに基づいています。

## [0.1.0] - 2026-03-17

初回リリース。日本株自動売買システム "KabuSys" の基盤機能を実装しました。主な追加点は以下の通りです。

### 追加 (Added)
- パッケージ初期化
  - src/kabusys/__init__.py
    - パッケージメタ情報（__version__ = "0.1.0"）と公開サブパッケージを定義。

- 環境設定管理
  - src/kabusys/config.py
    - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
    - 自動 .env ロード機能（プロジェクトルートは .git または pyproject.toml で判定）。
    - 読み込み順序: OS 環境変数 > .env.local > .env。テスト等で自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - .env パーサは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応。
    - 必須環境変数チェック用の _require() と、環境値検証（KABUSYS_ENV, LOG_LEVEL）を実装。
    - デフォルト値や Path 型変換（duckdb/sqlite のパス）などのユーティリティを提供。
    - J-Quants / kabuステーション / Slack 等の設定プロパティを定義。

- J-Quants API クライアント
  - src/kabusys/data/jquants_client.py
    - 日足・財務データ・市場カレンダーを取得する fetch_* 関数を実装（ページネーション対応）。
    - HTTP リクエストユーティリティ _request():
      - レート制限 (120 req/min) に従う固定間隔スロットリング実装（_RateLimiter）。
      - リトライロジック（最大 3 回、指数バックオフ、408/429/5xx を再試行対象）。
      - 401 受信時は id_token を自動リフレッシュして 1 回だけリトライ。
      - JSON デコードエラーハンドリング。
    - get_id_token() によるリフレッシュトークンからの idToken 取得。
    - DuckDB へ冪等に保存する save_* 関数群（ON CONFLICT DO UPDATE）を実装:
      - save_daily_quotes, save_financial_statements, save_market_calendar
      - fetched_at を UTC タイムスタンプで記録し、Look-ahead bias のトレースを可能に。
    - 型変換ユーティリティ _to_float/_to_int を用意（安全な変換と None 戻しの方針を明示）。

- ニュース収集モジュール（RSS -> DuckDB）
  - src/kabusys/data/news_collector.py
    - RSS フィードから記事を収集し raw_news / news_symbols に保存するフルスタック実装。
    - セキュリティ・堅牢性:
      - defusedxml を用いた XML パース（XML Bomb 等の防御）。
      - SSRF 対策: URL スキーム検証（http/https のみ）、ホストがプライベート/ループバック/リンクローカル/マルチキャストかを判定して拒否。
      - リダイレクト時も事前検証するカスタム HTTPRedirectHandler を実装。
      - レスポンスの最大バイト数制限（MAX_RESPONSE_BYTES = 10MB）を導入しメモリDoS防止。
      - gzip 圧縮レスポンスの解凍と解凍後サイズチェック（Gzip bomb 対策）。
    - 記事 ID の決定方法:
      - URL を正規化して（スキーム/ホスト小文字化、追跡パラメータ除去、フラグメント削除、クエリパラメータソート）SHA-256 の先頭32文字を ID として生成。これにより冪等性を担保。
    - テキスト前処理:
      - URL 除去、空白正規化、トリミング等を行う preprocess_text。
    - DB 保存:
      - save_raw_news はチャンク化して INSERT ... ON CONFLICT DO NOTHING RETURNING id を使い、実際に挿入された id のリストを返す（トランザクションでまとめる）。
      - save_news_symbols / _save_news_symbols_bulk で (news_id, code) の紐付けをチャンク INSERT で保存し挿入数を正確に返す。
    - 銘柄コード抽出:
      - extract_stock_codes: 4桁数字パターンを known_codes と照合して抽出（重複除去）。

- DuckDB スキーマ定義と初期化
  - src/kabusys/data/schema.py
    - DataSchema.md に基づく 3 層（Raw / Processed / Feature）＋実行レイヤーのテーブル定義を実装。
    - raw_prices, raw_financials, raw_news, raw_executions を含む Raw Layer。
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の Processed Layer。
    - features, ai_scores 等の Feature Layer。
    - signals, signal_queue, orders, trades, positions, portfolio_performance 等の Execution Layer。
    - インデックス定義（例: code×date や status 用）を実装。
    - init_schema(db_path) でディレクトリ作成〜全DDL実行（冪等）して接続を返す。get_connection(db_path) で既存 DB へ接続可能。
    - 各テーブルに適切なチェック制約（NOT NULL / CHECK / PRIMARY KEY / FOREIGN KEY）を定義。

- ETL パイプライン（差分更新・品質チェック連携）
  - src/kabusys/data/pipeline.py
    - ETLResult dataclass を実装（取得数／保存数／品質問題／エラー等を集約）。
    - 差分更新ヘルパー: 最終取得日取得関数 get_last_price_date / get_last_financial_date / get_last_calendar_date。
    - 市場カレンダー補正ヘルパー _adjust_to_trading_day（非営業日の調整）。
    - run_prices_etl の差分更新ロジック（最終取得日から backfill_days 前を date_from として再取得する挙動をサポート）。
    - 定数:
      - データ開始日 _MIN_DATA_DATE = 2017-01-01（初回ロード用）
      - カレンダー先読み _CALENDAR_LOOKAHEAD_DAYS = 90
      - デフォルト backfill_days = 3
    - 品質チェックは quality モジュールと連携する想定（quality.QualityIssue を扱う設計）。

- プレースホルダ / パッケージ構成
  - src/kabusys/data/__init__.py, src/kabusys/execution/__init__.py, src/kabusys/strategy/__init__.py を追加（パッケージ構成を整備）。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 削除 (Removed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- news_collector に SSRF 対策、defusedxml 使用、レスポンスサイズ制限等のセキュリティ強化を実装。

---

注意事項 / 備考:
- 環境変数・設定のうち必須のもの（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD 等）を未設定でアクセスすると ValueError を送出します。.env.example を参考に .env を作成してください。
- jquants_client のデフォルト API ベース URL は "https://api.jquants.com/v1"、kabu API のデフォルトは "http://localhost:18080/kabusapi" です。必要に応じて環境変数で上書きしてください。
- DuckDB のデフォルトファイルパスは data/kabusys.duckdb（init_schema は親ディレクトリを自動作成します）。":memory:" を指定するとインメモリ DB を使用できます。
- news_collector の extract_stock_codes は known_codes を与えると抽出を絞り込みます。known_codes を渡さない場合は紐付け処理をスキップします。
- ETL の品質チェックは設計上、品質エラーを検出しても即時停止はせず、呼び出し元が判断する方式です。

今後の予定（例）
- strategy / execution の具体的な戦略実装・発注ロジックの追加。
- quality モジュールの実装と ETL 内での自動アクション（アラート送信など）。
- テストカバレッジ拡充と CI/CD の整備。