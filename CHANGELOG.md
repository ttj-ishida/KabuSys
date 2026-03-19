# Changelog

すべての注目すべき変更はこのファイルに記録します。  
書式は「Keep a Changelog」に準拠しています。

## [0.1.0] - 2026-03-19

初回公開リリース。日本株自動売買システムのコア機能群を実装しました。主な追加点は以下の通りです。

### 追加 (Added)
- パッケージ基盤
  - パッケージ初期化: kabusys.__init__ に version（0.1.0）と主要サブパッケージ（data, strategy, execution, monitoring）のエクスポートを追加。

- 環境変数 / 設定管理（kabusys.config）
  - .env ファイル / 環境変数の自動ロード機能を実装。
    - プロジェクトルートは .git または pyproject.toml から探索（__file__ 起点）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - 自動ロード無効化は KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
    - .env のパースは export プレフィックス対応、クォート/エスケープ、インラインコメント処理に対応。
    - .env 読み込みに失敗した場合は警告発行。
  - Settings クラスで設定値をプロパティ経由で取得可能に。
    - 必須設定（未設定時に ValueError を発生させる）:
      - JQUANTS_REFRESH_TOKEN
      - KABU_API_PASSWORD
      - SLACK_BOT_TOKEN
      - SLACK_CHANNEL_ID
    - デフォルト値:
      - KABUSYS_ENV: development（有効値: development / paper_trading / live）
      - LOG_LEVEL: INFO（有効値: DEBUG/INFO/WARNING/ERROR/CRITICAL）
      - DUCKDB_PATH: data/kabusys.duckdb
      - SQLITE_PATH: data/monitoring.db
    - 環境判定ヘルパー: is_live / is_paper / is_dev を提供。

- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
    - レート制限 (120 req/min) を守る固定間隔スロットリング（RateLimiter）。
    - 再試行（指数バックオフ、最大 3 回）。HTTP 408/429/5xx をリトライ対象。429 の場合は Retry-After を尊重。
    - 401 受信時はリフレッシュトークンで自動的に id_token を再取得して 1 回だけ再試行。
    - ページネーション対応（pagination_key）。
    - 保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）は DuckDB へ冪等に保存（ON CONFLICT DO UPDATE / DO NOTHING）。
    - データ保存時に fetched_at を UTC ISO8601 で記録。
    - 型変換ユーティリティ _to_float / _to_int を実装（不正な値は None を返す等の安全設計）。
  - データ取得関数:
    - fetch_daily_quotes（株価日足、ページネーション対応）
    - fetch_financial_statements（四半期財務、ページネーション対応）
    - fetch_market_calendar（JPX カレンダー）

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード収集モジュールを実装。
    - デフォルト RSS ソースに Yahoo Finance を追加（news.yahoo.co.jp の business カテゴリ）。
    - RSS の XML パースに defusedxml を使用し XML ボム等を防止。
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）を導入しメモリ DoS を緩和。
    - URL 正規化 (_normalize_url): スキーム/ホストの小文字化、トラッキングパラメータ除去（utm_*, fbclid 等）、フラグメント削除、クエリソート。
    - 記事 ID を正規化 URL の SHA-256（先頭切り取り）等で生成し冪等性を確保する設計（リリース注記: 実装方針として記載）。
    - HTTP レスポンスのスキーム検査や受信制限等により SSRF / 大容量レスポンス対策を想定。
    - raw_news / news_symbols への保存をトランザクションでまとめて実行（バルク挿入、チャンクサイズ制御）。

- 研究用ファクター計算（kabusys.research）
  - ファクター計算モジュールを実装（prices_daily / raw_financials を使用）。
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日MA）を計算。データ不足時は None。
    - calc_volatility: 20日 ATR（atr_20）、相対ATR（atr_pct）、20日平均売買代金(avg_turnover)、volume_ratio を計算。true_range の NULL 伝播を考慮。
    - calc_value: target_date 以前の最新財務データと価格から PER / ROE を計算。EPS=0 等は None。
  - feature_exploration:
    - calc_forward_returns: 与えたホライズン（デフォルト [1,5,21]）の将来リターンを計算（営業日ベース）。
    - calc_ic: スピアマンランク相関（Information Coefficient）を実装。サンプルが 3 未満の場合は None を返す。
    - factor_summary: 指定カラムの count/mean/std/min/max/median を計算。
    - rank: 同順位は平均ランクとするランク化ユーティリティ（丸め誤差対策あり）。
  - 研究 API は外部ライブラリに依存せず、DuckDB 接続を受け取る設計。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - build_features(conn, target_date) を実装。
    - research の calc_momentum / calc_volatility / calc_value を呼び出して生ファクターを取得。
    - ユニバースフィルタ（株価 >= 300円、20日平均売買代金 >= 5 億円）を適用。
    - 数値ファクターを z-score 正規化（kabusys.data.stats の zscore_normalize を利用）、±3 でクリッピング。
    - features テーブルへ日付単位で置換（削除→挿入）し冪等性・原子性を確保（トランザクション／バルク挿入）。
    - 保存カラム: momentum_20, momentum_60, volatility_20, volume_ratio, per, ma200_dev 等。
    - ログ出力で処理結果（銘柄数）を記録。

- シグナル生成（kabusys.strategy.signal_generator）
  - generate_signals(conn, target_date, threshold=0.60, weights=None) を実装。
    - features, ai_scores, positions テーブルを参照して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - コンポーネントはシグモイド変換や PER の逆数などで正規化。欠損値は中立値 0.5 で補完。
    - デフォルト重み（momentum:0.40, value:0.20, volatility:0.15, liquidity:0.15, news:0.10）。weights 引数は検証・正規化され合計 1.0 に再スケール。
    - Bear レジーム判定: ai_scores の regime_score の平均が負で、サンプル数が最小閾値（3）以上の場合は BUY を抑制。
    - BUY シグナル: final_score >= threshold（Bear 時は抑制）。ランク付け（score 降順）。
    - SELL シグナル（エグジット判定）:
      - ストップロス: 終値 / avg_price - 1 < -8%（最優先）
      - スコア低下: final_score < threshold
      - 未実装だが設計に記載: トレーリングストップ、時間決済（要 positions に peak_price / entry_date）
    - SELL を優先して BUY から除外、signals テーブルへ日付単位で置換（トランザクションで原子性確保）。
    - ログ出力で BUY/SELL 数を記録。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- news_collector で defusedxml を使用して XML 関連の脆弱性（XML Bomb 等）に対応。
- news_collector で受信サイズ制限や URL 正規化を導入し SSRF やメモリ DoS 対策を考慮。
- J-Quants クライアントはトークンリフレッシュと再試行により安定性を向上。

### 注意事項 / 互換性
- Settings の必須環境変数（上記参照）が未設定だと ValueError が発生します。デフォルト .env.example 等を用意して設定してください。
- DuckDB のテーブルスキーマ（prices_daily, raw_prices, raw_financials, features, ai_scores, positions, signals, market_calendar 等）に依存します。既存 DB を利用する場合はスキーマ整合性に注意してください。
- news_collector は外部 RSS にアクセスするためネットワーク接続と信頼できるフィードを使用してください。
- execution パッケージは空の初期化モジュールのみ含まれます。発注ロジックは別途実装が必要です。

もし CHANGELOG に追記してほしい点（例: 実装の追加的な設計意図や既知の制限、テーブルスキーマ例など）があれば教えてください。