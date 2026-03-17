# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

※このファイルはリポジトリ内のソースコードから実装内容を推測して作成した初期の変更履歴です。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-03-17
初回リリース。日本株自動売買システム KabuSys の基本的なデータ収集・スキーマ・ETL・設定周りの基盤機能を実装。

### 追加 (Added)
- パッケージ初期化
  - src/kabusys/__init__.py にてバージョン __version__ = "0.1.0" を設定し、主要サブパッケージ（data, strategy, execution, monitoring）を公開。

- 設定・環境変数読み込み機能（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を自動ロード（プロジェクトルートを .git または pyproject.toml を基準に検出）。
  - 自動ロードを無効化するためのフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD 対応。
  - .env パース機能（export プレフィックス対応、クォート内エスケープ、コメント処理など）。
  - 環境変数の「保護」機能（既存 OS 環境変数を上書きしない / .env.local による上書きの仕組み）。
  - Settings クラスを導入し、J-Quants / kabuAPI / Slack / DB パス / システム環境等のプロパティを提供。値検証（KABUSYS_ENV や LOG_LEVEL の許容値チェック）を実装。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - ID トークン取得（get_id_token）と API リクエストユーティリティ（_request）を実装。
  - レート制御（120 req/min 固定間隔スロットリング _RateLimiter）。
  - リトライロジック（指数バックオフ、最大3回、408/429/5xx を対象、429 の場合は Retry-After を尊重）。
  - 401 受信時の自動トークンリフレッシュ（1回のみ）とトークンキャッシュ共有機能。
  - データ取得関数:
    - fetch_daily_quotes（株価日足、ページネーション対応）
    - fetch_financial_statements（財務データ、ページネーション対応）
    - fetch_market_calendar（JPX マーケットカレンダー）
  - DuckDB への冪等的保存関数（ON CONFLICT DO UPDATE を利用）:
    - save_daily_quotes, save_financial_statements, save_market_calendar
  - 取得時刻の fetched_at を UTC で記録して Look-ahead bias 対策。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードから記事を取得し raw_news に保存する処理を実装。
  - 主な機能:
    - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント削除）。
    - 記事 ID の生成: 正規化 URL の SHA-256 の先頭32文字を使用して冪等性を確保。
    - defusedxml を利用した XML パースで安全性を確保。
    - SSRF を考慮した検査: URL スキーム検証（http/https のみ許可）、プライベート IP/ループバック/リンクローカル/マルチキャスト判定による拒否。
    - リダイレクト時の事前検査を行うカスタム RedirectHandler（_SSRFBlockRedirectHandler）。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）および gzip 解凍後のサイズチェックによる DoS 対策。
    - テキスト前処理（URL 除去、空白正規化）。
    - DB 保存はチャンク化＋1 トランザクションで INSERT ... ON CONFLICT DO NOTHING RETURNING を用いて実際に挿入された ID を返す（save_raw_news）。
    - 記事と銘柄コードの紐付け（extract_stock_codes / save_news_symbols / _save_news_symbols_bulk）。
    - run_news_collection による複数ソースの統合収集ジョブ（ソース単位でエラーハンドリングして継続）。

- DuckDB スキーマ定義・初期化（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution 層にまたがるテーブル群の DDL を定義。
  - 主要テーブル:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種制約（PRIMARY KEY / CHECK / FOREIGN KEY）とインデックス（頻出クエリ向け）を定義。
  - init_schema(db_path) による初期化処理を提供（親ディレクトリ自動作成、冪等実行）。
  - get_connection(db_path) で既存 DB 接続を取得可能。

- ETL パイプライン基盤（src/kabusys/data/pipeline.py）
  - ETLResult dataclass による ETL 結果の集約（品質問題・エラーの集約、辞書化機能）。
  - 差分取得用ユーティリティ:
    - _table_exists, _get_max_date, get_last_price_date, get_last_financial_date, get_last_calendar_date。
  - 市場カレンダーをもとに営業日に調整するヘルパー（_adjust_to_trading_day）。
  - run_prices_etl の実装（差分更新、backfill_days による再取得、fetch/save の呼び出し）。（ETL ワークフローの基礎を実装）

### 修正 (Changed)
- （初回リリースのため既存リポジトリからの変更はなし）

### 修正 (Fixed)
- （初回リリースのため既存不具合修正はなし）

### セキュリティ (Security)
- RSS パーサーに defusedxml を使用し、XML Bomb 等の攻撃緩和を実施。
- HTTP(S) 以外のスキーム拒否、プライベートアドレスへのアクセス拒否、リダイレクト時の検査で SSRF 対策を実装。
- .env 読み込み時のファイル読み取りエラーは警告に留め、プロセス中断を避ける設計。

### 注意事項 / 既知の制限
- ETL の品質チェック（quality モジュール参照）は呼び出し元での判断に任せる設計（Fail-Fast ではなく問題を列挙）。
- run_prices_etl の呼び出しは target_date／date_from の整合性に依存する。backfill_days のデフォルトは 3 日。
- J-Quants API レート制約は固定間隔スロットリングで満たす設計（120 req/min）。大量ページネーション時のスループットに注意。
- news_collector の既定 RSS ソースは限定（DEFAULT_RSS_SOURCES に Yahoo Finance を登録）。現実運用ではソース追加が必要。
- schema の外部キー／制約は DuckDB のサポート範囲内で定義されているが、運用上のマイグレーションや互換性には注意が必要。

---

将来のリリースでは、strategy/execution/monitoring の具体的実装や品質チェック詳細、モニタリング・アラート機能、テストカバレッジの追加を予定しています。