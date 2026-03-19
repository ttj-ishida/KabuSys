# CHANGELOG

すべての変更は Keep a Changelog の方針に従って記載しています。  
このファイルはパッケージのコードベース（src/kabusys 以下）の実装内容から推測して作成しています。

## [Unreleased]
（次バージョンに向けた変更や予定機能をここに追記します）

## [0.1.0] - 2026-03-19
初回公開リリース。日本株の自動売買・リサーチ基盤として以下の主要機能を実装しています。

### 追加
- パッケージ初期化
  - kabusys パッケージのメタ情報を追加（__version__ = "0.1.0"）。
  - 公開 API をパッケージレベルでエクスポート（data, strategy, execution, monitoring）。

- 環境設定 / 設定管理（kabusys.config）
  - .env / .env.local の自動読み込み機能を実装。読み込み優先順位は OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプションを追加（テスト等で利用）。
  - .git または pyproject.toml を基準にプロジェクトルートを探索するロジックを実装（CWD 非依存）。
  - .env の行パーサー追加（export プレフィックス対応、シングル/ダブルクォート内のエスケープ、インラインコメント処理）。
  - 環境変数取得ユーティリティ _require と Settings クラスを追加。J-Quants / kabu API / Slack / DB パス / 実行環境（env）/ログレベル等のアクセスを提供。
  - env（development / paper_trading / live）と log_level（DEBUG/INFO/WARNING/ERROR/CRITICAL）のバリデーションを実装。
  - duckdb/sqlite パスを Path オブジェクトで返す。

- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
    - 固定間隔スロットリングによるレート制限（120 req/min）の実装（内部 RateLimiter）。
    - 冪等性のためのページネーション対応とモジュール内トークンキャッシュ。
    - リトライロジック（指数バックオフ、最大3回、408/429/5xx を対象）。
    - 401 受信時にリフレッシュトークンで自動的に ID トークンを再取得して再試行。
    - データ取得関数を実装（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
    - DuckDB への保存関数を実装（save_daily_quotes, save_financial_statements, save_market_calendar）。ON CONFLICT による更新（アップサート）を行い冪等性を確保。
    - JSON デコードエラーやネットワーク例外に対する適切な例外処理とログ。

  - ユーティリティ関数を実装（_to_float, _to_int）で外部データの型変換を安全に処理。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードから記事を収集して raw_news に保存するための基盤を追加。
  - URL 正規化（トラッキングパラメータ除去、スキーム/ホストの小文字化、クエリキーソート、フラグメント除去）および記事 ID（正規化 URL の SHA-256 ハッシュ先頭）による冪等性の設計。
  - defusedxml を用いた XML パース（XML Bomb 等の防御）、受信最大バイト数制限（MAX_RESPONSE_BYTES）などの安全対策。
  - デフォルト RSS ソース（Yahoo Finance のビジネスカテゴリ）を追加。
  - SQL バルク挿入のチャンク処理とトランザクションでの一括保存設計。

- ファクター計算（kabusys.research.factor_research）
  - Momentum, Volatility, Value（および一部 Liquidity 指標）を DuckDB の prices_daily / raw_financials を基に計算する関数を実装。
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日移動平均乖離）を計算。データ不足の場合は None を返す。
    - calc_volatility: ATR（20日）ベースの atr_20 / atr_pct、avg_turnover、volume_ratio を計算。true_range の NULL 伝播を厳密に扱う設計。
    - calc_value: raw_financials の最新財務レコードを結合して PER / ROE を計算。EPS が 0 や欠損の際には PER を None にする。
  - 各関数は date, code を含む辞書リストを返す設計で、外部 API へのアクセスは行わない。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - research モジュールで計算した生ファクターをマージ・フィルタ・正規化して features テーブルへ保存する build_features を実装。
  - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）を実装。
  - Z スコア正規化（kabusys.data.stats を利用）→ ±3 でクリップの処理を実装。
  - 日付単位での置換（DELETE + INSERT、トランザクション）により冪等性と原子性を確保。
  - 価格参照は target_date 以前の最新価格を使用し、ルックアヘッドを防止。

- シグナル生成（kabusys.strategy.signal_generator）
  - features と ai_scores を統合して final_score を計算し、BUY / SELL シグナルを生成する generate_signals を実装。
  - コンポーネントスコア（momentum / value / volatility / liquidity / news）の計算を実装（シグモイド変換や PER の逆数変換等）。
  - デフォルト重みの導入とユーザ提供 weights の検証・正規化（負値・非数値を無視し合計を 1.0 に再スケール）。
  - Bear レジーム（ai_scores の regime_score 平均が負）検出による BUY シグナル抑制ロジックを実装。
  - エグジット判定（ストップロス -8% / スコア低下）と SELL シグナル生成を実装。価格欠損時は SELL 判定をスキップして安全策を採用。
  - SELL 優先ポリシー（SELL 対象を BUY から除外）と signals テーブルへの日次置換（トランザクション）で冪等性を確保。
  - generate_signals は features が空の場合の挙動（BUY なし、SELL のみ）を明示。

- 研究用解析（kabusys.research.feature_exploration）
  - 将来リターン計算 calc_forward_returns（LEAD を用いた複数ホライズン対応）を実装。horizons の入力検証を実施。
  - IC（Information Coefficient）計算 calc_ic（スピアマンのランク相関）を実装。サンプル不足（<3）や分散ゼロの場合は None を返す保守的設計。
  - rank, factor_summary（count/mean/std/min/max/median）などの補助ユーティリティを実装。
  - pandas 等外部依存を持たず標準ライブラリ + DuckDB で完結する設計。

- パッケージの研究 API エクスポート（kabusys.research.__init__）
  - 主要関数（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）を再エクスポート。

### 変更
- （初回リリースのため該当なし）

### 修正
- （初回リリースのため該当なし）

### 既知の制限 / 注意事項
- NewsCollector の記事 ID は URL 正規化後のハッシュに依存するため、URL の取り扱いルールを変更すると重複判定に影響します。
- calc_momentum / calc_volatility など時系列の計算は「連続する営業日レコード」の数を基準にしており、カレンダー日数のギャップ（祝日など）は DuckDB の prices_daily の連続性に依存します。
- signal_generator の一部エグジット条件（トレーリングストップ、時間決済）は未実装。positions テーブルに peak_price や entry_date を追加すると実装可能。
- J-Quants クライアントは最大リトライやレート制限を備えていますが、実運用では API 仕様変更・レート制限ポリシーの変化に注意してください。
- Settings は必須環境変数が未設定の場合に ValueError を投げます（起動前に .env を用意するか環境変数を設定してください）。

### セキュリティ
- defusedxml を用いた XML パースや RSS の受信バイト数制限、URL のスキーム検査など、外部データ取り込み時の基本的な安全対策を実装しています。
- HTTP 取得時のトークンリフレッシュやエラーハンドリングで無限再帰や情報漏洩にならないよう考慮されています。

---

README やドキュメントに以下を追記すると利用者の導入が容易になります（推奨）：
- 必須環境変数一覧（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など）と .env.example の用意
- DuckDB / SQLite のスキーマ定義（必要なテーブル名とカラム）
- 実際の運用におけるレート制限・リトライ挙動の説明
- signal_generator のパラメータ（weights, threshold）調整例

（この CHANGELOG はコード内容から推測して作成しています。実際のリリースノート作成時はコミット履歴・変更差分に基づき調整してください。）