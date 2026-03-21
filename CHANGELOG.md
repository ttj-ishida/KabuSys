Keep a Changelog
=================

すべての変更は https://keepachangelog.com/ja/ に準拠して記載しています。

Unreleased
----------

（なし）

[0.1.0] - 2026-03-21
-------------------

追加 (Added)
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージルート: src/kabusys/__init__.py にバージョンと公開 API を定義。

- 設定/環境変数管理 (src/kabusys/config.py)
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を探索して判別）。
  - .env パーサ実装: コメント・export プレフィックス・クォート・エスケープ処理・インラインコメント処理などをサポート。
  - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - Settings クラスを提供し、以下の環境変数を型付きプロパティで取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）, SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（development / paper_trading / live の検証）、LOG_LEVEL（DEBUG/INFO/... の検証）
  - 必須キー未設定時は ValueError を送出する _require 実装。

- Data 層: J-Quants クライアント (src/kabusys/data/jquants_client.py)
  - API 呼び出しユーティリティを実装（JSON デコード検証、ページネーション対応）。
  - レート制限制御: 固定間隔スロットリングで 120 req/min を尊重する RateLimiter を導入。
  - リトライ/バックオフロジック: 指数バックオフ、最大 3 回、408/429/5xx をリトライ対象。429 の場合は Retry-After ヘッダを優先。
  - 401 受信時にリフレッシュトークンで自動再取得を行い 1 回だけ再試行する実装（再帰防止フラグあり）。
  - データ取得関数:
    - fetch_daily_quotes: 日足（OHLCV）をページネーション対応で取得。
    - fetch_financial_statements: 財務データをページネーション対応で取得。
    - fetch_market_calendar: JPX カレンダー取得。
  - DuckDB への保存関数（冪等化: ON CONFLICT DO UPDATE）:
    - save_daily_quotes → raw_prices
    - save_financial_statements → raw_financials
    - save_market_calendar → market_calendar
  - 型変換ユーティリティ: _to_float / _to_int（安全な変換ルールを明確化）。
  - 取得時刻（fetched_at）を UTC ISO8601 形式で保存し、look-ahead バイアスのトレースを容易に。

- Data 層: ニュース収集 (src/kabusys/data/news_collector.py)
  - RSS から記事を取得して raw_news に冪等保存するモジュールを実装。
  - URL 正規化（トラッキングパラメータ除去、フラグメント削除、キーソート）と記事 ID の SHA-256 ベース生成による冪等性。
  - セキュリティ対策:
    - defusedxml を利用して XML/BOM 攻撃を防止。
    - HTTP/HTTPS スキーム以外や SSRF を考慮したホスト検証（IP/名前解決等）を想定する設計（コード内での意図が明記）。
    - 受信サイズ上限（MAX_RESPONSE_BYTES=10MB）でメモリ DoS を軽減。
  - バルク INSERT のチャンク処理を実装し、SQL のパラメータ上限・長さを抑制。

- Research 層 (src/kabusys/research/*.py)
  - ファクター計算: factor_research モジュールで以下を実装
    - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200 日移動平均を考慮、データ不足時は None）
    - calc_volatility: ATR（20 日平均 true range）、atr_pct、avg_turnover、volume_ratio（ウィンドウ不足時は None）
    - calc_value: PER（EPS を用いた計算、EPS が 0/欠損なら None）、ROE（raw_financials を参照）
  - 特徴量探索: feature_exploration モジュールで以下を実装
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一度のクエリで取得（LEAD を利用）。
    - calc_ic: Spearman のランク相関（ランク計算は同順位を平均ランクにする実装、データ数不足時は None）。
    - factor_summary: 基本統計量（count/mean/std/min/max/median）を計算。
    - rank ユーティリティ（round(...,12) で ties 検出を安定化）。

  - research パッケージ __all__ に主要関数を公開。

- Strategy 層 (src/kabusys/strategy/*.py)
  - 特徴量エンジニアリング (feature_engineering.build_features)
    - research の生ファクターを取得し（calc_momentum/calc_volatility/calc_value）、ユニバースフィルタ（最低株価、20日平均売買代金）を適用。
    - 指定カラムを z-score 正規化（kabusys.data.stats.zscore_normalize を利用）、±3 でクリップ。
    - DuckDB の features テーブルへ日付単位で置換（DELETE + INSERT）し冪等性を確保（トランザクション内で実行）。
    - ユニバースフィルタ基準: _MIN_PRICE=300 円、_MIN_TURNOVER=5e8（5 億円）。
  - シグナル生成 (signal_generator.generate_signals)
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を算出。
    - シグモイド変換、欠損コンポーネントは中立値 0.5 で補完することで欠損による不当な降格を防止。
    - デフォルト重みは StrategyModel.md に従う（momentum 0.4, value 0.2, volatility 0.15, liquidity 0.15, news 0.10）。ユーザー指定 weights は安全に検証・正規化。
    - Bear レジーム判定（ai_scores の regime_score 平均が負かつ十分なサンプル数がある場合）で BUY シグナルを抑制。
    - BUY / SELL シグナルの生成と signals テーブルへの日付単位置換（トランザクション + バルク挿入）。
    - SELL 判定ロジックにストップロス（-8%）・スコア低下を実装（positions / prices_daily を参照）。価格欠損時は SELL 判定をスキップ。

- strategy/__init__.py で主要 API（build_features, generate_signals）を公開。

変更 (Changed)
- なし（初期リリース）

修正 (Fixed)
- なし（初期リリース）

削除 (Removed)
- なし（初期リリース）

既知の制限・未実装 (Known issues / Notes)
- signal_generator のエグジット条件に記載の以下は未実装（コメントあり）:
  - トレーリングストップ（peak_price 必須: positions テーブルに peak_price / entry_date が必要）
  - 時間決済（保有 60 営業日超過）
- news_collector のホスト検証・SSRF 防止は設計上考慮されているが、実運用で追加のネットワーク制限（プロキシ/名前解決制御）が必要になる場合がある。
- research / factor 計算は prices_daily / raw_financials に依存。これらのテーブルに十分なレコードがない場合、多くの戻り値が None となることがある（関数はその旨を明示している）。
- DuckDB マイグレーション／スキーマはリポジトリに含まれていないため、利用前に expected schema を用意する必要がある（features / raw_prices / raw_financials / ai_scores / signals / positions 等）。

セキュリティ (Security)
- news_collector: defusedxml を使用し XML 攻撃を軽減。受信サイズ上限を設定。
- jquants_client: 認証トークン管理は refresh トークンを用いるが、環境変数の管理・保護（.env の取り扱い等）は運用に依存。Settings では必須変数未設定時に明示的なエラーを返す。

アップグレード / 移行ノート (Upgrade / Migration)
- 既存プロジェクトから導入する場合、以下の環境変数を設定してください:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - 必要に応じて KABUSYS_ENV, LOG_LEVEL, DUCKDB_PATH, SQLITE_PATH
- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml）を基準に行われます。CI/テスト環境で自動読み込みを抑止するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

貢献・フィードバック
- 初期実装として主要機能を揃えていますが、運用上の観察に基づく改善（エラー処理強化、スキーマ・マイグレーション、追加の安全策、性能改善など）を歓迎します。