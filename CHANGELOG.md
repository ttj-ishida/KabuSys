# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。

## [0.1.0] - 2026-03-19

初回リリース。日本株自動売買システム "KabuSys" の基礎機能を実装しました。主な追加点、設計方針、既知の制約や移行注意点を以下にまとめます。

### 追加 (Added)
- パッケージ基盤
  - パッケージ名: kabusys、バージョン 0.1.0
  - パッケージ初期化（__all__）に data / strategy / execution / monitoring を公開。

- 設定管理 (kabusys.config)
  - .env / .env.local からの自動読み込み（読み込み順: OS 環境変数 > .env.local > .env）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化機能。
  - .git または pyproject.toml を基準にプロジェクトルートを探す実装（CWD 非依存）。
  - 環境変数取得用 Settings クラスを導入（必須値取得の _require を含む）。
  - 必須の環境変数:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - デフォルト値:
    - KABUSYS_ENV: "development"（有効値: development / paper_trading / live）
    - LOG_LEVEL: "INFO"（有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL）
    - KABU_API_BASE_URL: "http://localhost:18080/kabusapi"
    - DUCKDB_PATH, SQLITE_PATH のデフォルトパスをサポート

- データ取得・保存 (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装:
    - レート制限制御（_RateLimiter、120 req/min 固定間隔スロットリング）。
    - 再試行ロジック（指数バックオフ、最大リトライ 3 回、408/429/5xx を対象）。
    - 401 が返る場合のトークン自動リフレッシュ（1 回のみ）とトークンキャッシュ。
    - ページネーション対応の fetch_* メソッド:
      - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
    - DuckDB への保存関数（冪等化: ON CONFLICT DO UPDATE）
      - save_daily_quotes → raw_prices
      - save_financial_statements → raw_financials
      - save_market_calendar → market_calendar
    - 入力データの型変換ユーティリティ (_to_float, _to_int)

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードから記事を収集して raw_news に保存する処理を追加。
  - セキュリティ・堅牢化:
    - defusedxml を用いた XML パース（XML Bomb 等の防御）。
    - 受信サイズ制限（MAX_RESPONSE_BYTES = 10MB）。
    - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト正規化、フラグメント除去）。
    - 記事ID は正規化 URL の SHA-256（先頭 32 文字）で冪等性を確保。
    - HTTP スキーム以外を拒否する等の SSRF 対策の想定（コード内に検証ロジックを配置）。
  - デフォルト RSS ソースを提供（例: Yahoo Finance ビジネスカテゴリ）。

- 研究（Research）モジュール (kabusys.research)
  - ファクター計算:
    - calc_momentum, calc_volatility, calc_value（prices_daily / raw_financials を参照）
  - 特徴量探索・評価:
    - calc_forward_returns（複数ホライズン対応、デフォルト [1,5,21]）
    - calc_ic（Spearman の rank 相関による IC 計算）
    - factor_summary（count/mean/std/min/max/median）
    - rank（同順位は平均ランク処理）
  - 外部依存を極力避ける設計（標準ライブラリ + duckdb を想定）

- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - build_features(conn, target_date):
    - research モジュールから算出された生ファクターをマージ。
    - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 >= 5 億円）適用。
    - 正規化: zscore_normalize を適用し ±3 でクリップ。
    - features テーブルへの日付単位の置換（DELETE + bulk INSERT、トランザクションで原子性保証）。
    - 冪等性を担保。

- シグナル生成 (kabusys.strategy.signal_generator)
  - generate_signals(conn, target_date, threshold=0.60, weights=None):
    - features と ai_scores を統合して各コンポーネントスコアを計算（momentum/value/volatility/liquidity/news）。
    - コンポーネント毎のスコア計算ロジックを実装（sigmoid や逆 PER 処理など）。
    - デフォルト重み（momentum:0.40, value:0.20, volatility:0.15, liquidity:0.15, news:0.10）をサポートし、ユーザー重みを検証・正規化。
    - Bear レジーム検知（AI の regime_score 平均が負の場合に BUY を抑制）。
    - BUY シグナル（threshold 以上）と SELL（ストップロス -8% / final_score < threshold）を生成。
    - SELL を優先して BUY を除外、signals テーブルへの日付単位置換で書き込み（トランザクションで原子性保証）。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- news_collector で defusedxml と受信サイズ制限を導入し、XML インジェクション・DoS のリスク軽減を図っています。
- J-Quants クライアントはトークン管理とレート制御を備え、認証失敗時に自動リフレッシュ処理を安全に行います。

### 既知の制約・未実装の機能 (Known issues / Notes)
- signal_generator のエグジット条件で以下は未実装（実装コメントあり）:
  - トレーリングストップ（peak_price / entry_date 等の positions テーブル拡張が必要）
  - 時間決済（保有 60 営業日超過）
- research モジュールは外部の高速データフレームライブラリ（pandas 等）に依存しない実装を目指していますが、大規模データでのパフォーマンスは検証が必要です。
- _RateLimiter は固定間隔スロットリング（単純実装）であり、peak なトラフィックや複数プロセス・分散環境での厳密なレート制御は想定していません。
- news_collector の URL 正規化・SSRF 防止ロジックは複雑なケース（プロキシ、IPv6、特殊ホスト名等）で追加検証が必要です。
- jquants_client の _request は urllib を使用した同期実装のため、大量同時リクエストや非同期処理には最適化が必要です。

### マイグレーション / 利用時の注意 (Migration / Upgrade notes)
- 必須環境変数を必ず設定してください。未設定だと Settings プロパティから ValueError が発生します。
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- DuckDB スキーマ（raw_prices / raw_financials / market_calendar / features / ai_scores / positions / signals 等）は本パッケージの各関数が期待するカラム構成を前提としています。既存 DB を利用する場合はスキーマ互換を確認してください。
- KABUSYS_ENV と LOG_LEVEL は許容値チェックを行うため、不正値を入れると起動時に例外になります。

---

今後の予定（例）
- execution 層との統合（kabu API を使った実際の発注ロジック）
- モニタリング・アラート機能（Slack 通知等）の実装
- トレーリングストップや時間決済など追加のエグジットロジック
- 非同期化・並列化によるデータ収集の高速化

もしリリース日や記載内容の形式を変更したい場合は教えてください。