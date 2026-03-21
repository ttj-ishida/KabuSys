# CHANGELOG

すべての変更は Keep a Changelog のフォーマットに準拠します。  
このプロジェクトはセマンティックバージョニングを採用しています。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-21

初回リリース。日本株自動売買システム「KabuSys」のコア機能群を追加しました。

### Added
- パッケージ基盤
  - パッケージ名 kabusys を追加。バージョンを 0.1.0 に設定（src/kabusys/__init__.py）。
  - サブパッケージのエクスポートを定義（data, strategy, execution, monitoring）。

- 設定・環境変数管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定値を読み込む Settings クラスを追加。
  - 自動ロードの探索はパッケージファイル位置からプロジェクトルート（.git または pyproject.toml）を特定して行うため CWD に依存しない設計。
  - .env/.env.local の読み込み優先順位を実装（OS 環境変数 > .env.local > .env）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート（テスト用途）。
  - .env 行パーサを実装:
    - export プレフィックス、シングル／ダブルクォート、バックスラッシュエスケープ、インラインコメント処理をサポート。
    - 無効行（空行／コメント／等号なし行）はスキップ。
  - 必須環境変数取得用の _require と、各種プロパティ（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, Slack, DB パスなど）を提供。
  - KABUSYS_ENV（development/paper_trading/live）・LOG_LEVEL の値検証と is_live/is_paper/is_dev の補助プロパティを追加。

- Data レイヤー（src/kabusys/data/）
  - J-Quants クライアント（src/kabusys/data/jquants_client.py）
    - API ベース通信処理を実装。ページネーション対応で日足・財務・カレンダー等の取得関数を提供（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
    - レート制限（120 req/min）を固定間隔スロットリングで制御する RateLimiter を実装。
    - 再試行ロジック（指数バックオフ、最大 3 回）を実装。HTTP 408/429/5xx に対するリトライ、429 の Retry-After 優先対応。
    - 401 受信時は refresh token による id_token 再取得を自動で行い 1 回だけリトライする仕組みを実装（キャッシュ付き）。
    - JSON パースエラー・ネットワークエラーのハンドリングを実装。
    - DuckDB への保存ユーティリティを追加（save_daily_quotes, save_financial_statements, save_market_calendar）。保存は冪等性を保つため ON CONFLICT DO UPDATE を使用。
    - データ変換ユーティリティ（_to_float, _to_int）を実装し、入力値の安全な変換を担保。
    - 取得時の fetched_at を UTC ISO8601 形式で記録して Look-ahead バイアスのトレーサビリティを確保。

  - ニュース収集モジュール（src/kabusys/data/news_collector.py）
    - RSS フィードから記事を収集・前処理し raw_news へ保存するための仕組みを実装（RSS ソースのデフォルトに Yahoo Finance を設定）。
    - URL 正規化（小文字化、トラッキングパラメータ除去、フラグメント削除、クエリソート）を実装。
    - 受信最大サイズ制限（MAX_RESPONSE_BYTES = 10MB）や XML パーシングに defusedxml を使用することで DoS/XXE 攻撃対策を考慮。
    - 記事の重複排除・冪等化、バルク挿入のチャンク処理（チャンクサイズ）を導入。
    - 設計上、記事 ID は URL 正規化後のハッシュを用いる（ドキュメントに記載。実装の一部はコード内に設計方針として含む）。

- Research / ファクター計算（src/kabusys/research/）
  - factor_research モジュールを追加:
    - Momentum（mom_1m, mom_3m, mom_6m, ma200_dev）、Volatility（atr_20, atr_pct, avg_turnover, volume_ratio）、Value（per, roe）を DuckDB の prices_daily / raw_financials から計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
    - ウィンドウ欠損時の None 処理やスキャン日数のバッファを考慮した SQL 実装。
  - feature_exploration モジュールを追加:
    - 将来リターン計算（calc_forward_returns）を実装。複数ホライズン（デフォルト [1,5,21]）を一度の SQL で取得。
    - IC（Spearman の ρ）計算（calc_ic）を実装。最低サンプル数チェック、ランク付け（rank）の実装。
    - ファクター統計サマリー（factor_summary）を追加（count/mean/std/min/max/median）。
    - 外部ライブラリに依存せず、標準ライブラリ + DuckDB で完結する設計。
  - research パッケージの __all__ を整備し、zscore_normalize（data.stats 由来）や上記関数を公開。

- Strategy 層（src/kabusys/strategy/）
  - 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
    - research 側で計算した生ファクターをマージし、ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
    - 正規化（zscore_normalize を利用）、±3 でのクリップ、features テーブルへの日付単位の置換（トランザクション + 一括挿入で原子性）を実装。冪等性を担保。
    - 価格取得は target_date 以前の最新価格を参照して休場日等に対応。
  - シグナル生成（src/kabusys/strategy/signal_generator.py）
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - コンポーネントを重み付きで合算して final_score を算出（デフォルト重みを定義）。
    - Bear レジーム判定（AI の regime_score の平均が負の場合）により BUY シグナルを抑制するロジックを実装。
    - BUY シグナル閾値（デフォルト 0.60）以上の銘柄に対して BUY を生成、保有ポジションに対するエグジット判定（ストップロス -8%、スコア低下）で SELL を生成。
    - positions / prices_daily / ai_scores / features を参照し、signals テーブルへ日付単位の置換で保存（トランザクション + バルク挿入）。SELL 優先ポリシーを適用（SELL 対象を BUY から除外しランクを再付与）。
    - weights の検証・補完（無効値・未知キーは無視、合計が 1.0 になるよう再スケール）を実装。
    - 数学的ユーティリティ（シグモイド、平均計算、スコア集計）を実装。

- トランザクションとロギング
  - 各種 DB 書き込み処理（features, signals, raw_prices, raw_financials, market_calendar, raw_news 等）はトランザクションで保護し、失敗時の ROLLBACK とログ出力を行う設計。
  - 主要処理には logger による情報・警告・デバッグログを埋め込み。

### Security
- RSS XML 解析に defusedxml を使い XML 関連の脆弱性（XML Bomb など）に対策。
- news_collector では URL 正規化やトラッキング除去、受信サイズ制限、スキーム検査（設計方針）などにより SSRF / メモリ DoS の軽減を想定。
- J-Quants クライアントは HTTP レスポンスハンドリングと例外処理を丁寧に行い、不正な JSON を検出した場合に明示的エラーを出す。

### Notes / Known limitations
- 一部の機能は設計ドキュメントに基づく記載のみで、実運用向けの追加実装（例: positions テーブルの peak_price / entry_date を使ったトレーリングストップや時間決済）は未実装。信号生成ロジック内に未実装箇所として注記あり。
- NewsCollector の記事 ID 生成（URI 正規化後の SHA-256 先頭 32 文字）などは方針として明記しているが、実装の細部（例: トラッキング除去の全ケースや SSRF 判定の厳密ルール）は今後の改善候補。
- DuckDB スキーマ（テーブル列・インデックス等）はリリース内のコード内 SQL 使用ルールに依存するため、運用前にスキーマ整備が必要。

### Removed
- （なし）

### Fixed
- （初回リリースのため該当なし）

---

今後の予定:
- 実運用向けのエラー監視・メトリクス、発注実装（execution 層）、テストカバレッジ拡充、news→銘柄マッピング（news_symbols）の強化などを予定しています。