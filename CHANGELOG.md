# Changelog

すべての注目すべき変更をここに記録します。  
このファイルは Keep a Changelog の形式に準拠しています。

フォーマット:
- Added: 新機能、追加されたモジュールや API
- Changed: 変更点（互換性維持）
- Fixed: 修正
- Security: セキュリティ関連の改善
- 注意 / 既知の問題: 現状の注意点や未解決の問題

-----------------------------------------------------------------------

## [0.1.0] - 2026-03-18

初回リリース。日本株自動売買システム「KabuSys」の基本機能を実装しました。
主にデータ取得・保存・ETL・RSSニュース収集・設定管理・DBスキーマを含みます。

### Added
- パッケージ基盤
  - パッケージ初期化およびバージョン情報を追加（src/kabusys/__init__.py: __version__ = "0.1.0"）。
  - 主要サブパッケージのエクスポートを定義（data, strategy, execution, monitoring）。

- 設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を自動読み込みする機能を実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - プロジェクトルートは __file__ を基点に .git または pyproject.toml を探索して特定（CWD 非依存）。
  - .env のパースロジックを実装（export プレフィックス、クォート、インラインコメント対応など）。
  - 上書き（override）挙動と protected（OS 環境変数保護）をサポート。
  - 必須環境変数チェック（_require）と Settings クラスを公開。
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID などを参照。
    - KABUSYS_ENV（development/paper_trading/live）や LOG_LEVEL の検証ロジックを実装。
    - デフォルトの DB パス（DUCKDB_PATH, SQLITE_PATH）と判定プロパティ（is_live, is_paper, is_dev）を提供。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - 日足・財務・マーケットカレンダー取得 API 実装（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
  - レート制限制御（固定間隔スロットリング _RateLimiter、120 req/min に対応）。
  - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）。
  - 401 受信時の自動トークンリフレッシュ（1 回のみ）とモジュールレベルのトークンキャッシュ。
  - duckdb への冪等保存関数を実装（save_daily_quotes, save_financial_statements, save_market_calendar）。
    - ON CONFLICT DO UPDATE を使用して重複を排除・更新。
  - 値変換ユーティリティ（_to_float, _to_int）やログ出力の補助。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードからのニュース収集処理を実装（fetch_rss, run_news_collection）。
  - セキュアな XML パース（defusedxml を使用）と XML/HTTP に対する堅牢化。
  - SSRF 対策
    - URL スキーム検証（http/https のみ許可）。
    - リダイレクト先の事前検証（_SSRFBlockRedirectHandler）。
    - プライベートIP/ループバック/リンクローカル/マルチキャストの拒否（_is_private_host）。
  - 大きなレスポンスや Gzip bomb に対する防御（MAX_RESPONSE_BYTES = 10MB、解凍後サイズ検査）。
  - URL 正規化とトラッキングパラメータ除去（_normalize_url、utm_* 等を除去）。
  - 記事ID生成は正規化 URL の SHA-256（先頭32文字）を採用して冪等性を担保。
  - テキスト前処理（URL除去・空白正規化）。
  - DuckDB への冪等保存（save_raw_news: チャンク分割 + トランザクション + INSERT ... RETURNING を使用）。
  - 記事と銘柄コードの紐付け（save_news_symbols / _save_news_symbols_bulk）。  
  - 銘柄コード抽出ユーティリティ（4桁数字パターン + known_codes フィルタ）。

- DuckDB スキーマ定義・初期化（src/kabusys/data/schema.py）
  - DataPlatform 設計に基づく3層（Raw / Processed / Feature）と Execution 層のテーブルを定義。
  - raw_prices, raw_financials, raw_news, raw_executions 等の Raw テーブル定義。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の Processed テーブル。
  - features, ai_scores などの Feature 層テーブル。
  - signals, signal_queue, orders, trades, positions, portfolio_performance 等の Execution 層テーブル。
  - 各種 CHECK 制約や PRIMARY KEY、外部キー、インデックスを定義。
  - init_schema(db_path) によりファイルの親ディレクトリを自動作成し、DDL を実行して初期化を行う。
  - get_connection(db_path) で既存 DB に接続可能。

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - 差分更新を前提とした ETL の骨組みを実装（差分の算出、backfill の概念、品質チェックを想定）。
  - ETLResult dataclass により ETL 実行結果を構造化（品質問題・エラーの収集、to_dict メソッド）。
  - 市場カレンダー調整ヘルパー（_adjust_to_trading_day）や最終取得日取得ユーティリティ（get_last_price_date 等）。
  - run_prices_etl（株価差分 ETL）を実装（idempotent に取得→保存の流れ、backfill_days を利用）。

### Changed
- 初回リリースのため該当なし（新規実装が中心）。

### Fixed
- 初回リリースのため該当なし（ただし既知の不具合あり — 下記参照）。

### Security
- RSS/XML ハンドリングに defusedxml を採用し XML ベースの攻撃に対処。
- SSRF 対策（スキーム検証、プライベートIP検出、リダイレクト事前検査）。
- レスポンスサイズの上限と Gzip 解凍後のチェックを導入（メモリ DoS / Gzip bomb 対策）。
- .env ロード時に OS 環境変数を保護する protected セットを導入。

### 注意 / 既知の問題
- run_prices_etl の戻り値が不完全（実装の途中で末尾が切れているように見え、現在は
  `return len(records), ` のみで second value を返していません）。これにより実行時に TypeError 等が発生する可能性があります。
  - 対応案: saved 変数（保存済みレコード数）を2番目の要素として返す実装に修正する必要があります。
- SQL 実行で一部文字列連結を用いた SQL 文が直接生成されている箇所がある（ただしパラメータ化して値を渡す方式を基本としている）。
  - 注意: 現在の設計では入力元が内部データ（記事/銘柄等）であり SQL インジェクションのリスクは低いが、外部入力を直接埋め込む場合はパラメータ化を徹底してください。
- strategy/execution パッケージの __init__.py は空で、戦略・注文実行のロジックはまだ未実装（プレースホルダ）。
- news_collector の DNS 解決失敗時の挙動: 現状は安全側に倒して解決失敗を非プライベートと見なす実装（テスト・運用での挙動確認推奨）。

### 開発者向けメモ
- 自動 .env ロードはテスト時に副作用となるため KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- news_collector の低レイヤー I/O はテスト容易性を考慮して _urlopen をモック可能に設計。
- jquants_client のトークンリフレッシュ回りは allow_refresh フラグで再帰を回避する設計。リフレッシュの失敗は明示的に例外化。

-----------------------------------------------------------------------

今後の予定（例）
- run_prices_etl の修正・拡完、その他 ETL ジョブ（財務・カレンダーの統合差分処理）の実装完了。
- strategy 層・execution 層の具体的なアルゴリズムと kabu API 連携の実装。
- テストカバレッジの拡充（特に SSRF/大容量レスポンス/リトライロジックのエッジケース）。
- ドキュメント整備（使用方法・データモデルの説明・運用ガイド）。

-----------------------------------------------------------------------

(注) リリースノートはコードベースから推測して作成しています。実際のコミット履歴やリリース計画に基づく変更点がある場合は、本ファイルを適宜更新してください。