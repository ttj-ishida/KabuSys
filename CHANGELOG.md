CHANGELOG
=========

すべての注目すべき変更点を記録します。本ファイルは "Keep a Changelog" の形式に従います。  
このプロジェクトはセマンティックバージョニングを採用します。

[Unreleased]
-------------

- なし

[0.1.0] - 2026-03-17
--------------------

Added
- 初回リリース (kabusys v0.1.0)
  - パッケージ骨格を追加（kabusys/__init__.py）。
  - モジュール構成: data, strategy, execution, monitoring（strategy/execution は初期プレースホルダ）。

- 環境設定管理（kabusys.config）
  - .env ファイルまたは環境変数を読み込む自動ローダーを実装。
    - プロジェクトルートは __file__ から .git または pyproject.toml を探索して特定。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
  - .env 行パーサーの強化:
    - export KEY=val 形式対応。
    - シングル/ダブルクォートとバックスラッシュエスケープを考慮して値を正確に解析。
    - インラインコメントやクォートなしでのコメント扱い（スペース前の#）に対応。
  - settings オブジェクトを提供し、各種必須値（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）を取得。未設定時は ValueError を送出。
  - 環境変数の検証:
    - KABUSYS_ENV の有効値チェック (development, paper_trading, live)。
    - LOG_LEVEL の有効値チェック (DEBUG, INFO, WARNING, ERROR, CRITICAL)。
  - DB パス（DUCKDB_PATH, SQLITE_PATH）プロパティを Path 型で提供。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 基本機能:
    - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーを取得する fetch_* 関数を実装（ページネーション対応）。
  - レート制御:
    - 固定間隔スロットリングで 120 req/min を遵守する _RateLimiter 実装。
  - リトライ / エラーハンドリング:
    - 指数バックオフによるリトライ（最大 3 回）。対象ステータス: 408, 429, 5xx。
    - 429 の場合は Retry-After ヘッダを優先利用。
    - ネットワークエラー（URLError/OSError）にもリトライ。
  - 認証:
    - refresh token から id_token を取得する get_id_token を実装。
    - 401 受信時は id_token を自動リフレッシュして 1 回だけ再試行（無限再帰の回避）。
    - モジュールレベルで id_token をキャッシュしてページネーション間で共有。
  - DuckDB への保存:
    - save_daily_quotes / save_financial_statements / save_market_calendar を実装。
    - 冪等性: INSERT ... ON CONFLICT DO UPDATE を使用。
    - fetched_at を UTC ISO 形式で保存し、データ取得時刻を記録（Look-ahead Bias 対策）。
  - ユーティリティ関数:
    - _to_float / _to_int により安全な数値変換（空値・不正値を None へ）。

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィードから記事を収集し raw_news に保存する機能を実装。
  - セキュリティ対策:
    - defusedxml を用いた XML パース（XML Bomb 等の緩和）。
    - URL スキーム検証（http/https のみ許可）。
    - リダイレクト時の事前検査とプライベートIP判定により SSRF を防止するカスタムRedirectHandler。
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10 MB）でメモリ DoS / Gzip Bomb を防止。
  - データ処理:
    - URL 正規化: 小文字化・トラッキングパラメータ（utm_* 等）削除・フラグメント除去・クエリソート。
    - 記事 ID は正規化 URL の SHA-256（先頭32文字）で生成し冪等性を確保。
    - テキスト前処理: URL 除去・空白正規化。
    - fetch_rss: gzip 解凍対応、最終 URL の再検証、XML パースフォールバックを実装。
  - DB 保存:
    - save_raw_news: チャンク化して INSERT ... ON CONFLICT DO NOTHING RETURNING id を使用し、実際に挿入された記事IDリストを返す。トランザクションでまとめて実行。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けをチャンクINSERTで一括保存（ON CONFLICT DO NOTHING、RETURNING で正確な挿入数を取得）。
  - 銘柄抽出:
    - 4桁数字パターンによる銘柄コード抽出（known_codes を用いてフィルタ）。重複除去。

- DuckDB スキーマ定義 / 初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution の各レイヤに対応したテーブル群を定義（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance 等）。
  - 各種制約（PRIMARY KEY, CHECK, FOREIGN KEY）とパフォーマンスを考慮した INDEX を定義。
  - init_schema(db_path) により親ディレクトリ生成→DDL 実行→インデックス作成を行い、接続を返却。
  - get_connection(db_path) で既存 DB へ接続可能。

- ETL パイプライン（kabusys.data.pipeline）
  - ETLResult データクラスによるエラー・品質問題の集約表現を提供。
  - 差分更新ロジック:
    - DB の最終取得日を基に差分（および backfill_days による再取得レンジ）を自動算出。
    - 市場カレンダーは先読み（_CALENDAR_LOOKAHEAD_DAYS）。
  - ヘルパー:
    - テーブル存在チェック、最大日付取得、営業日調整（非営業日の場合は直近営業日に調整）。
  - 個別ジョブ:
    - run_prices_etl: 差分取得 → jq.fetch_daily_quotes → jq.save_daily_quotes の流れを実装（backfill 対応）。
  - 品質チェックモジュール（quality）は分離（呼び出し/連携想定）。

Security
- RSS/HTTP 周りに複数のセキュリティ対策を導入:
  - defusedxml を用いた安全な XML パース。
  - SSRF 対策: URL スキーム検証、ホストのプライベートIP判定、リダイレクト時の検査。
  - レスポンスサイズ上限と gzip 解凍後の再検査で Gzip/Zip Bomb を緩和。

Performance
- API 呼び出しでのレート制御（固定間隔スロットリング）。
- id_token のモジュールキャッシュにより不要な認証呼び出しを削減。
- DB への一括挿入はチャンク化してトランザクションでまとめ、INSERT ... RETURNING を活用して挿入結果を正確に把握。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- なし

Removed
- なし

Notes / 今後の改善候補
- quality モジュールを実装して ETL 内での品質チェックを有効化する（現在は参照のみ）。
- strategy / execution / monitoring 層の実装（現在はプレースホルダ）。
- news_collector の既存コードに対するユニットテスト、外部ネットワーク呼び出しのモック追加。
- J-Quants client のページネーションやエラーハンドリングに対する統合テストを整備。

-----
発行日: 2026-03-17