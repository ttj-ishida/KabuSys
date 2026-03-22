# Changelog

すべての変更は「Keep a Changelog」フォーマットに従い、慣例に沿ってカテゴリ分けしています。  
このファイルは、提供されたコードベースの内容から推測して作成した初期リリース（v0.1.0）の変更履歴です。

※日付はコード解析時点のものです。

## [Unreleased]
- （今後の変更をここに記載）

## [0.1.0] - 2026-03-22
初回リリース。日本株自動売買システム「KabuSys」のコア機能を実装。

### Added
- パッケージ基本情報
  - パッケージ名・バージョンを定義（src/kabusys/__init__.py, __version__ = "0.1.0"）。
  - パッケージ公開 API に data, strategy, execution, monitoring を含める。

- 環境設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
  - プロジェクトルート検出: .git または pyproject.toml を基準に探索（cwd に依存しない実装）。
  - .env ファイルパーサーを実装:
    - export KEY=val 形式、クォート付き値（エスケープ処理）、コメント（#）の取り扱いに対応。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - OS 環境変数を保護する protected 上書き制御を実装（.env と .env.local の優先順位処理）。
  - Settings クラスを提供し、必要な環境値（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID 等）をプロパティとして取得。env/log_level のバリデーションと is_live / is_paper / is_dev ヘルパーを実装。
  - デフォルト DB パス（duckdb/sqlite）に対する Path 型プロパティを用意。

- 研究用ファクター計算（src/kabusys/research/*.py）
  - ファクター計算モジュール（factor_research）を実装:
    - モメンタム（mom_1m / mom_3m / mom_6m / ma200_dev）
    - ボラティリティ / 流動性（atr_20, atr_pct, avg_turnover, volume_ratio）
    - バリュー（per, roe） — raw_financials と prices_daily の組合せで算出
    - DuckDB SQL を用いた効率的なウィンドウ集計と欠損制御
  - 特徴量探索モジュール（feature_exploration）を実装:
    - 将来リターン計算 calc_forward_returns（任意ホライズン、horizons デフォルト=[1,5,21]）
    - ランク相関（Spearman）による IC 計算 calc_ic（最小サンプルチェック）
    - 基本統計量を返す factor_summary（count/mean/std/min/max/median）
    - ランク付けユーティリティ rank（同順位は平均ランク、丸め対策あり）
  - 研究モジュールは外部ライブラリ（pandas 等）に依存せず、DuckDB と標準ライブラリのみで実装。

- 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
  - research 側で算出した raw ファクターを統合し、features テーブルへ書き込む build_features を実装。
  - ユニバースフィルタ（最低株価 _MIN_PRICE=300 円、20日平均売買代金 _MIN_TURNOVER=5e8）を適用。
  - 正規化: zscore_normalize を利用して指定カラムを Z スコア化し、±3 でクリップ（_ZSCORE_CLIP）。
  - 日付単位での置換（DELETE + bulk INSERT, トランザクションで原子性確保）により冪等性を担保。
  - 欠損・価格欠損に対する安全策を組み込み（価格マップ参照で当日欠損や休場日対応）。

- シグナル生成（src/kabusys/strategy/signal_generator.py）
  - features と ai_scores を組み合わせ、final_score を計算して BUY/SELL シグナルを生成する generate_signals を実装。
  - デフォルトの重み（momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）と閾値（_DEFAULT_THRESHOLD=0.60）を設定。
  - コンポーネントスコア計算:
    - momentum: momentum_20, momentum_60, ma200_dev を sigmoid 後平均
    - value: PER に基づく 1 / (1 + per/20) 形式
    - volatility: atr_pct の Z スコアを反転して sigmoid
    - liquidity: volume_ratio を sigmoid
    - news: ai_score を sigmoid（未登録は中立）
  - 欠損値の補完ポリシー: コンポーネントが None の場合は中立 0.5 で補完して不当な降格を防止。
  - Bear レジーム判定: ai_scores の regime_score 平均が負であれば BUY を抑制（サンプル数閾値 _BEAR_MIN_SAMPLES あり）。
  - SELL 条件（エグジット）を実装:
    - ストップロス（終値 / avg_price - 1 < -8%）
    - スコア低下（final_score < threshold）
    - positions テーブルに price 欠損等がある場合の警告と挙動定義
  - signals テーブルへの日付単位置換（トランザクション + bulk insert）で冪等性を保証。
  - ユーザが渡す weights は検証・正規化され、既知キーのみ受け入れ合計が 1 に再スケールされる。

- バックテストフレームワーク（src/kabusys/backtest/*）
  - PortfolioSimulator（simulator.py）を実装:
    - 約定ロジック（SELL 優先、SELL は保有全量クローズ、BUY の株数は floor）、スリッページ（slippage_rate）、手数料（commission_rate）を反映。
    - 平均取得単価管理（cost_basis）、現金処理、TradeRecord・DailySnapshot の収集。
    - mark_to_market により終値での評価を行い DailySnapshot を履歴に追加。終値欠損時は 0 で評価して警告を出力。
  - run_backtest（engine.py）を実装:
    - 本番 DB から必要テーブルをインメモリ DuckDB（init_schema(":memory:")）にコピーしてバックテストを実行（signals/positions を汚染しない）。
    - コピー対象テーブルと期間の扱い（prices_daily, features, ai_scores, market_regime を start_date-300 日から end_date までフィルタしてコピー、market_calendar は全件コピー）。
    - 日次ループ: 前日シグナルの約定 → positions 書き戻し → 時価評価 → generate_signals 実行 → signal 読み取り → ポジションサイジング/約定準備。
    - run_backtest は BacktestResult を返却（history, trades, metrics）。
  - バックテストメトリクス（metrics.py）を実装:
    - CAGR、シャープレシオ（無リスク金利=0, 年次化252 営業日換算）、最大ドローダウン、勝率、ペイオフ比、総クローズトレード数を計算する calc_metrics を提供。
    - 指標の内部実装は安全チェック（ゼロ割り回避、データ不足時のデフォルト 0.0）を行う。

- モジュール間の設計方針（明示）
  - strategy / research レイヤは発注 API / execution 層に依存しない純粋な計算ロジックで記述。
  - 研究モジュールは本番リソースやネットワークにアクセスしない。
  - DuckDB を中心とした SQL + Python のハイブリッド実装で、パフォーマンスと可読性のバランスを考慮。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- 環境変数読み込みで OS 環境変数を上書きしない保護機構を実装（protected set）。  
  - .env.local は OS 環境変数を除き .env より優先して上書きされるが、OS の既存環境変数は保護される。

---

脚注:
- 多くの SQL クエリは date をキーに最新/過去データを参照する設計で、休場日や当日欠損に対する安全策が施されています。
- トランザクション処理中の例外時は ROLLBACK を試み、失敗時は warn ログを出力する実装が各所にあります。
- 実行（execution）層の具体的外部 API 呼び出しや Slack 連携等は設定環境変数のプロパティとして用意されていますが、提示コード内には発注接続部分の具体的実装は含まれていません（設計上分離）。
- 本 CHANGELOG はコードの実装内容から推測して作成しています。実際の変更履歴・コミットログが利用可能な場合はそちらを優先してください。