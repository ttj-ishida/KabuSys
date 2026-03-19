# CHANGELOG

すべての変更は Keep a Changelog の形式に従っています。  
このプロジェクトの初期リリースを記録しています。

## [Unreleased]

## [0.1.0] - 2026-03-19
初回リリース。日本株自動売買システム「KabuSys」のコア機能を実装しました。

### 追加 (Added)
- パッケージ構成
  - パッケージエントリポイント `kabusys` を追加し、主要サブパッケージを公開（data, strategy, execution, monitoring）。
  - パッケージバージョンを `__version__ = "0.1.0"` に設定。

- 環境設定
  - `kabusys.config` モジュールを追加：
    - .env / .env.local をプロジェクトルート（.git または pyproject.toml 基準）から自動読み込み（`KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能）。
    - .env の行パース機能を強化（`export `プレフィックス対応、クォート内のエスケープ、インラインコメント処理など）。
    - 環境変数上書きロジック（override/protected）を実装。OS 環境変数を保護可能。
    - `Settings` クラスを導入し、J-Quants / kabu API / Slack / DB パス / 実行環境等の設定プロパティを提供。
    - `KABUSYS_ENV` と `LOG_LEVEL` に対する値検証（許容値チェック）とユーティリティプロパティ（is_live / is_paper / is_dev）を追加。

- データ取得・保存
  - `kabusys.data.jquants_client` を追加：
    - J-Quants API クライアント（株価、財務、マーケットカレンダー）。
    - 固定間隔レートリミッタ（120 req/min）を実装。
    - リトライ（指数バックオフ、最大 3 回）、HTTP ステータスに基づくリトライ制御、429 の Retry-After 尊重。
    - 401 を検知してリフレッシュトークンから自動的に ID トークンを再取得し 1 回リトライする仕組み。
    - ページネーション対応の fetch 関数（daily_quotes, financial_statements, market_calendar）。
    - DuckDB へ冪等（ON CONFLICT DO UPDATE）で保存する save_* 関数（raw_prices, raw_financials, market_calendar）。
    - 型変換ヘルパー `_to_float`, `_to_int`（異常値や空文字列を適切に None と扱う）。

  - `kabusys.data.news_collector` を追加：
    - RSS フィードからニュースを収集して `raw_news` へ冪等保存する処理（記事IDは正規化 URL の SHA-256 先頭を利用して一意化）。
    - URL 正規化（トラッキングパラメータ除去、ソート、フラグメント削除、スキーム/ホスト小文字化）。
    - defusedxml を利用した XML パース（XML Bomb 等の緩和）。
    - 受信サイズ上限（10 MB）やバルク挿入チャンク（1000）など DoS 緩和措置。
    - 記事テキスト前処理（URL 除去、空白正規化）と銘柄紐付けの方針を文書化。

- 研究（Research）
  - `kabusys.research` パッケージを追加（research 用ユーティリティとファクター計算）。
  - `factor_research`：
    - Momentum（1M/3M/6M リターン、MA200 乖離）計算。
    - Volatility（20日 ATR、相対 ATR、20日平均売買代金、出来高比率）計算。
    - Value（PER、ROE）計算。`raw_financials` から target_date 以前の最新財務データを参照。
    - 各関数は DuckDB の prices_daily / raw_financials テーブルのみを参照、データ不足時の安全な None ハンドリングを実装。
  - `feature_exploration`：
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）。
    - Information Coefficient（Spearman の ρ）計算（同順位の平均ランク処理、round による ties 対策）。
    - factor_summary（count/mean/std/min/max/median）等の統計要約。

- 戦略（Strategy）
  - `kabusys.strategy.feature_engineering`：
    - 研究で計算した raw ファクターを統合して `features` テーブルへ保存する `build_features` を実装。
    - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 >= 5 億円）を実装。
    - 正規化（zscore_normalize を使用）後、Z スコアを ±3 でクリップ。
    - 日付単位の置換（DELETE + INSERT）で冪等性と原子性を確保（トランザクション使用）。
  - `kabusys.strategy.signal_generator`：
    - `generate_signals` を実装。`features` と `ai_scores` を統合して final_score を算出。
    - コンポーネントスコア（momentum / value / volatility / liquidity / news）の計算ロジックを実装（シグモイド変換、欠損は中立 0.5 で補完）。
    - 重みのマージ・検証・再スケーリング機能を実装（未知キー・非数値は無視）。
    - Bear レジーム判定（ai_scores の regime_score の平均が負の場合、ただしサンプル数閾値あり）。
    - BUY シグナル生成（閾値デフォルト 0.60、Bear 時は BUY を抑制）。
    - SELL シグナル生成（ポジションに対するエグジット判定）：ストップロス（-8%）およびスコア低下によるエグジット。
    - SELL 優先の振る舞い（SELL 対象は BUY から除外）と signals テーブルへの日付単位置換（トランザクション使用）。

### 変更 (Changed)
- なし（初回リリースのため該当なし）。

### 修正 (Fixed)
- なし（初回リリースのため該当なし）。

### 既知の制限・未実装 (Known issues / Not implemented)
- signal_generator 内の一部エグジット条件（トレーリングストップ、時間決済）は未実装（コード内に TODO として記載）。これらは positions テーブルに peak_price / entry_date 情報が必要。
- news_collector の SSRF 緩和やネットワーク制限については設計方針を文書化しているが、運用環境に応じた追加検証が必要。
- 外部ライブラリ（pandas 等）に依存しない実装のため、大規模データでのパフォーマンスチューニングは今後の改善領域。

### セキュリティ (Security)
- news_collector で defusedxml を利用して XML 関連の脆弱性（XML Bomb 等）に対処。
- news_collector における URL 正規化とトラッキングパラメータ除去により、同一記事の重複登録と追跡パラメータの漏洩を低減。
- jquants_client のトークン自動リフレッシュ処理では再帰を避けるため allow_refresh フラグを導入し、不正な無限リトライを防止。

---

注記：
- 各モジュールの詳細な挙動・設計方針はソースの docstring に記載しています。運用・検証時はデータベーススキーマ（tables: raw_prices, raw_financials, prices_daily, features, ai_scores, positions, signals, market_calendar, raw_news 等）との整合性を確認してください。