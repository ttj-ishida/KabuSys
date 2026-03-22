# Changelog

すべての変更は「Keep a Changelog」形式に準拠し、セマンティックバージョニングを使用します。  
初回リリース 0.1.0 を含む内容をコードベースから推測して記載しています。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-22
初回公開リリース。日本株自動売買システム「KabuSys」ベース機能を実装。

### Added
- パッケージ基礎
  - src/kabusys/__init__.py: パッケージ定義とバージョン (0.1.0) を追加。
  - __all__ に主要サブパッケージ（data, strategy, execution, monitoring）を宣言。

- 環境・設定管理
  - src/kabusys/config.py: 環境変数読み込み／設定管理モジュールを実装。
    - .env / .env.local の自動読み込み（プロジェクトルートを .git / pyproject.toml から探索）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化。
    - export 形式・クォート・インラインコメント等に対応した .env パーサー実装。
    - OS 環境変数保護（.env.local の上書き時に OS 環境を保護）。
    - settings オブジェクト: J-Quants / kabu API / Slack / DB パス（duckdb/sqlite）/実行環境（development/paper_trading/live）/ログレベル等の取得およびバリデーション。

- 戦略（feature engineering / signal generation）
  - src/kabusys/strategy/feature_engineering.py: features テーブル作成処理を実装。
    - research 側の生ファクター（momentum/volatility/value）からマージ・ユニバースフィルタ適用（株価 >= 300 円、20 日平均売買代金 >= 5 億円）。
    - Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）、±3 でクリップ、日付単位で冪等的に UPSERT（DELETE + INSERT、トランザクション）。
  - src/kabusys/strategy/signal_generator.py: シグナル生成ロジックを実装。
    - features と ai_scores を統合して複数コンポーネント（momentum / value / volatility / liquidity / news）から final_score を計算。
    - デフォルト重みとしきい値を実装（デフォルト weights、BUY 閾値 0.60）。
    - AI レジームスコアに基づく Bear レジーム判定（サンプル数閾値あり）で BUY を抑制。
    - エグジット条件（ストップロス -8% / スコア低下）を実装し SELL シグナルを生成。
    - signals テーブルへ日付単位での置換（トランザクション）を保証。
    - 重みの入力検査（未知キー・非数値・負値・NaN/Inf を無視）と合計再スケーリング。

- 研究（research）
  - src/kabusys/research/factor_research.py: ファクター計算の実装。
    - calc_momentum: mom_1m/mom_3m/mom_6m、200 日移動平均乖離（ma200_dev）を計算。
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から最新財務（eps, roe）を取得し PER / ROE を計算（EPS=0/欠損は None）。
    - SQL + DuckDB ウィンドウ関数により営業日ベースのラグ/移動平均を計算。
  - src/kabusys/research/feature_exploration.py: 特徴量探索ユーティリティを追加。
    - calc_forward_returns: 将来リターン（デフォルト [1,5,21]）を一括取得。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）計算（有効レコード >=3 を要件）。
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）を計算。
    - rank: 同順位の平均ランク処理を伴うランク変換（丸め処理で tie 検出の安定化）。
  - src/kabusys/research/__init__.py: 研究用 API をエクスポート。

- バックテスト（backtest）
  - src/kabusys/backtest/simulator.py:
    - PortfolioSimulator 実装（キャッシュ・保有株・平均取得単価の管理、履歴・約定記録保持）。
    - execute_orders: SELL を先に処理、BUY は資金に応じて株数を計算（スリッページ・手数料を考慮）、部分利確非対応（SELL は全量クローズ）。
    - mark_to_market: 終値で時価評価し DailySnapshot を記録（終値欠損時は 0 で評価し WARNING）。
    - TradeRecord / DailySnapshot の dataclass を提供。
  - src/kabusys/backtest/metrics.py:
    - バックテスト指標計算: CAGR, Sharpe Ratio（無リスク金利=0）, 最大ドローダウン, 勝率, ペイオフ比率, 総トレード数。
  - src/kabusys/backtest/engine.py:
    - run_backtest 実装: 本番 DuckDB からインメモリ DB へ必要テーブルをコピーしてバックテスト実行（signals/positions を汚さない）。
    - データコピーは日付範囲でフィルタ（performance を考慮して start_date - 300 日からコピー）。
    - market_calendar は全件コピー。コピー失敗は警告ログでスキップ。
    - 日次ループ: 前日シグナル約定 → positions に書き戻し → mark_to_market → generate_signals 呼び出し → ポジションサイジング／注文作成の流れを実装。
    - デフォルトパラメータ: initial_cash=10_000_000, slippage_rate=0.001, commission_rate=0.00055, max_position_pct=0.20。

- パッケージ公開 API
  - src/kabusys/strategy/__init__.py, src/kabusys/backtest/__init__.py などで主要関数/型をエクスポート。

### Changed
- （初回リリースにつき該当なし）

### Fixed
- （初回リリースにつき該当なし）

### Deprecated
- （初回リリースにつき該当なし）

### Removed
- （初回リリースにつき該当なし）

### Security
- 環境変数読み込み時に OS 環境を上書きしない保護機構（protected keys）を導入。機密値の上書きを予期せず行わない設計。

---

注記・設計上の重要点（コードからの推測）
- 外部依存の最小化: research/feature_exploration は pandas 等に依存せず標準ライブラリ＋DuckDBで実装。
- ルックアヘッドバイアス対策: すべての計算は target_date 時点のデータのみ参照するよう設計されている旨のコメントが一貫して存在。
- トランザクション/冪等性: features / signals / positions 等への書き込みは日付単位で DELETE → INSERT（トランザクション）により原子性・冪等性を確保。
- 異常値・欠損の扱い: Z スコアは ±3 でクリップ、None/非有限値は適切に扱う（スコア計算で中立値 0.5 を補完する等）。
- ドメイン閾値等はソース中の定数として明示（例: 最低株価 300 円、最低売買代金 5e8、STOP_LOSS -8% 等）。

もし変更点や追記してほしい項目（例: リリース日を別の日付にする、より詳細なファイル別差分など）があれば指示してください。