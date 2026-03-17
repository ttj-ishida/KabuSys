# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。

履歴
----

### [0.1.0] - 2026-03-17

Added
- 初回リリース。
- パッケージ初期化
  - kabusys パッケージの公開バージョンを `0.1.0` に設定。公開モジュールは data/strategy/execution/monitoring を想定。
- 環境設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダを実装。プロジェクトルートは `.git` または `pyproject.toml` を基準に探索するため、CWD に依存しない。
  - .env パース機能強化:
    - コメント行のスキップ、`export KEY=val` 形式対応、シングル/ダブルクォート内のエスケープ処理、インラインコメント処理などに対応。
    - 既存 OS 環境変数は保護され、`.env.local` は上書き（override）される設計。自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能（テスト用）。
  - 必須設定取得ヘルパー `_require` と、型変換を含む各種プロパティを提供（J-Quants トークン、kabuAPI パスワード、Slack トークン/チャンネル、DB パスなど）。
  - `KABUSYS_ENV` と `LOG_LEVEL` の値検証を実装（許容値チェック）。
- J-Quants API クライアント (kabusys.data.jquants_client)
  - API との通信ロジックを実装。
  - レート制御: 固定間隔スロットリングで 120 req/min に対応する RateLimiter を実装。
  - 再試行ロジック: ネットワークエラーや 408/429/5xx を対象に指数バックオフで最大 3 回リトライ。429 の場合は `Retry-After` ヘッダを尊重。
  - 認証: リフレッシュトークンから ID トークンを取得する `get_id_token` を実装。401 受信時はトークン自動リフレッシュを 1 回行って再試行する仕組みを実装（無限再帰防止のため一部呼び出しではリフレッシュ禁止）。
  - ページネーション対応で以下の取得関数を実装:
    - `fetch_daily_quotes` (OHLCV 日足)
    - `fetch_financial_statements` (四半期 BS/PL 等)
    - `fetch_market_calendar` (JPX マーケットカレンダー)
  - DuckDB 保存用の冪等保存関数を実装（ON CONFLICT DO UPDATE）:
    - `save_daily_quotes`, `save_financial_statements`, `save_market_calendar`
  - 取得時刻（fetched_at）は UTC ISO 形式で記録し、Look-ahead bias を防止する設計。
  - JSON デコード失敗や HTTP エラー時のログ/例外処理を整備。
  - ユーティリティ関数 `_to_float` / `_to_int` を実装し、文字列から安全に数値化する挙動を定義（小数部が残る場合の int 変換は None を返す等）。
- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードから記事を収集して DuckDB の raw_news テーブルへ保存する一連の処理を実装。
  - セキュリティと堅牢性:
    - `defusedxml` を用いた XML パース（XML Bomb 等への対策）。
    - SSRF 対策: URL スキーム検証（http/https のみ許可）、ホストがプライベート/ループバック/リンクローカルでないことを DNS 解決や IP 判定で確認、リダイレクト先も検査するカスタムリダイレクトハンドラを実装。
    - レスポンスサイズ上限 (10 MB) を導入し、事前チェック・読み込み上限・gzip 解凍後の再チェックでメモリ DoS を防止。
    - URL 正規化時にトラッキングパラメータ（utm_* 等）を削除。
  - 冪等性:
    - 記事 ID は正規化 URL の SHA-256 ハッシュの先頭32文字を使用し同一性を保証。
    - DB は INSERT ... ON CONFLICT で重複を排除。
    - raw_news の保存はチャンク分割（デフォルト 1000 件）かつ単一トランザクションで実行、`INSERT ... RETURNING id` で挿入された ID を返す。
    - news_symbols（記事と銘柄の紐付け）保存のための単件/一括関数を実装（重複除去・チャンク処理・RETURNING を使用）。
  - テキスト前処理・抽出機能:
    - URL 除去、空白正規化を行う `preprocess_text`。
    - RSS pubDate のパース関数 `_parse_rss_datetime`（RFC2822 -> UTC naive datetime。パース失敗時は代替時刻を使用）。
    - テキストから 4 桁の銘柄コードを抽出する `extract_stock_codes`（known_codes フィルタ付き）。
  - エントリポイント `fetch_rss`, `save_raw_news`, `save_news_symbols`, `_save_news_symbols_bulk`, `run_news_collection` を提供。`run_news_collection` は複数ソースを独立して処理し、ソース単位でエラーを無視して他ソースを継続する設計。
  - デフォルト RSS ソースに Yahoo Finance のカテゴリーニュースを含む。
- DuckDB スキーマ (kabusys.data.schema)
  - DataPlatform.md に従った 3 層 + 実行レイヤーのスキーマを定義:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルの制約（PRIMARY KEY、CHECK、FOREIGN KEY）を設定し、主要クエリパターン向けに複数のインデックスを作成。
  - `init_schema(db_path)` によりファイル DB の親ディレクトリ自動作成、DDL の冪等実行、インデックス作成を行い接続を返す。`:memory:` によるインメモリ DB をサポート。
  - `get_connection(db_path)` で既存 DB への接続を取得（スキーマ初期化は行わない）。
- ETL パイプライン (kabusys.data.pipeline)
  - ETL の設計方針と差分更新フローを実装。
  - ETL 実行結果を表す `ETLResult` データクラスを導入（品質検査結果やエラーリストを含む）。
  - テーブル存在チェック、最大日付取得ヘルパー（`_table_exists`, `_get_max_date`）と、raw_prices / raw_financials / market_calendar の最終取得日を返す `get_last_price_date`, `get_last_financial_date`, `get_last_calendar_date` を実装。
  - 営業日補正ヘルパー `_adjust_to_trading_day` を実装（market_calendar を参照して過去方向に調整、未取得時はフォールバック）。
  - 差分更新ロジックを有する `run_prices_etl` を実装:
    - DB の最終取得日から backfill_days 日分を再取得して API の後出し修正を吸収する設計。
    - デフォルトのバックフィル日数は 3 日、最小取得日 `_MIN_DATA_DATE`（2017-01-01）を設定。
    - 取得は jquants_client の fetch / save 関数を利用して冪等保存する。
- モジュール構成
  - strategy と execution パッケージの __init__ を用意（スケルトン）。

Security
- news_collector: defusedxml の使用、SSRF 対策、受信サイズ制限、gzip 解凍後の追加チェックなど、外部入力・HTTP レスポンスに対する強化を実施。

Notes / Implementation details
- J-Quants クライアントはグローバルな ID トークンキャッシュを持ち、ページネーション間でトークンを共有して認証コストを削減する。必要に応じて強制リフレッシュが可能。
- DuckDB への保存では ON CONFLICT を利用して冪等性を確保しているため、再実行による重複登録を防止できる。
- RSS 記事ID生成は URL 正規化後のハッシュを利用するため、トラッキングパラメータの違いによる重複を低減する。
- テスト時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動 .env ロードを無効化し、環境を制御可能。

Known issues
- （初期リリース）戦略（strategy）・実行（execution）の具体的実装は骨組み中心で、取引ロジックやライブ連携は未実装／未完成の箇所があります。
- pipeline モジュールは主要なヘルパーと prices の差分 ETL を実装しているが、財務データ・カレンダー等の完全な ETL ワークフローや品質チェックの呼び出しは、今後の拡張対象です。

----