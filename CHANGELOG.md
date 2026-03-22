# CHANGELOG

すべての重要な変更点をこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠しています。

全てのリリースは semver に従います。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-22
初回リリース — 日本株自動売買システムのコアライブラリを追加。

### Added
- パッケージ全体
  - kabusys パッケージ初期版を追加。モジュール群は data, strategy, execution, monitoring をエクスポート。
  - バージョン: 0.1.0 を src/kabusys/__init__.py に設定。

- 設定管理 (kabusys.config)
  - .env / .env.local ファイルまたは環境変数から設定読み込みを行う自動ローダを実装。
  - プロジェクトルート検出ロジック: .git または pyproject.toml を基準に __file__ を起点に親ディレクトリを探索。
  - .env パーサ実装:
    - コメント / 空行スキップ、export KEY=val 形式対応。
    - シングル／ダブルクォート内のエスケープを扱うクォート解析。
    - インラインコメント（無クォートの場合、直前がスペース/タブならコメントと認識）。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能（テスト用）。
  - Settings クラスを提供:
    - 必須環境変数検証（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）。
    - デフォルト値: KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, KABUSYS_ENV。
    - KABUSYS_ENV と LOG_LEVEL の有効値チェック（不正値は ValueError）。
    - ユーティリティプロパティ: is_live / is_paper / is_dev。

- 戦略（feature engineering / signal generator）
  - feature_engineering.build_features:
    - research モジュール（calc_momentum / calc_volatility / calc_value）から生ファクターを取得。
    - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 >= 5 億円）を適用。
    - 指定列の Z スコア正規化（zscore_normalize を利用）、±3 でクリップ。
    - features テーブルへの日付単位の置換（DELETE + BULK INSERT）により冪等性を確保。
    - 価格参照は target_date 以前の最新価格を利用し、休場日等に対応。

  - signal_generator.generate_signals:
    - features と ai_scores を統合して最終スコア(final_score) を算出。
    - モメンタム / バリュー / ボラティリティ / 流動性 / ニュース（AI）といったコンポーネントを合成（デフォルト重みを定義）。
    - 無効コンポーネントは中立値 0.5 で補完、weights の入力検証と合計が 1.0 になるよう正規化。
    - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数閾値を満たす場合）により BUY シグナルを抑制。
    - BUY（閾値 default=0.60）および SELL（ストップロス -8%、スコア低下）を生成し signals テーブルへ日付単位で置換（冪等）。
    - SELL 判定では positions テーブルの最新ポジション・価格を参照。価格欠損時は判定をスキップして警告を出力。

  - 設計ノート（ドキュメント記載箇所を参照する実装思想）
    - ルックアヘッドバイアス防止のため target_date 時点のデータのみを利用する実装方針。
    - 発注 API / execution 層への直接依存は持たない。

- Research（研究用ユーティリティ）
  - factor_research モジュール:
    - calc_momentum, calc_volatility, calc_value を実装。prices_daily / raw_financials に基づくファクター計算を提供。
    - 各ファクターはデータ不足時に None を返す設計。
  - feature_exploration モジュール:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得する SQL 実装。
    - calc_ic: スピアマン（順位）相関に基づく IC 計算（有効レコードが 3 未満なら None）。
    - rank, factor_summary: ランク付け、基本統計量（count, mean, std, min, max, median）を提供。
  - research パッケージの __all__ を整備。

- バックテストフレームワーク (kabusys.backtest)
  - simulator:
    - PortfolioSimulator クラスを追加。メモリ内でポジション・平均取得単価・履歴・トレード履歴を管理。
    - execute_orders: SELL を先に処理、BUY は alloc（割当）に基づいて始値で約定。部分利確は非対応（SELL は保有全量をクローズ）。
    - スリッページ（買いは +、売りは -）、手数料率を考慮。開始時の資金不足に応じて購入株数を再計算。
    - mark_to_market: 終値で評価し DailySnapshot を記録。終値欠損は 0 として警告。
    - TradeRecord / DailySnapshot の dataclass を定義。
  - metrics:
    - calc_metrics を追加。CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, total_trades を計算。
  - engine.run_backtest:
    - 本番 DuckDB から日付範囲でデータをコピーしてインメモリ DuckDB を作成（init_schema(":memory:") を使用）。
    - signals の生成に generate_signals を呼び出す日次ループを実装。
    - positions テーブルへの書き戻し、open/close 価格取得、約定処理、マーク・トゥ・マーケットを行い、最終的に BacktestResult（history, trades, metrics）を返す。
    - デフォルトパラメータ: initial_cash=10_000_000, slippage_rate=0.001, commission_rate=0.00055, max_position_pct=0.20。
    - コピー対象テーブルやデータ期間の取り扱い（start_date - 300 日から end_date まで）を実装。
    - market_calendar は全件コピー。

### Changed
- （該当なし。初回リリースのため変更履歴はありません）

### Fixed
- （該当なし）

### Deprecated
- （該当なし）

### Removed
- （該当なし）

### Security
- （該当なし）

---

注意・既知の制限 / TODO
- signal_generator の SELL 条件について、ドキュメントで言及されている「トレーリングストップ（直近最高値基準）」「時間決済（保有 60 営業日超過）」は未実装。positions テーブルに peak_price / entry_date 等の追加が必要。
- calc_value は PER / ROE を実装済みだが、PBR・配当利回りは未実装。
- PortfolioSimulator の SELL は常に全量クローズ。部分利確や部分損切りのロジックはない。
- 一部ユーティリティ（例: zscore_normalize）は kabusys.data.stats を参照する（該当実装は本変更セット外にあることを想定）。
- .env の自動読み込みはプロジェクトルートが検出できない場合はスキップされる。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能。
- データベーススキーマ（必須テーブル）:
  - prices_daily, features, ai_scores, positions, signals, raw_financials, market_calendar, market_regime などが各処理で参照される想定。

マイグレーション / 運用メモ
- 必須環境変数を設定しないと Settings 呼び出し時に ValueError が発生します（CI/デプロイ時に注意）。
- デフォルトの DB パスは data/kabusys.duckdb、SQLite は data/monitoring.db。必要に応じて DUCKDB_PATH / SQLITE_PATH を設定してください。
- ログレベル・環境は環境変数 LOG_LEVEL / KABUSYS_ENV で制御。無効な値は例外になります。

このリリースはコア機能の骨格を提供します。以降のリリースでは未実装の出口戦略、追加ファクター、execution 層との統合、テストカバレッジ拡充などを予定しています。