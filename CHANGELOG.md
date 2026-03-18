# Changelog

すべての変更は Keep a Changelog 規約に準拠します。  
このプロジェクトはセマンティックバージョニングを採用しています。

## [Unreleased]


## [0.1.0] - 2026-03-18

初回リリース。日本株自動売買システムのベースライブラリを実装しました。主な追加項目は以下の通りです。

### 追加（Added）
- パッケージ基盤
  - kabusys パッケージの初期公開（__version__ = 0.1.0）。
  - サブパッケージ構成: data, strategy, execution, monitoring（strategy/execution は初期は空の __init__ を提供）。

- 設定/環境変数管理（kabusys.config）
  - .env/.env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml から探索）。
  - 自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサ実装: export プレフィックス、クォート対応、インラインコメント処理などをサポートする堅牢なパース処理。
  - Settings クラスを提供し、主要設定値をプロパティで取得（必須項目は未設定時に ValueError を送出）。
  - サポートする主要設定:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN（必須）
    - SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV (development|paper_trading|live、検証あり)
    - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL、検証あり)
  - OS 環境変数を保護するため .env の上書きロジックに protected set を導入。

- Data 層（kabusys.data）
  - J-Quants API クライアント（kabusys.data.jquants_client）
    - API レート制限（120 req/min）を守る固定間隔スロットリング実装（_RateLimiter）。
    - HTTP リトライロジック（指数バックオフ、最大 3 回、408/429/5xx をリトライ対象）。
    - 401 受信時は自動的にリフレッシュして 1 回リトライ（トークン再取得時は再帰防止）。
    - ページネーション対応の fetch_* 関数:
      - fetch_daily_quotes（株価日足）
      - fetch_financial_statements（四半期財務）
      - fetch_market_calendar（JPX カレンダー）
    - DuckDB への保存関数（冪等性を考慮、ON CONFLICT DO UPDATE を使用）:
      - save_daily_quotes → raw_prices
      - save_financial_statements → raw_financials
      - save_market_calendar → market_calendar
    - 入力データの安全な型変換ユーティリティ: _to_float, _to_int（不正入力は None に変換）。
    - id_token のモジュールレベルキャッシュを実装（ページネーション間で共有）。

  - ニュース収集（kabusys.data.news_collector）
    - RSS フィードから記事を取得して raw_news に保存するフローを実装。
    - セキュリティ/堅牢化:
      - defusedxml を使用した XML パース（XML Bomb 対策）。
      - SSRF 対策: 非 http/https スキーム拒否、リダイレクト先のスキーム/プライベートアドレス検査、DNS 解決でのプライベートIP検出関数を実装。
      - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）と gzip 展開後のサイズ検査（Gzip bomb 対策）。
      - User-Agent を設定し、Content-Length の事前チェック。
    - 記事 ID: URL 正規化（スキーム/ホスト小文字化、トラッキングパラメータ削除、フラグメント削除、クエリソート）後の SHA-256 の先頭 32 文字を採用し、冪等性を確保。
    - テキスト前処理: URL 除去、空白正規化。
    - 銘柄抽出: 正規表現による 4 桁コード検出（既知コード集合でフィルタ）。
    - DB 保存:
      - save_raw_news: INSERT ... ON CONFLICT DO NOTHING RETURNING id を使い、実際に挿入された記事IDを返却。チャンク挿入・単一トランザクション。
      - save_news_symbols / _save_news_symbols_bulk: news_symbols テーブルへの紐付けをチャンク挿入で実施し、実挿入数を正確に返却。
    - run_news_collection: 複数ソースを順次処理し、個々のソース失敗が全体を止めないように設計。既知銘柄コードが与えられれば記事と銘柄の紐付けまで実行。

  - DuckDB スキーマ定義（kabusys.data.schema）
    - Raw Layer の DDL を定義（raw_prices, raw_financials, raw_news, raw_executions の定義を含む。初期DDLを実装）。

- Research 層（kabusys.research）
  - feature_exploration モジュール:
    - calc_forward_returns: DuckDB の prices_daily を参照して将来リターンをまとめて取得（複数ホライズン対応、存在しない場合は None）。
    - calc_ic: Spearman ランク相関による IC 計算（欠損や ties を考慮、有効サンプル < 3 の場合 None を返す）。
    - rank: 同順位は平均ランクを返すランク化ユーティリティ（丸めによる ties 検出漏れ対策あり）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー。
  - factor_research モジュール:
    - calc_momentum: mom_1m, mom_3m, mom_6m, ma200_dev（200 日 MA 乖離）を計算。
    - calc_volatility: atr_20（20 日 ATR の平均）、atr_pct、avg_turnover（20 日平均売買代金）、volume_ratio（当日/20日平均）を計算。true_range の NULL 伝播制御を施し不正なカウントを防止。
    - calc_value: raw_financials から最新財務（target_date 以前）を取得し per, roe を計算（EPS が 0 または欠損時は per = None）。
  - すべての research 関数は prices_daily / raw_financials テーブルのみ参照し、本番の発注 API 等にはアクセスしない設計（Research 環境向け）。

### 変更（Changed）
- （初版のため該当なし）

### 修正（Fixed）
- （初版のため該当なし）

### セキュリティ（Security）
- RSS 取得処理に対する SSRF 対策と XML パースの安全化、レスポンスサイズ制限などを導入し、外部入力起点の攻撃に対する耐性を高めています。

### 既知の制限 / 注意点（Known issues / Notes）
- strategy / execution / monitoring の具体的な発注ロジック・監視機能はこのバージョンでは未実装（パッケージ構成のみ）。
- DuckDB のテーブル名（prices_daily 等）に依存するため、Data 層の利用時はスキーマ初期化を適切に行ってください。
- J-Quants API の rate limiting は固定間隔待ち合わせ方式で実装されており、厳密なスループット要件がある場合は運用で調整が必要です。
- get_id_token や _ID_TOKEN_CACHE はモジュールレベルの簡易キャッシュであり、マルチプロセス環境では外部共有されません。
- news_collector の DNS 解決失敗時は安全側（非プライベートとみなす）に通す設計です。必要に応じて挙動を見直してください。

---

今後の予定（例）
- strategy / execution の実装（発注ロジック、バックテスト、ポジション管理）
- 監視・アラート連携（Slack 等）
- テストカバレッジの拡充、CI 設定

以上。