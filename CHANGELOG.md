Keep a Changelog に準拠した形式で、本コードベースの変更履歴（推測に基づく）を以下に示します。

全ての注目すべき変更点を記録しています。各項目はコード内容から推測してまとめています。

# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。

## [0.1.0] - 初回リリース
最初の公開バージョン。以下の主要な機能・設計要素を実装しています。

### Added
- パッケージ基盤
  - kabusys パッケージを導入。バージョン情報を src/kabusys/__init__.py にて __version__ = "0.1.0" として管理。公開モジュールは data, strategy, execution, monitoring を想定。
- 設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを追加（プロジェクトルートの検出は .git または pyproject.toml を基準）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。
  - .env のパース（コメント、export 形式、クォートとエスケープ、行末コメントの取り扱いなど）に対応する堅牢なパーサを実装。
  - 環境変数の必須チェック（_require）と Settings クラスを実装し、J-Quants トークン、kabu API、Slack、DB パス、環境（development/paper_trading/live）、ログレベル等のプロパティを提供。
  - 環境値の妥当性チェック（KABUSYS_ENV / LOG_LEVEL の許容値検査）。
- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - 株価日足（OHLCV）、財務データ、マーケットカレンダーの取得関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）を実装。ページネーション対応。
  - API レート制御（固定間隔スロットリング）を導入（120 req/min 想定）。
  - リトライ戦略（指数バックオフ、最大 3 回）を実装。HTTP 408/429/5xx 等に対して再試行。429 の場合は Retry-After を優先。
  - 401 Unauthorized 受信時はトークン自動リフレッシュを一度行ってリトライする仕組みを実装（無限再帰防止）。
  - トークンのモジュールレベルキャッシュと get_id_token での取得ロジック。
  - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）: fetched_at を UTC で記録し、ON CONFLICT DO UPDATE による冪等性を確保。
  - 値変換ユーティリティ (_to_float, _to_int) を実装し、無効値や丸めによる誤変換を回避。
- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードから記事を収集するフル機能を実装（fetch_rss, save_raw_news, save_news_symbols, run_news_collection）。
  - セキュリティ・堅牢性設計:
    - defusedxml を利用し XML Bomb 等を防御。
    - SSRF 対策: リダイレクト時のスキーム/ホスト検査用ハンドラ、ホストがプライベートアドレスか判定する関数、最初と最終 URL の検証。
    - URL スキーム検証（http/https のみ許可）。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズチェック（Gzip bomb 対策）。
    - 受信バイト数の事前チェックと超過時の安全なスキップ。
  - 記事 ID は URL を正規化（スキーム/ホスト小文字化、トラッキングパラメータ除去、フラグメント削除、クエリキーソート）したのち SHA-256 の先頭32文字を使用し冪等性を担保。
  - トラッキングパラメータ（utm_*, fbclid, gclid 等）の除去ロジックを実装。
  - テキスト前処理（URL 除去、空白正規化）と RSS の pubDate パース（RFC 2822、UTC へ変換）を実装。
  - DuckDB への保存はチャンク化してトランザクションで実行し、INSERT ... RETURNING を用いて実際に挿入された件数/ID を正確に取得（save_raw_news, save_news_symbols, _save_news_symbols_bulk）。
  - 銘柄コード抽出（4桁の数字、known_codes によるフィルタ）と新規記事に対する銘柄紐付けを一括で行う run_news_collection を実装。
- DuckDB スキーマ定義と初期化（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution 層をカバーする包括的なテーブル定義を実装（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance）。
  - カラム制約（CHECK、NOT NULL、PRIMARY KEY、FOREIGN KEY）を設計し、データ整合性を重視。
  - よく使われるクエリに備えたインデックスを追加（例: idx_prices_daily_code_date, idx_signal_queue_status など）。
  - init_schema(db_path) による冪等的テーブル初期化、get_connection による既存 DB 接続取得機能を提供。
- ETL パイプライン（src/kabusys/data/pipeline.py）
  - ETLResult データクラスを導入し ETL 実行結果（取得数、保存数、品質問題、エラー等）を構造化して返す仕組みを実装。
  - 差分更新ロジックのためのヘルパー関数（_table_exists, _get_max_date, get_last_price_date, get_last_financial_date, get_last_calendar_date）。
  - 非営業日調整ロジック（_adjust_to_trading_day）を実装して、target_date が非営業日の場合に直近の営業日に調整。
  - run_prices_etl を実装（差分取得、backfill_days による再取得、jq.fetch_daily_quotes / jq.save_daily_quotes の利用）。（コード断片のため続きがある想定）

### Security
- RSS ニュース収集での SSRF・XML 攻撃対策を明示的に実装（_defusedxml、SSRF リダイレクトハンドラ、プライベートIP 判定、スキーム検証）。
- 外部 API 呼び出しでのリトライ時に HTTP ヘッダ Retry-After を尊重する等、健全なネットワークハンドリングを実装。

### Performance / Reliability
- J-Quants API 呼び出し時のレートリミッティングと再試行（指数バックオフ）により API レート制限・一時障害に対する耐性を確保。
- DuckDB へのバルク挿入をチャンク化してトランザクションでまとめ、IO とオーバーヘッドを低減。
- ニュースの保存は INSERT ... RETURNING を使用して実際に挿入された件数のみをカウント（ON CONFLICT によるスキップを正確に把握）。

### Other
- 多くの操作で UTC もしくは明示的な日時処理を採用（fetched_at に UTC を ISO8601 Z 表記で記録、RSS pubDate の UTC 標準化、save_* 系での時間付与）。
- コード全体でロギングを利用して処理状況や警告を出力する設計（logger 使用）。

### Known / 想定される制約（コードからの推測）
- run_prices_etl 等 ETL 関数は基本設計が含まれているが、ログ出力や一部のフロー（品質チェック呼び出し quality モジュールの連携など）は別モジュール（quality）に委譲されているため、その実装が必要。
- news_collector の fetch_rss は HTTP エラーを呼び出し元に伝搬する設計であり、run_news_collection は個別ソースの失敗をスキップして続行する設計。
- 一部関数の実装はファイル内で完結しているが、外部設定や DB スキーマ初期化（init_schema）を事前に行う運用が必要。

---

今後のリリース候補（推奨）:
- 品質チェックモジュール（quality）との統合および ETL の完全なワークフロー（品質問題レポート/自動修正）を実装。
- strategy / execution / monitoring パッケージの具体的な実装（現在はパッケージ参照のみ）。
- 単体テスト・統合テストの追加（特にネットワーク周り・DB 周り・SSRF / XML の安全性テスト）。
- ドキュメント（DataPlatform.md, DataSchema.md, 使用ガイド）の整備とサンプル運用スクリプトの追加。

（注）本 CHANGELOG は提供されたソースコードから機能・設計を推測して作成しています。実際のコミット履歴や CHANGELOG の詳細はリポジトリの履歴に基づいて調整してください。