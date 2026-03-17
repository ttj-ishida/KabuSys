# Changelog

すべての変更は Keep a Changelog 準拠で記載します。  
このプロジェクトの初期リリースを記録しています。

全般的なバージョニングは SemVer に従います。

## [0.1.0] - 2026-03-17

### 追加 (Added)
- パッケージ初期リリース "KabuSys"。
  - パッケージ名: kabusys
  - バージョン: 0.1.0 (src/kabusys/__init__.py)

- 環境設定管理モジュール (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
    - プロジェクトルート判定は `.git` または `pyproject.toml` に基づくため CWD に依存しない。
  - .env 解析器の実装:
    - コメント、export プレフィックス、シングル/ダブルクォートおよびバックスラッシュエスケープ、インラインコメント処理に対応。
  - 必須環境変数チェック機能 (_require) と Settings クラスを公開。
    - 主な環境変数:
      - JQUANTS_REFRESH_TOKEN（必須）
      - KABU_API_PASSWORD（必須）
      - SLACK_BOT_TOKEN、SLACK_CHANNEL_ID（必須）
      - KABUSYS_ENV（development / paper_trading / live のいずれか）
      - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）
      - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
      - SQLITE_PATH（デフォルト: data/monitoring.db）
  - Settings に便利プロパティ: is_live / is_paper / is_dev。

- J-Quants API クライアント (kabusys.data.jquants_client)
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーを取得する API クライアント実装。
  - レートリミッタ実装: 120 req/min を固定間隔スロットリングで遵守（デフォルト最小間隔 = 60/120 秒）。
  - リトライロジック:
    - 最大リトライ回数 3 回、指数バックオフ（base=2 秒）を採用。
    - 408/429 および 5xx をリトライ対象に設定。429 の場合は Retry-After ヘッダ優先。
    - ネットワーク例外 (URLError / OSError) に対するリトライ。
  - 認証トークン自動リフレッシュ:
    - 401 受信時にリフレッシュトークンから id_token を再取得して 1 回だけ自動リトライ。
    - id_token のモジュールレベルキャッシュを持ち、ページネーション間で共有。
  - ページネーション対応の fetch_* 関数を提供:
    - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
    - 取得時のログ出力（取得件数）
    - Look-ahead bias 対策として fetched_at の UTC 表示ポリシー（保存側で使用）
  - DuckDB への保存関数（冪等性を意識）:
    - save_daily_quotes, save_financial_statements, save_market_calendar
    - ON CONFLICT DO UPDATE による上書きで冪等性を保持
    - PK 欠損行はスキップし警告ログを出力
  - 型変換ユーティリティ: _to_float / _to_int（不正値や小数切り捨ての扱いを明示）

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードからニュースを収集して DuckDB に保存する機能を実装。
  - セキュリティ/堅牢性対策:
    - XML パースに defusedxml を使用して XML-Bomb 等の攻撃を軽減。
    - SSRF 防止: URL スキーム制限（http/https のみ）、ホストがプライベート/ループバック/リンクローカル/マルチキャストでないかを検査。リダイレクト時も検証するカスタムハンドラを実装。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後の再チェック（Gzip bomb 対策）。
    - User-Agent と Accept-Encoding ヘッダの指定。
  - URL 正規化と記事IDの生成:
    - トラッキングパラメータ（utm_*, fbclid, gclid 等）を削除し、スキーム/ホストを小文字化、クエリパラメータをソートして正規化。
    - 記事ID は正規化 URL の SHA-256 ハッシュ先頭 32 文字。
  - テキスト前処理: URL 除去、空白正規化。
  - DB 保存:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING RETURNING id を使い、実際に挿入された記事 ID のリストを返す（チャンク化で一括挿入）。
    - save_news_symbols / _save_news_symbols_bulk: news_symbols テーブルへの紐付けを一括挿入（ON CONFLICT DO NOTHING RETURNING を利用して実際に挿入された件数を返す）。
  - 銘柄コード抽出:
    - 正規表現により 4 桁数字を候補とし、known_codes に含まれるもののみ採用（重複除去）。

- DuckDB スキーマ管理 (kabusys.data.schema)
  - DataSchema.md に基づく 3 層構造（Raw / Processed / Feature / Execution）のテーブル定義を実装。
  - 主なテーブル:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な制約（PRIMARY KEY / CHECK / FOREIGN KEY）を設定。
  - 頻出クエリ用のインデックス定義を追加。
  - init_schema(db_path) によりディスク上の DB ファイル作成と DDL 実行を行い、接続を返す（冪等）。get_connection も提供。

- ETL パイプライン (kabusys.data.pipeline)
  - 差分更新および保存、品質チェックといった ETL フローの基礎を実装。
  - 設計方針に従い、差分単位は営業日単位。backfill_days により後出し修正を吸収（デフォルト 3 日）。
  - 市場カレンダー先読み: _CALENDAR_LOOKAHEAD_DAYS = 90 日。
  - 最小データ開始日: _MIN_DATA_DATE = 2017-01-01（初回ロード用）。
  - ETLResult dataclass を導入し、各 ETL 実行結果（取得件数、保存件数、品質問題、エラー）を集約して返却可能。
  - get_last_* ヘルパー、_adjust_to_trading_day、run_prices_etl（差分 ETL の雛形）を実装。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- ニュース収集における SSRF と XML 攻撃に対する複数の防御策を追加。
  - defusedxml、リダイレクト検証、プライベートアドレス検出、スキーム制限、レスポンスサイズ制限、gzip 解凍後の検査。

### 既知の制限 (Known issues / Notes)
- jquants_client の HTTP 実装で urllib を使用。高度な HTTP 機能（接続プールなど）が必要な場合は将来的に requests 等への移行を検討。
- quality モジュール参照（pipeline 内）は存在前提。品質チェック実装は外部モジュール（kabusys.data.quality）に依存するため、実装状況に応じて ETL の挙動が変わります。
- ETL の run_prices_etl が末尾での return の記述が未完了（len(records), のような形で切れている可能性）など、細かい実装レビューが必要。実行時に Syntax / 意図した戻り値の確認を推奨。

### 互換性の破壊 (Breaking Changes)
- 初回リリースのため該当なし。

---

今後のリリースでは、以下を予定しています（例）:
- execution モジュールの発注/約定統合
- strategy モジュールのサンプル戦略実装
- モニタリング / Slack 通知機能の追加
- 単体テストと CI 設定の整備

※ 本 CHANGELOG はコードベースから推定して作成しています。実際のリリースノートとして利用する場合は、リリース時の差分・テスト結果・ドキュメントを反映してください。