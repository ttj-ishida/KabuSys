# CHANGELOG

すべての変更は Keep a Changelog のフォーマットに準拠します。

## [Unreleased]

### Added
- パッケージ初期構成（kabusys）を追加。主要サブパッケージ: data, strategy, execution, monitoring を公開。
- バージョン情報を src/kabusys/__init__.py にて管理（__version__ = "0.1.0"）。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

---

## [0.1.0] - 2026-03-22

初回公開リリース。日本株自動売買システムのコアロジック（研究・特徴量生成・シグナル生成・バックテスト）を含む。

### Added

- 設定・環境変数管理
  - src/kabusys/config.py を追加。
  - .env/.env.local 自動ロード機構を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。CWD に依存しない実装。
  - .env パーサを実装: コメント行、export KEY=val 形式、シングル/ダブルクォートとバックスラッシュエスケープ、インラインコメント処理に対応。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト用途）。
  - OS 環境変数保護（.env 上書きを protected set で制限）。
  - Settings クラスを提供し、環境変数の取得・バリデーションを集中管理:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID を必須としてチェック（未設定時は ValueError を送出）。
    - KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH のデフォルト値を提供。
    - KABUSYS_ENV（development / paper_trading / live）と LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）のバリデーション。
    - is_live / is_paper / is_dev のユーティリティプロパティ。

- 研究（research）モジュール
  - src/kabusys/research/factor_research.py
    - Momentum（mom_1m, mom_3m, mom_6m, ma200_dev）計算。
    - Volatility（atr_20, atr_pct, avg_turnover, volume_ratio）計算（true range の NULL 伝播を考慮）。
    - Value（per, roe）計算（raw_financials から target_date 以前の最新レコードを取得）。
    - DuckDB を用いた SQL + Python のハイブリッド実装で、prices_daily / raw_financials のみを参照。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン calc_forward_returns（複数ホライズンに対応、引数バリデーションあり）。
    - スピアマンの IC を計算する calc_ic（ランク変換、同順位は平均ランク）。
    - factor_summary（count/mean/std/min/max/median の計算）。
    - rank ユーティリティ（同率は平均ランク、丸め誤差対策あり）。
  - research パッケージの __all__ を整備し、主要関数を公開。

- 特徴量エンジニアリング（strategy）
  - src/kabusys/strategy/feature_engineering.py
    - 研究環境で計算した raw factors を統合し、正規化（Z スコア）・合成して features テーブルへ保存する処理を実装。
    - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）を実装。
    - Z スコア対象列の正規化と ±3 でのクリップ処理を実装。
    - DuckDB 上で日付単位の置換（DELETE → INSERT）をトランザクションで実行し、冪等性と原子性を保証。
    - 依存は発注 API / execution 層に持たない設計。

- シグナル生成（strategy）
  - src/kabusys/strategy/signal_generator.py
    - features と ai_scores（AI ニュース／レジームスコア）を統合して final_score を算出。
    - コンポーネントスコア計算:
      - momentum: momentum_20 / momentum_60 / ma200_dev（シグモイド + 平均）
      - value: PER に基づく逆相関スコア（PER=20 → 0.5 を基準）
      - volatility: atr_pct の Z スコアを反転してシグモイド
      - liquidity: 出来高比率のシグモイド
      - news: ai_score のシグモイド（未登録は中立）
    - 重み合成: デフォルトウェイトを用意（momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）。ユーザー指定 weights は検証・補正・再スケールされる（未知キーや負値・非数値は無視）。
    - Bear レジーム判定: ai_scores の regime_score の平均が負の場合に Bear とみなす（ただしサンプル数が不足する場合は Bear 判定を行わない）。
    - BUY シグナル生成: final_score が閾値（デフォルト 0.60）を超える銘柄をスコア降順で選出。Bear レジーム時は BUY を抑制。
    - SELL（エグジット）判定: positions / prices を参照してストップロス（終値ベースで -8% 以下）と final_score の閾値割れで判定。SELL を優先して処理（SELL 対象は BUY から除外）。
    - signals テーブルへの日付単位置換（トランザクション）で冪等性を保証。
    - ロギングによる欠損値/警告メッセージを実装（価格欠損時の判定スキップ、features 未登録保有銘柄の扱い等）。

- バックテストフレームワーク
  - src/kabusys/backtest/simulator.py
    - PortfolioSimulator 実装（メモリ内で cash / positions / cost_basis / history / trades を管理）。
    - BUY/SELL の簡易約定ロジック（始値ベース、スリッページ・手数料を反映）。
    - SELL は保有全量クローズ（部分利確/部分損切り、トレーリング非対応）。
    - mark_to_market による日次スナップショット記録（終値欠損時は 0 で評価し警告）。
    - TradeRecord / DailySnapshot dataclass 定義。
  - src/kabusys/backtest/metrics.py
    - バックテスト評価指標計算: CAGR, Sharpe Ratio, Max Drawdown, Win Rate, Payoff Ratio, total_trades。
    - 数学的エッジケースをハンドリング（データ不足やゼロ割回避）。
  - src/kabusys/backtest/engine.py
    - run_backtest API を実装:
      - 本番接続から必要データ（prices_daily, features, ai_scores, market_regime, market_calendar）をコピーしてインメモリ DuckDB を構築（init_schema を用いた初期化）。
      - 日次ループ: 前日シグナルの約定 → positions 書き戻し → 終値評価 → generate_signals 呼び出し → 発注リスト作成（ポジションサイジング）→ 次日へループ。
      - get_trading_days を用いた営業日リスト取得。
      - slippage_rate / commission_rate / max_position_pct 等のパラメータをサポート。
    - DB コピー処理はテーブルごとに例外を捕捉し、失敗したテーブルはスキップして警告を残す（堅牢性向上）。
    - positions テーブルへの書き戻しは冪等（DELETE + INSERT）。

- パッケージ公開 API を整理
  - strategy.__init__ で build_features / generate_signals を公開。
  - backtest.__init__ で run_backtest, BacktestResult, DailySnapshot, TradeRecord, BacktestMetrics を公開。
  - research.__init__ で研究用ユーティリティを公開。

### Notes / Known issues / TODO
- signal_generator のエグジット条件で「トレーリングストップ（直近最高値から -10%）」や「時間決済（保有 60 営業日超過）」は未実装。positions テーブルに peak_price / entry_date が必要となるため将来的な拡張予定。
- PortfolioSimulator の SELL は全量クローズのみ。部分利確/部分損切りが必要な場合はシミュレータ拡張が必要。
- calc_forward_returns は horizon の妥当性チェック（<=252 営業日）を行う。データ不足により None が返るケースがある。
- DuckDB スキーマ初期化（init_schema）、data.schema 等は別モジュールに依存。実運用前にスキーマ定義とデータ投入が必要。
- .env パーサは一般的なシェル形式に沿うが、全ての edge-case をカバーしているわけではない。必要に応じて拡張可能。
- ログ出力や警告は実装済みだが、運用向けにより詳細な監視/アラート統合（Slack 通知等）を今後追加予定。

### Security
- 環境変数（API トークン等）は Settings 経由で必須チェックを行う。機密情報は .env/.env.local の管理と OS 環境変数の併用を想定。

---

作成者注:
- 実装内のコメント（StrategyModel.md, BacktestFramework.md 等）に設計仕様の参照が複数存在します。実運用・研究用にそれらのドキュメントを併せて参照してください。
- 本 CHANGELOG はソースコードのコメントと実装から推測してまとめた初期リリースノートです。リリース時の最終確認で日付・機能記述の微調整を推奨します。