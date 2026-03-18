CHANGELOG
=========
すべての重要な変更を記録します。フォーマットは "Keep a Changelog" に準拠しています。

Unreleased
----------
（なし）


[0.1.0] - 2026-03-18
--------------------
初回リリース。日本株自動売買システムの基盤機能を実装しました。主な追加点・設計方針は以下の通りです。

Added
- パッケージの初期バージョンを追加（kabusys v0.1.0）。
- 環境変数／設定管理モジュール（kabusys.config）
  - .env、自動読み込みロジック（プロジェクトルートの判定：.git または pyproject.toml を基準）。
  - .env → .env.local の読み込み優先度（.env.local は上書き、OS 環境変数保護）。
  - 読み込みの自動無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - 必須設定取得ヘルパ（_require）と Settings クラス。
  - サポートする主要な環境変数例:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH（デフォルト data/kabusys.duckdb）、SQLITE_PATH（デフォルト data/monitoring.db）
    - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL 検証

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 日足（OHLCV）、財務データ（四半期）、JPX マーケットカレンダー取得 API を実装。
  - ページネーション対応。
  - API レート制限遵守（120 req/min）用の固定間隔スロットリング _RateLimiter を実装。
  - リトライ戦略（指数バックオフ、最大 3 回）。429 の場合は Retry-After を考慮。
  - 401 受信時はリフレッシュトークンで id_token を自動更新して 1 回リトライ（無限再帰防止フラグあり）。
  - id_token のモジュールレベルキャッシュ（ページネーション間で共有）。
  - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）
    - 冪等性: INSERT ... ON CONFLICT DO UPDATE を使用して重複上書き。
    - fetched_at に UTC タイムスタンプを記録（Look-ahead バイアス防止のため）。
  - 型変換ユーティリティ _to_float, _to_int（入力の頑健な変換）。

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS 取得から raw_news / news_symbols への保存までのフローを実装。
  - 設計上の特徴：
    - 記事ID は正規化した URL の SHA-256（先頭32文字）で生成し冪等性を保証。
    - トラッキングパラメータ（utm_*, fbclid 等）を除去する URL 正規化。
    - defusedxml を利用して XML Bomb 等の攻撃を防御。
    - SSRF 対策：
      - URL スキーム検証（http/https のみ許可）。
      - リダイレクト時にスキームとホストの事前検証を行う _SSRFBlockRedirectHandler。
      - ホストがプライベート/ループバック/リンクローカル等の場合は拒否。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）でメモリ DoS を防止。gzip 解凍後も検査。
    - チャンク単位のバルク INSERT（_INSERT_CHUNK_SIZE）とトランザクションでの一括保存。
    - INSERT ... RETURNING を使い、実際に挿入された記事IDや紐付け件数を正確に返却。
  - RSS パーサは title, content（content:encoded 優先）, pubDate パース、テキスト前処理（URL 除去・空白正規化）を実施。
  - 銘柄コード抽出ユーティリティ（4桁数字パターン）と bulk 紐付け保存ロジック。

- DuckDB スキーマ管理（kabusys.data.schema）
  - DataPlatform に基づく 3 層＋実行層のテーブル定義を実装（Raw / Processed / Feature / Execution）。
  - 代表的テーブル：
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種制約（CHECK/PRIMARY KEY/FOREIGN KEY）を定義。
  - 検索向けインデックスを作成する DDL を提供。
  - init_schema(db_path) でディレクトリ作成 → 全DDL実行 → 接続を返すユーティリティ。
  - get_connection(db_path) で既存 DB へ接続（初期化は行わない）。

- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新フロー（最終取得日からの差分計算、バックフィル対応）と個別 ETL ジョブの骨組みを実装。
  - ETLResult データクラスで実行結果・品質チェック結果・エラーを集約。
  - 差分取得のユーティリティ（最終日取得、営業日調整、テーブル存在チェック）を実装。
  - run_prices_etl の差分ロジック（バックフィル日数、最小データ日付、fetch → save の流れ）を実装。

Security
- 複数のセキュリティ対策を導入：
  - RSS パーサに defusedxml を使用して XML 攻撃を防止。
  - SSRF 対策（スキーム検証、プライベート IP 拒否、リダイレクト時検証）。
  - .env 自動読み込みは安全に設計（OS 環境変数を保護、オプトアウト可能）。
  - ネットワーク呼び出しに対してタイムアウトと受信サイズチェックを適用。

Performance / Reliability
- API 呼び出しに対してレートリミットとリトライ（指数バックオフ）を組み合わせて信頼性を確保。
- DuckDB へのバルク挿入をチャンク化し、トランザクションでコミットしてオーバーヘッドを削減。
- ページネーションと id_token キャッシュをサポートし、長い取得処理での効率化を図る。
- 各種保存処理は冪等（ON CONFLICT）を志向しており、再実行可能な ETL を想定。

Notes / Known limitations
- strategy および execution パッケージは初期のパッケージ構成を提供していますが、個別戦略や発注ロジックの実装は含まれていません（今後の拡張ポイント）。
- ETL モジュールは品質チェック機能（quality モジュール）を想定した設計になっていますが、quality の具体実装はこのリリースに含まれない可能性があります（コード内参照あり）。
- SQLite（monitoring 用）などの監視用 DB 連携は設定値とパスを提供しますが、監視機能本体は別実装を想定。

その他
- ログ出力を多用しており、動作可視化と障害診断がしやすい設計になっています。

Acknowledgements
- 本リリースはプロジェクトの初期基盤を整えることを目的としています。今後、戦略実装、発注エンジン、監視・アラート、品質検出ルールなどを段階的に追加予定です。