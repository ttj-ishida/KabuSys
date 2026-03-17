# Changelog

すべての注目に値する変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。

## [0.1.0] - 2026-03-17

初回リリース（ベース実装）。日本株自動売買システム「KabuSys」のコア機能群を実装しました。

### 追加 (Added)
- パッケージ基礎
  - パッケージのエントリポイントを追加（src/kabusys/__init__.py）。バージョンは 0.1.0、公開モジュールは data, strategy, execution, monitoring。

- 設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数を読み込む自動ロード機能を実装。読み込み順は OS 環境 > .env.local > .env。
  - プロジェクトルート検出 ( .git または pyproject.toml を探索 ) により、CWD に依存しない自動ロードを実現。
  - .env 行パーサを実装（export プレフィックス対応、シングル/ダブルクォート処理、インラインコメント処理）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能（テスト向け）。
  - 必須環境変数取得ヘルパ _require と Settings クラスを導入。J-Quants / kabuAPI / Slack / DB パス等の設定をプロパティとして提供。
  - KABUSYS_ENV / LOG_LEVEL の入力値検証を実装（許容値チェック）。

- J-Quants クライアント (src/kabusys/data/jquants_client.py)
  - J-Quants API 用クライアントを実装。
  - レート制限制御: 固定間隔スロットリング（デフォルト 120 req/min）を実装する RateLimiter。
  - リトライロジック: 指数バックオフ、最大 3 回、HTTP 408/429 と 5xx に対する再試行。
  - 401 Unauthorized を受けた場合はリフレッシュトークンで id_token を自動更新して 1 回リトライ（無限再帰防止を考慮）。
  - id_token のモジュールレベルキャッシュを導入（ページネーション間で共有）。
  - JSON デコードエラーやネットワークエラーに対する明確なエラーメッセージを実装。
  - データ取得関数:
    - fetch_daily_quotes: 株価日足（OHLCV）、ページネーション対応。
    - fetch_financial_statements: 四半期財務データ、ページネーション対応。
    - fetch_market_calendar: JPX マーケットカレンダー取得。
  - DuckDB への保存関数（冪等に保存、ON CONFLICT DO UPDATE）:
    - save_daily_quotes: raw_prices テーブルへ保存。fetched_at を UTC (ISO Z) で記録。
    - save_financial_statements: raw_financials テーブルへ保存。
    - save_market_calendar: market_calendar テーブルへ保存（is_trading_day / is_half_day / is_sq_day 変換）。
  - データ変換ユーティリティ _to_float / _to_int を実装（安全な変換と None 処理）。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードから記事を安全に取得・保存するニュースコレクタを実装。
  - セキュリティ対策:
    - defusedxml による XML パース（XML Bomb 対策）。
    - SSRF 対策: リダイレクト時のスキーム/ホスト検証用ハンドラ、ホストがプライベート/ループバックであれば拒否。
    - URL スキームは http/https のみ許可。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズ検査（Gzip bomb 対策）。
  - URL 正規化:
    - トラッキングパラメータ（utm_* 等）除去、スキーム/ホスト小文字化、フラグメント削除、クエリパラメータソート。
    - 正規化 URL の SHA-256（先頭32文字）から記事ID を生成し冪等性を確保。
  - RSS 取得関数 fetch_rss:
    - content:encoded を優先、description をフォールバック。
    - pubDate パース（失敗時は現在時刻を代替）。
    - 不正なフィードや大きすぎるレスポンスはスキップして警告ログ。
  - DuckDB 保存関数:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING + RETURNING id を利用し、新規挿入された記事ID一覧を返す。チャンク化（デフォルト 1000 件）かつ単一トランザクションで処理。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けをチャンク化して保存。ON CONFLICT で重複スキップ、INSERT ... RETURNING で挿入数を正確に返却。
  - 銘柄抽出:
    - extract_stock_codes: テキスト中の 4 桁数字を候補とし、known_codes に含まれるコードのみを返す（重複除去）。

- データスキーマ (src/kabusys/data/schema.py)
  - DuckDB 用スキーマ初期化モジュールを追加。
  - Raw / Processed / Feature / Execution 層を想定したテーブル定義を実装（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance 等）。
  - 各種列にチェック制約（NOT NULL / CHECK）を設定してデータ品質向上を図る。
  - 利用頻度の高いクエリを想定したインデックスを追加。
  - init_schema(db_path) を実装: 親ディレクトリの自動作成、DDL 実行、インデックス作成、接続返却。
  - get_connection(db_path) を追加（既存 DB への接続、スキーマ初期化は行わない）。

- ETL パイプライン (src/kabusys/data/pipeline.py)
  - ETL 実行結果を表す ETLResult dataclass を実装（品質問題・エラー集約、辞書化ヘルパ）。
  - スキーマ／テーブルの存在確認、最大日付取得ヘルパ（_table_exists, _get_max_date, get_last_price_date, get_last_financial_date, get_last_calendar_date）。
  - 市場カレンダーヘルパ _adjust_to_trading_day を実装（非営業日は過去方向で最も近い営業日に調整）。
  - run_prices_etl を実装（差分更新ロジック、デフォルトバックフィル 3 日、_MIN_DATA_DATE を初期開始日として利用、fetch と save の呼び出し、ロギング）。

### 変更 (Changed)
- —（初回リリースのため過去バージョンとの差分はなし）

### 修正 (Fixed)
- —（初回リリースのため修正履歴はなし）

### セキュリティ (Security)
- ニュース収集において SSRF 対策と defusedxml を利用した XML パース防御を導入。
- HTTP レスポンスサイズ制限や gzip 解凍後の再チェックにより、リモートからの DoS / Bomb 攻撃に対処。

### 既知の問題 / 注意点 (Known issues / Notes)
- pipeline.run_prices_etl の返り値について:
  - 実装では (取得レコード数, 保存レコード数) を返す想定ですが、現状ソースの末尾が "return len(records)," のように 2 要素ではなく 1 要素のタプル（または意図せぬ trailing comma）になっている箇所が見られます。ユースケースに応じて保存数を明示的に返す実装確認・修正を推奨します。
- DuckDB に対する SQL 実行は文字列連結でプレースホルダを構築している箇所があります（注: プレースホルダ自体は使用されていますが、動的 SQL を実行している場所では SQL インジェクションのリスクが無いように入力ソースを制御してください）。
- fetch_rss / HTTP 周りはネットワーク例外を呼び出し元へ伝播させる場合があるため、実運用ではリトライやバックオフのラッパーを検討してください。

## 今後の予定 (Planned)
- ETL 全体の品質チェック統合（quality モジュールとの連携強化）。
- strategy / execution / monitoring モジュールの実装（パッケージ公開済みの名前空間に対する機能追加）。
- CI テストの導入（.env 自動ロードを無効化する仕組みを活用してユニットテスト実行）。
- run_news_collection のスケジューリングや冪等性向上に関する運用改善。

---

（本 CHANGELOG はソースコードの内容から推測して作成しています。実際のリリースノート作成時はコミットログやリリース方針に基づいて調整してください。）