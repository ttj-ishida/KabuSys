Keep a Changelog
=================

すべての重要な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。

Unreleased
----------

- （なし）

[0.1.0] - 2026-03-26
--------------------

Added
- パッケージ初版リリース (バージョン 0.1.0)
  - パッケージ名: kabusys
  - エクスポート: data, strategy, execution, monitoring（トップレベル __all__）

- 設定 / 環境変数読み込み (kabusys.config)
  - .env/.env.local ファイルおよび OS 環境変数から設定を読み込む自動ロード機能を実装。
  - プロジェクトルート検出は __file__ を起点に .git または pyproject.toml を探索（CWD 非依存）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサに対して:
    - export KEY=val 形式対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応
    - コメントルールの柔軟な解釈（クォートの有無で挙動を切り替え）
  - 読み込み時の上書き制御（override, protected）をサポートし、既存 OS 環境変数の保護付き読み込みを実装。
  - Settings クラスを提供し、必須変数取得時に未設定で ValueError を送出するユーティリティを備える。
  - 各種設定プロパティ:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID を必須として取得
    - KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH のデフォルト値
    - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL の検証ロジック
    - is_live / is_paper / is_dev のブール補助プロパティ

- ポートフォリオ構築 (kabusys.portfolio)
  - 候補選定:
    - select_candidates: スコア降順、同点タイブレークに signal_rank を使用し上位 N を選択
  - ウェイト算出:
    - calc_equal_weights: 等金額配分
    - calc_score_weights: スコア加重。全スコアが 0 の場合は等金額にフォールバック（warning）
  - リスク調整:
    - apply_sector_cap: 既存保有のセクター別時価からセクター集中を検査し閾値超過セクターの新規候補を除外（"unknown" セクターは除外しない）
    - calc_regime_multiplier: 市場レジーム ("bull","neutral","bear") に応じた投下資金乗数を返す（未知レジームは 1.0 にフォールバック、warn ログ）
  - 株数決定:
    - calc_position_sizes:
      - allocation_method: "risk_based" / "equal" / "score" に対応
      - risk_based: 許容リスク率と stop_loss_pct から目標株数を算出
      - equal / score: ウェイトに基づく配分、per-position と aggregate の上限管理
      - 単元株（lot_size）で丸め、_max_per_stock による上限を適用
      - cost_buffer を用いた保守的コスト見積りと aggregate cap によるスケールダウン（スケールダウン後は端数を lot 単位で再配分）
      - 価格が欠損する銘柄はスキップし、適宜ログを出力

- 戦略 (kabusys.strategy)
  - 特徴量エンジニアリング (feature_engineering.build_features)
    - research の calc_momentum / calc_volatility / calc_value を呼び出して生ファクターを取得
    - ユニバースフィルタ: 株価 >= 300 円、20日平均売買代金 >= 5e8 円
    - 指定列を Z スコア正規化（kabusys.data.stats.zscore_normalize を使用）、±3 でクリップ
    - features テーブルへ日付単位の置換（冪等）でアップサート（トランザクションで原子性保証）
  - シグナル生成 (signal_generator.generate_signals)
    - features と ai_scores を統合し、component スコア(mom/value/volatility/liquidity/news) を計算
    - デフォルト重みを提供し、ユーザ渡し重みは検証・補完・正規化して適用
    - AI ニューススコア未登録時は中立値で補完
    - Bear レジーム判定機構を実装し、Bear の場合は BUY シグナルを抑制
    - BUY 判定は final_score >= threshold（デフォルト 0.60）
    - SELL 判定はストップロス（-8%）とスコア低下（threshold 未満）を実装。price 欠損時は判定スキップし警告ログ
    - signals テーブルへ日付単位の置換（冪等）で書き込み

- リサーチユーティリティ (kabusys.research)
  - ファクター計算 (factor_research)
    - calc_momentum: 1m/3m/6m リターン、MA200 乖離を計算（必要行数不足時は None）
    - calc_volatility: 20日 ATR、ATR/close、20日平均売買代金、出来高比率
    - calc_value: raw_financials から最新財務を取得し PER / ROE を計算（EPS=0 または欠損時は PER=None）
  - 特徴量解析 (feature_exploration)
    - calc_forward_returns: 指定ホライズン（デフォルト 1,5,21 営業日）に対する将来リターンを一括 SQL で取得
    - calc_ic: スピアマンのランク相関（IC）計算（有効レコード < 3 の場合は None）
    - factor_summary: count/mean/std/min/max/median を算出（None 値を除外）
    - rank: 同順位は平均ランクにするランク計算（round で丸めて ties の安定化を図る）

- バックテスト (kabusys.backtest)
  - metrics:
    - calc_metrics: DailySnapshot と TradeRecord から CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, total_trades を計算
    - 各内部計算は欠損・ゼロ除算に配慮して安全に 0.0 を返す仕様
  - simulator:
    - PortfolioSimulator クラス: メモリ内でのポートフォリオ状態・約定シミュレーションを提供
    - TradeRecord / DailySnapshot のデータモデル
    - execute_orders:
      - SELL を先に処理してから BUY（資金確保）
      - スリッページ（BUY +, SELL -）と手数料モデルを反映した約定価格/手数料計算
      - SELL は現状「全量クローズ」。部分利確/トレーリングストップ等は未実装
      - lot_size による丸め対応（日本株一般は 100）

Changed
- （初版のためなし）

Fixed
- （初版のためなし）

Deprecated
- （初版のためなし）

Removed
- （初版のためなし）

Security
- （初版のためなし）

Notes / Known limitations
- apply_sector_cap:
  - "unknown" セクターはセクター上限適用対象外（意図的）
  - price_map に price が欠損（0.0）だとエクスポージャーが過少見積りされうる（将来的にフォールバック価格を検討）
- signal_generator:
  - トレーリングストップ・時間決済などの一部エグジットロジックは未実装（positions テーブルに peak_price/entry_date が必要）
- calc_regime_multiplier:
  - 未知のレジームはログ出力のうえ 1.0 でフォールバック
- 全体:
  - DuckDB を用いるモジュールは接続とテーブルスキーマ（prices_daily, features, ai_scores, positions, raw_financials 等）を前提とする
  - 一部の実装は将来的な拡張（銘柄別 lot_size、手数料モデルの細分化、価格フォールバックなど）を想定して TODO コメントあり

開発者連絡
- 仕様や動作に不明点がある場合はソース内ドキュメント（docstring / コメント）を参照してください。