CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従って記載しています。  
セマンティックバージョニング (SemVer) を採用しています。

[0.1.0] - 2026-03-17
--------------------

Added
- 初回リリース: KabuSys 日本株自動売買の骨組みを実装。
  - パッケージ構成:
    - kabusys (package): data, strategy, execution, monitoring の公開を準備。
    - バージョン: 0.1.0 (src/kabusys/__init__.py)
- 環境変数 / 設定管理 (src/kabusys/config.py)
  - プロジェクトルートを .git または pyproject.toml から検出して .env/.env.local を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能）。
  - .env のパース: export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、インラインコメント処理などを実装。
  - 環境設定を Settings クラスで提供（J-Quants、kabuステーション、Slack、DB パス、環境/ログレベル検証、is_live/is_paper/is_dev ヘルパー）。
  - 不足する必須環境変数は ValueError を投げて明確に通知。
- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - 基本的な API 呼び出しラッパーを実装。
  - レートリミット制御: 固定間隔スロットリングで 120 req/min を保障する RateLimiter を導入。
  - 再試行ポリシー: 指数バックオフ、最大 3 回の再試行（対象: 408/429/5xx）、429 の Retry-After ヘッダ優先。
  - 認証: リフレッシュトークンから id_token を取得する get_id_token、401 受信時に自動リフレッシュして 1 回だけリトライする仕組み。
  - ページネーション対応の取得関数: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar。
  - DuckDB へ冪等保存する save_daily_quotes, save_financial_statements, save_market_calendar（ON CONFLICT DO UPDATE を利用）。
  - データ正規化ユーティリティ: _to_float, _to_int（詳細な数値変換ポリシーを実装）。
- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードからの記事収集および DuckDB への保存機能を実装。
  - セキュリティ対策:
    - defusedxml による XML パース（XML Bomb 等の防止）。
    - HTTP リダイレクト時にスキームと到達先ホストの検証を行うカスタム RedirectHandler（内部ネットワーク到達の防止）。
    - URL スキーム検証（http/https のみ許可）、ホストのプライベートアドレス検出（SSRF 対策）。
    - レスポンス受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後の再チェック（Gzip bomb 対策）。
  - URL 正規化: トラッキングパラメータ（utm_*, fbclid 等）除去、クエリキーソート、フラグメント削除。
  - 記事ID 生成: 正規化 URL の SHA-256 ハッシュの先頭 32 文字で一意 ID を生成し冪等性を担保。
  - DB 保存: トランザクションでのバルク INSERT、ON CONFLICT DO NOTHING と INSERT ... RETURNING による実際に挿入された件数の取得。
  - 銘柄コード抽出: 正規表現による 4 桁コード抽出（known_codes によるフィルタリング）。
  - 統合ジョブ run_news_collection により複数ソースの収集→保存→銘柄紐付けを実行。
  - テスト性: HTTP 呼び出し部分(_urlopen) をモック可能に実装。
- DuckDB スキーマ定義と初期化 (src/kabusys/data/schema.py)
  - DataPlatform 指針に基づく 3 層（Raw / Processed / Feature）＋Execution 層のテーブル DDL を定義。
  - raw_prices, raw_financials, raw_news, raw_executions などの Raw テーブル。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols などの Processed テーブル。
  - features, ai_scores 等の Feature テーブル。
  - signals, signal_queue, orders, trades, positions, portfolio_performance 等の Execution テーブル。
  - 適切なチェック制約（NOT NULL / CHECK / PRIMARY KEY / FOREIGN KEY）と索引を定義。
  - init_schema(db_path) でディレクトリ作成→DDL 実行→接続返却、get_connection() も提供。
- ETL パイプラインの下地 (src/kabusys/data/pipeline.py)
  - ETLResult dataclass による ETL 実行結果の集約（品質問題/エラーの収集、辞書化 to_dict）。
  - 差分更新のためのヘルパー (get_last_price_date, get_last_financial_date, get_last_calendar_date)。
  - 市場カレンダーに基づく営業日調整関数 _adjust_to_trading_day。
  - 差分取得・バックフィルを考慮した run_prices_etl の骨組み（最小データ日付、backfill の適用、jquants_client 経由での取得と保存）。

Security
- RSS 収集周りの SSRF/DoS 対策（スキーム検証、プライベートアドレス除外、サイズ上限、defusedxml、gzip 解凍後チェック）。
- DuckDB スキーマにおける CHECK 制約等で型・値の整合性を担保。
- .env 読み込み時に OS 環境変数を保護する protected オプションを採用。

Known issues / Notes
- run_prices_etl の末尾が未完（ソース内で return が途中で終わっているように見える断片が存在）。現状の実装では (取得数, 保存数) を返す想定だが、現行コードではタプルが不完全な形で返っている可能性があり、修正が必要です。
- pipeline モジュールは品質チェックモジュール (kabusys.data.quality) を参照しているが、quality モジュールの実装はこのスナップショットには含まれていません。品質チェック連携は別途実装・接続が必要です。
- jquants_client の _request は urllib を用いており、細かい HTTP ヘッダやタイムアウト設定/証明書などの設定が将来的に必要になる可能性があります。
- news_collector の URL 正規化やコード抽出は既知コードセットを受け取る設計のため、known_codes を最新化する運用が必要です。

Acknowledgements / Testing hooks
- news_collector._urlopen はユニットテストでモック可能に実装。ID トークンのキャッシュや自動リフレッシュもテスト用に注入が可能（id_token 引数経由）。

今後の予定（例）
- run_prices_etl の戻り値バグ修正と単体テスト追加。
- pipeline における品質チェック・ログ保存・監視通知の実装。
- strategy / execution / monitoring の具体的な実装を追加（バックテスト・実取引インターフェースの完成）。
- HTTP クライアントを requests 等に置き換え、接続管理やセッション再利用を改善。

以上。必要であればリリースノートを英語版に変換したり、各変更点に対応するコミット/チケット番号を追記します。