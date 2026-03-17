CHANGELOG
=========

すべての注目すべき変更はここに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

Unreleased
----------

（なし）

0.1.0 - 2026-03-17
------------------

Added
- 初期リリース: KabuSys 日本株自動売買システムのコアモジュールを追加。
  - パッケージメタ情報:
    - バージョン: 0.1.0 (src/kabusys/__init__.py)
    - エクスポート: data, strategy, execution, monitoring（strategy と execution はプレースホルダを含む）
- 環境設定管理 (src/kabusys/config.py)
  - .env / .env.local の自動読み込み（プロジェクトルートは .git または pyproject.toml を起点に探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - .env パーサ: export 形式、シングル/ダブルクォート、エスケープ、行内コメントの扱いに対応。
  - 必須環境変数取得ヘルパー (_require) と Settings クラスにより設定値をプロパティで提供（J-Quants トークン、kabu API、Slack、DB パス、環境種別、ログレベル等）。
  - env / log_level 値のバリデーション（許容値セットを定義）。
- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、マーケットカレンダー取得 API を実装。
  - レート制御: 固定間隔スロットリングで 120 req/min を遵守する RateLimiter 実装。
  - 再試行ロジック: 指数バックオフ、最大 3 回（408/429/5xx を対象）。429 の場合は Retry-After ヘッダ優先。
  - 401 発生時の自動トークンリフレッシュ（1 回のみ）とトークンキャッシュ。
  - ページネーション対応（pagination_key の追跡）。
  - DuckDB への冪等保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を提供。INSERT ... ON CONFLICT DO UPDATE を使用。
  - fetched_at を UTC (Z) 形式で記録。
  - データ変換ユーティリティ (_to_float, _to_int) を実装し、型安全に処理。
- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィード収集、前処理、記事の冪等保存、銘柄紐付けワークフローを実装。
  - セキュリティ対策・堅牢化:
    - defusedxml による XML パース（XML Bomb 対策）。
    - SSRF 対策: URL スキーム検証（http/https のみ）、プライベートホスト判定（IP/DNS 解決による検査）、リダイレクト時の事前検証ハンドラ実装。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES=10MB）と gzip 解凍後の追加検査（Gzip bomb 対策）。
    - 受信時の Content-Length チェックと実際に読み込むバイト数の上限管理。
  - URL 正規化とトラッキングパラメータ除去（utm_, fbclid 等）、SHA-256（先頭32文字）で記事 ID を生成して冪等性を担保。
  - テキスト前処理（URL 除去、空白正規化）。
  - DB 保存はチャンク分割、トランザクションでまとめて行い、INSERT ... RETURNING により実際に挿入された件数を取得。
  - 銘柄コード抽出ロジック（4桁数字、既知銘柄セットとの突合）と bulk 紐付け保存。
- DuckDB スキーマ管理 (src/kabusys/data/schema.py)
  - Raw / Processed / Feature / Execution 層にまたがるテーブル群（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance）を定義。
  - 各種制約（PRIMARY KEY、CHECK 等）を定義してデータ品質を担保。
  - 利用頻度の高いクエリに対応するインデックス群を作成。
  - init_schema(db_path) でディスク上の親ディレクトリ自動作成 → テーブル/インデックス作成（冪等）。
  - get_connection(db_path) により既存 DB へ接続。
- ETL パイプライン (src/kabusys/data/pipeline.py)
  - 差分更新型 ETL の実装: 最終取得日確認 → 必要な範囲だけ API から取得 → DB に保存。
  - ETLResult データクラスで実行結果（取得件数、保存件数、品質問題、エラー）を集約・シリアライズ可能。
  - 市場カレンダーヘルパー: 非営業日の調整ロジック（過去方向に最近の営業日へ調整）。
  - 差分ヘルパー: raw_prices/raw_financials/market_calendar の最終日取得ユーティリティ。
  - run_prices_etl 実装（差分取得、バックフィル日数の考慮、J-Quants クライアント利用、保存処理）。
  - 設計上の方針: デフォルトのバックフィルは 3 日、初回ロードは 2017-01-01 から。
- その他
  - data パッケージの初期モジュール構成を追加（jquants_client, news_collector, schema, pipeline）。
  - SQL 文の長大化を考慮したチャンク/プレースホルダロジックやトランザクション処理を多数導入。

Security
- news_collector の実装により、RSS 取り込みに関する以下の脅威に対処:
  - XML Bomb / 実行時 XML 攻撃（defusedxml）
  - SSRF（スキーム/ホスト検証、リダイレクト検査、プライベート IP 判定）
  - 大容量応答によるメモリ DoS（受信サイズ上限、gzip 解凍後のチェック）

Changed
- （初回リリースのためなし）

Fixed
- （初回リリースのためなし）

Deprecated
- （初回リリースのためなし）

Removed
- （初回リリースのためなし）

Notes / Known limitations
- strategy と execution パッケージは現状モジュール定義（パッケージ）を含むが、エンドポイント実装はこれから追加される想定です。
- 品質チェック（quality モジュール）はパイプラインから利用する設計になっているが、quality モジュール自体は本差分に含まれるコードベースに依存するため、統合時に追加実装や調整が必要です。
- ETL 周りは設計によりエラー検出後も収集を継続する方針ですが、運用上のアクション（リトライ／アラート等）は呼び出し元で処理する想定です。

Authors
- 開発者: KabuSys 開発チーム（コードベースから推測して作成）

License
- 明示的なライセンス表記はソース内に含まれていません。利用時はリポジトリの LICENSE を確認してください。