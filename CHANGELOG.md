# CHANGELOG

すべての変更は Keep a Changelog の方針に従って記載しています。  
リリースバージョンは semantic versioning を想定しています。

## [Unreleased]

- （なし）

## [0.1.0] - 2026-03-20

初回リリース。日本株自動売買システム "KabuSys" のコア機能を実装しました。モジュール構成は主に以下を含みます：環境設定、データ取得/保存、ニュース収集、研究用ファクター計算、特徴量エンジニアリング、シグナル生成、および実行層のスケルトン。

### 追加 (Added)

- パッケージ基本情報
  - src/kabusys/__init__.py: パッケージ名とバージョン管理（__version__ = "0.1.0"）、公開 API エクスポート（data, strategy, execution, monitoring）。

- 環境変数・設定管理
  - src/kabusys/config.py: Settings クラスを実装。
    - .env ファイルまたは環境変数から設定を自動ロード（優先順位: OS 環境変数 > .env.local > .env）。
    - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` によって無効化可能。
    - .git または pyproject.toml を基準にプロジェクトルートを探索（パッケージ配布後も CWD に依存しない実装）。
    - .env パーサは export 形式、クォート、エスケープ、インラインコメントなどに対応。
    - 必須設定の取得 (`_require`) と、KABUSYS_ENV / LOG_LEVEL の値検証。
    - デフォルト DB パス（DuckDB/SQLite）や API の base URL の既定値を提供。
    - 必須の環境変数（参照例）:
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID

- J-Quants API クライアント
  - src/kabusys/data/jquants_client.py:
    - API 呼び出し共通処理を実装（_request）。
      - 固定間隔スロットリングによるレート制限（120 req/min）を実装する RateLimiter。
      - 再試行ロジック（指数バックオフ、最大 3 回）。リトライ対象は 408/429/5xx。
      - 401 Unauthorized 受信時に refresh token から ID トークンを自動更新して 1 回だけ再試行。
      - ページネーション対応（pagination_key を用いた逐次取得）。
      - タイムアウトや JSON デコード失敗時にわかりやすい例外を投げる。
    - 認証ヘルパー get_id_token とモジュールレベルの ID トークンキャッシュ実装（ページネーション間で共有）。
    - データ取得関数:
      - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar（各種パラメータ・ページネーション対応）。
    - DuckDB への保存関数（冪等）:
      - save_daily_quotes -> raw_prices（ON CONFLICT DO UPDATE）
      - save_financial_statements -> raw_financials（ON CONFLICT DO UPDATE）
      - save_market_calendar -> market_calendar（ON CONFLICT DO UPDATE）
    - fetched_at に UTC タイムスタンプを記録（Look-ahead バイアス対策）。
    - 型変換ユーティリティ _to_float / _to_int を実装し不正データに対処。

- ニュース収集
  - src/kabusys/data/news_collector.py:
    - RSS フィードからのニュース収集ロジック（デフォルト: Yahoo Finance ビジネス RSS）。
    - 記事 ID は正規化 URL の SHA-256（先頭 32 文字）を用いて冪等性を担保する方針を明示。
    - URL 正規化機能（スキーム/ホスト小文字化、トラッキングパラメータ除去、フラグメント除去、クエリソート）。
    - defusedxml を用いた XML の安全なパース（XML Bomb 対策）。
    - 受信サイズ上限（10MB）によるメモリ DoS 対策。
    - HTTP/HTTPS スキームの検証や SSRF に配慮した実装指針。
    - DB へのバルク INSERT をチャンク化して実行する（_INSERT_CHUNK_SIZE）。
    - raw_news / news_symbols 等への冪等保存のための方針を記載。

- 研究モジュール（Research）
  - src/kabusys/research/factor_research.py:
    - calc_momentum, calc_volatility, calc_value を実装。
      - Momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200 日 MA のデータ不足時は None）
      - Volatility: 20 日 ATR、atr_pct、avg_turnover、volume_ratio
      - Value: PER / ROE（最新財務データを raw_financials から取得）
    - DuckDB の SQL を活用して効率的に計算（外部ライブラリ非依存）。
  - src/kabusys/research/feature_exploration.py:
    - calc_forward_returns（任意ホライズンの将来リターン計算。デフォルト [1,5,21]）。
    - calc_ic（Spearman のランク相関 IC 計算。サンプル不足時は None を返す）。
    - factor_summary（count/mean/std/min/max/median を計算）。
    - rank ユーティリティ（同順位は平均ランクを付与）。
    - 実装は標準ライブラリのみを使用する方針。

- 特徴量エンジニアリング
  - src/kabusys/strategy/feature_engineering.py:
    - build_features(conn, target_date):
      - research の calc_momentum / calc_volatility / calc_value を呼び出して生ファクターを取得。
      - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 >= 5 億円）を適用。
      - 指定の数値ファクターを Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）し ±3 でクリップ。
      - features テーブルへ日付単位で置換（トランザクション + バルク挿入で原子性を確保、冪等）。
      - ルックアヘッドバイアス防止のため target_date 時点のデータのみを使用。

- シグナル生成
  - src/kabusys/strategy/signal_generator.py:
    - generate_signals(conn, target_date, threshold=0.60, weights=None):
      - features と ai_scores を統合して各銘柄のコンポーネントスコアを計算（momentum/value/volatility/liquidity/news）。
      - 各コンポーネントはシグモイド変換や反転などの正規化を行うユーティリティを提供。
      - weights の妥当性チェックと正規化（合計が 1.0 にリスケール、無効値はスキップ）。
      - Bear レジーム判定（ai_scores の regime_score の平均が負であれば BUY 抑制）。
      - BUY：final_score >= threshold の銘柄を採用（Bear 時は抑制）。
      - SELL（エグジット）判定:
        - ストップロス: 終値 / avg_price - 1 < -8%（最優先）
        - スコア低下: final_score が threshold 未満
        - 保有銘柄の価格欠損時は SELL 判定をスキップして不意なクローズを防止
      - signals テーブルへ日付単位で置換（トランザクション + バルク挿入、冪等）。
      - SELL を優先して BUY から除外し、BUY はランクを再付与（SELL 優先ポリシー）。

- モジュール公開
  - src/kabusys/strategy/__init__.py で build_features / generate_signals を公開。
  - src/kabusys/research/__init__.py で主要ユーティリティを再エクスポート。

### 変更 (Changed)

- 初回リリースのため該当なし。

### 修正 (Fixed)

- 初回リリースのため該当なし。

### 削除 (Removed)

- 初回リリースのため該当なし。

### セキュリティ (Security)

- ニュース収集:
  - defusedxml を使った XML パースにより XML-Bomb 等を緩和。
  - 受信サイズ制限（MAX_RESPONSE_BYTES = 10MB）を設定しメモリ攻撃を抑制。
  - URL 正規化時にトラッキングパラメータを除去して ID を生成（冪等性）すると同時に、不正な URL に起因するリスクを低減。
  - RSS フィードの取り込みに際して HTTP スキームの検証など SSRF を抑止する実装方針を明示。

- J-Quants クライアント:
  - レートリミット（120 req/min）を厳守する固定間隔スロットリングを実装。
  - 401 リフレッシュは最小限（1 回）のみ行い無限再帰を防止。
  - ネットワーク系エラーに対するリトライとログ出力。

### 既知の制約 / 注意点 (Notes)

- DuckDB スキーマ
  - 各モジュールは特定のテーブル（raw_prices, raw_financials, market_calendar, prices_daily, features, ai_scores, positions, signals, raw_news 等）を参照/更新する前提です。リリース時点でテーブル定義は別途用意する必要があります。
- look-ahead バイアス
  - 取得時刻（fetched_at）の保存や target_date 以前の最新価格参照など、ルックアヘッドバイアス防止に配慮していますが、運用時のデータ取得タイミングに注意してください。
- 未実装 / 将来対応
  - signal_generator のエグジット条件でトレーリングストップや時間決済（保有 60 営業日等）は未実装（positions テーブルに peak_price / entry_date が必要）。
  - 一部の統計処理は外部ライブラリ（pandas 等）を使わず標準ライブラリで実装しています。大量データの処理性能は運用状況に応じて要評価。

---

（この CHANGELOG はコードベースから推測して作成しています。README や設計資料（StrategyModel.md, DataPlatform.md 等）と合わせてご確認ください。）