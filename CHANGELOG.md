Keep a Changelog に準拠した CHANGELOG.md（日本語）
※ コードベースから推測して作成しています。

All notable changes to this project will be documented in this file.
The format is based on "Keep a Changelog" and this project adheres to
https://keepachangelog.com/ja/1.0.0/

未リリース (Unreleased)
-----------------------
変更予定 / 既知の TODO
- 銘柄ごとの単元（lot_size）を stocks マスタから取得できるよう拡張予定（現状は全銘柄共通単元を想定）。
- position sizing の price 欠損時に前日終値や取得原価でフォールバックする仕組みの追加検討。
- シグナル/ポジションのトレーリングストップ（peak_price 必要）や時間決済（保有日数上限）の実装予定。
- 部分利確／部分損切りロジックの導入（現状は SELL は保有全量クローズ）。
- テストカバレッジ拡充、外部インターフェース（execution 層／API 呼び出し）の統合テスト追加。

0.1.0 - 2026-03-26
-----------------

Added
- パッケージ初期リリース相当の機能群を追加。
  - 基本パッケージ情報: kabusys.__version__ = 0.1.0 を設定。
- 環境設定管理 (kabusys.config)
  - .env ファイル自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を起点）。
  - .env / .env.local の読み込み優先度制御（OS 環境変数が保護される仕組み）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化機能（テスト用途）。
  - .env の行パーサを実装（export プレフィックス対応、クォート文字列のエスケープ処理、コメントの取り扱い）。
  - Settings クラスによる型付きアクセス（J-Quants / kabu / Slack / DB パス / 環境・ログレベル判定など）。
  - 無効な KABUSYS_ENV / LOG_LEVEL に対する検証と明示的なエラー。

- ポートフォリオ構築 (kabusys.portfolio)
  - 候補選定: select_candidates（スコア降順、同点時のタイブレークロジック）。
  - 配分重み: calc_equal_weights（等金額） / calc_score_weights（スコア比率。全スコア0 の場合は等金額へフォールバック）。
  - リスク調整: apply_sector_cap（セクター集中上限判定。unknown セクターは適用除外）、calc_regime_multiplier（市場レジームに応じた投下資金乗数、未知レジームはフォールバック）。
  - ポジションサイジング: calc_position_sizes
    - allocation_method に応じた株数計算（risk_based / equal / score）。
    - 単元丸め（lot_size）、1 銘柄上限、aggregate cap（available_cash に基づくスケーリング）。
    - cost_buffer を用いた保守的コスト見積りとスケールダウン時の端数配分アルゴリズム（lot 単位で残差再分配）。
    - 価格欠損時は該当銘柄をスキップする堅牢性。

- 戦略（Feature Engineering / Signal Generation） (kabusys.strategy)
  - feature_engineering.build_features
    - research モジュールから得た生ファクターを統合、ユニバースフィルタ（最低株価・平均売買代金）適用、Z スコア正規化（±3 クリッピング）、features テーブルへの日付単位の置換（トランザクションで原子性保証）。
    - DuckDB を利用して prices_daily / raw_financials を参照。
    - トランザクションの失敗時にロールバック処理を行い、例外は上位へ伝搬。
  - signal_generator.generate_signals
    - features と ai_scores を統合して最終スコア final_score を計算（momentum/value/volatility/liquidity/news の重み付け）。
    - 重み辞書のバリデーションと合計正規化（不正値はスキップ、合計が 1 でない場合に再スケール）。
    - Bear レジーム検知時は BUY シグナルを抑制（レジーム判定は ai_scores の regime_score 平均に依存、サンプル不足時は Bear とみなさない）。
    - BUY シグナル閾値（デフォルト 0.60）、SELL はストップロスおよびスコア低下による判定を実装。
    - signals テーブルへの日付単位置換（トランザクション + バルク挿入）。

- リサーチ（factor 計算・解析） (kabusys.research)
  - factor_research: calc_momentum / calc_volatility / calc_value を実装（prices_daily / raw_financials のみ参照）。
    - Momentum: mom_1m/mom_3m/mom_6m / ma200_dev（データ不足は None）。
    - Volatility: ATR（atr_20）、atr_pct、avg_turnover、volume_ratio。true_range の NULL 伝播制御により欠損制御。
    - Value: PER（EPS が 0/欠損 の場合は None）、ROE（最新財務レコードを参照）。
  - feature_exploration:
    - calc_forward_returns（複数ホライズンの将来リターンを一括取得。horizons 検証あり）。
    - calc_ic（Spearman ランク相関の計算。サンプル不足や分散 0 の場合は None）。
    - factor_summary（count/mean/std/min/max/median を算出）。
    - rank（同順位の平均ランク処理。丸めにより ties の検出を安定化）。
  - 依存は標準ライブラリ + DuckDB のみ（pandas 等に依存しない設計）。

- バックテスト（kabusys.backtest）
  - metrics.calc_metrics: DailySnapshot / TradeRecord から主要評価指標（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, total_trades）を計算。
  - simulator.PortfolioSimulator
    - メモリ内ポートフォリオ状態管理、擬似約定ロジック（SELL を先に処理してから BUY を処理）。
    - 約定時のスリッページ（BUY:+、SELL:-）と手数料モデルの適用、TradeRecord の生成、履歴記録。
    - SELL は保有全量クローズ（部分約定非対応、現状の仕様）。
    - 日次スナップショット（DailySnapshot）を保持。

Changed
- （初回リリース）プロジェクト構成に基づく API エクスポート（kabusys.portfolio, kabusys.strategy, kabusys.research の __all__ を通じた外部公開関数群の明示）。

Fixed
- .env パーサでのクォート・エスケープ処理、export プレフィックスとコメント処理を実装し、実運用での .env 設定の柔軟性を向上。
- DuckDB トランザクション処理での例外発生時に ROLLBACK を試行し、失敗は警告ログに記録するよう堅牢化。

Security
- 環境変数の自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD により明示的に無効化可能（CI/テスト環境向け）。OS 環境変数を保護する設計（protected set を利用して .env による上書きを防止）。

Notes / 実装上の注意点
- 多くの関数は DuckDB 接続や純粋なデータ構造を受け取り、副作用を減らす設計（本番 API への直接アクセスは行わない）。
- 一部のロジックは現状の入力データの有無に依存（価格欠損時は処理をスキップ、features 欠損銘柄は final_score=0 扱いで SELL 判定される等）。
- 将来的に銘柄別単元や価格フォールバック、部分利確・トレーリングストップ等の機能追加を見込んでいる（コード内に TODO コメントあり）。

---

上記は提供されたソースコードから推測してまとめた CHANGELOG です。必要であれば
- 各機能ごとの利用例（コードスニペット）
- 追加のリリースノート（マイナー/パッチリリース想定）
等を追記します。どの形式で詳細化しますか？