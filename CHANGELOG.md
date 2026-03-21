# Changelog

すべての変更は Keep a Changelog の形式に従っています。  
次のバージョン情報は、コードベースから推測した初回公開リリースの内容を日本語でまとめたものです。

なお、実装の設計方針や重要な動作（冪等性、レート制御、エラーハンドリングなど）も併せて記載しています。

## [0.1.0] - 2026-03-21

### 追加 (Added)
- パッケージ初期構造を追加
  - モジュール群:
    - kabusys.config: 環境変数／設定管理（.env 自動ロード、必須チェック、型/値検証）
    - kabusys.data:
      - jquants_client: J-Quants API クライアント（ページネーション、レート制御、リトライ、トークン自動リフレッシュ、DuckDB 保存ユーティリティ）
      - news_collector: RSS からニュース収集・正規化・DB 保存（ID 生成、トラッキングパラメータ除去、XML サニタイズ）
    - kabusys.research:
      - factor_research: モメンタム／ボラティリティ／バリュー等のファクター計算（DuckDB ベース）
      - feature_exploration: 将来リターン計算、IC（Spearman ρ）計算、ファクター統計サマリー、ランク付けユーティリティ
    - kabusys.strategy:
      - feature_engineering: 生ファクターの正規化・ユニバースフィルタ適用・features テーブルへの日付単位アップサート
      - signal_generator: features と ai_scores を統合して final_score を算出、BUY/SELL シグナルを生成して signals テーブルへ保存
    - kabusys.execution, kabusys.monitoring: パッケージ公開用プレースホルダを含む
  - パッケージバージョン: `kabusys.__version__ = "0.1.0"`

- 環境設定（kabusys.config.Settings）
  - .env 自動読み込み:
    - プロジェクトルートを .git または pyproject.toml で探索して .env / .env.local を自動読み込み
    - 読み込み順: OS 環境変数 > .env.local > .env（.env.local は上書き）
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動読み込みを無効化可能（テスト用途）
    - OS 環境変数は保護（protected）され、明示的な override で上書きされない
  - .env パーサ:
    - export KEY=val 形式に対応
    - シングル／ダブルクォート内のバックスラッシュエスケープ処理および内部コメント無視に対応
    - 非クォート値のインラインコメント処理（直前が空白/tab の場合のみ認識）
  - 必須設定取得 helper (`_require`) により未設定時は ValueError を送出
  - 設定プロパティ:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（必須）
    - KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
    - DUCKDB_PATH / SQLITE_PATH（デフォルトパス）
    - KABUSYS_ENV の検証（development, paper_trading, live のみ許容）
    - LOG_LEVEL の検証（DEBUG, INFO, WARNING, ERROR, CRITICAL）
    - is_live / is_paper / is_dev のユーティリティプロパティ

- J-Quants クライアント（kabusys.data.jquants_client）
  - レート制限: 固定間隔スロットリング（120 req/min）
  - リトライ: 指数バックオフ（最大 3 回）、HTTP 408/429/5xx を再試行対象
  - 401 受信時はリフレッシュトークンを用いてトークンを自動更新して1回リトライ
  - ページネーション処理をサポート（pagination_key を用いて全件取得）
  - データ保存ユーティリティ（DuckDB への冪等保存）:
    - save_daily_quotes: raw_prices テーブルに ON CONFLICT DO UPDATE（PK 欠損行はスキップ）
    - save_financial_statements: raw_financials テーブルに ON CONFLICT DO UPDATE
    - save_market_calendar: market_calendar テーブルに ON CONFLICT DO UPDATE
  - HTTP レスポンス JSON デコード失敗やネットワークエラーに対する明示的なエラーメッセージ

- ニュース収集（kabusys.data.news_collector）
  - RSS 取得から前処理、raw_news への冪等保存までの処理を実装する設計
  - URL 正規化:
    - スキーム・ホストの小文字化、トラッキングパラメータ（utm_ 等）の除去、フラグメント除去、クエリソート
  - デフォルト RSS ソースの定義（例: Yahoo Finance ビジネス RSS）
  - 受信サイズ上限（10 MB）や defusedxml を用いた XML のサニタイズ等の安全対策
  - バルク INSERT のチャンク化による DB 書き込み制御

- ファクター計算（kabusys.research.factor_research）
  - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200日データ未満は None）
  - calc_volatility: atr_20 / atr_pct、avg_turnover、volume_ratio（ウィンドウ不十分時は None）
  - calc_value: target_date 以前の最新財務データから per / roe を計算（EPS が 0/欠損時は None）
  - いずれも DuckDB の prices_daily / raw_financials のみ参照する純粋な実装

- 研究用解析ユーティリティ（kabusys.research.feature_exploration）
  - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得
  - calc_ic: スピアマンのランク相関（IC）を計算（有効行数が 3 未満なら None）
  - factor_summary: count/mean/std/min/max/median を計算（None は除外）
  - rank: 同順位は平均ランクとするランク付け（丸めにより ties 検出の安定化）

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - build_features:
    - research 側ファクター（momentum/volatility/value）を取得しマージ
    - ユニバースフィルタを適用:
      - 株価 >= 300 円
      - 20日平均売買代金 >= 5 億円
    - 正規化対象カラムを Z スコア正規化し ±3 でクリップ
    - features テーブルへ日付単位で削除→挿入（トランザクションで原子性保証）
    - 成功時は upsert した銘柄数を返す

- シグナル生成（kabusys.strategy.signal_generator）
  - generate_signals:
    - features と ai_scores を統合してコンポーネントスコア（momentum/value/volatility/liquidity/news）を算出
    - デフォルト重みと閾値（threshold=0.60）を備え、ユーザ指定 weights は妥当性検証の上で正規化
    - コンポーネント欠損値は中立 0.5 で補完して評価（欠損銘柄への不当な降格を回避）
    - Bear レジーム判定（ai_scores の regime_score 平均が負且つサンプル数 >= 3）
      - Bear の場合は BUY シグナルを抑制
    - BUY シグナル生成（score >= threshold）、SELL は保有ポジションに対して次の条件を評価:
      - ストップロス: 現在終値 / avg_price - 1 < -8%（最優先）
      - スコア低下: final_score が threshold 未満
    - SELL 対象は BUY から除外し、signals テーブルへ日付単位で置換（トランザクションで原子性保証）
    - 生成件数（BUY+SELL）を返す

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 非推奨 (Deprecated)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- news_collector で defusedxml を使用して XML を安全にパースする設計
- ニュース取得で受信バイト数上限（10 MB）を設定してメモリ DoS を軽減
- URL 正規化とスキーム制約により SSRF/Tampering リスクに配慮した実装方針
- J-Quants クライアントはトークン管理と HTTP エラー処理を実装し、不正な認証状態を自動復旧しつつ無限再帰を防止する設計

---

注意:
- 上記はソースコードの内容およびドキュメント文字列から推測してまとめた CHANGELOG です。実際のリリースノートに盛り込む場合は、リリース時の意図（API 互換性、既知の制限、追加の運用手順など）を併せて追記してください。