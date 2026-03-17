# Changelog

すべての重大な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

最新の変更は上部に記載します。

## [Unreleased]
- なし

## [0.1.0] - 2026-03-17
初回リリース（ベース機能の実装）

### 追加
- パッケージ基礎
  - kabusys パッケージを追加。バージョンは 0.1.0。
  - パッケージの公開 API として data, strategy, execution, monitoring を __all__ に定義。

- 設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
    - 読み込み順序: OS環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト用）。
    - プロジェクトルートは __file__ を起点に .git または pyproject.toml を探索して決定（CWD 非依存で配布後も動作）。
  - .env ファイルパーサを実装（コメント、export プレフィックス、クォート、インラインコメント、エスケープ等に対応）。
  - Settings クラスを提供し、以下の主要設定をプロパティ経由で取得可能に:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH / SQLITE_PATH（デフォルトを設定）
    - KABUSYS_ENV（development / paper_trading / live の検証）
    - LOG_LEVEL（検証）

- J-Quants クライアント（kabusys.data.jquants_client）
  - J-Quants API からのデータ取得を行うクライアントを実装。
    - 対応データ: 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダー
  - レート制御: 固定間隔スロットリング（120 req/min を想定）を実装する RateLimiter。
  - リトライロジック: 指数バックオフ付きリトライ（最大 3 回）。HTTP 408/429/5xx を再試行対象とする。
    - 429 の場合は Retry-After ヘッダを優先。
  - 認証トークン管理:
    - refresh token から id_token を取得する get_id_token。
    - モジュールレベルの id_token キャッシュを導入し、ページネーション間で共有。
    - 401 受信時は id_token を自動リフレッシュして 1 回だけリトライ。
  - ページネーション対応の fetch_* 関数を提供:
    - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - DuckDB へ冪等に保存する save_* 関数を提供:
    - save_daily_quotes, save_financial_statements, save_market_calendar
    - 保存は ON CONFLICT DO UPDATE により上書き（fetched_at を更新）して冪等性を確保
  - 値変換ユーティリティ: _to_float, _to_int（不正値や空値の安全なハンドリング）

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードから記事を収集し raw_news テーブルへ保存するモジュールを実装。
    - デフォルトソース: Yahoo Finance のビジネスカテゴリ RSS。
  - 設計上の特徴:
    - 記事ID: 正規化 URL の SHA-256（先頭32文字）で生成し冪等性を保証（utm 等のトラッキングパラメータ除去）。
    - defusedxml を用いて XML Bomb 等の攻撃に対処。
    - SSRF 対策:
      - URL スキーム検証（http/https のみ許可）
      - リダイレクト時にスキームと宛先がプライベートアドレスかを検証するカスタム RedirectHandler を利用
      - 初回 URL と最終 URL 双方でプライベートホストチェックを行う
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10 MB）および gzip 解凍後のサイズチェック（Gzip bomb 対策）
    - テキスト前処理（URL 除去・空白正規化）を実装（preprocess_text）
    - 銘柄コード抽出（4桁数字を抽出し、known_codes でフィルタ）を実装（extract_stock_codes）
    - DB 保存はチャンク化およびトランザクションで実施し INSERT ... RETURNING を用いて実際に挿入されたID/件数を返す
  - 主要関数:
    - fetch_rss: RSS 取得とパース
    - save_raw_news: raw_news へ挿入（新規挿入された記事IDの配列を返す）
    - save_news_symbols / _save_news_symbols_bulk: news_symbols への紐付け保存
    - run_news_collection: 複数ソースを巡回して収集・保存・銘柄紐付けを行う（各ソースは独立してエラーハンドリング）

- スキーマ定義（kabusys.data.schema）
  - DuckDB 用のスキーマを定義・初期化するモジュールを実装。
    - 3 層構造のテーブルを定義: Raw / Processed / Feature / Execution 層
    - 主要テーブル: raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance など
    - 制約（PRIMARY KEY / CHECK / FOREIGN KEY）やインデックスを定義
    - init_schema(db_path) で親ディレクトリ自動作成とテーブル作成（冪等）
    - get_connection(db_path) で既存 DB への接続（スキーマ初期化は行わない）

- ETL パイプライン（kabusys.data.pipeline）
  - ETL の基本実装を追加。
    - 差分更新の概念（最終取得日からの差分取得、バックフィル）
    - 市場カレンダーの先読み（lookahead）
    - ETLResult dataclass（実行結果の構造化、品質問題とエラーの集約）
    - ヘルパー: テーブル存在チェック、最大日付取得、営業日調整
    - 差分ETL の helper 関数: get_last_price_date, get_last_financial_date, get_last_calendar_date
    - run_prices_etl: 株価日足差分 ETL を実装（date_from 自動算出・backfill 処理・取得→保存の流れ）
  - テストしやすさを考慮した設計:
    - id_token の注入可能性（関数引数）
    - news_collector._urlopen をモック差し替え可能

### セキュリティ
- defusedxml を使った XML パースで XML 攻撃を軽減。
- RSS 収集での SSRF 対策を多数実装:
  - スキーム制限（http/https のみ）
  - リダイレクト先の事前検査（スキームとプライベートアドレス判定）
  - 初回および最終 URL の両方でプライベートホストチェック
  - Response サイズ上限と gzip 解凍後の上限チェック
- .env パーサでの安全配慮（クォートとエスケープの適切な扱い、コメントの扱い）

### パフォーマンス / 信頼性
- J-Quants API クライアントでレートリミットに従う RateLimiter を導入（外部 API のレート制限順守）。
- 冪等性を重視した DB 保存（ON CONFLICT DO UPDATE / DO NOTHING）により再実行コストを低減。
- 大量挿入時のチャンク処理（news_collector の _INSERT_CHUNK_SIZE）で SQL パラメータ数や長さの問題を回避。
- トランザクションをまとめてコミットし、ロールバックで一貫性を保護。

### テスト性
- ネットワークアクセス箇所を容易にモック可能に設計（例: news_collector._urlopen の差し替え）。
- jquants_client の id_token 注入で外部認証のモックが可能。

### 既知の問題（注意点）
- run_prices_etl の実装の末尾が不完全で、戻り値が (len(records), ) のようにタプルが不足している箇所がある（現状のコードでは target の戻り型注釈と矛盾し、呼び出し側でエラーとなる可能性がある）。この箇所は修正が必要。
- 実運用では環境変数（特に秘密情報）の取り扱いに注意すること。Settings は必須キー未設定時に ValueError を投げるため、起動前に .env か環境変数を正しく構成する必要がある。
- DuckDB スキーマは詳細に定義されているが、マイグレーション機能は未実装。スキーマ変更時は手動マイグレーションが必要。

### 破壊的変更
- なし（初回リリース）

### 削除
- なし

---

今後の予定（例）
- run_prices_etl の戻り値不備修正と同様の unit テスト追加
- pipeline の ETL フルワークフロー（財務・カレンダー ETL の実装と品質チェックの統合）
- strategy / execution / monitoring モジュールの実装拡充（現状はパッケージエントリのみ）
- マイグレーション機能の追加（スキーマ変更の自動適用）
- より細かいメトリクス収集と監視・アラート機能の追加

もし CHANGELOG に特定の項目を追記したい、あるいは日付・フォーマットを調整したい場合は指示してください。