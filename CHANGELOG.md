# Changelog

すべての変更は Keep a Changelog のフォーマットに準拠して記載しています。  
現在のバージョン: 0.1.0

## [0.1.0] - 2026-03-22

初回リリース。日本株自動売買システム「KabuSys」のコア機能を提供します。

### 追加 (Added)
- パッケージ構成
  - kabusys パッケージを提供。サブパッケージとして data, strategy, execution, monitoring を公開する初期 API を定義。
  - バージョン情報: 0.1.0。

- 環境設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
  - 自動ロード機能:
    - プロジェクトルート（.git または pyproject.toml）を探索して .env / .env.local を自動で読み込む（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - OS 環境変数を保護する仕組み（読み込み時の protected セット）を実装。
  - .env パーサーを独自実装:
    - export KEY=... 形式対応、シングル/ダブルクォート内のエスケープ処理、コメント取り扱いを考慮した堅牢なパース処理を実装。
  - 必須設定取得用のヘルパー _require と各種プロパティ（J-Quants / kabuAPI / Slack / DB パス / 環境・ログレベル判定等）を提供。
  - KABUSYS_ENV / LOG_LEVEL のバリデーション実装。is_live/is_paper/is_dev のユーティリティを追加。

- 研究用ファクター計算 (kabusys.research)
  - factor_research モジュール:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率を計算。
    - calc_volatility: 20日 ATR、相対 ATR (atr_pct)、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を算出（最新報告書を銘柄ごとに取得）。
  - feature_exploration モジュール:
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。
    - calc_ic: スピアマンのランク相関（IC）を計算するユーティリティ。
    - factor_summary: 基本統計量（count/mean/std/min/max/median）を算出。
    - rank: 同順位に平均ランクを割り当てるランク関数。
  - research パッケージの __all__ に主要関数をエクスポート。

- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - build_features(conn, target_date):
    - research 側で計算した生ファクターをマージ、ユニバースフィルタ（株価 >= 300 円、20日平均売買代金 >= 5億円）を適用。
    - 指定カラムを Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）、±3 でクリップ。
    - features テーブルへ日付単位で置換（DELETE + INSERT）し冪等性を担保。トランザクション処理を採用。

- シグナル生成 (kabusys.strategy.signal_generator)
  - generate_signals(conn, target_date, threshold=0.6, weights=None):
    - features と ai_scores を統合してコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - 各コンポーネントの算出ロジックを実装（シグモイド変換、PER のスケーリング、atr_pct の反転等）。
    - デフォルト重みを定義し、ユーザ指定 weights のバリデーション・補正（既知キーのみ、非数値や負値は無視、合計を1.0に再スケール）を実装。
    - Bear レジーム判定: ai_scores の regime_score の平均が負かつ十分なサンプル数がある場合は BUY を抑制。
    - BUY シグナル閾値デフォルト 0.60、ランク付けと signal_rank を付与。
    - SELL シグナル生成ロジック（ストップロス: -8% 以下、final_score < threshold）を実装。保有銘柄の価格欠損時の挙動を警告ログで明示。
    - signals テーブルへ日付単位で置換（トランザクション + バルク挿入）して冪等性を担保。

- バックテストフレームワーク (kabusys.backtest)
  - simulator モジュール:
    - PortfolioSimulator: 現金・保有・平均取得単価・トレード履歴の管理。
    - 約定ロジック（execute_orders）: SELL を先に処理し BUY を後に処理、スリッページ率・手数料率を反映、BUY は配分(alloc) に基づき株数端数切捨て、部分約定調整、約定記録の保存。
    - mark_to_market: 終値で評価し DailySnapshot を記録（価格欠損時は 0 評価かつ警告）。
    - TradeRecord / DailySnapshot のデータクラスを公開。
  - metrics モジュール:
    - calc_metrics: history と trades から BacktestMetrics を計算して返す。
    - 個別指標: CAGR、Sharpe、Max Drawdown、Win Rate、Payoff Ratio、total_trades の実装。各内部計算関数を分離して実装。
  - engine モジュール:
    - run_backtest(conn, start_date, end_date, ...):
      - 本番 DB からインメモリ DuckDB にデータを部分コピーしてバックテスト用接続を構築（signals/positions を汚染しない）。
      - 日次ループ: 前日シグナルの約定 → positions 書き戻し → 終値で評価 → generate_signals 実行 → 発注リスト組成（ポジションサイジング）という流れを実装。
      - 市場カレンダー・価格取得ユーティリティや positions の冪等書き込みを提供。
      - デフォルトのスリッページ(0.1%)、手数料(0.055%)、1銘柄最大比率 20% を採用。

- トランザクションとエラーハンドリング
  - features / signals への書き込みはトランザクション（BEGIN/COMMIT/ROLLBACK）とバルク挿入を利用して原子性を担保。ROLLBACK 失敗時は警告ログを出力。

- 実装方針明記
  - ルックアヘッドを避けるため target_date 時点のデータのみを使用する設計。
  - 本番口座/発注 API へは依存しない（DB とローカル処理のみ）。
  - 研究モジュールは外部ライブラリに依存せず標準ライブラリ + DuckDB のみで動作する設計。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### 既知の制限・未実装 (Known issues / Not implemented)
- signal_generator 内のエグジット条件で、以下の条件は未実装（要 positions テーブルの拡張: peak_price / entry_date 等）:
  - トレーリングストップ（最高値から -10%）
  - 時間決済（保有 60 営業日超過）
- calc_value は現時点で PBR や配当利回りを計算しない（未実装）。
- research モジュールは DuckDB の prices_daily / raw_financials の品質に依存する。
- execution / monitoring サブパッケージは初期骨格のみで、kabuステーション等への実行系インテグレーションは別途実装が必要。

### セキュリティ
- 環境変数の自動読み込みはデフォルトで有効。テストや特殊環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して自動ロードを無効化可能。

---

今後の予定（例）
- execution 層と実際の発注 API（kabuステーション）との接続実装。
- ポジション管理の拡張（peak_price / entry_date）、トレーリングストップ・時間決済の実装。
- モニタリング（Slack 通知等）機能の強化。