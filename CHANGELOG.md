# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠しています（日本語で記載）。

## [0.1.0] - 2026-03-17

初回リリース。日本株自動売買システム「KabuSys」の基本コンポーネントを実装しました。

### 追加 (Added)
- パッケージのメタ情報
  - kabusys パッケージ初期化。__version__ = 0.1.0、公開モジュール一覧を定義 (data, strategy, execution, monitoring)。 (src/kabusys/__init__.py)

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを実装。
  - 自動 .env ロード機能をプロジェクトルート（.git または pyproject.toml）から実行。
  - 自動ロードを無効化するためのフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト用）。
  - .env パーサーは export プレフィックス対応、クォートとエスケープ処理、インラインコメント処理を実装。
  - 必須環境変数取得用の _require と、J-Quants / kabu / Slack / DB 関連設定プロパティを提供。
  - KABUSYS_ENV と LOG_LEVEL の値検証（許容値チェック）を実装。

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - 日足（OHLCV）、財務データ（四半期 BS/PL）、マーケットカレンダーを取得する fetch_* 関数を実装。
  - API レート制御のための固定間隔スロットリング _RateLimiter（120 req/min デフォルト）を導入。
  - リトライロジック（指数バックオフ、最大 3 回）を実装。408/429/5xx を再試行対象に設定。
  - 401 発生時のトークン自動リフレッシュ（1回のみ）を実装。トークン取得は get_id_token。
  - ページネーション対応（pagination_key を用いてループ取得）。
  - DuckDB へ冪等に保存する save_* 関数を実装（ON CONFLICT DO UPDATE を利用）。
  - データ取得時間を UTC の fetched_at として記録し、Look-ahead Bias を防止する考慮を追加。
  - 型変換ユーティリティ (_to_float / _to_int) を実装し、空値・不正値に安全に対処。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードからニュース記事を収集し raw_news へ保存する機能を実装。
  - デフォルト RSS ソースに Yahoo Finance を登録。
  - セキュリティ対策・堅牢性:
    - defusedxml を使用して XML Bomb 等の攻撃を防止。
    - SSRF 対策：URL スキーム検証、ホストがプライベート/ループバックでないことを検査、リダイレクト時も検証する _SSRFBlockRedirectHandler。
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）をチェックし、Gzip 解凍後もサイズ検査。
    - 記事 URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント除去、クエリソート）。
    - 記事 ID を正規化 URL の SHA-256（先頭32文字）で生成し冪等性を確保。
    - URL のスキームは http/https のみ許可。
  - テキスト前処理（URL 除去・空白正規化）を実装。
  - DuckDB への保存はチャンク化とトランザクションでまとめて行い、INSERT ... RETURNING を使って実際に挿入された件数/ID を返す。
  - 銘柄コード抽出機能（4桁数字パターン）と news_symbols テーブルへの一括保存機能を提供。
  - _urlopen をエントリポイントとしてモック可能にしテストしやすく設計。

- DuckDB スキーマ定義と初期化 (src/kabusys/data/schema.py)
  - Raw / Processed / Feature / Execution レイヤーを含む包括的なテーブル定義を追加。
  - raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance 等のDDLを実装。
  - 各テーブルに適切な制約 (PRIMARY KEY, CHECK, FOREIGN KEY) を設定してデータ整合性を担保。
  - 頻出クエリ向けのインデックス群を追加。
  - init_schema(db_path) によりディレクトリ作成、DDL/インデックス作成をまとめて実行する初期化APIを提供。
  - get_connection(db_path) で既存 DB へ接続するユーティリティを実装。

- ETL パイプライン基盤 (src/kabusys/data/pipeline.py)
  - 差分更新を想定した ETL ロジックの土台を実装（差分取得、backfill 支援、品質チェックのためのフック）。
  - ETLResult データクラスを導入し、取得件数・保存件数・品質問題・エラー情報を集約して返す設計。
  - DB の最終取得日取得ユーティリティ (get_last_price_date, get_last_financial_date, get_last_calendar_date) を実装。
  - 市場カレンダーを参照して非営業日を直近営業日に調整する _adjust_to_trading_day を提供。
  - run_prices_etl を実装（差分算出、fetch_daily_quotes 呼び出し、save_daily_quotes 呼び出し）。backfill_days による再取得対応。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- ニュース取得で XML パーサに defusedxml を使用し、XML に関する脆弱性を緩和。
- RSS フェッチ時の SSRF 対策を導入（スキーム検証、プライベートアドレス拒否、リダイレクト時検査）。
- HTTP レスポンスサイズと gzip 解凍後のサイズ上限チェックで DoS リスクを低減。

### パフォーマンス (Performance)
- J-Quants API 呼び出しのレート制御（固定間隔スロットリング）を実装し、API レート制限順守を容易化。
- DuckDB へのバルク挿入をチャンク化してトランザクションでまとめ、オーバーヘッドを削減。
- news_symbols / raw_news の一括 INSERT に RETURNING を活用して実効挿入数を正確に把握。

### 開発者向け注記 (Notes for developers)
- 環境変数の自動ロードはパッケージ内からプロジェクトルートを探索して行うため、パッケージ配布後も想定通りに動作するよう考慮しています。必要な場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- jquants_client の HTTP 呼び出しは urllib を直接使っています。テストやモックが必要な場合は _get_cached_token / _rate_limiter / _request の振る舞いを差し替えてください。
- news_collector のネットワーク部分（_urlopen）はテストでモック可能です。
- DuckDB スキーマは冪等（CREATE IF NOT EXISTS）なので既存 DB に安全に初期化できます。
- 日付・数値変換のユーティリティは不正値に対して安全に None を返す設計になっています。保存関数は主キー欠損行をスキップしてログ出力します。

---

今後の予定（例）
- ETL の品質チェックモジュール（quality）の実装と統合。
- strategy / execution / monitoring モジュールの実装（インターフェースはパッケージ構成で確保済み）。
- 単体テスト・統合テストの整備、CI ワークフローの追加。