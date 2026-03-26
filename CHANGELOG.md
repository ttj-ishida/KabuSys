# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。  
このプロジェクトの初期リリース (v0.1.0) に含まれる主要な実装・機能をコードベースから推測してまとめています。

最新リリース
------------

### [0.1.0] - 2026-03-26

Added
-----
- パッケージ全体
  - パッケージの初期公開。トップレベル `kabusys`（__version__ = "0.1.0"）。
  - モジュールのエクスポート整理（strategy / portfolio / execution / monitoring 等を想定）。

- 環境設定 (kabusys.config)
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
    - 自動読み込みはプロジェクトルート（.git または pyproject.toml）を探索して行うため、CWD に依存しない。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env 解析の堅牢化:
    - コメント行、`export KEY=...` 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの取扱いなどに対応。
  - Settings クラスを提供し、必要な環境変数をプロパティで取得（必須項目は未設定時に ValueError を送出）。
    - J-Quants / kabu ステーション / Slack / データベースパス等の設定を提供。
    - KABUSYS_ENV の値検証（development / paper_trading / live）。
    - LOG_LEVEL の値検証（DEBUG/INFO/...）。

- ポートフォリオ構築 (kabusys.portfolio)
  - 候補選定・配分計算（pure functions）を実装。
    - select_candidates: BUY シグナルをスコア降順（同点は signal_rank 昇順でタイブレーク）で上位 N を選択。
    - calc_equal_weights: 等金額配分（各銘柄 1/N）。
    - calc_score_weights: スコア加重配分（全スコアが 0 の場合は等配分へフォールバックし WARNING を出力）。
  - リスク調整:
    - apply_sector_cap: セクター集中制限の適用。既存保有の時価を計算し、指定比率を超えるセクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数を返す（bull=1.0, neutral=0.7, bear=0.3）。未知レジームは 1.0 にフォールバックし警告出力。
  - ポジションサイジング:
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に対応した発注株数計算。
      - risk_based: 許容リスク率、損切り率に基づく計算。
      - equal/score: 重み・利用可能現金・max_utilization・max_position_pct を考慮した計算。
      - lot_size（単元）を考慮した丸め、price の欠損や上限遵守、cost_buffer を用いた保守的見積り、aggregate cap 時の縮小比率計算と端数処理（ロット単位での再配分）を実装。
      - price 欠損時のスキップやログ出力など堅牢なハンドリング。

- 戦略（特徴量・シグナル） (kabusys.strategy)
  - feature_engineering.build_features:
    - research モジュールから得た raw ファクターをマージし、ユニバースフィルタ（株価・流動性）、Z スコア正規化、±3 でのクリップを行い `features` テーブルへ冪等的（削除→挿入）に書き込み。
    - DuckDB を利用したクエリで target_date 以前の最新価格を参照する等、ルックアヘッドバイアスを避ける設計。
    - トランザクション制御（BEGIN/COMMIT/ROLLBACK）とエラー時の安全なロールバック処理。
  - signal_generator.generate_signals:
    - `features` と `ai_scores` を統合し、momentum/value/volatility/liquidity/news のコンポーネントスコアを計算して最終スコア（final_score）を算出。
    - デフォルト重み（momentum=0.40 等）と閾値（default 0.60）を採用。ユーザ重みの検証・フォールバック・正規化を実装。
    - AI レジームスコアの平均に基づく Bear レジーム判定（サンプル不足時は Bear ではない扱い）。Bear では BUY シグナルを抑制。
    - 保有ポジションに対する SELL（エグジット）判定を実装（ストップロスとスコア低下）。SELL 優先ポリシー（SELL 対象は BUY から除外）を実装。
    - signals テーブルへの冪等書き込み（削除→挿入）、トランザクション保護。

- リサーチ機能 (kabusys.research)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率を計算（データ不足は None）。
    - calc_volatility: ATR20・相対ATR(atr_pct)・20日平均売買代金・出来高比率を計算（true_range の NULL 伝播制御等を配慮）。
    - calc_value: raw_financials から直近財務データを取得し PER/ROE を計算。
    - DuckDB による効率的なクエリとデータ不足時の適切な取り扱い。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。
    - calc_ic: factor と将来リターンの Spearman ランク相関（IC）を計算。サンプル不足時に None を返す。
    - factor_summary: count/mean/std/min/max/median を算出する統計サマリ。
    - rank: 同順位は平均ランクを与えるランク関数（round(...,12) による丸めで ties 対応）。

- バックテスト (kabusys.backtest)
  - simulator:
    - DailySnapshot / TradeRecord のデータモデルを実装。
    - PortfolioSimulator: メモリ内でポートフォリオ状態を管理し、signals を受けて約定処理を行う。SELL を先に処理し（保有全量クローズ）、その後 BUY を処理。スリッページ・手数料モデルを適用した約定価格・手数料計算。
    - 約定時の lot_size をサポート（日本株の単元に対応可能）。
  - metrics:
    - calc_metrics: history（DailySnapshot）と trades（TradeRecord）からバックテスト指標（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, total trades）を計算する一連の関数を提供。

- その他
  - 各モジュールでログ出力（logger）と警告を適切に行うよう実装。
  - DuckDB を前提とした SQL クエリとトランザクション管理でデータ一貫性を確保。
  - 研究/戦略/実行/バックテスト間の依存を分離し、本番 API への直接アクセスを行わない設計（安全性の確保）。

Known issues / Notes / TODO
--------------------------
- apply_sector_cap における price 欠損（0.0）の場合、エクスポージャーが過少見積りされブロックが外れる可能性があると注記があり、将来的にフォールバック価格（前日終値や取得原価）を導入する余地がある。
- position_sizing では現状全銘柄共通の lot_size を仮定。将来的に銘柄別 lot_map を受け取る拡張が想定されている。
- signal_generator の一部エグジットルール（トレーリングストップ、時間決済）は positions テーブルに peak_price / entry_date が必要であり未実装。
- 一部ユーティリティ（例: kabusys.data.stats.zscore_normalize）は参照されているが本 changelog のコードスニペットでは定義ファイルが省略されているため、別ファイルでの実装がある前提。

Changed
-------
- 初回リリースのため該当なし。

Fixed
-----
- 初回リリースのため該当なし（.env パーサーなど堅牢化実装を含む初期実装を追加）。

Removed / Deprecated
--------------------
- 初回リリースのため該当なし。

ライセンスやリリース手順、以降のマイナーバージョンでの追加予定（例: execution 層の具体的な発注実装、モニタリング機能の追加、銘柄別 lot 対応、より細かい価格フォールバック戦略など）は README やドキュメントに別途まとめることを推奨します。