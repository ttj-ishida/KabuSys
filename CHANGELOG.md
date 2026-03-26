CHANGELOG
=========

すべての重要な変更点をここに記録します。  
このファイルは「Keep a Changelog」仕様に準拠しています。

フォーマット:
- 変更はセクションごとに分類（Added / Changed / Fixed / Deprecated / Removed / Security）しています。
- 可能な限り機能・振る舞い・既知の制約を明記しています。

[Unreleased]
------------

（現在のリポジトリ状態では未リリースの変更はありません）

[0.1.0] - 2026-03-26
-------------------

Added
- パッケージ初期リリース (kabusys v0.1.0)
  - 高頻度売買エンジンではなく、日本株のアルゴリズムトレーディング基盤としてのコア機能群を実装。
- 環境設定 / 読み込み
  - 環境変数読み込みユーティリティ (kabusys.config)
    - プロジェクトルートを .git または pyproject.toml を基準に探索して .env / .env.local を自動ロード（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - .env ファイルの行解析で export プレフィックス、クォート、バックスラッシュエスケープ、インラインコメントの扱いに対応。
    - .env.local は .env の上書き（OS 環境変数は protected として上書き不可）。
    - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パス / 環境（development/paper_trading/live）/ログレベル等の取得とバリデーションを行う。
- ポートフォリオ構築
  - 候補選定・重み付け (kabusys.portfolio.portfolio_builder)
    - select_candidates: スコア降順、同点時 signal_rank 昇順で上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等分配とスコア加重配分（スコア合計が 0 の場合は等分配にフォールバックし警告）。
  - リスク調整 (kabusys.portfolio.risk_adjustment)
    - apply_sector_cap: 既存ポジションのセクター別エクスポージャーを計算し、指定比率を超過しているセクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3。未知レジームは警告後 1.0 フォールバック）。
  - ポジションサイズ計算 (kabusys.portfolio.position_sizing)
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") による株数計算。
    - risk_based: 許容リスク率 / 損切り率に基づく算出、単元（lot_size）丸め。
    - equal/score: 重みと max_utilization を使った割当、per-position と aggregate の上限、cost_buffer による保守的見積り。
    - aggregate cap を超えた場合はスケーリングして端数（lot 単位）を残差処理で再配分。
    - 単元株将来拡張（銘柄別 lot_map）は TODO。
- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - build_features: research モジュールの生ファクターを統合し、ユニバースフィルタ（最低株価／最低売買代金）、Z スコア正規化（指定カラム、±3 クリップ）、features テーブルへ日付単位の冪等 UPSERT を実行。
  - DuckDB を用いた価格取得とトランザクション（BEGIN/COMMIT/ROLLBACK）を管理。ROLLBACK エラーは警告ログを出力。
- シグナル生成 (kabusys.strategy.signal_generator)
  - generate_signals: features と ai_scores を統合して final_score を算出し BUY / SELL シグナルを生成して signals テーブルへ冪等で書き込み。
    - コンポーネントスコア: momentum / value / volatility / liquidity / news（AI）。
    - スコア正規化・欠損値補完: None のコンポーネントは中立 0.5 で補完。
    - AI スコア未登録時はニューススコア中立（0.5）扱い。
    - Bear レジーム検知時は BUY シグナルを抑制（レジーム判定は ai_scores の regime_score の平均）。
    - SELL（エグジット）ロジック: ストップロス（終値 / avg_price -1 < -8%）および final_score が閾値未満。
    - SELL 優先ポリシー: SELL 対象は BUY 候補から除外しランクを再付与。
    - weights パラメータは デフォルト値でフォールバック、ユーザ提供値はバリデーション/正規化して受け付ける。
    - 未実装のエグジット条件（Trailing stop / 時間決済）はコード内で明示。
- 研究ユーティリティ (kabusys.research)
  - factor_research:
    - calc_momentum: mom_1m/mom_3m/mom_6m と ma200_dev（200 日ウィンドウ必須）を計算。
    - calc_volatility: ATR(20)/atr_pct、avg_turnover、volume_ratio を計算（true_range の NULL 伝播に注意）。
    - calc_value: raw_financials から直近財務を取得して PER/ROE を計算（EPSが0/欠損は None）。DuckDB の ROW_NUMBER を使用して最新財務を取得。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。horizons は 1〜252 の整数で検証。
    - calc_ic: スピアマンのランク相関（IC）を計算。3 銘柄未満で None を返す。
    - factor_summary: 各カラムの count/mean/std/min/max/median を返す。
    - rank: 同順位は平均ランクを割り当てる実装。
  - 研究 API は DuckDB の prices_daily/raw_financials のみ参照し、本番環境への副作用はなし。
- バックテスト (kabusys.backtest)
  - simulator:
    - PortfolioSimulator: メモリ内でポートフォリオ状態を管理。SELL を先に処理し全量クローズする（部分利確未対応）。
    - スリッページ（BUY は +、SELL は -）・手数料の適用を考慮した約定モデル。TradeRecord / DailySnapshot のデータモデルを提供。
    - execute_orders は lot_size を受け取り単元考慮した挙動をサポート（デフォルト lot_size=1。日本株は通常 100 を期待）。
  - metrics:
    - calc_metrics: DailySnapshot / TradeRecord から各種評価指標を計算（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, Total Trades）。
    - 内部関数で日次リターン計算、年次化（252 営業日）等を実装。

Changed
- （初版のため該当なし）

Fixed
- （初版のため該当なし）

Deprecated
- （初版のため該当なし）

Removed
- （初版のため該当なし）

Security
- （初版のため該当なし）

Notes / Known limitations / TODO
- .env パーサは多くのユースケースに対応しているが、複雑なシェル展開や改行を跨ぐクォート等には対応していない点に注意。
- apply_sector_cap は price_map に価格が欠損（0.0）の場合、エクスポージャーが過少見積もられる可能性があることを TODO コメントで明示。将来的に前日終値や取得原価等のフォールバックを検討。
- signal_generator の一部エグジット条件（トレーリングストップ、時間決済）は未実装（positions テーブルに peak_price / entry_date が必要）。
- position_sizing は現状全銘柄共通の lot_size を想定。将来的に銘柄別 lot_map を受け取る拡張を予定。
- generate_signals の Bear 判定は ai_scores のサンプル数が一定数未満の場合は False（Bear とみなさない）としている（誤検知防止）。
- DB トランザクションでの例外発生時は Rollback を試み、失敗すると警告ログを出す実装。アプリ側でも上位での例外ハンドリングを推奨。

API / エクスポートまとめ
- 主要公開関数 / クラス（例）
  - kabusys.config.settings (Settings)
  - kabusys.portfolio.select_candidates / calc_equal_weights / calc_score_weights / calc_position_sizes / apply_sector_cap / calc_regime_multiplier
  - kabusys.strategy.build_features / generate_signals
  - kabusys.research.calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary / rank
  - kabusys.backtest.PortfolioSimulator / DailySnapshot / TradeRecord / calc_metrics

開発者向け補足
- ログは各モジュールで logger.getLogger(__name__) を使用。DEBUG レベルの詳細情報（セクター除外や価格欠損スキップ等）を出力する箇所あり。
- DuckDB を用いる処理では SQL 内でウィンドウ関数や LEAD/LAG/AVG 等を活用しており、実行パフォーマンスの観点でインデックス的事前集約が有効な場合がある。
- バージョニング: package の __version__ は "0.1.0"。

追加要望や誤りの指摘があれば知らせてください。コードから推測した点を含むため、実装意図と異なる箇所があれば調整します。