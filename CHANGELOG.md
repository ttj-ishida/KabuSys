# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。  
このプロジェクトの初期公開バージョンとして v0.1.0 をリリースします。

## [0.1.0] - 2026-03-19

### 追加 (Added)
- パッケージ初期構成を追加
  - パッケージ名: kabusys、バージョン 0.1.0
  - 公開モジュール: data, strategy, execution, monitoring（__init__ で __all__ 指定）
- 環境設定管理モジュールを追加（kabusys.config）
  - .env/.env.local ファイルおよび OS 環境変数から設定を自動読み込みする機能（プロジェクトルートは .git または pyproject.toml により探索）。
  - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により無効化可能。
  - .env パースロジックの実装（コメント行、export プレフィックス、クォート文字列とエスケープ対応、インラインコメント処理など）。
  - Settings クラスによりアプリケーション設定をプロパティとして取得可能：
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - データベースパス: DUCKDB_PATH, SQLITE_PATH（Path 型で展開）
    - 環境種別（KABUSYS_ENV: development/paper_trading/live）のバリデーション
    - LOG_LEVEL のバリデーション（DEBUG/INFO/WARNING/ERROR/CRITICAL）と利便性プロパティ（is_live/is_paper/is_dev）
- Data 層（kabusys.data）を追加
  - J-Quants API クライアント（kabusys.data.jquants_client）
    - 固定間隔の RateLimiter（120 req/min）を実装
    - リトライ（指数バックオフ、最大 3 回）と 429 に対する Retry-After 処理
    - 401 受信時の自動トークンリフレッシュ処理（1 回のみ）とモジュールレベルの ID トークンキャッシュ
    - ページネーション対応の取得関数:
      - fetch_daily_quotes（株価日足）
      - fetch_financial_statements（財務データ）
      - fetch_market_calendar（JPX カレンダー）
    - DuckDB への冪等保存関数:
      - save_daily_quotes, save_financial_statements, save_market_calendar（ON CONFLICT / DO UPDATE を利用）
    - 型安全なユーティリティ変換関数 (_to_float / _to_int)
  - ニュース収集モジュール（kabusys.data.news_collector）
    - RSS からニュースを収集し raw_news に保存する処理（記事IDは正規化 URL の SHA-256 ハッシュを利用）
    - トラッキングパラメータ除去、URL 正規化、受信バイト数上限（10MB）、XML 攻撃対策（defusedxml）等の安全対策
    - バルク INSERT のチャンク化とトランザクション最適化
- Research 層（kabusys.research）を追加
  - ファクター計算モジュール（kabusys.research.factor_research）
    - モメンタム（1M/3M/6M, MA200 乖離）、ボラティリティ（20 日 ATR, 相対 ATR, 出来高比率）、バリュー（PER, ROE）等の計算を実装
    - DuckDB 上の SQL ウィンドウ関数を活用した実装（営業日欠損を考慮したスキャン範囲バッファあり）
  - 特徴量探索モジュール（kabusys.research.feature_exploration）
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）
    - IC（Spearman の rank correlation）計算
    - ファクター統計サマリ（count/mean/std/min/max/median）と rank ユーティリティ
  - zscore_normalize を共通公開（kabusys.research.__init__ でデータ層のユーティリティを再公開）
- Strategy 層（kabusys.strategy）を追加
  - 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
    - research 層の生ファクターをマージしてユニバースフィルタ（株価 >= 300 円、20 日平均売買代金 >= 5 億円）を適用
    - 指定列の Z スコア正規化、±3 でクリップ
    - features テーブルへの日付単位 UPSERT（トランザクションで削除→挿入の冪等処理）
  - シグナル生成器（kabusys.strategy.signal_generator）
    - features と ai_scores を統合して各コンポーネントスコア（momentum/value/volatility/liquidity/news）を算出
    - 最終スコア（final_score）を重み付き合算（デフォルトウェイトを持ち、ユーザ入力で正規化／フォールバック）
    - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル閾値を満たす場合）
    - BUY（閾値デフォルト 0.60）および SELL（ストップロス -8%、score_drop）シグナルの生成
    - signals テーブルへの日付単位置換（トランザクションとバルク挿入で原子性を担保）
- 実行層のスケルトン: src/kabusys/execution/__init__.py を配置（将来の拡張を想定）

### 修正 (Fixed)
- データ取得・保存での冪等性と欠損データ扱いを明確化
  - raw_* テーブルへの保存は PK 欠損行をスキップし、スキップ数をログ出力
  - prices/financials の保存は ON CONFLICT で既存行を更新することで重複挿入を防止
- Signal/Feature の生成処理でトランザクション失敗時に ROLLBACK を試み、失敗があれば警告を出すロギングを追加
- env ファイルパーサの堅牢化（export プレフィックス、クォート内のエスケープ、インラインコメントルール等）

### セキュリティ (Security)
- ニュース収集で defusedxml を使用し XML 実行攻撃（XML Bomb 等）を防止
- news_collector で URL 正規化とスキーム確認を行う設計（SSRF リスク低減に配慮）
- HTTP クライアントでタイムアウトを設定（urlopen timeout）し、リトライ時の挙動を明記

### その他 (Notes)
- 多くのモジュールは DuckDB 接続を受け取り、prices_daily / raw_prices / raw_financials / features / ai_scores / positions / signals / market_calendar 等のテーブルを参照・更新することを前提としています。データスキーマは別途 DataPlatform / StrategyModel のドキュメントを参照してください（コード内コメントに設計参照箇所を記載）。
- generate_signals の weights 引数は不正値に対して警告を出し無効キーを無視、合計が 1.0 でなければ再スケールする堅牢化を行っています。
- conserve look-ahead bias: research/strategy 層は target_date 時点までのデータのみを参照する設計になっています。

## 既知の未実装項目 / TODO
- strategy のエグジット条件の一部（トレーリングストップや時間決済）は positions に peak_price / entry_date 等のカラムが必要であり現時点では未実装（コード内にコメントで明記）。
- news_collector の RSS フィード一覧はデフォルトで Yahoo を設定。拡張やソース管理は今後の課題。
- execution 層（実際の発注ロジック）および monitoring 層の実装はスケルトンのみ。実運用での API 呼び出しや注文管理は別実装が必要。

---

このリリースはコードベースの初期公開版として、データ取り込み、因子計算、特徴量構築、シグナル生成の主要機能を提供します。今後は execution（注文発行）、モニタリング、バックテストといった運用周りの実装・拡充を予定しています。