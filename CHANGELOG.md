# Changelog

すべての変更は「Keep a Changelog」準拠で記載しています。フォーマットは Markdown (CHANGELOG.md) です。

## [Unreleased]

（現時点では未リリースの変更はありません）

## [0.1.0] - 2026-03-22

初回リリース。日本株向け自動売買システムのコアライブラリを提供します。以下の主要コンポーネントと機能を含みます。

### Added（追加）
- パッケージ初期化
  - pakage metadata: `kabusys.__version__ = "0.1.0"`、主要サブパッケージを `__all__` に公開。

- 環境設定管理 (`kabusys.config`)
  - .env ファイルおよび環境変数の読み込み機能を実装。
  - プロジェクトルート検出ロジック（.git または pyproject.toml を起点）により、CWD に依存しない自動ロードを実現。
  - 自動ロードの無効化オプション `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート（テスト用途）。
  - `.env` と `.env.local` の読み込み優先度制御（OS 環境変数を保護する protected 機構）。
  - 複雑な .env パース機能を実装（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱い）。
  - 必須変数取得ヘルパ `_require()`（未設定時は ValueError）。
  - 設定アクセス用の `Settings` クラスを提供（J-Quants / kabuAPI / Slack / DB パス / 実行環境 / ログレベル等）。
  - `KABUSYS_ENV` と `LOG_LEVEL` の値検証（許容値チェック）。

- 戦略（Strategy）モジュール
  - 特徴量エンジニアリング (`kabusys.strategy.feature_engineering`)
    - 研究環境で生成された生ファクターを結合・正規化して `features` テーブルへ保存する `build_features()` を実装。
    - フロー：research の `calc_momentum` / `calc_volatility` / `calc_value` を呼び、ユニバースフィルタを適用、Zスコア正規化、±3 でクリップ、日付単位の置換（トランザクション）で DB に UPSERT。
    - ユニバースフィルタ：最低株価（300円）・20日平均売買代金（5億円）を適用。
    - DuckDB を使用した SQL ベース処理とトランザクションによる原子性確保、失敗時のロールバック対応。

  - シグナル生成 (`kabusys.strategy.signal_generator`)
    - `features` と `ai_scores` を統合し、複数コンポーネント（momentum, value, volatility, liquidity, news）から最終スコア（final_score）を計算して売買シグナルを生成する `generate_signals()` を実装。
    - AI スコアの補完（未登録は中立）とレジーム判定（複数サンプルの regime_score 平均が負なら Bear と判定して BUY を抑制）。
    - スコア計算におけるシグモイド・平均化・欠損補完ロジックを実装。
    - 重みのマージ/正規化（デフォルト重みはドキュメント準拠）、無効な重み入力の警告・スキップ。
    - SELL エグジット条件の判定機能（ストップロス -8%、final_score が閾値未満でのクローズ）。
    - シグナル（BUY/SELL）を `signals` テーブルへ日付単位で置換（トランザクション）し、ロールバック対処を実装。

- 研究（Research）モジュール
  - ファクター計算 (`kabusys.research.factor_research`)
    - Momentum（mom_1m, mom_3m, mom_6m, ma200_dev）計算の `calc_momentum()`。
    - Volatility／Liquidity（atr_20, atr_pct, avg_turnover, volume_ratio）計算の `calc_volatility()`。
    - Value（per, roe）計算の `calc_value()`。raw_financials の最新レコード取得ロジックを実装。
    - DuckDB 上で SQL とウィンドウ関数を駆使した効率的な実装。欠損時の None 処理を明確化。

  - 特徴量探索ツール (`kabusys.research.feature_exploration`)
    - 将来リターン計算 `calc_forward_returns()`（複数ホライズン、範囲バッファによる効率化）。
    - IC（Information Coefficient）計算 `calc_ic()`（Spearman の ρ をランク計算で算出、サンプル不足時は None）。
    - 基本統計サマリ `factor_summary()` とランク変換ユーティリティ `rank()`。
    - 外部依存（pandas 等）を避け、標準ライブラリで完結する設計。

- バックテスト（Backtest）フレームワーク
  - シミュレータ (`kabusys.backtest.simulator`)
    - `PortfolioSimulator`：メモリ内ポートフォリオ管理、擬似約定ロジック（SELL を先に処理、BUY は資金に応じて株数を計算）。
    - スリッページと手数料を反映した約定価格・手数料計算、平均取得単価の更新、売却時の realized_pnl 計算。
    - 日次評価（mark_to_market）で `DailySnapshot` を記録。価格欠損時は 0 評価で警告ログ。

  - エンジン (`kabusys.backtest.engine`)
    - `run_backtest()`：本番 DB から要データをインメモリ DuckDB にコピーし、日次ループでシミュレーションを実行する高レベル API。
    - データコピー `_build_backtest_conn()`：日付フィルタ付きテーブルコピー（prices_daily, features, ai_scores, market_regime 等）と market_calendar の全件コピー。コピー失敗は警告でスキップ。
    - 日次の価格取得ヘルパ、positions の DB 書き戻し（`_write_positions`）など運用に必要なユーティリティを提供。
    - シグナル生成を組み込み（`generate_signals` 呼び出し）し、ポジションサイジング→約定→評価→次シグナルの流れを実現。

  - メトリクス (`kabusys.backtest.metrics`)
    - バックテスト評価指標を集約する `BacktestMetrics` を定義（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, Total Trades）。
    - 各指標算出ロジック（CAGR、シャープレシオ、最大ドローダウン、勝率、ペイオフ比）を実装。

- 共通設計/運用面
  - DuckDB を中心とした SQL ベースのデータ処理。
  - ルックアヘッドバイアス防止のため、すべての主要処理は target_date 時点のデータのみ参照する方針。
  - トランザクション + バルク挿入による日付単位の置換で冪等性と原子性を担保。
  - ロギングにより警告・情報・デバッグを出力（エラーハンドリングでロールバック失敗時は警告を出す）。

### Changed（変更）
- 初回リリースのため該当なし。

### Fixed（修正）
- 初回リリースのため該当なし。

### Removed（削除）
- 初回リリースのため該当なし。

### Known issues / 未実装の機能（注意点）
- シグナル生成における一部エグジット条件が未実装であることをコード内で明記：
  - トレーリングストップ（peak_price が positions テーブルに必要）未実装。
  - 時間決済（保有 60 営業日超）未実装。
- `kabusys.data.stats.zscore_normalize` など一部ユーティリティは参照されているが、このリリースのコード断片内での実装場所に注意が必要（data パッケージの他ファイルで提供されている想定）。
- DuckDB のスキーマ初期化関数 `init_schema` は `kabusys.data.schema` に依存。外部 DB スキーマとの整合性に注意。
- 実行環境（実際の kabu API / Slack 通知等）への接続コードは本リリースの研究/シミュレーション層とは分離されている（実運用時の追加実装が必要）。

---

メンテナンスや次バージョンでの予定（非公式）
- SELL 条件の追加（トレーリングストップ、時間決済）の実装。
- ポジションサイジングやリスク管理の拡張（複合的な配分ルール）。
- 単体テスト・統合テストの整備と CI パイプラインの追加。
- ドキュメント（StrategyModel.md, BacktestFramework.md 等）の公開とサンプルデータセットの提供。

（以上）