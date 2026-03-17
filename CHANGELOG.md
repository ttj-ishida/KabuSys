CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

Unreleased
----------

- なし

[0.1.0] - 2026-03-17
--------------------

Added
- 初回リリース: KabuSys 日本株自動売買システムの基盤機能を追加。
- パッケージ基礎
  - src/kabusys/__init__.py: パッケージ化、バージョンを 0.1.0 に設定。公開サブパッケージを __all__ に指定。
- 設定／環境変数管理（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を自動ロード。読み込み優先順位は OS 環境変数 > .env.local > .env。
  - プロジェクトルート検出は __file__ を起点に .git または pyproject.toml を探索して行うため、CWD に依存しない実装。
  - .env パーサの強化: export 句対応、シングル/ダブルクォート内のエスケープ処理、インラインコメント対応など。
  - 自動ロードを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数に対応。
  - Settings クラスを公開。必須項目取得時は未設定で ValueError を送出。環境（development/paper_trading/live）とログレベル値のバリデーションを実装。
  - DB パス（DuckDB/SQLite）のデフォルト値を提供。

- J-Quants クライアント（src/kabusys/data/jquants_client.py）
  - 日足（OHLCV）、四半期財務データ、マーケットカレンダー取得用 API クライアント実装。
  - API レート制御: 固定間隔スロットリングによる RateLimiter（120 req/min）。
  - リトライロジック: 指数バックオフ（最大 3 回）、HTTP 408/429/5xx の再試行処理。
  - 401 Unauthorized を検出した場合はリフレッシュトークンで ID トークンを自動再取得して再試行（1 回のみ）。
  - ページネーション対応（pagination_key を用いた取得ループ）。
  - モジュールレベルで ID トークンをキャッシュし、ページネーション間で共有。
  - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）は冪等性を確保（ON CONFLICT DO UPDATE）し、fetched_at を UTC で記録して「いつデータを知ったか」を追跡可能に。
  - 値変換ユーティリティ(_to_float/_to_int) により入力データの堅牢な正規化を提供。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードからの記事収集と DuckDB への保存処理を実装。
  - セキュリティ対策:
    - defusedxml を用いた XML パース（XML Bomb 等への対策）。
    - SSRF 対策: URL スキーム検証（http/https のみ許可）、ホスト/リダイレクト先がプライベートアドレスでないかのチェック、リダイレクト時にも検証を行うカスタム HTTPRedirectHandler。
    - レスポンス受信サイズ上限（10 MB）設定と超過チェック、gzip 解凍後の再検査（Gzip bomb 対策）。
  - URL 正規化とトラッキングパラメータ除去（utm_*, fbclid 等）を実装し、その正規化 URL から SHA-256（先頭32文字）で記事 ID を生成して冪等性を保証。
  - テキスト前処理（URL 除去、空白正規化）。
  - DuckDB への一括挿入はチャンク化しトランザクションでまとめて実行。INSERT ... RETURNING を利用して実際に挿入された記事 ID を返す実装。
  - 銘柄抽出ロジック: 4桁数字パターンを抽出し、与えられた known_codes に含まれるものを紐付ける。news_symbols の一括保存（重複除去、チャンク挿入）を実装。
  - デフォルト RSS ソースに Yahoo Finance のビジネスカテゴリを設定（DEFAULT_RSS_SOURCES）。

- DuckDB スキーマ管理（src/kabusys/data/schema.py）
  - DataSchema.md に基づくスキーマ定義を追加（Raw / Processed / Feature / Execution 層）。
  - テーブルには適切な型チェック制約（CHECK）や PRIMARY KEY、外部キーを設定。
  - 利便性のためのインデックス定義を追加（頻出クエリ向け）。
  - init_schema(db_path) でディレクトリ作成→全 DDL とインデックスを実行する初期化機能。init_schema は冪等（既存オブジェクトはスキップ）。
  - get_connection(db_path) で既存 DB への接続を取得（スキーマ初期化は行わない）。

- ETL / パイプライン（src/kabusys/data/pipeline.py）
  - ETLResult データクラスを追加し、ETL 実行結果・品質問題・エラーメッセージを構造化して返却。
  - 差分更新用ユーティリティ: テーブル存在確認、最大日付取得、営業日への調整ロジック（market_calendar に基づく）を実装。
  - get_last_price_date / get_last_financial_date / get_last_calendar_date を提供。
  - run_prices_etl を実装（差分算出、backfill により最終取得日の数日前から再取得、J-Quants からの取得→保存）。品質チェックモジュールとの連携を想定。
  - ETL の設計方針として、Fail-Fast を避ける（品質エラーがあっても処理を継続し、呼び出し側で判断できるようにする）。

Security
- ニュース取得部分で SSRF や XML 注入、巨大レスポンスに対する複数の防御を実装。
- .env 読み込み時の権限保護（OS 環境変数を保護する protected 機構）。

Changed
- 新規リリースのため該当なし。

Fixed
- 新規リリースのため該当なし。

Known issues / Notes
- run_prices_etl の戻り値に関する不整合:
  - 実装の末尾が現在のコードでは "return len(records)," のように見え、ETLResult の想定する (fetched, saved) タプルが正しく返っていない可能性があります。次リリースで戻り値を (取得レコード数, 保存レコード数) に合わせて修正予定です。
- pipeline モジュールは品質チェック (kabusys.data.quality) に依存していますが、quality モジュールの具象実装はリポジトリ外（または別途実装が必要）である点に注意してください。
- NewsCollector の URL 正規化や 4 桁抽出ルールは一般的な日本株向けルールに基づくため、個別のニュースソースの特殊ケースで調整が必要になる場合があります。

備考（開発者向け）
- 設定の自動ロードをテスト等で抑制したい場合は、環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants の API レート制限や 401 自動リフレッシュの挙動はモジュールレベルで実装されているため、テスト時は get_id_token や _urlopen をモックして注入テストを行うことを推奨します。
- DuckDB の初期化は init_schema を呼ぶことで行います。既存 DB を操作する場合は get_connection を利用してください。

--- End of CHANGELOG ---