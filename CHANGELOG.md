CHANGELOG
=========
すべての変更は Keep a Changelog の形式に準拠しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

[0.1.0] - 2026-03-20
--------------------

Added
- 初回リリース: KabuSys 日本株自動売買システムの基本コンポーネントを実装。
  - パッケージメタ:
    - バージョン: 0.1.0
    - パッケージ名: kabusys
  - モジュール構成:
    - kabusys.config
      - .env ファイルおよび環境変数からの設定読み込み機能を実装。
      - 自動ロードの挙動:
        - プロジェクトルートは __file__ を起点に .git または pyproject.toml を探索して特定（CWD に依存しない）。
        - 読み込み優先順位: OS 環境変数 > .env.local > .env。
        - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
      - .env パーサ:
        - コメント行・空行スキップ
        - export KEY=val 形式対応
        - シングル/ダブルクォート内のバックスラッシュエスケープ処理
        - クォートなしの行でのインラインコメント判定（直前が空白/タブの場合のみ）
      - 環境変数必須チェック（_require）と型変換（Path 等）を提供。
      - 有効な KABUSYS_ENV 値検証 (development, paper_trading, live) と LOG_LEVEL 検証を実装。
    - kabusys.data.jquants_client
      - J-Quants API クライアントを実装。
      - レート制限:
        - 固定間隔スロットリング（120 req/min）で制御する RateLimiter を実装。
      - リトライと指数バックオフ:
        - 最大 3 回のリトライ（対象: 408, 429, 5xx 等）。429 の場合は Retry-After を優先。
      - 認証:
        - リフレッシュトークンから ID トークンを取得する get_id_token を実装。
        - 401 受信時はトークンを自動リフレッシュして 1 回だけ再試行する仕組みを実装（無限再帰防止のため allow_refresh 制御あり）。
        - モジュールレベルのトークンキャッシュを実装し、ページネーション間で共有。
      - ページネーション対応のデータ取得関数:
        - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar を実装。
      - DuckDB への保存ユーティリティ:
        - save_daily_quotes, save_financial_statements, save_market_calendar（ON CONFLICT DO UPDATE による冪等保存）。
      - データ変換ユーティリティ:
        - _to_float / _to_int: 安全な型変換ルールを実装（不適切な値は None を返す）。
      - ログ出力と取得件数報告を実装。
    - kabusys.data.news_collector
      - RSS フィードからのニュース収集と raw_news への保存処理を実装。
      - セキュリティ対策:
        - defusedxml を使用して XML Bomb 等に対処。
        - URL 正規化でトラッキングパラメータ除去（utm_*, fbclid 等）。
        - 受信サイズ上限（10 MB）を導入してメモリDoS を緩和。
        - URL 正規化・検証により SSRF リスク低減（HTTP/HTTPS 前提の処理設計）。
      - 冪等性:
        - 記事 ID を正規化 URL の SHA-256 ハッシュ先頭で生成し、ON CONFLICT DO NOTHING / バルク挿入で冪等性を確保。
      - バルク挿入最適化（チャンクサイズ）とトランザクション化による性能配慮。
    - kabusys.research
      - ファクター計算・解析機能を実装（研究用途）。
      - calc_momentum, calc_volatility, calc_value:
        - prices_daily / raw_financials を参照して各種ファクター（1M/3M/6M リターン、MA200 乖離、ATR20、avg turnover、PER/ROE 等）を計算。
        - ウィンドウサイズ・データ不足時の扱い（条件付き None）を明記。
        - パフォーマンス配慮のためスキャン範囲にバッファ（カレンダー日ベース）を採用。
      - calc_forward_returns:
        - 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一度に取得する効率的なクエリを実装。
        - horizons の入力検証（正の整数かつ <=252）。
      - calc_ic, rank, factor_summary:
        - Spearman ランク相関（IC）計算、同順位の平均ランク処理、基本統計量サマリを実装。
        - ties 対策として round(v, 12) による丸めを採用。
    - kabusys.strategy
      - feature_engineering.build_features:
        - research モジュールから生ファクターを取得し、ユニバースフィルタ（最低株価・最低平均売買代金）を適用、Z スコア正規化（kabusys.data.stats の zscore_normalize を使用）・±3 でクリップして features テーブルへ UPSERT（トランザクションで日付単位の置換）する処理を実装。
        - 価格取得は target_date 以前の最新価格を参照し、休場日や当日の欠損に対応。
        - 冪等性: target_date の既存レコードを削除してから挿入（BEGIN/COMMIT、例外時は ROLLBACK）。
      - signal_generator.generate_signals:
        - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を算出、重み付け合算で final_score を計算し BUY/SELL シグナルを生成して signals テーブルへ保存。
        - 重みの扱い:
          - ユーザ指定 weights をデフォルト重みでフォールバック・補完、合計が 1.0 でなければ再スケール。
          - 無効なキーや非数値、負値は無視して既知キーのみを受け付ける。
        - Bear レジーム判定:
          - ai_scores の regime_score の平均が負かつ十分なサンプル数 (_BEAR_MIN_SAMPLES) の場合に BUY シグナルを抑制。
        - SELL（エグジット）判定:
          - ストップロス（終値 / avg_price - 1 < -8%）優先判定。
          - final_score が閾値未満のスコア低下によるエグジット。
          - 価格欠損時の SELL 判定スキップと警告ログ。
        - 欠損コンポーネントは中立値 0.5 で補完して不当な降格を防止。
        - 冪等性: target_date の既存 signals を削除してから挿入（BEGIN/COMMIT、例外時は ROLLBACK）。
    - kabusys.execution
      - パッケージプレースホルダを追加（実装のためのエントリポイント確保）。

Changed
- n/a（初回リリースのため既存からの変更は無し）

Fixed
- n/a（初回リリース）

Security
- defusedxml の採用、RSS パース／URL 正規化、受信サイズ制限、SSRF を考慮した URL 検証など、外部データ取り込み周りの安全性に配慮。

Performance
- DuckDB を用いた集約 SQL による一括処理を採用し、研究／本番データ処理での効率性に配慮。
- バルク INSERT / チャンク化 / トランザクションにより DB 書き込みのオーバーヘッドを低減。
- API 呼び出しは固定間隔スロットリングとページネーションで安定性を確保。

Notes / Known limitations
- signal_generator の一部のエグジット条件（トレーリングストップ、時間決済など）は positions テーブルに peak_price / entry_date 等の追加フィールドが必要なため未実装。
- kabusys.data.stats の zscore_normalize の実装詳細は本差分に含まれていない（外部モジュールから利用）。
- NewsCollector の記事 ID は正規化 URL に依存するため、極端な URL 形式の変化がある場合は重複判定に影響する可能性あり。

Acknowledgements
- 初回リリース。今後のフィードバックに基づき API、戦略ロジック、テストを拡充予定。

-----