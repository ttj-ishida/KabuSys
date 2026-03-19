# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトはセマンティック バージョニングを採用します。

最新リリース
=============

Unreleased
----------

- （現在なし）

[0.1.0] - 2026-03-19
-------------------

Added
- 初回リリース。日本株自動売買プラットフォームのコアモジュールを追加。
  - パッケージ名: kabusys、バージョン 0.1.0。
- 環境設定管理（kabusys.config）
  - .env/.env.local 自動読み込み機能（プロジェクトルートの判定は .git または pyproject.toml）。
  - .env パーサの強化:
    - export プレフィックス対応
    - シングル/ダブルクォート内のエスケープ処理対応
    - インラインコメントの扱い（クォートなしでは直前が空白/タブの場合にコメントとみなす）
  - 自動読み込みを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数サポート。
  - Settings クラスを提供し、以下の必須設定をプロパティ経由で取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - デフォルト値 / 検証:
    - KABUSYS_ENV（development / paper_trading / live のみ有効）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - デフォルト DB パス: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"
- Data 層（kabusys.data）
  - J-Quants API クライアント（data.jquants_client）
    - レート制限（120 req/min）を固定間隔スロットリングで実装
    - リトライ（指数バックオフ、最大3回）、408/429/5xx をリトライ対象
    - 401 時はリフレッシュトークンで自動トークン更新して再試行（1 回のみ）
    - ページネーション対応の fetch_* 関数（daily_quotes / financial_statements / market_calendar）
    - DuckDB への冪等保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）
      - ON CONFLICT DO UPDATE により重複を排除
      - fetched_at を UTC ISO フォーマットで記録（look-ahead bias 対策）
      - 型変換ユーティリティ (_to_float / _to_int)
  - ニュース収集モジュール（data.news_collector）
    - RSS フィード収集機能（デフォルトソースに Yahoo Finance を含む）
    - URL 正規化（utm_* 等トラッキングパラメータ削除、クエリソート、フラグメント除去）
    - defusedxml による XML パース（XML Bomb 等の防御）
    - 受信サイズ上限（10MB）や HTTP スキーム検証などセキュリティ考慮
    - 挿入はバルクかつチャンク処理、挿入済判定はハッシュ ID（冪等性）
- Research 層（kabusys.research）
  - ファクター計算（research.factor_research）
    - モメンタム (1/3/6M)、MA200乖離、ATR20、相対ATR、20日平均売買代金、出来高比率、PER/ROE 等を計算
    - DuckDB SQL を用いた効率的なウィンドウ計算。データ不足時は None を返す設計
  - 特徴量探索ユーティリティ（research.feature_exploration）
    - 将来リターン計算（calc_forward_returns、複数ホライズン対応、入力検証）
    - IC（スピアマンのランク相関）計算（calc_ic）
    - ファクター統計サマリー（factor_summary）とランク計算ユーティリティ（rank）
  - research パッケージ API エクスポートを整理（calc_momentum 等を __all__ に追加）
- Strategy 層（kabusys.strategy）
  - 特徴量エンジニアリング（strategy.feature_engineering）
    - research で算出した raw ファクターをマージ、ユニバースフィルタ（価格・平均売買代金）適用
    - 指定カラムを Z スコア正規化（zscore_normalize を使用）、±3 でクリップ
    - features テーブルへ日付単位の置換（トランザクション＋バルク挿入で冪等）
    - デフォルトのユニバース基準値: 最低株価 300 円、最低 20 日平均売買代金 5 億円
  - シグナル生成（strategy.signal_generator）
    - features と ai_scores を統合して最終スコア（final_score）を計算
    - コンポーネントスコア: momentum / value / volatility / liquidity / news
      - momentum: sigmoid を用いた正規化後の平均
      - value: PER を基に 1/(1 + per/20) のスケーリング
      - volatility: atr_pct の Z スコアを反転して sigmoid
      - liquidity: volume_ratio を sigmoid
    - デフォルト重み・閾値: momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10、BUY 閾値 0.60
    - weights 引数の検証と再スケーリング（未知キー・非数値・負値は無視）
    - Bear レジーム判定（ai_scores の regime_score の平均が負の場合）で BUY シグナルを抑制
    - SELL シグナル（エグジット判定）実装:
      - ストップロス: (close / avg_price - 1) < -8% は即時 SELL
      - スコア低下: final_score < threshold
      - 一部の条件（トレーリングストップ、時間決済）は未実装（positions テーブルに追加データが必要）
    - signals テーブルへ日付単位で置換して保存（冪等）
- パッケージ API エクスポートを整備（strategy.build_features / generate_signals を __all__ に追加）

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- news_collector は defusedxml を使用して XML 攻撃を軽減
- ニュース収集では受信サイズ上限や URL スキーム検査を導入して DoS / SSRF リスクを低減

Notes / Migration / Known expectations
- 必須環境変数が未設定の場合、Settings のプロパティ参照で ValueError が発生します:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - CI/デプロイ環境では .env（.env.local）または環境変数で設定してください。
- DuckDB / DB スキーマ（期待されるテーブル）
  - raw_prices / raw_financials / market_calendar / prices_daily / features / ai_scores / positions / signals 等のスキーマが前提となっています。初期化スクリプトでこれらのテーブルを準備する必要があります。
- J-Quants API クライアント:
  - レート制限とリトライ挙動により、短時間で大量のリクエストを投げる用途ではスループットが制限されます。
  - 401 の自動リフレッシュは1回のみ実施します。リフレッシュに失敗すると例外になります。
- signal_generator の SELL 判定では価格欠損時に SELL 判定をスキップし、features に存在しない保有銘柄は final_score=0 として扱います（警告ログ出力）。
- research.calc_forward_returns の horizons は 1 ≤ h ≤ 252 の整数を想定。無効な値は ValueError。

今後の予定（例）
- positions テーブルに peak_price / entry_date 等を追加してトレーリングストップ・時間決済を実装
- news_collector のシンボル紐付け（news_symbols）ロジック強化
- zscore_normalize 実装の最適化（並列化や DuckDB 内集計への移行検討）

--- 

参照:
- パッケージバージョン: src/kabusys/__init__.py にて __version__ = "0.1.0"