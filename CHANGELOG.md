CHANGELOG
=========

すべての注目すべき変更をこのファイルに記録します。  
形式は「Keep a Changelog」に準拠します。

未リリースの変更点は Unreleased に記載します。

Unreleased
----------

- なし

[0.1.0] - 2026-03-17
--------------------

初回リリース (初版)。日本株自動売買システム「KabuSys」の基盤機能を実装しました。主にデータ取得・保存・ETL・ニュース収集・設定管理・データスキーマ周りの実装を含みます。

Added
- パッケージ公開情報
  - パッケージルート: kabusys、バージョン 0.1.0 を設定。
- 環境設定管理 (kabusys.config)
  - .env ファイルまたは環境変数からの設定読み込み機能を実装。
  - プロジェクトルート（.git または pyproject.toml）を起点に .env/.env.local を自動ロード（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
  - export プレフィックス、クォート値、インラインコメント等に対応した .env 行パーサ実装。
  - 必須設定取得用の _require() と Settings クラスを実装（J-Quants・kabu API・Slack・DB パス・環境モード・ログレベル等）。
  - KABUSYS_ENV と LOG_LEVEL の検証（有効値チェック）と convenience プロパティ（is_live, is_paper, is_dev）。
- J-Quants API クライアント (kabusys.data.jquants_client)
  - 日足（OHLCV）、財務（四半期 BS/PL）、マーケットカレンダー取得用の fetch_*/pagination 対応関数を実装。
  - API 利用のための HTTP ユーティリティと JSON デコード処理。
  - レート制限（120 req/min）を守る固定間隔スロットリング（RateLimiter）。
  - 再試行ロジック（指数バックオフ、最大 3 回。408/429/5xx を再試行対象）。
  - 401 を検出した場合はリフレッシュトークンで id_token を自動リフレッシュして 1 回だけリトライする仕組み。
  - id_token キャッシュをモジュールレベルで保持（ページネーション間で共有）。
  - DuckDB へ保存する save_* 関数は冪等性を確保（ON CONFLICT DO UPDATE）。
  - 保存時に fetched_at を UTC フォーマットで記録。
  - 安全な型変換ユーティリティ (_to_float, _to_int) を追加。
- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードから記事を取得し raw_news テーブルへ保存する機能。
  - defusedxml による安全な XML パース、gzip 解凍、最大応答サイズ制限（10 MB）による DoS 対策。
  - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント除去）と記事ID を SHA-256（先頭32文字）で生成して冪等性を確保。
  - SSRF 対策：URL スキーム検証、ホストのプライベートアドレス検査、リダイレクト時の事前検証ハンドラ（_SSRFBlockRedirectHandler）。
  - レスポンスチャンク読み込み後のサイズ検査、gzip 解凍後のサイズ検査（Gzip bomb 対策）。
  - テキスト前処理（URL 除去、空白正規化）。
  - DuckDB への保存はチャンク化した INSERT ... RETURNING を用い、トランザクションで一括挿入（save_raw_news, save_news_symbols, _save_news_symbols_bulk）。
  - 銘柄コード抽出ユーティリティ（4桁コード）と run_news_collection による統合ジョブ。既知銘柄セットを使った紐付け処理をサポート。
  - HTTP ユーザーエージェントを "KabuSys-NewsCollector/1.0" に設定。
  - テスト容易性のため _urlopen をモック可能に設計。
- DuckDB スキーマ (kabusys.data.schema)
  - Data Platform 設計に基づく 3 層（Raw / Processed / Feature）および Execution 層のテーブルを定義する DDL を実装。
  - raw_prices, raw_financials, raw_news, raw_executions を含む Raw 層。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols を含む Processed 層。
  - features, ai_scores を含む Feature 層。
  - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance を含む Execution 層。
  - 性能を想定したインデックス定義を追加（頻繁な検索パターンに対応）。
  - init_schema(db_path) によりディレクトリ自動作成と DDL 実行を行い、冪等にスキーマを初期化。
  - get_connection(db_path) で既存 DB への接続を取得。
- ETL パイプライン (kabusys.data.pipeline)
  - 差分更新（最終取得日からの差分取得）を行う ETL フレームワークの骨組みを実装。
  - ETLResult データクラス（取得・保存件数、品質問題・エラーの収集、has_errors / has_quality_errors 等）を実装。
  - 差分取得のためのヘルパー（テーブル存在チェック、最大日付取得、営業日調整）を実装。
  - run_prices_etl を実装（差分ロジック、バックフィル days のサポート、J-Quants からの取得と保存の連携）。
  - 設計方針としてバックフィルデフォルト 3 日、カレンダー先読み 90 日を採用。
- その他
  - 型ヒント、詳細な docstring とログ出力を多用し可観測性とメンテナンス性を向上。
  - テスト性を考慮した設計（外部呼び出しの注入やモック可能な内部関数）。

Security
- RSS/XML 関連の脆弱性対策を多層で実装
  - defusedxml による XML パース（XML Bomb 対策）
  - レスポンスサイズ制限（MAX_RESPONSE_BYTES）と gzip 解凍後サイズ検査
  - SSRF 対策（スキーム検証、プライベートアドレス検査、リダイレクト時の検証）
  - 外部 URL のスキーム制限（http/https のみ）
- .env の読み込みで OS 環境変数（protected）を上書かない安全設計
- J-Quants のトークンリフレッシュは allow_refresh フラグで無限再帰を回避

Changed
- 初版のため該当なし

Fixed
- 初版のため該当なし

Known issues / Notes
- run_prices_etl の戻り値箇所が未完（コード末尾が不完全に見える）。現状のままだと呼び出し元で期待するタプル (fetched_count, saved_count) を常に返さない可能性があるため注意が必要。リリース後に修正が必要。
- モジュールレベルの id_token キャッシュ（_ID_TOKEN_CACHE）はプロセス単位のキャッシュで、マルチスレッド/マルチプロセス環境での競合や最新性の担保については追加検討が必要。
- RateLimiter はプロセス内単純スロットリング（固定間隔）で、より高度なトークンバケットや分散レートリミッティングが必要な場合は拡張が必要。
- DuckDB の INSERT 文ではプレースホルダを文字列連結で作成している場所があり（多件挿入のための動的構築）、非常に大きなチャンクを扱うと SQL 文長やパラメータ数の上限に達する可能性がある。既定でチャンクサイズを設定しているが、大規模環境では監視が必要。
- news_collector の _is_private_host は DNS 解決失敗時に安全側（非プライベート）とみなしている箇所がある。極めて保守的な設定を望む場合は振る舞いを変更する必要がある。

Development / Testing notes
- テストでは kabusys.data.news_collector._urlopen や jquants_client の id_token 注入機能を利用して外部ネットワークコールをモック可能。
- .env の自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できるため、CI やユニットテストでの環境分離が容易。

ライセンス
- 本リリースに含まれるコードはリポジトリの LICENSE に従います（リポジトリに LICENSE が存在する前提の記述）。

---

注: 上記は提供されたソースコードの内容から推測して作成した CHANGELOG です。使用中に発見されたバグや仕様変更は、以降のリリースで適宜更新してください。