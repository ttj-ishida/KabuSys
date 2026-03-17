# Keep a Changelog

すべての注目すべき変更をここに記録します。  
このファイルは Keep a Changelog の形式に準拠しています。

## [0.1.0] - 2026-03-17

初回リリース

### Added
- パッケージ基盤
  - 初期パッケージ構成を追加（src/kabusys/__init__.py）。バージョン 0.1.0 を設定。
  - モジュール公開APIに data, strategy, execution, monitoring を定義。

- 環境設定管理
  - .env ファイルおよび環境変数から設定を読み込む自動ローダを実装（src/kabusys/config.py）。
    - プロジェクトルートの自動検出（.git または pyproject.toml を探索）により CWD に依存しない読み込みを実現。
    - .env と .env.local の優先順位を実装（OS 環境変数 > .env.local > .env）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能（テスト用）。
    - 複雑な .env 行パーサ（export プレフィックス、クォート・エスケープ、インラインコメント処理）を実装。
    - Settings クラスでアプリ設定をプロパティとして提供（J-Quants / kabu / Slack / DB パス / env / log_level 判定など）。
    - 環境値検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）。

- J-Quants API クライアント
  - jquants_client モジュールを追加（src/kabusys/data/jquants_client.py）。
    - レート制限（120 req/min）を守る固定間隔スロットリング RateLimiter を実装。
    - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx 対象）。
    - 401 受信時の自動 ID トークンリフレッシュ（1 回のみ）とキャッシュ機構。
    - ページネーション対応の取得関数:
      - fetch_daily_quotes（株価日足）
      - fetch_financial_statements（財務四半期データ）
      - fetch_market_calendar（JPX カレンダー）
    - DuckDB への冪等保存関数（ON CONFLICT DO UPDATE）:
      - save_daily_quotes, save_financial_statements, save_market_calendar
    - 数値変換ユーティリティ _to_float / _to_int（安全な型変換・空値処理）。

- ニュース収集（RSS）
  - news_collector モジュールを追加（src/kabusys/data/news_collector.py）。
    - RSS フィード取得と記事整形パイプラインを実装。
    - URL 正規化とトラッキングパラメータ除去（utm_* 等）。
    - 記事IDは正規化 URL の SHA-256（先頭32文字）で生成し冪等性を保証。
    - defusedxml を使った安全な XML パース（XML Bomb 等対策）。
    - SSRF 対策:
      - URL スキーム検証（http/https のみ許可）。
      - ホストのプライベートアドレス判定（IP 直判定 + DNS 解決して A/AAAA を検査）。
      - リダイレクト時にスキーム・ホストを検査するカスタムハンドラを使用。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後サイズチェック（Gzip bomb 対策）。
    - RSS 内の pubDate パース（RFC2822 互換）と UTC 正規化。パース失敗時は警告ログと現在時刻で代替。
    - DB 保存機能（DuckDB）:
      - save_raw_news: チャンク挿入、トランザクション、INSERT ... RETURNING により新規挿入 ID を取得。
      - save_news_symbols / _save_news_symbols_bulk: 銘柄紐付けをチャンク・トランザクションで保存（ON CONFLICT でスキップ）。
    - 銘柄コード抽出ロジック（4桁数字パターン）と run_news_collection による統合収集ジョブ。

- DuckDB スキーマ
  - schema モジュールを追加（src/kabusys/data/schema.py）。
    - Raw / Processed / Feature / Execution 層にまたがるテーブル定義を用意（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance 等）。
    - 各種制約（PRIMARY KEY, CHECK, FOREIGN KEY）と Index の定義を含む。
    - init_schema(db_path) によりファイルパスの親ディレクトリ自動作成とテーブル作成（冪等）を実装。
    - get_connection(db_path) で既存 DB 接続取得。

- ETL パイプライン
  - pipeline モジュールを追加（src/kabusys/data/pipeline.py）。
    - ETLResult dataclass により ETL 実行結果と品質問題の集約を提供（to_dict をサポート）。
    - 差分更新ヘルパー（最終取得日の取得 get_last_price_date / get_last_financial_date / get_last_calendar_date）。
    - 市場カレンダーに基づく営業日調整 _adjust_to_trading_day（不足時フォールバック）。
    - run_prices_etl（差分取得・バックフィル機能、デフォルト backfill_days=3）などの個別 ETL ジョブの雛形。
    - データ品質チェック（quality モジュール）統合の設計（欠損・スパイク・重複検出等を想定）。

### Security
- XML パースに defusedxml を使用して XML 関連の攻撃を軽減。
- RSS フェッチに対して多重の SSRF 対策を導入（スキーム検証、プライベートIP検査、リダイレクト検査）。
- レスポンス最大バイト数と gzip 解凍後のサイズ検査によりメモリ DoS を低減。
- .env 読み込みにおいて OS 環境変数保護（protected set）を実装し、意図しない上書きを防止。

### Reliability / Robustness
- API 呼び出しに対するレートリミット制御（_RateLimiter）とリトライ／バックオフ実装。
- 401 時のトークン自動リフレッシュとキャッシュを備え、ページネーション間でトークン共有。
- DuckDB 保存処理は冪等（ON CONFLICT）かつトランザクションを用いた安全な実装。
- RSS／DB のバルク挿入はチャンク化により SQL 長・パラメータ数の上限対策。
- 数値変換ユーティリティが不正な文字列・小数切捨て等に慎重に対処。

### Notes / Known issues
- run_prices_etl の最後の return 文がソースコード上で中断（末尾が `return len(records),` で終わっている）しており、実際には (fetched, saved) のタプルを返す意図があるが、このままだと構文エラーまたは不完全な戻り値になる可能性があります。リリース前に修正が必要です。
- quality モジュールの具体的な実装はこのスナップショットに含まれておらず、ETL の品質判定部分は外部実装に依存します。
- strategy / execution / monitoring パッケージのエントリは存在するものの、具体的実装は含まれていません（今後の実装予定）。

---

今後のリリースでは、pipeline の完全実装（各 ETL ジョブの完結）、戦略（strategy）および発注実装（execution）、監視・アラート（monitoring）の実装、テストカバレッジ拡充を予定しています。