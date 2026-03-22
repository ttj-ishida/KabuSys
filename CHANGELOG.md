CHANGELOG
=========

すべての注目すべき変更は本ファイルに記録します。
フォーマットは "Keep a Changelog" に準拠し、セマンティック バージョニングを使用します。

[Unreleased]
------------

（なし）

[0.1.0] - 2026-03-22
-------------------

Added
- 初回公開。日本株自動売買ライブラリ "KabuSys" の基本機能を提供するパッケージを追加。
  - パッケージエントリポイント: kabusys.__version__ = "0.1.0"、主要サブモジュールを __all__ に公開。
- 環境設定管理（kabusys.config）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml 基準）から自動読み込み（OS 環境変数優先、.env.local は上書き）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動読み込みを無効化可能。
  - .env の行パーサーを実装（コメント、export プレフィックス、シングル/ダブルクォートとバックスラッシュエスケープ、インラインコメント処理に対応）。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 実行環境・ログレベルなどをプロパティ経由で取得。必須キー未設定時は ValueError を送出。
  - KABUSYS_ENV の許容値検証（development / paper_trading / live）や LOG_LEVEL 検証を実装。
- 戦略関連（kabusys.strategy）
  - feature_engineering.build_features
    - research 側で計算した生ファクターを読み込み、ユニバースフィルタ（最低株価・最低平均売買代金）適用、指定列の Z スコア正規化（±3 でクリップ）を行い、features テーブルに日付単位で冪等に書き込み。
    - 価格は target_date 以前の最新価格を参照してルックアヘッドを防止。
    - トランザクション＋バルク挿入で原子性を保証。ROLLBACK の失敗は警告。
  - signal_generator.generate_signals
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum / value / volatility / liquidity / news）を計算し、重み付き合算で final_score を算出。
    - デフォルト重み・閾値を内蔵（例: momentum=0.40, threshold=0.60）。ユーザ指定 weights は検証・スケーリングされる（不正なキーや非数値は無視）。
    - Bear レジーム判定（AI の regime_score の平均が負かどうか、サンプル閾値あり）で BUY を抑制。
    - 保有ポジションに対するエグジット判定（ストップロス -8% とスコア低下）を実装し、signals テーブルへ日付単位で冪等に書き込み。
    - SELL 優先ポリシー（SELL 対象は BUY から除外しランク再付与）。
- リサーチ関連（kabusys.research）
  - factor_research モジュール
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev を prices_daily から計算。データ不足時は None を許容。
    - calc_volatility: 20日 ATR（true range の取り扱いに注意）、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から target_date 以前の最新財務データを取得し PER / ROE を計算（EPS が 0 または欠損の場合は PER=None）。
  - feature_exploration モジュール
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。引数検証（1〜252 営業日）あり。
    - calc_ic: Spearman（ランク）相関による IC 計算。有効レコードが 3 件未満の場合は None を返す。
    - factor_summary / rank: 基本統計量の計算、同順位は平均ランクで処理。標準ライブラリのみで実装（pandas 等に非依存）。
  - research パッケージは主要関数を __all__ で公開。
- バックテスト（kabusys.backtest）
  - simulator.PortfolioSimulator
    - メモリ内での約定処理、資金・保有・平均取得単価管理、約定記録（TradeRecord）を保持。
    - execute_orders: 当日始値で擬似約定（SELL 先行、SELL は全量クローズ）。スリッページ・手数料モデルを適用し、手数料込みで株数再計算。
    - mark_to_market: 終値で時価評価し DailySnapshot を記録。終値欠損時は 0 評価で警告。
  - metrics.calc_metrics
    - CAGR / Sharpe / Max Drawdown / Win Rate / Payoff Ratio / トレード数を計算するユーティリティを提供。
  - engine.run_backtest
    - 本番 DB からインメモリ DuckDB へデータをコピーしてバックテストを実行するフローを提供。
    - signals の生成 → 約定 → positions の書き戻し → マーク・トゥ・マーケット → 翌日シグナル生成 のループを実装。
    - _build_backtest_conn により必要テーブルを日付範囲でフィルタしてコピー（market_calendar は全件コピー）、コピー時の失敗は警告でスキップ。
    - positions の書き戻し（冪等な DELETE + INSERT）や signals 読み取りヘルパーを提供。
  - backtest パッケージは run_backtest / BacktestResult / DailySnapshot / TradeRecord / BacktestMetrics を公開。
- パッケージ設計方針（ドキュメント記載の挙動を実装）
  - ルックアヘッドバイアスを防ぐため target_date までのデータのみ参照する実装方針を徹底。
  - 発注 API への直接依存を持たない（execution 層との分離）。
  - DuckDB をデータバックエンドとして使用。トランザクションとバルク挿入により原子性を確保。
  - ロギングを随所に追加し、警告や情報を適切に出力。

Changed
- 該当なし（初回リリース）。

Fixed
- .env ファイル読み込み時のエラーを警告に変換して処理継続（ファイル読み込み失敗で例外を投げず自動ロードをスキップ可能）。
- DB 書き込み時のトランザクションエラー発生時に ROLLBACK を試行し、ROLLBACK 自身の失敗は警告ログを出すことで予期せぬ例外情報を補足。

Deprecated
- 該当なし。

Removed
- 該当なし。

Security
- 該当なし。

Notes
- 一部ユーティリティ（例: zscore_normalize）は kabusys.data.stats から呼び出されることを前提としている（本差分には実装の参照あり）。
- 実稼働での使用時は必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）を .env に設定すること。Settings._require により未設定の場合は ValueError が発生する。