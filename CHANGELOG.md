# CHANGELOG

すべての変更は Keep a Changelog のフォーマットに準拠します。  
このリポジトリはセマンティックバージョニングを採用しています。

なお、本CHANGELOGは提供されたソースコードから機能・設計意図を推測して作成しています。

## [Unreleased]

## [0.1.0] - 2026-03-17
初回公開リリース。日本株の自動売買基盤（KabuSys）のコアライブラリを実装。

### 追加 (Added)
- パッケージ基礎
  - パッケージ初期化: `kabusys.__init__` にバージョン `0.1.0` とエクスポートモジュール一覧を追加。

- 設定 / 環境変数管理 (`kabusys.config`)
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを実装。
  - プロジェクトルート自動検出機能（.git または pyproject.toml を探索）を実装し、CWD に依存しない自動 .env ロードを実現。
  - .env の自動読み込み順序: OS 環境変数 > .env.local > .env。テスト等で無効化するために `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
  - .env パーサーの強化: export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、インラインコメントの扱い等に対応。
  - 必須項目取得時のエラー報告 (`_require`)。環境値の検証（`KABUSYS_ENV`, `LOG_LEVEL`）を実装。
  - 設定プロパティ: J-Quants / kabuステーション / Slack / データベースパス等。

- J-Quants API クライアント (`kabusys.data.jquants_client`)
  - 基本機能: 日次株価（OHLCV）、財務データ（四半期 BS/PL）、マーケットカレンダーを取得する fetch_* 関数を実装（ページネーション対応）。
  - 認証: リフレッシュトークンから ID トークンを取得する `get_id_token` を実装。401 時の自動トークンリフレッシュをサポート。
  - レート制御: モジュール内固定間隔スロットリング（120 req/min）を実装する `_RateLimiter`。
  - 再試行ロジック: 指数バックオフ、最大3回のリトライ、HTTP 408/429 と 5xx に対するリトライ処理、429 の場合は `Retry-After` ヘッダ優先。
  - エラーハンドリング: JSON デコード失敗や各種ネットワーク例外の扱いを整備し、詳細ログを出力。
  - DuckDB への保存関数（冪等）: `save_daily_quotes`, `save_financial_statements`, `save_market_calendar` を実装（INSERT ... ON CONFLICT DO UPDATE を利用）。
  - 取得時刻の記録（look-ahead bias 対策）: `fetched_at` を UTC ISO フォーマットで保存。
  - 型変換ユーティリティ `_to_float`, `_to_int` を実装し、入力の堅牢な正規化を実現。

- ニュース収集モジュール (`kabusys.data.news_collector`)
  - RSS フィードから記事を取得する `fetch_rss`、記事を DuckDB に保存する `save_raw_news`、記事と銘柄紐付けを保存する `save_news_symbols`、一括紐付け用 `_save_news_symbols_bulk`、および統合ジョブ `run_news_collection` を実装。
  - セキュリティ対策:
    - XML パースに defusedxml を使用し XML Bomb 等に対処。
    - リダイレクト時にスキーム検証・ホストのプライベートIP検査を行う `_SSRFBlockRedirectHandler` を導入（SSRF 対策）。
    - RSS URL のスキームは http/https のみ許可。
    - レスポンス受信サイズ上限（MAX_RESPONSE_BYTES=10MB）を設け、受信時に超過を検出して拒否（メモリ DoS / gzip bomb への対策）。
    - gzip 圧縮レスポンスの解凍後にもサイズチェックを行う。
  - 安全な URL 処理:
    - トラッキングパラメータ（utm_* 等）を削除・正規化してから SHA-256（先頭32文字）で記事IDを生成（冪等性確保）。
    - URL スキーム検証、最終URLの再検証を行うことで不正なリンクを除外。
  - テキスト前処理: URL 除去・空白正規化を行う `preprocess_text`。
  - 銘柄コード抽出: 正規表現ベースで 4桁コード抽出し、`known_codes` によるフィルタリングを行う `extract_stock_codes`。
  - DB 操作の最適化: チャンクサイズ制御、1 トランザクション内でのバルク INSERT、INSERT ... RETURNING を用いて実際に挿入されたレコードID/件数を返す設計。

- DuckDB スキーマ管理 (`kabusys.data.schema`)
  - DataSchema.md に基づくテーブル群を定義して初期化する DDL を実装。
    - Raw / Processed / Feature / Execution 各レイヤ向けのテーブルを網羅（raw_prices, raw_financials, raw_news, market_calendar, prices_daily, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance など）。
  - 制約・チェック: CHECK 制約や PRIMARY KEY、外部キーを適用してデータ整合性を確保。
  - インデックス定義を提供（頻出クエリパターンを想定）。
  - `init_schema(db_path)` でスキーマ初期化（親ディレクトリ自動作成）と接続を返す。`:memory:` によるインメモリ DB にも対応。
  - `get_connection(db_path)` で既存 DB に接続（スキーマ初期化は行わない）。

- ETL パイプライン基盤 (`kabusys.data.pipeline`)
  - ETL 実行結果を表す `ETLResult` dataclass を実装（品質チェック結果・エラー一覧・集計値等を保持）。
  - 差分取得ユーティリティ: テーブル最終日取得ヘルパー、営業日に調整する `_adjust_to_trading_day`、最低開始日 `_MIN_DATA_DATE` 等。
  - 個別 ETL ジョブ（差分更新）: `run_prices_etl` の初期実装。DB の最終取得日を元に date_from を自動算出し、J-Quants から差分取得→保存するフローを実装。
  - 品質チェックのためのフック（quality モジュールとの連携を想定）。

- その他
  - 型ヒント・ドキュメンテーション文字列を豊富に付与し、テスト容易性のため一部関数（例: `_urlopen`）をモック可能に設計。
  - ロギング（logger）を各モジュールで用い、操作ログと警告を出力。

### セキュリティ (Security)
- RSS/HTTP 周りでの複数の防御を実装:
  - defusedxml を使用した XML パース（XML 脆弱性対策）。
  - SSRF 対策: リダイレクト先スキーム検証、ホストのプライベートアドレス判定、最終URLの再検証。
  - レスポンスサイズ制限と gzip 解凍後の再チェック（Gzip/Bomb対策）。
- .env 読み込みにおいて OS 環境変数を保護するための protected キーセットを導入。  

### パフォーマンス (Performance)
- J-Quants クライアントでのレート制御（固定間隔）導入により API 制限準拠。
- DB のバルク挿入でチャンクリング（_INSERT_CHUNK_SIZE）を採用し、SQL 長やパラメータ数の問題に対処。
- DuckDB への複数行挿入は executemany / INSERT ... RETURNING などで効率化。

### 変更 (Changed)
- （初版のため該当なし）

### 修正 (Fixed)
- （初版のため該当なし）

### 削除 (Removed)
- （初版のため該当なし）

### 非推奨 (Deprecated)
- （初版のため該当なし）

### 既知の制限・注意点 (Known issues / Notes)
- run_prices_etl のソースは差分取得・保存の実装を行っているが、提供されたコードの末尾が途中で切れているように見え、戻り値処理や品質チェック適用の最終的な統合処理が継続実装される想定です（本CHANGELOG作成時点では一部未完成の可能性があります）。
- テストコード（ユニット・統合テスト）はソース内に含まれていないため、CI やテストシナリオを別途用意する必要があります。
- 実運用では各種リトライ/例外ハンドリングの動作確認（特にネットワーク/認証周り）や、DuckDB のバックアップ・スキーマ移行方針を検討してください。
- NewsCollector の URL 正規化やトラッキングパラメータのリストは固定的（_TRACKING_PARAM_PREFIXES）であり、必要に応じて拡張が必要です。
- Slack / kabu API 等への実際の送信（発注や通知）に関する実装はこのスナップショットには含まれていません（execution/strategy パッケージは初期化ファイルのみ）。

---

メジャー/マイナーな機能追加やセキュリティ修正は、次回リリース時に [Unreleased] から移動して記録します。必要であれば、CHANGELOG をより詳細に分割（例えば「API クライアント」「ニュース収集」「DB スキーマ」「ETL」など）して拡張します。