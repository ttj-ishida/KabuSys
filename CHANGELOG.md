# Changelog

すべての重要な変更点を記録します。本ドキュメントは「Keep a Changelog」形式に準拠します。

表記ルール:
- バージョンは semver を想定しています。
- 日付はリリース日を示します。

## [0.1.0] - 2026-03-19

初回リリース（ベース機能の実装）。以下の機能群と実装方針を含みます。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージの初期モジュールを追加。バージョンは 0.1.0。
  - パッケージの公開 API を定義（kabusys.data, kabusys.strategy, kabusys.execution, kabusys.monitoring を __all__ に設定）。

- 設定・環境変数管理 (kabusys.config)
  - .env ファイル（.env, .env.local）および OS 環境変数からの自動読み込み機能を実装。
  - プロジェクトルート検出ロジックを実装（.git / pyproject.toml を探索）。
  - .env パーサを実装（export 形式、クォート処理、行内コメント処理に対応）。
  - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス等の設定を取得可能。
  - 必須環境変数の検査を実装（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）。
  - 環境値のバリデーション: KABUSYS_ENV（development / paper_trading / live）、LOG_LEVEL（DEBUG/INFO/...）の検証。

- データ収集・保存 (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装。
  - レート制限（120 req/min）を守る固定間隔 RateLimiter を実装。
  - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）を実装。
  - 401 応答時にリフレッシュトークンで ID トークンを自動更新して 1 回リトライする機能を実装。
  - ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
  - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装し、ON CONFLICT による冪等性を保証。
  - 型変換ユーティリティ (_to_float, _to_int) を実装し、不正値を安全に処理。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードから記事を収集するニュース収集モジュールを実装。
  - URL 正規化（トラッキングパラメータ除去、スキーム/ホストの小文字化、フラグメント削除、クエリソート）を実装。
  - 記事 ID を正規化 URL の SHA-256（先頭 32 文字）で生成して冪等性を確保。
  - defusedxml を用いた安全な XML パース、受信サイズ制限（最大 10MB）、SSRF 対策の方針を明示。
  - raw_news / news_symbols などの DB 保存を想定したバルク INSERT 実装方針（チャンク処理）。

- リサーチ関連 (kabusys.research)
  - ファクター算出および解析ユーティリティを実装:
    - calc_momentum, calc_volatility, calc_value（kabusys.research.factor_research）
    - calc_forward_returns, calc_ic, factor_summary, rank（kabusys.research.feature_exploration）
  - DuckDB 上の prices_daily / raw_financials テーブルのみを使用する設計。外部 API への依存なし。
  - ランク相関（Spearman ρ）や統計サマリー（count/mean/std/min/max/median）の計算を実装。

- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - research で算出した生ファクターを統合・正規化して features テーブルに保存する build_features 関数を実装。
  - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
  - Z スコア正規化（外部 zscore_normalize を使用）、±3 でクリップ。
  - 日付単位での置換（DELETE → INSERT）をトランザクションで実装し、冪等性・原子性を保証。

- シグナル生成 (kabusys.strategy.signal_generator)
  - features と ai_scores を統合して最終スコア（final_score）を算出し、BUY / SELL シグナルを生成する generate_signals 関数を実装。
  - コンポーネントスコア（momentum / value / volatility / liquidity / news）計算と重み付け合算を実装（デフォルト重みを内蔵）。
  - 重みの入力検証（負値/NaN/未知キーを無視）と合計を 1.0 に再スケールするロジックを実装。
  - Bear レジーム判定（ai_scores の regime_score 平均が負の場合に BUY を抑制）。
  - エグジット判定（ストップロス -8% / final_score が閾値未満）を実装。positions テーブルからの最新ポジション・最新価格参照を行う。
  - signals テーブルへの日付単位置換をトランザクションで実装（BUY は rank を付与、SELL は優先）。

### 変更 (Changed)
- なし（初回リリースのため既存変更なし）

### 修正 (Fixed)
- なし（初回リリース）

### セキュリティ (Security)
- RSS の XML パースに defusedxml を採用して XML Bomb 等の攻撃に対策。
- ニュース収集で受信バイト数の上限（10MB）を設け、メモリ DoS を軽減する設計。

### 仕様メモ / 運用上の注意 (Notes)
- 必須環境変数
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は Settings 経由で必須チェックされます。未設定時は ValueError が発生します。
- 自動 .env 読み込み
  - プロジェクトルートが検出されれば .env → .env.local の順で自動読み込みします。OS 環境変数が優先され、.env.local は上書き（override=True）されます。
  - テスト等で自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- データベースのデフォルトパス
  - DuckDB: data/kabusys.duckdb（環境変数 DUCKDB_PATH で変更可能）
  - SQLite (monitoring 用): data/monitoring.db（環境変数 SQLITE_PATH で変更可能）
- 外部依存
  - duckdb（ランタイムで DuckDB Python API を利用）
  - defusedxml（RSS パースの安全化に使用）
  - できるだけ標準ライブラリ（urllib 等）で HTTP を実装する方針。ただし運用環境での信頼性を考慮の上、HTTP クライアントの差し替えは検討可。
- テーブル期待スキーマ（概要）
  - prices_daily, raw_prices, raw_financials, market_calendar, features, ai_scores, positions, signals, raw_news などを前提に処理を実装。各関数はこれらのテーブルを参照/更新します。
- Look-ahead バイアス対策
  - 取得タイムスタンプ（fetched_at）を UTC で保存する等、「いつデータを知り得たか」を追跡する実装方針を採用。

### 既知の未実装 / 将来実装予定 (Known limitations)
- signal_generator のエグジット条件の一部（トレーリングストップ、時間決済）は positions テーブルに peak_price / entry_date 等の情報が必要であり、現時点では未実装としてコメントに記載。
- 一部の分析処理は外部ライブラリ（pandas 等）を使わずに標準ライブラリで実装しているため、パフォーマンス改善の余地がある。
- news_collector の完全な RSS フィード収集ループや記事→銘柄マッチングロジック（news_symbols への紐付け）は設計方針を示しているが、実運用での拡張が想定される。

----

今後のリリースでは、実運用で得られたフィードバックに基づく安定化、テスト追加、パフォーマンス最適化、外部 HTTP クライアントの選定、監視/モニタリング機能の充実などを予定しています。