# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このファイルではリリースごとの主要な追加・変更・修正点、注意事項を日本語で記載しています。

## [Unreleased]

## [0.1.0] - 2026-03-19
初回リリース。日本株自動売買システム「KabuSys」の基礎機能を実装しました。

### 追加
- パッケージ初期化
  - kabusys パッケージの基本構成（__version__ = 0.1.0、__all__）を追加。

- 設定 / 環境変数管理（kabusys.config）
  - プロジェクトルート検出機能を実装（.git または pyproject.toml を探索）。
  - .env ファイルの自動読み込み（OS 環境変数 > .env.local > .env の優先順位）。
  - .env パースロジックの実装（export 形式、シングル/ダブルクォート内のエスケープ、コメント処理等に対応）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート（テスト向け）。
  - Settings クラスを実装し、主要な設定値をプロパティとして提供：
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN（必須）
    - SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV の検証（development / paper_trading / live）
    - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - is_live / is_paper / is_dev ヘルパー

- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装：
    - 固定間隔スロットリングでのレート制御（120 req/min を想定）
    - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx をリトライ対象）
    - 401 受信時のリフレッシュ（1 回のみ）と id_token キャッシュ
    - ページネーション対応の fetch_* 関数（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）
  - DuckDB への冪等保存関数を実装：
    - save_daily_quotes (raw_prices) / save_financial_statements (raw_financials) / save_market_calendar (market_calendar)
    - ON CONFLICT 句を利用して重複更新を回避
    - fetched_at を UTC ISO8601 で記録
    - PK 欠損レコードのスキップ警告

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードからの記事収集基盤を実装（デフォルトに Yahoo Finance のカテゴリ RSS を含む）。
  - セキュリティと堅牢性を考慮した実装：
    - defusedxml を用いた XML パース（XML Bomb 等対策）
    - URL 正規化／トラッキングパラメータ除去（utm_*, fbclid 等）
    - URL スキーム検証（http/https のみ許可想定）
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10 MiB）によるメモリ DoS 防止
    - 記事 ID は正規化 URL の SHA-256 ハッシュ（先頭 32 文字）で生成し冪等性を確保
    - DB へのバルク INSERT をチャンク化（パフォーマンスと SQL 長対策）
    - raw_news に ON CONFLICT DO NOTHING 相当で保存し、news_symbols への紐付けを想定

- 研究モジュール（kabusys.research）
  - ファクター計算ユーティリティの公開 API を集約（calc_momentum / calc_value / calc_volatility / zscore_normalize 等）
  - 特徴量探索モジュール（feature_exploration）を実装：
    - 将来リターン計算（calc_forward_returns、デフォルト horizons = [1,5,21]）
    - IC（Information Coefficient）計算（calc_ic：Spearman ランク相関）
    - 基本統計量サマリー（factor_summary）
    - 安定的なランク付け関数 rank（同順位は平均ランク）

- ファクター計算（kabusys.research.factor_research）
  - Momentum ファクター計算（mom_1m, mom_3m, mom_6m, ma200_dev）
  - Volatility / Liquidity ファクター（atr_20, atr_pct, avg_turnover, volume_ratio）
  - Value ファクター（per, roe） — raw_financials の最新財務データを参照
  - DuckDB を用いた SQL ベースの実装（営業日不連続を考慮したスキャン範囲バッファ）

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - research モジュールから得た生ファクターをマージ、ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用
  - 指定カラムの Z スコア正規化（zscore_normalize を利用）、±3 でクリップ
  - features テーブルへ日付単位で置換（トランザクション＋バルク挿入で冪等性）

- シグナル生成（kabusys.strategy.signal_generator）
  - features と ai_scores を統合して各銘柄の final_score を計算する生成器を実装
  - コンポーネントスコア：momentum / value / volatility / liquidity / news（AI）
  - デフォルト重みと閾値を実装（デフォルト閾値 = 0.60、重みは Model に基づく）
  - Bear レジーム判定（ai_scores の regime_score 平均が負なら Bear）
  - BUY（threshold 超過）と SELL（ストップロス -8%／スコア低下）の生成、保有銘柄に対するエグジット判定を実装
  - signals テーブルへ日付単位で置換（トランザクション＋バルク挿入で冪等性）
  - 重みの入力検証（未知キーや無効値をスキップ、合計が 1.0 でない場合に再スケール）

- 公開 API 集約（kabusys.strategy.__init__ / kabusys.research.__init__）
  - 主要関数をパッケージトップからインポート可能にしたエクスポートを追加

### 変更
- なし（初回リリースにつき既存変更はありません）

### 修正
- なし（初回リリースにつき既知のバグ修正履歴はありません）

### セキュリティ
- news_collector で defusedxml を使用し XML パーサ攻撃対策を導入。
- RSS URL 正規化とスキームチェック、受信サイズ制限により SSRF / メモリ DoS のリスクを低減。

### 既知の制限 / TODO
- signal_generator 内の未実装エグジット条件:
  - トレーリングストップ（peak_price が positions テーブルに必要）
  - 時間決済（保有 60 営業日超過）
- news_collector の一部詳細（実際の RSS フィードパース実装の具体的ロジック）は将来的に拡張予定。
- execution パッケージはスケルトン（発注ロジック／kabu ステーション連携の実実装は今後）。
- DuckDB スキーマ（tables: raw_prices, raw_financials, prices_daily, features, ai_scores, positions, signals, market_calendar, raw_news 等）は本 CHANGELOG に含まれず、別途スキーマ定義が必要。

### マイグレーション / 注意事項
- 必須環境変数（未設定時は起動時にエラーになる）:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- 自動 .env ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用）。
- デフォルト DB パス:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
- J-Quants API 呼び出しは rate limit（120 req/min）を前提として設計されています。大量取得時は制御に注意してください。
- news_collector の外部 URL 関連処理はセキュリティ上の制約（http/https 以外禁止など）を持ちます。カスタム RSS を使う際はフィードの互換性にご注意ください。

---

フィードバックや改善提案は歓迎します。必要であれば各モジュールごとの詳細な変更ログ（関数一覧、引数仕様、戻り値の型、例）も作成します。