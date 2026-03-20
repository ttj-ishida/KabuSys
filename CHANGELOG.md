# CHANGELOG

すべての注目すべき変更点を記録します。  
このファイルは Keep a Changelog の形式に準拠しています。  

※ 日付はこのリリース作成時点（2026-03-20）を使用しています。

## [0.1.0] - 2026-03-20

### 追加 (Added)
- パッケージ基盤を追加
  - kabusys パッケージの初期公開。モジュール公開インターフェースとして data / strategy / execution / monitoring を __all__ でエクスポート。

- 環境設定管理 (`src/kabusys/config.py`)
  - .env ファイル自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を起点に探索）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env のパース実装:
    - コメント行、`export KEY=val` 形式、クォート内のエスケープ、インラインコメントの扱いなどに対応。
    - override / protected を考慮した読み込みロジックを提供。
  - Settings クラスを提供（プロパティ経由で設定値取得）:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等の必須チェック（未設定時は ValueError）。
    - KABU_API_BASE_URL のデフォルト、DUCKDB / SQLITE の既定パス、KABUSYS_ENV の許容値検証（development / paper_trading / live）、LOG_LEVEL 検証。
    - is_live / is_paper / is_dev ヘルパーを提供。

- J-Quants API クライアント (`src/kabusys/data/jquants_client.py`)
  - API 呼び出しの共通ユーティリティを実装:
    - 固定間隔スロットリングによるレート制限 (120 req/min)。
    - リトライ（指数バックオフ、最大 3 回）。408/429/5xx をリトライ対象。429 の Retry-After を尊重。
    - 401 受信時のトークン自動リフレッシュ（1 回のみ）とモジュールレベルの ID トークンキャッシュ。
    - JSON デコード失敗時の明示的エラー。
  - データ取得関数:
    - fetch_daily_quotes（ページネーション対応、日足 OHLCV 取得）
    - fetch_financial_statements（四半期財務データ取得）
    - fetch_market_calendar（JPX カレンダー取得）
  - DuckDB への保存関数（冪等性）:
    - save_daily_quotes / save_financial_statements / save_market_calendar — ON CONFLICT による upsert を利用。
    - fetched_at を UTC で記録。
  - 型安全なパースユーティリティ `_to_float`, `_to_int` を実装。

- ニュース収集モジュール (`src/kabusys/data/news_collector.py`)
  - RSS フィードからの記事収集処理を実装（デフォルトソースに Yahoo Finance を設定）。
  - セキュリティ・健全性対策:
    - defusedxml を利用した XML パース（XML Bomb 対策）。
    - 受信最大バイト数制限（10 MB）によりメモリ DoS を緩和。
    - URL 正規化とトラッキングパラメータ除去（utm_*, fbclid 等）。フラグメント除去・クエリソート化。
    - 記事 ID は URL 正規化後の SHA-256 ハッシュ（先頭 32 文字）で生成し、冪等性を確保。
    - DB への一括挿入はチャンク化して処理（パフォーマンスと SQL 長制限対策）。
  - raw_news / news_symbols などへの保存を想定した処理フローを実装。

- 研究用モジュール（research）
  - ファクター計算 (`src/kabusys/research/factor_research.py`)
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev を DuckDB SQL で計算（ウィンドウ関数利用）。
    - calc_volatility: 20日 ATR（atr_20, atr_pct）、20日平均売買代金、volume_ratio を計算（true_range の NULL 伝播を制御）。
    - calc_value: raw_financials から最新財務を参照して PER / ROE を算出（EPS が 0 や欠損の場合は None）。
    - 各関数は target_date ベース、欠損データに対する安全な扱い、ログ出力あり。
  - 特徴量探索 (`src/kabusys/research/feature_exploration.py`)
    - calc_forward_returns: 指定したホライズン（デフォルト [1,5,21]）について将来リターンを計算。horizons のバリデーション実装。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を実装。ペア数が 3 未満なら None を返す。
    - factor_summary: count / mean / std / min / max / median を計算する統計サマリー機能。
    - rank: 同順位は平均ランクとするランク変換ユーティリティ（丸めによる ties 対策あり）。
  - research パッケージの __init__ で便利な関数を再エクスポート。

- 戦略モジュール（strategy）
  - 特徴量エンジニアリング (`src/kabusys/strategy/feature_engineering.py`)
    - build_features: research モジュールの生ファクターを取得し、ユニバースフィルタ（最低株価 300 円・20日平均売買代金 5 億円）を適用。
    - 数値ファクターを z-score 正規化（kabusys.data.stats の zscore_normalize を使用）し ±3 でクリップ。
    - features テーブルへ日付単位で置換（トランザクション + バルク挿入で原子性）し、冪等性を実現。
    - ルックアヘッドバイアス防止のため target_date 時点のデータのみ使用。
  - シグナル生成 (`src/kabusys/strategy/signal_generator.py`)
    - generate_signals: features と ai_scores を統合して component score（momentum/value/volatility/liquidity/news）を計算。
    - スコアはシグモイド変換・欠損補完（中立 0.5）を適用し、重み付き合算で final_score を算出（デフォルト重みを実装）。
    - Bear レジーム判定: ai_scores の regime_score 平均が負なら BUY シグナルを抑制（サンプル数下限あり）。
    - BUY シグナル閾値デフォルト 0.60、SELL シグナルはストップロス（-8%）とスコア低下で判定。
    - positions / prices_daily を参照して保有ポジションのエグジット判定を行い、signals テーブルへ日付単位で置換（冪等）。
    - weights の入力検証（未知キーや負値・NaN を無視）と合計 1.0 への再スケール機能を実装。

### 変更 (Changed)
- （初版リリースのため見送り）主要機能は上記として新規実装。

### 修正 (Fixed)
- （初版リリース）堅牢性向上:
  - DuckDB への挿入で PK 欠損レコードをスキップしログ警告を出すようにした（save_* 系）。
  - HTTP レスポンスの JSON デコードエラーを明示的に捕捉して理解しやすい例外を投げるようにした。
  - リトライロジック・トークンリフレッシュで無限再帰にならないガードを追加。

### 注意事項 (Notes)
- 環境変数が未設定の場合、Settings の必須プロパティ呼び出しで ValueError が発生します（特に JQUANTS_REFRESH_TOKEN / SLACK_BOT_TOKEN / SLACK_CHANNEL_ID / KABU_API_PASSWORD）。
- デフォルトのデータベースパス:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
- KABUSYS_ENV は "development" / "paper_trading" / "live" のいずれかを設定してください。LOG_LEVEL は標準の "DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL" を期待します。
- 自動 .env ロードはパッケージ検出ロジック（.git または pyproject.toml が存在する親ディレクトリ）に依存するため、配布環境では無効化するか適切に配置してください。
- J-Quants API のレート制限（120 req/min）・リトライ方針・token refresh の動作はこの実装に依存します。外部 API の挙動変更時は互換性に注意してください。
- 戦略・研究モジュールは DuckDB 上のテーブル（prices_daily / raw_prices / raw_financials / features / ai_scores / positions / signals など）を前提とします。スキーマの準備が必要です。

### 今後の予定（取り組み案）
- news_collector の SSRF/IP 検査やネットワーク制約の実装をより明確に（現行実装は URL 正規化等の一部を含む）。
- signals -> execution 層の接続（発注ロジック・注文管理）の実装。
- 単体テスト・統合テストの充実（特に外部 API モック、DuckDB 初期化スクリプト）。
- パフォーマンス改善（大規模データ処理時の並列化・バッチ処理最適化）。

---

この CHANGELOG はコードベースの実装内容から推測して作成しています。実運用向けのリリースノートにする場合は実際の変更履歴（コミットや PR）に基づいた補正を行ってください。