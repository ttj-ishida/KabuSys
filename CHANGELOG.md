# Changelog

すべての注記はソースコードから推測して作成しています。

このファイルは Keep a Changelog の形式に準拠しています。  
※バージョンはパッケージの __version__（0.1.0）に基づきます。

## [Unreleased]

## [0.1.0] - 2026-03-17
初回リリース。日本株自動売買プラットフォームのコア機能群を実装・統合しました。主な追加点は以下のとおりです。

### Added
- 全体
  - パッケージ `kabusys` の初期構成を追加（__version__ = "0.1.0"、公開モジュール: data, strategy, execution, monitoring）。
  - 型アノテーションと logging を積極的に利用した実装。

- 設定 / 環境変数管理（kabusys.config）
  - .env ファイルまたは OS 環境変数から設定を読み込む自動ロード機能を実装。プロジェクトルートは .git または pyproject.toml を基準に探索。
  - 読み込み優先度: OS 環境変数 > .env.local > .env。環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効にできる（テスト向け）。
  - .env パーサーで以下をサポート:
    - コメント行・空行のスキップ、`export KEY=val` 形式、
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理、
    - クォートなし値での行内コメント扱い（直前がスペース/タブの場合）。
  - Settings クラスを提供し、必須項目（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）を取得。値検証:
    - KABUSYS_ENV は "development" / "paper_trading" / "live" のみ許容。
    - LOG_LEVEL は DEBUG/INFO/WARNING/ERROR/CRITICAL のみ許容。
  - データベースファイルパスのデフォルト（DuckDB/SQLite）を設定。

- データ取得クライアント（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装（株価日足、財務データ、マーケットカレンダーを取得）。
  - レート制御: 固定間隔スロットリングで 120 req/min を遵守する RateLimiter を実装。
  - リトライ/バックオフ: 指数バックオフ（最大 3 回）、HTTP 408/429/5xx を対象。429 の場合は Retry-After ヘッダを尊重。
  - 認証トークン管理:
    - refresh token から id token を取得する get_id_token().
    - モジュールレベルの id token キャッシュを保持し、401 を受けた場合は一度トークンをリフレッシュして再試行。
  - ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
  - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）:
    - 挿入は冪等（ON CONFLICT DO UPDATE / DO NOTHING）で重複を排除。
    - fetched_at（UTC）を記録してデータ取得時刻をトレース可能に。
  - 値変換ユーティリティ (_to_float, _to_int) を実装し、不正値や小数切り捨て問題に配慮。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードからの記事収集モジュールを実装（デフォルトで Yahoo Finance のビジネスカテゴリ RSS を登録）。
  - セキュリティ対策:
    - defusedxml による XML パース（XML Bomb 等への耐性）、
    - URL スキーム検証（http/https のみ許可）とリダイレクト時の検査（カスタム RedirectHandler）で SSRF を防止、
    - ホスト/IP のプライベートアドレス検査（直接 IP と DNS 解決の両方を判定）、
    - レスポンス読み取りは最大 10MB に制限（受信サイズ・gzip 解凍後のサイズも検査）。
  - URL 正規化とトラッキングパラメータ除去（utm_*, fbclid, gclid 等）を実装し、正規化した URL の SHA-256（先頭32文字）を記事IDとして生成し冪等性を確保。
  - テキスト前処理（URL 除去、空白正規化）を実装。
  - DB 保存:
    - raw_news へのチャンク単位挿入（INSERT ... ON CONFLICT DO NOTHING RETURNING id）で実際に挿入された ID を返す設計、
    - news_symbols（記事 ↔ 銘柄コード紐付け）をチャンク挿入で保存、重複排除、トランザクションでロールバック対応。
  - 銘柄コード抽出 (extract_stock_codes): 正規表現で 4 桁数字を抽出し、与えられた known_codes のみを返却。
  - run_news_collection: 複数 RSS ソースを順次取得し、個々のソースごとにエラーハンドリングを行いながら raw_news 保存と銘柄紐付けを実行。結果を {source: saved_count} の辞書で返す。

- スキーマ / DB 初期化（kabusys.data.schema）
  - DuckDB 向けに3層（Raw / Processed / Feature）＋Execution 関連のテーブル定義を追加。
  - raw_prices, raw_financials, raw_news, raw_executions をはじめ、prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance などを定義。
  - 各テーブルに適切な制約（PRIMARY KEY / CHECK / FOREIGN KEY）とインデックスを設定。
  - init_schema(db_path) でディレクトリ作成→全DDL実行→インデックス作成を行う冪等な初期化処理を提供。
  - get_connection(db_path) で既存 DB への接続を返す（スキーマ初期化は行わない）。

- ETL パイプライン（kabusys.data.pipeline）
  - ETL の設計方針に沿った pipeline モジュールを実装（差分更新、バックフィル、品質チェックの統合）。
  - ETLResult dataclass を追加し、ETL 実行結果・品質問題・エラー等を構造化して返す（to_dict メソッドで品質問題をタプル化）。
  - 市場カレンダー補助: 非営業日の調整ロジック（_adjust_to_trading_day）を実装。
  - 差分取得のヘルパー（get_last_price_date, get_last_financial_date, get_last_calendar_date）を実装。
  - run_prices_etl を実装（差分算出、backfill_days による再取得、jquants_client 経由の取得と save 呼び出し）。バックフィルデフォルトは 3 日。最小データ日付は 2017-01-01、カレンダー先読みは 90 日などの定数を定義。
  - 品質チェック（quality モジュール）との連携を想定（重大度の扱い等を定義）。

### Security
- 環境変数の取り扱いで OS 環境を保護する protected set を採用（.env 上書き時に保護）。
- NewsCollector 側で SSRF 対策、受信サイズ制限、defusedxml 使用など多数の防御策を実装。
- J-Quants クライアントで 401 発生時にのみトークンリフレッシュし、無限再帰を回避（allow_refresh フラグ）。

### Performance / Reliability
- API 呼び出しに対しレート制限・リトライ・トークンキャッシュを実装し安定性を確保。
- DuckDB 側はバルク挿入・チャンク処理・トランザクションを利用しオーバーヘッドを削減。
- データ保存は冪等（ON CONFLICT）で再実行耐性あり。

### Notes / Limitations（コードから推測）
- pipeline.run_prices_etl の末尾が途中で切れている/ファイルが途中で終わっているように見える箇所があり、完全な戻り値のシグネチャや他の ETL ジョブ（financials, calendar）の完全実装は未確認。
- strategy / execution / monitoring パッケージの __init__.py は空であり、個別戦略や発注ロジックは別途実装が必要。
- quality モジュールは pipeline から参照されているが、この差分での実装は含まれていない可能性がある（別ファイルにある想定）。

### Fixed
- （初版のため特に無し）

---

参考: 実装ファイル
- src/kabusys/config.py
- src/kabusys/data/jquants_client.py
- src/kabusys/data/news_collector.py
- src/kabusys/data/schema.py
- src/kabusys/data/pipeline.py

もしリリースノートをより詳細（各関数の例、注意事項、移行ガイド、既知の問題一覧）にしたい場合は、対象読者（開発者/運用者/エンドユーザー）を指定していただければ、追記します。