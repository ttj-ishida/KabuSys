Keep a Changelog
----------------

すべての重要な変更点をここに記録します。  
このファイルは Keep a Changelog の形式に準拠しています。  

最新版: 0.1.0

[Unreleased]
-----------

- なし

0.1.0 - 2026-03-17
------------------

Added
- パッケージ初期リリース: kabusys (src/kabusys/__init__.py)
  - バージョン 0.1.0 を設定し、公開 API として data, strategy, execution, monitoring をエクスポート。

- 環境設定モジュール (src/kabusys/config.py)
  - .env/.env.local または OS 環境変数から設定を読み込む自動ロード機能を実装。プロジェクトルートは .git または pyproject.toml を基準に探索して特定。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト用）。
  - export KEY=val 形式やクォート、インラインコメントの取り扱いを考慮した .env パーサを実装。
  - 必須環境変数取得用 _require と、Settings クラスで各種設定プロパティ（J-Quants トークン、kabu API、Slack、データベースパス、環境判定、ログレベル etc.）を提供。
  - KABUSYS_ENV / LOG_LEVEL のバリデーション実装。

- J‑Quants API クライアント (src/kabusys/data/jquants_client.py)
  - APIアクセス用の共通実装:
    - 固定間隔スロットリングによるレート制御（120 req/min）。
    - 冪等性を意識したページネーション対応。
    - 再試行ロジック（指数バックオフ、最大3回）。HTTP 408/429/5xx に対するリトライ。
    - 401 受信時にリフレッシュトークンで id_token を自動更新して再試行（1回のみ）。
    - レスポンス JSON のデコードエラーハンドリング。
  - データ取得関数:
    - fetch_daily_quotes: 日次株価（OHLCV）取得（ページネーション対応）。
    - fetch_financial_statements: 財務データ（四半期 BS/PL）取得（ページネーション対応）。
    - fetch_market_calendar: JPX マーケットカレンダー取得。
  - DuckDB への保存関数（冪等保存）:
    - save_daily_quotes, save_financial_statements, save_market_calendar: ON CONFLICT ... DO UPDATE を使って重複を排除・更新。
    - 各保存時に fetched_at を UTC ISO8601 で記録し、Look‑ahead bias のトレーサビリティを確保。
  - 型変換ユーティリティ _to_float / _to_int を提供（安全な変換・異常値処理）。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードから記事を収集して raw_news/ news_symbols へ保存する一連の処理を実装。
  - セキュリティ対策:
    - defusedxml による XML パース（XML Bomb 等の対策）。
    - SSRF 対策: URL スキーム検証（http/https のみ許可）、ホストがプライベート/ループバック/リンクローカルかを検査、リダイレクト先の事前検証を行うカスタム RedirectHandler を実装。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズ検査でメモリ DoS を防止。
    - User-Agent と Accept-Encoding を適切に設定してフェッチ。
  - データ整形・ID設計:
    - URL 正規化（スキーム/ホストの小文字化、追跡パラメータ除去、フラグメント除去、クエリソート）。
    - 記事ID を正規化 URL の SHA‑256 の先頭32文字で生成し冪等性を保証。
    - preprocess_text による URL 除去と空白正規化。
  - DB 書き込み:
    - save_raw_news は chunked INSERT + INSERT ... RETURNING を利用して新規挿入された記事IDを返す。トランザクションでまとめてコミット/ロールバック。
    - save_news_symbols / _save_news_symbols_bulk は記事と銘柄コードの紐付けを一括挿入（ON CONFLICT DO NOTHING）して挿入件数を正確に返す。
  - 銘柄抽出ロジック:
    - 4桁数字パターンから known_codes と照合して有効銘柄コードを抽出する extract_stock_codes を実装。
  - デフォルト RSS ソースとして Yahoo Finance のカテゴリフィードを定義。

- DuckDB スキーマ定義・初期化モジュール (src/kabusys/data/schema.py)
  - Raw / Processed / Feature / Execution の多層スキーマを定義。
  - raw_prices, raw_financials, raw_news, raw_executions、prices_daily, market_calendar, fundamentals, news_articles, news_symbols、features, ai_scores、signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance 等を定義。
  - 各テーブルに適切な型・制約（CHECK / PRIMARY KEY / FOREIGN KEY）を付与。
  - よく使うクエリパターンのためのインデックスを定義（例: idx_prices_daily_code_date, idx_signal_queue_status 等）。
  - init_schema(db_path) で親ディレクトリ自動作成とテーブル一括作成（冪等）を行い、DuckDB 接続を返す。get_connection も提供。

- ETL パイプライン (src/kabusys/data/pipeline.py)
  - ETL の設計思想に基づく差分更新パイプライン補助関数を提供。
  - ETLResult データクラスで処理結果・品質問題・エラーを集約。to_dict により品質問題をシリアライズ可能。
  - テーブル存在確認、最終取得日の取得ヘルパー（get_last_price_date / get_last_financial_date / get_last_calendar_date）を実装。
  - 市場カレンダーを用いて非営業日の対象日の補正を行う _adjust_to_trading_day を実装。
  - run_prices_etl の骨子を実装（差分更新ロジック、backfill_days による再取得、jquants_client 呼び出し、保存、ログ出力）。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Security
- RSS/HTTP フェッチに関して SSRF、XML Bomb、Gzip Bomb、メモリ DoS を防ぐ複数の対策を導入（news_collector）。
- .env 読み込みのファイルオープン失敗で警告を出して継続するように安全に実装（config）。

Notes / その他
- 多くの機能は設計文書（DataPlatform.md / DataSchema.md など）に準拠した実装を想定しており、API レート制限・トレーサビリティ・冪等性を重視しています。
- strategy, execution, monitoring パッケージはパッケージ公開上は存在するが（__all__ に含まれる）本リリースでは内部実装が空または別モジュールで拡張する前提です。
- 今後の予定:
  - ETL の統合実行（run_prices_etl を含む各 run_* ジョブの完成）、品質チェックモジュール (kabusys.data.quality) の連携強化。
  - strategy / execution / monitoring の実装と、それらを結合するランタイムコンポーネントの追加。

BREAKING CHANGES
- なし

----