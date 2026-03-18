# Changelog

すべての変更は Keep a Changelog 準拠で記載しています。  
このプロジェクトはセマンティックバージョニング (SemVer) を採用しています。

## [0.1.0] - 2026-03-18

### Added
- 初期リリース。KabuSys 日本株自動売買システムのコアコンポーネントを実装。
  - パッケージ情報とエクスポート
    - src/kabusys/__init__.py にて __version__ = "0.1.0" および主要サブパッケージをエクスポート (data, strategy, execution, monitoring)。

  - 設定管理
    - src/kabusys/config.py
      - .env ファイルまたは環境変数から設定を読み込む自動ロード機能（プロジェクトルートを .git または pyproject.toml から検出）。
      - .env / .env.local の読み込み順序（OS環境変数 > .env.local > .env）。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
      - .env の柔軟なパース処理（export キーワード対応、シングル/ダブルクォート、インラインコメント処理）。
      - 必須環境変数の取得 (JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID) と検証。
      - 設定の型変換（Path返却等）と検証（KABUSYS_ENV, LOG_LEVEL の有効値チェック）およびユーティリティプロパティ（is_live / is_paper / is_dev）。

  - J-Quants API クライアント
    - src/kabusys/data/jquants_client.py
      - 株価日足 (OHLCV)、財務データ（四半期 BS/PL）、JPX マーケットカレンダーを取得する API クライアントを実装。
      - レート制限 (120 req/min) を守る固定間隔スロットリング（RateLimiter）を実装。
      - 再試行ロジック（指数バックオフ、最大 3 回、対象ステータス: 408/429/5xx）。
      - 401 受信時にリフレッシュトークン経由で id_token を自動更新して 1 回再試行する仕組み。
      - ページネーション対応（pagination_key を利用）で全件取得。
      - データ保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）:
        - DuckDB へ保存し冪等性を担保（ON CONFLICT DO UPDATE）。
        - fetched_at を UTC で記録して Look-ahead Bias を回避。
      - ユーティリティ関数 (_to_float, _to_int) により型変換を安全に処理。
      - id_token キャッシュをモジュールレベルで保持し、ページネーション間で共有。

  - ニュース収集モジュール
    - src/kabusys/data/news_collector.py
      - RSS フィードから記事を収集して raw_news に保存する実装。
      - セキュリティ / 安全対策:
        - defusedxml を用いた XML パース（XML Bomb 等の対策）。
        - SSRF 対策: URL スキーム検証 (http/https のみ)、リダイレクト時にスキーム・ホストの事前検査、プライベートアドレス拒否。
        - 受信サイズ上限 (MAX_RESPONSE_BYTES = 10MB) のチェックと gzip 解凍後のサイズ検証（Gzip bomb 対策）。
      - URL 正規化とトラッキングパラメータ除去（utm_* 等）、さらに正規化 URL の SHA-256 先頭32文字を記事IDとして生成し冪等性を保証。
      - テキスト前処理（URL除去・空白正規化）。
      - DB保存はトランザクションでまとめ、INSERT ... RETURNING を用いて実際に挿入された記事IDや件数を正確に返す実装（save_raw_news, save_news_symbols, _save_news_symbols_bulk）。
      - 銘柄コード抽出（4桁数字パターン）と既知銘柄セットによるフィルタリング（extract_stock_codes）。
      - run_news_collection により複数ソースからの収集・保存・銘柄紐付けを行う高レベルジョブを提供。各ソースは独立してエラーハンドリング。

  - DuckDB スキーマ定義と初期化
    - src/kabusys/data/schema.py
      - Raw / Processed / Feature / Execution の多層スキーマ定義（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance 等）。
      - テーブル制約（型チェック、NOT NULL、PRIMARY KEY、FOREIGN KEY、CHECK 等）を明示的に設定。
      - パフォーマンス目的のインデックスを作成（頻出クエリを想定したインデックス）。
      - init_schema(db_path) による初期化（親ディレクトリ自動作成、冪等な DDL 実行）と get_connection(db_path) を提供。

  - ETL パイプライン基盤
    - src/kabusys/data/pipeline.py
      - ETLResult dataclass による ETL 実行結果の構造化（品質問題・エラー一覧の格納、シリアライズ to_dict）。
      - 差分更新ロジックのためのユーティリティ（テーブル存在確認、最大日付取得）。
      - 市場カレンダーを用いた営業日調整ヘルパー (_adjust_to_trading_day)。
      - run_prices_etl の構成（差分取得、backfill_days デフォルト 3、最小データ日 2017-01-01、取得→保存のフロー） — ETL の差分更新設計が反映（未取得範囲の自動算出、バックフィル対応）。
      - パイプラインは品質チェックモジュール（quality）と協調する設計を想定（品質問題は収集を継続し呼び出し元で判断）。

### Security
- ニュース収集における複数のセキュリティ対策を導入:
  - defusedxml を使用した安全な XML パース。
  - SSRF 対策（スキーム検証、リダイレクト時のアドレス検査、プライベート/ループバック/リンクローカル/マルチキャストの拒否）。
  - レスポンスサイズ制限および gzip 解凍後サイズチェック（DoS / Bomb 対策）。
  - URL スキームのホワイトリスト化（http/https のみ許可）。

### Notes / Usage
- 必要な環境変数:
  - JQUANTS_REFRESH_TOKEN（必須）
  - KABU_API_PASSWORD（必須）
  - SLACK_BOT_TOKEN（必須）
  - SLACK_CHANNEL_ID（必須）
  - DUCKDB_PATH / SQLITE_PATH はデフォルトを持つ（data/kabusys.duckdb, data/monitoring.db）。
- 自動 .env ロードを抑止するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください（例: KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。
- DuckDB スキーマ初期化は init_schema() を使用してください。既存テーブルがある場合は冪等にスキップされます。

### Breaking Changes
- 初回公開のため該当なし。

### Fixed
- 初回リリースのため該当なし。

-- End of changelog for 0.1.0 --