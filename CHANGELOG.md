CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」形式に準拠しています。

[Unreleased]
------------

- なし（初回公開時点）

[0.1.0] - 2026-03-17
-------------------

Added
- 初期リリース (0.1.0)
  - パッケージメタ情報:
    - パッケージ名: KabuSys
    - バージョン: 0.1.0 (src/kabusys/__init__.py に定義)
  - 環境設定管理 (src/kabusys/config.py)
    - .env / .env.local ファイルと OS 環境変数の優先順位に基づく自動読み込み機能実装
    - プロジェクトルート検出ロジック（.git または pyproject.toml を基準）により CWD 非依存での自動読み込み
    - .env 行パーサ（export 形式、クォート、インラインコメント、エスケープ処理に対応）
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート（テスト用途）
    - Settings クラスによる設定プロパティ提供（J-Quants トークン、kabu API 設定、Slack、DB パス、環境・ログレベル判定など）
    - env / log_level のバリデーション（許容値セットを定義）
  - J-Quants API クライアント (src/kabusys/data/jquants_client.py)
    - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダー取得 API を実装
    - 固定間隔スロットリングによるレート制限 (120 req/min) 実装（内部 RateLimiter）
    - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx 対応）
    - 401 発生時の自動トークンリフレッシュ（1 回のみリトライ）およびモジュールレベルの ID トークンキャッシュ
    - ページネーション対応（pagination_key を使用）
    - DuckDB への冪等保存関数（ON CONFLICT DO UPDATE）: save_daily_quotes / save_financial_statements / save_market_calendar
    - レスポンス JSON デコードエラーや HTTP エラーの詳細ログ化
  - ニュース収集モジュール (src/kabusys/data/news_collector.py)
    - RSS フィード取得・パース機能（defusedxml による安全な XML パース）
    - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント削除）
    - 記事ID は正規化URL の SHA-256（先頭32文字）で生成し冪等性を確保
    - SSRF 対策:
      - fetch 前にホストがプライベートか検査
      - リダイレクト時にスキーム／ホストを再検証するカスタム RedirectHandler を使用
      - 許可スキームは http/https のみ
    - レスポンスサイズ上限 (MAX_RESPONSE_BYTES = 10MB) と gzip 解凍後サイズ検査（Gzip bomb 対策）
    - RSS → NewsArticle 変換、テキスト前処理（URL 除去・空白正規化）
    - DuckDB への冗長挿入防止（INSERT ... ON CONFLICT DO NOTHING）および INSERT ... RETURNING を利用した挿入件数取得:
      - save_raw_news（チャンク分割、トランザクションでコミット/ロールバック）
      - save_news_symbols / _save_news_symbols_bulk（銘柄紐付けを一括挿入）
    - 銘柄コード抽出ユーティリティ（4桁数字パターン + known_codes によるフィルタ）
    - run_news_collection による複数 RSS ソースの統合収集ジョブ（個別ソースごとに失敗を隔離）
  - DuckDB スキーマ定義と初期化 (src/kabusys/data/schema.py)
    - Raw / Processed / Feature / Execution の 3 層＋実行関連テーブルを定義
    - 主要テーブル:
      - raw_prices, raw_financials, raw_news, raw_executions
      - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
      - features, ai_scores
      - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
    - 各種 CHECK 制約、PRIMARY KEY、外部キー、インデックス定義を含む DDL を提供
    - init_schema(db_path) でディレクトリ自動作成後に全 DDL・インデックスを適用
    - get_connection(db_path) による既存 DB への接続補助
  - ETL パイプライン (src/kabusys/data/pipeline.py)
    - 差分更新方針の実装:
      - DB 側の最終取得日を参照して差分（および backfill_days による再取得）を自動算出
      - _MIN_DATA_DATE, カレンダー先読みなどの定数定義
    - ETLResult データクラスによる実行結果の集約（品質問題 / エラー一覧を含む）
    - 市場カレンダー補助（_adjust_to_trading_day）やテーブル存在/最大日付取得ユーティリティ
    - run_prices_etl（株価差分取得 → 保存の処理フロー、J-Quants クライアントを利用）
  - その他
    - テスト容易性を考慮した設計（_urlopen の差し替えモックを想定、id_token 注入可能など）
    - ロギングを各モジュールに設定し、処理状況・警告を明確に出力

Changed
- なし（新規機能追加の初回リリース）

Fixed
- なし

Security
- news_collector: defusedxml を使用した XML パース、SSRF 向けの多層防御（事前ホスト検査、リダイレクト検査、スキーム制限）、レスポンスサイズ制限、gzip 解凍後検査を実装
- jquants_client: HTTP エラーやネットワークエラーのハンドリングとログにより異常時の情報を保持

Notes / Known issues
- run_prices_etl の戻り値部分がファイル末尾で切れている（現在のコード片では return 文が不完全: "return len(records), "）。実行時に例外または構文エラーになる可能性があるため要修正。
- 一部の API 呼び出しに対してタイムアウトやより細かなエラー分類（例: JSON スキーマ検証）は未実装。運用にあたっては監視/アラートの追加を推奨。
- 現段階でユニットテスト／統合テストは同梱されていない（モジュールはテストフレンドリーに実装されているのでテスト追加を推奨）。
- J-Quants / kabu API の認証情報は必須（Settings._require により未設定時は ValueError を送出）。.env.example に基づいたセットアップが必要。

Contributing
- バグ修正や機能追加は Pull Request を通じて実施してください。  
- 特に以下を優先的に改善してください:
  - run_prices_etl の戻り値修正とテスト追加
  - API エラー条件の網羅的テスト（401 リフレッシュ、429 Retry-After 等）
  - RSS パーサの多様なフィードに対する互換性テスト

License
- 明示的なライセンス情報はコード内に含まれていません。公開時は LICENSE を追加してください。