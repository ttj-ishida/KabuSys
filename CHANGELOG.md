CHANGELOG
=========

すべての重要な変更点をこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠しています。

v0.1.0 - 2026-03-17
-------------------

初回リリース。日本株自動売買プラットフォーム "KabuSys" のコア機能群を実装しました。

Added
- パッケージ基礎
  - パッケージエントリポイントを追加 (src/kabusys/__init__.py)。バージョンは 0.1.0、公開モジュール一覧を __all__ で定義。
- 設定/環境変数管理（src/kabusys/config.py）
  - .env/.env.local からの自動読み込み機能を追加（優先順位: OS環境変数 > .env.local > .env）。
  - プロジェクトルート自動検出（.git または pyproject.toml を探索）により、CWD に依存しない読み込みを実現。
  - export KEY=val 形式やクォート済み値、行末コメント、コメント行を考慮した .env パース処理を実装。
  - OS 環境変数を保護する protected オプション、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化を提供。
  - Settings クラスを実装し、J-Quants / kabu API / Slack / DB パス / システム設定（KABUSYS_ENV, LOG_LEVEL）をプロパティ経由で取得。値検証を実装（有効な環境値・ログレベルのチェック）。
- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーを取得する関数を実装（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
  - HTTP リクエストでの共通処理を実装: レート制限（固定スロットリングで 120 req/min を保証）、リトライ（指数バックオフ、最大3回）、429 の Retry-After 処理、ネットワーク/HTTP エラーの扱い。
  - 401 Unauthorized を検知した場合はトークンを自動リフレッシュして再試行するロジックを実装（get_id_token とトークンキャッシュ）。
  - ページネーション対応（pagination_key を用いたループ取得）。
  - DuckDB への保存用関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。ON CONFLICT DO UPDATE により冪等性を確保し、fetched_at（UTC）を付与してデータ取得時点をトレース可能に。
  - 型変換ユーティリティ（_to_float, _to_int）を実装し、空値や不正値を安全に扱う。
- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードからニュースを収集し DuckDB に保存する一連の処理を実装（fetch_rss, save_raw_news, save_news_symbols, run_news_collection）。
  - セキュリティ/堅牢性:
    - defusedxml を利用して XML Bomb 等への対策。
    - SSRF 対策: URL スキーム検証（http/https のみ許可）、プライベート/ループバック/リンクローカルアドレスの検出と拒否、リダイレクト先の検査（独自の RedirectHandler）。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）を導入し、受信時・gzip 解凍後ともにサイズ制限をチェック。
  - 記事ID は正規化した URL の SHA-256（先頭32文字）で生成し冪等性を保証（追跡パラメータを除去）。
  - URL 正規化（スキーム/ホスト小文字化、トラッキングパラメータ削除、フラグメント削除、クエリパラメータソート）を実装。
  - テキスト前処理（URL 除去・空白正規化）を実装。
  - DuckDB への保存はチャンク化して1トランザクションで行い、INSERT ... RETURNING を使って実際に挿入された件数を正確に取得。
  - 銘柄コード抽出機能（4桁数字パターン、既知銘柄セットでフィルタリング）を実装。
- DuckDB スキーマ定義と初期化（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution の4層をカバーするスキーマ DDL を実装（raw_prices, raw_financials, raw_news, market_calendar, prices_daily, features, ai_scores, signals, orders, trades, positions, etc.）。
  - 主キー・外部キー・制約（CHECK）やインデックスを含む設計を実装し、init_schema(db_path) で初期化（冪等）・get_connection() を提供。
- ETL パイプライン基盤（src/kabusys/data/pipeline.py）
  - ETL の設計方針に基づく差分更新・バックフィル機能を持つヘルパー群（ETLResult dataclass、_table_exists、_get_max_date、get_last_price_date など）を実装。
  - 市場カレンダーを参照して非営業日を調整するヘルパー（_adjust_to_trading_day）を実装。
  - run_prices_etl を実装（差分取得、backfill 処理、jquants_client を用いた取得と保存の呼び出し）。
- その他
  - 各モジュールでのログ出力（logger）を整備し、処理の可視化を容易に。

Security
- RSS 取得と XML パース周りにおけるセキュリティ対策を多数実装（defusedxml, SSRF 検査、レスポンスサイズ上限、gzip 解凍後サイズチェック）。
- HTTP クライアントでのトークンリフレッシュ時の無限再帰防止、Retry-After の尊重、レートリミット遵守を実装。

Notes / Implementation details
- 環境設定:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で .env 自動読み込みを無効化可能。
  - .env 読み込み時は OS 環境変数を protected として優先保持し、.env.local は .env を上書きできる。
- ニュース記事の ID は URL 正規化 → SHA-256（先頭32文字）で生成。utm_* などのトラッキングパラメータは削除。
- DuckDB の保存は基本的に ON CONFLICT で冪等化しており、既存レコードの更新を行う DDL/SQL を用意。
- J-Quants クライアントはページネーションを考慮してデータ取得を行う。

Known issues
- （本リリースは初版リリースのため、運用での追加テストや監視を推奨します。今後、品質チェックルールや監視・アラートの細かな拡張、追加の ETL ジョブ（財務データの差分ETL 等）の実装を予定しています。）

今後の予定（例）
- 品質チェックモジュール quality のルール実装と ETL への統合（欠損・スパイク検出の自動通知）。
- execution 層（kabuステーション連携）とモニタリング（Slack通知等）の実装強化。
- CI テスト、ユニットテストの充実化（特にネットワーク周りのモックテスト）。

------------------------------------
参考: Keep a Changelog の推奨カテゴリに従って記載しました。必要であれば英語版やより細かな差分（コミット単位）に分解します。