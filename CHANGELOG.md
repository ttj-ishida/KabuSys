# Changelog

すべての注目すべき変更はこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠します。  

一覧は重要度の高い変更をカテゴリ別（Added / Changed / Fixed / Security など）に分けて記載しています。

## [unreleased]

（現在リリース済みの変更は下のバージョン履歴を参照してください。）

---

## [0.1.0] - 2026-03-17

初期リリース。日本株自動売買システム「KabuSys」の基本コンポーネントを実装しました。

### Added
- パッケージ基礎
  - kabusys パッケージの初期化（src/kabusys/__init__.py）およびバージョン設定（0.1.0）。
  - パッケージ構成: data, strategy, execution, monitoring を公開APIに含める。

- 環境設定管理
  - .env / .env.local / OS 環境変数からの設定自動読み込み機能を実装（src/kabusys/config.py）。
  - プロジェクトルート検出ロジック（.git または pyproject.toml を基準）を追加し、CWD に依存しない自動ロードを実現。
  - .env パーサを実装し、export 形式やクォート、インラインコメント等に対応する堅牢なパース処理をサポート。
  - 自動ロードを無効化するためのフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を導入。
  - 必須環境変数チェック（_require）と Settings クラスを提供（J-Quants / kabu / Slack / DB パス等のプロパティを含む）。
  - KABUSYS_ENV と LOG_LEVEL の検証（許容値チェック）および便利なプロパティ（is_live / is_paper / is_dev）を追加。

- J-Quants API クライアント
  - 株価日足、財務（四半期 BS/PL）、JPX マーケットカレンダーを取得するクライアントを実装（src/kabusys/data/jquants_client.py）。
  - API レート制御（120 req/min）を行う固定間隔レートリミッタを追加。
  - リトライロジック（指数バックオフ、最大3回）とステータス別扱い（408/429/5xx の再試行、429 の Retry-After 優先）を実装。
  - 401 レスポンス時の自動トークンリフレッシュ（1回のみ）を実装。
  - ページネーション対応（pagination_key を用いたループ取得）。
  - DuckDB へ冪等に保存する save_* 関数（save_daily_quotes / save_financial_statements / save_market_calendar）を追加。ON CONFLICT DO UPDATE により上書き可能。
  - 型変換ユーティリティ（_to_float / _to_int）を実装し、不正値を安全に扱う。
  - 取得時刻（fetched_at）を UTC で記録し、Look-ahead Bias のトレースを可能に。

- ニュース収集モジュール
  - RSS フィードから記事を収集・正規化し DuckDB に保存する機能を実装（src/kabusys/data/news_collector.py）。
  - デフォルトRSSソース（Yahoo Finance のカテゴリ RSS）を提供。
  - URL 正規化（トラッキングパラメータ除去、クエリソート、スキーム/ホスト小文字化、フラグメント除去）と記事ID（SHA-256 の先頭32文字）生成を実装。
  - defusedxml を用いた安全な XML パース、gzip 対応、レスポンスサイズ上限（10 MB）によるメモリDoS対策を実装。
  - SSRF 対策: URL スキーム検証（http/https のみ許可）、ホストのプライベートアドレス検査、リダイレクト時の事前検証ハンドラを導入。
  - 記事テキスト前処理（URL 除去・空白正規化）を実装。
  - DuckDB への冪等保存: save_raw_news は INSERT ... RETURNING により実際に挿入された記事IDを返す。チャンク挿入とトランザクションを利用。
  - 記事と銘柄コードの紐付け（news_symbols）を一括保存する内部ユーティリティを実装。
  - テキスト中から4桁銘柄コードを抽出する関数（extract_stock_codes）を追加。known_codes によりフィルタリング。

- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution 層のテーブル定義と初期化関数を追加（src/kabusys/data/schema.py）。
  - raw_prices、raw_financials、raw_news、raw_executions などの Raw テーブル、processed（prices_daily、market_calendar、fundamentals、news_articles 等）、features / ai_scores、signals / signal_queue / orders / trades / positions / portfolio_performance を含む実用的なスキーマを実装。
  - インデックス（頻出クエリのための idx_*）を作成。
  - init_schema(db_path) によりディレクトリ自動作成と DDL の冪等実行を提供。get_connection() で既存DBへ接続可能。

- ETL パイプライン
  - 差分更新戦略（最終取得日を元に backfill_days を考慮した差分取得）を持つ ETL パイプラインの雛形を実装（src/kabusys/data/pipeline.py）。
  - ETLResult データクラスを追加し、取得数・保存数・品質問題・エラーの集約を行う仕組みを提供。
  - 市場カレンダー先読み（lookahead）や最小データ開始日の定義など、運用上のパラメータを導入。
  - テーブル存在チェックや最大日付取得ユーティリティを実装。
  - run_prices_etl の骨組み（差分算出・fetch -> save のフロー）を実装（fetch は jquants_client を使用）。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Security
- ニュース収集時に以下のセキュリティ対策を実装:
  - defusedxml を使用した XML パースで XML Bomb 等を軽減。
  - レスポンスサイズ制限（MAX_RESPONSE_BYTES）および gzip 解凍後サイズ検査でメモリ攻撃を緩和。
  - SSRF 対策: 非 http/https スキームの拒否、DNS 解決したアドレスのプライベート判定、リダイレクト先の検証。
- .env 読み込みでは OS 環境変数を保護するため protected セットを導入し、上書き操作を制御。

### Notes / Design decisions
- J-Quants API はレート制限やページネーション、トークンリフレッシュ、リトライの複雑さがあるため、クライアントはこれらを包括的に扱う設計とした。
- DB 操作は可能な限り冪等（ON CONFLICT）にして再実行耐性を持たせた。
- ETL は品質チェックを別モジュール（quality）で行い、重大障害検出時でも収集処理自体は継続させる方針（Fail-Fast ではない）。
- NewsCollector の記事IDはトラッキングパラメータ除去後にハッシュ化して冪等性を確保。

---

## その他
- ドキュメントや DataPlatform.md / DataSchema.md / Section など設計資料に基づく実装を行っています。今後のリリースで以下を追加・改善予定です:
  - strategy / execution / monitoring の具象実装（現在はパッケージプレースホルダ）。
  - quality モジュールの実働実装と ETL への統合テスト。
  - 単体テスト・統合テスト、CI 設定、型チェックの強化。

---

（注）日付はソースコードの初期バージョンに合わせた仮のリリース日です。必要に応じて実際のリリース日やコミットハッシュ、比較リンクを追記してください。