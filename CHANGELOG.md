# Changelog

すべての注目すべき変更は Keep a Changelog の方針に従って記載しています。  
このプロジェクトのバージョンはパッケージ定義に基づき 0.1.0 です。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-21

### Added
- パッケージの初期実装を追加。
  - パッケージ名: kabusys（__version__ = 0.1.0）
  - モジュール構成: data, strategy, execution, monitoring（execution は空のパッケージとして準備）
- 環境設定・ロード機能（kabusys.config）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動読み込み（OS 環境変数優先）。
  - 自動読み込みは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env のパースは以下に対応:
    - 空行、コメント行（# 先頭）を無視
    - export KEY=val 形式のサポート
    - シングル/ダブルクォート内でのバックスラッシュエスケープ対応
    - クォートなし行でのインラインコメント扱い（直前が空白/タブの # をコメントと判定）
  - 読み込み時に OS 環境変数を保護する protected 上書き制御（.env.local は override=True だが OS 環境変数は保護）
  - Settings クラスを提供し、必須環境変数取得ヘルパ（_require）やプロパティを通して設定値にアクセス可能:
    - JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID を必須として取得
    - KABU_API_BASE_URL / DUCKDB_PATH / SQLITE_PATH のデフォルト値を定義
    - KABUSYS_ENV（development/paper_trading/live）の検証、LOG_LEVEL の検証
    - is_live / is_paper / is_dev のブールプロパティを提供
- データ収集クライアント（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装:
    - 固定間隔のレート制限（120 req/min）を _RateLimiter で実装
    - 再試行ロジック（指数バックオフ、最大 3 回）。リトライ対象に 408, 429, 5xx を含む
    - 401 受信時はトークン自動リフレッシュを 1 回行って再試行（無限再帰防止）
    - ページネーション対応で pagination_key を使って全件取得
    - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar を提供
  - DuckDB への冪等保存関数を実装:
    - save_daily_quotes：raw_prices へ INSERT ... ON CONFLICT DO UPDATE
    - save_financial_statements：raw_financials へ INSERT ... ON CONFLICT DO UPDATE
    - save_market_calendar：market_calendar へ INSERT ... ON CONFLICT DO UPDATE
    - 取得日時（fetched_at）は UTC ISO8601 で記録し、Look-ahead バイアスのトレースを可能に
  - データ変換ユーティリティ:
    - _to_float / _to_int により安全にパースし、無効値は None を返す
- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィードから記事を収集して raw_news に冪等保存するための基盤
  - セキュリティ・安定性対策:
    - defusedxml を用いた XML パース（XML Bomb 等に対する保護）
    - HTTP/HTTPS 以外のスキーム拒否（SSRF の軽減方針）
    - 最大受信バイト数制限（MAX_RESPONSE_BYTES = 10 MB）によるメモリ DoS 緩和
    - 記事 ID を URL 正規化後の SHA-256（先頭32文字）で生成して冪等性を担保（ドキュメント記載）
    - トラッキングパラメータ（utm_*, fbclid 等）の除去、クエリのキーソート、フラグメント除去による URL 正規化機能
  - バルク挿入のチャンクサイズや DB トランザクションの集中化による性能向上
  - デフォルト RSS ソースに Yahoo Finance（日本語ビジネスカテゴリ）を追加
- リサーチモジュール（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）:
    - calc_momentum：1M/3M/6M リターン、MA200 乖離率を計算（ウィンドウ不足時は None）
    - calc_volatility：20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算
    - calc_value：最新の raw_financials と当日株価から PER/ROE を計算
    - DuckDB のウィンドウ関数や適切な NULL 伝播を考慮した実装
  - 特徴量探索（kabusys.research.feature_exploration）:
    - calc_forward_returns：翌日/翌週/翌月など任意ホライズンの将来リターンを計算（複数ホライズンを一度に取得）
    - calc_ic：Spearman（ランク相関）で IC を計算（有効サンプルが3未満の場合は None）
    - rank：同順位は平均ランクとするランク関数（丸めによる ties 対応）
    - factor_summary：count/mean/std/min/max/median を計算する統計サマリー関数
  - zscore_normalize をデータユーティリティとして公開（kabusys.research.__init__ から再エクスポート）
- 戦略モジュール（kabusys.strategy）
  - 特徴量生成（kabusys.strategy.feature_engineering）
    - research モジュールで計算した生ファクターをマージし、ユニバースフィルタ（最低株価、20日平均売買代金）を適用
    - 指定カラムを Z スコア正規化し ±3 でクリップ（外れ値抑制）
    - features テーブルへ日付単位の置換（トランザクション + バルク挿入で冪等性／原子性保証）
    - target_date 時点のみ使用してルックアヘッドバイアスを防止
  - シグナル生成（kabusys.strategy.signal_generator）
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum / value / volatility / liquidity / news）を計算
    - sigmoid、重み付き合算により final_score を算出。デフォルト重みを用意し、ユーザー重みは検証・正規化してマージ
    - Bear レジーム検出（AI の regime_score の平均が負、サンプル数閾値あり）時は BUY シグナルを抑制
    - BUY シグナル閾値（デフォルト 0.60）
    - SELL（エグジット）ルールを実装（ストップロス -8%、スコア低下）および SELL 優先ポリシー（SELL 対象は BUY から除外）
    - signals テーブルへ日付単位の置換（トランザクション + バルク挿入）
    - 欠損コンポーネントは中立（0.5）で補完して不当な降格を防止
    - 重みの不正値（負・NaN/Inf・非数値）は警告してスキップ
- ロギングとエラーハンドリング
  - 各処理で情報・警告・デバッグログを追加して運用時の可観測性を向上
  - DB 操作時のトランザクション管理（BEGIN/COMMIT/ROLLBACK）を実装し、ROLLBACK 失敗時は警告を出力

### Changed
- （初期リリースのため変更履歴なし）

### Fixed
- （初期リリースのため修正履歴なし）

### Security
- XML パースに defusedxml を使用して XML ベースの攻撃を軽減（news_collector）
- RSS の URL 正規化・トラッキングパラメータ除去、受信サイズ制限、スキーム検証により SSRF/DoS のリスク低減

### Notes / Limitations
- 一部の高度なエグジット条件（トレーリングストップ、時間決済）は positions テーブルに peak_price / entry_date 等の追加情報が未実装のため未実装として記載
- news_collector の実装はモジュール内で設計方針とユーティリティを備えており、実際のパーサー/保存ループは続きの実装が想定される（ファイルは途中で切れている部分があります）
- レート制限は固定間隔スロットリング（スループットを均等化）で実装しているため、バースト性能を必要とするユースケースでは別の実装が必要

---

配布・運用に際して:
- .env.example を元に必要な環境変数を配置してください（Settings._require が未設定時に ValueError を投げます）。
- DuckDB スキーマ（raw_prices, raw_financials, market_calendar, prices_daily, features, ai_scores, positions, signals 等）は本コードの期待に合わせて事前に作成してください。