# Changelog

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。  
このリポジトリの最初の公開リリースを下に記載します（コードベースから推測して作成）。

## [0.1.0] - 2026-03-17

### 追加 (Added)
- パッケージ初期化
  - kabusys パッケージの基本構造を追加。バージョンは 0.1.0。
  - サブパッケージ：data, strategy, execution, monitoring をエクスポート。

- 環境設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を自動読み込み（優先順位: OS 環境 > .env.local > .env）。
  - プロジェクトルート検出ロジック（.git または pyproject.toml を探索）を実装し、カレントディレクトリに依存しない読み込みを実現。
  - .env パーサを実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープシーケンス、インラインコメント処理に対応）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート（テスト用）。
  - Settings クラスを提供し、必須環境変数の取得（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）と検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）を行う。
  - データベースパス (duckdb, sqlite) の既定値と Path での展開を提供。
  - 環境判定ユーティリティ（is_live, is_paper, is_dev）を追加。

- J-Quants クライアント (kabusys.data.jquants_client)
  - J-Quants API からのデータ取得機能を実装（株価日足、財務データ（四半期 BS/PL）、マーケットカレンダー）。
  - レート制限を守るための固定間隔スロットリング (_RateLimiter、120 req/min 相当) を導入。
  - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を再試行対象）を実装。
  - 401 Unauthorized 受信時にリフレッシュトークンで自動リフレッシュして 1 回だけ再試行する仕組みを実装（無限再帰防止のため allow_refresh フラグあり）。
  - ページネーション対応の fetch 関数（fetch_daily_quotes, fetch_financial_statements）を実装（pagination_key の重複チェックで安全にループ終了）。
  - 取得時刻（fetched_at）を UTC ISO 形式で付与して Look-ahead bias を追跡できるように設計。
  - DuckDB へ冪等に保存する save_* 関数を実装（ON CONFLICT DO UPDATE を使用して重複を排除／更新）。
  - 型変換ユーティリティ _to_float, _to_int を提供（不正値や空文字の扱い、"1.0" のような float 文字列の安全な int 変換の扱いを明確化）。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードから記事を収集して raw_news テーブルへ保存する機能を実装。
  - セキュリティ上の対策を多数導入:
    - defusedxml を使用して XML Bomb 等の攻撃を防止。
    - SSRF 対策: URL スキーム検証（http/https のみ許可）、ホストがプライベート/ループバック/リンクローカル/マルチキャストかを判定し拒否、リダイレクト時にも検証するカスタム RedirectHandler を導入。
    - レスポンス最大サイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズチェック（Gzip bomb 対策）。
    - 受信時の Content-Length チェックと読み取り上限。
  - URL 正規化とトラッキングパラメータ除去を実装（_normalize_url）。
  - 記事 ID を正規化 URL の SHA-256 の先頭 32 文字で一意生成し冪等性を担保（_make_article_id）。
  - テキスト前処理（URL 除去、空白正規化）実装（preprocess_text）。
  - RSS の pubDate を UTC naive datetime にパースするユーティリティを追加（_parse_rss_datetime）。
  - DB 保存はチャンク化してトランザクション内で実行し、INSERT ... RETURNING により実際に挿入された ID を返す（save_raw_news, save_news_symbols, _save_news_symbols_bulk）。
  - 銘柄コード抽出ロジックを実装（4 桁数字の候補から known_codes に存在するもののみ抽出、重複除去）。

- DuckDB スキーマ管理 (kabusys.data.schema)
  - DataSchema.md に基づく 3 層（Raw / Processed / Feature）+ Execution 層のテーブル定義を実装。
  - raw_prices, raw_financials, raw_news, raw_executions 等の Raw テーブルを定義。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の Processed テーブルを定義。
  - features, ai_scores などの Feature 層を定義。
  - orders, trades, positions, signal_queue 等の Execution 層を定義。
  - 運用上の頻出クエリを想定したインデックスを作成（例: idx_prices_daily_code_date, idx_signal_queue_status など）。
  - init_schema(db_path) により親ディレクトリ自動作成、全テーブルとインデックスを冪等に作成して DuckDB 接続を返す。
  - get_connection(db_path) により既存 DB へ接続するユーティリティを提供。

- ETL パイプライン (kabusys.data.pipeline)
  - ETL の設計方針に基づくユーティリティ群と ETLResult データクラスを実装。
  - 差分更新（最終取得日に基づく date_from 自動算出、backfill_days による緩和）をサポートする helper を実装（get_last_price_date, get_last_financial_date, get_last_calendar_date, _get_max_date, _table_exists）。
  - 市場カレンダーに基づく営業日調整ロジックを実装（_adjust_to_trading_day）。
  - run_prices_etl を追加（差分フェッチ→保存→品質チェックの流れを想定。fetch/save は jquants_client を利用）。品質チェック用モジュール quality との連携を想定。

- その他
  - デフォルト RSS ソースを追加（Yahoo Finance のビジネスカテゴリ RSS）。
  - テスト用の差し替えポイントを設計（例: news_collector._urlopen をモック可能にして HTTP 呼び出しを差し替えやすくしている）。

### 修正 (Fixed)
- （初回リリースのため大きな修正履歴は無し。実装時の設計/安全性を重視した調整が含まれる）

### セキュリティ (Security)
- XML パーサに defusedxml を採用して XML 関連の攻撃を防止。
- RSS フェッチ時の SSRF 対策を強化（スキーム検証、プライベートアドレス拒否、リダイレクト検査）。
- .env 読み込み時に OS 環境変数を保護する protected 機構を導入（.env.local での上書き制御など）。
- HTTP 429 応答時は Retry-After ヘッダを優先してリトライ待機時間を決定。

### 既知の問題 / TODO
- run_prices_etl の戻り値が本来の仕様（取得数, 保存数 のタプル）から外れている可能性があります（コード末尾で saved を返していない/戻り値が不完全な形になっている）。意図は (len(records), saved) を返すことと推測されます。実運用前に戻り値と呼び出し側の期待値を確認し修正してください。
- strategy と execution パッケージは __init__.py が存在するのみで、具体的な戦略実装・発注ロジックは未実装（今後の追加予定）。
- quality モジュールは参照されているが（ETLResult 等）、ここに含まれるファイル群は今回のスナップショットには含まれていないようです。品質チェックの具体実装とルール定義を追加する必要あり。
- テストカバレッジ、エラーハンドリングの端点テスト（特にネットワーク障害・リダイレクト・巨大レスポンス）を追加で整備することを推奨。

---

上記はソースコードの内容から推測してまとめた CHANGELOG です。必要であれば、リリースノートの文言や日付をプロジェクトの実際のリリース方針に合わせて調整します。