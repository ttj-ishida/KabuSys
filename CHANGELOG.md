# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトはセマンティックバージョニングに従います。

## [Unreleased]
（現時点の変更はありません）

## [0.1.0] - 2026-03-20
初回公開リリース。

### 追加 (Added)
- パッケージ全体
  - KabuSys: 日本株自動売買システムの基本モジュール群を提供。
  - パッケージバージョン: 0.1.0。

- 環境設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を自動読み込みする機能を追加。
    - 自動読み込み順序: OS 環境変数 > .env.local > .env。
    - プロジェクトルートは .git または pyproject.toml を基準に __file__ から探索（CWD に依存しない）。
    - 自動読み込みを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env のパース実装:
    - export KEY=val 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの扱いなど。
  - Settings クラスを提供（settings インスタンスを利用可能）。主なプロパティ:
    - jquants_refresh_token (JQUANTS_REFRESH_TOKEN 必須)
    - kabu_api_password (KABU_API_PASSWORD 必須)
    - kabu_api_base_url（デフォルト: http://localhost:18080/kabusapi）
    - slack_bot_token / slack_channel_id（SLACK_BOT_TOKEN / SLACK_CHANNEL_ID 必須）
    - duckdb_path（デフォルト: data/kabusys.duckdb）
    - sqlite_path（デフォルト: data/monitoring.db）
    - env（有効値: development, paper_trading, live）
    - log_level（有効値: DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - is_live / is_paper / is_dev 判定プロパティ
  - 必須環境変数未設定時は ValueError を発生させる明示的なチェック。

- データ取得・保存 (kabusys.data.jquants_client)
  - J-Quants API クライアントを追加。
    - レート制限: 120 req/min に基づく固定間隔スロットリング実装（RateLimiter）。
    - 自動リトライ: 指数バックオフ（最大 3 回）、対象ステータス 408/429 および 5xx、429 の場合は Retry-After を尊重。
    - 401 受信時はトークンを自動リフレッシュして 1 回リトライ（無限再帰を防止）。
    - ID トークンのモジュールレベルキャッシュを実装（ページネーション間で共有）。
    - JSON デコードエラーやネットワークエラーのハンドリング。
  - API ラッパー関数:
    - get_id_token(refresh_token: Optional[str]) -> str
    - fetch_daily_quotes(...)（ページネーション対応）
    - fetch_financial_statements(...)（ページネーション対応）
    - fetch_market_calendar(...)
  - DuckDB への保存関数（冪等・ON CONFLICT を利用）:
    - save_daily_quotes(conn, records) -> 挿入・更新件数
    - save_financial_statements(conn, records) -> 挿入・更新件数
    - save_market_calendar(conn, records) -> 挿入・更新件数
  - データ変換ユーティリティ:
    - _to_float / _to_int（安全な変換、空値・不正値で None を返す）
  - Look-ahead バイアス対策:
    - fetched_at を UTC ISO8601 で記録。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードから記事を収集して raw_news に保存する機能を追加。
  - セキュリティ・堅牢性対策:
    - defusedxml を使用して XML 攻撃を防止。
    - 最大受信サイズ制限（デフォルト 10MB）でメモリ DoS を軽減。
    - URL 正規化：トラッキングパラメータ（utm_*, fbclid, gclid 等）を除去、スキーム/ホスト小文字化、フラグメント除去、クエリソート。
    - 記事ID は正規化 URL の SHA-256（先頭 32 文字）を使用して冪等性を確保。
    - HTTP/HTTPS スキーム以外を拒否し SSRF を抑止。
  - バルク INSERT のチャンク化やトランザクションを利用してパフォーマンスと一貫性を確保。
  - デフォルト RSS ソースとして Yahoo Finance のカテゴリ RSS を設定。

- リサーチ用ユーティリティ (kabusys.research)
  - 研究環境向けのファクター計算・探索ユーティリティを提供。
  - エクスポートされた関数:
    - calc_momentum, calc_volatility, calc_value（factor_research）
    - zscore_normalize（kabusys.data.stats から再エクスポート）
    - calc_forward_returns, calc_ic, factor_summary, rank（feature_exploration）
  - 実装方針: DuckDB の prices_daily / raw_financials テーブルのみ参照し、本番 API や発注システムに接続しない。

- ファクター計算 (kabusys.research.factor_research)
  - calc_momentum(conn, target_date):
    - mom_1m / mom_3m / mom_6m（営業日ベースのラグ）、ma200_dev（200 日移動平均乖離）
    - データ不足時は None を返す設計
  - calc_volatility(conn, target_date):
    - atr_20（20 日 ATR の平均）、atr_pct（相対 ATR）、avg_turnover（20 日平均売買代金）、volume_ratio（当日/20 日平均）
    - true_range の NULL 伝播を制御してカウントを適切に扱う
  - calc_value(conn, target_date):
    - raw_financials から target_date 以前の最新財務データを取得して per / roe を計算
    - EPS が 0 または欠損のとき per は None

- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - build_features(conn, target_date) を実装:
    - research の calc_momentum / calc_volatility / calc_value を呼び出してファクターを取得
    - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 >= 5 億円）を適用
    - 指定カラムの Z スコア正規化（_NORM_COLS）および ±3 でクリップ
    - features テーブルへ date 単位で置換（DELETE + INSERT をトランザクションで行い冪等性を担保）
    - ルックアヘッドバイアス防止のため target_date 時点の価格を利用

- シグナル生成 (kabusys.strategy.signal_generator)
  - generate_signals(conn, target_date, threshold=0.60, weights=None) を実装:
    - features / ai_scores / positions を参照し、各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算
    - コンポーネントの変換:
      - Z スコアをシグモイドで [0,1] に変換（欠損は None として扱い、最終的に中立 0.5 で補完）
      - value は PER を 20 を基準に変換 (1/(1+per/20))
      - volatility は atr_pct の逆符号にシグモイド適用
    - デフォルト重み: momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10。ユーザ指定 weights は検証・正規化され合計が 1 に再スケールされる。
    - Bear レジーム判定: ai_scores の regime_score 平均が負かつサンプル数 >= 3 の場合、BUY シグナルを抑制
    - BUY シグナル: final_score >= threshold（Bear では抑制）
    - SELL シグナル（エグジット判定）:
      - ストップロス: 終値/avg_price - 1 < -8%（最優先）
      - final_score が threshold 未満
      - 保有銘柄で価格欠損時は SELL 判定をスキップ、features 未存在の場合は final_score=0 とみなす（SELL 対象）
    - signals テーブルへ date 単位で置換（DELETE + INSERT をトランザクションで行い冪等性を担保）
    - SELL を優先し、BUY から SELL 対象を除外してランクを再付与
  - ログ出力: 生成結果（BUY/SELL 件数）や各種警告・情報ログを出力

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### セキュリティ (Security)
- news_collector で defusedxml を利用し XML による攻撃を軽減。
- news_collector で受信サイズ制限やスキーム検査を導入し SSRF/DoS を抑止。

### 既知の制約・未実装 (Known limitations / TODO)
- signal_generator のエグジット条件:
  - トレーリングストップ（peak_price に基づく -10%）や時間決済（保有 60 営業日超過）は未実装（positions テーブルに peak_price / entry_date が必要）。
- research / strategy 層は DuckDB 上のテーブル構造（prices_daily, raw_financials, features, ai_scores, positions, signals など）に依存する。DB スキーマは別途定義が必要。
- ai_scores テーブルの生成・AI モデルとの連携は本リリースでは含まれていない（外部で生成する前提）。
- data.stats.zscore_normalize は参照されるが本 CHANGELOG の範囲では実装詳細を省略。

### マイグレーション / 注意事項 (Migration notes)
- 必須の環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - 未設定時は settings のプロパティ参照で例外が発生します。
- .env 自動読み込みによりローカル開発で .env / .env.local を使った設定が可能。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB / SQLite のデフォルトパスはそれぞれ data/kabusys.duckdb / data/monitoring.db。必要に応じて環境変数 DUCKDB_PATH / SQLITE_PATH で変更してください。

---

（今後のリリースでは、ai スコア生成との統合、execution 層による発注ロジック、追加のエグジット条件やリスク管理ルール、テストカバレッジ向上などを予定しています。）