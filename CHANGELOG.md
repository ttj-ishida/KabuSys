CHANGELOG
=========

すべての注目すべき変更点をこのファイルに記録します。
このプロジェクトでは "Keep a Changelog" の形式に従い、セマンティックバージョニングを使用します。

[Unreleased]
------------

（なし）

[0.1.0] - 2026-03-26
--------------------

Added
- パッケージ基盤
  - パッケージの初期バージョンをリリース。パッケージメタ情報は src/kabusys/__init__.py にて __version__ = "0.1.0" として管理。
  - __all__ に主要サブパッケージ（data, strategy, execution, monitoring）を宣言。

- 環境設定管理（src/kabusys/config.py）
  - .env / .env.local の自動読み込み機能を実装。プロジェクトルート判定は .git または pyproject.toml を基準に行うため、CWD に依存しない安全なロードを実現。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 による自動ロード無効化に対応（テスト用途）。
  - .env パース機能を実装：コメント行・export プレフィックス・シングル/ダブルクォート内エスケープ・インラインコメントの扱い等に対応。
  - 環境値取得ユーティリティ Settings を実装。J-Quants / kabu API / Slack / DB パス / 環境 (development/paper_trading/live) / ログレベルの検証と補完を行う（未設定の必須値は ValueError を送出）。

- ポートフォリオ構築（src/kabusys/portfolio/*）
  - 候補選定: select_candidates — スコア降順・同点時は signal_rank でタイブレークして上位 N 件を返す。
  - 重み計算: calc_equal_weights / calc_score_weights — スコア合計 0 の場合は等配分へフォールバックし警告を出力。
  - リスク制御: apply_sector_cap — 既存保有のセクター別エクスポージャを計算し、セクター集中上限を超える新規候補を除外（"unknown" セクターは制限対象外として扱う）。
  - レジーム乗数: calc_regime_multiplier — "bull"/"neutral"/"bear" に基づく投下資金乗数を提供。未知レジームは警告のうえ 1.0 にフォールバック。
  - 株数決定: calc_position_sizes — allocation_method ("risk_based", "equal", "score") に対応した発注株数決定ロジックを実装。単元（lot_size）丸め、1銘柄上限、aggregate cap（利用可能現金に対するスケーリング）、cost_buffer を用いた保守的コスト見積り、価格欠損ハンドリングなどを含む。

- 特徴量生成（src/kabusys/strategy/feature_engineering.py）
  - build_features を実装。research モジュールから生ファクターを取得しユニバースフィルタ（最低株価・最低平均売買代金）を適用、Z スコア正規化（指定列に対して）と ±3 クリッピングを行い、features テーブルへ日付単位の置換（冪等な UPSERT）で書き込む。
  - DuckDB を用いた prices_daily / raw_financials 参照に対応。欠損やトランザクションエラー時のロールバックを実装。

- シグナル生成（src/kabusys/strategy/signal_generator.py）
  - generate_signals を実装。features と ai_scores を組み合わせ、各コンポーネント（momentum/value/volatility/liquidity/news）を計算し最終スコア(final_score) を作成。
  - AI スコア（news）とレジームスコアを統合し、Bear レジーム検知時は BUY シグナルを抑制する挙動を実装。
  - BUY は閾値（デフォルト 0.60）を超えた銘柄を選定、SELL はストップロス・スコア低下を基に判定（保有銘柄の全量売却を想定）。
  - 重みの入力検証と合計正規化、欠損値の中立補完（0.5）など堅牢性向上のための処理を実装。
  - signals テーブルへ日付単位の置換で書き込む（トランザクションで原子性保証）。

- リサーチ / ファクター（src/kabusys/research/*）
  - ファクター計算: calc_momentum, calc_volatility, calc_value を実装。
    - momentum: 1/3/6 ヶ月リターン、200 日移動平均乖離率（データ不足時は None）。
    - volatility: 20 日 ATR / 相対 ATR（atr_pct）、20 日平均売買代金、出来高比率。true range 計算は高値/安値/前日終値の欠損に配慮。
    - value: raw_financials から直近財務データを取得し PER / ROE を計算（EPS=0 は None）。
  - 研究用ユーティリティ:
    - calc_forward_returns: 指定ホライズンについて将来リターンを一括算出（複数ホライズンをサポート、入力検証あり）。
    - calc_ic: スピアマンのランク相関（IC）計算。サンプル不足時は None。
    - factor_summary: 基本統計量（count/mean/std/min/max/median）を計算。
    - rank: 平均ランク付け（同順位は平均ランク）を実装。
  - すべて DuckDB を利用し、外部大規模依存のない実装を目指す。

- バックテスト（src/kabusys/backtest/*）
  - PortfolioSimulator を実装。メモリ内でポジション・取得単価・履歴・約定記録を管理。シグナル処理は SELL を先に、BUY を後に処理。スリッページ（BUY はプラス、SELL はマイナス）・手数料率を適用し TradeRecord を記録。部分約定や lot_size を考慮。
  - DailySnapshot / TradeRecord のデータクラスを定義。
  - バックテスト指標計算: calc_metrics（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, total_trades）を提供。各指標の内部計算関数を実装し、エッジケース（サンプル不足・ゼロ除算）への防御を行う。

- その他
  - 各モジュールに詳細な docstring と設計方針コメントを付与し、仕様参照（StrategyModel.md / PortfolioConstruction.md / BacktestFramework.md 等）を明示。
  - ロガー出力（debug/info/warning）を各所に実装して挙動のトレースと潜在問題の可視化を実現。

Known limitations / Notes
- 一部仕様は将来的な拡張を前提とした TODO を残している（例: 銘柄ごとの lot_size 対応、price 欠損時のフォールバック価格利用、トレーリングストップや時間決済の未実装）。
- calc_score_weights は全スコアが 0 の場合に等配分へフォールバックする設計だが、これは意図的な運用ルールである（警告出力あり）。
- generate_signals の Bear 相場時の BUY 抑制は、AI 側のレジームスコアサンプル数が閾値未満のときは判定されないように設計（誤判定回避のため）。
- データベース（DuckDB）スキーマやテーブル（prices_daily, raw_financials, features, ai_scores, positions, signals 等）は外部で準備することを想定。

Security
- この段階では機密情報の取り扱いにおいて環境変数管理をサポートしているが、実運用では .env ファイルの取り扱い（権限・非コミット等）や API トークン管理に十分注意してください。

Authors
- 初期実装（機能群の整備・API の定義・ドキュメント注釈）

LICENSE
- 各自の配布ポリシーに準じてください。