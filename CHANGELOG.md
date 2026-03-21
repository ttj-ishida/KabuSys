# Changelog

すべての注目すべき変更点を Keep a Changelog の形式で記録します。  
このファイルは、パッケージ内のソースコード（src/kabusys/**）から推測して作成しています。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-03-21

### Added
- パッケージの初期リリース。
  - パッケージ名: kabusys（src/kabusys/__init__.py, __version__ = "0.1.0"）
  - 公開 API:
    - strategy.build_features: 特徴量作成/正規化処理を実行（src/kabusys/strategy/feature_engineering.py）
    - strategy.generate_signals: 正規化済みファクターと AI スコアを統合してシグナルを生成（src/kabusys/strategy/signal_generator.py）
    - research.*: 研究用ユーティリティ（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）（src/kabusys/research/*）
    - data.jquants_client: J-Quants API クライアント（データ取得・DuckDB への保存機能）（src/kabusys/data/jquants_client.py）
    - data.news_collector: RSS ベースのニュース収集・正規化・DB 保存（src/kabusys/data/news_collector.py）
    - config.Settings: 環境変数/設定管理（src/kabusys/config.py）

- 環境変数自動ロード機能（config）
  - プロジェクトルートを .git または pyproject.toml から探索して .env / .env.local を自動読み込み。
  - 読み込み優先度: OS 環境変数 > .env.local > .env
  - 自動ロードを無効化するためのフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - .env パーサは次の構文をサポート:
    - export KEY=val 形式
    - シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱い
    - 無効行・コメント行の無害化
  - .env.local は override=True（既存の OS 環境変数は保護）

- 設定キー検証（config.Settings）
  - 必須キー取得で未設定時に ValueError を送出（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD）
  - KABUSYS_ENV の許容値検証（development / paper_trading / live）
  - LOG_LEVEL の許容値検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - パス系設定（DUCKDB_PATH, SQLITE_PATH）は Path オブジェクトとして返すユーティリティを提供

- ファクター計算（research/factor_research.py）
  - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離率（ma200_dev）
  - calc_volatility: ATR（20 日）・相対 ATR（atr_pct）・20 日平均売買代金・出来高比率
  - calc_value: 最新の財務データ（raw_financials）と当日の株価から PER / ROE を計算
  - 各関数は DuckDB の prices_daily / raw_financials テーブルのみを参照し、(date, code) 形式の dict リストを返す

- 特徴量エンジニアリング（strategy/feature_engineering.py）
  - research の生ファクターを統合し、ユニバースフィルタ（最低株価・最低売買代金）を適用
  - 指定カラムを z-score 正規化（kabusys.data.stats.zscore_normalize を利用）、±3 でクリップ
  - features テーブルへ日付単位で置換（トランザクション + バルク挿入）し冪等性を確保

- シグナル生成（strategy/signal_generator.py）
  - features と ai_scores を組み合わせてコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算し、重み付け合算で final_score を算出
  - デフォルト重み・閾値を定義（デフォルト閾値 BUY=0.60）
  - 重みの入力検証・合計での再スケール処理（不正値はスキップ）
  - Bear レジーム判定（ai_scores の regime_score 平均が負の場合に BUY を抑制）
  - SELL 判定（ストップロス -8% / final_score が閾値未満）
  - signals テーブルへ日付単位で置換（トランザクション + バルク挿入）し冪等性を確保

- J-Quants API クライアント（data/jquants_client.py）
  - レート制限対応（_RateLimiter、120 req/min 固定間隔スロットリング）
  - 再試行（指数バックオフ、最大 3 回）と特定ステータスコードでの再試行ロジック（408/429/5xx）
  - 401 受信時はリフレッシュトークンで自動的に ID トークンをリフレッシュして 1 回再試行
  - ページネーション対応（pagination_key を用いたループ）
  - 保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）は
    - fetched_at を UTC ISO 形式で保存
    - DuckDB への INSERT は ON CONFLICT DO UPDATE を使用し冪等性を保証
    - 入力フォーマット変換ユーティリティ (_to_float/_to_int)

- ニュース収集（data/news_collector.py）
  - RSS フィードから記事を取得し raw_news に冪等保存する処理
  - セキュリティ対策:
    - defusedxml を用いた XML パース（XML Bomb 等への防御）
    - URL 正規化: トラッキングパラメータ除去（utm_*, fbclid, gclid 等）、スキーム/ホストの小文字化・フラグメント除去・クエリソート
    - 最大受信バイト数の制限（MAX_RESPONSE_BYTES = 10MB）
    - RSS から抽出した URL に対する基本検証（HTTP/HTTPS のみなどを想定）
  - DB 挿入はチャンク化（_INSERT_CHUNK_SIZE=1000）してオーバーヘッドを抑制
  - 記事 ID は正規化 URL のハッシュ（ドキュメント記載。実装に基づく冪等性確保手法）

- 研究用ユーティリティ（research/feature_exploration.py）
  - calc_forward_returns: target_date の終値から複数ホライズン（デフォルト [1,5,21]）の将来リターンを計算（LEAD を利用）
  - calc_ic: スピアマンのランク相関（IC）を計算（tie は平均ランクで扱う）
  - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算
  - rank: 同順位は平均ランクとして扱うランク変換ユーティリティ（比較前に round(..., 12) で丸めて精度問題を回避）

### Changed
- なし（初回リリースに相当するため、変更履歴は追加のみ）

### Fixed
- なし（初回リリース）

### Security
- news_collector で defusedxml を使用して XML パース脆弱性を軽減
- RSS から取得する URL を正規化・トラッキング除去し、ID 生成による冪等性・追跡を容易に
- J-Quants クライアントでのトークン自動リフレッシュ時に無限再帰を防止するフラグ（allow_refresh=False）を導入

### Notes / Known limitations
- シグナル生成側の SELL 条件としてトレーリングストップ（直近最高値からの -10%）や時間決済（60 営業日超）については未実装。これらは positions テーブルに peak_price / entry_date 型の追加が必要（該当コードのコメントに記載）。
- ニュース記事の一部実装詳細（記事 ID 生成の正確な箇所や、ニュース→銘柄の紐付けロジック）はドキュメントに記載があるが、ソースコード全体の一部のみが提示されているため、実装範囲は限定的に推測して記載。
- DuckDB に依存する設計のため、ローカルに DuckDB の環境・適切なスキーマ（raw_prices / raw_financials / prices_daily / features / ai_scores / positions / signals / market_calendar / raw_news 等）の準備が必要。
- 外部ライブラリへの依存は最小化されている（defusedxml を使用）、ただし運用時は requests 等の利用やネットワーク/認証周りの堅牢化が想定される。

---

もし CHANGELOG に追記したい重点（例: セキュリティ注意、将来のマイグレーション手順、既知のバグや TODO）や、日付表記をリリース日とは別にしたい場合は教えてください。必要に応じて英語版やより詳細な個別ファイルごとの変更ログも作成します。