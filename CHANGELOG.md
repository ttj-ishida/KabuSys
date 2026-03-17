# Changelog

すべての重要な変更点は Keep a Changelog の形式に従って記載しています。  
このプロジェクトの初回公開バージョンは 0.1.0 です。

## [0.1.0] - 2026-03-17

### 追加 (Added)
- 初期パッケージを追加。パッケージ名: kabusys
  - パッケージエントリポイント src/kabusys/__init__.py にバージョンおよび公開モジュール定義を追加。

- 環境設定管理
  - src/kabusys/config.py を追加。
  - .env / .env.local の自動ロード機構を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。環境変数の読み込み優先順位は OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD を使って自動ロードを無効化可能。
  - .env 行パーサを実装（export プレフィックス、クォート、インラインコメントの処理に対応）。
  - Settings クラスを提供し、J-Quants トークン、kabu API パスワード、Slack トークン・チャンネル、DB パス、実行環境（development/paper_trading/live）やログレベル検証などのプロパティを公開。環境変数未設定時の明確なエラーメッセージを提供。

- J-Quants API クライアント
  - src/kabusys/data/jquants_client.py を追加。
  - 株価日足（OHLCV）、四半期財務データ、JPX マーケットカレンダーを取得する fetch_* 関数を実装（ページネーション対応）。
  - API レート制限（120 req/min）を守る固定間隔スロットリング (_RateLimiter) を実装。
  - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx を再試行）を実装。429 時は Retry-After ヘッダ優先。
  - 401 Unauthorized 受信時の自動トークンリフレッシュ処理を実装（リフレッシュは 1 回限定）。
  - データ取得時に fetched_at（UTC）を付与して「いつデータが利用可能になったか」を記録（Look-ahead Bias 対策）。
  - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。ON CONFLICT DO UPDATE により冪等性を担保。
  - 型変換ユーティリティ（_to_float, _to_int）を実装して不正データや空値を安全に扱う。

- ニュース収集モジュール
  - src/kabusys/data/news_collector.py を追加。
  - RSS フィード取得・パース・正規化・DB 保存までの ETL を実装（fetch_rss, save_raw_news, save_news_symbols, run_news_collection）。
  - defusedxml を使った安全な XML パース（XML Bomb 対策）。
  - URL 正規化処理（トラッキングパラメータ除去、フラグメント除去、クエリソート）および記事ID（正規化 URL の SHA-256 先頭32文字）生成を実装し、冪等性を確保。
  - SSRF 対策:
    - リダイレクト先のスキーム検証・プライベート IP 検査を行う _SSRFBlockRedirectHandler を実装。
    - URL スキームは http/https のみ許可。リダイレクト後の最終 URL も再検証。
    - ホストがプライベート/ループバック等の場合はスキップ。
  - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）、gzip 解凍後のサイズ再チェックを実装（メモリ DoS / Gzip bomb 対策）。
  - RSS の pubDate パース関数（タイムゾーンを UTC に正規化）を実装。
  - テキスト前処理（URL 除去、空白正規化）を実装。
  - 銘柄コード抽出（4桁数字パターン）機能と、既知コードセットに基づくフィルタリングを実装。
  - DuckDB へのバルク挿入はチャンク処理、トランザクション、INSERT ... RETURNING を用い、実際に挿入された行だけを返す設計。

- DuckDB スキーマ
  - src/kabusys/data/schema.py を追加。
  - Raw / Processed / Feature / Execution の 3 層（+実行レイヤ）に対応したテーブル定義を実装。
  - raw_prices, raw_financials, raw_news, raw_executions 等の Raw テーブルを定義。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の Processed テーブルを定義。
  - features, ai_scores 等の Feature テーブルを定義。
  - signals, signal_queue, orders, trades, positions, portfolio_performance 等の Execution テーブルを定義。
  - 頻出クエリ向けのインデックスを追加。
  - init_schema(db_path) によりディレクトリ自動作成（必要時）と全 DDL の実行で初期化を行い、get_connection() で既存 DB へ接続できる API を提供。

- ETL パイプライン
  - src/kabusys/data/pipeline.py を追加（ETL の骨格）。
  - 差分更新の考え方（最終取得日からの差分再取得、backfill_days による後出し修正の吸収）を実装。
  - 市場カレンダー先読み、取得範囲の自動算出、品質チェック（quality モジュールとの連携を想定）などを設計。
  - ETLResult データクラスを実装し、取得数・保存数・品質問題・エラーの集約と to_dict 出力を提供。
  - テーブル存在チェック、最大日付取得ヘルパー、営業日調整ロジックを実装。
  - run_prices_etl の差分取得ロジックと jquants_client との連携を実装（取得→保存→ログ）。

- 空のパッケージモジュール（プレースホルダ）
  - src/kabusys/execution/__init__.py, src/kabusys/strategy/__init__.py, src/kabusys/data/__init__.py を追加（将来の実装用プレースホルダ）。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- RSS パーサに defusedxml を利用し XML 関連の脆弱性を低減。
- ニュース取得時に SSRF 対策（リダイレクト検査・プライベートアドレスブロック）を実装。
- .env 読み込み時に OS 環境変数を保護する protected 機構を実装（.env.local の override 動作含む）。

### 既知の制約 / 注意点 (Known issues / Notes)
- schema.init_schema は初回に DB の親ディレクトリを自動作成するため、永続化先パスの権限に注意してください。
- run_news_collection の銘柄紐付けは known_codes を渡さない場合はスキップされます。known_codes は外部でメンテナンスしてください。
- jquants_client の HTTP 実行は urllib を直接使っているため、アプリケーションのリトライ / タイムアウト要件に応じて監視・調整を行ってください。
- quality モジュールは pipeline で参照する設計になっていますが、本リリースに含まれていない場合は品質チェックは無効化されます（pipeline 側はエラーを収集して継続する設計）。

---

初回リリース（0.1.0）では、データ取得・保存・初期スキーマ・ニュース収集・環境管理・ETL の基盤を整備しました。今後は戦略（strategy）、発注実行（execution）、監視（monitoring）等のモジュール実装と、品質チェック・自動化ジョブの追加を予定しています。