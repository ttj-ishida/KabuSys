# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に準拠して記載しています。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-22
初回公開リリース。日本株自動売買システムのコア機能群を実装しています。主な追加点・仕様は以下の通りです。

### Added
- パッケージ基礎
  - kabusys パッケージ初期化（__version__ = 0.1.0）。主要サブパッケージを __all__ で公開（data, strategy, execution, monitoring）。
- 設定 / 環境変数管理（kabusys.config）
  - .env ファイルまたは OS 環境変数から設定を自動読み込み。
  - プロジェクトルート検出: __file__ から親ディレクトリを探索し `.git` または `pyproject.toml` を検出してルートを特定。
  - 読み込み順序: OS 環境変数 > .env.local > .env。テスト等で自動ロードを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD フラグを実装。
  - .env パーサの強化:
    - export KEY=val 形式対応
    - シングル/ダブルクォート文字列のエスケープ処理対応
    - インラインコメントの扱い（クォートなしでは '#' の直前が空白/タブの場合のみコメントと認識）
  - 環境変数取得ユーティリティ Settings を提供。必須項目取得時に未設定なら明示的に ValueError を送出。
  - KABUSYS_ENV（development/paper_trading/live）や LOG_LEVEL の値検証、デフォルト値（例: KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH）を設定。
- 戦略・特徴量（kabusys.strategy）
  - feature_engineering.build_features:
    - research モジュールの生ファクター（calc_momentum, calc_volatility, calc_value）を取得して統合。
    - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5億円）を適用。
    - 指定カラムを Z スコア正規化（kabusys.data.stats.zscore_normalize を使用）、±3 でクリップして外れ値影響を抑制。
    - features テーブルへ日付単位で置換（DELETE→INSERT）しトランザクションで原子性を保証。
  - signal_generator.generate_signals:
    - features と ai_scores を統合し各コンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - シグモイド変換等により各成分を [0,1] に正規化し、重み付き合算で final_score を算出（デフォルト重み実装）。
    - Bear レジーム検知（ai_scores の regime_score 平均が負かつサンプル数 >= 3）により BUY シグナルを抑制。
    - BUY 閾値デフォルト 0.60。SELL 判定としてストップロス（-8%）と final_score の閾値未満を実装。
    - positions テーブルを参照して保有銘柄のエグジット判定を行い、signals テーブルへ日付単位で置換（トランザクション）。
    - weights に対する入力検証（未知キー・非数値・負値・NaN/Inf を無視、合計が 1 になるよう再スケール）。
- リサーチ機能（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率（ma200_dev）を DuckDB SQL で計算。過去データ不足時は None を返す。
    - calc_volatility: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算。true_range の NULL 伝播を適切に制御。
    - calc_value: raw_financials から target_date 以前の最新財務を取得し PER/ROE を計算。EPS 未定義/0 の場合は PER を None。
  - feature_exploration:
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを一括 SQL で取得。ホライズン入力の検証（正の整数かつ <=252）。
    - calc_ic: ファクター値と将来リターンの Spearman ランク相関（IC）を計算。サンプル不足（<3）や分散 0 の場合は None。
    - factor_summary: count/mean/std/min/max/median を計算（None は除外）。
    - rank: 同順位（ties）を平均ランクで処理。丸め（round(..., 12)）で浮動小数点の ties 検出漏れを低減。
  - research パッケージの public API を整理してエクスポート。
- バックテストフレームワーク（kabusys.backtest）
  - simulator:
    - PortfolioSimulator: メモリ内でのポートフォリオ管理、BUY/SELL 約定ロジック、スリッページ・手数料モデルを実装。
    - BUY は資金配分（alloc）に基づき始値にスリッページを加味、手数料を差し引いて購入株数を計算。BUY 処理は不足資金を考慮して再計算。
    - SELL は保有全量クローズ（部分利確非対応）、始値にスリッページを適用、手数料控除、実現損益を計上。
    - execute_orders は SELL を先に処理（資金確保のため）し、BUY を後で処理する。
    - mark_to_market: 終値で評価し DailySnapshot を記録。評価価格欠損時は 0 で評価し警告ログを出力。
    - TradeRecord / DailySnapshot dataclass を定義。
  - metrics:
    - calc_metrics と内部関数で CAGR、Sharpe（無リスク金利=0）、最大ドローダウン、勝率、Payoff Ratio、総トレード数を計算。
  - engine.run_backtest:
    - 本番 DB からインメモリ DuckDB へ必要データをコピーしてバックテスト実行（signals/positions を汚染しない）。
    - _build_backtest_conn: 指定レンジのテーブルをフィルタしてコピー、market_calendar は全件コピー。コピー失敗は警告でスキップ。
    - 日次ループ: 前日シグナルの約定 → positions テーブルに書き戻し（generate_signals の SELL 判定に必要）→ 終値評価 → generate_signals（当日）→ ポジションサイジング → 次日約定の順序で実行。
    - デフォルトのスリッページ/手数料/最大ポジション比率のパラメタを提供。
  - backtest パッケージの public API を整理してエクスポート（run_backtest, BacktestResult, DailySnapshot, TradeRecord, BacktestMetrics）。

### Changed
- （新規リリースのため該当なし）

### Fixed
- （新規リリースのため該当なし）

### Removed
- （新規リリースのため該当なし）

### Security
- 環境変数自動読み込み時に OS 環境変数を保護するため protected set を導入（.env ファイルで既存 OS 環境を上書きしない挙動を実現）。

### Notes / Limitations
- エグジット条件の一部（トレーリングストップ、時間決済）は実装予定（コメントで未実装箇所を明記。positions テーブルに peak_price / entry_date 等の追加が必要）。
- research モジュールは外部ライブラリに依存せず標準ライブラリ + DuckDB SQL で実装しているため、Pandas 等の利便性は利用していない。
- generate_signals / build_features はルックアヘッドバイアスを防ぐ設計（target_date 時点のデータのみ使用）を意図している。
- DB 書き込み（features / signals / positions）は日付単位で削除→挿入を行いトランザクションで整合性を担保しているが、外部からの同時更新シナリオでは追加の排他制御が必要な場合がある。

---
開発・利用に関する詳細は各モジュールの docstring とリポジトリ内の設計ドキュメント（StrategyModel.md / BacktestFramework.md 等）を参照してください。