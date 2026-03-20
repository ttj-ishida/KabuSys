# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
初回リリースの内容はリポジトリのソースコードから推測して記載しています。

## [Unreleased]


## [0.1.0] - 2026-03-20
初回リリース。

### Added
- パッケージ基盤
  - kabusys パッケージを追加。トップレベルで data / strategy / execution / monitoring をエクスポート。
  - パッケージバージョン: 0.1.0

- 設定管理 (kabusys.config)
  - .env / .env.local と環境変数の自動読み込み機能を実装（読み込み順: OS 環境変数 > .env.local > .env）。
  - プロジェクトルート探索は __file__ を起点に .git または pyproject.toml を探索する実装で CWD に依存しない設計。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env パーサ実装: export プレフィックス対応、クォート内のバックスラッシュエスケープ処理、インラインコメント処理など。
  - 必須環境変数取得ヘルパ _require と Settings クラスを提供。各種設定プロパティ（J-Quants / kabu / Slack / DB パス / 環境・ログレベル判定等）を実装。
  - KABUSYS_ENV / LOG_LEVEL の値検証を行い不正値の場合は ValueError を送出。

- データ取得 / 保存 (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装。
    - 固定間隔の RateLimiter（120 req/min）によるスロットリング。
    - 冪等的な DuckDB への保存（raw_prices / raw_financials / market_calendar）を実装（ON CONFLICT DO UPDATE）。
    - ページネーション対応の fetch_* API（daily_quotes, financial_statements, market_calendar）。
    - リトライロジック（指数バックオフ、最大 3 回、HTTP 408/429/5xx を再試行対象）。429 の Retry-After ヘッダ考慮。
    - 401 発生時は ID トークンを自動リフレッシュして再試行（無限再帰を防ぐフラグ実装）。
    - モジュールレベルの ID トークンキャッシュを実装（ページネーション間で共有）。
    - データの fetched_at は UTC ISO8601 で記録し、look-ahead バイアスの追跡を容易に。
    - 型変換ユーティリティ (_to_float / _to_int) を提供し不正データを安全に扱う。
    - 保存時に主キー欠損行をスキップしてログ出力。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィード取得・記事保存の実装（DEFAULT_RSS_SOURCES に既定の RSS を含む）。
  - セキュリティ設計:
    - defusedxml を使用して XML による攻撃を緩和。
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）を設定してメモリ DoS を軽減。
    - URL 正規化でトラッキングパラメータ除去（utm_*, fbclid 等）・小文字化・フラグメント除去・クエリソートを実施。
    - 記事 ID は正規化 URL の SHA-256（先頭 32 文字等）を利用して冪等性を保証する設計方針（コード中にその旨コメントあり）。
    - HTTP/HTTPS スキーム以外の URL 拒否や SSRF を意識した実装方針がコメントで示されている。
  - bulk insert のチャンク化など DB 負荷低減の配慮あり。

- 研究 (kabusys.research)
  - ファクター計算群を提供:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日移動平均乖離）を算出。
    - calc_volatility: 20日 ATR / atr_pct / avg_turnover / volume_ratio を算出。true_range の NULL 伝播を制御。
    - calc_value: target_date 以前の最新財務データから PER / ROE を算出。
  - 特徴量探索ユーティリティ:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。
    - calc_ic: スピアマンランク相関（IC）を計算。サンプル不足時（<3）には None を返す。
    - factor_summary: count / mean / std / min / max / median を計算する統計サマリー。
    - rank: 同順位の平均ランク処理、丸め誤差対策（round(..., 12)）を含むランク関数。
  - DuckDB のみに依存し、外部ライブラリ（pandas 等）を使用しない方針。

- 戦略 (kabusys.strategy)
  - 特徴量作成 (feature_engineering.build_features)
    - research モジュールの生ファクターを取得し統合。
    - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 >= 5 億円）を適用。
    - 指定列を Z スコア正規化（zscore_normalize を利用）し ±3 でクリップ。
    - features テーブルへの日付単位の置換（BEGIN/DELETE/INSERT/COMMIT でトランザクション原子性を保証）。
    - 休場日や当日欠損に対応するため target_date 以前の最新価格を参照。
  - シグナル生成 (signal_generator.generate_signals)
    - features と ai_scores を統合して momentum / value / volatility / liquidity / news のコンポーネントスコアを計算。
    - コンポーネントはシグモイド変換や PER の逆数等で正規化。欠損コンポーネントは中立 0.5 で補完。
    - 重み指定を受け付け（デフォルトはモデル定義）。不正な重みは無視し合計を 1.0 に再スケール。
    - Bear レジーム判定（ai_scores の regime_score 平均が負である場合、かつサンプル数閾値を満たす場合に BUY を抑制）。
    - BUY は閾値（デフォルト 0.60）超で生成。SELL はストップロス（-8%）・スコア低下等のルールで生成。
    - positions / prices_daily を参照し、価格欠損時は SELL 判定をスキップまたは警告ログ出力。
    - signals テーブルへの日付単位の置換を行い冪等性を保持。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- news_collector: defusedxml 使用、受信サイズ制限、URL 正規化・トラッキング除去等の対策を導入。
- jquants_client: 429 の Retry-After 処理や 401 自動リフレッシュの実装により認証・レート関連の堅牢性を向上。

---

注記:
- 実装の多くは DuckDB を前提とした SQL 処理と Python の組み合わせで設計されています（prices_daily / raw_prices / raw_financials / features / ai_scores / positions / signals 等のテーブルを前提）。
- 一部機能（例: execution 層や一部の監視機能）はサンプルコード内で参照や設計方針のみが記載され、発注 API に直接アクセスする実装は含まれていません。
- 本 CHANGELOG はリポジトリ内のソースコメント・実装挙動から推測して作成しています。実際のリリースノート作成時はプロジェクトの意図・変更履歴管理方針に従って調整してください。