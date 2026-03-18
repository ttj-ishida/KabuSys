# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に従います。  
現在のバージョンはパッケージメタデータに基づき 0.1.0 です。

## [Unreleased]


## [0.1.0] - 2026-03-18

初回リリース — KabuSys 日本株自動売買システムの基礎モジュール群を追加。

### 追加 (Added)

- パッケージ全体
  - 初期パッケージ構成を追加。主要サブパッケージ: data, research, strategy, execution, monitoring（__all__ に定義）。
  - バージョン: 0.1.0 を設定。

- 設定・環境読み込み (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを追加。
  - プロジェクトルート検出ロジックを実装（.git または pyproject.toml を探索）。作業ディレクトリ (CWD) に依存しない自動読み込み。
  - .env/.env.local の読み込み順序を実装（OS 環境変数 > .env.local > .env）。.env.local は上書き（override）される。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化するフラグを実装（テストのため）。
  - .env のパースを堅牢化:
    - コメント行や export KEY=val 形式に対応。
    - シングル/ダブルクォートとバックスラッシュエスケープを正しく処理。
    - インラインコメント判定や空白処理の挙動を明確化。
  - 必須環境変数取得関数 _require と Settings のプロパティを提供（J-Quants/J-Quants トークン、kabu API、Slack、DB パス、ログレベル、環境モード等）。
  - KABUSYS_ENV / LOG_LEVEL の妥当性チェックを追加（許容値は development / paper_trading / live、及び DEBUG/INFO/...）。

- データ取得クライアント (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装。
  - レート制御: 固定間隔スロットリングによる 120 req/min 制限（内部 RateLimiter）。
  - 再試行 (retry) ロジック: 指数バックオフ、最大3回、408/429/5xx に対応。429 の場合は Retry-After ヘッダを優先。
  - 401 Unauthorized を検知して自動でリフレッシュトークンから id_token を再取得して一回リトライする機構を実装（無限再帰回避のため allow_refresh フラグあり）。
  - ページネーション対応で /prices/daily_quotes、/fins/statements、/markets/trading_calendar 等の fetch_* 関数を実装。
  - DuckDB へ保存する save_* 関数を提供（raw_prices, raw_financials, market_calendar 用）。冪等化のため ON CONFLICT DO UPDATE を使用。
  - データパースユーティリティ _to_float / _to_int を追加。_to_int は "1.0" のようなケースを変換可能だが小数部が残るものは None で安全に処理。
  - fetched_at を UTC ISO 形式で記録し、Look-ahead Bias のトレーサビリティを考慮。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードから記事を取得し raw_news / news_symbols に保存する機能を実装。
  - セキュリティと堅牢性:
    - defusedxml を使用して XML Bomb 等を防止。
    - SSRF 対策: URL スキーム検証、プライベート/ループバックアドレスの検出（DNS 経由の A/AAAA 解析含む）、リダイレクト時の事前検証ハンドラ実装（_SSRFBlockRedirectHandler）。
    - 受信サイズ上限: MAX_RESPONSE_BYTES（デフォルト 10MB）でメモリ DoS や gzip-bomb を防止。
    - gzip 圧縮レスポンスの安全な解凍と再サイズチェック。
  - URL 正規化・記事ID生成:
    - URL のトラッキングパラメータ（utm_* 等）を除去して正規化し、SHA-256 の先頭32文字を記事IDとして生成（冪等性の担保）。
  - テキスト前処理ユーティリティ: URL 除去、空白正規化等。
  - RSS パースと記事抽出（title, content, pubDate のパース）を実装。pubDate のパース失敗時は現在時刻で代替し警告を出力。
  - DB 保存:
    - save_raw_news はチャンク化して INSERT ... ON CONFLICT DO NOTHING RETURNING id を使い、実際に挿入された記事IDのリストを返す（トランザクションを使用）。
    - save_news_symbols / _save_news_symbols_bulk で記事と銘柄の紐付けを効率的に保存（重複除去、チャンク化、INSERT ... RETURNING により正確な挿入数を返す）。
  - 銘柄コード抽出: 正規表現で 4 桁数字を抽出し、known_codes によるフィルタリングを行い重複を除去して返す。
  - run_news_collection により複数ソースを横断して収集・保存・銘柄紐付けを実行。ソースごとに独立してエラーハンドリング（1 ソース失敗でも他は継続）。

- 研究用（Research）モジュール (kabusys.research)
  - feature_exploration モジュールを追加:
    - calc_forward_returns: ある基準日から複数ホライズン（デフォルト 1,5,21 営業日）の将来リターンを DuckDB の prices_daily テーブルを参照して計算。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算するユーティリティ（NA と ties の扱い、最低有効レコード数チェックを実装）。
    - rank: 同順位（ties）は平均ランクを与える実装で、丸め誤差対策として round(..., 12) を使用。
    - factor_summary: 指定カラムの count/mean/std/min/max/median を計算。
  - factor_research モジュールを追加:
    - calc_momentum: mom_1m/mom_3m/mom_6m、200日移動平均乖離率 (ma200_dev) を計算（ウィンドウ不足時は None）。
    - calc_volatility: 20日 ATR、ATR 比率、20日平均売買代金、出来高比率を計算。true_range の NULL 伝播を厳密に扱う実装。
    - calc_value: raw_financials から基準日以前の最新財務データを結合して PER/ROE を計算（EPS が 0 または NULL の場合は PER を None）。
  - 研究系関数はすべて DuckDB の prices_daily / raw_financials テーブルのみを参照し、本番発注 API にはアクセスしない方針。

- スキーマ定義 (kabusys.data.schema)
  - DuckDB 用の初期スキーマ定義を追加（Raw Layer を含む）。raw_prices, raw_financials, raw_news, raw_executions などの DDL を用意（CREATE TABLE IF NOT EXISTS）。
  - データレイヤの想定（Raw / Processed / Feature / Execution）をドキュメントに明記。

- テスト・開発補助
  - ニュース収集の _urlopen（内部で opener を利用）や config の自動ロード無効化フラグなど、単体テストで差し替え可能なフックを提供。

### セキュリティ (Security)

- RSS/HTTP 関連で以下を実装し安全性を向上:
  - defusedxml による XML パース（XML Bomb 対策）。
  - SSRF 対策: スキーム検証、プライベート IP/ループバック/リンクローカル/マルチキャストの拒否、リダイレクト時の検査。
  - レスポンス長の制限（MAX_RESPONSE_BYTES）、gzip の検査で DoS を抑制。
- API クライアント側:
  - 認証トークンの取り扱いで自動リフレッシュ機構を実装（401 の際に id_token 再取得）し、不正アクセス時の耐性を向上。

### 変更 (Changed)

- 初回リリースのため該当なし。

### 修正 (Fixed)

- 初回リリースのため該当なし。

### 既知の制約 / 注意点 (Notes)

- duckdb の SQL 実行は SQL 文内に f-string を用いている箇所があり、実行時にプレースホルダで渡されるパラメータと組み合わせているが、将来的に SQL インジェクションへの注意（動的 SQL 生成時の変数展開）を推奨。
- research モジュールや data モジュールは外部ライブラリ（pandas 等）に依存しない実装を目指しているため、大規模データ処理での最適化は今後の課題。
- raw_executions の DDL はファイル末尾で途中まで定義があるため、実運用前にスキーマの最終確認が必要。

---

もし追加で CHANGELOG に記載してほしい細かなポイント（例: 重要な関数の使用例、リリース時のマイグレーション手順など）があれば教えてください。