Keep a Changelog に準拠した形式で、本リポジトリの最初のリリース向け CHANGELOG をコード内容から推測して作成しました。

全ての注目すべき変更はここに記載します。詳細はソース内の docstring / コメントも参照してください。

v0.1.0 - 2026-03-19
===================

Added
-----
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージエントリポイントを定義 (src/kabusys/__init__.py)。公開モジュール: data, strategy, execution, monitoring。
- 環境設定管理 (src/kabusys/config.py)
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から探索）。
  - export KEY=val 形式や引用符付き値、インラインコメントのパースに対応する堅牢な .env パーサを実装。
  - 読み込み順序: OS 環境 > .env.local > .env。OS 環境変数は保護（protected）され、.env.local で上書きする際に保護可能。
  - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - 必須環境変数取得ユーティリティ _require を提供。
  - Settings クラスを提供し、以下のプロパティを公開:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（デフォルト data/monitoring.db）
    - KABUSYS_ENV の妥当性検証（development / paper_trading / live）
    - LOG_LEVEL の妥当性検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - is_live/is_paper/is_dev の利便性プロパティ
- Data 層: J-Quants クライアント (src/kabusys/data/jquants_client.py)
  - API 呼び出しの共通処理を実装（_request）。
  - レート制限: 固定間隔スロットリングによる 120 req/min の制御 (_RateLimiter)。
  - 再試行ロジック: 指数バックオフ（最大 3 回）、ステータス 408/429/5xx でリトライを試行。
  - 401 発生時は自動トークンリフレッシュ（1 回のみ）を行い再試行する仕組みを実装。
  - ページネーション対応で fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar を提供。
  - DuckDB へ保存するための保存関数を実装（save_daily_quotes / save_financial_statements / save_market_calendar）。
    - ON CONFLICT DO UPDATE により冪等保存を実現。
  - データ型変換ユーティリティ _to_float / _to_int を実装。厳密な変換ルールを用いて意図しない切り捨てを防止。
  - API トークンキャッシュをモジュールレベルで保持しページネーションに共有。
  - 取得時刻（fetched_at）を UTC ISO8601 で記録し、look-ahead bias の追跡を可能に。
- News 層: ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードから記事を収集し raw_news に保存する仕組み。
  - URL 正規化 (utm_* 等トラッキングパラメータ除去、ソート、フラグメント削除、小文字化) を実装。
  - 記事 ID を正規化 URL の SHA-256（先頭 32 文字）で生成して冪等性を担保。
  - defusedxml を用いて XML ベースの攻撃（XML Bomb 等）を防御。
  - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10 MB）や SSRF 対策（HTTP/HTTPS チェック）などの安全策を導入。
  - バルク INSERT のチャンク化やトランザクションまとめによりパフォーマンスを最適化。
  - デフォルト RSS ソースとして Yahoo ビジネスカテゴリを登録。
- Strategy 層
  - 特徴量エンジニアリング (src/kabusys/strategy/feature_engineering.py)
    - research で計算した生ファクターを取り込み、ユニバースフィルタ、Z スコア正規化（zscore_normalize を利用）、±3 でのクリップを行い features テーブルへ冪等 (日付単位で DELETE→INSERT) に保存する build_features を実装。
    - ユニバースフィルタの基準: 株価 >= 300 円、20 日平均売買代金 >= 5 億円。
    - 正規化対象カラムは mom_1m, mom_3m, atr_pct, volume_ratio, ma200_dev。
    - DuckDB を用いたトランザクション処理で原子性を保証。
  - シグナル生成 (src/kabusys/strategy/signal_generator.py)
    - features と ai_scores を統合し、各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算して final_score を算出する generate_signals を実装。
    - デフォルト重み: momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10。合計を 1 に正規化するロジックあり。ユーザー指定 weights の妥当性検証（非数値・負値などを除外）。
    - BUY 閾値のデフォルトは 0.60。Bear regime（ai_scores の regime_score 平均が負でかつサンプル数 >= 3）の場合は BUY シグナルを抑制。
    - エグジット判定: ストップロス（終値/avg_price - 1 < -8%）とスコア低下（final_score < threshold）を実装。SELL 判定は positions と prices_daily を参照。
    - SELL は BUY に優先し、signals テーブルへの日付単位置換（DELETE→INSERT）で冪等性を実現。
    - None（欠損）コンポーネントは中立値 0.5 で補完する振る舞いにより欠損銘柄の過度な不利扱いを回避。
- Research 層
  - ファクター計算 (src/kabusys/research/factor_research.py)
    - mom (1m/3m/6m, ma200_dev)、volatility (ATR20, atr_pct, avg_turnover, volume_ratio)、value (per, roe) を計算する calc_momentum / calc_volatility / calc_value を実装。prices_daily / raw_financials のみ参照。
    - 各種ウィンドウやスキャン範囲でカレンダー日バッファを採用し、週末祝日を吸収する設計。
  - 特徴量探索 (src/kabusys/research/feature_exploration.py)
    - 将来リターン計算 calc_forward_returns（ホライズン指定: デフォルト [1,5,21]）を実装。
    - スピアマンの IC（calc_ic）を実装（ランク変換、同順位は平均ランク）。
    - factor_summary により count/mean/std/min/max/median を計算する統計要約を実装。
    - rank ユーティリティを提供（小数丸めで ties を適切扱い）。
  - research パッケージ __all__ に主要関数をエクスポート。
- DuckDB を利用した SQL 実行パターンやトランザクション処理の標準化（features / signals / raw_* 等の日付単位置換、ON CONFLICT 処理）。

Changed
-------
- （初回リリースのため差分はなし。将来の変更点はここに記載します）

Fixed
-----
- （初回リリースのため差分はなし。将来の修正はここに記載します）

Security
--------
- news_collector で defusedxml を使用して XML による攻撃を軽減。
- RSS/URL 正規化・トラッキングパラメータ除去・レスポンスサイズ制限・スキームチェックなどで SSRF / DoS 対策を導入。
- J-Quants API クライアントでタイムアウトやリトライに配慮し、過剰トラフィックによる失敗モードを緩和。

Known issues / TODO
------------------
- signal_generator._generate_sell_signals 内でトレーリングストップ（直近最高値から -10%）や時間決済（保有 60 営業日超過）は未実装。これらは positions テーブルに peak_price / entry_date 等の追加が必要。
- execution パッケージ (src/kabusys/execution) は初期状態では未実装（プレースホルダ）。実際の発注ロジック・kabu API 統合は今後の実装予定。
- news_collector の記事 ID は SHA-256 の先頭 32 文字を利用する設計だが、運用上の衝突確率・仕様変更の影響検討が必要。
- DB スキーマ（tables: raw_prices, raw_financials, prices_daily, features, ai_scores, positions, signals, market_calendar, raw_news 等）は本 CHANGELOG に含めていません。各保存関数は期待するスキーマに依存するため、導入時にスキーマの準備が必要です。
- 一部の機能（例: zscore_normalize の実装）は別モジュール（kabusys.data.stats）に依存しており、当該モジュールの互換性に注意が必要。

Environment / Migration notes
-----------------------------
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- 開発環境設定:
  - KABUSYS_ENV は development / paper_trading / live のいずれか
  - LOG_LEVEL は DEBUG/INFO/WARNING/ERROR/CRITICAL のいずれか
  - 自動 .env 読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
- デフォルト DB パス:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db

Notes
-----
- 多くの箇所で「ルックアヘッドバイアスを防ぐ」設計方針が明示されており、target_date 時点で利用可能なデータのみを参照する実装になっています。
- 各種保存処理は冪等性を重視（ON CONFLICT や日付単位の DELETE→INSERT）しており、定期実行ジョブでの再実行に耐える設計です。

今後のリリースでは、execution 層の実装、トレーリングストップ等のエグジット条件の追加、より詳しいドキュメント（DB スキーマ、運用手順、例: cron / Airflow ジョブ設定）を追加する予定です。