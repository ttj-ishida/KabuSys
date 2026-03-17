# Changelog

すべての重要な変更をここに記載します。  
このプロジェクトはセマンティックバージョニングに従います。詳細は「Keep a Changelog」形式に準拠しています。

## [0.1.0] - 2026-03-17

### 追加 (Added)
- パッケージ初期リリースを追加
  - パッケージメタ: src/kabusys/__init__.py に __version__ = "0.1.0"、公開モジュール一覧を定義。

- 環境設定管理 (src/kabusys/config.py)
  - .env および環境変数から設定を自動読み込み（OS環境変数 > .env.local > .env の優先）。
  - プロジェクトルート検出ロジック（.git または pyproject.toml を起点）を実装し、パッケージ配布後でも正しく .env を探索。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト向け）。
  - .env パーサ（export プレフィックス、シングル/ダブルクォートのエスケープ、インラインコメントの扱い等）を実装。
  - 必須設定取得ヘルパ `_require` と Settings クラスを提供（J-Quants, kabu, Slack, DB パス, 環境/ログレベル検証プロパティ等）。
  - Settings に is_live / is_paper / is_dev 等のユーティリティプロパティを追加。

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - 株価日足、財務データ、マーケットカレンダーを取得する fetch_* 関数を実装（ページネーション対応）。
  - get_id_token によるリフレッシュトークン→IDトークン取得を実装。
  - グローバルなトークンキャッシュ（ページネーション間共有）を実装。
  - レート制限（120 req/min）を固定間隔スロットリングで制御する RateLimiter を実装。
  - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）を実装。429 の場合は Retry-After ヘッダを優先。
  - 401 受信時はトークン自動リフレッシュを試み、1 回だけリトライする処理を追加。
  - DuckDB への冪等保存関数 save_daily_quotes / save_financial_statements / save_market_calendar を実装（ON CONFLICT DO UPDATE で重複更新）。
  - データ整形ユーティリティ (安全な数値変換: _to_float, _to_int) を実装。
  - レスポンスの JSON デコードエラーや最大リトライ到達時の適切な例外処理を追加。

- RSS ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィード取得、記事整形、raw_news への保存、記事と銘柄コードの紐付け処理を実装。
  - 既定の RSS ソース（例: Yahoo Finance ビジネスカテゴリ）を定義。
  - 記事 ID を正規化URL の SHA-256（先頭32文字）で生成し冪等性を担保。
  - URL 正規化でトラッキングパラメータ (utm_*, fbclid 等) を除去、クエリをソート、フラグメント除去を実施。
  - defusedxml を使用して XML パース（XML Bomb 等への対策）。
  - SSRF 対策:
    - リダイレクト検査ハンドラでスキームとプライベートIPを検証。
    - 事前にホストがプライベートかチェックしてアクセスを拒否。
    - URL スキームは http/https のみ許可。
  - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）および gzip 解凍後のサイズチェックによるメモリDoS対策。
  - テキスト前処理（URL除去、空白正規化）を実装。
  - DuckDB への保存はチャンク化とトランザクションで一括挿入、INSERT ... RETURNING を用いて実際に挿入された件数を返す（save_raw_news, save_news_symbols, _save_news_symbols_bulk）。
  - 銘柄コード抽出ロジック（4桁数字、known_codes フィルタ）を実装。
  - run_news_collection により複数ソースの独立した収集と DB 保存を行い、銘柄紐付けを一括保存。

- DuckDB スキーマ定義と初期化 (src/kabusys/data/schema.py)
  - Raw / Processed / Feature / Execution 層を意識したテーブル定義を実装（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance）。
  - 各テーブルに適切な制約（PRIMARY KEY, CHECK, FOREIGN KEY）を定義。
  - 頻出クエリ向けのインデックスを定義。
  - init_schema(db_path) でディレクトリ自動作成およびテーブル/インデックス作成を行う、get_connection を提供。

- ETL パイプライン (src/kabusys/data/pipeline.py)
  - 差分更新を行う ETL ヘルパ関数群を実装（最終取得日の取得ヘルパ、営業日調整、個別 ETL ジョブの骨組み）。
  - ETLResult データクラスタを実装し、取得数・保存数・品質問題・エラー一覧等の集約と to_dict 出力を提供。
  - run_prices_etl の差分更新ロジック（最終取得日 - backfill_days による再取得、最小データ日付の扱い）を実装。
  - 市場カレンダー先読み等の定数を定義（_CALENDAR_LOOKAHEAD_DAYS 等）。
  - 品質チェックモジュール（quality）との連携仕組みを用意（重大度の扱い等、品質問題は集約して呼び出し元で判断）。

### 修正 (Changed)
- 初期リリースのため該当なし。

### 修正 (Fixed)
- 初期リリースのため該当なし。

### セキュリティ (Security)
- RSS パーサで defusedxml を使用し XML パーシングの脆弱性を軽減。
- SSRF 対策を多数実装:
  - URL スキーム制限（http/https のみ）。
  - ホストのプライベート/ループバック/リンクローカル判定（DNS 解決した全 A/AAAA レコードも検査）。
  - リダイレクト時にスキーム・ホストを検査するカスタムリダイレクトハンドラ。
- ネットワーク経由のリソース取得に対して受信バイト数上限を設け、gzip 解凍後のサイズチェックも実施（Gzip bomb 対策）。
- .env パースでのエスケープ処理やコメント処理を慎重に実装し、不正な環境設定読み込みを低減。

### 既知の制限 / 今後の課題 (Known issues / TODO)
- quality モジュールの実装詳細（チェックルールや閾値）はこの変更セットに含まれておらず、ETL パイプラインからの呼び出しで利用する想定。
- pipeline.run_prices_etl の戻り値は現状 (len(records), ) のように未完の形になっている箇所がある（実装継続の必要あり）。（ソースを参照のこと）
- 単体テスト・統合テストはコードに合わせて追加することを推奨。特にネットワーク周り、SSRF 判定、.env パーサ、DB トランザクション周りのテストが重要。

---

（初期リリース: データ収集・保存基盤と基本的な ETL フロー、外部 API クライアント、ニュース収集機能、DB スキーマを整備しました。今後は品質チェック実装、監視・実行モジュールの実装、テストの充実を進めます。）