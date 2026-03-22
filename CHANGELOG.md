# Changelog

すべての注目すべき変更点をこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。

現在のリリース履歴は以下の通りです。

## [0.1.0] - 2026-03-22

初回公開リリース。

### 追加 (Added)
- パッケージ基盤
  - パッケージ初期化とバージョン管理を追加（kabusys.__version__ = "0.1.0"）。
- 環境設定管理 (src/kabusys/config.py)
  - .env/.env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml で探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト等で使用）。
  - .env パーサ（クォート対応、バックスラッシュエスケープ、コメント処理、`export KEY=val` 形式対応）を実装。
  - OS 環境変数を「protected」として .env.local による上書きを防止する仕組みを追加。
  - Settings クラスを導入し、J-Quants / kabu API / Slack / DB パス / 実行環境などの設定アクセサを提供。必須環境変数未設定時は ValueError を送出。
  - KABUSYS_ENV と LOG_LEVEL の値検証（許容値チェック）を実装。
- 戦略関連 (src/kabusys/strategy/)
  - 特徴量エンジニアリング (feature_engineering.build_features)
    - research 層で計算した生ファクターを結合・正規化して features テーブルに日付単位で UPSERT（トランザクションによる置換）する処理を追加。
    - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 >= 5億円）を実装。
    - Z スコア正規化と ±3 でのクリップ処理を適用。
    - DuckDB 接続を受け取り prices_daily / raw_financials を参照する独立した実装。
  - シグナル生成 (signal_generator.generate_signals)
    - features と ai_scores を統合して最終スコア(final_score) を算出し、BUY/SELL シグナルを生成して signals テーブルへ日付単位で置換（トランザクション）で書き込む。
    - コンポーネントスコア（momentum, value, volatility, liquidity, news）を計算。デフォルト重みと閾値（threshold=0.60）を採用。
    - Sigmoid 変換、欠損コンポーネントは中立値(0.5)で補完する設計。
    - Bear レジーム検知（ai_scores の regime_score 平均が負の場合に BUY を抑制）を実装。
    - SELL 判定はポジションのストップロス（-8%）とスコア低下による判定を実装し、SELL 優先（BUY から除外）を採用。
    - 価格欠損時の挙動（判定スキップや警告出力）を明確化。
- 研究用ユーティリティ (src/kabusys/research/)
  - factor_research: calc_momentum / calc_volatility / calc_value を実装。prices_daily/raw_financials を参照して各種ファクターを計算する（mom_1m/mom_3m/mom_6m, ma200_dev, atr_20/atr_pct, avg_turnover, volume_ratio, per, roe など）。
  - feature_exploration: 将来リターン計算(calc_forward_returns)、IC（Spearman ρ）計算(calc_ic)、factor_summary、rank を実装。外部依存なしで統計解析が可能。
  - research パッケージのエクスポートを追加（calc_momentum 等と zscore_normalize の公開）。
- バックテスト (src/kabusys/backtest/)
  - Simulator（src/kabusys/backtest/simulator.py）
    - PortfolioSimulator を実装。シグナルの擬似約定（SELL を先行、BUY は資金に応じて約定）、スリッページ・手数料モデル、平均取得単価管理、日次時価評価（mark_to_market）、トレードレコード生成を実装。
    - DailySnapshot / TradeRecord dataclass を提供。
  - Metrics（src/kabusys/backtest/metrics.py）
    - CAGR、Sharpe Ratio、Max Drawdown、Win Rate、Payoff Ratio、総トレード数などの指標計算を実装。
  - Engine（src/kabusys/backtest/engine.py）
    - run_backtest: 本番 DB から必要テーブルをインメモリ DuckDB にコピーして日次ループでシミュレーションを実行する機能を追加。positions テーブルの書き戻し、signals の読み取り、注文実行・資金配分ロジックを統合。
    - DB のコピーは日付レンジフィルタ（prices_daily, features, ai_scores, market_regime）や market_calendar の全件コピーをサポート。コピー失敗時は警告ログでスキップ。
    - バックテスト用に init_schema(":memory:") を使ったインメモリ接続を返却するユーティリティを実装。
  - backtest パッケージのエクスポート（run_backtest, BacktestResult, DailySnapshot, TradeRecord, BacktestMetrics）。

### 変更 (Changed)
- なし（初回リリースのため新規実装が中心）。

### 修正 (Fixed)
- なし（初回リリース）。

### 注意・設計上の決定 (Notes)
- DB 書き込みは日付単位で削除→挿入する方式（トランザクション + バルク挿入）で冪等性と原子性を確保。例外発生時は ROLLBACK を試行し、失敗した場合は警告ログを出力。
- .env のパースはクォート内部のエスケープやインラインコメントを考慮するよう実装。クォートなしの場合のコメント扱いは '#' の直前がスペース/タブの場合のみコメントとして扱う仕様。
- weights の与え方に対する堅牢性確保（未定義キーや非数値、負値、NaN/Inf を無視し、合計が 1.0 でない場合は再スケールする）。
- Sigmoid による正規化と Z スコアの ±3 クリップにより外れ値の影響を抑制。
- SELL 判定ロジックは price 欠損時の誤クローズを避けるため価格未取得なら判定をスキップ。
- generate_signals は AI スコア（ai_scores）を参照するが、未登録銘柄は中立値で補完する（過度な降格を防止）。

### 未実装・既知の制限 (Known issues / TODO)
- エグジット条件の一部（トレーリングストップや一定保有期間での自動決済）は未実装（コメントで今後の実装予定として記載）。実装には positions テーブルの peak_price / entry_date 情報が必要。
- Value ファクターでは PER / ROE のみを実装。PBR・配当利回り等は現バージョンでは未対応。
- Backtest のポジションサイジングは単純化されている（max_position_pct の単純制約など）。実運用向けのリスク管理ロジックは拡張の余地あり。
- 外部依存は最小限にしているが DuckDB を使用するため実行環境に duckdb が必要。
- 一部のエラー処理はログ警告に留めており、堅牢性向上のため詳細なエラーハンドリングを今後強化予定。

### 互換性 (Compatibility)
- 本バージョンは初回リリースのため破壊的変更はなし。

---

今後のリリースでは、未実装のエグジットルール追加、より柔軟なサイジング/リスク管理、外部モデル（AI）との統合強化、テストカバレッジの拡充などを予定しています。フィードバックやバグ報告は歓迎します。