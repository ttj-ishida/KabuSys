# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。
このプロジェクトは Keep a Changelog の慣習に従います。
セマンティックバージョニングを採用します。

[0.1.0] - 2026-03-17
====================

Added
-----
- 初回リリース: KabuSys — 日本株自動売買システムのコアライブラリを追加。
- パッケージ構成:
  - kabusys.config: 環境変数 / 設定管理（Settings オブジェクトを公開）。
  - kabusys.data: データ取得・保存・スキーマ・ETL パイプライン。
  - kabusys.strategy, kabusys.execution, kabusys.monitoring: 名前空間を公開（実装の拡張を想定）。
- 環境変数自動読み込み:
  - プロジェクトルート（.git または pyproject.toml を基準）を探索し、.env → .env.local の順で自動読み込み（OS 環境変数を保護）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサの強化:
    - export KEY=val 形式対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応
    - インラインコメント（#）の扱い改善
- Settings（設定取得）:
  - J-Quants、kabuステーション、Slack、データベースパス（DuckDB / SQLite）などのプロパティを提供。
  - KABUSYS_ENV（development/paper_trading/live）の検証、LOG_LEVEL の検証などを実装。
- J-Quants API クライアント（kabusys.data.jquants_client）:
  - API 呼び出し用の汎用リクエスト関数を実装（JSON デコード検証含む）。
  - レート制限（固定間隔スロットリング）を実装（デフォルト 120 req/min）。
  - 再試行（最大 3 回）と指数バックオフ、HTTP 408/429/5xx に対するリトライ処理。
  - 401 受信時はリフレッシュトークンで自動的に id_token を更新して 1 回リトライ。
  - ページネーション対応のデータ取得関数:
    - fetch_daily_quotes（株価日足）
    - fetch_financial_statements（四半期 BS/PL）
    - fetch_market_calendar（JPX マーケットカレンダー）
  - DuckDB への冪等保存関数（ON CONFLICT DO UPDATE を使用）:
    - save_daily_quotes / save_financial_statements / save_market_calendar
  - 取得時刻（fetched_at）を UTC で記録して Look-ahead Bias を防止。
  - 型変換ユーティリティ（_to_float, _to_int）を実装。
  - モジュールレベルの id_token キャッシュを実装（ページネーション間で共有）。
- ニュース収集（kabusys.data.news_collector）:
  - RSS フィードからの記事収集処理を実装（デフォルトに Yahoo Finance を含む）。
  - セキュリティ・堅牢性:
    - defusedxml による XML パース（XML Bomb 等の対策）。
    - SSRF 対策: URL スキーム検証（http/https のみ許可）、ホストがプライベート IP の場合拒否、リダイレクト時も検査するハンドラ実装。
    - レスポンス受信サイズの上限（MAX_RESPONSE_BYTES = 10MB）を設け、超過はスキップ。
    - gzip 解凍時のサイズチェック（Gzip bomb 対策）。
    - 許可されないスキームの URL を検出して除外。
  - URL 正規化と記事 ID 生成:
    - トラッキングパラメータ（utm_*, fbclid 等）を除去してクエリソート、フラグメント除去。
    - 正規化後の URL を SHA-256 でハッシュ化し先頭32文字を記事 ID として使用（冪等性確保）。
  - テキスト前処理（URL 除去、空白正規化）。
  - DB 保存:
    - save_raw_news: チャンク化／トランザクション／INSERT ... RETURNING により挿入された ID を正確に取得。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括保存（重複除去、RETURNING による挿入数算出）。
  - 銘柄コード抽出: 4桁数字パターン（known_codes に基づくフィルタ、重複除去）。
- DuckDB スキーマ（kabusys.data.schema）:
  - Raw / Processed / Feature / Execution 各レイヤのテーブル定義を追加（raw_prices, raw_financials, raw_news, prices_daily, market_calendar, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance 等）。
  - インデックス定義（頻出クエリ向け）。
  - init_schema(db_path) で冪等にスキーマ初期化を実行、必要に応じて親ディレクトリを作成。
  - get_connection(db_path) を提供。
- ETL パイプライン（kabusys.data.pipeline）:
  - ETLResult データクラス（成果物 / 品質問題 / エラー情報を保持）。
  - 差分更新ヘルパー（テーブル最終取得日の取得、営業日調整、バックフィル考慮）。
  - run_prices_etl の差分取得ロジック（最終取得日 - backfill_days を date_from に使用する等）を実装の一部として追加。
  - 市場カレンダーの先読み日数・デフォルトバックフィル設定等の定義。

Changed
-------
- （初回リリースのため該当なし）

Fixed
-----
- （初回リリースのため該当なし）

Security
--------
- RSS パーサで defusedxml を利用、SSRF 対策ハンドラ、URL スキーム検証、レスポンスサイズ上限など多数の安全対策を実装。

Removed / Deprecated
--------------------
- （初回リリースのため該当なし）

Notes / 既知の問題
-----------------
- run_prices_etl の実装ファイルが現在のコードベースの末尾で戻り値のタプルが途中で切れている（return len(records), ）ため、そのままでは構文エラーまたは不完全な実装になっている可能性があります。リリース直前に意図した (fetched_count, saved_count) の返却を確認・修正してください。
- jquants_client._request は urllib を直接利用しており、より高度な接続設定（プロキシ、セッション管理、詳細タイムアウト制御等）が必要な場合は拡張の余地があります。
- news_collector の既定ソースは少数に留めているため、追加フィードを利用する際は run_news_collection に sources 引数で渡してください。

開発 / テストに関する補足
------------------------
- 環境変数の自動ロードはテスト時に KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定することで無効化できます。
- news_collector 内の _urlopen はテスト時にモック差し替え可能な設計になっています。

このバージョンは初期機能の骨格（データ取得、保存、スキーマ、基本 ETL、ニュース収集の安全性）を備えています。今後のリリースでは、戦略モジュール・発注実行ロジック・監視／通知機能の充実、細かなエラーハンドリング改善、単体テストの整備等を予定しています。