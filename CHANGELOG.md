# CHANGELOG

すべての注目すべき変更はこのファイルに記載します。  
フォーマットは「Keep a Changelog」準拠です。

なお、本CHANGELOGは与えられたコードベースの内容から推測して作成しています（初期リリース相当のまとめ）。

## [Unreleased]

- 特になし（初期リリース相当の状態を反映）

## [0.1.0] - 2026-03-19

### 追加 (Added)
- パッケージ基盤
  - パッケージエントリポイントを追加（src/kabusys/__init__.py）。バージョンを "0.1.0" とし、公開 API として data/strategy/execution/monitoring をエクスポート。

- 環境設定管理
  - 環境変数自動読み込み機能を実装（src/kabusys/config.py）。
    - .env/.env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動検出して読み込む。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動読み込みを無効化可能。
    - .env パーサは export プレフィックス、シングル/ダブルクォート、インラインコメント、エスケープを考慮した堅牢な実装。
    - 必須環境変数取得用ヘルパー _require と、settings オブジェクトを提供。
    - サポートされる設定例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL など。KABUSYS_ENV と LOG_LEVEL は許容値チェックを行う（development/paper_trading/live / DEBUG|INFO|...）。

- データ取得クライアント（J-Quants）
  - J-Quants API クライアントを実装（src/kabusys/data/jquants_client.py）。
    - レート制限（120 req/min）を守る固定間隔レートリミッタ実装。
    - 冪等的な DuckDB 保存用ユーティリティ（save_daily_quotes, save_financial_statements, save_market_calendar）。
    - ページネーション対応の fetch_daily_quotes / fetch_financial_statements（pagination_key 利用）。
    - 401 受信時のトークン自動リフレッシュ、指定のステータスに対する指数バックオフリトライ（408/429/5xx を対象）。
    - レスポンス JSON のデコードエラーやネットワーク例外に対する明示的なハンドリング。
    - 型変換ユーティリティ (_to_float, _to_int) を提供（不正値は None に正規化）。

- ニュース収集（RSS）
  - ニュース収集モジュールを追加（src/kabusys/data/news_collector.py）。
    - RSS フィード取得（fetch_rss）と前処理（URL 除去・空白正規化）。
    - defusedxml を用いた安全な XML パース（XML Bomb 等への対策）。
    - SSRF 対策: リダイレクト時のスキーム検査、プライベート IP 判定、最終 URL 再検証を実装。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES=10MB）および gzip 解凍後のサイズ検査を実装（DoS対策）。
    - URL 正規化（トラッキングパラメータ除去、フラグメント除去、クエリソート）と記事ID生成（正規化 URL の SHA-256 先頭32文字）。
    - raw_news テーブルへの冪等保存（INSERT ... ON CONFLICT DO NOTHING）と、INSERT ... RETURNING による新規挿入IDの取得（チャンク処理、トランザクションまとめ）。
    - 銘柄コード抽出ユーティリティ（4桁コードを正規表現で抽出し既知コード集合でフィルタ）。
    - run_news_collection により複数ソースの収集→保存→（既知銘柄が与えられた場合）銘柄紐付けまで一括実行。

- DuckDB スキーマ
  - DuckDB のスキーマ定義モジュールを追加（src/kabusys/data/schema.py）。
    - Raw 層用テーブル DDL 定義: raw_prices, raw_financials, raw_news, raw_executions（設計ノートと制約付きカラムを含む）。
    - スキーマは DataSchema.md に基づく 3 層（Raw / Processed / Feature / Execution）構造の方針を明記。

- リサーチ（特徴量・ファクター）
  - 研究用モジュールを追加（src/kabusys/research/*）。
    - feature_exploration.py:
      - calc_forward_returns: 指定基準日から複数ホライズン（デフォルト 1,5,21 営業日）の将来リターンを DuckDB の prices_daily から一括取得。
      - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）計算。欠損・非有限値の除外、3件未満は None を返す。
      - rank: 同順位の平均ランク処理を行うランク関数（round(v,12) により浮動小数誤差を緩和）。
      - factor_summary: 各ファクター列の count/mean/std/min/max/median を算出。
    - factor_research.py:
      - calc_momentum: mom_1m/mom_3m/mom_6m/ma200_dev を prices_daily を用いて計算（ウィンドウ不足は None）。
      - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio を計算。true_range の NULL 伝播制御により ATR 計算精度を担保。
      - calc_value: raw_financials から最新財務（target_date 以前）を取得し PER/ROE を計算（EPS 0/欠損は None）。
    - モジュール設計方針として、DuckDB 接続を受け取り prices_daily/raw_financials のみを参照し、本番 API や外部ネットワークにアクセスしないことを明記。
    - research パッケージ __init__ で主要関数群と zscore_normalize（kabusys.data.stats から）を公開。

### 変更 (Changed)
- 初期リリースのため特段の変更履歴なし（このバージョンでの初期実装）。

### 修正 (Fixed)
- 初期リリースのため特段の修正履歴なし。

### パフォーマンス (Performance)
- 大量レコード保存時の効率化:
  - news_collector はチャンク挿入、INSERT ... RETURNING を用いて実際の挿入数を正確に取得。
  - jquants_client の save_* は executemany を使用してバルク保存。
  - DuckDB 側のウィンドウ関数を活用して一括計算（リサーチ関数の SQL はパフォーマンスを意識した設計）。

### セキュリティ (Security)
- RSS パーサに defusedxml を使用して XML による攻撃を軽減。
- RSS フェッチで SSRF 対策（スキーム検査、プライベートIPチェック、リダイレクト時の検査）。
- API クライアントはトークンリフレッシュを制御し、無限再帰を防ぐため allow_refresh フラグを導入。
- .env 読み込みは明示的に無効化可能（テストでの安全性向上）。

### 依存関係（明示）
- ランタイムで以下が必要 / 想定される:
  - duckdb（DuckDB 接続・SQL 実行）
  - defusedxml（RSS XML パースの安全化）
- それ以外の機能は標準ライブラリ中心で実装（pandas 等には依存しない設計）。

### 既知の制約 / 注意点 (Notes)
- research モジュールは pandas 等の外部解析ライブラリに依存せず標準ライブラリ + DuckDB を前提としているため、大量データ処理では DuckDB 側のリソースを利用する設計。
- jquants_client の _BASE_URL, レート制限等の定数はソース内定義。環境や要件に応じた設定の外出しは今後の改善候補。
- schema.py の raw_executions 定義が途中で切れている（与えられたコードスナップショットの都合）。実運用前にスキーマ定義の完全性を確認してください。
- NewsCollector の記事 ID は正規化 URL のハッシュに依存するため、URL が変わると同一記事として検出されない可能性がある。

---

開発者向け簡易メモ:
- 環境変数の自動ロードはプロジェクトルート検出に __file__ を使用するため、パッケージ配布後も動作する想定。ただしパッケージ化環境ではプロジェクトルートが見つからない場合がある点に注意。
- J-Quants のトークン周りはモジュールレベルでキャッシュされるため、テスト時は _ID_TOKEN_CACHE の操作や get_id_token の引数で制御可能。

（以上）