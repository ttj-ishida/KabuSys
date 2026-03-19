# Changelog

すべての注目すべき変更をこのファイルに記録します。フォーマットは Keep a Changelog に準拠します。

なお本リポジトリの初回リリースとして、実装済みの機能・設計方針・制約をコードベースから推測して記載しています。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-19

### Added
- パッケージ初期リリース "KabuSys"（バージョン 0.1.0）。
- パッケージ公開 API
  - kabusys.strategy.build_features: DuckDB の prices_daily / raw_financials を元に特徴量を構築し、features テーブルへ日付単位で置換（冪等）で保存する機能。
  - kabusys.strategy.generate_signals: features と ai_scores、positions 等を参照して最終スコアを算出し、BUY / SELL シグナルを signals テーブルへ日付単位で置換保存する機能。
- 研究（research）モジュール群
  - kabusys.research.factor_research: モメンタム（1/3/6 ヶ月等）、MA200 乖離、ATR（20日）、出来高関連、財務指標（PER/ROE）などのファクター計算。DuckDB の prices_daily / raw_financials のみ参照するよう設計。
  - kabusys.research.feature_exploration: 将来リターン（複数ホライズン）計算、IC（Spearman のランク相関）算出、ファクター統計サマリー、ランク関数などの分析ユーティリティ。
  - 共通ユーティリティとして zscore 正規化を利用（kabusys.data.stats 経由）。
- データ取得・保存（data）モジュール
  - kabusys.data.jquants_client:
    - J-Quants API から日足・財務・取引カレンダー等を取得するクライアント。
    - ページネーション対応、ID トークンキャッシュ、自動リフレッシュ（401 を受けた場合に 1 回まで）、リトライ（指数バックオフ、最大 3 回、408/429/5xx を対象）を実装。
    - API レート制限（120 req/min）を固定間隔スロットリングで制御（内部 RateLimiter）。
    - 取得データを raw_prices / raw_financials / market_calendar に冪等保存（ON CONFLICT DO UPDATE）する保存ユーティリティを提供。
  - kabusys.data.news_collector:
    - RSS フィードから記事を収集して raw_news へ保存するモジュール（IDempotent 保存方針、記事IDは正規化 URL のハッシュなどで重複防止の想定）。
    - テキスト前処理、トラッキングパラメータ除去、受信サイズ制限、XML パーサに defusedxml を用いた安全性配慮などを実装方針として採用。
- 環境設定管理
  - kabusys.config.Settings: 多数の環境変数をプロパティとしてラップ（必須・任意設定の取得、バリデーションを実施）。
    - 必須環境変数（プロパティ経由で ValueError を送出するもの）: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - 任意/デフォルトあり: KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）、DUCKDB_PATH（デフォルト data/kabusys.duckdb）、SQLITE_PATH（デフォルト data/monitoring.db）、KABUSYS_ENV（development/paper_trading/live）、LOG_LEVEL（DEBUG/INFO/...）。
  - .env 自動ロード機能（プロジェクトルートを .git または pyproject.toml から探して .env → .env.local の順で読み込み、OS 環境変数が保護される。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
  - .env のパースは export プレフィックス／クォート処理／インラインコメント等に対応する実装。
- 戦略ロジック・パラメータ（デフォルト）
  - feature_engineering:
    - ユニバースフィルタ: 株価 >= 300 円、20日平均売買代金 >= 5 億円。
    - 正規化対象カラムの Z スコアは ±3 でクリップ。
    - features テーブルへの書き込みはトランザクション＋置換（DELETE→INSERT）で原子性を確保。
  - signal_generator:
    - デフォルト重み: momentum 0.40、value 0.20、volatility 0.15、liquidity 0.15、news 0.10。ユーザ指定 weights は検証・正規化され合計が 1 に再スケールされる。
    - BUY 閾値のデフォルト: 0.60。
    - Stop-loss: -8%（終値 / avg_price - 1 < -0.08 で SELL）。
    - Bear レジーム判定: ai_scores の regime_score 平均が負（サンプル数 >= 3 の場合）で BUY を抑制。
    - BUY/SELL 判定結果は signals テーブルへトランザクションで置換保存。
- ロギング / 警告
  - 不足データや不整合時に logger.warning で通知する実装多数（例: PK 欠損で行をスキップ、価格欠損で SELL 判定をスキップ等）。
- 設計方針（ドキュメント化された主要点）
  - ルックアヘッドバイアス回避のため、すべて target_date 時点（および過去データのみ）を参照する実装方針を採用。
  - execution 層（発注 API）への直接依存を避け、strategy 層は signals / features の読み書きに限定。
  - research モジュールは外部ライブラリ（pandas 等）に依存せず標準ライブラリと DuckDB SQL で完結。
  - DB 操作は冪等性（ON CONFLICT）とトランザクションで原子性を担保。

### Security
- news_collector における XML 解析に defusedxml を利用する旨を明記し、XML Bomb 等への対策方針を実装に反映。
- RSS 受信サイズ上限（10 MB）やトラッキングパラメータ除去など、悪意ある入力や DoS に対する防御方針を採用。
- J-Quants クライアントは Authorization ヘッダ扱い（Bearer）とトークン自動リフレッシュを実装。リトライ対象ステータスや RateLimit（120 req/min）に従う。

### Known limitations / TODOs
- 一部エグジット条件は未実装（ドキュメントに記載）
  - トレーリングストップ（peak_price が positions に保存される必要あり）
  - 時間決済（保有 60 営業日超過）など
- news_collector の URL/SSRF 周りや記事→銘柄紐付け（news_symbols）など、完全実装はドキュメント方針のみでコード全体が未完の場合あり（現行実装の範囲はドキュメントに基づく）。
- positions テーブルに必要なメタ（peak_price, entry_date 等）が揃っていない場合、トレーリング系ロジックは未完成。
- 外部 API 呼び出しは J-Quants に依存するため、実行時に有効なトークン・ネットワーク接続が必要。

### Breaking Changes
- 初回リリースのため breaking change はありません。

---

開発者向け補足（実装上の注記）
- DuckDB のテーブル名・カラム（raw_prices / raw_financials / prices_daily / features / ai_scores / signals / positions / market_calendar / raw_news 等）を前提とした実装になっています。マイグレーションや初期スキーマはREADME または別途提供されるスキーマ定義を参照してください。
- settings により環境値が不足すると ValueError を投げます。CI/デプロイ時は .env(.local) または OS 環境変数を適切に設定してください。
- API クライアントは urllib を利用する低レベル実装で、429 の場合は Retry-After ヘッダを優先してリトライ待ち時間を決定します。

（本 CHANGELOG はソースコードのドキュメント文字列・実装から推測して作成しています。実際のリリースノート作成時は実環境での動作確認に基づく補足・修正を推奨します。）