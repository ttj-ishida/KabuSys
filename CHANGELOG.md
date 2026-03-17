CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠しています。  
現在のリリースバージョンは v0.1.0（パッケージ内 __version__ に準拠）です。

Unreleased
----------
- Known issues / 注意事項
  - run_prices_etl の実装に不備があり、戻り値のタプル (fetched, saved) を返すべき箇所で fetched のみを返している（ファイルの途中で切れている状態）。ETL の呼び出し側で期待する戻り値と異なるため、呼び出し時にエラーや不整合を招く可能性があります。早急に修正が必要です。

0.1.0 - 2026-03-17
------------------

Added
- パッケージ初期実装を追加（kabusys v0.1.0）。
  - パッケージメタ情報: src/kabusys/__init__.py に __version__ = "0.1.0" を定義。
- 環境変数・設定管理モジュールを追加（src/kabusys/config.py）。
  - .env/.env.local を自動読み込みする仕組みを搭載（優先順位: OS 環境 > .env.local > .env）。
  - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト用途など）。
  - .env ファイルの柔軟なパースを実装:
    - export プレフィックス対応、クォート（シングル/ダブル）とバックスラッシュエスケープ対応、インラインコメントの扱い（クォート外のみ）、無効行のスキップ等。
    - OS 環境変数を保護する protected オプション（自動ロード時に既存 OS 環境変数を上書きしない）。
  - 設定アクセス用 Settings クラスを提供（J-Quants、kabu ステーション、Slack、DB パス、環境種別・ログレベルの検証など）。
  - KABUSYS_ENV と LOG_LEVEL の許容値検証を実装（不正値は ValueError）。

- J-Quants API クライアントを追加（src/kabusys/data/jquants_client.py）。
  - データ取得: 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーの取得関数を実装（ページネーション対応）。
  - 認証: refresh token から id_token を取得する get_id_token を実装。モジュール内で id_token をキャッシュしてページネーション間で共有。
  - レート制御: 固定間隔スロットリング（120 req/min）を実装する RateLimiter を内蔵。
  - 再試行ロジック: 指数バックオフ、最大リトライ回数、HTTP 429 の Retry-After ヘッダ優先、408/429/5xx に対するリトライ等を実装。
  - 401 発生時はトークン自動リフレッシュを 1 回行って再試行（無限再帰防止のメカニズムあり）。
  - DuckDB への保存関数を実装（save_daily_quotes / save_financial_statements / save_market_calendar）。
    - 冪等性を確保：INSERT ... ON CONFLICT DO UPDATE を用いて既存レコードを更新。
    - fetched_at に UTC タイムスタンプを記録（Look-ahead Bias 防止のための設計）。
    - 型変換ユーティリティ（_to_float, _to_int）を実装して不正値を安全に扱う。

- ニュース収集モジュールを追加（src/kabusys/data/news_collector.py）。
  - RSS フィード収集・前処理・DuckDB 保存のワークフローを実装。
  - セキュリティ対策:
    - defusedxml を用いた XML パース（XML Bomb 等への防御）。
    - SSRF 対策: リダイレクトを検査するカスタム HTTPRedirectHandler を実装し、スキーム検証・内部プライベートアドレスへのアクセス拒否を行う。
    - URL スキーム検証（http/https のみ）とホストがプライベートかどうかの判定。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES=10MB）によるメモリ DoS と Gzip bomb 対策（圧縮前後ともチェック）。
    - 受信ヘッダの Content-Length を事前検査。
  - 機能:
    - URL 正規化（トラッキングパラメータ削除、クエリソート、フラグメント削除）と記事ID生成（正規化 URL の SHA-256 先頭32文字）。
    - テキスト前処理（URL 除去、空白正規化）。
    - RSS item の優先的処理（content:encoded を description より優先）。
    - DuckDB への保存はトランザクション内でチャンク INSERT を行い、INSERT ... RETURNING により実際に挿入された id のみを返却（冪等、ON CONFLICT DO NOTHING）。
    - ニュース⇔銘柄紐付け: extract_stock_codes により本文から 4桁銘柄コード抽出（known_codes によるフィルタ）、一括保存用の _save_news_symbols_bulk を提供。
    - テスト容易性のため _urlopen を差し替え可能にしてモック化を容易に。

- DuckDB スキーマ定義と初期化モジュールを追加（src/kabusys/data/schema.py）。
  - Raw / Processed / Feature / Execution の各レイヤーに対応したテーブル DDL を定義。
  - テーブルには妥当性チェック（CHECK）、PRIMARY KEY、FOREIGN KEY を設定。
  - 頻出クエリを想定したインデックス群を定義。
  - init_schema(db_path) による初期化関数を提供（親ディレクトリ自動作成、冪等な CREATE TABLE）。
  - get_connection(db_path) による接続取得を提供（スキーマ初期化は行わない）。

- ETL パイプライン基盤を追加（src/kabusys/data/pipeline.py）。
  - ETLResult dataclass を導入して ETL 実行結果（取得数、保存数、品質問題、エラー等）を整理・辞書化できるようにした。
  - 差分更新の補助関数: 最終取得日の取得（get_last_price_date / get_last_financial_date / get_last_calendar_date）、テーブル存在確認、営業日調整ヘルパー（_adjust_to_trading_day）などを実装。
  - run_prices_etl を含む差分ETLジョブ骨格を追加:
    - 差分更新ロジック（最終取得日から backfill_days を遡って再取得）を実装。
    - デフォルトの backfill_days=3、カレンダー先読み 90 日等の設計方針を導入。
    - jquants_client の fetch_* / save_* を用いる設計（外部品質チェックモジュール quality と連携する想定）。
  - 品質チェックは重大エラーがあっても全件収集を続行する設計（Fail-Fast ではない）。

Changed
- （初版のため該当なし）

Fixed
- （初版のため該当なし）

Security
- ニュース収集に関して以下のセキュリティ対策を導入:
  - defusedxml による安全な XML パース
  - SSRF を防ぐリダイレクト検査とプライベートアドレス拒否
  - レスポンスサイズチェックと gzip 解凍後のサイズ検証（Gzip bomb 対策）
  - URL スキーム検証（http/https のみ受け付け）

Removed / Deprecated
- （初版のため該当なし）

Notes / その他
- DB 保存処理は各所で冪等性（ON CONFLICT）を意識した実装になっています。これにより再実行時のデータ重複や不整合を軽減します。
- settings を通じて必要な外部シークレット（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID など）を管理します。未設定時は明示的に例外が送出されます。
- run_news_collection は各 RSS ソースを独立して処理し、1 ソースの失敗が他のソースに影響しない設計です。
- 今後の優先作業:
  - run_prices_etl の戻り値不整合の修正（fetched, saved の正しいタプルを返すように）。
  - pipeline 側で quality モジュールを統合し、実際の品質チェックレポートの採取と ETLResult への反映を行う。
  - strategy / execution パッケージの実装（現状は __init__.py のみで中身は未実装）。

Contributors
- コードベースから自動的に推測して作成した CHANGELOG（実際のコントリビュータ情報はリポジトリのコミット履歴を参照してください）。

--- 

この CHANGELOG はコード内容から推測して作成したため、実際のコミット履歴やリリースノートと差異がある可能性があります。必要であれば、実コミットログやチームのリリースポリシーに合わせて調整してください。