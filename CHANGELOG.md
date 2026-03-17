KEEP A CHANGELOG
=================

すべての変更は Keep a Changelog のフォーマットに従って記載します。
このファイルは人間に読みやすく、変更履歴の管理・リリースノート作成に利用します。

フォーマット
-----------
- 変更は "Unreleased" と各リリース（バージョン）ごとに区分しています。
- 日付は YYYY-MM-DD 形式です。

Unreleased
----------
- 既知の問題 / TODO
  - run_prices_etl の戻り値の実装が途中（return 文が不完全）になっており、呼び出し側が想定するタプル (fetched, saved) を返していないため修正が必要です。
  - package 内の一部サブパッケージ（strategy, execution, data の __init__.py）が空のまま。将来的な API エクスポート整理やドキュメント追記が推奨されます。
  - 単体テスト・統合テストのカバレッジを追加して、HTTP エラーや DB トランザクションの異常系を網羅することを推奨。

0.1.0 - 2026-03-17
------------------
Added
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージメタ情報
    - src/kabusys/__init__.py にて __version__ = "0.1.0" を設定、主要サブモジュールを __all__ で公開。

- 環境設定管理
  - src/kabusys/config.py
    - .env ファイルおよび環境変数から設定値を読み込む Settings クラスを実装。
    - 自動 .env ロード機能（プロジェクトルートの検出: .git または pyproject.toml を基準）。
    - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD に対応。
    - .env パーサ実装: export プレフィックス、クォート／エスケープ、インラインコメント処理、保護キー（OS環境変数を上書き禁止）に対応。
    - 必須設定取得のヘルパー _require と環境値検証（KABUSYS_ENV, LOG_LEVEL の許容値検査）。
    - 代表的な設定プロパティ:
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
      - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
      - DUCKDB_PATH, SQLITE_PATH
      - env / is_live / is_paper / is_dev / log_level

- データ取得クライアント（J-Quants）
  - src/kabusys/data/jquants_client.py
    - J-Quants API クライアントを実装。取得対象: 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダー。
    - レート制御: 固定間隔スロットリングで 120 req/min を尊重する RateLimiter を実装。
    - 再試行ロジック: 指数バックオフ（最大 3 回）、HTTP 408/429/5xx に対する再試行。
    - 401 応答時の自動トークンリフレッシュ（1 回のみ試行）を実装。ID トークンはモジュールレベルでキャッシュ。
    - ページネーション対応で fetch_* 系関数（fetch_daily_quotes, fetch_financial_statements）を実装。
    - DuckDB へ冪等保存する save_* 関数を実装（ON CONFLICT DO UPDATE を使用）。
    - 値変換ユーティリティ (_to_float, _to_int) を実装し、入力の堅牢性を高める。
    - デザイン方針/注記:
      - fetched_at を UTC で記録し、Look-ahead bias の追跡を可能に。
      - DuckDB への挿入は主キー重複時に更新することで冪等性を担保。

- ニュース収集モジュール
  - src/kabusys/data/news_collector.py
    - RSS フィードから記事を収集し raw_news テーブルへ保存する一連の機能を実装。
    - セキュリティと堅牢性に配慮:
      - defusedxml を用いた XML パース（XML Bomb 等の対策）。
      - SSRF 対策: URL スキーム検証（http/https 限定）、リダイレクト先検査、プライベートアドレス拒否（IP/ホスト名の判定）。
      - レスポンス最大サイズ制限（MAX_RESPONSE_BYTES=10MB）および gzip 解凍後のサイズ検証（Gzip bomb 対策）。
    - URL 正規化: トラッキングパラメータ（utm_* など）除去、クエリソート、フラグメント削除。
    - 記事IDは正規化 URL の SHA-256 ハッシュ（先頭32文字）で生成し冪等性を担保。
    - RSS 取得処理（fetch_rss）: content:encoded を優先、pubDate パース、title/content の前処理（URL除去・空白正規化）。
    - DuckDB への保存:
      - save_raw_news: INSERT ... RETURNING id を用い、新規挿入された記事IDを正確に返す。
      - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括挿入（ON CONFLICT DO NOTHING とRETURNINGで正確な件数を取得）。
    - 銘柄抽出ユーティリティ extract_stock_codes（4桁数字の日本株コードを既知リストと照合）。

- データベーススキーマ定義（DuckDB）
  - src/kabusys/data/schema.py
    - DataSchema に基づく DuckDB の DDL を定義し、init_schema(db_path) で初期化可能。
    - 3 層（Raw / Processed / Feature）＋ Execution 層のテーブルを定義:
      - Raw: raw_prices, raw_financials, raw_news, raw_executions
      - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
      - Feature: features, ai_scores
      - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
    - 各種 CHECK 制約・PRIMARY KEY・FOREIGN KEY を付与してデータ整合性を担保。
    - 頻出クエリ用のインデックスを作成（例: idx_prices_daily_code_date, idx_signal_queue_status 等）。
    - get_connection(db_path) を用いて既存 DB に接続可能。

- ETL パイプライン（部分実装）
  - src/kabusys/data/pipeline.py
    - ETL の設計（差分更新、backfill、品質チェックの取り扱い）と補助機能を実装。
    - ETLResult データクラスを導入し、実行結果・品質問題・エラー情報を集約可能に。
    - 差分更新ヘルパー: テーブル存在チェック、最大日付取得のユーティリティ（_get_max_date, get_last_price_date 等）。
    - 市場カレンダー補助: _adjust_to_trading_day（非営業日の調整）実装。
    - run_prices_etl の骨組みを実装（最終取得日からの差分取得、backfill サポート、jq.fetch_daily_quotes と jq.save_daily_quotes を利用して取得→保存を実行）。
    - 注意: run_prices_etl の戻り値実装が途中のため、呼び出し側での利用前に修正が必要（Unreleased に記載）。

Security
- 複数箇所でセキュリティ対策を導入:
  - RSS パーサは defusedxml を使用。
  - RSS フェッチでの SSRF 対策（スキーム検証、プライベートIP/ホストの拒否、リダイレクト検査）。
  - 外部データ取り込み時にサイズ制限や gzip 解凍後の検査を実施。
  - 環境変数読み込みで OS 環境変数を保護する仕組みを提供。

Notes / 使用上の注意
- DB 初期化:
  - 初回は schema.init_schema(db_path) を実行してテーブルを作成してください。
  - 既存 DB に接続する場合は schema.get_connection(db_path) を使用し、init_schema は不要です。
- 環境変数の自動ロード:
  - パッケージはプロジェクトルート（.git または pyproject.toml）を検出して .env / .env.local を自動読み込みします。テスト時などに自動ロードを停止するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants のレート制限や認証に関する挙動:
  - 120 req/min のレート制御、リトライ、401 時のリフレッシュを組み込んでいます。
  - テスト時の id_token 注入や強制リフレッシュは設計上可能です（関数引数で id_token を渡せます）。

貢献
- バグ報告、改善提案、テスト追加は歓迎します。Unreleased に記載した既知の問題（特に run_prices_etl の戻り値修正）を優先して対応してください。

ライセンス
- 本リポジトリに含まれるソースコードのライセンス表記はリポジトリ本体（LICENSE 等）を参照してください。