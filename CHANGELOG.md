# Changelog

すべての重要な変更を記録します。本ファイルは「Keep a Changelog」準拠の形式で記載しています。

フォーマット:
- 追加 (Added)
- 変更 (Changed)
- 修正 (Fixed)
- 削除 (Removed)
- セキュリティ (Security)
- その他注記 (Notes)

※ 日付はリリース日です。

## [Unreleased]
（未リリースの変更はここに記載）

---

## [0.1.0] - 2026-03-20

初回リリース。日本株自動売買システム「KabuSys」のコアライブラリを公開します。以下の主要コンポーネントと機能を含みます。

### Added
- パッケージ初期化
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。
  - public API として data, strategy, execution, monitoring を公開。

- 環境設定管理 (`kabusys.config`)
  - .env ファイルまたは環境変数から設定を自動ロードする機能を実装（ルート検出は .git または pyproject.toml に依存）。
  - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能（テスト向け）。
  - .env/.env.local の読み込み順序を実装（OS 環境変数を保護するため protected keys を扱う）。
  - .env の各行パーサは export プレフィックス、クォート、エスケープ、インラインコメントを正しく扱う。
  - 必須環境変数取得ヘルパ `_require` と設定ラッパ `Settings` を提供（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_*、DB パス等）。
  - 環境（development / paper_trading / live）やログレベルの検証ロジックを実装。
  - DB パス（DuckDB / SQLite）はデフォルト値を提供（例: data/kabusys.duckdb）。

- データ取得・保存モジュール (`kabusys.data.jquants_client`)
  - J-Quants API クライアントを提供（株価日足、財務データ、マーケットカレンダーの取得）。
  - API レート制限（120 req/min）を守る固定間隔スロットリング実装（RateLimiter）。
  - リトライ・バックオフロジック（最大 3 回、408/429/5xx を対象、429 の Retry-After 優先）。
  - 401 受信時はリフレッシュトークンから ID トークンを自動更新して 1 回リトライする処理を実装。モジュール内で ID トークンをキャッシュ。
  - ページネーション対応（pagination_key によるループ）。
  - DuckDB への保存関数（raw_prices, raw_financials, market_calendar）を実装し、ON CONFLICT（UPSERT）で冪等性を確保。
  - レスポンスパースや型変換用ユーティリティ `_to_float`, `_to_int` を実装。

- ニュース収集モジュール (`kabusys.data.news_collector`)
  - RSS フィードから記事を収集し raw_news へ保存する処理を実装（デフォルトソースに Yahoo Finance）。
  - URL 正規化（utm_* 等トラッキングパラメータ除去、クエリソート、フラグメント削除）。
  - 記事 ID は正規化 URL の SHA-256 を用いて冪等性を保証（先頭 32 文字など）。
  - defusedxml を用いた安全な XML パース、受信バイト上限（10MB）によるメモリ DoS 対策、SSRF 防止の考慮を実装。
  - DB バルク挿入のチャンク化（パフォーマンスと SQL 長制限対策）。

- 研究用ファクター計算・探索 (`kabusys.research`)
  - ファクター計算モジュール（calc_momentum, calc_volatility, calc_value）を実装。prices_daily / raw_financials テーブルのみ参照する設計。
  - 特徴量探索ユーティリティ（calc_forward_returns, calc_ic, factor_summary, rank）を提供。外部ライブラリに依存せず標準ライブラリのみで実装。
  - Spearman（ランク相関）ベースの IC 計算、将来リターン計算（デフォルト horizon = [1,5,21]）、列ごとの統計サマリーを提供。

- 特徴量エンジニアリング (`kabusys.strategy.feature_engineering`)
  - 研究側の生ファクターを統合して features テーブルを構築する `build_features` を実装。
  - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 >= 5 億円）を適用。
  - 指定カラムの Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）と ±3 のクリップを実施。
  - 日付単位での置換（DELETE + bulk INSERT）をトランザクションで行い原子性を保証（冪等）。

- シグナル生成 (`kabusys.strategy.signal_generator`)
  - 正規化済み features と ai_scores を統合して最終スコア final_score を計算し、BUY/SELL シグナルを生成する `generate_signals` を実装。
  - デフォルト重みと閾値: momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10、BUY 閾値 0.60。
  - AI ニューススコアは sigmoid で [0,1] に変換。未登録コンポーネントは中立値 0.5 で補完。
  - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数閾値に達する場合に BUY を抑制）。
  - エグジット（SELL）条件を実装（ストップロス: 終値/avg_price - 1 < -8%、final_score が閾値未満）。保有ポジションの価格欠損時は判定をスキップする安全策あり。
  - signals テーブルへの日付単位置換（トランザクション + bulk INSERT）で冪等性を保証。
  - 重みの入力検証（不正値は警告して無視）、合計が 1.0 でない場合は正規化して適用。

- 実装方針・運用上の配慮（ドキュメント化）
  - ルックアヘッドバイアス回避のため、すべての計算は target_date 時点で利用可能なデータのみを参照。
  - 発注/実行層（execution）への直接依存を持たない設計（戦略は signals テーブルへの出力に専念）。
  - DuckDB 接続を外部から注入することでテスト容易性を確保。

### Changed
- 初回リリースのため該当なし（新規導入）。

### Fixed
- 初回リリースのため該当なし。

### Security
- RSS XML パースに defusedxml を利用して XML Bomb 等を防止。
- 外部 URL 処理でスキーム制限やトラッキングパラメータ除去、受信上限を設けることで SSRF/DoS のリスクを低減。
- J-Quants クライアントの認証トークン取り扱いは最小限にし、リフレッシュ時の無限再帰を防止するフラグを実装。

### Notes / 運用メモ
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など。
- DuckDB のテーブル構成（本実装が参照/書き込みを行う主なテーブル）:
  - prices_daily, raw_prices, raw_financials, market_calendar, features, ai_scores, positions, signals, raw_news
- 大量データ投入はバルク / チャンクで行うため、パフォーマンスに配慮した運用が可能。
- 自動 .env ロードはプロジェクトルートの検出に依存するため、パッケージ配布後は環境変数の管理に注意（CI/CD では KABUSYS_DISABLE_AUTO_ENV_LOAD を利用する等）。

---

今後のリリースで想定される追加項目（例）
- execution 層: kabu ステーションへの発注ラッパ、注文監視・リトライ
- モデル管理: 学習済みモデルの読み込み/更新、自動スコア再計算パイプライン
- モニタリング: Slack 通知・ダッシュボード連携（monitoring モジュール）
- テストカバレッジ拡充とドキュメント例（設定例、DB スキーマ、運用手順）

---