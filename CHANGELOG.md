# Changelog

すべての注目すべき変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。

## [Unreleased]


## [0.1.0] - 2026-03-22

初回リリース。日本株自動売買システム「KabuSys」のコア機能を実装しました。以下はコードベースから推測してまとめた主要な追加点・設計上の挙動です。

### Added
- パッケージ初期化
  - src/kabusys/__init__.py によりパッケージ名・バージョン管理を提供（__version__ = 0.1.0）。
  - 公開モジュール: data, strategy, execution, monitoring を __all__ に登録。

- 環境設定管理
  - src/kabusys/config.py
    - .env ファイルおよび環境変数を読み込む Settings クラスを提供。
    - プロジェクトルート検出機能: .git または pyproject.toml を起点にパスを探索し自動で .env/.env.local を読み込む（KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化可）。
    - .env パーサは export KEY=val 形式、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメント処理をサポート。
    - 読み込み時に OS 環境変数を保護する protected 機構を実装（.env.local は override=True）。
    - 必須環境変数取得時に未設定なら ValueError を送出。
    - KABUSYS_ENV（development / paper_trading / live）と LOG_LEVEL（DEBUG/INFO/...）の値検証、ユーティリティプロパティ（is_live / is_paper / is_dev）を実装。
    - DB パス（DUCKDB_PATH / SQLITE_PATH）、各種 API トークン（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / SLACK_*）の取得用プロパティを提供。

- ファクター計算（Research）
  - src/kabusys/research/factor_research.py
    - Momentum: mom_1m / mom_3m / mom_6m / ma200_dev を prices_daily から計算（必要行数/ウィンドウを考慮）。
    - Volatility: 20日 ATR（true range の NULL 伝播制御）、相対 ATR（atr_pct）、20日平均売買代金、volume_ratio を計算。
    - Value: raw_financials から最新の財務を取得して PER / ROE を算出（EPS が 0／欠損の場合は None）。
    - 各関数は DuckDB 接続を受け取り SQL で効率的に集計。データ不足時は None を返す設計。

  - src/kabusys/research/feature_exploration.py
    - 将来リターン calc_forward_returns を実装（horizons のバリデーション、SQL による LEAD を活用、カレンダーバッファを使用）。
    - ランク相関（Spearman）を計算する calc_ic（ペア数が少ない・分散がゼロのケースは None を返す）。
    - rank ユーティリティは同順位（ties）を平均ランクで扱い、丸め（round(v,12)）で浮動小数点の ties 検出漏れに対処。
    - factor_summary で count/mean/std/min/max/median を計算（None を除外）。

  - src/kabusys/research/__init__.py で上記 API を公開。

- 特徴量エンジニアリング（Production 戦略用）
  - src/kabusys/strategy/feature_engineering.py
    - research の生ファクターを統合し、ユニバースフィルタ（最低株価 300 円、20日平均売買代金 >= 5 億円）を適用。
    - 正規化（zscore_normalize を利用）、Z スコアを ±3 でクリップして外れ値影響を抑制。
    - DuckDB の features テーブルへ日付単位で置換（DELETE + INSERT）しトランザクションで原子性を保持。ROLLBACK に失敗した場合は警告ログを出力。

- シグナル生成
  - src/kabusys/strategy/signal_generator.py
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum / value / volatility / liquidity / news）を算出。
    - スコア変換: Z スコアを sigmoid で [0,1] に変換。欠損コンポーネントは中立値 0.5 で補完。
    - デフォルト重み（momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）を提供。ユーザ重みは検証・正規化（非数値・負値は無視、合計で再スケール）。
    - Bear レジーム判定: ai_scores の regime_score 平均が負かつ十分なサンプル数（デフォルト 3）で BUY を抑制。
    - BUY 生成: threshold（デフォルト 0.60）を上回る銘柄をランク付けして BUY。
    - SELL 生成: positions / latest price を参照してストップロス（終値ベース -8% 以下）およびスコア低下でエグジット判定。features に存在しない保有銘柄は final_score=0 として扱う（警告ログ）。
    - signals テーブルへの書き込みは日付単位の置換をトランザクションで実施。

- バックテストフレームワーク
  - src/kabusys/backtest/simulator.py
    - PortfolioSimulator を実装（メモリ内の cash / positions / cost_basis / history / trades 管理）。
    - execute_orders: SELL を先に処理（保有全量をクローズ）、BUY は alloc を基に当日始値で約定。スリッページ・手数料モデルを適用し、手数料込みで買付可能株数を再計算する安全処理を実装。
    - mark_to_market: 終値で時価評価。終値欠損時は 0 で評価して警告ログ。

  - src/kabusys/backtest/metrics.py
    - バックテスト評価指標（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, Total Trades）を計算するユーティリティを提供。データ不足時のフォールバック（0.0 など）を安全に処理。

  - src/kabusys/backtest/engine.py
    - run_backtest を実装。実稼働用の DuckDB からインメモリ DuckDB に必要テーブルをコピーしてバックテストを実行（signals/positions など本番テーブルを汚染しない）。
    - _build_backtest_conn: 日付フィルタ付きのテーブルコピー（prices_daily, features, ai_scores, market_regime）と market_calendar のコピー処理。コピー失敗時は警告ログを出す。
    - 日次ループは (1) 前日シグナルを当日始値で約定 → (2) positions を DB に書き戻し → (3) 終値で時価評価 → (4) generate_signals（当日）→ (5) signals から買い割当てを決定 の流れを実装。
    - DuckDB 接続を分離してバックテスト用に初期化（init_schema(":memory:") を想定）。

- モジュール公開整理
  - src/kabusys/strategy/__init__.py で build_features, generate_signals を公開。
  - src/kabusys/backtest/__init__.py で run_backtest, BacktestResult, DailySnapshot, TradeRecord, BacktestMetrics を公開。
  - src/kabusys/research/__init__.py で主要研究用 API を公開。

### Behavior / Implementation notes
- DB 書き込みは可能な限り日付単位の置換（DELETE + INSERT）をトランザクションで行い、原子性を担保する設計（rollback 障害時は警告ログ）。
- Research / Strategy 層は発注 API に依存しない純粋な計算ロジックに留め、実取引依存を分離している（安全なテスト・バックテストが可能）。
- 欠損値・数値の非有限値に対して頑健な実装（None/NaN/Inf を扱うロジック、平均化での補完、サンプル不足時の None 返却やフォールバック値の適用）。
- ロギングにより重要な異常（価格欠損、.env 読み込み失敗、ROLLBACK 失敗、無効な重み定義など）を通知。

### Known / Intentional limitations（実装上の注記）
- signal_generator のエグジット条件はストップロス・スコア低下を実装するが、トレーリングストップや時間決済（保有日数判定）は未実装で、positions テーブルに peak_price / entry_date が必要と注記されている。
- 一部の機能はデータ前提（prices_daily, raw_financials, features, ai_scores 等）の存在に依存する。バックテストは start_date より前に必要データをコピーするため、元データの期間が短いと影響を受ける可能性がある。
- execution モジュールは初期化のみ（パッケージ存在）で実装ファイルは提供されていない（将来的な発注層実装想定）。

### Security
- 環境変数の取り扱いは慎重に設計されている（OS 環境の保護、.env.local の override 方針）。ただし本コード内でのトークン管理は環境変数依存のため、実運用時は適切なシークレット管理の運用を推奨。

---

（注）本CHANGELOG は提示されたソースコードからの推測に基づいて作成しています。ドキュメントやリリースノートと異なる場合があります。