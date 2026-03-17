# Changelog

すべての注目すべき変更点を記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

全般:
- 初期リリース v0.1.0 を作成。
- パッケージエントリポイント: kabusys パッケージは data, strategy, execution, monitoring を公開。

[0.1.0] - 2026-03-17
--------------------

Added
- 基本パッケージ構成
  - src/kabusys/__init__.py によるバージョン定義（0.1.0）と公開モジュール指定。

- 環境設定 / ロード機能（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを追加。
  - プロジェクトルート検出ロジック: __file__ から親ディレクトリを探索して .git または pyproject.toml を基準に自動検出（配布後の動作を考慮）。
  - .env 自動読み込みの優先順位を実装: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード無効化可能。
  - .env パーサは export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、行末コメントの扱いなど堅牢なパースを実装。
  - 環境変数取得の必須チェック（_require）と検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）。
  - DB パス（DUCKDB_PATH / SQLITE_PATH）、Slack / API 関連トークン等のプロパティ化された設定を提供。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダー取得を実装。
  - レートリミッタ（固定間隔スロットリング）を実装し、デフォルトで 120 req/min を遵守。
  - リトライロジック（指数バックオフ、最大 3 回）を実装。対象ステータス: 408, 429, 5xx。429 の場合は Retry-After ヘッダを尊重。
  - 401 Unauthorized 受信時の自動トークンリフレッシュを 1 回まで行い再試行（無限再帰防止のため allow_refresh フラグあり）。
  - ページネーション対応の fetch_XXX 関数（fetch_daily_quotes, fetch_financial_statements）。
  - DuckDB への冪等保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。ON CONFLICT DO UPDATE により重複を排除。
  - データ取得時に fetched_at（UTC）を付与して Look-ahead bias 対策を意識。
  - 型変換ユーティリティ（_to_float, _to_int）は不正値や空値を安全に None に変換。_to_int は "1.0" などの float 文字列を扱うが小数非ゼロは None を返す等の挙動を定義。

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィードからのニュース収集機能を実装（DEFAULT_RSS_SOURCES に代表的フィードを定義）。
  - セキュリティ対策:
    - defusedxml を利用した XML パースで XML Bomb 等を軽減。
    - SSRF 対策: リダイレクト検査用ハンドラ（_SSRFBlockRedirectHandler）を実装し、スキーム検証・プライベートIP/ループバック/リンクローカルのブロックを行う。
    - URL スキーム検証（http/https のみ許可）とホストのプライベート判定。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズ再チェック（Gzip bomb 対策）。
    - トラッキングパラメータ（utm_* 等）の除去と URL 正規化を行い、記事ID を正規化 URL の SHA-256（先頭32文字）で生成して冪等性を保証。
  - フィード取得とパース:
    - fetch_rss にてフィード取得、content:encoded 優先の本文抽出、pubDate の RFC2822 パース（失敗時は警告して現在時刻で代替）。
    - テキスト前処理（URL 除去・空白正規化）を実装。
  - DuckDB への保存:
    - save_raw_news はチャンク化して INSERT ... RETURNING により実際に挿入された記事IDを返す。1 トランザクションで実行しロールバック処理を備える。
    - save_news_symbols / _save_news_symbols_bulk は news_symbols テーブルへの紐付けをバルク挿入し、ON CONFLICT DO NOTHING を使用して重複を排除。RETURNING により挿入数を正確に返却。
  - 銘柄抽出ロジック: 4桁数字パターンを検出し、与えられた known_codes セットに含まれるもののみ返す。

- DuckDB スキーマ / 初期化（kabusys.data.schema）
  - DataSchema.md に基づく 3 層（Raw / Processed / Feature）＋Execution 層のテーブル定義を実装。
  - raw_prices, raw_financials, raw_news, raw_executions 等の Raw 層、prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の Processed 層、features, ai_scores の Feature 層、signals, signal_queue, orders, trades, positions, portfolio_performance 等の Execution 層を定義。
  - 各テーブルに対して制約（PRIMARY KEY, CHECK, FOREIGN KEY 等）を付与。一般的なクエリ向けに複数のインデックスを追加。
  - init_schema(db_path) によりディレクトリ作成・DDL 実行を行い、冪等にスキーマ初期化を実施。get_connection は既存 DB へ接続するユーティリティを提供。

- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新を行う ETL の構成要素を実装（差分算出、backfill による後出し修正吸収、保存、品質チェック連携）。
  - ETLResult データクラスを追加し、取得数・保存数・品質問題一覧・エラーメッセージ等をまとめて返却可能。
  - 市場カレンダー調整ヘルパー（_adjust_to_trading_day）とテーブル最終日取得ユーティリティ（get_last_price_date, get_last_financial_date, get_last_calendar_date）を実装。
  - run_prices_etl の骨子を実装（差分日付算出、fetch -> save の流れ）。backfill_days デフォルトは 3 日。

Changed
- （初期リリースのため該当なし）

Fixed
- （初期リリースのため該当なし）

Security
- RSS/XML 周りと外部 URL 取得に対する複数のセーフガードを導入（defusedxml、SSRF リダイレクト検査、プライベート IP チェック、最大読み取りバイト数制限、gzip 解凍後のサイズ検査）。
- .env 自動読み込みは OS 環境変数を保護するために保護リストを用いる実装。

Notes / Implementation details
- API 呼び出しは urllib.request ベースで実装されており、トークンのキャッシュと自動リフレッシュによりページネーション時の効率化を図っている。
- DuckDB とのやり取りは直接 SQL 文を用い、ON CONFLICT 句や INSERT ... RETURNING を活用して冪等性と正確な挿入把握を行う。
- 日付/時刻は取得時に fetched_at を UTC で記録する設計（Look-ahead bias 対策）。
- 一部のネットワーク/ファイル操作はテスト時に差し替え可能（例: news_collector._urlopen をモック可能）。

今後
- strategy, execution, monitoring の各モジュールの実装・テスト追加。
- 品質チェックモジュール（kabusys.data.quality）との連携を深める。
- 追加データソースやフィードの拡充、API エンドポイントの拡張。

---

（参考）主要ファイル一覧:
- src/kabusys/__init__.py
- src/kabusys/config.py
- src/kabusys/data/jquants_client.py
- src/kabusys/data/news_collector.py
- src/kabusys/data/schema.py
- src/kabusys/data/pipeline.py
- （空のパッケージプレースホルダ） src/kabusys/data/__init__.py, src/kabusys/execution/__init__.py, src/kabusys/strategy/__init__.py

以上。