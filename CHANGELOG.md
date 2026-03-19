# Changelog

すべての変更は Keep a Changelog の仕様に従って記載しています。  
初版リリース (v0.1.0) の内容は、ソースコードから実装内容を推測してまとめています。

## [0.1.0] - 2026-03-19

### 追加 (Added)
- 基本パッケージ初期化
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - __all__ に data, strategy, execution, monitoring を公開

- 環境設定管理 (kabusys.config)
  - .env / .env.local を自動的に読み込む自動ロード機能（OS環境変数が優先）
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - .git / pyproject.toml を基準にプロジェクトルートを探索して .env をロード
  - .env パーサ実装（export 構文、クォートやエスケープ、インラインコメントの処理に対応）
  - 環境変数必須チェック用の _require と Settings クラスを提供
  - 主な設定項目（プロパティ）:
    - JQUANTS_REFRESH_TOKEN
    - KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH
    - KABUSYS_ENV (development/paper_trading/live)、LOG_LEVEL
    - is_live / is_paper / is_dev ヘルパー

- Data 層: J-Quants クライアント (kabusys.data.jquants_client)
  - API 呼び出しユーティリティを実装（_request）
  - 固定間隔のレートリミッタ実装（120 req/min）
  - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx に対応）
  - 401 レスポンス時のトークン自動リフレッシュ（1 回のみ）
  - ID トークンのモジュールレベルキャッシュ
  - データ取得関数:
    - fetch_daily_quotes (日足・ページネーション対応)
    - fetch_financial_statements (財務データ・ページネーション対応)
    - fetch_market_calendar (JPX カレンダー)
  - DuckDB 保存関数（冪等）:
    - save_daily_quotes -> raw_prices に ON CONFLICT DO UPDATE
    - save_financial_statements -> raw_financials に ON CONFLICT DO UPDATE
    - save_market_calendar -> market_calendar に ON CONFLICT DO UPDATE
  - 入出力の型変換ユーティリティ: _to_float, _to_int
  - 取得時の fetched_at を UTC ISO8601 で記録（Look-ahead バイアス対策）

- Data 層: ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィード収集の実装方針とユーティリティ
  - 既定 RSS ソースに Yahoo Finance を含む
  - 記事 ID は URL 正規化後の SHA-256（先頭 32 文字）で生成し冪等性を確保
  - URL 正規化: トラッキングパラメータ除去（utm_*, fbclid 等）、スキーム/ホスト小文字化、フラグメント除去、クエリソート
  - defusedxml を使用して XML に対する安全対策
  - HTTP 応答サイズ制限（MAX_RESPONSE_BYTES）や SSRF 対策（スキーム制限等を想定）
  - DB への一括挿入のチャンク処理とトランザクションまとめ保存

- Research 層
  - ファクター計算モジュール (kabusys.research.factor_research)
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200 日移動平均の存在チェック含む）
    - calc_volatility: atr_20 / atr_pct / avg_turnover / volume_ratio（ATR の NULL 伝播制御）
    - calc_value: per / roe（raw_financials と prices_daily を組合せ）
    - 各関数は DuckDB の prices_daily / raw_financials を参照し結果を (date, code) キーの dict リストで返す
  - 特徴量探索モジュール (kabusys.research.feature_exploration)
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算（LEAD を使用、スキャン範囲にバッファ）
    - calc_ic: スピアマンのランク相関（Information Coefficient）実装（有効レコード 3 件未満は None）
    - rank: 同順位は平均ランクとするランク関数（丸めで ties 検出の安定化）
    - factor_summary: count/mean/std/min/max/median を算出する統計サマリ
  - 研究用実装方針: pandas 等に依存せず標準ライブラリ + duckdb で完結

- Strategy 層
  - 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
    - build_features(conn, target_date): research モジュールの raw factor を統合、ユニバースフィルタ適用、Zスコア正規化（指定カラム）、±3 でクリップ、features テーブルへ日付単位の置換（トランザクション）
    - ユニバースフィルタ条件: 株価 >= 300 円、20 日平均売買代金 >= 5 億円
    - 正規化対象カラム: mom_1m, mom_3m, atr_pct, volume_ratio, ma200_dev
  - シグナル生成 (kabusys.strategy.signal_generator)
    - generate_signals(conn, target_date, threshold=0.6, weights=None)
      - features と ai_scores を統合して component スコアを算出
      - momentum/value/volatility/liquidity/news を重み付けして final_score を算出（デフォルト重みを提供）
      - AI の regime_score を集計して Bear レジームを判定（サンプル閾値あり）
      - Bear レジーム時は BUY シグナルを抑制
      - BUY: final_score >= threshold、SELL: ストップロス（-8%）やスコア低下
      - positions テーブルを参照してエグジット判定を行う（SELL と BUY は日付ごとに置換して保存）
      - weights の検証・スケーリングロジック、欠損コンポーネントは中立値 0.5 で補完
    - 内部ユーティリティ: _sigmoid, _avg_scores, 各種コンポーネント計算、_is_bear_regime、_generate_sell_signals
    - 未実装だが設計に言及している機能:
      - トレーリングストップ、時間決済（positions テーブルに peak_price / entry_date が必要）

### 変更 (Changed)
- 初期リリースのため該当なし（全て新規追加として実装を含む）。

### 修正 (Fixed)
- 初期リリースのため該当なし。

### 削除 (Removed)
- 初期リリースのため該当なし。

### セキュリティ (Security)
- news_collector は defusedxml を使用して XML 関連の攻撃を緩和
- RSS 処理で受信上限（MAX_RESPONSE_BYTES）を設定しメモリ DoS を軽減
- jquants_client はトークン管理と自動リフレッシュを実装（認証失敗時の安全な再試行）
- .env 読み込みでは OS 環境変数を保護する protected 機構を導入（.env.local による上書きルールあり）

### 既知の制限・注意点 (Known issues / Notes)
- positions テーブルに peak_price / entry_date 等の追加情報がないと、トレーリングストップや時間決済は未実装（コード内コメント参照）。
- jquants_client のリトライ対象ステータスやバックオフは保守時に調整が必要な可能性あり（429 の Retry-After を優先）。
- news_collector の具体的な RSS 取得／パースの完全実装（ネットワーク例外処理、SSRF 対応の完全網羅）は使用環境に応じて追加テスト推奨。
- DuckDB のスキーマ（テーブル名・カラム）に依存するため、使用前にデータベーススキーマを準備する必要あり（raw_prices, raw_financials, prices_daily, features, ai_scores, positions, signals, market_calendar など）。

---

今後のリリース候補（例）
- 自動テストや CI による回帰検証、ニュースパーシングの堅牢化、execution 層の実装（kabu ステーション連携）、Webhooks/Slack 通知の追加などを予定。変更履歴は次回リリースで詳細を追記します。