Keep a Changelog に準拠した CHANGELOG.md（日本語）を以下に作成しました。

CHANGELOG.md

全ての注目すべき変更はこのファイルで管理します。

Unreleased
----------

- （現在なし）

0.1.0 - 2026-03-22
------------------

Added
- 初回リリース。日本株自動売買システム「KabuSys」の基本機能を追加。
  - パッケージ識別子とバージョン:
    - kabusys.__version__ = "0.1.0"
  - 設定 / 環境変数管理（kabusys.config）
    - .env ファイルおよび環境変数の自動読み込み機能（プロジェクトルートの .git または pyproject.toml を基準に探索）。
    - .env のパースは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントを考慮。
    - OS 環境変数を保護する protected モードを実装（.env.local は上書き可能だが、既存 OS 環境変数は保護）。
    - 自動ロードを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数対応。
    - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID）とデフォルト値（KABUSYS_ENV, LOG_LEVEL, KABU_API_BASE_URL, DB パス等）の提供。
    - env 値の妥当性チェック（KABUSYS_ENV, LOG_LEVEL）と便利なプロパティ（is_live / is_paper / is_dev）。
  - 戦略（strategy）モジュール
    - 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
      - 研究側（research）で計算された生ファクターを取得し、ユニバースフィルタ（株価 >= 300 円、20日平均売買代金 >= 5億円）を適用。
      - 指定カラムの Z スコア正規化（外れ値は ±3 にクリップ）を行い、features テーブルへ日付単位で冪等に UPSERT（トランザクション使用で原子性保証）。
      - prices_daily / raw_financials を参照して計算。
    - シグナル生成（kabusys.strategy.signal_generator）
      - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum / value / volatility / liquidity / news）を算出。
      - デフォルト重みの適用とユーザ指定 weights の検証・正規化（合計が 1 になるよう再スケール）。
      - Bear レジーム判定（AI の regime_score 平均が負の場合、かつサンプル数が閾値以上）により BUY シグナルを抑制。
      - BUY 閾値デフォルト 0.60、STOP-LOSS -8% を実装。
      - 保有ポジションのエグジット判定（ストップロス、スコア低下）と SELL シグナル生成。SELL は BUY より優先され BUY から除外。
      - signals テーブルへ日付単位で置換（トランザクション＋バルク挿入で冪等）。
  - 研究（research）モジュール
    - factor_research: Momentum / Volatility / Value ファクター計算（mom_1m/mom_3m/mom_6m, ma200_dev, atr_20/atr_pct, avg_turnover, volume_ratio, per, roe）。
    - feature_exploration:
      - 将来リターン calc_forward_returns（複数ホライズン対応、入力検証あり）。
      - スピアマン IC（calc_ic）とランク変換（rank：同順位は平均ランク、丸めによる ties 対策）。
      - factor_summary：count/mean/std/min/max/median を算出。
    - research パッケージは外部依存（pandas 等）を使わず DuckDB + 標準ライブラリで実装。
  - データ（data）関連（参照のみ。実装は data パッケージに依存）
    - zscore_normalize 等のユーティリティを使用。
  - バックテスト（backtest）フレームワーク
    - simulator: PortfolioSimulator（疑似約定、スリッページ/手数料モデル、BUY は配分に基づき株数算出、SELL は保有全量クローズ）、DailySnapshot / TradeRecord 型。
    - metrics: バックテスト評価指標（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, Total Trades）を計算。
    - engine: run_backtest を提供。
      - 本番 DB からインメモリ DuckDB へデータコピー（signals / positions を汚染せずに実行）。
      - 日次ループ：前日シグナルを始値で約定 → positions テーブルへ書き戻し → 終値で時価評価 → generate_signals で翌日シグナル生成 → ポジションサイジング → 次日約定、というフローを実装。
      - positions の書き戻し、signals 読取等の補助関数を含む。
  - 公開 API エクスポート
    - strategy: build_features, generate_signals
    - backtest: run_backtest, BacktestResult, DailySnapshot, TradeRecord, BacktestMetrics
    - research: calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank, zscore_normalize

Security
- 環境変数は OS の既存値を保護する実装になっており、.env にある秘密情報で OS 環境変数を誤って上書きしないよう配慮。

Notes / 実装上の設計判断
- ルックアヘッドバイアス回避のため、すべての計算は target_date 時点（または target_date 以前の最新データ）に基づいて実施。
- research / strategy / backtest の各モジュールは直接発注 API や実行層（execution）への依存を持たない設計（単体でテストしやすい）。
- データベース操作は日付単位で削除→挿入の置換を行い、トランザクションとバルク挿入で原子性と冪等性を担保。
- 多くの処理で欠損値 / 非有限値（NaN, Inf）を明示的に扱い、安全性を高めている。
- DuckDB を一次的なデータ処理に想定（インメモリコピー機能あり）。

Known limitations / 未実装の仕様（明記）
- signal_generator の SELL 判定に関連して、以下は未実装（コード内コメント参照）:
  - トレーリングストップ（peak_price に基づく -10% 等） — positions テーブルに peak_price / entry_date 等が必要。
  - 時間決済（保有 60 営業日超過） — 追加のメタデータが必要。
- calc_value: PBR / 配当利回り は現バージョンで未実装。
- 一部のテーブルコピー時に例外が発生した場合はコピーをスキップすることで堅牢化しているが、データ欠落に起因するテスト差異に注意。

Compatibility / Requirements
- 内部で DuckDB を利用（DuckDB Python パッケージが必要）。
- 環境変数に依存する設定があるため、.env.example を元に .env を用意することを推奨。
- ローカルでの自動 .env 読み込みはプロジェクトルートを基準に行われるため、パッケージ配布後でも挙動は安定する設計。

Breaking Changes
- 初回リリースのため破壊的変更なし。

---

この CHANGELOG はコードベースの注釈・コメントから推測して作成しています。追加のコミット履歴や実際の仕様書（StrategyModel.md, BacktestFramework.md 等）があれば、より正確に差分や設計経緯を記載できます。必要であればそれらを反映した改訂版を作成します。