# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを使用します。

## [Unreleased]


## [0.1.0] - 2026-03-22

初回リリース。日本株自動売買システムのコア機能を一通り実装しています。主な追加点は以下の通りです。

### Added
- パッケージ初期化とバージョン情報
  - src/kabusys/__init__.py にて __version__ = "0.1.0" を設定し、公開 API（data, strategy, execution, monitoring）を定義。

- 環境変数／設定管理
  - src/kabusys/config.py
    - .env ファイルまたは実行環境の環境変数から設定を読み込む自動ローダを実装（プロジェクトルートは .git または pyproject.toml から探索）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
    - .env 読み込み:
      - export KEY=val 形式に対応
      - シングル/ダブルクォート内のバックスラッシュエスケープ処理を考慮
      - クォートなしの行でのインラインコメント処理（スペース/タブ直前の # をコメントと判定）
      - override と protected 機能で OS 環境変数を保護しつつ .env.local による上書きを許可
    - Settings クラスを提供し、主要な設定をプロパティ経由で取得:
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など必須項目を _require() で厳格にチェック
      - KABUSYS_ENV（development / paper_trading / live）と LOG_LEVEL の検証とデフォルト値
      - デフォルト DB パス（DUCKDB_PATH, SQLITE_PATH）を提供

- 研究（research）モジュール
  - src/kabusys/research/factor_research.py
    - Momentum, Volatility, Value 等のファクター計算を DuckDB SQL と組み合わせて実装:
      - calc_momentum(conn, target_date)
      - calc_volatility(conn, target_date)
      - calc_value(conn, target_date)
    - 各関数は prices_daily / raw_financials テーブルのみ参照し、副作用なしで辞書リストを返す設計。
  - src/kabusys/research/feature_exploration.py
    - calc_forward_returns(conn, target_date, horizons=None): 将来リターン計算（複数ホライズン対応）
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンのランク相関（IC）計算
    - factor_summary(records, columns): 基本統計量（count/mean/std/min/max/median）
    - rank(values): 平均ランク（同順位は平均ランク）を返すユーティリティ
  - research パッケージの __all__ を設定して主要関数を再公開。

- データ前処理 / 特徴量エンジニアリング
  - src/kabusys/strategy/feature_engineering.py
    - 研究環境で計算された raw ファクターをマージし、ユニバースフィルタ（最低株価・最低平均売買代金）、Z スコア正規化（zscore_normalize を利用）、±3 でクリップ、features テーブルへ日付単位で UPSERT（トランザクションで原子性確保）する build_features(conn, target_date) を実装。
    - ユニバース基準: _MIN_PRICE = 300 円、_MIN_TURNOVER = 5e8 円
    - 正規化対象カラム一覧を定義（mom_1m, mom_3m, atr_pct, volume_ratio, ma200_dev）

- シグナル生成
  - src/kabusys/strategy/signal_generator.py
    - features と ai_scores を組み合わせて最終スコアを計算し、BUY / SELL シグナルを生成して signals テーブルへ日付単位で置換挿入する generate_signals(conn, target_date, threshold, weights) を実装。
    - デフォルト重みや閾値を定義:
      - デフォルト重み: momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10
      - デフォルト閾値: 0.60
      - ストップロス閾値: -8%
      - Bear レジーム判定（AI の regime_score の平均が負かつサンプル数 >= 3）
    - スコア計算のユーティリティを実装（シグモイド変換、コンポーネントスコア計算、欠損補完処理等）
    - weights の検証と正規化（既知キーのみ受け付け、無効値はログ警告しスキップ、合計が 1.0 にならない場合は再スケール）
    - SELL 判定ロジック（ストップロス優先、スコア低下）を _generate_sell_signals() として分離し実装。未実装の追加エグジット（トレーリングストップ等）はコメントで明示。

- バックテストフレームワーク
  - src/kabusys/backtest/simulator.py
    - PortfolioSimulator: メモリ内でのポートフォリオ状態管理、約定ロジック、マーク・トゥ・マーケット、トレード記録（TradeRecord / DailySnapshot）の実装。
    - 約定方針: SELL を先に処理、SELL は全量クローズ、BUY は割当額に基づき floor で株数算出、スリッページ・手数料を反映、平均取得単価の更新、cash の更新。
    - mark_to_market: 終値が無い銘柄は 0 で評価し警告ログを出す設計。
  - src/kabusys/backtest/metrics.py
    - バックテスト評価指標を計算する calc_metrics(history, trades) と内部関数群を実装:
      - CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, total trades 等。
  - src/kabusys/backtest/engine.py
    - run_backtest(conn, start_date, end_date, initial_cash=..., slippage_rate=..., commission_rate=..., max_position_pct=...) を提供。
    - 本番 DuckDB から日付範囲を絞ってインメモリ DuckDB にコピーする _build_backtest_conn を実装（signals/positions を汚染しないための設計）。
    - 日次ループの実装: 前日シグナル約定 -> positions 書き戻し -> mark_to_market -> generate_signals 呼び出し -> signals を読み取り発注を組成 → 次営業日へ。
    - DuckDB を用いた open/close price の取得と positions テーブルの冪等書き込みをサポート。
    - デフォルトパラメータ: initial_cash=10,000,000 円, slippage_rate=0.001, commission_rate=0.00055, max_position_pct=0.20

- パッケージエクスポート
  - backtest パッケージの __init__ にて run_backtest, BacktestResult, DailySnapshot, TradeRecord, BacktestMetrics を公開。
  - strategy パッケージの __init__ で build_features, generate_signals を公開。
  - research パッケージの __init__ で主要ユーティリティを公開。

### Fixed / Improved
- トランザクション安全性とエラーハンドリング
  - features / signals への日付単位置換は BEGIN / COMMIT / ROLLBACK を利用して原子性を確保。ROLLBACK に失敗した場合は警告ログを出力。
- .env 読み込みの堅牢性向上
  - ファイルオープン時の OSError を捕捉して警告を出し自動ロード処理を継続（致命エラー防止）。
  - quote 処理やエスケープ処理を実装し、実運用で見られる多様な .env 形式に対応。

### Notes / ユーザーへの注記
- Settings による必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は未設定時に ValueError を送出するため、本番実行前に .env を準備してください（.env.example を参照）。
- 自動 .env ロードの優先順位:
  - OS 環境変数 > .env.local > .env。OS 環境変数は保護され、.env.local が OS の値を上書きする際にも保護されます。
- DuckDB 接続を受け取る関数群（research/strategy/backtest）は外部 API に依存せず、prices_daily / raw_financials 等のテーブルを前提としているため、テスト用データを用意してから実行してください。
- 一部保留／未実装事項:
  - signal_generator のエグジット条件のうちトレーリングストップや時間決済は positions テーブルに追加のメタ情報（peak_price / entry_date 等）を格納する必要があり現状は未実装。
  - execution パッケージは空の初期化があるが、実際の発注インテグレーション・Kabu API 呼び出し等は未実装（今後の追加予定）。

### Breaking Changes
- 初回リリースのため該当なし。

### Security
- 本バージョンにおけるセキュリティ修正は特になし。ただし、機密情報（API トークン等）は .env または実環境変数で管理し、リポジトリに直接コミットしないでください。

---

今後のリリースでは、execution 層の実装（kabusapi 連携）、モニタリング/通知の強化、追加のエグジットロジックや最適化機能を予定しています。必要な改善点や追加機能の要望があればお知らせください。