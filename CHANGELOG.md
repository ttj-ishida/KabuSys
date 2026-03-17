# CHANGELOG

すべての注目すべき変更点は Keep a Changelog の形式に従って記載します。  
初回リリース 0.1.0 の内容は、コードベースから推測できる実装済み機能・設計方針・セキュリティ対策をまとめたものです。

全般的な注意
- 本ログはソースコードから推測して作成しています。実際の動作や将来の実装差分はコードやドキュメントを参照してください。

## [0.1.0] - 2026-03-17

### 追加
- パッケージの初期公開
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - パッケージエントリでの公開モジュール: data, strategy, execution, monitoring

- 環境設定管理 (kabusys.config)
  - .env / .env.local ファイルまたは環境変数から設定値を自動読み込みする仕組みを追加（ただし環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード無効化可能）。
  - プロジェクトルート検出ロジック: __file__ を起点に .git または pyproject.toml を探索してプロジェクトルートを特定（CWD に依存しない実装）。
  - .env パーサー実装:
    - export KEY=val 形式対応
    - シングル/ダブルクォート内のエスケープ処理対応
    - インラインコメントの取り扱い（クォート有無で挙動を分離）
  - Settings クラスを公開:
    - J-Quants / kabuステーション / Slack / データベースパス 等のプロパティを提供
    - 環境値の妥当性チェック（KABUSYS_ENV, LOG_LEVEL の許容値検査）
    - DuckDB/SQLite のデフォルトパス設定（expanduser 対応）
    - is_live / is_paper / is_dev のユーティリティプロパティ

- J-Quants API クライアント (kabusys.data.jquants_client)
  - API ベース URL, レート制限、リトライ、認証更新などを考慮したクライアント実装を追加
  - 機能:
    - get_id_token: リフレッシュトークンからの idToken 取得（POST）
    - fetch_daily_quotes: 株価日足（OHLCV、ページネーション対応）取得
    - fetch_financial_statements: 四半期財務データ取得（ページネーション対応）
    - fetch_market_calendar: JPX マーケットカレンダー取得
  - 実装上の特徴:
    - 固定間隔スロットリングによるレート制限遵守（120 req/min、_RateLimiter）
    - 最大リトライ回数（3回）、指数バックオフ、HTTP 408/429/5xx に対する再試行
    - 401 を受けた場合は自動でトークンをリフレッシュして 1 回リトライ（再帰停止制御あり）
    - id_token のモジュールレベルキャッシュを共有（ページネーション間で再利用）
    - 取得時刻（fetched_at）を UTC で記録して Look-ahead バイアス対策
    - DuckDB へは冪等性を保つ保存（ON CONFLICT DO UPDATE）で保存する save_* 関数を提供
    - 型変換ユーティリティ: _to_float / _to_int（空値・不正値を安全に扱うロジック）

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードからニュースを収集し raw_news に保存し、銘柄紐付けを行う一連の処理を実装
  - 機能:
    - fetch_rss: RSS 取得・XML パース・記事抽出（content:encoded 優先、guid/link のフォールバック）
    - preprocess_text: URL 除去と空白正規化
    - URL 正規化: トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント削除、クエリソート
    - 記事 ID は正規化 URL の SHA-256 の先頭 32 文字で生成（冪等性確保）
    - SSRF 対策:
      - fetch 前にスキーム検査（http/https のみ許可）
      - ホストがプライベート/ループバック/リンクローカルでないことを検証（直接 IP と DNS 解決の両方を判定）
      - リダイレクト時の検査ハンドラ（_SSRFBlockRedirectHandler）を使用してリダイレクト先も検証
    - サイズ・DoS 対策:
      - 受信最大バイト数の制限（MAX_RESPONSE_BYTES = 10 MB）
      - Content-Length の事前チェックと MAX_RESPONSE_BYTES+1 バイト読み取りによる超過検出
      - gzip 圧縮レスポンスの解凍と解凍後サイズ検査（Gzip bomb 対策）
    - XML の安全処理に defusedxml を使用
    - DB 保存:
      - save_raw_news: INSERT ... RETURNING id を使って新規挿入された記事 ID を正確に取得。チャンク/トランザクションにより効率化。
      - save_news_symbols / _save_news_symbols_bulk: news_symbols テーブルへ銘柄紐付けを一括挿入。ON CONFLICT DO NOTHING と INSERT RETURNING により実際に挿入された件数を返す。
    - 銘柄抽出ロジック:
      - 正規表現で 4 桁数字を抽出し、与えられた known_codes のみを採用（重複除去）

- DuckDB スキーマ定義と初期化 (kabusys.data.schema)
  - Raw / Processed / Feature / Execution の 3 層＋実行層に対応したテーブル定義を追加
  - テーブル例:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各カラムに適切な型・制約（PK, CHECK 等）を定義
  - インデックス群を定義（頻出クエリの高速化を想定）
  - init_schema(db_path) を提供してデータベースファイル作成（親ディレクトリ自動作成）＋DDL 実行による初期化を行う
  - get_connection(db_path) で既存 DB へ接続（スキーマ初期化は行わない）

- ETL パイプライン (kabusys.data.pipeline)
  - ETLResult データクラスによる ETL 実行結果の表現（品質問題一覧とエラー一覧を含む）
  - 差分更新を支援するヘルパー関数:
    - get_last_price_date / get_last_financial_date / get_last_calendar_date
    - _get_max_date, _table_exists などの内部ユーティリティ
  - run_prices_etl の差分更新ロジックを実装（最終取得日からの backfill を考慮）:
    - デフォルト backfill_days = 3
    - 最小取得日 _MIN_DATA_DATE = 2017-01-01 を考慮
    - 取得したレコードを jquants_client.save_daily_quotes で冪等的に保存
  - 市場カレンダーの先読み設定: _CALENDAR_LOOKAHEAD_DAYS = 90（設計上の定数として定義）

### 変更
- 初期リリースのため過去バージョンからの差分はありません（新規実装群）。

### パフォーマンス
- API 呼び出しのレート制御とチャンク単位の DB 挿入によりスループットと安定性を改善。
- DuckDB へはバルク挿入とインデックスでクエリ性能を考慮。

### セキュリティ
- RSS/XML パースに defusedxml を使用し XML 関連脆弱性を軽減。
- RSS フェッチで SSRF 対策を複数層で実施（スキーム検査 / ホスト IP 判定 / リダイレクト時検査）。
- 大容量レスポンスや gzip 圧縮を扱う際の上限チェックを導入してメモリ DoS を軽減。
- 環境変数読み込みは OS 環境変数を保護する仕組み（override/protected）を持つ。

### 既知の制約・注意点
- 一部関数・モジュールはテスト用にオーバーライド可能な実装（例: _urlopen のモック化）が想定されているが、テストコードはこのリリースに含まれない。
- ETL の品質チェック（quality モジュール）との連携が設計に記載されているが、quality モジュールの実装詳細は本コード断片からは明示されていない。
- run_prices_etl の戻り値の記載位置でコードが切れている箇所があるため（ファイル末尾の一部断片）、細かな挙動は実装ファイル全体を参照する必要がある。

---

今後のリリース案（例）
- Unreleased:
  - strategy / execution / monitoring モジュールの具現化（発注ロジック、監視、バックテスト機能）
  - quality モジュールの実装と ETL 連携
  - テストカバレッジの拡充、CI/CD の導入
  - ドキュメントの追加（DataPlatform.md, API 使用例, 運用ガイド）

以上。