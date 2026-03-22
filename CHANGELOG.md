CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従います。  
このファイルは日本語で記載しています。

フォーマット:
- 参照: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

（現在なし）

[0.1.0] - 2026-03-22
--------------------

Added
- パッケージ初回リリース (kabusys 0.1.0)
  - 基本構成
    - パッケージメタ情報: src/kabusys/__init__.py に __version__ = "0.1.0" を追加。
    - __all__ に data, strategy, execution, monitoring を公開。
  - 環境設定管理 (src/kabusys/config.py)
    - .env / .env.local から環境変数を自動読み込み（プロジェクトルートは .git または pyproject.toml を基準に探索）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
    - export KEY=val 形式やクォート、インラインコメントの扱いに対応する行パーサ実装。
    - OS 環境変数を保護する読み込みロジック（.env.local は上書き可能だが OS 環境は protected）。
    - Settings クラスを提供し、必須環境変数取得時に ValueError を投げるユーティリティを実装。
    - J-Quants / kabuステーション / Slack / データベースパス（DuckDB/SQLite）等の設定プロパティを用意。
    - KABUSYS_ENV と LOG_LEVEL の値検証（許容値の検査）。
  - 研究（research）モジュール
    - ファクター研究 (src/kabusys/research/factor_research.py)
      - Momentum（1M/3M/6M リターン、200日移動平均乖離率）、Volatility（20日 ATR、相対 ATR、20日平均売買代金、出来高比率）、Value（PER、ROE）を計算する関数を実装。
      - prices_daily / raw_financials テーブルのみ参照。データ不足時は None を返す設計。
    - 特徴量探索 (src/kabusys/research/feature_exploration.py)
      - 将来リターン calc_forward_returns（複数ホライズン対応、horizons デフォルト [1,5,21]、最大 252 日の入力検証）。
      - スピアマン（ランク）IC 計算 calc_ic（結合・欠損除外・サンプル数閾値あり）。
      - factor_summary により基本統計量（count/mean/std/min/max/median）を算出。
      - rank ユーティリティ（同順位は平均ランク）を実装。
    - research パッケージから主要関数を再エクスポート。
  - 特徴量エンジニアリング (src/kabusys/strategy/feature_engineering.py)
    - build_features(conn, target_date): research モジュールの生ファクターを取得・マージし、ユニバースフィルタ（最小株価 300 円、20日平均売買代金 5 億円）を適用。
    - 正規化: 指定列を Z スコア正規化し ±3 でクリップ（外れ値抑制）。
    - features テーブルへ日付単位で置換（DELETE + bulk INSERT、トランザクションで原子性確保）。
    - DuckDB を使用した価格の「target_date 以前の最新価格」参照により休場日などに対応。
  - シグナル生成 (src/kabusys/strategy/signal_generator.py)
    - generate_signals(conn, target_date, threshold=0.6, weights=None)
      - features と ai_scores を統合してコンポーネントスコア（momentum/value/volatility/liquidity/news）を算出。
      - デフォルト重みを定義（momentum:0.40, value:0.20, volatility:0.15, liquidity:0.15, news:0.10）。user weights を検証・補完し合計で再スケール。
      - Sigmoid 変換・欠損値は中立 0.5 で補完、最終スコア final_score を計算。
      - Bear レジーム判定（ai_scores の regime_score 平均が負で、十分なサンプル数がある場合は Bear）：Bear 時には BUY を抑制。
      - BUY シグナルは閾値超過銘柄、SELL シグナルはストップロス（終値と avg_price の損失率 <= -8%）およびスコア低下（final_score < threshold）で生成。
      - signals テーブルへ日付単位で置換（トランザクションで原子性確保）。SELL 優先ポリシー（SELL 銘柄は BUY から除外しランクを再付与）。
      - 不正な weights 値のログ出力や、features が空の際の挙動ログあり。
  - バックテストフレームワーク (src/kabusys/backtest/)
    - シミュレータ (src/kabusys/backtest/simulator.py)
      - PortfolioSimulator: メモリ上で保有・コスト基準・現金・履歴・約定履歴を管理。
      - 約定モデル: execute_orders は SELL を先に処理、BUY は始値にスリッページを適用して発注、手数料を考慮した株数調整（端数切捨て）。SELL は保有全量クローズのみサポート。
      - mark_to_market で終値評価、保有株に終値がない場合は 0 で評価して警告ログ出力。
      - TradeRecord / DailySnapshot Dataclass を提供。
    - メトリクス (src/kabusys/backtest/metrics.py)
      - calc_metrics: history（DailySnapshot リスト）と trades（TradeRecord リスト）から CAGR, Sharpe (無リスク=0, 年次化252日), Max Drawdown, Win Rate, Payoff Ratio, total_trades を算出。
      - 各種内部計算関数を分割実装。
    - エンジン (src/kabusys/backtest/engine.py)
      - run_backtest(conn, start_date, end_date, initial_cash=10_000_000, slippage_rate=0.001, commission_rate=0.00055, max_position_pct=0.20)
        - 本番 DuckDB からインメモリ DuckDB へデータをコピーしてバックテスト用接続を構築（_build_backtest_conn）。コピー対象テーブルは日付範囲フィルタあり（prices_daily, features, ai_scores, market_regime）、market_calendar は全件コピー。
        - 日次ループ: 前日シグナルを当日始値で約定、positions テーブルへ書き戻し（generate_signals の SELL 判定に必要）、終値で時価評価してスナップショット記録、generate_signals 呼び出し、次日の発注リストを構築（ポジションサイジングのための alloc 計算）。
        - DuckDB 接続のコピーに失敗した場合には警告ログを出力して続行する耐障害性。
  - パッケージ構成
    - strategy パッケージは build_features / generate_signals をエクスポート。
    - backtest パッケージは run_backtest / BacktestResult / DailySnapshot / TradeRecord / BacktestMetrics をエクスポート。

Changed
- n/a（初回リリースのため変更履歴はなし）

Fixed
- n/a（初回リリースのため bugfix はなし）

Deprecated
- n/a

Removed
- n/a

Security
- n/a

Known issues / Limitations
- feature_engineering / research
  - PER 計算は EPS が 0 または欠損の場合 None を返す。PBR・配当利回りは未実装。
  - build_features は features テーブルへ書き込む際に avg_turnover を保存しない（フィルタ用途のみ）。
- signal_generator
  - SELL の追加ルール（トレーリングストップ、時間決済）は未実装（positions テーブルに peak_price / entry_date が必要）。
  - ai_scores が未登録の銘柄は news コンポーネントを中立（0.5）と扱う。
- simulator
  - SELL は「全量クローズ」のみ。部分利確 / 部分損切りは未対応。
  - mark_to_market で終値が欠損した銘柄は 0 で評価される（警告ログあり）。
- backtest/engine
  - コピー対象テーブルの構造変更や大規模データでのメモリ使用に注意。コピー失敗は警告でスキップするが結果に影響する可能性あり。
- 依存
  - DuckDB を利用する設計のため、DuckDB が利用可能であることが前提。
  - research モジュールは外部ライブラリ（pandas 等）に依存しない実装だが、実行には十分な prices_daily/raw_financials データが必要。

Notes / Migration
- .env の自動読み込みはプロジェクトルート検出に依存するため、パッケージ配布後に期待通りに動作しない環境がある場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して手動で環境変数を用意してください。
- Settings クラスは必須環境変数が欠けていると ValueError を発生させます。CI/デプロイ時は .env.example を参考に必須項目を設定してください。

Contributing
- 初期リリース。バグ報告・機能提案は issue を開いてください。

---

配布されたコードから推測して CHANGELOG を作成しました。必要に応じて文言の追加・修正や、実際のリリース日・貢献者情報の追記を行ってください。