CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。
フォーマットは "Keep a Changelog"（https://keepachangelog.com/ja/1.0.0/）に準拠します。

なお、本 CHANGELOG はソースコードの実装内容から推測して作成しています。

Unreleased
----------

- なし

0.1.0 - 2026-03-22
------------------

Added
- パッケージ初期リリース。
  - パッケージ名: kabusys（__version__ = 0.1.0）
  - 主要サブパッケージ/モジュールを提供:
    - kabusys.config: 環境変数・設定管理（.env / .env.local の自動読み込み、KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化、キー保護機構）
      - プロジェクトルート検出ロジック（.git または pyproject.toml を起点）
      - .env パースの細かい挙動対応（export プレフィックス、シングル/ダブルクォート内のエスケープ、インラインコメントの扱い）
      - Settings クラス: J-Quants / kabu API / Slack / DB パス / 環境種別・ログレベル検証プロパティを提供
    - kabusys.strategy
      - feature_engineering.build_features:
        - research モジュール（calc_momentum / calc_volatility / calc_value）からファクターを取得
        - ユニバースフィルタ（最低株価、20日平均売買代金）適用
        - 指定カラムの Z スコア正規化（zscore_normalize を利用）と ±3 でのクリップ
        - features テーブルへ日付単位の置換（冪等、トランザクション＋バルク挿入）
      - signal_generator.generate_signals:
        - features と ai_scores を統合してコンポーネントスコア（momentum/value/volatility/liquidity/news）を算出
        - デフォルト重み（momentum 0.40 等）をサポート。ユーザ重みはバリデーション・正規化しフォールバック処理
        - AI による市場レジーム判定（regime_score の平均が負なら Bear）および Bear 時の BUY 抑制
        - BUY/SELL の生成（閾値・ストップロス等）、SELL 優先ポリシー、signals テーブルへ日付単位の置換（冪等）
    - kabusys.research
      - factor_research: calc_momentum / calc_volatility / calc_value を実装
        - momentum: 1M/3M/6M リターン、200日移動平均乖離（データ不足時は None）
        - volatility: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比率
        - value: PER・ROE（raw_financials の target_date 以前の最新レコードを参照）
      - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank を実装
        - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得
        - calc_ic: スピアマンランク相関（IC）を実装（有効レコードが3未満なら None）
        - rank: ties を平均ランクに処理、丸め誤差対策として round(v, 12) を使用
        - factor_summary: count/mean/std/min/max/median を算出
      - research パッケージは pandas 等の外部依存を避けて標準ライブラリ + duckdb で実装
    - kabusys.backtest
      - engine.run_backtest:
        - 本番 DB からインメモリ DuckDB へ必要テーブルをコピーしてバックテスト実行
        - 日次ループ: 約定（前日シグナルを当日の始値で約定）→ positions 書き戻し → 時価評価 → generate_signals 呼び出し → 発注準備
        - ポジションサイジング（max_position_pct 等）をサポート
      - simulator.PortfolioSimulator:
        - メモリ内でのポートフォリオ状態管理、BUY/SELL の擬似約定（始値・スリッページ・手数料を考慮）
        - SELL は保有全量クローズ（部分利確未対応）
        - mark_to_market により DailySnapshot を記録（終値欠損は 0 評価かつ警告）
        - TradeRecord / DailySnapshot dataclass を提供
      - metrics.calc_metrics:
        - CAGR / Sharpe / Max Drawdown / Win Rate / Payoff Ratio / total_trades を計算
        - 各内部関数に境界ケース処理を実装（データ不足時は 0.0 を返す等）
    - kabusys.data.stats の zscore_normalize を利用する設計（モジュール間の責務分離）
    - 各所でログ出力（情報・警告・デバッグ）を追加しオペレーション性を向上

Fixed
- DB 操作の原子性を考慮して features / signals / positions への更新を日付単位で置換（トランザクション + バルク挿入）。失敗時は ROLLBACK を試行し、失敗ログを出力するよう改善。
- .env 読み込みで OS 環境変数を上書きしない既定動作と、.env.local による上書きサポートを実装（テスト時用の KABUSYS_DISABLE_AUTO_ENV_LOAD も提供）。

Changed
- なし（初期リリースのため比較対象なし）

Security
- なし

Notes / Known limitations
- _generate_sell_signals 内で未実装とされている条件:
  - トレーリングストップ（peak_price が positions テーブルに未実装のため保留）
  - 時間決済（保有 60 営業日超過など）
- バックテスト環境では本番 DB の signals / positions を汚染しないようインメモリ接続を作成しているが、コピー処理での例外は警告としてスキップする実装になっている（データ不足時の挙動に注意）。
- research モジュールは外部データ解析ライブラリを使わず純 Python 実装のため、大規模データでの性能・便利性は将来的に改善余地あり。
- signal_generator の weights パラメータ入力は厳密に検証され、不正値は無視される。合計が 1.0 でなければ自動で正規化するが、合計が 0 以下の場合はデフォルト重みにフォールバックする。

Authors
- kabusys 開発チーム（コードコメント・実装から推測）

References
- 各モジュール内コメントに記載の StrategyModel.md / BacktestFramework.md 等の設計ドキュメントに準拠して実装されています（プロジェクト内設計書想定）。