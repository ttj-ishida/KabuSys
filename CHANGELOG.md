CHANGELOG
=========

すべての変更は "Keep a Changelog" の形式に準拠して記載しています。
バージョン番号はパッケージの __version__ に対応します。

Unreleased
----------

（現在差分はありません）

0.1.0 - 2026-03-22
-----------------

Added
- パッケージ初期リリースを追加。
  - パッケージ名: kabusys
  - バージョン: 0.1.0

- 環境設定・自動 .env ロード機能（kabusys.config）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動読み込み。
  - 読み込み優先度: OS 環境変数 > .env.local > .env。
  - テスト等で自動ロードを無効化するためのフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env パーサは export KEY=val 形式、シングル/ダブルクォート、エスケープ、インラインコメントルール等に対応。
  - 環境変数必須取得ヘルパー _require()（未設定時は ValueError を送出）。
  - Settings クラスを公開（settings インスタンス経由で利用）。
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等の必須設定。
    - KABUSYS_ENV（development / paper_trading / live）、LOG_LEVEL（DEBUG/INFO/...）の検証。
    - データベースパスの取得（DUCKDB_PATH, SQLITE_PATH）を Path 型で提供。
    - is_live / is_paper / is_dev のブールプロパティを提供。

- 戦略関連（kabusys.strategy）
  - 特徴量エンジニアリング（feature_engineering.build_features）
    - research 側で算出した生ファクター（momentum / volatility / value）を統合し、正規化（Z スコア）・±3 クリップして features テーブルへ日付単位で UPSERT（トランザクション + バルク挿入で原子性を確保）。
    - ユニバースフィルタとして最低株価（300 円）・20日平均売買代金（5 億円）を適用。
    - DuckDB 接続を受け取り prices_daily / raw_financials を参照。発注 API などの外部依存なし。
  - シグナル生成（signal_generator.generate_signals）
    - features と ai_scores を統合して銘柄ごとのコンポーネントスコア（momentum / value / volatility / liquidity / news）を計算し、重み付きで final_score を算出。
    - デフォルト重みは StrategyModel.md の仕様に準拠（momentum 0.40 など）。ユーザ指定 weights は検証・正規化して受け入れ。
    - Sigmoid 変換、欠損値は中立値 0.5 で補完するポリシーを採用。
    - Bear レジーム検出（ai_scores の regime_score 平均 < 0 かつサンプル数閾値を満たす場合）では BUY シグナルを抑制。
    - BUY 閾値デフォルト 0.60。BUY/SELL を signals テーブルへ日付単位で置換（原子性保証）。
    - エグジット判定（_generate_sell_signals）:
      - ストップロス: 終値 / avg_price - 1 <= -8%（最優先）
      - スコア低下: final_score < threshold
      - features に存在しない保有銘柄は final_score = 0 と扱い SELL 対象にする（警告ログ）。
      - 価格欠損時は SELL 判定をスキップ（誤クローズ防止）。
    - 未実装 / 将来の拡張箇所: トレーリングストップ、時間決済（positions に peak_price / entry_date が必要）。

- リサーチツール群（kabusys.research）
  - factor_research モジュール
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離率を計算（prices_daily を参照）。
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から最新財務を取得し PER / ROE を計算（prices_daily と結合）。
  - feature_exploration モジュール
    - calc_forward_returns: 指定日の終値から複数ホライズン先（デフォルト 1,5,21 営業日）の将来リターンを計算。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算（3 サンプル未満で None）。
    - factor_summary: 複数カラムの count/mean/std/min/max/median を計算。
    - rank: 同順位は平均ランクを返すランク関数（round の丸めで ties 検出を安定化）。
  - 設計方針: DuckDB 接続のみを受け取り prices_daily / raw_financials を参照。外部ライブラリ (pandas 等) に依存しない。

- バックテストフレームワーク（kabusys.backtest）
  - Portfolio シミュレータ（simulator.PortfolioSimulator）
    - メモリ内でキャッシュ・ポジション管理、約定ロジックを実装。
    - execute_orders: SELL を先に処理、BUY は alloc に基づく買付（スリッページ率、手数料率考慮）。BUY は手数料込みで調整後の株数で約定。
    - _execute_sell/_execute_buy: 約定記録を TradeRecord として保持。realized_pnl の計算、cost_basis（平均取得単価）更新。
    - mark_to_market: 終値で評価して DailySnapshot を履歴に追加。不足価格は 0 と評価し警告ログを出力。
  - バックテストエンジン（engine.run_backtest）
    - 本番 DuckDB からインメモリ DuckDB へ必要テーブルを日付範囲でコピー（signals/positions を汚さない）。
    - 日次ループ: 前日シグナルの約定 → positions テーブル更新 → 時価評価記録 → generate_signals 呼出し → 発注リスト組立（ポジションサイジング）。
    - run_backtest は初期資金、スリッページ率（デフォルト 0.1%）、手数料率（デフォルト 0.055%）、1 銘柄あたりの最大比率（デフォルト 20%）をパラメータ化。
  - メトリクス（metrics.calc_metrics）
    - CAGR, Sharpe Ratio（無リスク金利=0 想定）、最大ドローダウン、勝率、ペイオフ比、総取引数を算出。
    - 各内部計算関数は境界ケース（サンプル不足、0 除算）をハンドリングして安全に 0 を返す実装。

- パッケージエクスポート
  - 主要 API を __all__ で公開（strategy.build_features / strategy.generate_signals、research のユーティリティ、backtest の run_backtest など）。

Notes / Known limitations
- 一部の戦術的エグジットロジック（トレーリングストップや時間決済）は未実装で、将来の拡張予定。
- PBR や配当利回りは現バージョンでは未実装。
- feature_engineering は kabusys.research 側の関数（calc_*）および kabusys.data.stats.zscore_normalize に依存する（data モジュールは本差分に含まれません）。
- DuckDB のテーブルスキーマ（prices_daily, features, ai_scores, positions, raw_financials, market_calendar など）に依存した実装のため、スキーマ不整合は実行時エラーの原因となる可能性があります。
- generate_signals / build_features は DB 上で日付単位の DELETE → INSERT（トランザクション）を行い冪等性を確保しますが、大量データでのパフォーマンスは利用状況に依存します。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Security
- 初回リリースのため該当なし。

作者注
- 実装の多くは設計ドキュメント（StrategyModel.md / BacktestFramework.md 等）に従っています。運用前に .env 設定、DuckDB スキーマ、必要データの有無を確認してください。