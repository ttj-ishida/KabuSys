# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
正式リリース前の変更履歴は semver を想定しています。

## [Unreleased]
- 今後の変更を記載します。

## [0.1.0] - 2026-03-20
最初の公開リリース。

### Added
- パッケージ全体
  - kabusys パッケージ初期版を追加。パッケージバージョンは 0.1.0。
  - パッケージエクスポート: data, strategy, execution, monitoring（execution は空パッケージ、monitoring は参照のみ）。

- 設定 / 環境読み込み（kabusys.config）
  - .env / .env.local ファイルおよび OS 環境変数から設定を読み込む自動ローダーを実装。
  - プロジェクトルートの自動検出（.git または pyproject.toml を基準）により CWD に依存しない読み込みを実現。
  - .env パーサーは export プレフィックス・クォート・エスケープ・インラインコメント等に対応。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - 環境変数取得ヘルパー _require と Settings クラスを提供。J-Quants, kabuステーション, Slack, DB パスなどの設定プロパティを公開。
  - KABUSYS_ENV と LOG_LEVEL の値検証を実装（有効値セットをチェック）。
  - サンプル: settings.jquants_refresh_token 等の直感的なプロパティアクセス。

- Data - J-Quants クライアント（kabusys.data.jquants_client）
  - J-Quants API 用クライアントを実装。
  - 固定間隔の RateLimiter（120 req/min 想定）を実装し呼び出し間隔を制御。
  - HTTP リクエストラッパーは:
    - 指数バックオフを用いたリトライ（最大 3 回、408/429/5xx 等に対応）
    - 429 の Retry-After ヘッダ優先処理
    - 401 受信時の自動トークンリフレッシュ（1 回のみ）を実装
    - JSON デコードエラーやネットワーク例外の取り扱いを実装
  - get_id_token でリフレッシュトークンから ID トークンを取得。
  - ページネーション対応の fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar を実装。
  - DuckDB への保存ユーティリティ（save_daily_quotes / save_financial_statements / save_market_calendar）を実装し、ON CONFLICT を利用した冪等保存を実現。
  - データ変換ユーティリティ _to_float / _to_int を提供（堅牢な型変換と不正値の除外）。

- Data - ニュース収集（kabusys.data.news_collector）
  - RSS フィードから記事を収集して raw_news に保存する処理の基盤を実装。
  - URL 正規化（スキーム/ホストの正規化、トラッキングパラメータ除去、クエリソート、フラグメント削除）を実装。
  - defusedxml を使った XML パース（XML Bomb 等への対策）。
  - HTTP レスポンスの最大読み取りバイト数制限 (MAX_RESPONSE_BYTES) を実装しメモリ DoS を軽減。
  - 記事 ID をトラッキングパラメータ除去後のハッシュで生成し冪等性を担保する設計（ドキュメント記載）。
  - SSRF 回避・安全な URL 処理、バルク INSERT のチャンク化など運用上の対策を盛り込んだ設計。

- Research（kabusys.research）
  - factor_research:
    - calc_momentum / calc_volatility / calc_value を実装。prices_daily / raw_financials を参照して各種ファクターを算出（mom_1m/3m/6m, ma200_dev, atr_20/atr_pct, avg_turnover, volume_ratio, per, roe など）。
    - ウィンドウ不足時は None を返すなど欠損ハンドリングを実装。
  - feature_exploration:
    - calc_forward_returns: 各銘柄の将来リターン（指定ホライズン）を計算。
    - calc_ic: スピアマンランク相関（IC）計算を実装。サンプル不足時は None を返す。
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）を計算。
    - rank: 平均ランクを考慮したランク付けユーティリティを実装（同順位は平均ランク処理、丸め誤差対策あり）。
  - 研究向けユーティリティとして zscore_normalize を再エクスポート（kabusys.data.stats に依存）。

- Strategy（kabusys.strategy）
  - feature_engineering.build_features:
    - research モジュールで計算した生ファクターを統合し、ユニバースフィルタ（最低株価・最低平均売買代金）を適用後、指定カラムを Z スコア正規化して ±3 でクリップし features テーブルへ日付単位で置換（トランザクション＋バルク挿入で原子性を確保）。
    - ユニバースフィルタ条件はデフォルトで株価 >= 300 円、20 日平均売買代金 >= 5 億円。
    - ルックアヘッドバイアスを防ぐため target_date 時点のデータのみを使用。
  - signal_generator.generate_signals:
    - features と ai_scores を統合し、各コンポーネントスコア（momentum, value, volatility, liquidity, news）を計算、重み付き和で final_score を算出。
    - デフォルト重み・閾値を持ち、ユーザ指定の weights を検証・補完・再スケール。
    - Bear レジーム検出（ai_scores の regime_score の平均が負の場合）により BUY シグナルを抑制。
    - BUY シグナルは閾値を超えた銘柄、SELL シグナルはストップロス（-8%）およびスコア低下に基づく判定を実装。
    - 保有銘柄のエグジット判定は positions テーブルと最新価格を参照。価格欠損時は SELL 判定をスキップして誤クローズを防止する。
    - signals テーブルへ日付単位で置換（トランザクション＋バルク挿入）。
    - 生成アルゴリズムは発注層に依存せず、シグナル生成のみを担当。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Security
- news_collector で defusedxml を利用し XML パース安全性を確保。
- ニュース収集で外部 URL 正規化・トラッキングパラメータ除去・スキームチェック等を行い SSRF / トラッキング情報漏洩リスクを低減。
- J-Quants クライアントでトークンリフレッシュロジックと安全な例外処理を実装。

### Notes / Implementation details
- DuckDB を主要なストレージとして利用する設計。多数の処理で SQL ウィンドウ関数とトランザクションを利用している。
- 全体を通じて「ルックアヘッドバイアス回避」「冪等性」「トランザクションによる原子性確保」「外部 API に対する堅牢なエラーハンドリング」を設計方針として採用。
- execution パッケージは存在するもののこのリリースでは発注 API への具体的な実装依存は持たない（シグナル生成と発注層を分離）。

---

編集・追加したい項目やリリース日を修正したい場合はお知らせください。