# CHANGELOG

すべての注目すべき変更をここに記録します。本ファイルは「Keep a Changelog」形式に準拠しています。  
※以下の内容は提示されたコードベースの実装内容から推測して作成した初回リリース向けの変更履歴です。

## [0.1.0] - 2026-03-22

### Added
- パッケージ基盤
  - パッケージ名: kabusys、トップレベルで data / strategy / execution / monitoring を公開。
  - バージョン定義: src/kabusys/__init__.py に __version__ = "0.1.0" を追加。

- 環境設定 / ロード機能（src/kabusys/config.py）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を探索して検出）から自動読み込みする仕組みを追加。
  - ロード順序: OS 環境 > .env.local > .env。既存 OS 環境を保護する protected 機構を実装。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト等で自動ロードを抑止可能）。
  - .env パーサーを実装:
    - export KEY=val 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いに対応。
    - 無効行の無視、キー未定義時のスキップ等のロバストな処理。
  - Settings クラスを追加し、環境変数からアプリケーション設定をプロパティ経由で取得:
    - J-Quants / kabu API / Slack / DB パス（duckdb/sqlite） / ログレベル / 環境（development/paper_trading/live） 等。
    - 必須キー未設定時は ValueError を送出する _require() を提供。
    - env / log_level に対する検証を実装（許容値を限定）。

- 戦略（strategy）
  - 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
    - research で計算した raw factor（calc_momentum / calc_volatility / calc_value）を統合して features テーブルへ保存する build_features(conn, target_date) を実装。
    - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 >= 5 億円）を適用。
    - 指定列を Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）、±3 でクリップ。
    - 日付単位で既存データを削除してから挿入することで冪等性とトランザクショナルな置換を保証（BEGIN/COMMIT/ROLLBACK 処理）。
  - シグナル生成（src/kabusys/strategy/signal_generator.py）
    - features と ai_scores を統合して最終スコア final_score を算出し、BUY/SELL シグナルを生成する generate_signals(conn, target_date, threshold, weights) を実装。
    - コンポーネントスコア: momentum / value / volatility / liquidity / news（AI スコア）。
    - デフォルト重みを定義し、ユーザー指定 weights を受け付けつつ妥当性チェック・再スケーリングを行う。
    - Sigmoid 変換、欠損コンポーネントは中立値 0.5 で補完。
    - Bear レジーム判定（ai_scores の regime_score 平均が負の場合、サンプル数閾値あり）で BUY シグナル抑制。
    - SELL 条件としてストップロス（終値ベース -8%）とスコア低下を実装。
    - signals テーブルへ日付単位で置換挿入（冪等性・トランザクション対応）。
    - 各公開 API を strategy.__init__ でエクスポート（build_features, generate_signals）。

- リサーチ（research）
  - ファクター計算モジュール（src/kabusys/research/factor_research.py）
    - calc_momentum / calc_volatility / calc_value を実装。prices_daily / raw_financials テーブルのみ参照。
    - 各ファクター（1M/3M/6M リターン、MA200 乖離、ATR20、avg_turnover、volume_ratio、per, roe 等）を SQL + Python により計算。
    - データ不足時の None ハンドリングやウィンドウサイズ検査を実装。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns(conn, target_date, horizons) により複数ホライズンの将来リターンを LEAD ウィンドウで取得。
    - calc_ic(factor_records, forward_records, factor_col, return_col) による Spearman の ρ（ランク相関）計算を実装（同順位は平均ランク処理）。
    - factor_summary(records, columns) により count / mean / std / min / max / median を算出。
    - rank(values) 実装で同順位（ties）を平均ランクとする処理を追加。
  - research パッケージで代表的関数を __all__ にて公開。

- バックテストフレームワーク（src/kabusys/backtest）
  - ポートフォリオシミュレータ（src/kabusys/backtest/simulator.py）
    - PortfolioSimulator クラスを実装（cash, positions, cost_basis, history, trades 管理）。
    - execute_orders: SELL を先行して約定し、BUY を後で約定（SELL は保有全量クローズ、部分利確非対応）。
    - スリッページ・手数料モデル（入出金・commission 計算）、株数切り捨て、手数料込みでの再計算処理を実装。
    - mark_to_market により終値で時価評価し DailySnapshot を記録。終値欠損時は 0 評価で警告ログを出力。
    - TradeRecord / DailySnapshot dataclass を提供。
  - バックテストエンジン（src/kabusys/backtest/engine.py）
    - run_backtest(conn, start_date, end_date, ...) を実装。運用 DB からインメモリ DuckDB へデータをコピーして日次シミュレーションを実行。
    - _build_backtest_conn で date 範囲でテーブルをコピー（prices_daily, features, ai_scores, market_regime など）、market_calendar は全件コピー。
    - 日次ループ: 前日シグナル約定 → positions 書き戻し → 時価評価記録 → generate_signals 呼出し → 発注リスト作成（ポジションサイジング）という流れを実装。
    - positions テーブルとの整合性を保つための書き戻し関数 _write_positions を提供。
  - メトリクス（src/kabusys/backtest/metrics.py）
    - calc_metrics(history, trades) により BacktestMetrics（cagr, sharpe_ratio, max_drawdown, win_rate, payoff_ratio, total_trades）を算出。
    - 小サンプル時の安全なデフォールト値（0.0 等）やゼロ分散ハンドリング等を実装。
  - backtest パッケージで run_backtest / BacktestResult / DailySnapshot / TradeRecord / BacktestMetrics を公開。

- DB 操作の堅牢性
  - features / signals / positions への書き込みは削除→挿入の置換方式で日付単位の冪等性を確保。
  - トランザクション（BEGIN/COMMIT/ROLLBACK）を利用し、エラー時にロールバックを試行。ロールバック失敗時に警告ログを出力。

- ロギング・入力検証・数値安全性
  - math.isfinite チェックや None ハンドリング、無効パラメータをスキップするロギックを広範に導入。
  - 重み・ホライズン等の引数検証、無効値に対するフォールバックが実装されている。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- 環境変数の自動ロード時に OS 環境変数を保護する protected キーセットを導入（.env が OS 環境を上書きしない）。

---

## Notes / Known issues / TODO（コード内コメントより推測）
- _generate_sell_signals 内で言及されているトレーリングストップや時間決済（保有 60 営業日超過）は未実装。これらを実装するには positions テーブルに peak_price / entry_date 等のフィールドが必要。
- 一部の処理は DuckDB に依存した SQL 実装を前提としており、DB スキーマ（テーブル・カラム名）が存在しないと動作しない。
- research モジュールは pandas など外部ライブラリに依存しない実装方針のため、大量データを扱う場合のメモリ/性能は運用で確認が必要。
- .env の自動読み込みはプロジェクトルート検出に依存するため、配布環境やインストール先での動作はワークフローに応じた検証を推奨。

---

開発・運用者向け補足:
- 自動ロードを無効化したいテストや CI では環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 各公開 API（build_features / generate_signals / run_backtest など）は DuckDB 接続と日付を引数に取り、外部発注・実口座とは直接依存しない設計です。