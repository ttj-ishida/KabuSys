CHANGELOG
=========

すべての変更は Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に準拠して記載しています。

[Unreleased]
------------

- なし

[0.1.0] - 2026-03-26
-------------------

Added
- 初回リリース: KabuSys 日本株自動売買システムの基本モジュール群を追加。
  - パッケージ初期バージョン: __version__ = "0.1.0"
  - パッケージ公開 API: data, strategy, execution, monitoring をエクスポート。

- 環境設定管理 (kabusys.config)
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルート判定は .git または pyproject.toml を基準）。
  - 自動ロードを無効化するための環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト用）。
  - .env パーサを強化:
    - export KEY=val 形式を受け入れ。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理に対応。
    - コメント処理（アンコメントルール）を細かく制御。
  - settings オブジェクトを提供。必須環境変数取得時に未設定だと ValueError を送出する _require を実装。
  - 各種設定プロパティを追加（J-Quants / kabuステーション / Slack / DB パス / 環境・ログレベル検証など）。
  - KABUSYS_ENV / LOG_LEVEL の値検証（許容値以外は ValueError）。

- ポートフォリオ構築 (kabusys.portfolio)
  - 銘柄選定:
    - select_candidates: スコア降順・タイブレークに signal_rank を使って上位 N を選択。
  - 重み計算:
    - calc_equal_weights: 等比率配分。
    - calc_score_weights: スコア加重配分。全スコアが 0 の場合は等配分へフォールバック（WARNING ログ）。
  - リスク調整:
    - apply_sector_cap: 既存保有のセクター別エクスポージャーを計算し、セクター集中上限を超えるセクターの新規候補を除外（"unknown" セクターは除外対象から除外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3）。未知レジームは 1.0 にフォールバックして警告ログを出力。

  - ポジションサイジング:
    - calc_position_sizes: allocation_method に応じた発注株数計算を実装（"risk_based","equal","score" をサポート）。
    - 単元（lot_size）で丸め、1銘柄上限・aggregate 上限（available_cash）を考慮。
    - cost_buffer を使った保守的コスト見積もりと、現金不足時のスケーリング論理（スケールダウン後の切片を lot_size 単位で再配分するアルゴリズムを実装）。
    - price 欠損時はその銘柄をスキップし、ログを出力。

- 戦略 (kabusys.strategy)
  - 特徴量エンジニアリング:
    - build_features: research モジュールの生ファクターを統合して正規化（Z スコア）・±3 でクリップした上で features テーブルへ日付単位で置換（トランザクション + バルク挿入、冪等性確保）。
    - ユニバースフィルタ（株価 >= 300 円、20日平均売買代金 >= 5億円）を適用。
  - シグナル生成:
    - generate_signals: features と ai_scores を統合し、momentum/value/volatility/liquidity/news の重み付き和で final_score を算出。
    - デフォルト重みを定義し、外部から与えられた weights は検証・補完・正規化して受け入れる（無効値は無視して警告ログ）。
    - AI スコアが未登録の銘柄はニュース要素を中立 (0.5) と扱う。
    - Bear レジーム判定時は BUY シグナルを抑制（レジーム判定は ai_scores の regime_score 平均が負で十分なサンプル数がある場合）。
    - エグジット判定 (_generate_sell_signals): ストップロス（終値/avg_price - 1 < -8%）とスコア低下（final_score < threshold）により SELL シグナル生成。保有銘柄の価格欠損時は SELL 判定をスキップして警告ログ。
    - SELL 優先ポリシー: SELL 対象銘柄は BUY 候補から除外し、BUY のランクを再割当て。
    - signals テーブルへ日付単位の置換（トランザクションで原子性を保証）。

- リサーチ (kabusys.research)
  - calc_momentum / calc_volatility / calc_value を実装（DuckDB を用いた SQL ウィンドウ関数で計算）。返り値は (date, code) キーの dict リスト。
  - feature_exploration:
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを1クエリで取得。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を実装。サンプル数不足時は None を返す。
    - factor_summary: 各ファクター列の基本統計量（count, mean, std, min, max, median）を計算。
    - rank: 同順位は平均ランクで処理（値は round(..., 12) で丸めて tie 検出の安定化）。

- バックテスト (kabusys.backtest)
  - metrics: DailySnapshot / TradeRecord から
    - CAGR, Sharpe Ratio（無リスク金利=0）, Max Drawdown, Win Rate, Payoff Ratio, total_trades を計算するユーティリティを実装。
  - simulator:
    - PortfolioSimulator クラスを実装。メモリ内でポートフォリオ状態・約定を管理。
    - execute_orders: SELL を先に処理（保有全量クローズ）、その後 BUY を処理。約定ではスリッページ率・手数料率を考慮し、TradeRecord を記録。
    - lot_size 引数を受け取り単元に対応（デフォルト 1、呼び出し側で 100 を渡す想定）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- （特に無し）

Notes / Known issues / TODO
- apply_sector_cap:
  - price_map に 0.0（または未設定）があるとエクスポージャーが過少評価され、ブロックが解除される恐れがある。将来的には前日終値や取得原価でフォールバックする検討が必要。
- position_sizing:
  - lot_size は現状グローバル共通（関数引数）。将来的に銘柄別 lot_map を受け取る設計へ拡張予定。
- signal_generator:
  - トレーリングストップや保有時間による時間決済は未実装（positions に peak_price / entry_date 等の情報が必要）。
  - ai_scores のサンプル数が少ないとレジーム判定が行われないように保護（サンプル閾値あり）。
- feature_engineering / generate_signals / build_features:
  - DUCKDB のテーブルスキーマ（features, ai_scores, positions, prices_daily, raw_financials, signals 等）に依存するため、スキーマ変更があった場合は調整が必要。
- config:
  - .env 読み込みはプロジェクトルートの探索に .git または pyproject.toml を使用。パッケージ配布後の設置環境で想定通りに動作するか注意。

Contact / Contributing
- バグ報告・機能提案はリポジトリの Issue を利用してください。テスト・CI の整備およびドキュメント整備を進める予定です。