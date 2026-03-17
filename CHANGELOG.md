CHANGELOG
=========

すべての変更は Keep a Changelog に準拠して記載しています。  
フォーマット: https://keepachangelog.com/ （日本語訳に準拠）

Unreleased
----------

- 注意事項 / 既知の未完了点
  - ETL パイプラインの run_prices_etl 関数が途中で戻り値の記述が切れているため（ソース内の末尾が不完全）、実行時エラーや意図しない挙動になる可能性があります。早期に戻り値の整合性（取得数・保存数のタプルを正しく返す）を修正してください。

[0.1.0] - 2026-03-17
--------------------

Added
- 基本パッケージ構成を追加
  - kabusys パッケージの公開 API を定義（__version__ = "0.1.0", __all__）。
  - 空のサブパッケージプレースホルダ: execution/, strategy/, monitoring/。

- 環境設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルート検出: .git または pyproject.toml を基準に探索（CWD に依存しない）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 による自動読み込み無効化対応。
  - .env パーサを強化:
    - export KEY=val 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応、インラインコメント処理。
  - Settings クラスを提供:
    - J-Quants / kabu API / Slack / DB パス等のプロパティアクセスを提供。
    - KABUSYS_ENV と LOG_LEVEL の入力検証（有効値チェック）とヘルパー is_live/is_paper/is_dev。
    - デフォルトの DuckDB/SQLite パスの提供。

- J-Quants API クライアント (kabusys.data.jquants_client)
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーの取得関数を実装。
  - 設計方針の実装:
    - API レート制限制御: 固定間隔スロットリング（120 req/min）を _RateLimiter で実装。
    - リトライ処理: 指数バックオフ、最大 3 回リトライ（408/429/5xx などを対象）。429 時は Retry-After ヘッダを優先。
    - 401 受信時にリフレッシュ トークンで自動的に 1 回リトライする仕組み。
    - ページネーション対応（pagination_key を用いた反復取得）。
    - 取得時刻（fetched_at）を UTC ISO フォーマットで記録し Look-ahead Bias を緩和。
  - DuckDB への冪等保存関数を実装（ON CONFLICT DO UPDATE を使用）:
    - save_daily_quotes, save_financial_statements, save_market_calendar。
  - 型変換ユーティリティ: _to_float/_to_int（エッジケースに配慮した変換ロジック）。

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィード取得と raw_news への保存を実装。
  - セキュリティ・堅牢性機能:
    - defusedxml を利用した XML パースで XML Bomb 等に対処。
    - SSRF 防止:
      - URL スキーム検証（http/https のみ許可）。
      - ホスト/IP のプライベートアドレス判定（直接 IP・DNS 解決の両方を確認）。
      - リダイレクト時にスキーム/ホストを検査するカスタムハンドラ _SSRFBlockRedirectHandler を実装。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズ検査（Gzip bomb 対策）。
  - 記事ID生成・正規化:
    - URL 正規化（スキーム/ホスト小文字化、トラッキングパラメータ除去、フラグメント除去、クエリソート）。
    - SHA-256 の先頭 32 文字を記事 ID に利用して冪等性を確保。
    - トラッキングパラメータを除去するためのプレフィックスリスト（utm_ 等）。
  - DB 保存パフォーマンス:
    - チャンク化したバルク INSERT（_INSERT_CHUNK_SIZE）、トランザクションでまとめて挿入。
    - INSERT ... RETURNING を使い実際に挿入された id / 件数を正確に返却。
  - 銘柄コード抽出:
    - 正規表現で 4 桁数字を候補抽出し、known_codes に基づきフィルタリング（重複除去）。

- スキーマ定義 (kabusys.data.schema)
  - DuckDB 用の DDL を網羅的に定義（Raw / Processed / Feature / Execution レイヤー）。
  - テーブル定義には型チェック・制約を明示（CHECK / PRIMARY KEY / FOREIGN KEY）。
  - パフォーマンス考慮で頻出クエリ向けインデックスを作成。
  - init_schema(db_path) によるスキーマ初期化関数と get_connection を提供。親ディレクトリの自動作成や :memory: サポートあり。

- ETL パイプライン (kabusys.data.pipeline)
  - 差分更新とバックフィル、品質チェックの方針を実装（設計ドキュメントに沿った実装）。
  - ETLResult データクラスを追加（取得数・保存数・品質問題・エラー情報を保持）。
  - DB の最終取得日取得ヘルパー（get_last_price_date 等）と営業日調整ロジックを提供。
  - run_prices_etl 等の差分 ETL ジョブを実装し、jquants_client を使った取得→保存の流れを構築。

Changed
- （初期リリースのため該当なし）

Fixed
- （初期リリースのため該当なし）

Security
- RSS 収集での SSRF 対策、defusedxml による XML アンセーフ処理防止、レスポンスサイズ制限（DoS 対策）を実装。
- .env の自動読み込みは OS 環境変数を保護する仕組み（protected set）を導入し、重要な既存環境変数が .env によって上書きされないよう配慮。

Notes / Implementation details
- J-Quants クライアントはモジュールレベルで ID トークンをキャッシュし、ページネーション間で共有することで認証コールを節約。
- NewsCollector は article の URL 正規化→ハッシュ化によりトラッキングパラメータの違いによる重複登録を防止。
- DuckDB 側は外部キーやインデックスなどを定義しており、データ整合性と検索性能に配慮。
- run_news_collection は各 RSS ソースごとに独立してエラーハンドリングするため、1 ソース失敗でも他ソースの収集は継続される。

Known issues / TODO
- run_prices_etl の戻り値部分が実装途中のように見える（ソースの最終行が "return len(records), " で終わっている）。ユニットテストで ETLResult の期待値と整合するよう修正が必要。
- 単体テスト・統合テスト・CI 用のテストスイートが含まれていないため、外部 API 呼び出し部分（ネットワーク/認証）や DB 書き込み部分のモック／テスト実装を推奨。

ライセンスや作者情報はパッケージ外部ドキュメント参照。

-- end of changelog --