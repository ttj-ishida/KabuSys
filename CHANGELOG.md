Keep a Changelog
=================

すべての重要な変更点をこのファイルで管理します。  
フォーマットは「Keep a Changelog」に準拠しています。

Unreleased
----------

- （未リリースの変更はここに記載）

0.1.0 - 2026-03-17
------------------

初回リリース。日本株自動売買システムの基盤となる以下のモジュール群と機能を実装しています。

Added
- パッケージ基礎
  - kabusys パッケージ初期化（src/kabusys/__init__.py、バージョン 0.1.0）。
  - public API として data, strategy, execution, monitoring をエクスポート。

- 設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。プロジェクトルート検出は .git または pyproject.toml を基準に行うため、CWD に依存しない。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサ実装: export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメント処理に対応。
  - Settings クラスを提供（J-Quants トークン、kabu API、Slack、DB パス、環境モード、ログレベル判定等）。
  - 環境値バリデーション（KABUSYS_ENV と LOG_LEVEL の許容値チェック）と必須変数取得時の例外処理。

- J-Quants データクライアント（src/kabusys/data/jquants_client.py）
  - API クライアントを実装。株価日足（OHLCV）、四半期財務データ、マーケットカレンダーの取得をサポート。
  - レート制限（120 req/min）を守る固定間隔スロットリング（RateLimiter）を実装。
  - リトライ戦略（指数バックオフ、最大 3 回、408/429/5xx を対象）を実装。429 の場合は Retry-After を優先。
  - 401 応答時は ID トークンを自動リフレッシュして 1 回リトライする仕組みを実装（無限再帰を回避）。
  - トークンのモジュールレベルキャッシュ（ページネーション時に共有）。
  - ページネーション対応（pagination_key を使った繰り返し取得）。
  - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装し、ON CONFLICT ... DO UPDATE により冪等性を確保。
  - データ整形ユーティリティ (_to_float / _to_int) を実装し、型変換と不正値対策を実装。
  - fetched_at を UTC で記録し、Look-ahead Bias のトレースを可能に。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードから記事を取得して raw_news に保存する収集パイプラインを実装。
  - 記事 ID は URL 正規化後の SHA-256（先頭32文字）で生成し、トラッキングパラメータ（utm_ 等）を削除して冪等性を担保。
  - defusedxml を利用し XML Bom 等の攻撃対策を実装。
  - SSRF 対策:
    - fetch 前のホスト検査（プライベート/ループバック/リンクローカルの拒否）。
    - リダイレクト時にスキーム・ホストを検査するカスタム RedirectHandler を導入。
    - 許可スキームは http/https のみ。
  - レスポンスの最大受信サイズを MAX_RESPONSE_BYTES（10 MB）で制限し、gzip 解凍後にもサイズを検査（Gzip bomb 対策）。
  - テキスト前処理（URL 除去、空白正規化）、RFC2822 形式の pubDate パース（UTC 揃え、パース失敗時は警告ログと現在時刻で代替）。
  - DB 保存はバルク挿入とトランザクションで効率化（INSERT ... RETURNING を利用して実際に挿入された ID を返す）。
  - 銘柄コード抽出機能（4桁数字、known_codes に基づくフィルタ）と一括紐付け保存機能を実装。
  - デフォルト RSS ソースに Yahoo Finance Business カテゴリを追加。

- DuckDB スキーマ定義と初期化（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution 層のテーブルを DataSchema.md に基づき定義。
  - raw_prices, raw_financials, raw_news, raw_executions を含む Raw レイヤー。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols を含む Processed レイヤー。
  - features, ai_scores を含む Feature レイヤー。
  - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance を含む Execution レイヤー。
  - インデックス定義（頻出クエリ向け）を追加。
  - init_schema(db_path) により必要ディレクトリ作成→接続→DDL/インデックス実行を行う冪等な初期化を実装。get_connection() も提供。

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - 差分更新を行う ETL 基盤を実装（差分算出、バックフィルの考慮、品質チェックフック等の設計）。
  - ETLResult データクラスを実装し、品質問題リストやエラー一覧を保持、辞書化メソッドを提供。
  - raw テーブルの最終取得日取得ユーティリティ（get_last_price_date 等）を実装。
  - 市場カレンダー未取得時のフォールバック処理や営業日調整関数を実装（_adjust_to_trading_day）。
  - run_prices_etl を実装（差分算出、backfill_days による再取得、J-Quants からの取得→保存フロー）。

Security
- 環境変数読み込みでは OS 環境変数を保護する仕組み（protected set）を導入し、.env による上書きを制御可能。
- news_collector での SSRF 対策、defusedxml の利用、応答サイズ制限、gzip 解凍後の再チェックなど、外部データ取り込みにおける安全性を考慮。
- jquants_client の HTTP エラーハンドリングはリトライとトークンリフレッシュで堅牢化。

Notes / Usage
- 環境変数:
  - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（Settings により取得時に例外）。
  - DB デフォルト: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"。
  - 自動 .env ロードの無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
- J-Quants API は 120 req/min の制限を守る必要があり、クライアント側でスロットリング済み。
- DuckDB スキーマは init_schema() により初期化すること。get_connection() は既存 DB 接続用。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Acknowledgements / Design decisions
- API 呼び出しや外部データ取り込みに関する「冪等性」「Look-ahead Bias の追跡」「セキュリティ（SSRF / XML Bomb）」「効率的なバルク挿入」の確保を優先して設計しています。

今後
- pipeline モジュールの ETL ジョブ拡張（財務データ・カレンダーの差分 ETL の実装）、品質チェックルール実装、モニタリング / execution 層の実振る舞い（API 発注・約定連携）を予定しています。