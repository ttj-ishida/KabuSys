CHANGELOG
=========

すべての重要な変更は Keep a Changelog の形式で記録します。
このプロジェクトはセマンティック バージョニングに従います。

フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

- （なし）

0.1.0 - 2026-03-17
------------------

Added
- パッケージ初期リリース: kabusys 0.1.0
  - 基本パッケージ構成:
    - モジュール: data, strategy, execution, monitoring を __all__ に公開。
    - バージョン定義: src/kabusys/__init__.py にて __version__ = "0.1.0" を設定。

- 環境変数・設定管理（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を自動読み込み（プロジェクトルート判定: .git または pyproject.toml を探索）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - 自動ロードを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env パーサ実装の強化:
    - "export KEY=val" 形式に対応。
    - シングル／ダブルクォート内のバックスラッシュエスケープ処理と閉じクォート検出をサポート。
    - クォートなし値でのインラインコメント判定（'#' の直前が空白/タブのときのみコメントとみなす）。
  - 必須設定取得ヘルパー _require()（未設定時に ValueError を送出）。
  - 設定プロパティ群（Settings）を提供:
    - J-Quants / kabu ステーション / Slack / DB パス等の取得。
    - KABUSYS_ENV の検証（development / paper_trading / live）。
    - LOG_LEVEL の検証（DEBUG, INFO, WARNING, ERROR, CRITICAL）。
    - is_live / is_paper / is_dev の簡易プロパティ。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - 基本機能:
    - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、マーケットカレンダー取得関数を実装（ページネーション対応）。
    - get_id_token() によるリフレッシュトークン→IDトークン取得（POST）。
  - レート制限制御:
    - 固定間隔スロットリング _RateLimiter を実装（デフォルト 120 req/min、最小間隔 60/120 秒）。
  - リトライ・エラーハンドリング:
    - 最大リトライ回数 3、指数バックオフ（基数 2 秒）。
    - 再試行対象ステータス: 408, 429 と 5xx。
    - 429 の場合は Retry-After ヘッダを優先。
    - ネットワークエラー時もリトライ。
  - トークン更新:
    - 401 受信時はトークンを自動リフレッシュして 1 回のみ再試行（無限再帰防止のため allow_refresh フラグを使用）。
    - モジュールレベルの ID トークンキャッシュを共有（ページネーション跨ぎで再利用）。
  - DuckDB への保存関数:
    - save_daily_quotes / save_financial_statements / save_market_calendar: 冪等性を保つため INSERT ... ON CONFLICT DO UPDATE を使用。
    - 保存時に fetched_at を UTC ISO 8601 形式で記録。
  - ユーティリティ:
    - _to_float, _to_int の堅牢な変換ヘルパ（空値・不正値は None、"1.0" のような float 文字列→int 対応、非整数の小数は変換しない）。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードからニュース収集し raw_news に保存する完全実装。
  - セキュリティと頑健性:
    - defusedxml を用いた XML パース（XML Bomb 等の対策）。
    - SSRF 対策:
      - リダイレクトごとにスキームとホストを検証する _SSRFBlockRedirectHandler。
      - 事前にホストがプライベートアドレスかをチェックする _is_private_host。
      - 許可スキームは http/https のみ。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）と、gzip 解凍後のサイズ検査（GZip bomb 対策）。
    - User-Agent / Accept-Encoding を設定してフェッチ。
  - 記事 ID と正規化:
    - URL 正規化: スキーム/ホスト小文字化、トラッキングパラメータ（utm_* 等）削除、フラグメント削除、クエリキーソート。
    - 記事ID は正規化 URL の SHA-256 ハッシュの先頭32文字を使用（冪等性保証）。
  - テキスト前処理:
    - URL 削除、空白正規化、先頭/末尾トリム（preprocess_text）。
  - DB 保存:
    - save_raw_news: チャンク INSERT、トランザクション内で INSERT ... ON CONFLICT DO NOTHING RETURNING id を利用し、実際に挿入された記事IDのみを返す。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けをチャンク & トランザクションで保存し、実挿入数を返す。
    - insert チャンクサイズ上限（_INSERT_CHUNK_SIZE = 1000）で SQL 長とパラメータ数を制御。
  - 銘柄コード抽出:
    - 4桁数字パターンを検出し、known_codes セットでフィルタリング（重複除去）。

- DuckDB スキーマ定義（src/kabusys/data/schema.py）
  - DataSchema.md に基づく 3 層＋Execution レイヤのテーブルを定義:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - カラム定義、制約（PRIMARY KEY / CHECK / FOREIGN KEY）を含む DDL を整備。
  - 使用頻度を考慮したインデックスを追加（コード×日付のクエリ等を想定）。
  - init_schema(db_path) による初期化ユーティリティ（親ディレクトリ自動作成、:memory: 対応）。
  - get_connection(db_path) による既存 DB 接続。

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - ETL フローの骨格実装:
    - 差分更新ロジック: DB の最終取得日から backfill_days 日分を巻き戻して再取得（デフォルト backfill_days=3）。
    - run_prices_etl: 日次株価差分 ETL（date_from 自動算出、取得→保存の流れ）。
  - ETLResult dataclass:
    - target_date / fetched/saved カウンタ / quality_issues / errors を含む実行結果オブジェクト。
    - has_errors / has_quality_errors / to_dict() を提供（品質問題は辞書化して出力）。
  - ユーティリティ:
    - テーブル存在チェック、テーブルの最大日付取得ヘルパ（_get_max_date）。
    - 市場カレンダーに基づく営業日調整ヘルパ (_adjust_to_trading_day)（最大 30 日遡るフォールバック）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- RSS/HTTP 周りで SSRF 対策、defusedxml の採用、レスポンスサイズ検査など多数の防御ロジックを導入。

Notes / Migration
- DB 初期化は init_schema() を必ず最初に実行してください。既存スキーマがある場合は冪等的にスキップされます。
- 自動 .env 読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます（テストや CI 用）。
- J-Quants API 利用には環境変数 JQUANTS_REFRESH_TOKEN が必須です。Slack や kabu API 用の必須変数も Settings にて確認できます。
- news_collector の挙動は外部ネットワークおよび RSS フィード構造に依存します。SSRF / サイズ制限により一部フィードがスキップされることがあります。

今後の予定（例）
- quality モジュールとの統合強化（品質チェックルールの実装と ETL 結果への反映）。
- strategy / execution モジュールの具体実装（信号生成、発注ラッパー、約定処理）。
- テストカバレッジの拡充と CI ワークフローの整備。

---