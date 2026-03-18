CHANGELOG
=========

すべての注目すべき変更をこのファイルに記録します。
このプロジェクトは Keep a Changelog の慣例に従います。
安定したリリースでは SemVer を採用します。

[Unreleased]: https://example.com/kabusys/compare/v0.1.0...HEAD
[v0.1.0]: https://example.com/kabusys/releases/tag/v0.1.0

v0.1.0 - 2026-03-18
-------------------

Added
- 初回リリース: KabuSys — 日本株自動売買システムの基本モジュール群を追加。
  - パッケージエントリポイント
    - src/kabusys/__init__.py にてバージョン "0.1.0" を設定。
  - 環境設定管理 (src/kabusys/config.py)
    - .env ファイルまたは環境変数から設定を自動読み込み（プロジェクトルートを .git または pyproject.toml を基準に探索）。
    - .env/.env.local の読み込み順序と override/protected（OS環境変数保護）機能を実装。
    - 行パーサは export 形式、クォート（シングル/ダブル）、エスケープ、インラインコメント等に対応。
    - Settings クラスを公開（jquants refresh token や Kabu API 設定、Slack トークン、DB パス、環境種別検証、ログレベル検証など）。
    - 自動ロードを無効化するためのフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - 必須設定未指定時は ValueError による早期検出。

  - J-Quants クライアント (src/kabusys/data/jquants_client.py)
    - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダー取得機能を実装。
    - API レート制限対応: 固定間隔スロットリング（120 req/min、_RateLimiter）。
    - リトライロジック: 指数バックオフ、最大3回、408/429/5xx をリトライ対象に設定。429 の場合 Retry-After ヘッダを優先。
    - 401 受信時はリフレッシュトークンから id_token を自動更新して1回だけリトライ（無限再帰防止）。
    - ページネーション対応（pagination_key を用いたループ取得）。
    - DuckDB への保存関数 (save_daily_quotes, save_financial_statements, save_market_calendar) は冪等性を保つ（ON CONFLICT DO UPDATE）および fetched_at を UTC で記録。
    - 型安全な数値変換ユーティリティ（_to_float, _to_int）。float 文字列経由の int 変換に対する慎重な処理。

  - RSS ニュース収集モジュール (src/kabusys/data/news_collector.py)
    - RSS フィード取得→前処理→raw_news に冪等保存→銘柄紐付け（news_symbols）を行う統合収集ロジックを実装。
    - 記事 ID を URL 正規化（utm 等のトラッキングパラメータ削除）後の SHA-256 ハッシュ（先頭32文字）で生成し冪等性を担保。
    - defusedxml を用いた XML パース（XML Bomb 等を防止）。
    - SSRF 対策:
      - URL スキーム検証（http/https のみ許可）。
      - リダイレクト時にスキーム/ホストを検証するカスタムリダイレクトハンドラ（_SSRFBlockRedirectHandler）。
      - ホストのプライベートアドレス判定（IP 直接解析および DNS 解決による A/AAAA 検査）。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズ再検証（Gzip bomb 対策）。
    - URL 正規化、テキスト前処理（URL 除去・空白正規化）、記事抽出、pubDate の RFC2822 パースを実装。
    - DB 保存はトランザクションでまとめて行い、INSERT ... RETURNING で実際に挿入されたID/件数を返す（save_raw_news, save_news_symbols, _save_news_symbols_bulk）。
    - 銘柄コード抽出機能（4桁数字の抽出と既知銘柄セットでフィルタ）を提供。
    - run_news_collection により複数ソースを独立して処理。既知銘柄の紐付けを一括 INSERT で行う。

  - DuckDB スキーマ定義・初期化 (src/kabusys/data/schema.py)
    - DataSchema.md に沿った 3 層（Raw / Processed / Feature / Execution）スキーマを定義。
    - raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance を含む DDL を提供。
    - 代表的クエリへ向けたインデックス定義を追加。
    - init_schema(db_path) でディレクトリ作成→テーブル/インデックス作成を行い接続を返す（冪等）。get_connection 提供。

  - ETL パイプライン基盤 (src/kabusys/data/pipeline.py)
    - ETLResult dataclass により ETL 実行結果／品質問題／エラーを構造化して取得可能。
    - 差分更新ヘルパー（最終取得日の取得 get_last_price_date / get_last_financial_date / get_last_calendar_date）。
    - 営業日調整ヘルパー (_adjust_to_trading_day)（market_calendar を用いて非営業日を直近営業日に調整）。
    - run_prices_etl の差分更新ロジック（最終取得日からの backfill_days による再取得、取得→保存フロー）を追加。
    - ETL 設計方針: backfill による API の後出し修正吸収、品質チェックは致命的であっても他処理を止めない（fail-fast しない方針、quality モジュールと連携想定）。

  - その他
    - 各モジュールでロギングを活用（取得件数や警告を出力）。
    - public API として主要関数/クラスをエクスポート（settings, init_schema, get_connection 等）。

Security
- セキュリティ強化点
  - RSS パーサで defusedxml を採用し XML-related 攻撃に対処。
  - RSS フェッチで SSRF を抑止: スキーム検証、プライベートアドレス判定、リダイレクト時の検査を実装。
  - レスポンスサイズ上限（MAX_RESPONSE_BYTES）および gzip 解凍後のチェックでリソース浪費攻撃を軽減。
  - DB への直接組み込みを防ぐためプレースホルダを利用した INSERT（ただし大きなチャンクでは文字列連結で SQL を構築している箇所があるため注意）。

Notes
- 必須環境変数（Settings により参照）:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- デフォルト DB パス:
  - DuckDB: data/kabusys.duckdb （環境変数 DUCKDB_PATH で上書き可能）
  - SQLite (monitoring 用): data/monitoring.db （環境変数 SQLITE_PATH）
- 自動 .env 読み込みはプロジェクトルートが検出できない場合スキップされる。テスト等で無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- J-Quants API のレート制限・リトライ方針は jquants_client モジュール内定数で制御。
- news_collector.fetch_rss は HTTP エラー（urllib.error.URLError）を呼び出し元に伝播させる。XML パースエラー時は空リストを返す（警告ログあり）。
- DB スキーマの外部キーや CHECK 制約が多く含まれるため、外部キー制約違反や型違反に注意。

Known issues / TODO
- run_prices_etl の戻り値ドキュメントは取得数と保存数のタプルを想定しているが、実装コードの戻り値に不整合がないか（スニペット切り出しにより途中で終わっている可能性）を確認する必要があります。
- 一部の SQL はプレースホルダ数が多くなるため、非常に大きなチャンクを扱う場合に SQL の長さ制限に注意する必要があります（チャンク分割は組み込まれていますが、運用での監視を推奨）。

Footer
- 初回リリース 0.1.0。今後のリリースでバグ修正、API の安定化、品質チェック（quality モジュール）との統合、テストカバレッジ強化などを予定しています。