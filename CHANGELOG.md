Keep a Changelog に準拠した CHANGELOG.md（日本語）
※この変更履歴は提示されたコードベースの内容から推測して作成しています。

全ての注目すべき変更はここに記載します。  
フォーマットは Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に従います。

## [Unreleased]

（次回リリースのための変更をここに記載）

---

## [0.1.0] - 2026-03-17

初期リリース — KabuSys 日本株自動売買システムの骨組みを実装しました。主な追加点は以下のとおりです。

### Added
- パッケージ基礎
  - パッケージメタ情報（src/kabusys/__init__.py）を追加。バージョンは 0.1.0。
  - モジュール公開一覧: data, strategy, execution, monitoring。

- 環境設定管理（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を自動読み込み（プロジェクトルートは .git または pyproject.toml で検出）。
  - 自動ロードを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD 対応。
  - .env パーサ実装（export プレフィックス、シングル/ダブルクォート、インラインコメント処理、エスケープ処理等に対応）。
  - OS 環境変数を保護する protected キーセットによる上書き制御。
  - Settings クラスを提供し、主要な設定プロパティを定義:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト localhost）、SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - データベースパス（DUCKDB_PATH, SQLITE_PATH）
    - 環境（KABUSYS_ENV: development/paper_trading/live の検証）
    - LOG_LEVEL 検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）および is_live/is_paper/is_dev のユーティリティ

- J-Quants クライアント（src/kabusys/data/jquants_client.py）
  - API 呼び出しのための共通ライブラリを実装。
  - レート制御: 固定間隔スロットリングで 120 req/min を遵守する _RateLimiter 実装。
  - 再試行ロジック: 指数バックオフ、最大リトライ回数（3回）、対象ステータス（408, 429, 5xx）に対応。
  - 401 発生時の自動トークンリフレッシュ（1 回のみ）とモジュールレベルのトークンキャッシュ。
  - JSON デコードエラーハンドリング、タイムアウトの指定。
  - API 用関数:
    - get_id_token(refresh_token=None)
    - fetch_daily_quotes(...): ページネーション対応
    - fetch_financial_statements(...): ページネーション対応
    - fetch_market_calendar(...)
  - DuckDB への冪等保存関数（ON CONFLICT DO UPDATE）:
    - save_daily_quotes(conn, records)
    - save_financial_statements(conn, records)
    - save_market_calendar(conn, records)
  - データ整形ユーティリティ: _to_float / _to_int、取得時刻（fetched_at）を UTC ISO 形式で記録し Look-ahead バイアス対策

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードから記事を収集・前処理・DB 保存するフロー実装。
  - セキュリティ対策:
    - defusedxml を使用した XML パース（XML Bomb 対策）
    - HTTP リダイレクト時にスキーム検証およびプライベートアドレス判定を行う _SSRFBlockRedirectHandler 実装（SSRF 対策）
    - URL スキーム検証（http/https のみ許可）
    - 最大受信サイズ制限（MAX_RESPONSE_BYTES = 10 MB）および gzip 解凍後のサイズチェック（Gzip bomb 対策）
  - URL 正規化とトラッキングパラメータ除去（_normalize_url）に基づく記事 ID 生成（SHA-256 の先頭 32 文字）。
  - テキスト前処理（URL 除去、空白正規化）の実装（preprocess_text）。
  - RSS 取得関数 fetch_rss(url, source, timeout=30) を実装。非致命的エラーはログ出力してソース単位で継続。
  - DuckDB への保存:
    - save_raw_news(conn, articles): INSERT ... RETURNING を用いたチャンク単位のトランザクション保存
    - save_news_symbols(conn, news_id, codes) と内部バルク保存 _save_news_symbols_bulk
  - 銘柄コード抽出ロジック extract_stock_codes(text, known_codes)（4桁数字を候補として known_codes に基づきフィルタ）
  - 総合ジョブ run_news_collection(conn, sources=None, known_codes=None, timeout=30) を実装（各ソースを独立して処理）

- スキーマ定義と初期化（src/kabusys/data/schema.py）
  - DuckDB 用スキーマを定義（Raw / Processed / Feature / Execution 層）。
  - raw_prices, raw_financials, raw_news, raw_executions 等の Raw テーブル
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の Processed テーブル
  - features, ai_scores（Feature 層）
  - signals, signal_queue, orders, trades, positions, portfolio_performance（Execution 層）
  - 各種インデックス定義（頻出クエリを想定した index）
  - init_schema(db_path) でディレクトリ作成（必要な場合）と DDL 実行（冪等）、:memory: 対応
  - get_connection(db_path)（スキーマ初期化なしで接続を返す）

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - ETLResult dataclass による ETL 結果表現（品質問題リスト / エラーリストを含む）。
  - テーブル存在確認、最大日付取得ユーティリティ（_table_exists, _get_max_date）。
  - market_calendar を使って非営業日を直近営業日に調整する _adjust_to_trading_day。
  - 差分更新のためのヘルパ（get_last_price_date, get_last_financial_date, get_last_calendar_date）。
  - run_prices_etl の骨組み（差分取得ロジック、backfill_days デフォルト 3 日、jq.fetch_daily_quotes と jq.save_daily_quotes の呼び出し）を実装。

### Security
- XML パースに defusedxml を使用し、XML Bomb 等への耐性を強化。
- RSS フィード取得時の SSRF 対策（ホストのプライベート/ループバック判定、リダイレクト先検査）。
- レスポンスサイズ上限（MAX_RESPONSE_BYTES）と gzip 解凍後の再検査によりメモリ DoS を軽減。
- .env 読み込み時に OS 環境変数を保護し、意図しない上書きを防止。

### Fixed
- 初期実装のため該当なし。

### Known issues / Notes（既知の問題・注意事項）
- run_prices_etl の末尾が不完全（提示されたコード断片では戻り値が不完全に見える）。実運用では戻り値のタプル (fetched_count, saved_count) を正しく返すよう修正が必要です。
- 一部箇所で SQL を文字列結合している箇所がある（DDL や一括 INSERT のプレースホルダ組立等）。現在の実装はプレースホルダにより値の注入を行っているが、将来的により明示的な SQL 組立や SQA の確認を推奨します。
- news_collector のホスト名解決失敗時は安全側に通過させる設計（DNS 解決失敗は非プライベートと扱う）。ネットワーク構成によっては追加の検証が望ましい場合があります。

---

今後のリリースで予定される改善案（例）
- pipeline の完全実装（prices, financials, calendar の統合 ETL、一連の品質チェックフロー呼び出し）。
- strategy / execution / monitoring の具体実装（現在はパッケージ階層のみ定義）。
- テストカバレッジ拡充（ネットワーク操作のモック、DB マイグレーションテスト等）。
- observability（メトリクス、詳細な監査ログ、Slack 通知統合）の追加。

---

（以上）