# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。  

最新リリース
- 0.1.0 / 2026-03-17

## [0.1.0] - 2026-03-17
初回公開リリース。日本株自動売買システム「KabuSys」の基盤モジュール群を追加しました。主な追加点は以下のとおりです。

### 追加 (Added)
- パッケージ初期化
  - kabusys パッケージの基本 __version__ と公開モジュール定義を追加（0.1.0）。
- 環境設定管理 (kabusys.config)
  - .env ファイルおよび OS 環境変数から設定を読み込む自動ローダを実装。
  - 自動ロードの抑止フラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
  - `.env` / `.env.local` の優先順位制御（`.env.local` は override）。
  - 高度な .env パーサを実装:
    - `export KEY=val` 形式対応
    - シングル/ダブルクォート対応（バックスラッシュエスケープ処理）
    - インラインコメントの扱い、キー検証等
  - Settings クラスを提供（プロパティ経由で必須トークンやパス、環境モード、ログレベル等を取得）。
    - 環境モード検証（development / paper_trading / live）
    - ログレベル検証（DEBUG / INFO / WARNING / ERROR / CRITICAL）
    - DBパス取得（DuckDB / SQLite のデフォルトパスを提供）
- J-Quants API クライアント (kabusys.data.jquants_client)
  - 株価日足、財務データ（四半期BS/PL）、JPXマーケットカレンダーの取得・保存機能を実装。
  - レートリミッタ実装（120 req/min を守る固定間隔スロットリング）。
  - リトライ付き HTTP 呼び出し:
    - 最大リトライ回数 3 回
    - 指数バックオフ（ベース 2.0 秒）
    - ステータスコード 408/429/5xx を再試行対象
    - 429 の場合は `Retry-After` ヘッダ優先
  - 401 Unauthorized 受信時にリフレッシュトークンで自動的に id_token を再取得して1回だけリトライする仕組みを導入（無限再帰防止）。
  - id_token のモジュールレベルキャッシュを導入（ページネーション等で共有）。
  - ページネーション対応の fetch_* 関数を実装（daily_quotes, financial_statements, market_calendar）。
  - DuckDB への保存は冪等性を確保（INSERT ... ON CONFLICT DO UPDATE）する save_* 関数を実装（raw_prices, raw_financials, market_calendar）。
  - データ整形・型変換ユーティリティ（_to_float, _to_int）を提供。
  - データ取得時の fetched_at を UTC ISO 形式で記録（look-ahead bias 対策のため）。
- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードから記事を取得・前処理・DB保存するフローを実装。
  - セキュリティと堅牢性に配慮した実装:
    - defusedxml を使用した XML パース（XML Bomb 等への対策）
    - SSRF 対策: リダイレクト時のスキーム/ホスト検証ハンドラ、初回ホストのプライベートアドレス検証
    - URL スキーム制約（http/https のみ許可）
    - レスポンス受信サイズ上限（10 MB）と gzip 解凍後のサイズ検査（Gzip bomb 対策）
  - URL 正規化 (トラッキングパラメータ除去、クエリソート、フラグメント除去) と SHA-256（先頭32文字）に基づく記事ID生成で冪等性を実現。
  - テキスト前処理（URL除去・空白正規化）実装。
  - DuckDB への保存はトランザクションでチャンク化して実行、INSERT ... RETURNING を活用して実際に挿入されたレコードを返す（raw_news, news_symbols）。
  - 銘柄コード抽出ユーティリティ（4桁の日本株コード検出、既知コードセットフィルタリング）を実装。
  - 統合収集ジョブ run_news_collection を実装（ソース単位で独立したエラーハンドリング、銘柄紐付け一括保存）。
- DuckDB スキーマ定義 (kabusys.data.schema)
  - DataSchema.md に基づく包括的なスキーマを定義・初期化する init_schema を実装。
  - 生データ（raw_*）、整形済み（prices_daily 等）、特徴量（features, ai_scores）、実行系（signals, signal_queue, orders, trades, positions, portfolio_performance）まで含む多層テーブルを用意。
  - 各テーブルの制約（NOT NULL, CHECK, PRIMARY KEY, FOREIGN KEY）を明記。
  - 頻繁に使用されるクエリに対するインデックスを作成。
  - init_schema は冪等で、親ディレクトリを自動作成する機能を持つ（":memory:" 対応）。
  - get_connection を提供（既存DBへ接続。初回は init_schema を推奨）。
- ETL パイプライン基礎 (kabusys.data.pipeline)
  - 差分更新（最終取得日ベース）を行う ETL の骨子を実装。
  - ETLResult データクラスを実装（取得数・保存数・品質問題・エラーを保持、辞書化可能）。
  - 市場カレンダー先読み日数（既定 90 日）、デフォルトバックフィル日数（既定 3 日）等の定数を導入。
  - 差分更新ヘルパ（get_last_price_date / get_last_financial_date / get_last_calendar_date）を提供。
  - 価格ETLの run_prices_etl を実装（差分計算、バックフィルの挙動、取得→保存の流れ）。
  - テーブル存在確認や最大日付取得のユーティリティを実装。

### セキュリティ (Security)
- news_collector:
  - defusedxml による XML パースで外部攻撃に対する耐性を向上。
  - SSRF 防止のため、リダイレクト先検査・プライベートIPチェック・スキーム検証を実施。
  - 応答サイズの上限（MAX_RESPONSE_BYTES = 10MB）によるメモリDoS対策を実装。
- jquants_client:
  - 外部 API 通信の再試行やレート制御でサービス品質と安定性を向上（429/Retry-After 等に対応）。

### パフォーマンス (Performance)
- DuckDB へのバルク挿入はチャンク化してトランザクションを利用、挿入時のオーバーヘッドを低減。
- jquants_client は固定間隔スロットリングで API レートを平準化。

### 信頼性 / 可観測性 (Reliability / Observability)
- 各所でログ出力を強化（取得件数、保存件数、警告・例外）。
- ETLResult による処理の集約報告と品質チェック情報の保持。

### 既知の制限 / 未実装 (Known limitations)
- quality モジュール（データ品質チェック）は pipeline から参照される設計になっているが、実際のチェック実装は別途提供される想定。
- strategy / execution / monitoring パッケージはパッケージ構造上用意されていますが、このリリースでは基盤側（データ取得・保存・ETL・設定）の実装に注力しています。

## 互換性 (Compatibility)
- 初版のため破壊的変更は特にありません。将来のリリースで API（関数シグネチャやテーブル定義）に変更を加える可能性があります。

---

今後の改善予定（例）
- quality モジュールの具体的なルール実装とレポーティング（欠損・スパイク・重複検出）。
- ETL のスケジューリング / 並列化オプション。
- strategy / execution 層の実装（シミュレーション・ペーパートレード・実取引の統合）。
- テストカバレッジの拡充と CI ワークフローの追加。

（この CHANGELOG はコードベースから推測して作成しています。実際のリリースノート作成時はリリース担当者による確認・追記を推奨します。）