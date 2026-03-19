# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
このファイルはリポジトリ内のコード内容から推測して作成した初期の変更履歴です。

## [Unreleased]
- 現時点で未リリースの変更はありません。

## [0.1.0] - 2026-03-19
初回リリース。日本株自動売買システム「KabuSys」のコア機能を実装。

### 追加 (Added)
- パッケージ基本構成
  - パッケージエントリポイントを追加（src/kabusys/__init__.py）。公開モジュール: data, strategy, execution, monitoring。
  - バージョン情報 __version__ を "0.1.0" に設定。

- 設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを実装。
  - プロジェクトルート検出: .git または pyproject.toml を探索して自動的に .env/.env.local をロード（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
  - .env パーサを実装（export プレフィックス、クォート、エスケープ、インラインコメント、トラッキング対応）。
  - 環境変数の必須チェック（_require）。設定値のバリデーション（KABUSYS_ENV, LOG_LEVEL）を追加。
  - デフォルト設定: KABUSYS_API_BASE_URL などのフォールバック値とデータベースパス（DUCKDB_PATH/SQLITE_PATH）を提供。

- データ取得・保存 (src/kabusys/data/jquants_client.py)
  - J-Quants API クライアントを実装。
    - 固定間隔のレートリミッタ（120 req/min）を実装。
    - 再試行（指数バックオフ、最大3回）、408/429/5xx のハンドリング。
    - 401 受信時のトークン自動リフレッシュをサポート（1回のみ）。
    - ページネーション対応で全件取得。
    - Look-ahead バイアス対策として fetched_at を UTC で記録。
    - DuckDB へ冪等に保存する save_* 関数（raw_prices/raw_financials/market_calendar）を提供（ON CONFLICT による UPSERT）。
  - 型変換ユーティリティ _to_float/_to_int を実装し、不正値を安全に処理。

- ニュース収集 (src/kabusys/data/news_collector.py)
  - RSS フィードからニュースを収集して raw_news に保存するモジュールを実装。
  - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント除去）を実装。
  - RSS XML の安全なパースに defusedxml を使用。
  - HTTP レスポンスサイズ制限（最大 10MB）や SSRF 対策等を考慮した実装方針を採用。
  - 挿入はチャンク化してバルクINSERT（パフォーマンス考慮）。記事IDは正規化 URL のハッシュを用いることで冪等性を担保。

- リサーチ／ファクター計算 (src/kabusys/research/)
  - ファクター計算モジュール（factor_research.py）を実装。
    - Momentum（mom_1m/mom_3m/mom_6m, ma200_dev）
    - Volatility（atr_20, atr_pct, avg_turnover, volume_ratio）
    - Value（per, roe） — raw_financials と prices_daily の組合せで計算
    - DuckDB を用いた SQL ベースの高効率な計算。データ不足時の None 対応。
  - 特徴量探索モジュール（feature_exploration.py）を実装。
    - 将来リターン計算 calc_forward_returns（複数ホライズン対応、1/5/21 日をデフォルト）
    - IC（Information Coefficient）計算 calc_ic（Spearman ρ、rank ベース）
    - ファクター統計要約 factor_summary（count/mean/std/min/max/median）
    - ランク変換ユーティリティ rank（同順位は平均ランク、浮動小数の丸め制御）

- 特徴量エンジニアリング (src/kabusys/strategy/feature_engineering.py)
  - research モジュールで算出した生ファクターをマージ・ユニバースフィルタ適用・正規化して features テーブルへ保存する build_features を実装。
  - ユニバースフィルタ: 最低株価（300円）・20日平均売買代金（5億円）を適用。
  - Zスコア正規化（zscore_normalize を利用）、±3 でクリップ、日付単位での置換（DELETE→INSERT をトランザクションで実行）により冪等性を確保。

- シグナル生成 (src/kabusys/strategy/signal_generator.py)
  - features と ai_scores を統合し final_score を計算、BUY/SELL シグナルを生成する generate_signals を実装。
  - コンポーネントスコア: momentum, value, volatility, liquidity, news（AI）を計算するユーティリティを実装。
    - シグモイド変換、欠損値は中立値 0.5 で補完。
    - 値の許容重みを受け付け、合計が 1.0 になるよう再スケール。無効な重みはログ警告して無視。
  - Bear レジーム検知（ai_scores の regime_score の平均が負の場合、サンプル数閾値あり）による BUY 抑制。
  - エグジット条件（売りシグナル）としてストップロス（-8%）とスコア低下を実装。トレーリングストップ等は将来実装予定（未実装箇所はコメントで明示）。
  - signals テーブルへの日付単位置換をトランザクションで実行（冪等性確保）。ROLLBACK 時のログを実装。

- トランザクション／エラーハンドリング
  - データベース操作は原子性を保つためトランザクション（BEGIN/COMMIT/ROLLBACK）でまとめて実行。ROLLBACK の失敗時は警告ログを出力。

- ロギング・入力検証
  - 各処理で適切なログ出力（info/debug/warning）を追加。
  - 入力値・環境変数の妥当性チェックを多くの箇所で実装（負値・NaN/Inf・None の扱いを明示）。

### 変更 (Changed)
- 初回リリースにつき該当無し。

### 修正 (Fixed)
- 初回リリースにつき該当無し。

### 廃止 (Deprecated)
- 初回リリースにつき該当無し。

### セキュリティ (Security)
- RSS パーシングに defusedxml を採用し XML 攻撃対策を実施。
- ニュース収集で HTTP スキームの検証、レスポンスサイズ制限（メモリ DoS 対策）などを実装。
- J-Quants API クライアントにて認証トークンの自動リフレッシュを実装し、認証失敗時の安全なリトライをサポート。

### 既知の制限・今後の実装予定
- signal_generator の売却ロジックではトレーリングストップや保持期間によるタイムアウト等が未実装（コード内で明示）。positions テーブルに peak_price / entry_date を追加すれば対応可能。
- 一部の集計・統計処理は duckdb SQL と標準ライブラリのみで実装しており、外部依存（pandas 等）は排除しているが、将来的に解析用の補助ツールを追加する可能性あり。

----

注: 本 CHANGELOG は提供されたコード内容から推測して作成したもので、コミット単位の履歴ではありません。今後のコミットでは "Unreleased" セクションを更新し、リリースごとに新しいバージョンエントリを追加してください。