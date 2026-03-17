Keep a Changelog に準拠した CHANGELOG.md を以下に作成しました。リポジトリ内のコードから推測できる機能・設計方針・既知の注意点を記載しています。必要に応じて日付や文言を調整してください。

----------------------------------------------------------------------
Keep a Changelog
All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog and this project adheres to Semantic Versioning.
----------------------------------------------------------------------

## [0.1.0] - 2026-03-17

Added
- 初期リリース。日本株自動売買プラットフォーム "KabuSys" のコアモジュールを追加。
  - パッケージエントリポイント
    - src/kabusys/__init__.py: バージョン情報と公開サブパッケージ (data, strategy, execution, monitoring) のエクスポート。
  - 環境設定
    - src/kabusys/config.py:
      - .env / .env.local ファイルと OS 環境変数からの自動ロード機能を実装（KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能）。
      - .env パーサーは export プレフィックス、シングル/ダブルクォート、インラインコメントなどに対応。
      - OS 環境変数は保護され、.env.local が .env を上書きする挙動を実装。
      - 必須環境変数取得ヘルパー (_require) と各種設定プロパティ（J-Quants, kabu API, Slack, DB パス, 実行環境・ログレベル検証など）を提供。KABUSYS_ENV と LOG_LEVEL の値検証を行う。
  - J-Quants データクライアント
    - src/kabusys/data/jquants_client.py:
      - API レート制御（120 req/min）のための固定間隔レートリミッタ実装。
      - 冪等性（DuckDB へは ON CONFLICT DO UPDATE を用いた保存）。
      - リトライ/指数バックオフ（最大リトライ 3 回、408/429/5xx を対象）、429 の Retry-After ヘッダ優先処理。
      - 401 受信時はリフレッシュトークンから id_token を自動更新して 1 回リトライする仕組み（無限再帰回避）。
      - id_token のモジュールレベルキャッシュ（ページネーション間で共有）実装。
      - ページネーション対応の取得関数: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar。
      - DuckDB への保存関数: save_daily_quotes, save_financial_statements, save_market_calendar。fetched_at は UTC タイムスタンプで記録。
      - 型変換ユーティリティ: _to_float, _to_int（文字列の小数チェックや変換失敗時の None ハンドリング）。
  - ニュース収集モジュール
    - src/kabusys/data/news_collector.py:
      - RSS フィードからの記事収集と前処理パイプラインを実装。
      - URL 正規化とトラッキングパラメータ除去（utm_* 等）、正規化 URL の SHA-256（先頭32文字）で記事 ID を生成し冪等性を確保。
      - defusedxml を利用した安全な XML パース（XML Bomb 等対策）。
      - SSRF 対策:
        - リダイレクト先のスキーム検査とプライベートアドレス判定を行う専用の RedirectHandler。
        - リクエスト前のホスト事前検証（プライベートアドレス拒否）。
      - レスポンスサイズ制限（デフォルト 10MB）、gzip 解凍後のサイズ検査（Gzip bomb 対策）。
      - 取得・整形処理: preprocess_text（URL 除去、空白正規化）、RSS pubDate の安全なパースと UTC 変換。
      - DB 保存:
        - save_raw_news: チャンク分割とトランザクションでの INSERT ... ON CONFLICT DO NOTHING RETURNING を使い、実際に挿入された記事IDを返す。
        - save_news_symbols / _save_news_symbols_bulk: news_symbols への一括保存（重複除去、チャンク化、トランザクション）。
      - 銘柄コード抽出: 4桁数字パターンを用い、既知コードセットでフィルタ（extract_stock_codes）。
      - デフォルト RSS ソースに Yahoo Finance を設定。
  - DuckDB スキーマ定義
    - src/kabusys/data/schema.py:
      - Raw / Processed / Feature / Execution の 3 層（＋実行層）に基づくテーブルを定義する DDL を提供。
      - 各テーブルに適切な制約（PRIMARY KEY、CHECK、FOREIGN KEY）を設定。
      - 頻出クエリに備えたインデックス定義。
      - init_schema(db_path) によりディレクトリ作成→全 DDL とインデックスを実行して接続を返す。get_connection() で既存 DB への接続を返す。
  - ETL パイプライン
    - src/kabusys/data/pipeline.py:
      - 差分更新を行う ETL 設計（最終取得日からの差分算出、backfill による数日前からの再取得）。
      - ETLResult dataclass: 実行結果・品質問題・エラーメッセージを集約する API（to_dict を提供）。
      - 市場カレンダーを考慮した営業日調整ヘルパー (_adjust_to_trading_day)。
      - get_last_price_date / get_last_financial_date / get_last_calendar_date などの差分判定ヘルパー。
      - run_prices_etl: 差分取得ロジック（date_from 自動算出、backfill_days デフォルト 3 日）と保存を実装（J-Quants クライアント経由）。
  - その他
    - 型注釈を豊富に使用しテスト性・読みやすさを向上。
    - ロギングによる詳細情報・警告出力（fetch/save の件数、異常検知など）。

Security
- ニュース収集に関して SSRF 対策、defusedxml による XML 攻撃対策、レスポンスサイズの上限設定（メモリ DoS / Gzip bomb 対策）を実装。
- .env 読み込みでは OS 環境変数を保護する機構を備え、.env.local による上書きも制御。

Performance
- J-Quants API の呼び出しにレートリミッタを導入（120 req/min 固定スロットリング）。
- NewsCollector と news_symbols の INSERT はチャンク化してトランザクションをまとめることで DB オーバーヘッドを削減。
- ID トークンをモジュールレベルでキャッシュしてページネーション連続呼び出し時のオーバーヘッド低減。

Notes / Known issues
- run_prices_etl の末尾の return 文がファイル抜粋の都合で不完全に見える（現状のコード断片では "return len(records), " のように単一要素のタプルを返しており、関数シグネチャで期待される (int, int) を返していない可能性がある）。実運用前に run_prices_etl の戻り値（取得件数・保存件数のタプル）を確認・修正してください。
- pipeline モジュールは品質チェック（quality モジュール）との連携を前提としているが、quality の実装に依存した箇所があるため統合テストが必要。
- 実行環境（kabu ステーション API、J-Quants トークン、Slack トークン等）の設定が必須。設定不足時は Settings が ValueError を送出する。

----------------------------------------------------------------------

今後のリリース候補（例）
- 0.1.1: run_prices_etl の戻り値修正、テストカバレッジ追加、パーサのエッジケース対応。
- 0.2.0: strategy / execution / monitoring サブパッケージの実装（注文送信、モニタリング、戦略バックテスト機能）、AI スコア生成パイプラインの追加。

----------------------------------------------------------------------

必要であれば
- 日付を変更
- 既知の不具合を詳細化
- "Fixed/Changed/Removed/Deprecated" のセクションを追加
などを行います。ご希望があれば変更案を作成します。