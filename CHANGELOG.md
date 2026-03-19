# Changelog

すべての注記は Keep a Changelog の形式に準拠し、セマンティックバージョニングを採用します。  
（初期リリース v0.1.0 をコードベースから推測して作成しています）

## [0.1.0] - 2026-03-19

### 追加 (Added)
- パッケージ初期実装
  - パッケージ名: kabusys、バージョン: 0.1.0
  - パッケージ公開用 __all__ に data/strategy/execution/monitoring を定義。

- 設定・環境変数管理 (kabusys.config)
  - .env ファイル（.env, .env.local）または環境変数から設定読み込みを自動で行う機能を実装。
    - 自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に探すため、CWD に依存しない。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env.local は .env を上書き（override=True）する挙動。
    - OS 環境変数を protected キーとして保持し、不用意な上書きを防止。
  - .env パーサ実装（export プレフィックス、シングル/ダブルクォート、インラインコメント等を考慮）。
  - Settings クラスを提供し、以下の必須/既定設定をプロパティで取得可能:
    - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - 任意/既定: KABUSYS_ENV (development|paper_trading|live)、LOG_LEVEL（DEBUG, INFO, ...）、KABU_API_BASE_URL、DUCKDB_PATH、SQLITE_PATH
  - バリデーション（KABUSYS_ENV・LOG_LEVEL の有効値チェック）、ヘルパー（is_live 等）を実装。

- データ収集クライアント (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装。
    - レート制限（120 req/min）を固定間隔スロットリングで制御する RateLimiter。
    - 再試行ロジック（指数バックオフ、最大3回、408/429/5xx に対するリトライ）。
    - 401 応答時はリフレッシュトークンを用いた id_token 自動更新を1回のみ行い再試行。
    - ページネーション対応（pagination_key）で全件取得。
    - 取得時に fetched_at を UTC ISO8601 で付与し、look-ahead bias に対処。
  - データ保存ユーティリティ（DuckDB 用）
    - save_daily_quotes / save_financial_statements / save_market_calendar を実装。
    - raw_* テーブルへ冪等に保存（ON CONFLICT DO UPDATE）する実装。
    - 型変換ユーティリティ (_to_float, _to_int) を提供。空値や不正値を安全に扱う。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィード収集パイプラインを実装。
    - fetch_rss: RSS 取得・XML パース（defusedxml 使用）・記事抽出を実装。
    - preprocess_text: URL 除去・空白正規化。
    - URL 正規化 (_normalize_url) とトラッキングパラメータ除去（utm_* 等）。
    - 記事 ID を正規化 URL の SHA-256 の先頭32文字で生成（冪等性確保）。
    - SSRF 対策:
      - fetch 前にホストのプライベートアドレス判定（_is_private_host）を行い拒否。
      - リダイレクト時にスキーム/ホストを再検査するカスタムハンドラ (_SSRFBlockRedirectHandler) を利用。
      - 許可スキームは http/https のみ。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）、gzip 解凍後のサイズ検査を実装（Gzip bomb 対策）。
    - DB 保存:
      - save_raw_news: チャンク分割（_INSERT_CHUNK_SIZE）して INSERT ... ON CONFLICT DO NOTHING RETURNING id を用い、実際に挿入された記事IDを返す。トランザクションでコミット/ロールバック。
      - save_news_symbols / _save_news_symbols_bulk: news と銘柄コードの紐付けをバルク挿入（ON CONFLICT DO NOTHING RETURNING）で実装。
    - 銘柄コード抽出: 正規表現で 4 桁数字を抽出し、known_codes に存在するもののみを返す機能を提供。

- DuckDB スキーマ定義 (kabusys.data.schema)
  - Raw 層の主要テーブル DDL を定義:
    - raw_prices, raw_financials, raw_news, raw_executions（途中まで定義あり）
  - DataSchema.md に基づく 3 層構造（Raw / Processed / Feature / Execution）の方針を明記。

- 研究・特徴量モジュール (kabusys.research)
  - factor_research:
    - モメンタム（calc_momentum）: mom_1m/mom_3m/mom_6m、ma200_dev を計算（DuckDB のウィンドウ関数を活用）。
    - ボラティリティ（calc_volatility）: 20日 ATR、相対ATR (atr_pct)、20日平均売買代金(avg_turnover)、出来高比率(volume_ratio) を計算。
    - バリュー（calc_value）: raw_financials から最新の財務データを取得して PER / ROE を計算（EPS=0 や欠損時は None）。
    - スキャン範囲やウィンドウの設計（バッファや必要行数チェック）を実装。
  - feature_exploration:
    - calc_forward_returns: target_date の終値から N 営業日後までの将来リターンを一度に取得するクエリを実装（LEAD を利用）。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を実装。レコード数が 3 未満または分散が 0 の場合は None を返す。
    - rank: 同順位は平均ランクを返す実装（浮動小数誤差対策に round(v, 12) を使用）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリを実装。
  - 研究モジュールは DuckDB 接続を受け取り prices_daily / raw_financials のみを参照し、外部 API へはアクセスしない設計。

### セキュリティ (Security)
- news_collector:
  - defusedxml を使った XML パースで XML Bomb 等を低減。
  - SSRF 対策: ホストのプライベート判定、リダイレクト時のスキーム/ホスト検査、許可スキームの制限。
  - レスポンス上限（10MB）と gzip 解凍後の再検査を実装しメモリ DoS を防止。
- jquants_client:
  - 認証トークンの自動リフレッシュは 1 回に限定し、無限再帰を防止（allow_refresh フラグ）。

### パフォーマンス・信頼性
- API クライアント:
  - 固定間隔スロットリングと指数バックオフにより API レート制御とリトライを行う。
  - 401 リフレッシュ再試行や Retry-After ヘッダ優先対応（429）。
- DB 操作:
  - バルク挿入、チャンクサイズ制御、トランザクションまとめによりオーバーヘッドを削減。
  - INSERT ... RETURNING を活用して実際に挿入された件数を正確に取得。

### ドキュメント・設計注記 (Notes)
- 研究モジュールは外部ライブラリ（pandas 等）に依存せず標準ライブラリ + duckdb で実装されているため、軽量でテストしやすい反面、行列演算の最適化等は行っていない。
- calc_forward_returns の horizons は営業日ベース（LEAD のオフセット）で、引数は 1〜252 の正の整数である必要がある。
- rank は浮動小数点の丸め（round(v,12)）による ties 検出を行っているため、極端に近接した値の取り扱いに注意。
- news の記事 ID は正規化 URL に基づく SHA-256 の先頭 32 文字。トラッキングパラメータ削除およびクエリソートが行われるため、同一記事の別 URL バリエーションはある程度まとめられる。
- extract_stock_codes は 4 桁数字のみを対象（日本株標準）。特殊ケースは known_codes により制御可能。

### 既知の制約 / 注意点
- Settings._require は未設定時に ValueError を送出するため、サービス起動前に必須環境変数を準備する必要がある。
- DuckDB のスキーマ定義はファイル内で開始されているが、Execution 層（raw_executions）の定義が途中で終わっているため、完全なスキーマ定義は今後の追加を要する。
- news_collector の DNS 解決失敗時は安全側の判断で「非プライベート」とみなす（内部ネットワーク判定の厳格性は環境に依存）。

### 互換性 (Deprecated / Breaking changes)
- 初版のため破壊的変更は無し。ただし、今後のスキーマ拡張や設定名変更は互換性に影響を与える可能性がある。

---

（注）本 CHANGELOG は与えられたコードから推測して作成しています。リポジトリ内の実際のリリースノートや仕様書がある場合はそちらを優先してください。必要であれば、各モジュールごとにより詳細な変更点・使用例・環境設定手順を追記します。