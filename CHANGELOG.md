# Changelog

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の形式に従います。  

<!-- バージョン間の差分があれば Unreleased に記載してください -->
## [Unreleased]

---

## [0.1.0] - 2026-03-22

初回リリース。本リリースでは日本株自動売買フレームワークのコア機能を一通り実装しました。主な追加点と実装方針は以下のとおりです。

### Added
- パッケージの基本情報
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - エクスポート済みモジュール: data, strategy, execution, monitoring（execution は空パッケージ）
- 環境設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定値を自動読み込み
    - プロジェクトルート検出: .git または pyproject.toml を基準に探索（__file__ ベースで CWD に依存しない）
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - .env パーサ実装
    - export KEY=val 形式対応
    - シングル/ダブルクォート、バックスラッシュエスケープ対応
    - インラインコメントの扱い（クォート有無での動作差）
    - ファイル読み込み失敗時は警告を出して継続
    - protected（OS 環境変数）を保護する override ロジック
  - Settings クラス
    - J-Quants / kabu ステーション / Slack / DB パス 等のプロパティ（必須項目は未設定時に ValueError）
    - KABUSYS_ENV のバリデーション (development / paper_trading / live)
    - LOG_LEVEL のバリデーション（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - ユーティリティ: is_live / is_paper / is_dev
- 戦略: 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - build_features(conn, target_date)
    - research モジュールの生ファクター（calc_momentum / calc_volatility / calc_value）を取得して統合
    - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）を適用
    - 指定列を Z スコア正規化し ±3 でクリップ（外れ値の影響軽減）
    - features テーブルへ日付単位の置換（DELETE + バルク挿入、トランザクションで原子性保証）
    - ルックアヘッドバイアス回避のため target_date 時点のデータのみ参照
- 戦略: シグナル生成 (kabusys.strategy.signal_generator)
  - generate_signals(conn, target_date, threshold, weights)
    - features と ai_scores を統合し、momentum/value/volatility/liquidity/news のコンポーネントスコアを計算
    - シグモイド変換や欠損補完（None のコンポーネントは中立 0.5）を採用
    - デフォルト重みを提供、ユーザー重みは検証・合成・再スケール
    - Bear レジーム検知（ai_scores の regime_score の平均が負かつ十分なサンプル数がある場合）
      - Bear 時は BUY シグナルを抑制
    - SELL 条件（ストップロス -8% / final_score が閾値未満）を実装
    - signals テーブルへ日付単位の置換（トランザクションで原子性保証）
    - positions を参照して features に存在しない保有銘柄は score=0 とみなすなど、欠損耐性ロジックを実装
- Research（研究用ユーティリティ）
  - ファクター計算 (kabusys.research.factor_research)
    - calc_momentum: mom_1m/mom_3m/mom_6m, ma200_dev（200日分のデータが不足する場合は None）
    - calc_volatility: ATR(20)、atr_pct（相対 ATR）、avg_turnover、volume_ratio（20日移動平均）
      - true_range の NULL 伝播を適切に扱う実装（high/low/prev_close が NULL の場合は NULL）
    - calc_value: target_date 以前の最新 raw_financials を結合し PER / ROE を計算
  - 特徴量探索 (kabusys.research.feature_exploration)
    - calc_forward_returns: 指定ホライズン（デフォルト 1,5,21 営業日）の将来リターンを一括取得
    - calc_ic: スピアマンランク相関（Information Coefficient）を実装（同順位は平均ランク）
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算
    - rank: 同順位を平均ランクにするランク付けユーティリティ（丸めによる ties 対応）
  - 外部ライブラリに依存せず、DuckDB と標準ライブラリのみで実装
- バックテスト (kabusys.backtest)
  - engine.run_backtest: 本番 DB からインメモリ DuckDB へ必要データをコピーして日次ループでシミュレーション
    - データコピー範囲は start_date - 300日 〜 end_date（必要テーブルを日付範囲で絞ってコピー）
    - market_calendar は全件コピー
    - get_trading_days を利用して営業日ループ
    - シグナル生成→約定→positions 更新→時価評価→翌日シグナルの流れを実装
  - PortfolioSimulator（kabusys.backtest.simulator）
    - execute_orders: SELL を先に処理してから BUY（資金確保、SELL は全量クローズ）
    - スリッページ（slippage_rate）と手数料（commission_rate）を適用した約定価格・手数料計算
    - BUY の場合、手数料込みで取得可能株数を再計算して資金オーバーを回避
    - mark_to_market: 終値で時価評価、終値欠損時は 0 として警告を出す
    - TradeRecord / DailySnapshot の定義
  - metrics (kabusys.backtest.metrics)
    - calc_metrics: CAGR / Sharpe Ratio / Max Drawdown / Win Rate / Payoff Ratio / total_trades を計算
    - 各指標の堅牢な実装（データ不足やゼロ除算等に対する安全処理）
- DB 操作・トランザクションの堅牢化
  - features / signals の更新はトランザクション（BEGIN/COMMIT/ROLLBACK）で原子性を保証
  - バックテスト用データコピー時にエラーが発生してもプロセス継続（警告ログ）
- ロギングと警告
  - 各モジュールで適切な logger を利用し、欠損・不整合・無効な入力に対して警告・情報ログを出力

### Changed
- （初回リリースにつき該当なし）

### Fixed
- （初回リリースにつき該当なし）

### Deprecated
- 該当なし

### Removed
- 該当なし

### Security
- 特になし

---

Notes / 実装上の設計方針（抜粋）
- ルックアヘッドバイアスを避けるため、すべての集計・判定は target_date 時点のデータのみを参照します。
- 外部 API（発注先や実口座）への直接依存は持たない設計。生成される signals は DB に保存され、実運用の execution 層で読み取って発注する想定です。
- 研究コード（research/*）は本番処理とは分離され、DuckDB と標準ライブラリのみで動作するようにしています（pandas 等に依存しない設計）。
- トランザクションとバルク挿入で DB 更新の原子性・性能を確保しています。

もし CHANGELOG に追記してほしい点（例えば機能の細かい例、変更履歴の過去分、リリース日付の修正など）があれば教えてください。