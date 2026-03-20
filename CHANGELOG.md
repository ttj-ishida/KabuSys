CHANGELOG
=========

すべての注目すべき変更点を記録します。フォーマットは Keep a Changelog に準拠します。

[Unreleased]
------------

- （なし）

0.1.0 - 2026-03-20
------------------

Added
- 初回リリース: KabuSys 日本株自動売買ライブラリを追加。
- パッケージ公開情報
  - パッケージバージョン: 0.1.0
  - パッケージトップ: kabusys/__init__.py（__all__ に data, strategy, execution, monitoring をエクスポート）
- 設定・環境変数管理（kabusys.config）
  - .env / .env.local 自動ロード機能（プロジェクトルートを .git または pyproject.toml で探索）。
  - .env パースの堅牢化（export プレフィックス対応、クォート内のエスケープ、インラインコメント処理）。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラス: J-Quants / kabu API / Slack / DBパス / 環境（development/paper_trading/live）/ログレベルの取得と検証。デフォルト値（KABUSYS_ENV: development, KABUSAPI base URL 等）を提供。
  - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）。
- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装（ページネーション対応）。
  - レートリミット制御（120 req/min）を固定間隔スロットリングで実装（内部 RateLimiter）。
  - リトライロジック（指数バックオフ、最大 3 回）。再試行対象ステータスコード制御（408, 429, 5xx）と 429 時の Retry-After 利用。
  - 401 Unauthorized 時はリフレッシュトークンで id_token を自動更新して 1 回だけ再試行。
  - モジュールレベルの id_token キャッシュ（ページネーション間共有）。
  - データ保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を提供し、DuckDB へ冪等保存（ON CONFLICT DO UPDATE）を実現。
  - 型変換ユーティリティ (_to_float, _to_int) を追加し、入力の堅牢性を確保。
  - 取得日時（fetched_at）を UTC ISO8601 形式で記録し、look-ahead バイアス対策をサポート。
- ニュース収集（kabusys.data.news_collector）
  - RSS フィード収集フローを実装（デフォルトに Yahoo Finance のビジネス RSS を設定）。
  - セキュリティ対策: defusedxml を利用して XML 攻撃を防止、受信サイズ制限（MAX_RESPONSE_BYTES = 10MB）、HTTP/HTTPS スキームの強制、IP/SSRF 対策設計（実装方針として明記）。
  - URL 正規化とトラッキングパラメータ除去（utm_*, fbclid など）、記事 ID を正規化 URL の SHA-256 トップ 32 文字で生成し冪等性を担保。
  - raw_news へのバルク挿入最適化（チャンク化）とトランザクション運用の方針（INSERT RETURNING を用いる想定）。
- リサーチ（kabusys.research）
  - factor_research: prices_daily / raw_financials を用いたファクター計算を実装。
    - calc_momentum: mom_1m, mom_3m, mom_6m, ma200_dev（200日移動平均乖離）を計算。
    - calc_volatility: 20日 ATR（atr_20, atr_pct）、20日平均売買代金、volume_ratio を計算。true_range の NULL 伝播処理に注意。
    - calc_value: 最新財務データ（raw_financials）と当日株価を用いて PER/ROE を計算。EPS が 0/欠損時は None。
  - feature_exploration:
    - calc_forward_returns: 将来リターン（デフォルト horizons = [1,5,21]）を一括クエリで高速に取得。
    - calc_ic: スピアマンランク相関（Information Coefficient）計算。サンプル不足時（<3）に None を返す。
    - factor_summary: 基本統計量（count, mean, std, min, max, median）。
    - rank: 同値は平均ランクとするランク関数（round(v, 12) を用いた ties 対策）。
  - research パッケージは zscore_normalize を外部（kabusys.data.stats）から利用できるようエクスポート。
- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - build_features: research モジュールで計算した生ファクター（momentum/volatility/value）をマージし、
    - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 >= 5 億円）を適用、
    - 指定カラム群を Z スコア正規化（zscore_normalize を利用）し ±3 でクリップ、
    - features テーブルへ日付単位で置換（トランザクション＋バルク挿入で原子性）。
  - ルックアヘッドバイアス対策: target_date 時点のデータのみ使用、直近価格は target_date 以前の最新価格を参照。
- シグナル生成（kabusys.strategy.signal_generator）
  - generate_signals: features と ai_scores を統合して final_score を計算し、BUY/SELL シグナルを作成して signals テーブルへ日付単位で置換。
  - デフォルトの重み（momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）と BUY 閾値（0.60）を提供。ユーザー指定 weights は検証・正規化して合計 1 に再スケール。
  - コンポーネントスコア計算:
    - momentum: momentum_20/60 と ma200_dev を sigmoid で変換して平均。
    - value: PER を 1/(1 + per/20) でスコア化（per<=0/欠損は None）。
    - volatility: atr_pct の Z スコアを反転して sigmoid。
    - liquidity: volume_ratio を sigmoid。
    - news: ai_score を sigmoid、未登録は中立値で補完。
  - Bear レジーム検知: ai_scores の regime_score 平均が負なら Bear（サンプル数閾値あり）。
    - Bear レジームでは BUY シグナルを抑制。
  - SELL ルール（エグジット判定）実装:
    - ストップロス: 終値 / entry_avg_price - 1 < -8% → 優先 SELL。
    - final_score が threshold 未満 → SELL。
    - 注意: トレーリングストップや時間決済は未実装（positions テーブルに peak_price / entry_date が必要）。
  - signals テーブルへの書き込みは日付単位で置換（トランザクション + バルク挿入）。
- API エクスポート
  - strategy パッケージは build_features と generate_signals をトップレベルでエクスポート。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- RSS XML パースに defusedxml を採用して XML 攻撃を軽減。
- ニュース収集で受信最大バイト数制限、トラッキングパラメータ除去、スキーム検査等を設計に反映。
- J-Quants クライアントで 401 時のトークン自動リフレッシュは 1 回のみ行い、無限再帰を防止。

Notes / Migration
- 想定する DuckDB/SQLite スキーマ（テーブル）
  - raw_prices, raw_financials, market_calendar, prices_daily, features, ai_scores, positions, signals, raw_news, news_symbols 等が利用されることを想定しています。実際のテーブル定義は別途スキーマ定義を参照してください。
- 環境変数（必須）
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は必須。未設定時は Settings プロパティが ValueError を送出します。
  - デフォルトの DB パス: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"（変更可）。
  - 自動 .env ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 既知の未実装 / TODO
  - strategy の一部（トレーリングストップ、時間決済）については positions に追加データが必要なため未実装。
  - news_collector の詳細なネットワーク制約（IP/SSRF の積極的ブロック）は設計方針として記載されているが、環境に応じた追加実装が想定されます。
- ロギング / エラー処理
  - 多くの関数は警告ログを出力してフォールバック（例: 欠損データ時の中立補完やスキップ）する設計です。異常な状況はログを確認してください。

作者・連絡
- 初回リリース（0.1.0）。バグ報告や機能要望はリポジトリの issue へお願いします。