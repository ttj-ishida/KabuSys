# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠します。  
安定版のリリースが行われるまではこのファイルを更新してください。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

- （なし）

## [0.1.0] - 2026-03-17

初回リリース。日本株自動売買プラットフォームのコアモジュール群を追加。

### 追加したもの

- パッケージ初期化
  - kabusys パッケージを追加。__version__ = "0.1.0"。

- 設定 / 環境変数管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む自動ロード実装（優先度: OS 環境 > .env.local > .env）。
  - プロジェクトルート探索を __file__ から行い、.git または pyproject.toml を基準にルートを特定。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env パーサ: export プレフィックス、クォート、エスケープ、インラインコメントを考慮した堅牢なパース実装。
  - 必須環境変数取得ヘルパー（未設定時は ValueError）。
  - 設定項目:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN（必須）
    - SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
  - Settings クラス経由のプロパティアクセスを提供（settings オブジェクト）。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - API 呼び出しユーティリティを実装（_request）。
  - レート制御: 固定間隔スロットリング（120 req/min）による RateLimiter 実装。
  - 冪等性を考慮したデータ保存用ユーティリティ（DuckDB への save_* 関数）。
  - リトライロジック: 指数バックオフ、最大試行回数 3 回、408/429/5xx をリトライ対象に含む。429 の場合は Retry-After を優先。
  - 401 発生時の自動トークンリフレッシュを 1 回のみ許容（get_id_token と連携して再取得）。
  - ページネーション対応（pagination_key を用いた取得ループ）。
  - データ取得関数:
    - fetch_daily_quotes: 株価日足（OHLCV）
    - fetch_financial_statements: 四半期財務データ
    - fetch_market_calendar: JPX マーケットカレンダー
  - DuckDB への保存関数:
    - save_daily_quotes（raw_prices、ON CONFLICT DO UPDATE）
    - save_financial_statements（raw_financials、ON CONFLICT DO UPDATE）
    - save_market_calendar（market_calendar、ON CONFLICT DO UPDATE）
  - データ型変換ユーティリティ: _to_float, _to_int（不正値は None に安全変換）。
  - モジュールレベルの ID トークンキャッシュを保持し、ページネーション間で共有。

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィードから記事を収集し raw_news テーブルへ保存する処理を実装。
  - 設計上の特徴:
    - 記事 ID は正規化 URL の SHA-256（先頭32文字）で生成して冪等性を確保。
    - defusedxml を用いた XML パース（XML Bomb などへの防御）。
    - SSRF 対策:
      - URL スキーム検証（http/https のみ許可）
      - リダイレクト時にスキーム・ホストを検査するカスタムリダイレクトハンドラ（_SSRFBlockRedirectHandler）
      - ホスト名を DNS 解決してプライベート/ループバック/リンクローカル/マルチキャストを検出し拒否
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10 MB）および gzip 解凍後のサイズ検査（Gzip bomb 対策）
    - トラッキングパラメータ削除・URL 正規化（utm_ 等を除去）
    - テキスト前処理（URL除去・空白正規化）
    - DB 保存はチャンク化してトランザクションでまとめ、INSERT ... RETURNING を用いて実際に挿入された ID/件数を返す
    - 銘柄コード抽出ロジック（4桁数字パターン + known_codes によるフィルタ）
  - 公開 API:
    - fetch_rss(url, source, timeout)
    - save_raw_news(conn, articles) -> 新規挿入された記事 ID のリスト
    - save_news_symbols(conn, news_id, codes) -> 新規挿入件数
    - run_news_collection(conn, sources=None, known_codes=None, timeout=30) -> ソース毎の新規保存件数

- DuckDB スキーマ定義 / 初期化（kabusys.data.schema）
  - DataSchema.md に基づく多層スキーマを実装（Raw / Processed / Feature / Execution）。
  - 主要テーブル（例）:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに制約（PRIMARY KEY、CHECK 等）を定義し整合性を担保。
  - 頻出検索向けインデックスを作成（例: idx_prices_daily_code_date 等）。
  - init_schema(db_path) でファイル作成（親ディレクトリ自動生成）とテーブル初期化（冪等）を行い、DuckDB 接続を返す。
  - get_connection(db_path) で既存 DB への接続を返す（スキーマ初期化は行わない）。

- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新を行う ETL ジョブの骨格を実装。
  - 設計/機能:
    - 差分更新ロジック: DB 上の最終取得日から未取得分を算出して差分取得。初回は最小日付（2017-01-01）から取得。
    - backfill_days による再取得（デフォルト 3 日）で API の後出し修正を吸収。
    - 市場カレンダー先読み（デフォルト 90 日）。
    - 品質チェックとエラー集約（quality モジュールとの連携想定）。
    - ETL 結果を示す ETLResult データクラスを追加（品質問題・エラー・取得/保存件数を保持）。
    - テスト容易性のため id_token を注入可能。
  - ヘルパー:
    - テーブル存在チェック、最大日付取得、営業日調整（非営業日の補正）など。

### 変更点（設計/実装に関する注意）

- データ保存は可能な限り冪等性を確保（ON CONFLICT DO UPDATE / DO NOTHING）しているため、再実行に対して安全。
- ネットワーク呼び出しにはリトライ・レート制御を組み合わせており、429 の Retry-After ヘッダに対応。
- ニュース収集ではセキュリティ対策（SSRF / XML Bomb / Gzip bomb / レスポンスサイズ制限）を重視。
- DuckDB の SQL 実行においては動的 SQL（プレースホルダ組立）を利用している箇所があるため、引数は内部で適切に平坦化して渡す設計。
- 一部の挙動（例: _urlopen の差し替え、id_token の注入）はテスト用にモック可能に実装。

### 既知の制約・注意点

- 外部依存:
  - duckdb, defusedxml などが必要。
- Settings の必須環境変数が未設定の場合は ValueError を送出するため、実行前に .env または OS 環境で設定が必要。
- schema.init_schema を実行して初期化を行う必要がある（get_connection はスキーマ初期化を行わない）。
- pipeline.run_prices_etl の末尾がこのリリース差分ソースでは未完/途中で終わっているように見える（コードベースからは取得数のみを返す処理の継続が想定される）。（注: 実装の続き/完全化は今後の作業予定）

### セキュリティ

- ニュース収集モジュールで SSRF 対策、XML の安全パーシング、レスポンスサイズ制限を導入。
- API クライアントはトークンの自動リフレッシュ時に無限再帰しないよう設計。

---

今後の予定（例）:
- ETL pipeline の完成（品質チェック連携の詳細実装）。
- execution / strategy モジュールの実装（注文発行・約定管理・戦略実行）。
- 単体テスト・統合テストの追加、CI 設定。
- ドキュメント（DataPlatform.md / API 仕様書）の整備。