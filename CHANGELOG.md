# CHANGELOG

すべての変更は Keep a Changelog に準拠して記載しています。  
このファイルは、ソースコードの内容から推測して作成した初期リリース向けの変更履歴です。

全体方針
- バージョニングは package/__init__.py の __version__（0.1.0）に基づきます。
- 日付はコード解析時点の日付を使用しています。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-18
初回リリース（ベース実装）

### Added
- パッケージ基盤
  - kabusys パッケージを追加。公開モジュール: data, strategy, execution, monitoring（strategy・execution は __init__ のみで、実装は今後）。
  - バージョン: 0.1.0

- 設定管理
  - 環境変数管理モジュールを追加（kabusys.config）。
  - .env/.env.local の自動読み込み機能を実装（プロジェクトルート判定は .git / pyproject.toml を基準）。
  - .env のパースロジックを実装（コメント、export 形式、シングル/ダブルクォート、行内コメントの扱いに対応）。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を追加。
  - Settings クラスを提供し、J-Quants トークン、kabu API 設定、Slack トークン、DBパス（DuckDB/SQLite）、ログレベル、環境（development/paper_trading/live）等をプロパティで取得可能に。

- J-Quants API クライアント
  - kabusys.data.jquants_client を追加。
  - 日足（OHLCV）、財務データ（四半期 BS/PL）、マーケットカレンダーを取得する fetch_* 関数を実装（ページネーション対応）。
  - HTTP リクエスト層にレートリミッタ（固定間隔スロットリング、120 req/min）を導入。
  - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を再試行）。
  - 401 受信時はリフレッシュトークンから id_token を自動リフレッシュして 1 回リトライ。
  - id_token のモジュールレベルキャッシュを実装（ページネーション間で共有）。
  - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。いずれも冪等性を保つ（ON CONFLICT DO UPDATE を利用）。
  - 数値変換ユーティリティ（_to_float, _to_int）を実装し、空文字や不正値に対する安全な変換を提供。
  - 取得時刻（fetched_at）を UTC ISO8601 形式で記録し、データ取得のタイミングトレースをサポート。

- ニュース収集
  - kabusys.data.news_collector を追加。
  - RSS フィードからのニュース収集（fetch_rss）と DuckDB への保存（save_raw_news, save_news_symbols, _save_news_symbols_bulk）を実装。
  - 記事 ID を URL 正規化後の SHA-256（先頭32文字）で生成し冪等性を担保。トラッキングパラメータ（utm_* 等）を除去して正規化。
  - XML パースに defusedxml を使用して XML による攻撃を軽減。
  - SSRF 対策:
    - URL スキーム検証（http/https のみ許可）。
    - コンテンツ取得時のリダイレクト先を検査するカスタムリダイレクトハンドラ（ホストがプライベート/ループバック/リンクローカルであれば拒否）。
    - DNS 解決で取得したアドレスの判定も行う。
  - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）を導入し、事前の Content-Length チェックと実際の読み込みの両方で上限超過を検出。
  - gzip 圧縮のサポートと、解凍後のサイズ再チェック（Gzip bomb 対策）。
  - テキスト前処理（URL除去・連続空白正規化）と日付パース（RSS pubDate を UTC naive datetime に変換）を実装。
  - raw_news 挿入はチャンク化して一度のトランザクションで行い、INSERT ... RETURNING で実際に挿入された ID を返却することで正確な新規件数を取得。
  - news_symbols（記事と銘柄の紐付け）をバルク挿入で効率化。重複排除を行い INSERT ... RETURNING で挿入数を返す。

- スキーマ（DuckDB）
  - kabusys.data.schema を追加。
  - DataPlatform.md に基づく 3 層（Raw / Processed / Feature / Execution）を意識したテーブル定義を実装。
  - raw_prices, raw_financials, raw_news, raw_executions などの Raw レイヤー。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols などの Processed レイヤー。
  - features, ai_scores などの Feature レイヤー。
  - signals, signal_queue, orders, trades, positions, portfolio_* などの Execution レイヤー。
  - テーブル作成用の init_schema(db_path) を実装（親ディレクトリ自動作成、:memory: サポート）。get_connection() で既存 DB へ接続可能。
  - 頻出クエリ用のインデックス定義を追加。

- ETL パイプライン
  - kabusys.data.pipeline を追加。
  - ETLResult データクラスを実装し、ETL のメタ情報（取得件数／保存件数／品質問題／エラー一覧）を保持。
  - 差分更新用のユーティリティ（テーブルの最終取得日取得、営業日調整 _adjust_to_trading_day）を実装。
  - run_prices_etl を実装（差分算出、backfill デフォルト 3 日、jquants_client を使った取得と DuckDB への保存、ログ出力）。
  - 市場カレンダーの先読み（_CALENDAR_LOOKAHEAD_DAYS = 90）・データ最小開始日を定義。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- RSS パーサに defusedxml を採用し XML 関連の脆弱性を軽減。
- ニュース取得での SSRF 対策を導入（スキーム検証、プライベートアドレス検出、リダイレクト時検査）。
- .env パースで危険な入力やコメントを適切に扱うよう考慮。

### Internal / Notes
- jquants_client における API 呼び出しはページネーション、レートリミット、リトライ、401 自動リフレッシュに対応しており、大量データ取得時の堅牢性を向上。
- news_collector の記事ID設計（トラッキングパラメータ除去→正規化→SHA256）は、同一記事の二重保存を抑止するため設計された。
- DuckDB スキーマは将来の集計・機械学習・実運用（オーダー・トレード管理）を見越して幅広いテーブルを定義している。
- strategy / execution / monitoring モジュールはパッケージ構造のみ用意されており、各機能の実装は今後追加予定。

### Known issues / TODO
- run_prices_etl を含む ETL 関数群は基本ロジックが実装されているが、品質チェック（quality モジュール）との統合や追加の ETL ジョブ（財務データ・カレンダーの差分ETLなど）は今後の作業項目です。
- パッケージ内に空の __init__ を持つモジュール（strategy, execution, data.__init__, など）があり、今後の拡張で具体的な実装（発注ロジック、監視機能など）を追加予定。

---

（この CHANGELOG はコードベースの現状から推測して作成しました。実際のコミット履歴やリリースノートがある場合はそちらを優先してください。）