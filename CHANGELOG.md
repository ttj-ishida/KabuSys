CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。  
https://keepachangelog.com/ja/

[Unreleased]
------------

- （なし）

[0.1.0] - 2026-03-22
-------------------

初回リリース。日本株自動売買フレームワーク "KabuSys" の基本機能を実装しました。

Added
- パッケージ基盤
  - パッケージバージョンを src/kabusys/__init__.py にて "0.1.0" として公開。
  - 公開 API: data, strategy, execution, monitoring を __all__ で明示。

- 環境設定・読み込み（src/kabusys/config.py）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動読み込み。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化するオプションを提供。
  - export プレフィックス、クォート（シングル/ダブル）、バックスラッシュエスケープ、インラインコメント等に対応した堅牢な .env パーサを実装。
  - 必須環境変数取得ヘルパー _require と Settings クラスを実装。以下のキーをプロパティ経由で参照可能：
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルトあり）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（デフォルト data/monitoring.db）
    - KABUSYS_ENV（development/paper_trading/live の検証）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）
  - 環境判定ヘルパー: is_live / is_paper / is_dev

- 戦略（src/kabusys/strategy）
  - 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
    - research 側で計算した生ファクターを読み込み、ユニバースフィルタ（最低株価・最低平均売買代金）を適用。
    - 指定日（target_date）基準の Z スコア正規化（zscore_normalize を利用）と ±3 でのクリップ。
    - 結果を features テーブルへ日付単位で置換（UPSERT 相当）。関数: build_features(conn, target_date) → upsert 件数を返す。
    - ユニバース閾値定義: 最低価格 300 円、最低平均売買代金 5 億円。

  - シグナル生成（src/kabusys/strategy/signal_generator.py）
    - features テーブルと ai_scores を統合して各銘柄の最終スコア（final_score）を計算。
    - コンポーネントスコア: momentum / value / volatility / liquidity / news（AI スコア）。
    - 重み付けのデフォルトは StrategyModel.md の値を採用。ユーザー指定 weights の検証・正規化を実装。
    - Bear レジーム判定（ai_scores の regime_score 平均が負の場合）による BUY シグナル抑制。
    - BUY: final_score >= デフォルト閾値 0.60 で生成（Bear 時は抑制）。
    - SELL（エグジット）判定:
      - ストップロス（終値が平均取得単価から -8% 以下）
      - final_score が閾値未満
      - positions / prices の欠損時の挙動（ログ出力して判定をスキップ/扱い）を明示。
    - 日付単位で signals テーブルへ置換して書き込む。公開関数: generate_signals(conn, target_date, threshold=?, weights=?)

- リサーチ（src/kabusys/research）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - calc_momentum(conn, target_date): mom_1m / mom_3m / mom_6m / ma200_dev（200日 MA の乖離）。
    - calc_volatility(conn, target_date): atr_20 / atr_pct / avg_turnover / volume_ratio（20日ウィンドウベース）。
    - calc_value(conn, target_date): per / roe（raw_financials と prices_daily を結合して計算）。
    - 各関数は prices_daily / raw_financials のみ参照し、データ不足時は None を返す設計。
  - 特徴量探索ユーティリティ（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns(conn, target_date, horizons): 複数ホライズンの将来リターンを一度のクエリで取得。
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンランク相関（IC）を計算。
    - factor_summary(records, columns): count/mean/std/min/max/median の統計サマリーを計算。
    - rank(values): 同順位は平均ランクを返すランク関数。pandas に依存しない純粋 Python 実装。
  - research パッケージ __all__ に主要関数を登録。

- バックテスト（src/kabusys/backtest）
  - シミュレータ（src/kabusys/backtest/simulator.py）
    - PortfolioSimulator: メモリ内でポジション・コスト基準・履歴・約定記録を管理。
    - execute_orders: SELL を先に処理、BUY は割当額から株数算出、スリッページ（率）と手数料率を適用。BUY は必要に応じて手数料込みで株数を再計算。
    - SELL は保有全量クローズのみ（部分利確・部分損切りは非対応）。
    - mark_to_market: 終値で評価し DailySnapshot を記録（終値欠損時は警告して 0 評価）。
    - TradeRecord / DailySnapshot の dataclass を公開。
  - メトリクス（src/kabusys/backtest/metrics.py）
    - バックテスト評価指標の計算: CAGR, Sharpe Ratio（無リスク=0）, Max Drawdown, Win Rate, Payoff Ratio, total_trades。
    - calc_metrics(history, trades) により BacktestMetrics を返す。
  - エンジン（src/kabusys/backtest/engine.py）
    - run_backtest(conn, start_date, end_date, ...) を実装。
    - 本番 DuckDB から日時範囲を切り出してインメモリ DuckDB にコピー（signals/positions を汚染しない）。
    - 必要テーブルの範囲コピー（prices_daily, features, ai_scores, market_regime, market_calendar）。
    - 日次ループ: 当日始値で前日シグナル約定 → positions テーブルへ書き戻し → 終値で評価記録 → generate_signals 呼び出し → 翌日発注リスト作成（ポジションサイジング） の流れを実装。
    - 市場カレンダー取得は kabusys.data.calendar_management.get_trading_days を使用。
    - BacktestResult（history, trades, metrics）を返却。

- モジュール間の設計方針
  - ルックアヘッドバイアス防止のため、各処理は target_date 時点のデータのみを使用する設計
  - 発注 API や本番 execution 層への直接依存は持たない（signals テーブル経由で分離）
  - DuckDB を中心とした SQL と純粋 Python の組合せで効率的に実装
  - 外部大規模依存（pandas など）を避ける設計（research ツールも標準ライブラリのみ）

Fixed
- 初回リリースのため該当なし。

Changed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Security
- .env ファイル読み込み時に読み込み失敗があっても警告を出して継続する実装（例外を投げない）。重要なシークレットは Settings の必須プロパティで明示的に検証。

Known issues / Limitations
- Signal / Execution
  - SELL は現時点で「保有全量クローズ」のみ。部分利確や数量指定のサポートは未実装。
  - Trailing stop（直近最高値に対する追跡ストップ）や時間決済（保有日数による強制決済）は未実装（feature_engineering / signal_generator 内に TODO コメントあり）。
- AI スコアの取り扱い
  - ai_scores が未登録の銘柄はニューススコアを中立（0.5）で補完するため、AI スコア未整備環境でも動作するが、実運用時は ai_scores の投入を推奨。
- バックテスト
  - _build_backtest_conn はテーブルを日付レンジでフィルタしてコピーするが、テーブルスキーマ変更や特殊データ型によりコピーが失敗する場合は警告を出してスキップする実装。
  - run_backtest はトレード日数の取得やデータ範囲に対して暫定的なバッファ（例: features コピーは start_date - 300 日）を利用している。大幅な過去データ差異がある場合は注意。
- データ依存
  - 各リサーチ / 戦略機能は prices_daily / raw_financials / features / ai_scores / positions / signals / market_calendar 等のテーブルが正しく存在・整形されていることを前提とする。
- テスト・堅牢性
  - エッジケース（NaN/Inf/NULL 値、極端な weights の指定など）に対する防御コードは入れているが、さらなる実運用テストが必要。

Migration notes
- 本リリースは初版のため、特別な移行手順はありません。duckdb スキーマの初期化は kabusys.data.schema.init_schema を使用してください。

参考: 要設定環境変数（実行に必須）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

開発者向けメモ
- settings オブジェクトは kabusys.config.settings として singleton 的に利用可能。
- 自動 .env ロードを抑止したいユニットテスト等では KABUSYS_DISABLE_AUTO_ENV_LOAD を環境変数で有効化してください。

--- End of CHANGELOG ---