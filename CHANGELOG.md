# Changelog

すべての重要な変更点を記録します。本ファイルは Keep a Changelog の書式に準拠します。

## [0.1.0] - 2026-03-22

初回公開リリース。本リリースでは日本株向けの自動売買フレームワークの基礎機能を実装しました。主な追加点は以下のとおりです。

### Added
- パッケージ基盤
  - パッケージのエントリポイントを定義（kabusys.__init__）。公開 API として data / strategy / execution / monitoring をエクスポート。
  - バージョン番号を `__version__ = "0.1.0"` として設定。

- 環境設定（kabusys.config）
  - .env / .env.local を自動で読み込む仕組みを実装（プロジェクトルートは .git または pyproject.toml を探索して決定）。
  - .env のパース機能を実装：
    - コメント行、export プレフィックス、シングル/ダブルクォート、バックスラッシュによるエスケープ、インラインコメントの扱いを考慮。
  - 自動ロードの無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）をサポート。
  - OS 環境変数を保護するための上書き制御（.env.local は上書き、.env は既存値を変更しない）。
  - Settings クラスを提供し、必須値の取得（_require）や値検証（KABUSYS_ENV, LOG_LEVEL の妥当性チェック）などを行うプロパティを実装。
  - J-Quants / kabu ステーション / Slack / DB パス等の設定プロパティを定義。

- 戦略（kabusys.strategy）
  - 特徴量生成（feature_engineering.build_features）
    - 研究環境で計算された生ファクターを統合・正規化して `features` テーブルへ UPSERT（対象日の置換）する処理を実装。
    - ユニバースフィルタ（最低株価、20日平均売買代金）を実装。
    - Z スコア正規化（zscore_normalize を利用）と ±3 でのクリップ処理を実装。
    - 冪等性（トランザクション + 日付単位の DELETE→INSERT）を担保。
  - シグナル生成（signal_generator.generate_signals）
    - 正規化済みファクターと ai_scores を統合して final_score を算出。
    - momentum / value / volatility / liquidity / news の重み付けと、ユーザ指定重みの検証・統合（合計が 1.0 になるようリスケール）を実装。
    - Bear レジーム判定（AI の regime_score を集計）により BUY シグナルを抑制。
    - BUY（閾値超過）および SELL（ストップロス、スコア低下）シグナルの生成。
    - positions テーブルの読み取りに基づくエグジット判定、SELL 優先ポリシー（SELL が BUY を除外）を実装。
    - signals テーブルへの日付単位置換（トランザクション）で冪等性を保証。
    - 欠損値（None / NaN / Inf）やデータ不足を許容するフォールバックロジックを実装（例：AI スコア未登録時の中立補完、features 未登録保有銘柄を score=0 と見なす等）。

- リサーチ（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離を計算。
    - calc_volatility: ATR（20日）、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算。
    - calc_value: 最新財務データ（raw_financials）と株価を組み合わせて PER / ROE を計算。
    - 各関数は prices_daily / raw_financials のみ参照し、ルックアヘッドを防ぐ設計。
  - 特徴量探索（feature_exploration）
    - calc_forward_returns: 指定日の終値から指定ホライズン先までの将来リターンを計算（複数ホライズン対応、ホライズン検証有り）。
    - calc_ic: Spearman ランク相関（Information Coefficient）を実装（ペア不足時の None ハンドリング）。
    - factor_summary: 複数ファクター列の基本統計量（count/mean/std/min/max/median）を算出。
    - rank: 同順位は平均ランクにするランク関数（丸めで ties 検出の安定化）。
    - 研究モジュールは外部依存（pandas 等）を持たない純粋 Python + DuckDB 実装。

- バックテスト（kabusys.backtest）
  - シミュレーション（backtest.simulator）
    - PortfolioSimulator を実装（メモリ内でポジション / コスト基準管理）。
    - BUY/SELL の擬似約定ロジック（始値、スリッページ、手数料考慮）、SELL は全量クローズ、BUY は資金不足時の再計算を実装。
    - mark_to_market: 終値での時価評価と DailySnapshot 記録（終値欠損時の WARNING）。
    - TradeRecord / DailySnapshot のデータモデルを定義。
  - メトリクス（backtest.metrics）
    - calc_metrics: history/trades から BacktestMetrics（CAGR, Sharpe, MaxDrawdown, WinRate, PayoffRatio, TotalTrades）を算出。
    - 各指標の内部計算（年率化、分散計算、Edge case の処理）を実装。
  - エンジン（backtest.engine）
    - run_backtest: 本番 DuckDB からインメモリ DuckDB に必要データをコピーして日次シミュレーションを実行するトップレベル関数を実装。
    - _build_backtest_conn: 日付範囲でテーブルをフィルタしてインメモリ DB にコピー（market_calendar は全件コピー）。
    - シミュレーションループ: 前日シグナル約定 → positions 書戻し → 時価評価 → generate_signals 呼び出し → 発注リスト作成 の流れを実装。
    - 取引サイズ算出（max_position_pct ベースの配分）を実装。
    - run_backtest は generate_signals / PortfolioSimulator / calc_metrics を組み合わせて BacktestResult を返す。

- その他・内部実装
  - 各所でログ出力（logging）を充実させ、データ欠損や不整合時に WARNING/INFO/DEBUG を出すことでデバッグ性を向上。
  - SQL クエリは対象日以前の最新値参照などを意識してルックアヘッドを排除する設計。
  - DB 書き込み処理はトランザクション（BEGIN/COMMIT/ROLLBACK）で原子性を確保し、ROLLBACK 失敗時の警告ログを追加。

### Changed
- （初版のため該当なし）

### Fixed
- 多数の関数で欠損データ・NaN/Inf を安全に扱うように実装（価格欠損時のシグナル判定スキップや警告出力など）。

### Known limitations / Notes
- トレーリングストップや時間決済など、Engine/Strategy の一部仕様（StrategyModel の Section 5 内のいくつか）は未実装（ソース内に TODO コメントあり）。
- 一部の機能は kabusys.data.stats や kabusys.data.schema 等の別モジュールに依存する（本リリースではそれらが存在することを前提）。
- .env パースは一般的なケースを想定しているが、特殊な形式の .env では期待通りに動作しない可能性あり。

## Unreleased
- 今後の予定: トレーリングストップ実装、部分利確のサポート、より詳細なポジションサイジング戦略、テストカバレッジ拡充、およびドキュメント整備。

---

本 CHANGELOG はソースの docstring と実装内容から推測して記載しています。詳細な使用方法や API 仕様は各モジュールの docstring とプロジェクトの設計文書（StrategyModel.md / BacktestFramework.md 等）を参照してください。