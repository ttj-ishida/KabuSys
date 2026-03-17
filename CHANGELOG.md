# Changelog

すべての注目すべき変更を記録します。形式は Keep a Changelog に準拠しています。  
このファイルは後続のリリースごとに更新してください。

## [0.1.0] - 2026-03-17

初回リリース。日本株自動売買の基盤機能を提供する最初の実装を追加しました。

### 追加 (Added)
- パッケージの基本構造を追加
  - kabusys パッケージ（サブモジュール: data, strategy, execution, monitoring を公開）
  - バージョン: 0.1.0

- 設定・環境変数管理（kabusys.config）
  - .env/.env.local ファイルおよび環境変数から設定を自動ロード
  - プロジェクトルート検出（.git または pyproject.toml を基準）により CWD に依存しない自動ロード
  - .env パーサ: export プレフィックス、シングル/ダブルクォート、エスケープ、行末コメントの取り扱いに対応
  - 環境変数上書きルール（OS 環境変数を protected として保護）
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - Settings クラスを提供（J-Quants / kabu ステーション / Slack / DB パス / ログレベル / 環境判定プロパティ等）
  - KABUSYS_ENV, LOG_LEVEL の値検証（許可値チェック）

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 基本機能: id token 取得（get_id_token）、株価日足・財務データ・マーケットカレンダー取得（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）
  - ページネーション対応（pagination_key の追跡）
  - レートリミッタ実装（固定間隔スロットリング、デフォルト 120 req/min を尊重）
  - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）。429 の場合は Retry-After ヘッダを優先
  - 401 受信時はトークン自動リフレッシュを行い 1 回再試行（再帰を防ぐため allow_refresh オプション）
  - DuckDB への冪等保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）
    - INSERT ... ON CONFLICT DO UPDATE により重複排除・更新を実現
  - データ型変換ユーティリティ（_to_float / _to_int）
  - fetched_at（UTC）を保存して Look-ahead bias を追跡可能に

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィード取得と記事整形（fetch_rss / preprocess_text）
  - 記事ID の生成: URL 正規化後の SHA-256（先頭32文字）で冪等性を担保（utm_* 等のトラッキングパラメータ除去）
  - セキュリティ対策:
    - defusedxml を利用した XML パース（XML Bomb 等対策）
    - SSRF 対策: HTTP/HTTPS スキーム検証、ホスト/IP のプライベートアドレス判定、リダイレクト時の検査用ハンドラ
    - レスポンスサイズ上限（10 MB）指定、GZIP 解凍後のサイズチェック（Gzip bomb 対策）
    - 許可されないスキームやサイズ超過時はログを出して安全にスキップ
  - DuckDB への保存:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING + INSERT ... RETURNING id（チャンク処理、1 トランザクション）
    - save_news_symbols / _save_news_symbols_bulk: news と銘柄コードの紐付けを一括挿入（ON CONFLICT DO NOTHING + RETURNING で実際に挿入された件数を取得）
  - 銘柄コード抽出ユーティリティ（extract_stock_codes: 正規表現で 4 桁コード抽出し known_codes でフィルタ）
  - run_news_collection: 複数ソースの統合収集ジョブ（各ソースは独立してエラーハンドリング）

- DuckDB スキーマ定義・初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution レイヤーのテーブル定義を追加（raw_prices, raw_financials, raw_news, market_calendar, features, ai_scores, signals, orders, trades, positions, 等）
  - 各テーブルに制約（PRIMARY KEY, CHECK, FOREIGN KEY 等）を設定
  - 頻出クエリのためのインデックス作成（idx_*）
  - init_schema(db_path) でスキーマを冪等に初期化し DuckDB 接続を返す
  - get_connection(db_path) により既存 DB への接続を取得

- ETL パイプライン（kabusys.data.pipeline）
  - ETLResult データクラス: ETL 実行結果の集約（フェッチ数、保存数、品質問題、エラー等）
  - 差分更新ロジック: DB の最終取得日から差分だけ取得、backfill_days による再取得（デフォルト 3 日）のサポート
  - 市場カレンダー調整ユーティリティ（_adjust_to_trading_day）
  - テーブルの最終日取得ユーティリティ（get_last_price_date, get_last_financial_date, get_last_calendar_date）
  - run_prices_etl の骨格（fetch → save → ログ）

### 変更 (Changed)
- （初版のため過去からの変更はなし）

### 修正 (Fixed)
- （初版のため過去の不具合修正はなし）

### セキュリティ (Security)
- RSS XML のパースに defusedxml を使用し安全性を向上
- ニュース収集で SSRF 対策を実装（スキーム検証、プライベート IP 判定、リダイレクト時の検査）
- .env ローダーは OS 環境変数を保護し、テスト時に自動ロードを無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）

### 既知の問題 / 注意点 (Known issues / Notes)
- run_prices_etl の実装末尾に戻り値が途中で切れている個所が見られます（提供コードでは "return len(records), " のように保存件数を含めた完全なタプルが返されていないようです）。意図としては (fetched_count, saved_count) を返す想定のため、本番運用前に戻り値の確認とユニットテストを推奨します。
- DuckDB スキーマは多くの制約（CHECK, FOREIGN KEY）を含みます。既存 DB からの移行時はバックアップを取り、必要に応じてスキーマ変更手順を検討してください。
- J-Quants API のレート制限やリトライ挙動は実運用環境の API レスポンスに合わせて調整することを推奨します（閾値やバックオフ係数等）。
- news_collector の extract_stock_codes は 4 桁数字のみを候補とするため、将来的に銘柄形式を拡張する必要がある場合は正規表現とフィルタロジックを見直してください。

---

将来的なリリースでは以下を予定しています（非網羅）:
- ETL の完全実装と品質チェックモジュール（quality）の統合テスト
- execution / strategy / monitoring モジュールの実装とエンドツーエンドテスト
- 監視・アラート（Slack 連携）の追加
- より詳細なログ出力とメトリクス収集

ご質問やリクエストがあればお知らせください。