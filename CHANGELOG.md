# Changelog

すべての変更履歴は Keep a Changelog の形式に準拠します。  
現在のバージョンは 0.1.0（初回リリース）です。本ファイルは、コードベースから推測される実装内容と注意点を日本語でまとめたものです。

※ 日付はソース確認日（自動推定）です。

## [Unreleased]
- 今後の予定（ソース構成から推測）
  - strategy / execution / monitoring モジュールの実装拡充
  - quality モジュールを使った ETL 品質チェックの詳細実装・可視化
  - ETL パイプラインの拡張（prices_etl の処理完了・financials/calendar の定期実行）
  - 単体テスト・統合テストの整備（ネットワーク依存部分のモック活用）

---

## [0.1.0] - 2026-03-18
初回リリース。日本株自動売買システム「KabuSys」の基盤的なコンポーネントを実装。

### Added
- パッケージ基盤
  - kabusys パッケージを追加。公開 API として data, strategy, execution, monitoring を __all__ に定義（strategy/execution は空のパッケージ初期化子あり）。
  - バージョン情報 __version__ = "0.1.0" を設定。

- 設定管理 (kabusys.config)
  - .env / .env.local の自動読み込み機能（KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能）。
  - プロジェクトルート検出ロジック（.git または pyproject.toml を基準）により CWD に依存しない読み込み。
  - 強化された .env パーサ（export 形式、シングル/ダブルクォート、インラインコメント処理、保護された OS 環境変数の扱い）。
  - Settings クラスを提供し、以下の設定プロパティを取得可能:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルトあり）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（デフォルト data/monitoring.db）
    - KABUSYS_ENV（"development", "paper_trading", "live" の検証）
    - LOG_LEVEL（"DEBUG","INFO","WARNING","ERROR","CRITICAL" の検証）
    - is_live / is_paper / is_dev の便宜プロパティ

- J-Quants API クライアント (kabusys.data.jquants_client)
  - 基本的な API 呼び出しユーティリティを実装（/prices/daily_quotes, /fins/statements, /markets/trading_calendar 等の取得を想定）。
  - レートリミッタ実装（120 req/min、固定間隔スロットリング）。
  - 再試行ロジック（指数バックオフ、最大 3 回、対象ステータス 408/429/5xx）。
  - 401 受信時のトークン自動リフレッシュ（1 回のみ）によるリトライ処理。
  - ページネーション対応（pagination_key を用いた取得ループ）。
  - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を提供。ON CONFLICT DO UPDATE による冪等保存、fetched_at は UTC タイムスタンプで記録。
  - 型変換ユーティリティ (_to_float, _to_int) により不正値に対処。

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィード取得と前処理、raw_news への保存機能を実装。
  - セキュリティ対策:
    - defusedxml を使った XML パース（XML Bomb 等の防御）。
    - SSRF 対策（リダイレクト時の検査、HTTPRedirectHandler 派生クラスによるスキーム/ホスト検証）。
    - ホストがプライベート/ループバック/リンクローカル/マルチキャストでないことを判定（IP直接判定 + DNS 解決で A/AAAA を検査）。
    - URL スキーム制限（http/https のみ）。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10 MB）、gzip 解凍後もサイズ検査（Gzip bomb 対策）。
  - URL 正規化（トラッキングパラメータ削除、クエリソート、fragment 削除）、記事ID は正規化 URL の SHA-256（先頭32文字）で生成して冪等性確保。
  - preprocess_text による URL 除去・空白正規化。
  - DuckDB 保存処理はトランザクションでまとめて実行し、チャンク挿入と INSERT ... RETURNING により実際に挿入された件数を正確に取得。
  - 銘柄コード抽出機能（4 桁数字を候補に既知コードセット known_codes でフィルタ）と news_symbols への紐付けバルク保存。

- スキーマ定義 (kabusys.data.schema)
  - DuckDB 用のスキーマを DataPlatform.md 想定仕様に基づき実装。
  - Raw / Processed / Feature / Execution 層のテーブル DDL を定義（raw_prices, raw_financials, raw_news, market_calendar, prices_daily, features, ai_scores, signals, orders, trades, positions, など多数）。
  - 外部キーやチェック制約、インデックス定義を含む（頻出クエリを想定したインデックス）。
  - init_schema(db_path) によりディレクトリ作成→テーブル作成→接続オブジェクト返却、get_connection() も提供。

- ETL パイプライン基盤 (kabusys.data.pipeline)
  - ETLResult dataclass による ETL 実行結果の集約（品質問題、エラーの収集、to_dict で出力）。
  - テーブル存在チェック、最大日付取得ユーティリティ、営業日調整ロジックを提供（market_calendar 未取得時のフォールバックあり）。
  - 差分更新ロジックを想定した run_prices_etl を実装（最終取得日から backfill_days 日分を再取得する仕組み、_MIN_DATA_DATE の扱い）。
  - J-Quants クライアント（jquants_client）の fetch / save を組み合わせた差分 ETL の基本フローをサポート。

### Security
- RSS 集約処理および HTTP 取得処理に関して SSRF 対策、サイズ制限、defusedxml による XML パース保護を導入。
- .env の自動ロードにおいて OS 環境変数を保護する仕組み（protected set）を採用。

### Performance & Reliability
- J-Quants API クライアントでレート制御とリトライ（指数バックオフ）を実装し、安定したデータ取得を目指す。
- DuckDB へのバルク挿入をチャンク化し、トランザクションでまとめて実行することでオーバーヘッドを削減。
- ページネーション用のトークンをモジュールレベルでキャッシュして効率化。

### Notes / Known limitations
- strategy と execution の具体的なアルゴリズムやモジュール実装は未実装（初期のパッケージ骨格として空 __init__ を配置）。
- data.pipeline 内で参照される quality モジュールはソース内に含まれており、品質チェックの詳細実装（チェック一覧や判定基準）の提供が必要。
- run_prices_etl の戻り値や ETL の更なる統合（スケジューリング、監視、Slack 通知など）は今後の実装対象。
- monitoring パッケージは __all__ に列挙されているが、実装の有無は要確認。
- ネットワーク/外部 API に依存する実装が多いため、CI 上での安定したテストには外部依存のモック化が推奨される（_urlopen の差し替えポイントあり）。

---

履歴の補足や誤り、あるいは追加で注記したい点があれば知らせてください。必要に応じて日付の修正や各セクションの詳細化（SQL スキーマの列挙や環境変数一覧の完全列挙など）を行います。