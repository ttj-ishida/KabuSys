# Changelog

すべての重要な変更点をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

準備済みバージョン
- 0.1.0 - 2026-03-19

## [0.1.0] - 2026-03-19

### Added
- パッケージ初期リリース: KabuSys - 日本株自動売買システムの基礎機能を追加。
  - src/kabusys/__init__.py にパッケージメタ情報（__version__=0.1.0, 公開サブパッケージ一覧）を追加。

- 環境設定管理（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを追加。
  - 自動 .env ロード機能:
    - プロジェクトルートを .git または pyproject.toml を基準に探索して自動的に .env / .env.local を読み込む。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能。
    - .env の読み込みは OS 環境変数を保護する保護セット（protected）に配慮。
  - .env パーサは export プレフィックス、クォート文字列、エスケープ、インラインコメント処理などに対応。
  - 必須の環境変数チェック（_require）といくつかのプロパティを提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等を取得
    - DUCKDB_PATH / SQLITE_PATH のデフォルトパス設定
    - KABUSYS_ENV（development / paper_trading / live）の検証
    - LOG_LEVEL 値検証、is_live/is_paper/is_dev のユーティリティ

- データ取得・保存（src/kabusys/data/）
  - J-Quants API クライアント（src/kabusys/data/jquants_client.py）を追加。
    - 固定間隔スロットリングによるレート制限（120 req/min）の実装（_RateLimiter）。
    - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を再試行対象）。
    - 401 受信時にリフレッシュトークンから自動で id_token を再取得して 1 回リトライする仕組み。
    - ページネーション対応の fetch_* 関数:
      - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
    - DuckDB へ冪等に保存する save_* 関数:
      - save_daily_quotes (raw_prices)
      - save_financial_statements (raw_financials)
      - save_market_calendar (market_calendar)
    - データ整形ユーティリティ: _to_float / _to_int
    - 取得時の fetched_at を UTC ISO8601 で記録して look-ahead bias をトレース可能に。
    - INSERT は ON CONFLICT DO UPDATE を用い冪等性を確保。
  - ニュース収集モジュール（src/kabusys/data/news_collector.py）を追加。
    - RSS から記事を収集して raw_news へ冪等保存する設計。
    - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント削除）。
    - 記事ID は正規化 URL の SHA-256（先頭32文字）を利用して冪等性を保証。
    - defusedxml を利用して XML Bomb 等への対策、SSRF 対策（HTTP/HTTPS スキームのみ許可）、受信サイズ制限（10MB）等のセキュリティ対策を実装。
    - バルク INSERT のチャンク化や INSERT RETURNING を想定した実装方針。

- リサーチ・ファクター計算（src/kabusys/research/）
  - factor_research モジュール（src/kabusys/research/factor_research.py）を追加。
    - Momentum（mom_1m, mom_3m, mom_6m, ma200_dev）計算（window 内のデータ不足を考慮）。
    - Volatility（atr_20, atr_pct, avg_turnover, volume_ratio）計算（true range を正確に扱う）。
    - Value（per, roe）計算（raw_financials の最新報告を結合）。
    - DuckDB を用いた SQL + Python による実装。prices_daily / raw_financials のみ参照。
  - feature_exploration（src/kabusys/research/feature_exploration.py）を追加。
    - 将来リターン計算 calc_forward_returns（複数ホライズン対応、入力バリデーション）。
    - IC（Information Coefficient）計算 calc_ic（Spearman の ρ を rank を介して算出、最小サンプル数チェック）。
    - factor_summary（count/mean/std/min/max/median の集計）。
    - rank ユーティリティ（同順位は平均ランク、round で ties の安定化）。
  - パッケージ向け再エクスポートを実装（src/kabusys/research/__init__.py）。

- 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
  - build_features(conn, target_date) を追加。
    - research モジュールから生ファクターを取得（calc_momentum / calc_volatility / calc_value）。
    - 株価・流動性を用いたユニバースフィルタ（最低株価 300 円、20日平均売買代金 >= 5 億円）。
    - zscore_normalize を利用した Z スコア正規化（対象カラム指定）と ±3 でのクリップ。
    - DuckDB のトランザクションで日付単位の置換（DELETE → BULK INSERT）により冪等性と原子性を保証。

- シグナル生成（src/kabusys/strategy/signal_generator.py）
  - generate_signals(conn, target_date, threshold=0.6, weights=None) を追加。
    - features と ai_scores を統合してコンポーネントスコア（momentum/value/volatility/liquidity/news）を算出。
    - シグモイド変換、None を中立値 0.5 で補完するポリシー。
    - デフォルト重みのマージと正規化、入力 weights のバリデーション（未知キー/非数値/負値は無視）。
    - Bear レジーム判定（ai_scores の regime_score 平均 < 0 かつサンプル数閾値）による BUY 抑制。
    - BUY シグナルは閾値（デフォルト 0.60）超の銘柄、SELL シグナルはストップロス（-8%）およびスコア低下を判定。
    - positions / prices_daily を参照したエグジット判定、SELL 優先で BUY から除外。
    - signals テーブルへの日付単位置換（トランザクション + バルク挿入）で冪等性を保証。

- パッケージエクスポート（src/kabusys/strategy/__init__.py）: build_features, generate_signals を公開。

### Changed
- 初版の設計・実装においては外部依存（pandas 等）を避け、標準ライブラリ／DuckDB ベースで実装。
- SQL はパフォーマンスや欠損処理（NULL 伝播など）に配慮した記述を採用。

### Fixed
- （初版）なし（リリース時点では既知のバグ修正履歴なし）。

### Known (Not implemented / TODO)
- signal_generator の SELL 条件にはコメントで以下の未実装条件が記載されています:
  - トレーリングストップ（peak_price が必要）
  - 時間決済（保有 60 営業日超過）
  これらは positions テーブルに追加情報（peak_price / entry_date）がある場合に実装予定。
- news_collector 側の INSERT RETURNING を前提とした記述があるが、実際のテーブル定義や実行時の挙動により微調整が必要。

### Security
- news_collector: defusedxml を用いた XML パース、安全な URL 正規化、受信サイズ制限、SSRF 対策を実装。
- jquants_client: タイムアウトやリトライ、429 の Retry-After の考慮により外部 API への堅牢性を向上。

---

今後のバージョンでは以下を予定しています（抜粋）:
- positions テーブルに関するメタデータ強化（peak_price, entry_date）とそれに基づく追加のエグジットロジック実装
- News → symbol マッチングロジックの強化と NLP ベースのスコアリング連携
- テストカバレッジと CI の整備、型チェック（mypy 等）およびドキュメントの追加

（必要であれば各変更点についてさらに細かいコミット単位の説明や関連ファイル/関数の参照を追記します）