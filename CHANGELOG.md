# Changelog

すべての変更は Keep a Changelog の形式に従い、セマンティックバージョニングを採用しています。
現在のバージョンは 0.1.0 です（初期リリース）。

## [0.1.0] - 2026-03-22

Added
- パッケージ骨組みを追加
  - パッケージ名: kabusys
  - エントリポイント: src/kabusys/__init__.py（__version__ = "0.1.0"）
- 環境変数／設定管理（src/kabusys/config.py）
  - .env/.env.local をプロジェクトルート（.git または pyproject.toml）から自動読み込みする機能を実装。
  - 自動読み込みは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env パーサーは以下の仕様をサポート:
    - コメント行・空行の無視、`export KEY=val` 形式対応
    - 単一／二重クォート内のエスケープ処理（バックスラッシュ）対応
    - クォート無しの値におけるインラインコメント解釈（直前が空白/タブの場合のみ）
  - Settings クラスを提供し、アプリケーションで利用する主要設定をプロパティ経由で取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等の必須チェック（未設定時は ValueError）
    - KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH 等のデフォルト値
    - KABUSYS_ENV（development / paper_trading / live）や LOG_LEVEL のバリデーション、ユーティリティプロパティ（is_live 等）
- 戦略コンポーネント（src/kabusys/strategy/）
  - 特徴量作成（feature_engineering.build_features）
    - research で計算した生ファクター（momentum / volatility / value）をマージして特徴量（features）を生成
    - ユニバースフィルタ（最低株価: 300 円、20日平均売買代金 >= 5 億円）
    - 指定列の Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）と ±3 にクリップ
    - 日付単位での冪等な置換処理（トランザクション + バルク挿入）とロールバック保護
  - シグナル生成（signal_generator.generate_signals）
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を算出
    - 統合ウェイトの補完・正規化（デフォルトは StrategyModel に基づく重み）
    - Sigmoid・欠損値補完（中立 0.5）を用いた final_score 計算
    - Bear レジーム検知（ai_scores の regime_score 平均が負かつ十分なサンプル数がある場合）で BUY 抑制
    - BUY/SELL シグナルの生成と signals テーブルへの冪等書き込み（トランザクション処理）
    - SELL 条件にはストップロス（-8%）とスコア低下を実装（保有ポジションは positions テーブル参照）
- リサーチ（src/kabusys/research/）
  - ファクター計算 API を公開（calc_momentum, calc_volatility, calc_value）
    - momentum: 1M/3M/6M リターン、200 日移動平均乖離率（データ不足時は None）
    - volatility: 20 日 ATR, ATR/価格 (atr_pct), 20 日平均売買代金, 出来高比率
    - value: prices + raw_financials から PER/ROE を算出（最新の財務レコードを target_date 以前から取得）
  - 特徴量探索ユーティリティ（feature_exploration）
    - calc_forward_returns: 指定 horizon の将来リターンを一括取得（LEAD を利用）
    - calc_ic: スピアマンのランク相関（Information Coefficient）計算（有効サンプル < 3 の場合は None）
    - factor_summary: count/mean/std/min/max/median の統計要約
    - rank: 同順位は平均ランクで処理（丸めによる tie 回避のため round(v, 12) を使用）
  - research パッケージのエクスポートを整理（__all__ に主要関数を追加）
- バックテストフレームワーク（src/kabusys/backtest/）
  - ポートフォリオシミュレータ（simulator.PortfolioSimulator）
    - メモリ内状態管理（cash, positions, cost_basis, history, trades）
    - execute_orders: SELL を先、BUY を後に処理。BUY は資金に応じて発注株数を計算（切り捨て）、手数料・スリッページを考慮
    - BUY の平均取得単価更新、SELL での realized_pnl 計算を実装
    - mark_to_market: 終値で時価評価し DailySnapshot を記録（終値欠損は 0 として警告）
    - TradeRecord / DailySnapshot の dataclass を提供
  - バックテストエンジン（engine.run_backtest）
    - 本番 DuckDB から日付範囲をフィルタしてインメモリ DuckDB にコピーしバックテスト環境を構築（_build_backtest_conn）
    - get_trading_days を使った日次ループ、open での約定・positions テーブル書き戻し・終値評価・シグナル生成・ポジションサイジングの流れを実装
    - _write_positions/_fetch_open_prices/_fetch_close_prices/_read_day_signals 等の補助関数を提供
    - 最終的に BacktestResult（history, trades, metrics）を返却
  - バックテスト指標（metrics.calc_metrics）
    - CAGR, Sharpe Ratio（無リスク利率=0、年次化に営業日252を使用）, Max Drawdown, Win Rate, Payoff Ratio, total_trades の計算
- トランザクションとエラー処理の整備
  - features / signals の更新処理で BEGIN/COMMIT/ROLLBACK を用いて原子性を確保
  - ロールバック失敗時には警告ログを出力して例外を再送出
- ロギングを各モジュールに導入（重要な警告・情報を記録）

Changed
- （初期リリース）設計方針・実装ノートをソース内ドキュメント文字列にて明記
  - ルックアヘッドバイアス防止のため target_date 時点のデータのみを使用
  - 本番口座・発注 API への直接依存を避ける（DB と純粋な計算処理に分離）
  - 外部ライブラリ（pandas 等）への依存を最小化し、DuckDB と標準ライブラリ中心で実装

Fixed
- n/a（初回リリースのため、バグフィックスは該当なし）

Deprecated
- n/a

Removed
- n/a

Security
- n/a

Notes / Limitations / TODO
- 一部仕様は未実装（ソース内に明記）
  - generate_signals の SELL 条件でトレーリングストップや時間決済は未実装（positions に peak_price / entry_date が必要）
  - calc_value で PBR / 配当利回りは現バージョンでは未実装
  - execute_orders は部分利確 / 部分損切りをサポートしていない（SELL は全量クローズ）
- データ依存
  - 多くの関数は prices_daily / raw_financials / features / ai_scores などのテーブル存在を前提とする
  - 本パッケージでは kabusys.data.* の一部ユーティリティ（zscore_normalize, schema, calendar_management 等）を参照しているため、これらの実装とスキーマ準備が必要
- .env 読み込みの挙動
  - OS 環境変数が優先され、.env.local は .env をオーバーライドする（ただし OS 環境変数は保護される）
  - 必須 env が欠けている場合は Settings プロパティが ValueError を投げるため、起動前に .env を整備すること

今後の予定（提案）
- 部分利確・トレーリングストップ・保有日数での時間決済の実装
- PBR / 配当利回り等のバリューファクター追加
- テストカバレッジ（特にエッジケースのトランザクション処理・欠損値ハンドリング）
- ドキュメント化（使用例・マイグレーション手順・DB スキーマ定義）