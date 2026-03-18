CHANGELOG
=========

すべての注目すべき変更はここに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

[0.1.0] - 2026-03-18
--------------------

Added
- 初回リリースとしてパッケージ kabusys を追加。
  - パッケージバージョン: 0.1.0 (src/kabusys/__init__.py)
- 環境変数・設定管理モジュールを実装 (src/kabusys/config.py)
  - .env / .env.local の自動読み込み（プロジェクトルートは .git または pyproject.toml を探索して特定）
  - 読み込み順序: OS 環境変数 > .env.local > .env（.env.local は .env を上書き）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応
  - .env パーサーの強化:
    - export KEY=val 形式対応、シングル/ダブルクォート・エスケープ処理、インラインコメント処理
  - 必須キー取得ヘルパー (_require) と Settings クラス:
    - J-Quants / kabuステーション / Slack / DB パス 等のプロパティを提供
    - KABUSYS_ENV と LOG_LEVEL のバリデーション（許可値のチェック）
    - Path 型での duckdb/sqlite パス取得、is_live/is_paper/is_dev の便宜プロパティ
- J-Quants API クライアントを実装 (src/kabusys/data/jquants_client.py)
  - 日足（OHLCV）、財務データ、マーケットカレンダーの取得関数を実装（ページネーション対応）
    - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - 認証/トークン取得関数 get_id_token とモジュールレベルの ID トークンキャッシュ
  - HTTP リクエスト共通処理:
    - 固定間隔スロットリングによるレート制限（120 req/min）実装（_RateLimiter）
    - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx をリトライ）
    - 401 受信時は自動トークンリフレッシュ（1 回のみ）してリトライ
    - JSON デコード失敗時の明確なエラーメッセージ
  - DuckDB 保存用ユーティリティ（冪等性を担保）
    - save_daily_quotes, save_financial_statements, save_market_calendar
    - ON CONFLICT DO UPDATE による上書き（重複排除・更新）
  - 型変換ユーティリティ: _to_float, _to_int（厳密な変換ルール）
- ニュース収集モジュールを実装 (src/kabusys/data/news_collector.py)
  - RSS フィードからの記事取得・前処理・保存ワークフローを提供
    - fetch_rss: RSS 取得・XML パース・記事抽出（content:encoded 優先、pubDate パース等）
    - preprocess_text: URL 除去、空白正規化
    - URL 正規化と記事ID生成（_normalize_url / _make_article_id: SHA-256 の先頭32文字）
    - SSRF 対策:
      - リダイレクト先のスキーム/ホスト検証用ハンドラ (_SSRFBlockRedirectHandler)
      - ホストがプライベート IP / ループバック / リンクローカル / マルチキャストの場合は拒否
      - URL スキームは http/https のみ許可
    - 大きすぎるレスポンスを拒否（MAX_RESPONSE_BYTES = 10MB）、gzip の解凍後もサイズ検査
    - XML の安全なパースに defusedxml を使用
  - DuckDB への保存関数:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING + RETURNING id（チャンク挿入、トランザクション）
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付け保存（ON CONFLICT 無視、RETURNING で挿入数算出）
  - 銘柄コード抽出ユーティリティ extract_stock_codes（4桁数字、既知コードセットでフィルタ）
  - デフォルト RSS ソース定義（例: Yahoo Finance 日本版）
  - 統合収集ジョブ run_news_collection: 各ソースを独立して処理し、エラー時も他ソースを継続
- DuckDB スキーマ定義と初期化 (src/kabusys/data/schema.py)
  - Raw / Processed / Feature / Execution 層のテーブル定義を実装（raw_prices, raw_financials, raw_news, prices_daily, market_calendar, features, ai_scores, signals, orders, trades, positions 等）
  - 適切な型制約と CHECK 制約を設定（負値防止、列制約など）
  - 外部キー・PRIMARY KEY を含む定義
  - 頻出クエリ向けのインデックス定義
  - init_schema(db_path) により冪等的にスキーマ初期化（親ディレクトリ自動作成）
  - get_connection(db_path) で既存 DB への接続を提供
- ETL パイプライン基盤を実装 (src/kabusys/data/pipeline.py)
  - ETLResult dataclass による ETL 実行結果の集約（品質問題、エラー一覧等を含む）
  - 差分更新ヘルパー:
    - get_last_price_date / get_last_financial_date / get_last_calendar_date
    - テーブル存在チェックおよび最大日付取得ロジック
  - 市場カレンダー調整ヘルパー (_adjust_to_trading_day)
  - run_prices_etl: 株価日足の差分取得と保存ロジック（差分/バックフィルの算出、jquants_client 呼び出し、保存）
  - 設計方針としてバックフィル (既定 3 日)、カレンダー先読みなどを採用
- パッケージ骨格
  - data, strategy, execution, monitoring といったサブパッケージのプレースホルダを配置

Security
- XML パースに defusedxml を使用して XML-Bomb 等の攻撃を緩和
- news_collector において SSRF 対策を実装（スキーム検証、プライベートホスト拒否、リダイレクト検査）
- RSS の受信サイズ制限と gzip 解凍後サイズチェックでリソース消費攻撃を軽減

Notes / Known limitations
- strategy/execution/monitoring サブパッケージはファイル構成が用意されているが、実装は含まれていません（拡張用の骨組み）。
- quality モジュール参照 (pipeline は quality.QualityIssue を扱う設計) があるが、quality モジュール本体はこのリリースのコードベースには含まれていない可能性があります（別モジュール/今後追加予定）。
- run_prices_etl 等の ETL 関数は基本的な差分取得/保存の流れを実装しているが、全体のワークフロー（スケジューリング・監視・通知等）は別途実装が必要です。
- J-Quants API 周りのネットワーク/認証処理は堅牢性を考慮しているが、実環境での追加の監視・メトリクスやより詳細なエラーハンドリングは今後の改善ポイントです。

Authors
- 初版実装者（コードベースに記載の設計・実装者）

ライセンス
- ソース内に明示的なライセンスファイルがない場合は、適切なライセンスファイルを追加してください。

-------------------------------------------------------------------------------
注: 本 CHANGELOG はリポジトリ内のソースコードから推測して作成したもので、実際のコミット履歴やリリースノートとは差異がある場合があります。必要に応じて日付や詳細をプロジェクトの実際の履歴に合わせて調整してください。