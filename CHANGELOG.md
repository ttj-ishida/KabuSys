# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このファイルはリポジトリのコードベースから機能・振る舞いを推測して作成しています。

## [Unreleased]

## [0.1.0] - 2026-03-22

初回リリース。日本株自動売買フレームワーク「KabuSys」のコア機能を実装しました。主な追加点・設計方針は以下の通りです。

### Added
- パッケージ初期化
  - kabusys パッケージのバージョン情報を追加（__version__ = "0.1.0"）。
  - パッケージ API として "data", "strategy", "execution", "monitoring" を公開。

- 設定管理（kabusys.config）
  - .env / .env.local ファイルと OS 環境変数から設定を読み込む自動ロード機能を実装。
  - プロジェクトルート検出（.git / pyproject.toml）に基づく自動読み込み。
  - .env パーサ（引用符・エスケープ・export プレフィックス・インラインコメントの取り扱い）を実装。
  - .env の上書きルール（.env は既存環境変数を上書きしない、.env.local は上書きする）と保護（OS 環境変数は protected）を実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化フラグをサポート（テスト用途想定）。
  - Settings クラスを提供し、必須変数の取得（_require）や既定値、検証（KABUSYS_ENV / LOG_LEVEL）の整合性チェックを実装。
  - データベースパス（DUCKDB_PATH / SQLITE_PATH）、Slack / kabu API / J-Quants の設定項目を定義。

- 戦略（kabusys.strategy）
  - 特徴量エンジニアリング（feature_engineering.build_features）
    - research モジュールで算出した生ファクターを収集・マージし、ユニバースフィルタ（最低株価・最低平均売買代金）を適用。
    - 指定カラムを Z スコア正規化（zscore_normalize を利用）し ±3 でクリップ。
    - 日付単位の原子性を保った UPSERT（DELETE → INSERT をトランザクションで実行）で features テーブルを更新。
    - ルックアヘッドバイアス防止のため target_date 時点のデータのみ使用。

  - シグナル生成（signal_generator.generate_signals）
    - features と ai_scores を統合して個別コンポーネントスコア（momentum / value / volatility / liquidity / news）を算出。
    - コンポーネントごとの変換（シグモイド、PER の逆数近似、ボラ反転など）を実装。
    - デフォルト重み（momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）を導入し、外部渡し weights をバリデート・正規化して適用。
    - Bear レジーム判定（AI の regime_score の市場平均が負）による BUY 抑制機能を実装。
    - 保有ポジションのエグジット判定（ストップロス、スコア低下）による SELL シグナル生成を実装。
    - 日付単位の原子性を保った signals テーブル更新（トランザクション + バルク挿入）。
    - weights の不正値を警告して無視する堅牢化、欠損コンポーネントは中立値 0.5 で補完する挙動を採用。

- Research（kabusys.research）
  - ファクター計算（factor_research）
    - momentum（mom_1m, mom_3m, mom_6m, ma200_dev）計算（LAG / 移動平均を用いた SQL 実装）。
    - volatility（atr_20, atr_pct, avg_turnover, volume_ratio）計算（true range の扱い、部分窓の扱い）。
    - value（per, roe）計算（raw_financials から target_date 以前の最新財務を取得して株価と組合せ）。
    - DuckDB の SQL ウィンドウ関数を活用した効率的実装。関数は prices_daily / raw_financials のみ参照。

  - 特徴量探索（feature_exploration）
    - 将来リターン計算（calc_forward_returns）：複数ホライズン（デフォルト [1,5,21]）に対応し、LEAD を用いて一度のクエリで取得。
    - IC（calc_ic）：ファクターと将来リターンのスピアマンランク相関を計算（ties は平均ランクで扱う）。
    - 統計サマリー（factor_summary）：count/mean/std/min/max/median を計算。
    - ランク関数（rank）を提供（同順位は平均ランク、浮動小数の丸めによる ties の漏れ対策あり）。
    - 標準ライブラリのみでの実装を意図。

- バックテスト（kabusys.backtest）
  - シミュレータ（simulator）
    - PortfolioSimulator を実装（現金・保有・平均取得単価・履歴・トレード記録を管理）。
    - 約定処理（execute_orders）で SELL を先に処理、BUY は全額割当で購入。スリッページ・手数料モデルを適用。
    - BUY の株数算出、手数料込みでの再計算ロジック、平均取得単価の更新を実装。
    - SELL は保有全量クローズ（部分利確・部分損切りは未対応）。
    - 終値評価により DailySnapshot（date, cash, positions, portfolio_value）を記録。

  - メトリクス（metrics）
    - バックテスト結果から CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, Total Trades を計算する関数を実装。
    - 各指標の内部計算関数を提供し、データ不足時のフォールバック（0.0）を定義。

  - エンジン（engine.run_backtest）
    - 本番 DB から期間限定のデータをコピーして in-memory DuckDB を構築（signals / features 等は日付フィルタ付きでコピー）。
    - 日次ループ：前日シグナル約定 → positions 書き戻し → mark_to_market → generate_signals 実行 → シグナル読取 → ポジションサイジング → 次日約定 というフローを実装。
    - get_trading_days（外部）を用いた営業日管理、在庫状態を positions テーブルへ冪等に書き戻す実装。
    - バックテスト設定（slippage_rate, commission_rate, max_position_pct, initial_cash）をサポート。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed / Deprecated
- （初回リリースのため該当なし）

### Notes / Known limitations
- feature_engineering / signal_generator の設計は「ルックアヘッドバイアス防止」を重視し、target_date 時点のデータのみ使用するようになっています。
- signal_generator の SELL 条件では以下の未実装事項が明記されています：
  - トレーリングストップ（peak_price が positions に必要）
  - 時間決済（保有 60 営業日超過）
- PortfolioSimulator の BUY は部分保有（分割買い）や複雑なポジションサイズ調整をサポートしていません（将来的な拡張ポイント）。
- calc_forward_returns の horizons は 1〜252 営業日に制約。無効な値は ValueError を投げます。
- .env パースはかなり柔軟に実装されていますが、極端に壊れた .env 内容は想定外の挙動を招く可能性があります。
- generate_signals は ai_scores が無い場合でも動作するよう中立値で補完しますが、AI スコアの品質に依存する挙動のため実運用前に検証が必要です。

---

今後の予定（例）
- 部分利確・トレーリングストップ・時間決済などのエグジット条件を実装
- execution 層（実売買接続）と監視 (monitoring) の実装・統合
- テストカバレッジの追加とエラーケースの強化
- パフォーマンスチューニング（大規模銘柄数での DuckDB クエリ最適化）

もしこの CHANGELOG の内容をさらに詳細化（関数単位の変更履歴や責務分離、リリース日付の変更など）したい場合は、どの粒度で記載するか指示してください。