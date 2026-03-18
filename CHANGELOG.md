CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。形式は "Keep a Changelog" に準拠しています。

[Unreleased]
-------------

（なし）

[0.1.0] - 2026-03-18
-------------------

Added
- パッケージ初期リリース: KabuSys — 日本株自動売買システムの基礎機能を追加。
  - パッケージエントリポイント: kabusys.__version__ = "0.1.0"、公開モジュール data / strategy / execution / monitoring を定義。
- 環境設定管理 (kabusys.config):
  - .env ファイルおよび環境変数から設定を自動ロード（プロジェクトルートを .git または pyproject.toml で探索）。
  - 読み込み優先順位: OS環境変数 > .env.local > .env。
  - 自動ロード無効化用フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサ実装: export 形式対応、クォート/エスケープ処理、インラインコメント処理。
  - Settings クラスを公開（プロパティ経由で設定取得）:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（デフォルト data/monitoring.db）
    - KABUSYS_ENV の検証（allowed: development, paper_trading, live）
    - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - is_live / is_paper / is_dev の便宜プロパティ
- J-Quants API クライアント (kabusys.data.jquants_client):
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーの取得関数を実装（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）。
  - レート制御: 固定間隔スロットリングにより 120 req/min（_RateLimiter）。
  - リトライロジック: 指数バックオフ（base=2.0）、最大 3 回、対象ステータス (408, 429, 5xx)。429 の場合は Retry-After ヘッダを尊重。
  - 401 レスポンス時の自動トークンリフレッシュ（1 回のみ）と再試行処理を実装。トークンはモジュールレベルでキャッシュ。
  - ページネーション対応（pagination_key を使った繰り返し取得）。
  - DuckDB への冪等保存（save_daily_quotes / save_financial_statements / save_market_calendar）:
    - fetched_at を UTC ISO 形式（Z）で記録し、Look-ahead バイアスのトレースを想定。
    - INSERT ... ON CONFLICT DO UPDATE で同一 PK の更新を行い冪等性を確保。
  - 型変換ユーティリティ (_to_float / _to_int) を実装し不正値を安全に扱う。
- ニュース収集モジュール (kabusys.data.news_collector):
  - RSS フィード取得と記事保存のフルフローを実装（fetch_rss / save_raw_news / save_news_symbols / run_news_collection）。
  - 記事IDは URL 正規化後の SHA-256（先頭32文字）で生成し冪等性を担保（utm_* 等のトラッキングパラメータ除去）。
  - XML の安全パーサ defusedxml を利用して XML Bomb 等に対策。
  - SSRF 対策:
    - URL スキーム検証（http/https のみ）。
    - リダイレクト時にスキームとホストの事前検証（_SSRFBlockRedirectHandler）。
    - ホストがプライベート/ループバック/リンクローカル/マルチキャストであれば拒否（_is_private_host）。
  - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）を導入しメモリ DoS を防止。gzip 解凍後のサイズ検査も実施（Gzip bomb 対策）。
  - テキスト前処理（URL 除去・空白正規化）と銘柄コード抽出（4桁数字、known_codes フィルタ）を実装。
  - DuckDB への保存はチャンク化＆トランザクション化し、INSERT ... RETURNING を使用して実際に挿入された件数を正確に取得。
- DuckDB スキーマ定義と初期化 (kabusys.data.schema):
  - DataPlatform に基づく 3 層（Raw / Processed / Feature + Execution）をカバーするテーブル群を定義。
  - 主要テーブル例: raw_prices, raw_financials, raw_news, market_calendar, prices_daily, fundamentals, features, ai_scores, signal_queue, orders, trades, positions, portfolio_performance など。
  - 各種制約（PRIMARY KEY、CHECK、FOREIGN KEY）を設置してデータ整合性を高める。
  - 頻出クエリ向けのインデックスを定義。
  - init_schema(db_path) によりディレクトリ作成 → テーブル/インデックス作成 → DuckDB 接続を返す。get_connection は既存 DB への接続を返す（初期化は行わない）。
- ETL パイプライン基盤 (kabusys.data.pipeline):
  - 差分更新ロジック（DB の最終取得日から未取得分のみ取得）と backfill_days による後出し修正吸収を実装方針に組み込み。
  - ETLResult データクラス（品質問題・エラー情報を含む）を実装し結果の集約・変換を提供（to_dict）。
  - 市場カレンダーを考慮した取引日調整ユーティリティ (_adjust_to_trading_day) を実装。
  - raw_prices / raw_financials / market_calendar の最終取得日取得ユーティリティを提供。
  - run_prices_etl を実装（差分判定 → jq.fetch_daily_quotes → jq.save_daily_quotes を呼び出す）※差分処理・保存のフローを備える。

Security
- RSS パーサに defusedxml を導入して XML に関連する攻撃（外部実体、BOM 等）への耐性を確保。
- RSS/HTTP の SSRF 対策を多数導入（スキーム検証、プライベートアドレス検出、リダイレクト時検査）。
- ネットワークから受信するペイロードに対して最大バイト数を設定（MAX_RESPONSE_BYTES）し、メモリ/CPU DoS のリスクを低減。
- J-Quants クライアントでタイムアウト値を設定（urllib.request のタイムアウト）しハングを回避。

Changed
- （初回リリースなので変更履歴はありません）

Fixed
- （初回リリースなので修正履歴はありません）

Deprecated
- （なし）

Removed
- （なし）

注意 / 既知の問題
- run_prices_etl の戻り値定義について:
  - 実装中の run_prices_etl の最後の return でタプルの一部が欠けているように見える箇所が確認されます（コード末尾が途中で切れている）。実運用前に run_prices_etl が (fetched_count, saved_count) を確実に返すよう最終行の確認・修正を推奨します。
- テスト・運用時の注意:
  - 自動 .env ロードは CI やユニットテスト環境で予期せぬ環境変数上書きを行う可能性があるため、テストでは KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して自動ロードを無効化することを推奨します。
  - DuckDB スキーマは初回 init 時に作成されます。別プロセスでの同時初期化は競合する可能性があるため注意してください。

補足
- ログ出力や例外メッセージは実行時のトラブルシュートに有用な情報を出すよう設計されています（例: API リトライ時の警告、保存時のスキップ件数ログ、XML/ネットワークエラーの警告など）。
- 今後の改善案（例）:
  - ネットワーク操作の非同期化 / 並列化によるスループット改善（ただしレート制限に注意）。
  - news_collector のソース一覧を設定や DB から管理可能にする。
  - ETL の品質チェック（quality モジュール）をフル実装して自動アラート機能を追加。

---

このファイルはコードベースの現状から推測して作成しています。追加の変更やリリース情報があれば随時更新してください。