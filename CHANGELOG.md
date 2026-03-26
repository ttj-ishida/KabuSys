CHANGELOG
=========

All notable changes to this project will be documented in this file.

フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを採用します。

v0.1.0 — 2026-03-26
-------------------

Added
- 基本パッケージ初期実装（初回リリース）。
  - src/kabusys/__init__.py
    - パッケージ メタ情報（__version__ = 0.1.0）と主要サブパッケージの公開定義。
- 環境変数 / 設定管理
  - src/kabusys/config.py
    - .env ファイル（.env, .env.local）と OS 環境変数の自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml）。
    - export KEY=val 形式やクォート内のエスケープ、行コメントの取り扱いに対応したパーサ実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 による自動ロード無効化オプション。
    - Settings クラスを導入し、J-Quants / kabu ステーション / Slack / DB パス / 環境モード / ログレベル等の取得メソッドを提供。
    - env と log_level の値検証（許容値以外は ValueError を送出）。
- ポートフォリオ構築（選定・配分・リスク調整・株数算出）
  - src/kabusys/portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコアでソートして上位 N を選択（タイブレークは signal_rank）。
    - calc_equal_weights: 等金額配分の重み算出。
    - calc_score_weights: スコア加重配分（合計スコアが0のときは等金額へフォールバック、警告ログ出力）。
  - src/kabusys/portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェック（既存保有の時価ベースで算出、sell 対象は除外）。
      - "unknown" セクターは上限チェック対象外。
      - price 欠損時の注意点（将来的なフォールバックの TODO を注記）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を提供（未知レジームは 1.0 でフォールバックし警告を出力）。
  - src/kabusys/portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた発注株数算出。
      - risk_based: 許容リスク率・ストップロスを元にポジションサイズを算出。
      - equal/score: 重みに基づく配分、lot_size による丸め、各種上限（per-position, aggregate）考慮。
      - cost_buffer を用いた保守的な約定コスト見積りと aggregate cap 時のスケールダウン処理（切捨て・端数の lot サイズ順配分ロジックを実装）。
- 戦略（特徴量生成・シグナル生成）
  - src/kabusys/strategy/feature_engineering.py
    - build_features: research の生ファクターを取り込み、ユニバースフィルタ（最低株価・最低平均売買代金）、Zスコア正規化（±3 クリップ）、features テーブルへの日付単位の置換（冪等）を実装。
    - ユニバース基準: 最低株価 300 円、20日平均売買代金 5 億円。
  - src/kabusys/strategy/signal_generator.py
    - generate_signals: features と ai_scores を統合し、モメンタム/バリュー/ボラティリティ/流動性/ニュースのコンポーネントスコアを重み付き合算して final_score を計算。
      - デフォルト重み（momentum:0.40, value:0.20, volatility:0.15, liquidity:0.15, news:0.10）と閾値（0.60）。
      - AI スコア未登録銘柄の扱い（news は中立、features 未存在銘柄は final_score=0 として SELL 判定の対象に）。
      - Bear レジーム判定により BUY シグナル抑制（ai_scores の regime_score 平均が負かつサンプル数 >= 3 の場合）。
      - エグジット判定（stop_loss: -8% 以下、score_drop: final_score < threshold）。
      - signals テーブルへの日付単位置換（トランザクション + バルク挿入）。
- リサーチ / ファクター
  - src/kabusys/research/factor_research.py
    - calc_momentum: mom_1m/3m/6m と ma200_dev を計算（ウィンドウ不足時は None）。
    - calc_volatility: 20日 ATR / atr_pct / avg_turnover / volume_ratio を計算（true_range の NULL 伝播を制御）。
    - calc_value: raw_financials から最新財務を結合して PER / ROE を計算（EPS が 0/欠損のときは None）。
  - src/kabusys/research/feature_exploration.py
    - calc_forward_returns: 複数ホライズン（デフォルト 1/5/21）に対する将来リターンを一度のクエリで取得。
    - calc_ic: スピアマンのランク相関（IC）計算（有効サンプル < 3 の場合は None）。
    - factor_summary / rank: 基本統計量・ランク変換ユーティリティを提供。
  - src/kabusys/research/__init__.py にて主要関数を公開。
- バックテスト
  - src/kabusys/backtest/simulator.py
    - PortfolioSimulator: 擬似約定・ポジション管理機能（メモリ内）。
      - execute_orders: SELL を先に処理し全量クローズ（部分利確非対応）。BUY は指定株数で約定。スリッページ/手数料を適用した TradeRecord を記録。
      - DailySnapshot / TradeRecord の dataclass 定義。
  - src/kabusys/backtest/metrics.py
    - バックテスト評価指標計算（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, Total Trades）。
    - inputs は DailySnapshot と TradeRecord のみ（DB 参照なし）。
- パッケージエクスポート
  - strategy, research, portfolio など主要 API を __init__ 経由で公開（関数単位エクスポート）。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Security
- 環境変数の自動ロード時に既存 OS 環境変数を保護する仕組み（protected set）を追加。これによりシステム環境変数が .env により意図せず上書きされることを防止。

Known limitations / Notes
- apply_sector_cap: price_map に価格が欠損（0.0）だとエクスポージャーが過少評価され、セクター制限が適切に働かない可能性がある（将来的に前日終値や取得原価でのフォールバックを検討）。
- calc_value: PBR や配当利回りは現バージョンでは未実装。
- generate_signals: Bear レジーム時に BUY シグナルは抑制される設計（StrategyModel.md に基づく）。Bear 判定は ai_scores の regime_score に依存するため、ai_scores 未登録やサンプル不足時は誤検知を避けるため Bear 判定を行わない。
- PortfolioSimulator._execute_buy の lot_size ロジックは日本株向けの 100 単位想定（コード中に TODO が存在）。
- 一部機能は将来的な拡張を想定した TODO コメントを含む（例: 銘柄別 lot_size、フォールバック価格の導入、トレーリングストップ等）。
- DuckDB を前提とした SQL 実装（prices_daily / features / ai_scores / raw_financials / positions 等のテーブルスキーマを前提）。

Notes for users
- .env.example を参考に必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）を用意してください。Settings のプロパティは未設定時に ValueError を送出します。
- 自動 .env 読み込みを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

Acknowledgements
- ドキュメント内の参照（PortfolioConstruction.md, StrategyModel.md, BacktestFramework.md 等）は実装設計の根拠です（リポジトリ内に同名ドキュメントがある想定）。

---- 

（以上、v0.1.0 のリリースノート）