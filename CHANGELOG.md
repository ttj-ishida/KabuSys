CHANGELOG
=========

すべての重要な変更はここに記録します。  
このファイルは「Keep a Changelog」準拠の形式で書かれています。  

フォーマット:
- 変更はリリース（バージョン）単位で記載
- カテゴリ: Added / Changed / Fixed / Security / その他

[Unreleased]
------------

- （なし）

0.1.0 - 初回リリース
--------------------

リリース概要:
- 日本株自動売買システム「KabuSys」の初期実装を追加。
- データ取得、データベーススキーマ、RSS ニュース収集、環境設定管理、そして簡易 ETL パイプラインなどの基盤機能を提供。

Added
- パッケージ基盤
  - kabusys パッケージおよびサブパッケージを追加（data, strategy, execution, monitoring を公開）。
  - __version__ を "0.1.0" に設定。

- 環境設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む自動ロード実装。
  - プロジェクトルート検出ロジック（.git または pyproject.toml を探索）により CWD に依存しない読み込みを実現。
  - .env と .env.local のロード順（OS 環境変数 > .env.local > .env）と上書き制御を実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプションを追加（テスト用）。
  - .env 行パーサ（export 句、クォート、コメント、エスケープ対応）を実装。
  - Settings クラスを提供し、J-Quants や kabuAPI、Slack、DB パス、環境モード（development/paper_trading/live）およびログレベルの検証付きプロパティを実装。
  - 必須環境変数未設定時は明示的に ValueError を送出。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - API の取得/認証ロジックを実装（/token/auth_refresh による id_token 取得）。
  - レート制限（120 req/min）を守る固定間隔スロットリング実装（_RateLimiter）。
  - リトライと指数バックオフ（最大 3 回、408/429/5xx を対象）を実装。429 の場合は Retry-After ヘッダ考慮。
  - 401 受信時の自動トークンリフレッシュ（1 回のみ）を実装し、ページネーション間でのトークンキャッシュを保持。
  - 日足・財務・マーケットカレンダーのページネーション対応フェッチ関数を実装（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）を行う save_* 関数を実装（save_daily_quotes, save_financial_statements, save_market_calendar）。
  - データ整形ユーティリティ（_to_float, _to_int）を実装。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードからの記事取得・前処理・DB 保存のフルフローを実装。
  - URL 正規化（トラッキングパラメータ削除、クエリソート、フラグメント除去）と記事 ID を SHA-256（先頭32文字）で生成して冪等性を担保。
  - defusedxml を使った XML パース（XML Bomb 等への耐性）。
  - SSRF 対策: URL スキーム検証（http/https のみ）、ホストのプライベートアドレス判定、リダイレクト時の検査を行うカスタムリダイレクトハンドラを実装。
  - レスポンスサイズ制限（MAX_RESPONSE_BYTES=10MB）、gzip 解凍後のサイズ検査、Content-Length の事前チェックを実装。
  - テキスト前処理（URL 除去、空白正規化）。
  - DB 保存はトランザクションでまとめ、チャンク化して INSERT ... RETURNING を使い新規挿入 ID を返す（save_raw_news, save_news_symbols, _save_news_symbols_bulk）。
  - 記事中の銘柄コード抽出機能（4桁数字候補の known_codes フィルタ）を実装。
  - run_news_collection により複数 RSS ソースの独立処理、失敗時の個別スキップ、銘柄紐付けの一括保存を提供。

- DuckDB スキーマ定義・初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution の 3 層（＋Execution）構造のテーブル DDL を定義。
  - 各テーブルに対する制約（PRIMARY KEY, CHECK, FOREIGN KEY）を設定。
  - パフォーマンスを考慮したインデックス定義を追加。
  - init_schema(db_path) によりファイルパスの親ディレクトリ自動作成と DDL 実行を行い、DuckDB 接続を返す。get_connection() を提供。

- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新（最終取得日を基に date_from を自動算出）、backfill_days（デフォルト 3 日）による後出し修正吸収ロジックを実装。
  - 市場カレンダー先読み（_CALENDAR_LOOKAHEAD_DAYS）や最小データ日付定義。
  - ETLResult dataclass により ETL 実行結果（取得数、保存数、品質チェック結果、エラー一覧）を構造化して返す仕組みを実装。
  - テーブル存在チェック、最大日付取得ユーティリティ、営業日調整ヘルパーを実装。
  - run_prices_etl により差分取得→保存のワークフロー（取得→jq.save_daily_quotes）を提供。

- ロギングと可観測性
  - 各主要処理に logger.info/warning/exception の記録を追加し、運用時のトラブルシュートを容易に。

Security
- 認証・トークン処理
  - id_token 自動リフレッシュとキャッシュによりトークン漏洩や無限再帰を防止する設計。
- RSS / HTTP セキュリティ対策
  - defusedxml を用いた XML パース。
  - SSRF 対策（スキーム検証、プライベートホスト拒否、リダイレクト時検査）。
  - レスポンスサイズ制限（最大 10MB）と gzip 解凍後のサイズ検査でメモリ DoS を緩和。
- DB 操作
  - トランザクションを明示的に使用し、失敗時はロールバックして整合性を保つ。

Notes / Known limitations
- SQL 組立時にチャンクプレースホルダを文字列結合で生成している箇所があり、非常に大量の列数・長さのケースでは SQL 長制限に注意（チャンクサイズは _INSERT_CHUNK_SIZE で制御）。
- run_prices_etl など ETL の一部関数は外部の quality モジュールと連携する設計で、品質チェックのポリシー次第で挙動が変わります（品質問題は ETL を即時中止せず呼び出し元で判断する方針）。
- 外部ネットワーク依存の処理（J-Quants, RSS）では外部 API の仕様変更が影響する可能性あり。

アップグレード手順
- 初回利用前に init_schema() を呼んで DuckDB スキーマを作成してください。
- 必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）を .env に設定するか環境変数を設定してください。

謝辞
- このリリースではデータ取得と保存の基盤機能、セキュリティ対策、ETL の基礎を実装しました。今後は戦略ロジック（strategy）、発注/実行層（execution）、監視（monitoring）を充実させていく予定です。