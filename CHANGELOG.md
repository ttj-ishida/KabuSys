CHANGELOG
=========

すべての注目すべき変更をこのファイルに記録します。
このプロジェクトは Keep a Changelog の慣習に従います。
Semantic Versioning に従います。

Unreleased
----------

- 既知の問題・予定修正
  - run_prices_etl の戻り値が不完全なまま（現在の実装は (fetched_count, ) のようにタプルが途中で終わっている）。次回リリースで正しい (fetched, saved) を返すよう修正予定。
  - その他小さなリファクタリングやテストの追加を予定。

0.1.0 - 2026-03-17
------------------

Added
- パッケージ初期リリース（kabusys v0.1.0）
  - パッケージメタ情報: src/kabusys/__init__.py に __version__ = "0.1.0" を追加。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルまたは実環境変数から設定値を読み込む自動ロード機能を実装。
    - 読み込み順序: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
    - プロジェクトルートの検出は __file__ を基点に .git または pyproject.toml を探索して行う（配布後も動作するよう設計）。
  - .env 行パーサを実装（export プレフィックス対応、クォートとエスケープの処理、インラインコメントの扱い等）。
  - Settings クラスを公開:
    - J-Quants / kabuステーション / Slack / DB パス / 環境種別・ログレベル 等の取得用プロパティを提供。
    - 必須変数未設定時は ValueError を発生させる _require 関数を使用。

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - API クライアントを実装（/v1 ベース）。
  - レート制限遵守のための固定間隔スロットリング _RateLimiter（120 req/min 相当）を実装。
  - 再試行ロジック（指数バックオフ、最大 3 回、対象ステータス 408/429/5xx）を実装。
  - 401 受信時の自動トークンリフレッシュを 1 回だけ行う仕組みを実装（無限再帰防止）。
  - ID トークンのモジュールレベルキャッシュを実装し、ページネーション間で共有。
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar のページネーション対応取得関数を実装。
  - DuckDB へ冪等に保存する save_daily_quotes / save_financial_statements / save_market_calendar を実装（ON CONFLICT DO UPDATE）。
  - 取得時刻（fetched_at）を UTC で記録し Look-ahead Bias のトレースを可能にする。
  - 入力変換ユーティリティ _to_float / _to_int を実装（堅牢な型変換と不正値ハンドリング）。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードからニュース記事を収集するフルスタック実装。
    - defusedxml を用いた安全な XML パース。
    - URL 正規化（トラッキングパラメータ除去、ソート、フラグメント削除）と SHA-256 による記事ID生成（先頭32文字）。
    - SSRF 対策:
      - URL スキーム制限（http/https のみ許可）。
      - リダイレクト時にスキームとホストを検査するカスタムリダイレクトハンドラ。
      - ホストがプライベート/ループバック/リンクローカル/マルチキャストの場合は拒否。
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後サイズ検査（Gzip bomb 対策）。
    - RSS 内の pubDate をパースして UTC naive datetime として扱う処理。
    - テキスト前処理（URL除去、空白正規化）。
  - DuckDB への保存関数:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING と RETURNING を用い、実際に挿入された記事 ID のリストを返す。バルクチャンク処理に対応し単一トランザクションでコミット。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括保存（重複除去・チャンク処理・RETURNING により挿入数を正確に返す）。
  - 銘柄コード抽出: 正規表現で 4 桁数字を抽出し既知コードセットでフィルタする extract_stock_codes を実装。
  - run_news_collection: 複数 RSS ソースを走らせて記事収集 → raw_news 保存 → （既知コードが与えられれば）news_symbols に紐付けまで行う統合ジョブ。各ソースは独立してエラー処理（1 ソース失敗しても他は継続）。

- DuckDB スキーマ定義 & 初期化 (src/kabusys/data/schema.py)
  - Raw / Processed / Feature / Execution 層にわたるテーブル DDL を網羅的に定義（raw_prices, raw_financials, raw_news, market_calendar, features, ai_scores, signals, signal_queue, orders, trades, positions 等）。
  - 制約（PRIMARY KEY / CHECK / FOREIGN KEY）を多数定義してデータ品質を担保。
  - 検索パターンに基づくインデックスを複数定義（例: idx_prices_daily_code_date, idx_signal_queue_status 等）。
  - init_schema(db_path) で DB ファイル親ディレクトリ自動作成 → すべてのテーブルとインデックスを冪等に作成して接続を返す。
  - get_connection(db_path) による既存 DB への接続を提供。

- ETL パイプライン (src/kabusys/data/pipeline.py)
  - ETL 実行結果を格納する ETLResult dataclass を実装（品質問題やエラーの集約、辞書化メソッドを含む）。
  - 差分取得ロジックのヘルパーを実装:
    - テーブル存在チェック _table_exists, 最大日付取得 _get_max_date。
    - 市場カレンダーを考慮して非営業日を直近営業日に調整する _adjust_to_trading_day。
    - get_last_price_date / get_last_financial_date / get_last_calendar_date のユーティリティ。
  - run_prices_etl の骨組みを実装:
    - 差分更新（最終取得日 - backfill_days から再取得）をサポート。
    - jq.fetch_daily_quotes で取得し、jq.save_daily_quotes で保存する流れを実装。
    - （注）現状の実装に戻り値の不整合（上記 Unreleased 参照）があり、次回修正予定。

Security
- セキュリティ対策を重視した実装を多数導入:
  - RSS パースに defusedxml を使用して XML 関連の攻撃を軽減。
  - SSRF 対策（スキーム制限・プライベートホスト検査・リダイレクト検査）。
  - 外部レスポンスのサイズ上限設定と gzip 解凍後の再検査（メモリ DoS / Gzip bomb 対策）。

Deprecated
- なし（初回リリース）。

Removed
- なし（初回リリース）。

Fixed
- なし（初回リリース）。既知の問題は Unreleased に記載。

Notes / 設計上の補足
- J-Quants API のレート制限（120 req/min）やリトライ挙動、トークンリフレッシュ等はクライアント側で管理しているため、上位処理はこれらを意識せず利用可能。
- DuckDB への保存は冪等性（ON CONFLICT）を念頭に置いた設計のため、繰り返し実行しても重複や不整合が起きにくい。
- news_collector は既知銘柄セットを外部から注入する形を想定しており、記事→銘柄紐付けはそのセットに依存する。
- ETL モジュールは品質チェック（quality モジュール）との協調を想定しているが、quality モジュール自体の実装はこの差分からは含まれているか未実装か不明（呼び出し箇所は準備済み）。

もし特定の変更点をより詳細に分解してバージョンごとに記載したい、あるいは既知の問題（run_prices_etl 等）を優先的に修正してリリースノートへ反映したい場合は、その旨を教えてください。必要に応じてリリース日やコミットハッシュを追加して整備します。