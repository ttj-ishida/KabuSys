# CHANGELOG

すべての注目すべき変更を記録します。  
フォーマットは "Keep a Changelog" に準拠しています。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-22

初期リリース。日本株自動売買システム "KabuSys" のコア機能を実装しました。以下はコードベースから推測してまとめた主要な追加点・設計上の注意点です。

### 追加（Added）
- パッケージ基盤
  - パッケージルート: kabusys（バージョン: 0.1.0）。
  - __all__ に data/strategy/execution/monitoring をエクスポート。

- 環境設定管理（kabusys.config）
  - .env / .env.local ファイルと OS 環境変数の統合読み込みを実装。
  - プロジェクトルート判定: .git または pyproject.toml を基準に探索（CWD に依存しない）。
  - 自動ロードの無効化: 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で抑制可能。
  - .env パーサ: 'export KEY=val' 形式、シングル/ダブルクォートとバックスラッシュエスケープ、インラインコメント処理、無効行スキップに対応。
  - 読み込み優先度: OS 環境変数 > .env.local > .env。OS 環境変数は protected として上書き抑止。
  - Settings クラスを提供（プロパティ経由で設定取得）。
    - J-Quants / kabuAPI / Slack / DB パスなどの設定項目を定義。
    - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL のバリデーション。
    - convenience プロパティ: is_live / is_paper / is_dev。

- リサーチ（kabusys.research）
  - factor_research: モメンタム / ボラティリティ / バリュー系ファクター計算を実装。
    - calc_momentum: mom_1m/mom_3m/mom_6m, ma200_dev（200日移動平均乖離）を計算。
    - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio を計算（true_range の欠損取り扱いに注意）。
    - calc_value: latest 財務情報を用いた per / roe 計算（raw_financials と prices_daily を参照）。
  - feature_exploration:
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを計算。
    - calc_ic: Spearman（ランク）相関による IC 計算を実装（最小サンプル数チェックあり）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を算出。
    - rank: 同順位を平均ランクで処理（round で丸めて ties 対応）。

  - research パッケージの __all__ に主要関数をエクスポート。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - build_features(conn, target_date)
    - research モジュールの calc_momentum/calc_volatility/calc_value を組み合わせて features を作成。
    - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 >= 5 億円）を実装。
    - Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）、±3 でクリップして外れ値を抑制。
    - 日付単位の置換（DELETE -> INSERT）をトランザクションで行い冪等性を確保。

- シグナル生成（kabusys.strategy.signal_generator）
  - generate_signals(conn, target_date, threshold=0.60, weights=None)
    - features と ai_scores を統合して各銘柄の final_score を計算。
    - コンポーネントスコア: momentum / value / volatility / liquidity / news。
    - デフォルト重み: momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10（外部から weights を与え可能。無効値はスキップし正規化）。
    - final_score の閾値による BUY 生成（デフォルト 0.60）。
    - Bear レジーム判定（ai_scores の regime_score 平均が負でサンプル数閾値を満たす場合）により BUY を抑制。
    - 保有ポジションに対するエグジット（SELL）条件を実装（ストップロス -8% / スコア低下）。
    - SELL 優先ポリシー: SELL 対象は BUY から除外、signals テーブルへ日付単位の置換で書き込み（トランザクション）。

- バックテスト（kabusys.backtest）
  - simulator: PortfolioSimulator（メモリ内シミュレータ）
    - execute_orders: SELL を先に処理、SELL は全量クローズ、BUY は alloc に基づいて購入（スリッページ・手数料を考慮）。
    - マーク・ツー・マーケットと DailySnapshot の記録。
    - TradeRecord / DailySnapshot のデータクラスを提供。
  - engine:
    - run_backtest(conn, start_date, end_date, ...) を実装。
    - 本番 DB からインメモリ DuckDB へ必要テーブルをコピー（データ範囲フィルタと market_calendar 全件コピー）。
    - 日次ループ: 約定（open price） → positions 書き戻し → 時価評価 → generate_signals 呼び出し → 発注リスト作成 → 次日の約定 という流れを実装。
    - positions 書き戻しは冪等に動作（当日分を DELETE -> INSERT）。
  - metrics:
    - バックテスト評価指標を計算（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, Total Trades）。

- パッケージエクスポート
  - backtest / strategy の主要 API を __all__ で公開。

### 変更（Changed）
- （初版のため大きな差分はなし）ただし設計方針として下記が明記されている点を記載：
  - ルックアヘッドバイアス防止: すべての計算は target_date 時点（および過去データ）に基づく。
  - 発注 API / 実行層への直接依存排除: strategy 層は発注処理に依存しない設計。
  - DuckDB を用いた SQL + Python の混合実装でデータ解析・集計を行う。

### 修正（Fixed）
- 明示的なバグ修正履歴は初回リリースにつきなし。ただし実装上の安全策・例外処理を各所に導入：
  - .env 読み込み失敗時は warnings.warn を発行して処理継続。
  - DB トランザクション内で例外発生時に ROLLBACK 試行と警告ログ出力。
  - 欠損データ（NULL/NaN/Inf）に対する頑健な取り扱い（多くの関数で math.isfinite チェック）。

### 注意 / 未実装 / 設計メモ（Notes）
- signal_generator の SELL 条件として「トレーリングストップ」「時間決済（保有 60 営業日超過）」は未実装（positions テーブルに peak_price / entry_date 等の拡張が必要）。
- calc_value は PER / ROE を実装しているが PBR・配当利回りは未実装。
- backtest._build_backtest_conn はコピー時に失敗したテーブルをスキップして警告を出す設計（堅牢性重視）。
- simulator の売買は整数株数に丸め（math.floor）しており、部分株はサポートしない。
- mark_to_market で終値が存在しない銘柄は 0 で評価し警告を出す。
- zscore_normalize は別モジュール（kabusys.data.stats）に依存。正規化列は戦略側で定義（_NORM_COLS）。
- AI スコア（ai_scores）が未登録の銘柄は中立（0.5）で補完される設計。
- 環境設定は必須キーが未設定の場合 ValueError を送出する（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN 等）。

---

今後のリリースでは、実運用向けの execution 層統合、追加のリスク管理ルール、各種メトリクス拡張、ドキュメント（StrategyModel.md / BacktestFramework.md 等）の実装との整合性チェックが想定されます。