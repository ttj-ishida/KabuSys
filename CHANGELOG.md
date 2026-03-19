# CHANGELOG

すべての変更は Keep a Changelog のフォーマットに準拠して記載します。  
慣例としてセマンティックバージョニングを使用しています。

リンク: https://keepachangelog.com/ja/1.0.0/

## [未リリース]

- 今後のリリースで追加予定の改善点 / 未実装の機能（備忘）
  - positions テーブルに peak_price / entry_date を追加してトレーリングストップや時間決済を実装する
  - ニュース → 銘柄の紐付けロジック強化（NER 等の導入）
  - 単体テスト・統合テストの整備（特に外部 API のモック）
  - パフォーマンス改善（DuckDB クエリの最適化、bulk 処理のチューニング）

---

## [0.1.0] - 2026-03-19

初回公開リリース。日本株自動売買システムのコア機能群を実装。

### 追加 (Added)
- パッケージ基盤
  - パッケージ名: kabusys、バージョン 0.1.0（src/kabusys/__init__.py）。
  - パッケージ公開 API: data, strategy, execution, monitoring を __all__ でエクスポート。

- 設定管理 (src/kabusys/config.py)
  - .env / .env.local の自動読み込み（プロジェクトルートは .git または pyproject.toml から検出）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロード無効化が可能。
  - export KEY=val 形式や引用符付き値、行末コメント処理等に対応した .env パーサを実装。
  - Settings クラスを提供し、主要環境変数をプロパティで取得（必須変数は _require() で検証）。
  - 主要設定:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH / SQLITE_PATH のデフォルトパス（data/*.duckdb, data/monitoring.db）
    - KABUSYS_ENV 値検証 (development|paper_trading|live)
    - LOG_LEVEL の検証

- Data 層 (src/kabusys/data/)
  - J-Quants API クライアント (jquants_client.py)
    - API 呼び出しユーティリティ、ページネーション対応、JSON デコード検証。
    - レートリミッタ実装（120 req/min 固定間隔スロットリング）。
    - 再試行 (max 3 回) と指数バックオフ、HTTP 429 の Retry-After 処理、401 時のトークン自動リフレッシュ。
    - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar（ページング対応）。
    - DuckDB への保存関数: save_daily_quotes / save_financial_statements / save_market_calendar（冪等性対応、ON CONFLICT を使用）。
    - 型安全なパースユーティリティ _to_float / _to_int。
  - ニュース収集 (news_collector.py)
    - RSS フィード取得、XML パースに defusedxml を使用してセキュリティ対策。
    - URL 正規化（トラッキングパラメータ除去、フラグメント削除、キーソート）と記事 ID の SHA-256 ベース生成方針。
    - 最大受信バイト制限、HTTP(S) スキームのみ許可、挿入のバルク化・チャンク処理。
    - デフォルト RSS ソースに Yahoo Finance を設定。
  - RateLimiter / トークンキャッシュ等、API 安定化のためのユーティリティを実装。

- Research 層 (src/kabusys/research/)
  - ファクター計算 (factor_research.py)
    - Momentum（mom_1m, mom_3m, mom_6m, ma200_dev）計算。
    - Volatility（atr_20, atr_pct, avg_turnover, volume_ratio）計算（true range の NULL 伝播制御を含む）。
    - Value（per, roe）計算（raw_financials の最新レポート参照）。
    - DuckDB を用いた SQL ベース実装で prices_daily / raw_financials のみ参照。
  - 探索ユーティリティ (feature_exploration.py)
    - calc_forward_returns（複数ホライズンの将来リターンを一クエリで取得）。
    - calc_ic（スピアマンのランク相関 IC 計算。サンプル不足時は None を返す）。
    - factor_summary（count/mean/std/min/max/median）。
    - rank（平局ランク，同順位処理を考慮）。
  - zscore_normalize 等の正規化ユーティリティを再エクスポート (research/__init__.py)。

- Strategy 層 (src/kabusys/strategy/)
  - 特徴量エンジニアリング (feature_engineering.py)
    - research 側で算出した raw factor をマージし、ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）を適用。
    - 正規化対象列を Z スコアで正規化し ±3 でクリップ。
    - features テーブルへ日付単位の置換（トランザクション + バルク挿入で冪等性/原子性を確保）。
  - シグナル生成 (signal_generator.py)
    - features と ai_scores を統合してコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - シグモイド変換、欠損コンポーネントは中立 0.5 で補完。
    - デフォルト重み（momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）、閾値 0.60。
    - Bear レジーム検知（ai_scores の regime_score 平均が負かつ十分なサンプル時に BUY を抑制）。
    - BUY/SELL シグナルの生成（SELL は stop_loss と score_drop を実装、トランザクションで signals テーブルへ置換）。
    - weights の入力検証と正規化（未知キーや負値・非数値は無視、合計が 1 でない場合はリスケール）。
    - SELL 優先ポリシー（SELL の銘柄は BUY から除外してランク再付与）。

- DB/テーブル想定（ドキュメント化されている利用テーブル）
  - prices_daily / raw_prices / raw_financials / market_calendar / features / ai_scores / signals / positions 等を前提に実装。

### 変更 (Changed)
- 初回リリースのため過去リリースからの変更なし。

### 修正 (Fixed)
- 初回リリースのため過去リリースからの修正なし。

### 警告・注意点 (Notes)
- .env の自動ロードはプロジェクトルートの検出に依存するため、配布後の利用環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を適切に設定するか、環境変数を直接設定すること。
- J-Quants API 呼び出しはネットワーク/認証を伴うため、rate limit やトークンの管理（JQUANTS_REFRESH_TOKEN）が必須。
- DuckDB スキーマ（テーブル定義）や positions テーブルの拡張（peak_price 等）は現状の実装に合わせてプロジェクト側で準備する必要あり。
- ニュース収集は RSS フィードのフォーマット差異やエンコーディング等の差に注意。defusedxml を使用しているため XML の安全性は高いが入力検証は必要。

### 既知の未実装（初期仕様書に記載のもの）
- signal_generator のトレーリングストップ、時間決済（StrategyModel.md に記載された一部要件は positions の拡張が必要）。
- ニュース→銘柄マッピング（news_symbols 等）の詳細な実装（基本的な raw_news 保存までは実装済み）。

---

作成者: kabusys 開発チーム（コードベースから推測して自動生成）