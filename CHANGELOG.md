CHANGELOG
=========
(本ファイルは "Keep a Changelog" 形式に準拠しています)

フォーマット:
- すべての変更はカテゴリ別（Added / Changed / Fixed / Security / Deprecated / Removed）に記載しています。
- 日付はリリース日を表します。

Unreleased
----------
（現在ありません）

[0.1.0] - 2026-03-21
-------------------

Added
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージ構成:
    - kabusys.config: 環境変数・設定管理
    - kabusys.data: データ取得・保存機能（J-Quants クライアント・ニュース収集）
    - kabusys.research: ファクター計算・分析ユーティリティ
    - kabusys.strategy: 特徴量構築・シグナル生成
    - kabusys.execution: （パッケージ API に含めるが実装は別途）
  - モジュールエクスポート: __all__ に data, strategy, execution, monitoring を含む

- 環境設定（kabusys.config）
  - .env ファイルまたは環境変数から自動ロード（プロジェクトルートを .git または pyproject.toml で検出）
  - 読み込み順序: OS 環境変数 > .env.local > .env（.env.local は上書き）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能
  - .env の柔軟なパース機能:
    - export キーワード対応
    - 単一/二重クォート、エスケープシーケンス処理
    - インラインコメント処理（クォートあり／なしのケースに対応）
  - Settings クラスでアプリケーション設定を提供:
    - JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / SLACK_BOT_TOKEN / SLACK_CHANNEL_ID など必須設定を _require() で検証
    - DUCKDB_PATH / SQLITE_PATH のデフォルトパスを提供
    - KABUSYS_ENV の妥当値検証（development, paper_trading, live）
    - LOG_LEVEL の妥当値検証（DEBUG, INFO, WARNING, ERROR, CRITICAL）
    - is_live / is_paper / is_dev のブールプロパティ

- J-Quants API クライアント（kabusys.data.jquants_client）
  - レートリミッタ実装: 120 req/min を固定間隔スロットリングで遵守（_RateLimiter）
  - 汎用 HTTP リクエストユーティリティ _request():
    - 指数バックオフを使ったリトライ（最大 3 回）
    - 408/429/5xx 系のリトライ対応、429 の Retry-After 優先
    - 401 受信時は ID トークンを自動リフレッシュして最大 1 回リトライ
    - ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）
  - DuckDB 保存関数:
    - save_daily_quotes / save_financial_statements / save_market_calendar
    - ON CONFLICT / DO UPDATE による冪等保存
    - fetched_at に UTC タイムスタンプを付与
    - データ変換ユーティリティ _to_float / _to_int（安全変換）
    - ペイロードの PK 欠損行をスキップして警告ログ出力

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードからの記事収集パイプライン
  - URL 正規化（トラッキングパラメータ削除、クエリソート、スキーム/ホスト小文字化、フラグメント除去）_normalize_url
  - 記事 ID を URL 正規化後の SHA-256（先頭32文字）で生成して冪等性確保
  - defusedxml を用いた XML パースで XML-Bomb 等の攻撃緩和
  - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）でメモリ DoS を防止
  - SSRF 対応: HTTP/HTTPS 以外の URL や IP アドレスチェック等の制限（実装方針として明記）
  - DB 保存はチャンク化してバルク INSERT（_INSERT_CHUNK_SIZE）でパフォーマンス最適化

- 研究用ユーティリティ（kabusys.research）
  - factor_research:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200 日移動平均の乖離率）
    - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio（20 日窓）
    - calc_value: per, roe（raw_financials から最新財務を取得して計算）
    - 各関数は prices_daily / raw_financials のみ参照し、欠損時は None を返す設計
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（既定 [1,5,21]）の将来リターンを一括取得
    - calc_ic: Spearman のランク相関（IC）実装（rank 関数利用、同順位は平均ランク）
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリ
    - rank: 値リストを同順位の平均ランクで変換（丸めにより ties の誤判定を回避）

- 戦略モジュール（kabusys.strategy）
  - feature_engineering.build_features:
    - research の calc_momentum / calc_volatility / calc_value を利用して生ファクターを取得
    - ユニバースフィルタを適用（最低株価 _MIN_PRICE = 300 円、20 日平均売買代金 _MIN_TURNOVER = 5e8）
    - 数値ファクターを zscore_normalize（kabusys.data.stats）で正規化し ±3 でクリップ
    - features テーブルへ日付単位で置換（DELETE + INSERT）して冪等性／原子性を確保（トランザクション利用）
  - signal_generator.generate_signals:
    - features と ai_scores を統合してコンポーネントスコア（momentum / value / volatility / liquidity / news）を算出
    - デフォルト重みと閾値（DEFAULT_WEIGHTS, DEFAULT_THRESHOLD = 0.60）
    - ユーザー指定 weights を受け、妥当性チェック・フォールバック・再スケールを実施
    - Bear レジーム検知（_is_bear_regime: regime_score 平均が負かつサンプル数閾値）で BUY を抑制
    - BUY: final_score >= threshold（Bear 時は BUY 抑制）
    - SELL（_generate_sell_signals）:
      - ストップロス（終値/avg_price - 1 < -8%）
      - スコア低下（final_score < threshold）
      - price 欠損銘柄は SELL 判定をスキップし警告（誤クローズ防止）
    - signals テーブルへ日付単位で置換（DELETE + INSERT、トランザクション）

Changed
- 初版リリースのため過去の変更履歴はありません（新規追加のみ）。

Fixed
- 現時点での既知バグ修正は無し（初期リリース）。

Security
- news_collector で defusedxml を使用して XML パースに伴う脆弱性を緩和
- ニュースの URL 正規化でトラッキングパラメータを除去（個人情報流出・トラッキング低減）
- RSS 受信時の最大バイト数制限（MAX_RESPONSE_BYTES）でメモリ攻撃を軽減
- J-Quants クライアントは 401 発生時にトークンリフレッシュを行う際に無限再帰を避ける設計（allow_refresh フラグ）

Deprecated
- なし

Removed
- なし

Known limitations / Notes
- execution / monitoring モジュールの具体的な発注ロジックや監視機構は本リリースでは実装されていない（パッケージ公開 API に含める構成は整備済み）。
- news_collector の SSRF 保護や IP 検証は設計方針で明記されているが、環境による追加検証が必要な場合がある。
- 一部の関数は外部の zscore_normalize（kabusys.data.stats）に依存しており、その実装に応じて動作が変化する可能性がある。
- DuckDB のテーブルスキーマ（raw_prices, raw_financials, features, ai_scores, signals, positions, market_calendar など）が前提となるため、導入時にスキーマ準備が必要。

開発者向けヒント
- テスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を設定すると自動 .env 読み込みを無効化できる。
- J-Quants API のレート制限は _MIN_INTERVAL_SEC（60 / 120）で制御されるため、外部からの同時呼び出しに注意すること。
- save_* 関数は ON CONFLICT による更新を行うため、重複実行や再取得に対して冪等。

--- 
ご要望があれば、CHANGELOG の英語版、セクションの簡略化、または個別モジュールごとの詳細な変更点記載（関数一覧と変更理由など）を作成します。