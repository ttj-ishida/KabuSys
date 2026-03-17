CHANGELOG
=========

すべての注記は Keep a Changelog（https://keepachangelog.com/ja/1.0.0/）に準拠しています。  
このファイルはコードベースの内容から推測して作成しています。

[0.1.0] - 2026-03-17
-------------------

Added
- パッケージ初期リリース (kabusys v0.1.0)
  - パッケージ公開情報:
    - src/kabusys/__init__.py に __version__ = "0.1.0" と __all__ = ["data", "strategy", "execution", "monitoring"] を追加。

- 環境設定管理
  - src/kabusys/config.py
    - .env ファイルおよび環境変数から設定を読み込む Settings クラスを追加。
    - 自動 .env ロード機能を実装（プロジェクトルートを .git または pyproject.toml で探索）。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化可能。
    - .env パーサーを実装（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応）。
    - 必須設定取得用の _require() 、設定値検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）を実装。
    - デフォルト設定（KABU_API_BASE_URL、DB パス等）を提供。
    - 利用想定設定項目: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH など。

- データ取得クライアント（J-Quants）
  - src/kabusys/data/jquants_client.py
    - J-Quants API クライアントを実装。
    - RateLimiter（固定間隔スロットリング）により 120 req/min のレート制限を厳守。
    - リトライロジック（指数バックオフ）を実装（最大 3 回、408/429/5xx を対象）。
    - 401 受信時は自動でリフレッシュして 1 回だけリトライ（get_id_token と連携）。
    - ページネーション対応（pagination_key を利用して自動取得）。
    - データ取得 API: fetch_daily_quotes(), fetch_financial_statements(), fetch_market_calendar() を提供。
    - DuckDB への保存用 idempotent 関数を提供: save_daily_quotes(), save_financial_statements(), save_market_calendar()。ON CONFLICT DO UPDATE を使用して冪等性を確保。
    - データ取り込み時に fetched_at（UTC）を記録し、look-ahead bias の追跡を可能に。

- ニュース収集モジュール
  - src/kabusys/data/news_collector.py
    - RSS フィードから記事収集し raw_news に保存する機能を実装。
    - セキュリティ・堅牢性設計:
      - defusedxml を利用して XML Bomb 等の攻撃を緩和。
      - SSRF 対策: リダイレクト時にスキームとホスト/IP を検証するカスタムリダイレクトハンドラを実装。HTTP/HTTPS 以外のスキーム拒否、プライベートアドレスへの接続拒否。
      - 最大受信サイズ（MAX_RESPONSE_BYTES = 10MB）を導入しメモリ DoS を防止。gzip 解凍後もサイズ検査。
      - URL 正規化時にトラッキングパラメータ（utm_*, fbclid, gclid 等）を除去。
      - 記事 ID は正規化 URL の SHA-256 ハッシュ先頭 32 文字で生成し冪等性を保証。
    - フィード処理:
      - fetch_rss(url, source, timeout) により記事のリスト（NewsArticle 型）を取得。
      - preprocess_text で URL 除去と空白正規化。
      - save_raw_news(conn, articles) はチャンク分割と単一トランザクションで INSERT ... RETURNING を利用し、実際に挿入された記事 ID を返す。
      - save_news_symbols / _save_news_symbols_bulk で記事と銘柄コードの紐付けを保存（ON CONFLICT DO NOTHING、チャンク挿入）。
      - extract_stock_codes(text, known_codes) でテキストから 4 桁銘柄コードを抽出（既知コードセットによるフィルタ、重複排除）。
      - run_news_collection で複数 RSS ソースを統合して収集・保存・銘柄紐付けを実行。各ソースは独立してエラー処理。

- DuckDB スキーマ管理
  - src/kabusys/data/schema.py
    - Raw / Processed / Feature / Execution の各レイヤーに対応するテーブル定義を実装。
    - raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance などを定義。
    - 各種制約（PRIMARY KEY, CHECK, FOREIGN KEY）やインデックス（頻出クエリ向け）を定義。
    - init_schema(db_path) で DB ファイルの親ディレクトリ自動作成と DDL 実行により初期化（冪等）。
    - get_connection(db_path) で接続を取得（スキーマ初期化は行わない）。

- ETL パイプライン
  - src/kabusys/data/pipeline.py
    - 差分更新（incremental）を行う ETL の骨組みを実装。
    - ETLResult dataclass を用いて結果・品質問題・エラーを集約。品質問題は quality モジュールの型（QualityIssue）を想定。
    - get_last_price_date / get_last_financial_date / get_last_calendar_date 等のユーティリティを実装。
    - run_prices_etl() を含む個別 ETL ジョブの実装方針（差分取得・backfill_days による再取得、デフォルト backfill_days = 3、カレンダー先読み等）を盛り込む。
    - 市場カレンダーの調整ヘルパー _adjust_to_trading_day を実装（非営業日の補正、最大 30 日遡りのロジック）。

Changed
- N/A（初回リリースのため変更履歴なし）

Fixed
- N/A（初回リリース）

Security
- ニュース収集で SSRF / XML インジェクション / Gzip bomb / 大容量レスポンスへの対策を実装。
- .env 読み込みで OS 環境変数を保護する protected 機構を導入（上書き制御）。

Notes / 注意点
- DuckDB を利用するため、動作環境に duckdb パッケージが必要。
- J-Quants API を利用するため JQUANTS_REFRESH_TOKEN が必須。refresh token から idToken を取得して API 呼び出しを行う。
- save_* 関数は ON CONFLICT による upsert を行うため基本的に冪等だが、スキーマや制約により一部レコードがスキップされる（PK 欠損等）。
- news_collector の RSS 取得は外部ネットワークアクセスを伴うため、テストでは _urlopen のモック差し替えを想定。
- pipeline.run_prices_etl の戻り値の末尾に誤り（タプルの返却が不完全）等、実装中の未完了箇所が存在する可能性がある（コードコメント・処理フローは設計に沿っているが、ユニットテストでの検証推奨）。

今後の予定（推測）
- quality モジュール（欠損・スパイク・重複検出）の実装と統合テスト。
- strategy / execution / monitoring パッケージの実装拡充（__all__ に挙げられているが現状は空）。
- pipeline の各 ETL ジョブ完成と運用監視（Slack 通知等）。
- 単体テスト・CI 設定およびドキュメント整備。

----- 

この CHANGELOG はコードベースの内容を読み取り推測して作成しています。補足や修正希望があればその点を教えてください。