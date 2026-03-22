# CHANGELOG

すべての注目すべき変更点を記録します。  
フォーマットは Keep a Changelog に準拠します。  

最新リリース: [0.1.0] — 2026-03-22

## [Unreleased]
- 次回リリースに向けた変更点はここに記載します。

## [0.1.0] - 2026-03-22
初回リリース。本リポジトリの基礎機能を実装しています。主な追加点および挙動は以下の通りです。

### Added
- パッケージ基礎
  - kabusys パッケージの初期公開（__version__ = 0.1.0）。
  - 公開 API モジュールエクスポート（strategy, execution, monitoring, data 等を想定した __all__）。

- 環境設定管理（kabusys.config）
  - .env ファイル / 環境変数の自動ロード機能を実装。
    - プロジェクトルート検出は .git / pyproject.toml を親ディレクトリから探索して行うため、CWD に依存しない。
    - 読み込み順序: OS 環境変数 > .env.local > .env。
    - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env パーサ実装（クォート、エスケープ、インラインコメント、export プレフィックス等に対応）。
  - protected（OS 環境変数）を考慮した上書きロジック。
  - Settings クラスで代表的な設定項目をプロパティとして提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（必須取得は _require により未設定時に ValueError を送出）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）、SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV の検証（development / paper_trading / live のみ許容）
    - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - ヘルパープロパティ: is_live / is_paper / is_dev

- 研究用ファクター・特徴量処理（kabusys.research）
  - factor_research:
    - calc_momentum: 1/3/6ヶ月相当のモメンタム、200日移動平均乖離の算出。
    - calc_volatility: ATR(20)、相対ATR (atr_pct)、20日平均売買代金、出来高比率の算出。
    - calc_value: raw_financials から最新財務を取得して PER / ROE を算出。
    - SQL + DuckDB ウィンドウ関数中心の実装（外部ライブラリに依存しない）。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト: [1,5,21]）の将来リターンを一括取得。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。
    - rank: 同順位は平均ランクで扱うランク変換実装（丸め誤差対策あり）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
  - これら関数群は prices_daily / raw_financials のみを参照し、本番発注や外部 API に依存しない設計。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - build_features:
    - research モジュールの生ファクターを取得し統合。
    - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 >= 5 億円）を適用。
    - 指定カラムを Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）、±3 でクリップ。
    - features テーブルへの日付単位の置換（DELETE -> INSERT）による冪等な書き込み（トランザクション使用）。

- シグナル生成（kabusys.strategy.signal_generator）
  - generate_signals:
    - features と ai_scores を統合して各種コンポーネントスコア（momentum, value, volatility, liquidity, news）を算出。
    - コンポーネントスコアにシグモイド変換を適用。欠損コンポーネントは中立値 0.5 で補完。
    - デフォルト重みと閾値を実装（デフォルト閾値: 0.60、デフォルト重みは StrategyModel に準拠）。
    - weights 引数は検証・補完され、合計が 1.0 になるよう再スケール。
    - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数閾値以上で Bear と判定）により BUY シグナルを抑制。
    - エグジット（SELL）条件:
      - ストップロス（終値が avg_price に対して -8% 以下）。
      - final_score が閾値未満。
      - 未実装の条件はコード内に注記（トレーリングストップ、時間決済など）。
    - BUY / SELL を signals テーブルへ日付単位の置換で書き込む（トランザクション使用）。
    - データ欠損や不正値に対して警告ログ出力し安全にスキップする設計。

- バックテストフレームワーク（kabusys.backtest）
  - simulator:
    - PortfolioSimulator: メモリ内でのポートフォリオ状態管理、約定処理を実装。
    - スリッページ・手数料モデルを考慮（slippage_rate, commission_rate）。
    - BUY は割当金額に基づき収まる株数を算出（手数料込みで再計算）、SELL は保有全量をクローズ。
    - mark_to_market で終値評価、日次スナップショットを記録。
    - TradeRecord / DailySnapshot の dataclass を定義。
  - metrics:
    - calc_metrics: CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, total_trades の計算。
    - 各内部関数は境界条件（データ不足やゼロ除算等）を安全に扱う実装。
  - engine:
    - run_backtest: 本番 DB からインメモリ DuckDB に必要データをコピーして日次シミュレーションを実行するフローを実装。
    - データコピー (prices_daily, features, ai_scores, market_regime, market_calendar) は日付範囲でフィルタして安全に行う（コピー失敗は警告ログでスキップ）。
    - positions テーブルの一時書き戻しロジック（シミュレータ状態を書き戻す）を実装。generate_signals が positions を参照するための整合性確保。
    - 日次ループ: 前日シグナル約定 -> positions 書き戻し -> 時価評価 -> generate_signals -> ポジションサイジング -> 次日約定 に対応。

- モジュール間の明示的なエクスポート（各 __init__.py による公開関数の整理）

### Changed
- 初回リリースのため変更履歴はありません。

### Fixed
- 初回リリースのため修正点はありません。

### Notes / Known limitations
- signal_generator と _generate_sell_signals 内で、positions テーブルに peak_price / entry_date 等の列が存在しないため、トレーリングストップや時間決済（60営業日超）は未実装。将来の拡張で対応予定。
- simulator の BUY は部分約定（部分利確/部分損切）や複雑な発注戦略に非対応（現状は保有全量クローズの SELL、BUY は割当に基づく）。
- research モジュールは pandas 等に依存せず標準ライブラリ基盤の実装。大規模データ・高速処理の追加最適化は今後の課題。
- デフォルト値や閾値（例: 最低株価 300 円、5 億円の流動性、Zスコア ±3 クリップ、BUY閾値 0.60 等）は StrategyModel.md に基づく設計値。運用時はチューニングが必要。

### Security
- 環境変数の取り扱いは protected set を用いて OS 環境変数の上書きを防ぐ挙動を実装。
- 必須トークン等は未設定時に ValueError が発生して明示的に失敗するため、誤った動作を未然に防ぎやすい設計。

---

今後のリリースでは、以下のような改善・拡張を予定しています（例）:
- 部分利確 / トレーリングストップ / 時間決済の実装
- 発注 API（execution 層）との統合
- 性能改善（DuckDB クエリ最適化、並列処理）
- テストカバレッジの強化と CI/CD の整備

ご要望・不具合報告は issue にて受け付けてください。