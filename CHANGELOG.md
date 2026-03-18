# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
このパッケージの最初の公開リリースを記録しています。

全般的な方針:
- 可能な限り冪等性とセキュリティを重視した設計（DB の ON CONFLICT、SSRF 対策、defusedxml 等）
- 外部サービス呼び出しはレート制御・リトライ・トークン自動更新を実装
- DuckDB を中心としたローカルデータプラットフォーム構成

## [0.1.0] - 2026-03-18

### Added
- 初期パッケージ構成を追加
  - パッケージ名: kabusys
  - バージョン: 0.1.0

- 環境設定管理 (kabusys.config)
  - .env / .env.local の自動ロード（プロジェクトルートは .git または pyproject.toml を基準に探索）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能（テスト用途想定）
  - .env のパース機能:
    - export KEY=val 形式対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応
    - 行内コメント扱いルール（クォート無しで直前に空白がある場合のみ）
  - Settings クラスにより、必須/既定の設定値をプロパティで提供
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等の必須取得
    - KABUSYS_ENV / LOG_LEVEL の検証（許容値チェック）
    - データベースパス（DUCKDB_PATH, SQLITE_PATH）の既定値と Path 型での提供
    - is_live / is_paper / is_dev のヘルパー

- J-Quants API クライアント (kabusys.data.jquants_client)
  - API 呼び出しラッパーを実装（_request）
    - レート制限（120 req/min）を固定間隔スロットリングで強制（_RateLimiter）
    - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx に対処）
    - 401 時の自動トークンリフレッシュ（1 回のみ）と再試行
    - JSON デコードエラーの明示的扱い
  - get_id_token(): リフレッシュトークンから idToken を取得する POST 実装
  - ページネーション対応のデータ取得関数
    - fetch_daily_quotes(): 株価日足（OHLCV）取得（pagination_key 対応）
    - fetch_financial_statements(): 財務（四半期）取得（pagination_key 対応）
    - fetch_market_calendar(): JPX カレンダー取得
  - DuckDB への保存関数（冪等）
    - save_daily_quotes(), save_financial_statements(), save_market_calendar()
    - fetched_at を UTC ISO8601 で記録し Look-ahead bias のトレースを可能に
    - 重複は ON CONFLICT DO UPDATE で上書き（冪等）
  - ユーティリティ変換関数（_to_float, _to_int）を実装（不正値は None）

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィード取得と記事保存ワークフロー実装
    - fetch_rss(): RSS 取得、XML パース、記事整形（タイトル・コンテンツ前処理）
      - defusedxml を用いた XML パース（XML Bomb 防御）
      - gzip 圧縮対応および受信サイズ制限（MAX_RESPONSE_BYTES = 10MB）
      - リダイレクト時のスキーム/ホスト検査で SSRF 対策（_SSRFBlockRedirectHandler）
      - 最終 URL の再検証（リダイレクト後の追加チェック）
      - 不正スキーム（http/https 以外）の拒否
      - 記事の pubDate を UTC に正規化（フォールバックは現在時刻）
    - 記事ID は正規化 URL の SHA-256 先頭32文字で生成し冪等性を確保（utm_* 等のトラッキングパラメータ除去）
    - preprocess_text(): URL 除去・空白正規化を実施
    - save_raw_news(): DuckDB へ一括挿入（チャンク化、トランザクション、INSERT ... RETURNING で実際に挿入された id を返す）
    - save_news_symbols() / _save_news_symbols_bulk(): 記事と銘柄コードの紐付けを一括保存（ON CONFLICT で重複をスキップ、RETURNINGで実挿入数を取得）
    - extract_stock_codes(): テキストから4桁コードを抽出し known_codes でフィルタリング
  - デフォルト RSS ソースを定義（DEFAULT_RSS_SOURCES に Yahoo Finance ビジネスカテゴリを登録）

- スキーマ定義と初期化 (kabusys.data.schema)
  - DuckDB 用の包括的スキーマ（Raw / Processed / Feature / Execution 層）を定義
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 適切なチェック制約（数値の非負、列の NOT NULL、ENUM 的な CHECK 制約）を設定
  - インデックス定義（頻出クエリ向け）
  - init_schema(db_path): データベースファイルの親ディレクトリ作成を含む初期化関数（冪等）
  - get_connection(db_path): 既存 DB への接続取得（初期化は行わない）

- ETL パイプライン (kabusys.data.pipeline)
  - ETL の設計と主要ユーティリティを実装
    - 差分更新のための最終取得日取得関数（get_last_price_date, get_last_financial_date, get_last_calendar_date）
    - 営業日補正ヘルパー（_adjust_to_trading_day）
    - run_prices_etl(): 差分取得ロジック（差分開始日の自動算出、backfill_days による後出し修正吸収）、取得→保存のワークフロー（jquants_client を使用）
  - ETL 実行結果を保持する ETLResult dataclass（品質チェック問題・エラー一覧・集計値を保持）
  - 品質チェックモジュール（quality）との連携を想定した構造

### Security
- 外部入力・ネットワーク周りの安全対策を強化
  - RSS/XML は defusedxml で解析
  - SSRF 対策: リダイレクト先のスキーム検査、ホストがプライベートへ向かう場合は拒否
  - レスポンスサイズを上限で保護（Gzip 解凍後もチェック）
  - news_collector では http/https 以外のスキームを拒否

### Reliability / Robustness
- ネットワーク呼び出しはレート制御・リトライ・Retry-After の考慮を含む
- API トークンはモジュールレベルでキャッシュし、必要時に自動更新
- DuckDB への保存はトランザクションで行い、失敗時はロールバックして例外を再送出
- DB 側で一貫性チェック（PRIMARY KEY / FOREIGN KEY / CHECK）を導入

### Documentation / Examples
- モジュールの docstring に利用例・設計意図・注意点を明記（各モジュールに実装）

### Notes
- 初期リリースのため、一部サブモジュール（strategy, execution, monitoring 等）は __init__.py のみ存在し、今後拡張予定。
- ETL やニュース収集は外部 API / ネットワークに依存するため、テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD の利用、及びネットワーク呼び出しのモックを推奨。

---

今後の予定（例）
- strategy / execution 層の実装（発注ロジック、約定管理）
- 品質チェック（quality モジュール）の詳細実装と ETL への組み込み強化
- 単体テスト・統合テストの追加（ネットワーク周りのモックを含む）
- ドキュメントの拡充（DataPlatform.md, API 操作手順、運用ガイド等）