# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠し、慣例に従ってカテゴリ別（Added, Changed, Fixed, Security 等）で記載しています。

※以下は提供されたコードベースの内容から推測して作成した初期リリースの変更履歴です。

## [Unreleased]


## [0.1.0] - 2026-03-22
初回公開リリース。日本株自動売買システムのコアライブラリを実装。

### Added
- パッケージ基盤
  - kabusys パッケージを追加。公開 API として data, strategy, execution, monitoring を __all__ に設定。

- 環境設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
  - 自動 .env ロード機能を実装（プロジェクトルートは .git または pyproject.toml を探索して特定）。
  - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサを実装（export 形式対応、シングル/ダブルクォートのエスケープ、インラインコメントの扱いを考慮）。
  - OS 環境変数を保護する機構（読み込み時に protected set を用いて上書きを制御）。
  - Settings プロパティを実装:
    - JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / KABU_API_BASE_URL（デフォルト）などの必須/任意設定
    - Slack 関連設定（SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）
    - データベースパス（DUCKDB_PATH, SQLITE_PATH）のデフォルト
    - 環境（KABUSYS_ENV）の検証（development, paper_trading, live）
    - LOG_LEVEL の検証
    - is_live / is_paper / is_dev のユーティリティフラグ

- 戦略（strategy）モジュール
  - feature_engineering.build_features
    - research モジュールの生ファクター（momentum, volatility, value）を取得して統合。
    - ユニバースフィルタ（最低株価: 300 円、20日平均売買代金: 5億円）を実装。
    - 指定カラムを Z スコア正規化（zscore_normalize を利用）し ±3 でクリップ。
    - 日付単位の置換（DELETE→INSERT をトランザクションで行い冪等性を確保）で features テーブルを更新。
  - signal_generator.generate_signals
    - features と ai_scores を統合して銘柄ごとの final_score を算出。
    - コンポーネントスコア: momentum / value / volatility / liquidity / news（AIスコア）。
    - s_news は AI スコアが無い場合に中立（0.5）で補完。
    - 重み（defaults）を受け取り不正値を無視、合計を 1 に正規化。
    - Bear レジーム判定（ai_scores の regime_score 平均が負の場合、かつサンプル数閾値を満たす時に Bear と判定）により BUY を抑制。
    - SELL（エグジット）判定の実装:
      - ストップロス（終値 / avg_price - 1 <= -8%）
      - final_score が閾値未満（threshold デフォルト 0.60）
      - 保有銘柄で価格が欠損する場合は SELL 判定をスキップして警告ログを出力
    - SELL を優先して BUY から除外、signals テーブルへ日付単位の置換で書き込み（冪等）。

- リサーチ（research）モジュール
  - factor_research:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev を DuckDB SQL で計算。
    - calc_volatility: 20日 ATR（atr_20 / atr_pct）、avg_turnover、volume_ratio を計算。true_range 計算で NULL 伝播を適切に制御。
    - calc_value: raw_financials から直近財務を取得し PER / ROE を計算（EPS が 0/欠損のときは None）。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一クエリで取得。
    - calc_ic: スピアマンのランク相関（IC）を実装。データ不足（<3）時は None を返す。
    - factor_summary / rank: 基本統計量と同順位平均ランクのユーティリティ関数。
  - research パッケージは DuckDB 接続のみを参照し、外部ネットワークや発注 API にはアクセスしない設計。

- バックテスト（backtest）フレームワーク
  - simulator.PortfolioSimulator:
    - メモリ内でポートフォリオ状態を管理。BUY/SELL の擬似約定（始値ベース、スリッページ・手数料モデル適用）。
    - SELL は保有全量クローズ（部分利確未対応）。
    - mark_to_market で終値評価の DailySnapshot を記録。
    - TradeRecord / DailySnapshot のデータ構造を定義。
  - metrics.calc_metrics:
    - CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, トレード数などを計算するユーティリティを実装。
  - engine.run_backtest:
    - 本番 DuckDB からインメモリ DuckDB へ必要テーブル（prices_daily / features / ai_scores / market_regime / market_calendar）を日付範囲でコピーしてバックテスト接続を構築。
    - 日次ループで:
      1. 前日シグナルを当日始値で約定
      2. positions を DB に書き戻し（generate_signals の SELL 判定に必要）
      3. 終値で時価評価・スナップショット記録
      4. generate_signals を呼び出し翌日の signals を作成
      5. サイジングして翌日の買い注文を作成
    - バックテスト用コネクション構築は init_schema(":memory:") を利用し本番データを汚染しない。

### Fixed / Robustness
- 計算時の NaN / 無限大 / None への堅牢な対処を追加
  - 各種スコア計算で math.isfinite チェックを挿入し、非数値は無視または None 扱い。
  - シグモイド変換で OverflowError を捕捉して適切に 0/1 にフォールバック。
  - ファクター正規化・クリップ処理で None/非有限値に対する代替処理を追加。
- DB 書き込み時の原子性を確保
  - features / signals / positions の日付単位置換でトランザクション（BEGIN/COMMIT/ROLLBACK）を使用し、ROLLBACK 失敗のログ出力を追加。
- 売買ロジックの安全措置
  - BUY 約定時に手数料込みの再計算を行い現金不足を回避する処理を追加。
  - SELL / BUY で始値が取得できない場合のスキップと警告ログ。

### Security
- .env 読み込み時に OS 環境変数を保護する protected 機構を導入し、意図しない上書きを防止。
- 必須環境変数未設定時に ValueError を発生させることで安全な初期化を促進（JQUANTS_REFRESH_TOKEN など）。

### Notes
- 多くの SQL 処理は DuckDB 上で完結するよう設計。外部ライブラリ（pandas 等）に依存しない実装を志向。
- 一部設計仕様は外部ドキュメント（StrategyModel.md, BacktestFramework.md 等）に従っている旨のコメントが含まれる。
- 未実装／将来の拡張点（コード内コメント）:
  - トレーリングストップや時間決済などの追加エグジットルール。
  - PBR・配当利回り等のバリューファクター拡張。
  - execution 層（実取引）との連携実装（現状は発注 API への依存を持たない設計）。

---
（この CHANGELOG はソースコードの内容から推測して作成したものであり、実際のコミット履歴やリリースノートとは異なる場合があります。）