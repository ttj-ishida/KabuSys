Keep a Changelog
=================

すべての重要な変更点をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

[Unreleased]
------------

- 現在なし。

[0.1.0] - 2026-03-17
-------------------

初回公開リリース。日本株自動売買システム KabuSys のコア機能群を実装しました。以下は主要な追加点と設計上の注意点です。

Added
- パッケージの基本情報
  - kabusys.__version__ = "0.1.0"
  - パッケージ公開 API: data, strategy, execution, monitoring（空モジュールを含む初期構造）

- 環境変数・設定管理（kabusys.config）
  - .env / .env.local ファイルの自動読み込み（プロジェクトルートを __file__ の親階層から .git または pyproject.toml で探索）
  - 読み込み優先順位: OS 環境変数 > .env.local > .env
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - .env パース処理の強化:
    - export KEY=val 形式対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - クォートなしの値におけるインラインコメント（#）の扱い
  - 読み込み失敗時は警告を出力して継続（テスト時の扱いを容易に）
  - Settings クラスを提供し、アプリケーションで必要な設定値をプロパティとして取得可能:
    - J-Quants / kabu API / Slack トークンやチャネル、DBパス（DuckDB/SQLite）、環境（development/paper_trading/live）や log_level 等
  - env / log_level の値検証（有効値以外は ValueError）

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 主要機能:
    - 株価日足（OHLCV）、四半期財務データ、JPX マーケットカレンダーの取得
    - ページネーション対応で全件取得
  - 信頼性・レート制御:
    - レート制限遵守のための固定間隔スロットリング（120 req/min）
    - 再試行（指数バックオフ）、最大リトライ回数 3（408 / 429 / 5xx をリトライ対象）
    - 429 の場合は Retry-After を優先
    - 401 時は自動でリフレッシュトークンから id_token を取得して 1 回だけリトライ
    - id_token のモジュールレベルキャッシュを共有（ページネーションをまたぐトークン再利用）
  - 保存:
    - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）は冪等（ON CONFLICT DO UPDATE）
    - fetched_at を UTC で記録して look-ahead bias を防止
  - 入出力の堅牢性:
    - JSON デコード失敗時に詳細メッセージを出力
    - ネットワーク例外や HTTP エラーのログと再試行処理

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィードから記事を収集し raw_news/raw_news_symbols に保存する機能
  - セキュリティ対策:
    - defusedxml による XML パース（XML Bomb 等を防止）
    - URL スキーム検証（http/https のみ許可）
    - SSRF 対策:
      - リダイレクト用カスタムハンドラでリダイレクト先のスキーム・ホストを検査
      - ホストがプライベート/ループバック/リンクローカル/マルチキャストであればブロック
      - フェッチ前に最初のホストのプライベートチェックを実行
    - レスポンス最大バイト数制限（MAX_RESPONSE_BYTES = 10 MB）と追加の gzip 解凍後チェック（Gzip bomb 対策）
    - 受信ヘッダの Content-Length チェック（不正値は無視して安全にスキップ）
  - データ処理:
    - URL 正規化（スキーム・ホストを小文字化、トラッキングパラメータ（utm_* 等）削除、フラグメント削除、クエリソート）
    - 記事IDは正規化 URL の SHA-256（先頭32文字）で生成し冪等性を確保
    - テキスト前処理（URL 除去、空白正規化）
    - pubDate のパース（RFC 2822 対応、パース失敗時は警告と現在時刻で代替）
  - DB 保存:
    - チャンク分割と単一トランザクションでの保存（INSERT ... ON CONFLICT DO NOTHING RETURNING id を使用）により、実際に挿入されたレコードIDを返す
    - news_symbols の一括保存（重複除去、チャンク、トランザクション）で効率化
  - 高レベル API:
    - fetch_rss / save_raw_news / save_news_symbols / run_news_collection を提供
    - run_news_collection はソース毎に独立してエラーハンドリング（1つのソース失敗でも他は継続）し、既知銘柄セットによる銘柄抽出を行う

- DuckDB スキーマ定義・初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution の 3 層（＋実行層）に対応するテーブル群を DDL として定義
  - 各テーブルに適切なチェック制約・主キー・外部キーを設定
  - 頻出クエリに対応するインデックス定義を追加
  - init_schema(db_path) により親ディレクトリの自動作成、DDL の冪等実行、接続オブジェクトを返す
  - get_connection(db_path) で既存 DB へ接続（初回は init_schema を推奨）

- ETL パイプライン（kabusys.data.pipeline）
  - ETLResult dataclass により ETL 実行結果を集約・シリアライズ可能に
  - 差分更新支援:
    - DB の最終取得日を取得するユーティリティ（get_last_price_date / get_last_financial_date / get_last_calendar_date）
    - 取得範囲の算出（バックフィル日数 backfill_days=3、デフォルト最小日付 _MIN_DATA_DATE=2017-01-01）
    - 非営業日の自動調整ヘルパー（_adjust_to_trading_day）
  - run_prices_etl を含む個別 ETL ジョブ（差分取得 → 保存 → 品質チェック連携を想定）
  - 設計方針: 後出し修正を吸収するためのバックフィル、品質チェックは重大度に応じて呼び出し元で対処（Fail-Fast しない）

Changed
- N/A（初回リリースのため既存機能の変更履歴はありません）

Fixed
- .env パーサーの扱いを改善:
  - クォート内のバックスラッシュエスケープと閉じクォート探索を実装
  - クォートなし値のインラインコメント認識を改善

Security
- RSS フィード関連で複数の安全対策を実装:
  - defusedxml を利用した安全な XML パース
  - SSRF 対策（リダイレクト検査、プライベートIP/ホスト拒否）
  - レスポンスサイズ制限および gzip 解凍後のサイズチェック（DoS/Gzip-bomb 対策）
  - URL スキーム検証（http/https のみ）

Performance
- J-Quants クライアントでの固定間隔レートリミッタ（120 req/min）と再試行バックオフにより API 制限を尊重しつつ安定化
- id_token のキャッシュ共有によりページネーションや複数リクエスト時のオーバーヘッドを削減
- ニュース保存でチャンク化・バルク INSERT・トランザクションを使用し DB オーバーヘッドを低減

Documentation / Usage notes
- DB 初期化: schema.init_schema(path) を呼び出して DuckDB を作成・DDL を適用してください（":memory:" も可）
- 環境変数:
  - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - DB パス等はデフォルト値が設定されます（DUCKDB_PATH= data/kabusys.duckdb 等）
  - 自動読み込みを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
- テストしやすさ:
  - news_collector._urlopen をモックして HTTP レスポンスを差し替え可能
  - .env 自動ロードは無効化できるためテスト環境の制御が容易

Breaking Changes
- なし（初回リリース）

Known issues / Limitations
- run_prices_etl など pipeline 側の一部関数は将来的に品質チェック（quality モジュール）との連携を想定しており、品質チェックモジュールの実装依存があります。
- news_collector の extract_stock_codes は単純に 4 桁数字の抽出＋ known_codes フィルタに依存するため、誤検出・未検出があり得ます（将来的に NLP 等の強化を想定）。

Contributors
- 初期実装（単一リポジトリの作成・設計・実装）

--- 

（注）本 CHANGELOG は提供されたコードベースの内容から推測して作成したリリースノートです。実際のリリース日や追加・修正内容は開発履歴に合わせて適宜更新してください。