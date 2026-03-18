Keep a Changelog
=================

すべての重要な変更点をこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠します。

[Unreleased]
------------

- （現時点では未リリースの変更はありません）

0.1.0 - 2026-03-18
-----------------

Added
- パッケージ初期リリース。
  - パッケージバージョン: 0.1.0（src/kabusys/__init__.py にて定義）
- 環境設定管理モジュール (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - 自動ロードを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト向け）。
  - プロジェクトルート検出: .git または pyproject.toml を基準に __file__ を起点に探索（配布後も動作する設計）。
  - .env パーサ: export 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ、コメント取り扱い等を実装。
  - Settings クラスを提供し、J-Quants / kabu ステーション / Slack / DB パス 等の設定プロパティと入力検証（KABUSYS_ENV, LOG_LEVEL）を追加。
- J-Quants API クライアント (kabusys.data.jquants_client)
  - 日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダー取得機能を実装。
  - ページネーション対応で全件取得を行うユーティリティ関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
  - 認証: リフレッシュトークンから ID トークンを取得する get_id_token を実装。
  - レート制御: 固定間隔スロットリングで 120 req/min を守る RateLimiter 実装（最小待ち時間算出）。
  - 冗長性対策: リトライロジック（最大 3 回、指数バックオフ、408/429/5xx を対象）、429 の Retry-After 優先処理を実装。
  - 401 発生時の自動トークンリフレッシュを 1 回行う仕組み（無限再帰回避のため allow_refresh フラグを採用）。
  - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）は冪等（ON CONFLICT DO UPDATE）で fetched_at を UTC で記録。
  - 型変換ユーティリティ (_to_float, _to_int) を実装し、入力の不整合に対処。
- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードからニュース記事を収集して raw_news テーブルへ保存するフルワークフローを実装。
  - セキュリティ・堅牢性:
    - defusedxml を用いた XML パース（XML Bomb 等の防御）。
    - SSRF 対策: URL スキーム検査（http/https のみ）、ホストがプライベート/ループバック/リンクローカル/マルチキャストであれば拒否、リダイレクト時にも検査するカスタムリダイレクトハンドラを実装。
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10 MB）と gzip 解凍後サイズ検査（Gzip bomb 対策）。
    - User-Agent と Accept-Encoding を付与しての取得。
  - コンテンツ処理:
    - URL 正規化（スキーム/ホスト小文字化、トラッキングパラメータ（utm_*, fbclid, gclid 等）削除、クエリソート、フラグメント削除）。
    - 記事ID は正規化 URL の SHA-256 ハッシュ先頭32文字を採用し冪等性を担保。
    - テキスト前処理（URL 除去、空白正規化）。
    - pubDate のパースを実装し、UTC に正規化。パース失敗時は警告ログと現在時刻でフォールバック。
  - DB 保存:
    - DuckDB へチャンク化してバルク INSERT、INSERT ... RETURNING を用いて新規挿入 ID を取得（save_raw_news）。
    - news_symbols（記事と銘柄の紐付け）を一括で保存する内部関数（_save_news_symbols_bulk）を実装し、ON CONFLICT で重複を無視。
  - 銘柄抽出:
    - 本文/タイトルから 4 桁の銘柄コード候補を抽出し、既知銘柄セットでフィルタする extract_stock_codes を実装。
  - デフォルト RSS ソースをいくつか（例: Yahoo Finance カテゴリ）定義。
- DuckDB スキーマと初期化 (kabusys.data.schema)
  - DataSchema.md に基づいた多層スキーマを実装（Raw / Processed / Feature / Execution レイヤー）。
  - raw_prices, raw_financials, raw_news, raw_executions を含む Raw レイヤー。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の Processed レイヤー。
  - features, ai_scores 等の Feature レイヤー。
  - signals, signal_queue, orders, trades, positions, portfolio_performance 等の Execution レイヤー。
  - 各テーブルに制約（PRIMARY KEY / CHECK / FOREIGN KEY）を付与し、典型的な不整合を DB レベルで抑止。
  - 頻出クエリに対するインデックスを作成。
  - init_schema(db_path) によりファイル生成（親ディレクトリ自動作成）→ テーブル・インデックスを冪等作成する機能を実装。get_connection() で既存 DB に接続可能。
- ETL パイプライン (kabusys.data.pipeline)
  - 差分更新の概念を実装（最終取得日からの差分取得、backfill_days による再取得）。デフォルトの backfill_days = 3。
  - 市場カレンダー先読み（_CALENDAR_LOOKAHEAD_DAYS = 90）や J-Quants の最小データ日付（_MIN_DATA_DATE = 2017-01-01）を定義。
  - ETLResult データクラスを導入し、取得数・保存数・品質問題・エラー等を集約して返却。
  - テーブル存在チェックおよび最大日付取得ユーティリティを実装（_table_exists, _get_max_date）。
  - run_prices_etl の一部実装（差分計算、fetch + save の呼び出し）を追加（取得→保存→ログ）。
- パッケージ構成
  - モジュールの __all__ を設定（data, strategy, execution, monitoring）し、パッケージエントリポイントを整理。

Security
- RSS 収集での SSRF 対策（スキーム検査、ホストプライベート判定、リダイレクト検査）。
- defusedxml を用いた XML パースで XML 攻撃を軽減。
- HTTP 取得時のレスポンスサイズ上限と gzip 解凍後サイズチェックによりメモリ DoS を緩和。
- .env ロード時に OS 環境変数を保護（protected set）して誤って上書きしない仕組みを導入。

Performance
- J-Quants クライアントでの固定間隔レートリミッタにより API レートを安定化（120 req/min）。
- ニュース収集のバルク INSERT をチャンク化してトランザクション単位で実行し、オーバーヘッドを低減。
- ページネーション対応により API 呼び出しを自動で継続取得。

Notes / Design decisions
- 多くの保存処理は冪等化（ON CONFLICT ... DO UPDATE / DO NOTHING）されており、再実行や再取得時に安全。
- トークンの自動リフレッシュは 401 を受けた場合に 1 回のみ行う設計（無限再帰防止）。
- RSS の記事IDは URL 正規化後のハッシュを採用することで、トラッキングパラメータ差分による重複登録を防止。
- ETL は品質チェック結果を致命的エラーでも即時停止せず呼び出し元に委ねる方針（Fail-Fast ではない）。

Fixed
- （このリリースでの修正項目はありません／初回リリース）

Deprecated
- （なし）

Removed
- （なし）

Security (future)
- セキュリティ関連のアラートや依存ライブラリの脆弱性が判明した場合、以降のリリースで速やかに更新を行う予定です。

参考
- 詳細実装は各モジュールの docstring に設計方針・制約・処理フローが記載されています（kabusys/data/*, kabusys/config.py, kabusys/data/pipeline.py 等）。