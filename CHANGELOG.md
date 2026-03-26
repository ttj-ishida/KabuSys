Keep a Changelog に準拠した CHANGELOG.md（日本語）
※コードベースから推測した主要な変更点・機能説明を記載しています。

全ての重要な変更はここに記録します。フォーマットは Keep a Changelog に準拠しています。

未リリース: 0.1.0 (初回公開)
=================================
リリース日: 2026-03-26

Added
-----
- 基本パッケージ初期実装を追加。
  - パッケージメタ情報: kabusys.__version__ = 0.1.0、パッケージ公開 API を __all__ で定義。

- 環境設定・自動 .env 読み込み (kabusys.config)
  - .env / .env.local の自動読み込みをプロジェクトルート（.git または pyproject.toml）から行う仕組みを実装。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。OS 環境変数は保護（上書き不可）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読込を無効化可能（テスト向け）。
  - .env のパースは:
    - 空行・コメント行（#）を無視
    - export KEY=val 形式に対応
    - シングル/ダブルクォート内のバックスラッシュエスケープに対応
    - クォートなしの場合の行内コメントの取り扱いを改善
  - Settings クラスを提供し、必須環境変数取得（_require）や各種既定値・バリデーションを実装:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID などの必須取得
    - DB パス（DUCKDB_PATH / SQLITE_PATH）の既定値と Path 変換
    - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL の検証メソッド（is_live 等）を追加

- ポートフォリオ構築機能 (kabusys.portfolio)
  - portfolio_builder:
    - select_candidates: BUY シグナルを score 降順（同点は signal_rank でタイブレーク）で選択。
    - calc_equal_weights: 等金額配分を計算。
    - calc_score_weights: スコア加重配分を計算。全スコアが 0 の場合は等配分にフォールバックし警告。
  - risk_adjustment:
    - apply_sector_cap: セクター集中上限（max_sector_pct）をチェックし、上限を超えるセクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market regime（"bull","neutral","bear"）に応じた投下資金乗数を返す（未知レジームは警告後 1.0 フォールバック）。
  - position_sizing:
    - calc_position_sizes: allocation_method("risk_based"/"equal"/"score") に従い発注株数を計算。
      - risk_based: リスク（risk_pct）と stop_loss_pct からベース株数を計算、単元（lot_size）で丸め。
      - equal/score: weights に基づく配分、per-position 上限（max_position_pct）と aggregate cap（available_cash / portfolio_value * max_utilization）を考慮。
      - cost_buffer を用いた保守的コスト見積→ aggregate スケーリング（スケールダウン）を実装。スケーリング後に lot_size 単位で残差配分を行うロジックを含む。
      - 価格欠損時は当該銘柄をスキップし debug ログ出力。

- 戦略（feature / signal）モジュール (kabusys.strategy)
  - feature_engineering.build_features:
    - research モジュール（calc_momentum/calc_volatility/calc_value）から生ファクターを取得しマージ。
    - ユニバースフィルタ（最低株価 _MIN_PRICE=300 円、20日平均売買代金 _MIN_TURNOVER=5e8）を適用。
    - 指定列を Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）し ±3 でクリップ。
    - features テーブルへ日付単位で置換（DELETE + INSERT）のトランザクション処理で原子性を確保。
  - signal_generator.generate_signals:
    - features と ai_scores を統合して各銘柄の履歴スコア（momentum/value/volatility/liquidity/news）を計算し final_score を求める（既定重みあり）。
    - weights の入力検証と正常化（既知キーのみ受け付け、負値・非数は無視、合計が 1.0 に再スケール）。
    - AI の regime_score を集計して Bear レジーム判定（サンプル閾値あり）。Bear の場合は BUY シグナルを抑制。
    - BUY シグナル閾値（デフォルト 0.60）を超える銘柄を BUY 候補に、SELL はエグジット条件（ストップロス -8% / final_score の閾値未満）で生成。
    - price 欠損や features 未登録時のフォールバック動作（警告ログ）を明示。
    - signals テーブルへ日付単位で置換（トランザクション処理）。

- リサーチユーティリティ (kabusys.research)
  - factor_research:
    - calc_momentum: mom_1m/mom_3m/mom_6m と ma200_dev（200日 MA）を計算。必要な行数不足時は None を返す。
    - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio を計算。true_range の NULL 伝播を適切に扱う。
    - calc_value: raw_financials から最新財務（report_date <= target_date）を取得し PER/ROE を計算（EPS=0 等は None）。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）に対する将来リターンを一括 SQL で取得。
    - calc_ic: factor と forward return を code で結合して Spearman の ρ（ランク相関）を計算。有効レコードが 3 未満なら None。
    - rank: 値リストを同順位平均ランクで返す（round による tie 管理）。
    - factor_summary: count/mean/std/min/max/median を算出。

- バックテスト (kabusys.backtest)
  - metrics:
    - BacktestMetrics dataclass と calc_metrics を実装（CAGR, Sharpe, Max Drawdown, Win rate, Payoff ratio, total trades）。
    - 各内部計算関数（_calc_cagr, _calc_sharpe, _calc_max_drawdown, _calc_win_rate, _calc_payoff_ratio）を実装。
  - simulator:
    - DailySnapshot / TradeRecord dataclass を定義。
    - PortfolioSimulator: メモリ内でポートフォリオ状態を管理するシミュレータを実装。
      - execute_orders: SELL を先行、BUY を後処理する約定フロー。スリッページ率および手数料率を適用。部分約定や単元 lot_size の扱いをサポート。
      - BUY/SELL の詳細な約定ロジック（平均取得単価更新、現金・ポジション更新、TradeRecord 作成）を実装（途中までの実装を含むファイル）。

- パッケージの __init__ / export 整理
  - kabusys.portfolio / kabusys.strategy / kabusys.research の __all__ に主要 API を追加してパブリックインターフェースを整備。

Changed
-------
- （初期リリースのため該当なし）

Fixed
-----
- 各モジュールでの入力欠損に対する保護を追加（価格欠損時にスキップして警告ログを出す、None のコンポーネントを中立値 0.5 で補完する等）。
- SQL クエリでの NULL 扱いやウィンドウ集計の境界条件を慎重にコントロール（例: true_range が NULL の場合の ATR カウント等）。

Deprecated
----------
- （初期リリースのため該当なし）

Removed
-------
- （初期リリースのため該当なし）

Security
--------
- （特にセキュリティ修正は含まれず）

Known issues / TODO
-------------------
- apply_sector_cap 内で price_map に 0.0 が来た場合、エクスポージャーが過小評価される可能性がある旨をコメントで指摘。将来的に前日終値や取得原価をフォールバックすることを検討。
- signal_generator の未実装ロジック：トレーリングストップや時間決済（positions テーブルに peak_price / entry_date が必要）。
- PortfolioSimulator ファイルは約定ロジック実装が途中で終わっている箇所あり（_execute_buy の続きが未表示）。単体テストでの追加検証が必要。
- 個別銘柄の lot_size を銘柄マスタから取得する拡張（現在はグローバルな lot_size を想定）。

開発者向けメモ
---------------
- 設定・環境変数の自動読み込みは配布後も正しく動作するよう __file__ ベースでプロジェクトルートを探索する設計。CWD に依存しない。
- strategy と research 層はルックアヘッドバイアスを避けるため target_date 時点のデータのみを参照する方針で実装。
- DB 書き込み（features / signals）は日付単位での置換（DELETE → INSERT）をトランザクションで行い冪等性と原子性を保証。

以上がコードベースから推測できる主な変更点・機能です。必要に応じてリリース日や細かな文言を調整してください。