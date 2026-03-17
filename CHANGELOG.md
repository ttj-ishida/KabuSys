# Changelog

すべての注目すべき変更点をこのファイルで管理します。  
このファイルは「Keep a Changelog」フォーマットに準拠しています。

## [0.1.0] - 2026-03-17

### Added
- 初期リリース: KabuSys 日本株自動売買システムの基盤機能を追加。
  - パッケージエントリポイント (src/kabusys/__init__.py)
    - バージョン情報 `__version__ = "0.1.0"` を設定。
    - パブリック API として `data`, `strategy`, `execution`, `monitoring` をエクスポート。

  - 環境設定管理 (src/kabusys/config.py)
    - .env ファイルおよび環境変数から設定を自動読み込み（優先順: OS 環境 > .env.local > .env）。
    - プロジェクトルートの自動検出（.git または pyproject.toml を基準）により CWD に依存しない読み込みを実装。
    - .env パーサ実装（コメント、export プレフィックス、クォート内のエスケープ対応など）。
    - 自動ロード無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をサポート（テスト用途）。
    - `Settings` クラスを提供し、必須変数取得（未設定時は ValueError）、型変換（Path）や値検証（KABUSYS_ENV / LOG_LEVEL の許容値チェック）を実装。
    - DBファイルパスのデフォルト（DuckDB / SQLite）を設定。

  - J-Quants API クライアント (src/kabusys/data/jquants_client.py)
    - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーの取得機能を実装。
    - レート制限対応: 固定間隔スロットリングで 120 req/min を厳守（RateLimiter）。
    - 再試行ロジック: 指数バックオフ付きで最大 3 回のリトライ（408/429/5xx を対象）、429 の場合は Retry-After を尊重。
    - 401 受信時はリフレッシュトークンから id_token を自動更新して 1 回再試行（無限再帰防止）。
    - ページネーション対応で全ページを取得（pagination_key を使用）。
    - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）は冪等性を担保（ON CONFLICT DO UPDATE）。
    - データ型変換ユーティリティ `_to_float` / `_to_int` を実装（安全な変換、空値・不正値は None）。

  - ニュース収集モジュール (src/kabusys/data/news_collector.py)
    - RSS フィードからのニュース収集および DuckDB への保存を実装。
    - 設計方針として:
      - 記事 ID を URL 正規化後の SHA-256（先頭32文字）で生成して冪等性を確保。
      - トラッキングパラメータ（utm_* 等）を除去して正規化。
      - defusedxml を使った XML パースで XML Bomb 等の攻撃を緩和。
      - SSRF 対策: リダイレクト時にスキームとホストの検査を行い、プライベートアドレスへのアクセスを拒否。
      - レスポンス最大長制限（MAX_RESPONSE_BYTES=10MB）、gzip の検出と安全な解凍処理。
      - DB 保存はチャンク化してトランザクション内で行い、INSERT ... RETURNING により実際に新規挿入された ID を返す。
      - 銘柄コード抽出機能（4桁数字の抽出 + known_codes によるフィルタリング）。
    - 公開 API:
      - fetch_rss: RSS を取得して記事リストを返す（スキーム検証・SSRF 前置検証・XML パースエラーは安全に扱う）。
      - save_raw_news: raw_news テーブルへチャンク挿入（ON CONFLICT DO NOTHING）し、新規挿入 ID リストを返す。
      - save_news_symbols / _save_news_symbols_bulk: news_symbols テーブルへの銘柄紐付けをチャンク挿入で実装。
      - extract_stock_codes: テキストから既知銘柄コードを抽出。
      - run_news_collection: 複数 RSS ソースを順次処理し、各ソースの失敗は他ソースに影響させないロバストな収集処理を実装。

  - データベーススキーマ管理 (src/kabusys/data/schema.py)
    - DuckDB 用のスキーマ定義を追加（Raw / Processed / Feature / Execution の 3 層＋Execution layer を含む構成）。
    - raw_prices, raw_financials, raw_news, raw_executions 等の Raw レイヤ、prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の Processed レイヤ、features, ai_scores 等の Feature レイヤ、signals, signal_queue, orders, trades, positions, portfolio_performance 等の Execution レイヤを定義。
    - 各テーブルに制約 CHECK や PRIMARY KEY を設定。
    - 頻出クエリ向けのインデックスを定義。
    - init_schema(db_path) で DB ファイルの親ディレクトリ自動作成・DDL 実行を行い、冪等にスキーマ初期化を実施。
    - get_connection(db_path) で既存 DB への接続を返す（初期化は行わない）。

  - ETL パイプライン (src/kabusys/data/pipeline.py)
    - ETL の基本フローを実装（差分取得、保存、品質チェックを組み合わせる設計）。
    - ETLResult dataclass を追加し、実行メタ情報（取得件数、保存件数、品質問題、エラー）を保持。
    - テーブル存在チェック、テーブルの最大日付取得ユーティリティを実装。
    - 市場カレンダーに基づく営業日調整ヘルパー `_adjust_to_trading_day` を実装（30日遡りの上限つきフォールバック）。
    - 差分更新ロジック（get_last_* をもとに date_from を自動算出）を提供。
    - run_prices_etl を追加（backfill_days による後出し修正吸収、fetch_daily_quotes と save_daily_quotes の連携）。

### Security
- ニュース収集モジュールで以下のセキュリティ対策を実装:
  - defusedxml による安全な XML パース。
  - SSRF 対策: リダイレクト時のスキーム/ホスト検査、ホスト解決後のプライベート IP 判定。
  - レスポンスサイズ上限と gzip 解凍後のサイズ検査（メモリ DoS / Gzip bomb 対策）。
  - URL スキーム検証で file:, javascript:, mailto: 等を排除。

### Notes / その他
- 設定値が見つからない場合は明確な例外を発生させる（Settings._require による ValueError）。
- J-Quants API クライアントは id_token キャッシュをモジュールレベルで保持してページネーション間で再利用。
- DuckDB への保存はできる限り冪等（ON CONFLICT 句）にし、データの上書き/更新方針を明確化。
- ETL の品質チェック部分（quality モジュール呼び出し）は設計に示されているが、実装は別モジュールに依存。

### Deprecated
- なし

### Fixed
- 初期リリースのため該当なし

もしリリース日やバージョン命名ポリシーを別日にしたい場合や、さらに詳細な変更点（各関数のシグネチャ変更や DDL の微細差分など）を追記したい場合は教えてください。必要に応じて英語版やリリースノート向けの要約も作成できます。