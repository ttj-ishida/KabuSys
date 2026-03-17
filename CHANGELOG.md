# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に従います。  
このファイルは、コードベースから推測できる機能追加・設計方針・既知の問題点をまとめたものです。

## [0.1.0] - 2026-03-17

### 追加
- パッケージの初期リリース。
  - パッケージ名: kabusys
  - バージョン: 0.1.0 (src/kabusys/__init__.py)

- 環境変数 & 設定管理モジュール（src/kabusys/config.py）
  - プロジェクトルートを .git / pyproject.toml から検出し、.env / .env.local を自動ロード（KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化可）。
  - .env パーサーは以下のケースに対応:
    - export KEY=val 形式
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - インラインコメントの扱い（クォートの有無に応じた挙動）
  - OS 環境変数を保護するための protected キーセットを考慮した上書き/非上書き挙動。
  - 必須環境変数取得用の _require() により未設定時に明示的なエラーを発生させる。
  - Settings クラス経由で以下の設定を取得:
    - J-Quants / kabuステーション / Slack の認証情報
    - DBパス（DuckDB/SQLite）のデフォルト（data 以下）
    - 実行環境（development / paper_trading / live）の検証
    - ログレベルの検証
    - is_live / is_paper / is_dev の便利プロパティ

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - API 設計方針の反映:
    - レート制限 (120 req/min) を固定間隔スロットリングで実装（_RateLimiter）。
    - リトライ機構（最大 3 回、指数バックオフ、対象ステータス: 408, 429, 5xx）。
    - 401 応答時は ID トークンを自動リフレッシュして 1 回だけ再試行。
    - ページネーション対応（pagination_key を用いたループ）で全件取得。
    - 取得時刻（fetched_at）を UTC ISO 標準で記録し、Look-ahead Bias を抑制。
  - 提供 API:
    - get_id_token(): リフレッシュトークンから idToken を取得（POST）。
    - fetch_daily_quotes(), fetch_financial_statements(), fetch_market_calendar(): データ取得（ページネーション対応）。
    - save_daily_quotes(), save_financial_statements(), save_market_calendar(): DuckDB へ冪等的に保存（ON CONFLICT DO UPDATE）。
  - 型安全な変換ユーティリティ: _to_float(), _to_int()（不正値は None にする安全設計）。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードから記事を取得し raw_news / news_symbols に保存する ETL を実装。
  - セキュリティ / 安全性対策:
    - defusedxml を使用した XML パース（XML Bomb 等に対処）。
    - リダイレクト時にスキームとホストを検証する専用ハンドラで SSRF を防止（_SSRFBlockRedirectHandler）。
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）を導入しメモリ DoS を防止、gzip 解凍後も再検査。
    - 許可する URL スキームは http/https のみ（その他は拒否）。
    - ホスト/IP がプライベート・ループバック等であれば拒否（_is_private_host）。
  - 記事IDの生成:
    - URL 正規化（トラッキングパラメータ除去・小文字化・フラグメント除去・クエリソート）後、SHA-256 を取り先頭32文字を ID に使用（冪等性確保）。
  - DB 操作:
    - INSERT ... ON CONFLICT DO NOTHING と RETURNING を利用して「実際に挿入された」ID/件数を正確に取得。
    - チャンク単位（_INSERT_CHUNK_SIZE=1000）でバルク挿入、全操作を 1 トランザクションにまとめる（パフォーマンスと整合性の最適化）。
  - その他ユーティリティ:
    - preprocess_text(): URL 除去・空白正規化
    - extract_stock_codes(): テキストから 4 桁銘柄コードを抽出（既知コードセットに基づくフィルタ）
  - run_news_collection(): 複数 RSS ソースを順次処理し、個別ソースの失敗は他ソースに影響を与えない堅牢な収集ジョブを実装。デフォルトソースとして Yahoo Finance 系のカテゴリ RSS を用意。

- DuckDB スキーマ定義 & 初期化（src/kabusys/data/schema.py）
  - DataSchema.md に基づき 3 層（Raw / Processed / Feature）+ Execution 層のテーブル群を定義:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な PRIMARY KEY / CHECK 制約を付与。
  - クエリパターンを踏まえたインデックスを作成（code/date、ステータス検索等）。
  - init_schema(db_path): 親ディレクトリ自動作成を含め、全DDL/インデックスを実行して DB を初期化するユーティリティを提供。
  - get_connection(db_path): 既存 DB への接続を返すユーティリティ。

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - ETLResult dataclass により ETL 実行結果（取得数、保存数、品質問題、エラー）を構造化。
  - 差分更新ヘルパー:
    - get_last_price_date(), get_last_financial_date(), get_last_calendar_date() を提供。
    - 市場カレンダーに基づき非営業日を直近営業日に調整する _adjust_to_trading_day() を実装。
  - run_prices_etl(): 差分更新（最終取得日から backfill_days の再取得）、idempotent 保存の実装方針を導入。デフォルトの backfill_days = 3、最小データ開始日 _MIN_DATA_DATE = 2017-01-01。
  - 品質チェック設計: quality モジュールを利用して欠損・スパイク・重複・日付不整合を検出する方向性を持つ（検出しても ETL 自体は継続する設計）。

- モジュール構成
  - パッケージの __all__ に data, strategy, execution, monitoring を公開（src/kabusys/__init__.py）。
  - strategy / execution / data パッケージの __init__.py を配置（将来的な拡張を想定したプレースホルダ）。

### 変更
- 初版のため該当なし。

### 修正
- 初版のため該当なし。

### セキュリティ
- XML パースに defusedxml を採用。
- RSS フェッチで SSRF 対策を実装（スキーム検証・ホストプライベート判定・リダイレクト検査）。
- ネットワークレスポンスサイズ上限を導入（MAX_RESPONSE_BYTES）してメモリ攻撃を緩和。

### 既知の問題 / 注意点
- run_prices_etl() 実装の末尾が不完全（ソースから推測される箇所で戻り値が不完全に記述されている）。現在の実装では (fetched_count, saved_count) を返すことが意図されているが、実際のコード片では saved 値の返却が欠けている可能性があります。実運用前に戻り値を確認・修正してください。
- 一部のモジュール（strategy, execution, monitoring）の実装はプレースホルダまたは未実装であり、戦略ロジック・実行ロジック・監視ロジックは別途実装が必要です。
- DuckDB に対する SQL 実行で文字列組み立てを行う箇所があり（プレースホルダを使用しているが長い VALUES 部分を f-string で組み立てる実装）、外部からの値が直接 SQL に埋め込まれないよう呼び出し側で入力検証を行うことを推奨します（現在の実装はプレースホルダ(?, ...) を併用しているため基本的には安全だが、注意が必要な箇所がある可能性あり）。
- J-Quants API クライアントは urllib を使った同期実装のため、大量リクエスト時はブロッキングが発生する点に注意。スレッドまたはプロセス分散、もしくは非同期化の検討が必要な場面があります。

---

注: 本 CHANGELOG は提供されたコードベースの内容から推測して作成しています。実際のリリースノートや運用においては、さらに詳細なテスト結果・設計文書・実装差分に基づく説明を付加してください。