CHANGELOG
=========

すべての重要な変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」の慣例に従います。  

なお、本履歴は与えられたコードベースの内容から実装状況・機能を推測して作成しています（実際のコミット履歴ではありません）。

Unreleased
----------
- 今後のリリースでの作業候補（コード内の TODO / 制限事項に基づく）
  - position_sizing: 銘柄別の単元情報 (lot_map) を受け取る設計への拡張
  - price フォールバック: price_map に価格がない場合の前日終値や取得原価などの利用
  - strategy のトレーリングストップ／時間決済の実装（positions に peak_price / entry_date 情報が必要）
  - execution パッケージの実装補完（発注 API 連携や実行ロジックの追加）
  - PortfolioSimulator._execute_buy の残り実装確認（提供されたコードは途中で終了）

[0.1.0] - 2026-03-26
--------------------
Added
- 基本パッケージ構成を追加
  - パッケージ名: kabusys
  - バージョン: 0.1.0（src/kabusys/__init__.py）
  - エクスポート: data, strategy, execution, monitoring（__all__）

- 環境設定管理 (kabusys.config)
  - .env ファイルまたは OS 環境変数から設定を読み込む自動ロードを実装
    - プロジェクトルートは .git または pyproject.toml を基準に探索して決定
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能
  - .env パーサを実装（export プレフィックス、クォート、エスケープ、行内コメント処理に対応）
  - Settings クラスを実装し、必須項目取得（_require）や各種設定プロパティを提供
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など必須チェック
    - duckdb/sqlite のデフォルトパス、環境（development/paper_trading/live）や log_level の検証ユーティリティ
    - is_live / is_paper / is_dev のヘルパー

- ポートフォリオ構築モジュール (kabusys.portfolio)
  - 候補選定・重み計算 (portfolio_builder)
    - select_candidates: スコア降順＋signal_rank タイブレークで上位 N を選択
    - calc_equal_weights: 等金額配分を計算
    - calc_score_weights: スコア加重配分（全銘柄スコア 0 の場合は等配分にフォールバック）
  - リスク調整 (risk_adjustment)
    - apply_sector_cap: 既存保有のセクター集中を計算し、上限超過セクターの新規候補を除外
      - sell_codes を除外して当日売却予定銘柄を露出計算から除外可能
      - "unknown" セクターはセクター上限適用対象外
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear のマッピングとフォールバック）
  - ポジションサイズ算出 (position_sizing)
    - calc_position_sizes: allocation_method("risk_based"/"equal"/"score") に応じた発注株数計算
      - 単元丸め（lot_size）、1銘柄上限(max_position_pct)、aggregate cap（available_cash）、
        cost_buffer（手数料・スリッページの保守的見積）を考慮したスケーリングロジック実装
      - risk_based の場合は risk_pct と stop_loss_pct を用いた株数算出
      - aggregate スケールダウン時に端数（lot 単位）の再配分ロジックを実装

- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - build_features: research モジュールから取得した raw ファクターを結合・ユニバースフィルタ・Z スコア正規化・±3 クリップし、features テーブルへ UPSERT（トランザクション）するフローを実装
  - ユニバースフィルタ条件（株価 >= 300 円、20日平均売買代金 >= 5億円）を実装
  - Z スコア正規化は kabusys.data.stats.zscore_normalize を利用

- シグナル生成 (kabusys.strategy.signal_generator)
  - generate_signals: features と ai_scores を統合して final_score を計算し、BUY/SELL シグナルを生成して signals テーブルへ日付単位で置換（トランザクション）
    - コンポーネントスコア: momentum, value(per), volatility(atr), liquidity(volume_ratio), news(AI スコア)
    - デフォルト重み設定とユーザ指定 weights の検証・正規化ロジック
    - Sigmoid 変換、欠損コンポーネントは中立 0.5 で補完
    - Bear レジーム検出による BUY 抑制（AI の regime_score を集計）
    - SELL 判定ロジック（ストップロス / final_score の閾値割れ）
    - SELL を優先して BUY から除外するポリシー
    - ログ出力（欠損データや警告）

- 研究用モジュール (kabusys.research)
  - factor_research: calc_momentum, calc_volatility, calc_value の実装
    - momentum: mom_1m/3m/6m、ma200_dev（200日移動平均乖離）
    - volatility: atr_20、atr_pct、avg_turnover、volume_ratio（20日）を計算
    - value: raw_financials から最新財務を取得し per/roe を算出
  - feature_exploration: calc_forward_returns（複数ホライズンまとめて取得）、calc_ic（スピアマン ρ の実装）、factor_summary（基本統計）、rank（同順位は平均ランク）
  - 研究モジュールは外部依存を避け、DuckDB 経由で prices_daily / raw_financials のみ参照する設計

- バックテスト (kabusys.backtest)
  - simulator: PortfolioSimulator（メモリ内ポートフォリオ状態管理）
    - DailySnapshot, TradeRecord の dataclass 定義
    - execute_orders: SELL を先、BUY を後で処理。スリッページ・手数料モデルを反映。SELL は全量クローズ（部分利確非対応）
    - 取引記録（TradeRecord）と履歴（DailySnapshot）の管理
  - metrics: バックテスト評価指標計算
    - CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, total_trades を計算する calc_metrics 実装

Changed
- 初版リリースのため該当なし

Fixed
- 初版リリースのため該当なし

Security
- 初版リリースのため該当なし

Notes / Known limitations
- position_sizing: price が欠損 (0.0) の場合、エクスポージャーや target_shares の計算が過少評価される可能性がある（コード内で注記あり）。将来的に価格フォールバックを導入予定。
- calc_regime_multiplier: 未知のレジームは 1.0 でフォールバックし警告を出力する設計。
- generate_signals:
  - features が空の場合は BUY シグナルは生成されず、SELL 判定のみ行う。
  - features に存在しない保有銘柄は final_score=0.0 扱いで SELL 対象になりうる。
  - AI スコアが未登録の銘柄は news コンポーネントを中立扱いにする（0.5 補完）。
- _generate_sell_signals: 価格が取得できない保有銘柄は SELL 判定自体をスキップ（誤クローズ防止）。
- PortfolioSimulator:
  - SELL は保有全量をクローズする仕様（部分決済やトレードごとの平均取得単価更新ロジックの拡張は未実装／要検討）。
  - provided code の一部（_execute_buy の続き）が途切れている可能性があるため、本番利用前に実装完了の確認が必要。
- execution パッケージ（kabusys.execution）は現状プレースホルダ（実装未提供）で、実際の発注 API 連携は未実装。

ライセンス・その他
- 本 CHANGELOG は実装内容の説明を目的とする推測ベースの記述です。実際のコミットログやリリースノートはリポジトリの履歴を参照してください。