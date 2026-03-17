# Changelog

すべての重要な変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の形式に準拠します。  

※コードベースから推測して作成した初回リリース向けの変更履歴です。

## [Unreleased]
- なし

## [0.1.0] - 2026-03-17
初回リリース（初期実装）。以下のモジュールと主要機能を含みます。

### 追加 (Added)
- パッケージ基盤
  - パッケージ名: KabuSys、バージョン 0.1.0
  - モジュール構成: data, strategy, execution, monitoring の基本パッケージ構成を定義。

- 環境設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を自動読み込み（プロジェクトルートは .git または pyproject.toml を探索して検出）。
  - 自動ロードの無効化用フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env パースの強化:
    - export KEY=val 形式対応
    - シングル/ダブルクォート内のエスケープ処理対応
    - コメント（#）の考慮ルール
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パスなどの設定値をプロパティとして取得可能。
  - 環境変数検証（KABUSYS_ENV, LOG_LEVEL 等）と便利なブールプロパティ（is_live, is_paper, is_dev）。

- J-Quants API クライアント (kabusys.data.jquants_client)
  - 基本的な API 呼び出しラッパーと認証関係の機能を実装。
  - レート制限（120 req/min）を守る固定間隔スロットリング実装（_RateLimiter）。
  - リトライロジック（指数バックオフ、最大3回、408/429/5xx 対象）、429 の場合は Retry-After を優先。
  - 401 受信時は refresh token による id_token の自動リフレッシュを 1 回行って再試行する処理を実装。
  - API ページネーション対応（pagination_key）、ページネーション間で使用する id_token のモジュールキャッシュを実装。
  - データ取得関数:
    - fetch_daily_quotes（株価日足／OHLCV）
    - fetch_financial_statements（四半期財務データ）
    - fetch_market_calendar（JPX マーケットカレンダー）
  - DuckDB へ冪等に保存する save_* 関数を提供（ON CONFLICT DO UPDATE を利用）:
    - save_daily_quotes, save_financial_statements, save_market_calendar
  - 型変換ユーティリティ _to_float / _to_int を実装し、不正値の扱いを明示。

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードからの記事収集・正規化・DB保存フローを実装。
  - 設計上の特徴:
    - 記事ID は正規化 URL の SHA-256（先頭32文字）で生成し冪等性を保証（utm_* 等のトラッキングパラメータ削除後に正規化）。
    - defusedxml を使った安全な XML パース。
    - HTTP レスポンスの最大読み取りバイト数制限（MAX_RESPONSE_BYTES = 10MB）を導入しメモリDoSを緩和。
    - gzip 圧縮レスポンスの解凍と解凍後サイズ検査（Gzip bomb 対策）。
    - リダイレクトや最終 URL に対するスキーム／ホスト検証を実施（SSRF 対策）。
    - RSS の pubDate をパースして UTC に正規化（パース失敗時は警告を出して現在時刻で代替）。
  - 機能:
    - fetch_rss: RSS 取得と記事整形（title, content, datetime, url, id）を返却。
    - preprocess_text: URL 除去、空白正規化等の前処理。
    - extract_stock_codes: テキストから 4 桁銘柄コードを抽出（known_codes による検証）。
    - save_raw_news: DuckDB の raw_news テーブルへチャンク INSERT（ON CONFLICT DO NOTHING）を行い、実際に挿入された記事IDを返却（トランザクションまとめ）。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括保存（INSERT ... RETURNING を利用し正確な挿入数を取得）。
    - DEFAULT_RSS_SOURCES に既定の RSS ソースを定義（例: Yahoo Finance のビジネス RSS）。

- スキーマ定義 (kabusys.data.schema)
  - DuckDB 用スキーマを定義し、Raw / Processed / Feature / Execution の各レイヤーを網羅するテーブル DDL を実装。
  - raw_prices, raw_financials, raw_news, raw_executions を含む Raw レイヤー。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の Processed レイヤー。
  - features, ai_scores 等の Feature レイヤー。
  - signals, signal_queue, orders, trades, positions, portfolio_performance 等の Execution レイヤー。
  - パフォーマンスを考慮したインデックス群を定義。
  - init_schema(db_path) 関数でディレクトリ自動作成と DDL 実行、get_connection() で既存 DB への接続を提供。

- ETL パイプライン (kabusys.data.pipeline)
  - 差分更新（incremental）を意識した ETL ヘルパー群を実装。
  - ETLResult データクラスで実行結果・品質問題・エラーを集約。
  - DB 上の最終取得日を取得するユーティリティ（get_last_price_date, get_last_financial_date, get_last_calendar_date）。
  - 取引日調整ヘルパー _adjust_to_trading_day（market_calendar を利用）。
  - run_prices_etl: 差分算出（backfill_days を用いた再取得）→ jq.fetch_daily_quotes → jq.save_daily_quotes の流れを実装（差分ETLの基本実装）。

- テスト性・拡張性
  - _urlopen を差し替え可能にして fetch_rss のテスト容易性を確保。
  - fetch_* 関数は id_token を外部注入可能（テスト用に認証を注入可能）。

### セキュリティ (Security)
- RSS パーサに defusedxml を採用して XML External Entity（XXE）や XML Bomb 等の脆弱性を緩和。
- RSS 取得時の SSRF 防止:
  - URL スキーム検証（http/https のみ許可）。
  - ホストがプライベート / ループバック / リンクローカル の場合は拒否（DNS で A/AAAA を解決して検査）。
  - リダイレクト時にも同様の検証を実行するカスタムリダイレクトハンドラを導入。
- レスポンスサイズ・gzip 解凍後サイズの上限を導入してメモリ爆発を防止。

### 修正・品質 (Fixed / Improved)
- DB 保存の冪等性を重視（raw_* 保存で ON CONFLICT を使用し既存レコードは更新またはスキップ）。
- news_collector のバルク INSERT はチャンク化・トランザクションで処理し、DB オーバーヘッドを抑制。
- jquants_client の HTTP エラー処理を強化（Retry-After の優先、ネットワークエラーの再試行、ログ出力の強化）。
- .env パーサの堅牢化（空行・コメント・引用符付き値・エスケープ処理などの網羅）。

### 既知の注意点 / 制約 (Notes)
- DuckDB をストレージとして利用する設計のため、実稼働ではファイルパスやバックアップ運用方針の検討が必要。
- ETL 内の品質チェック（quality モジュール）と連携する設計になっているが、quality モジュール自体の実装詳細は本リリースで依存する想定。
- API クライアントではスレッド/プロセス間の id_token キャッシュの共有は行っておらず、マルチプロセス環境は運用設計が必要。
- run_news_collection / run_prices_etl 等はネットワーク・DB 操作を行うため、運用時は適切な監視とリトライポリシー、環境変数の管理を推奨。

---

(以降のバージョンでは、追加機能・バグ修正・互換性の変更などをこのファイルに記録してください。)