# CHANGELOG

すべての重要な変更点は Keep a Changelog の形式で記載します。  
このプロジェクトの初期リリースとしてバージョン 0.1.0 を作成しました。

全般:
- バージョンポリシー: セマンティックバージョニングに準拠
- データベース: DuckDB を主要な分析格納先として利用（raw / prices / features / ai_scores 等）
- ロギング、入力検証、冪等性、トランザクション処理を重視した設計

## [0.1.0] - 2026-03-19

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージ初期実装。公開 API として `data`, `strategy`, `execution`, `monitoring` をエクスポート。
  - __version__ = "0.1.0" を設定。

- 設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を自動読み込み（OS 環境変数が優先、.env.local が .env を上書き）。
  - プロジェクトルート自動検出: .git または pyproject.toml を基準に探索（CWD に依存しない）。
  - .env パーサ実装: export プレフィックス、クォート内エスケープ、インラインコメント処理に対応。
  - 自動ロードを無効化するための環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
  - 必須環境変数取得時の検証メソッド `_require` と Settings クラスを提供。
  - 主な必須環境変数例:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - システム設定値のデフォルト（例: KABUSYS_ENV, LOG_LEVEL）と検証（有効値チェック）。

- データ取得・保存 (src/kabusys/data/jquants_client.py)
  - J-Quants API クライアント実装:
    - 固定間隔スロットリングによるレート制限（120 req/min）を実装する RateLimiter。
    - 再試行ロジック（指数バックオフ、最大試行回数、408/429/5xx のリトライ処理）。
    - 401 応答時はリフレッシュトークンを用いて id_token を自動更新して 1 回リトライ。
    - ページネーション対応（pagination_key）をサポート。
    - UTC の fetched_at を記録してデータ取得時刻を追跡（Look-ahead バイアス対策）。
  - DuckDB への保存ユーティリティ:
    - save_daily_quotes / save_financial_statements / save_market_calendar を実装（ON CONFLICT DO UPDATE により冪等性を確保）。
    - レコード整形・型変換ユーティリティ `_to_float` / `_to_int` を提供。
    - PK 欠損行のスキップ・ログ出力。

- ニュース収集 (src/kabusys/data/news_collector.py)
  - RSS フィードからのニュース収集基盤を実装。
  - URL 正規化（スキーム/ホストの小文字化、トラッキングパラメータ除去、フラグメント削除、クエリソート）。
  - セキュリティ対策:
    - defusedxml を用いた XML パース（XML Bomb 等の防止）
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）
    - トラッキングパラメータ除去 (utm_*, fbclid 等)
    - SSRF を想定した URL スキーム制限（HTTP/HTTPS のみを許可する設計方針）
  - 冪等保存（ON CONFLICT DO NOTHING 相当）と銘柄紐付けの方針、INSERT チャンクング対応。

- リサーチ（研究用）機能 (src/kabusys/research/)
  - factor_research.py:
    - calc_momentum / calc_volatility / calc_value を実装。prices_daily / raw_financials テーブルのみ参照。
    - Momentum: 1M/3M/6M リターン、200日移動平均乖離率（ma200_dev）など。
    - Volatility: 20日 ATR、相対 ATR (atr_pct)、20日平均売買代金、出来高比率。
    - Value: PER（EPS が 0 または欠損なら None）、ROE（raw_financials から取得）。
  - feature_exploration.py:
    - calc_forward_returns（任意のホライズンに対する将来リターンの一括取得）
    - calc_ic（Spearman ランク相関による IC 計算。サンプル数が少ない場合は None を返す）
    - factor_summary（count/mean/std/min/max/median を計算）
    - rank（同順位は平均ランクで処理、丸めによる ties 検出対策あり）
  - 研究モジュールは外部ライブラリに依存せず標準ライブラリ + DuckDB のみで実装。

- 特徴量エンジニアリング (src/kabusys/strategy/feature_engineering.py)
  - build_features(conn, target_date) を実装:
    - research モジュールから生ファクターを取得し、ユニバースフィルタ（最低株価/最低平均売買代金）を適用。
    - 指定カラムを Z スコア正規化（kabusys.data.stats の zscore_normalize を利用）し ±3 にクリップ。
    - features テーブルへ日付単位で置換（DELETE + バルク INSERT、トランザクションで原子性保証）。
    - 設計上、発注層への依存なし。ルックアヘッドバイアスを避ける実装方針。

- シグナル生成 (src/kabusys/strategy/signal_generator.py)
  - generate_signals(conn, target_date, threshold=0.60, weights=None) を実装:
    - features と ai_scores を統合し、momentum/value/volatility/liquidity/news のコンポーネントスコアを計算。
    - コンポーネントはシグモイド変換や逆転処理を行い、欠損値は中立値 0.5 で補完。
    - 重みの検証・補完・再スケール機能（未知キー・無効値は無視）。
    - Bear レジーム判定（AI の regime_score の平均が負かつサンプル数閾値を満たす場合）による BUY 抑制。
    - BUY シグナル（threshold 超）と SELL シグナル（ストップロス -8% / final_score の低下）を生成。
    - SELL を優先し、signals テーブルへ日付単位の置換で保存（トランザクション + バルク挿入）。
    - ログ出力と入力検証を行う。

### 変更 (Changed)
- （初期リリースのため該当なし）

### 修正 (Fixed)
- （初期リリースのため該当なし）

### セキュリティ (Security)
- news_collector にて defusedxml を使用し XML パースの安全性を確保。
- news_collector で受信サイズ上限を導入しメモリ DoS を軽減。
- jquants_client の HTTP リクエストはタイムアウト・リトライ制御を実装し、トークン更新時の無限再帰を防止。
- config の .env パーサはクォートやエスケープを正しく処理し、誤ったパースによる設定漏洩や誤動作を抑止。

### 既知の制限 / TODO
- signal_generator の SELL 判定に記載された未実装条件:
  - トレーリングストップ（peak_price が positions テーブルに必要）
  - 時間決済（保有日数ベースの自動決済：60 営業日超など）
- 一部の数値は research 側で算出されるため、十分な過去データがない銘柄は None を返す（欠損処理は上位層で中立値補完）。
- news_collector の RSS パーシングは既定のソースのみ実装（拡張時にソース追加想定）。
- 実運用時は以下環境変数を必須でセットする必要あり:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- デフォルト DB パス:
  - DUCKDB_PATH = data/kabusys.duckdb
  - SQLITE_PATH = data/monitoring.db
  （必要に応じて環境変数で上書き可能）

### マイグレーション / 注意点
- 自動 .env 読み込みはプロジェクトルート検出に依存します。パッケージ配布後に .env 自動ロードを利用する場合は .git または pyproject.toml の配置に注意してください。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB スキーマ（tables: raw_prices, raw_financials, prices_daily, features, ai_scores, positions, signals, market_calendar 等）を事前に準備してください（スキーマ定義は別途管理）。
- J-Quants API の利用にはレート制限や API トークンの管理が必要です。リフレッシュトークンを環境変数に設定してください。

---

今後のリリースでは以下を予定しています（例）:
- execution 層の実装（kabu ステーション API 経由の発注ロジック）
- monitoring モジュールの整備（Slack 通知、稼働監視）
- news_collector の記事から銘柄抽出（NLP ベースのシンボルマッチング）や AI スコア連携
- トレーリングストップ等のエグジット戦略の実装

お問い合わせや改善提案は Issue を送ってください。