# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記録します。  
フォーマットの詳細: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

## [0.1.0] - 2026-03-17
初回リリース（初期実装）。日本株自動売買プラットフォームの基礎機能を実装しました。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージ初期実装。バージョン: 0.1.0。
  - パッケージ公開 API: data, strategy, execution, monitoring を __all__ としてエクスポート。

- 設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を自動読み込みする仕組みを実装。
    - 読み込み優先順位: OS 環境 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードの無効化が可能（テスト用途）。
  - robust な .env パーサー実装:
    - コメント行、export プレフィックス、クォート内のエスケープ処理、インラインコメント処理に対応。
    - ファイル読み込み失敗時の警告出力。
    - 既存 OS 環境変数を保護する protected オプション。
  - Settings クラスを提供し、主要設定をプロパティ経由で取得:
    - J-Quants / kabuステーション / Slack / DB パスなどの必須/任意設定を提供。
    - KABUSYS_ENV / LOG_LEVEL の値検証（許可された値のみ受け入れ）。
    - is_live / is_paper / is_dev のヘルパーメソッド。

- J-Quants クライアント (kabusys.data.jquants_client)
  - API 呼び出しユーティリティを実装:
    - レート制限: 固定間隔スロットリングで 120 req/min を厳守する RateLimiter を導入。
    - リトライロジック: 指数バックオフ、最大 3 回、408/429/5xx に対する再試行。
    - 401 受信時の自動トークンリフレッシュ（1 回のみ）とトークンキャッシュ（モジュールレベル）。
    - JSON デコードエラーの検出と明示的なエラーメッセージ。
  - API データ取得関数:
    - fetch_daily_quotes（株価日足、ページネーション対応）
    - fetch_financial_statements（四半期財務、ページネーション対応）
    - fetch_market_calendar（JPX カレンダー）
  - DuckDB への冪等保存関数:
    - save_daily_quotes / save_financial_statements / save_market_calendar
    - ON CONFLICT DO UPDATE を用いた重複排除・更新ロジック
    - fetched_at（UTC）を記録し、いつそのデータを知り得たかをトレース可能に

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィード取得と記事格納ワークフローを実装:
    - fetch_rss: RSS 取得、XML パース（defusedxml 利用）、記事整形、記事 ID（正規化 URL の SHA-256 先頭32文字）生成
    - preprocess_text: URL 除去、空白正規化
    - URL 正規化: トラッキングパラメータ除去（utm_*, fbclid 等）、クエリソート、フラグメント削除
    - SSRF 対策:
      - リダイレクト検査用ハンドラでスキーム/プライベートホストをブロック
      - ホストがプライベート/ループバック/リンクローカル/マルチキャストの場合アクセスを拒否
    - 応答サイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズ検査（Gzip bomb 防止）
    - DB 保存:
      - save_raw_news: チャンク化したバルク INSERT をトランザクションで実行、INSERT ... RETURNING で実際に挿入された記事 ID を返す
      - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けをバルク保存（ON CONFLICT DO NOTHING、挿入数を正確に返す）
    - 銘柄コード抽出: 4桁数値パターンから known_codes に基づく抽出（重複除去）
    - run_news_collection: 複数 RSS ソースを独立処理で収集し DB 保存、known_codes が与えられた場合は銘柄紐付けも実行

- DuckDB スキーマ (kabusys.data.schema)
  - DataSchema に基づくテーブル定義を追加（Raw / Processed / Feature / Execution 層）
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種制約（PRIMARY KEY / CHECK / FOREIGN KEY）および頻出クエリ向けのインデックスを定義
  - init_schema(db_path) でディレクトリ作成→全 DDL 実行→接続返却（冪等）
  - get_connection(db_path) を提供（スキーマ初期化は行わない）

- ETL パイプライン (kabusys.data.pipeline)
  - ETLResult dataclass による処理結果の集約（品質検査結果・エラー一覧を含む）
  - 差分取得ユーティリティ:
    - _table_exists / _get_max_date / get_last_price_date / get_last_financial_date / get_last_calendar_date
  - 市場カレンダー補助: _adjust_to_trading_day（非営業日を直近営業日に調整）
  - run_prices_etl（差分 ETL 実装）:
    - 最終取得日からの差分取得、自動バックフィル（デフォルト backfill_days=3）対応
    - jq.fetch_daily_quotes → jq.save_daily_quotes を呼び出し、取得数・保存数を返す
  - 設計上、id_token の注入やテスト用のフック（例: news_collector._urlopen のモック差替え）を考慮

### 変更 (Changed)
- 初版のため過去バージョンからの変更はありません（新規実装）。

### 修正 (Fixed)
- 初版のため既知のバグ修正履歴はありません。

### セキュリティ (Security)
- news_collector にて以下の対策を導入:
  - defusedxml を用いた XML パース（XML ボム／実行攻撃防止）
  - SSRF 対策: リダイレクト先スキーム検査、プライベートアドレス検査、初回ホスト検査
  - 応答サイズ上限と gzip 解凍後サイズ検査による DoS（メモリ）対策
- jquants_client の HTTP リクエストでタイムアウトやリトライを実装し、外部 API 呼び出しでの不安定さを軽減

### パフォーマンス (Performance)
- API レート制御（120 req/min）により J-Quants のレート制限に準拠
- DB バルク挿入のチャンク化（_INSERT_CHUNK_SIZE）とトランザクション集約により挿入コストを低減
- DuckDB のインデックス定義により頻出クエリの高速化を想定

### 既知の問題 / 注意事項 (Known issues / Notes)
- strategy および execution パッケージの __init__.py は空で、具体的戦略や発注ロジックはまだ実装されていません（初期骨格のみ）。
- quality モジュールは参照されているが（pipeline 内）、ここに含まれる具体的チェックの実装は別モジュールまたは将来のコミットでの追加を想定しています。
- run_prices_etl 等の ETL 処理は差分取得・バックフィル・品質チェック連携の設計を備えていますが、運用状況に合わせた追加の検証・監視が必要です。
- J-Quants API トークンや kabu ステーション API のパスワード等は環境変数に依存します。適切な .env や環境変数の設定が必須です。

---

（この CHANGELOG はコードベースの内容から推測して作成しています。実際のリリースノートとして使用する場合は、必要に応じて運用上の追加情報・依存関係・インストール/マイグレーション手順を追記してください。）