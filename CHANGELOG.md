CHANGELOG
=========

この CHANGELOG は "Keep a Changelog" の形式に準拠しています。  
このファイルはリポジトリ内のコードから推測して作成した初期の変更履歴です（実際の履歴が存在する場合は適宜編集してください）。

フォーマット:
- Unreleased: 今後の変更（空）
- バージョンごとに追加された主な機能・変更点・既知の制約を記載

Unreleased
----------

- なし

0.1.0 - 2026-03-22
------------------

Added
- 初回公開: KabuSys v0.1.0
  - パッケージルート: src/kabusys/__init__.py（__version__ = "0.1.0"）
- 設定管理
  - kabusys.config.Settings: 環境変数からアプリ設定を取得するユーティリティを追加
    - 必須値チェック（_require）により未設定時は ValueError を送出
    - 公開プロパティ例:
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
      - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
      - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
      - SQLITE_PATH（デフォルト: data/monitoring.db）
      - KABUSYS_ENV（validation: development/paper_trading/live）
      - LOG_LEVEL（validation）
      - ユーティリティ: is_live / is_paper / is_dev
  - .env 自動ロード機能
    - 自動ロード順序: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能
    - .env パーサ実装:
      - export KEY=val 形式対応
      - シングル・ダブルクォート内のバックスラッシュエスケープ対応
      - クォートなしの行でのインラインコメント処理（# 前が空白/タブならコメントとみなす）
    - .env 読み込みはプロジェクトルート（.git または pyproject.toml）発見時のみ実行
    - OS 環境変数は protected として .env による上書きを防止
- 戦略（strategy）
  - feature_engineering.build_features(conn, target_date)
    - research モジュールの生ファクター（momentum / volatility / value）をマージし、
      ユニバースフィルタ（最低株価 300 円・20日平均売買代金 5 億円）を適用
    - 指定列を Z スコア正規化（zscore_normalize を使用）、±3でクリップ
    - features テーブルへ日付単位の置換（トランザクション + バルク挿入で冪等化）
    - 標準化対象列: mom_1m, mom_3m, atr_pct, volume_ratio, ma200_dev
  - signal_generator.generate_signals(conn, target_date, threshold=0.60, weights=None)
    - features と ai_scores を統合して各銘柄の final_score を計算
    - コンポーネントスコア: momentum / value / volatility / liquidity / news
    - スコア変換に sigmoid を使用、欠損コンポーネントは中立 0.5 で補完
    - デフォルト重み: momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10
    - weights の検証・補完・再スケールを実装（無効なキー・値は無視）
    - Bear レジーム検知（ai_scores の regime_score 平均が負かつサンプル数 >= 3）
      - Bear 時は BUY シグナルを抑制
    - SELL（エグジット）ルール実装:
      - ストップロス: 終値/avg_price - 1 < -8%
      - スコア低下: final_score < threshold
      - positions テーブルや価格欠損時の挙動（ログ出力・スキップ）を明確化
    - signals テーブルへ日付単位の置換（冪等）
    - SELL 優先ポリシー（SELL 銘柄は BUY から除外、BUY にランク付け）
- Research（research）
  - factor_research: calc_momentum / calc_volatility / calc_value
    - prices_daily, raw_financials を用いてモメンタム・ボラティリティ・バリュー系ファクターを算出
    - 各関数は (date, code) をキーとする dict のリストを返す
  - feature_exploration:
    - calc_forward_returns(conn, target_date, horizons=[1,5,21]) — 将来リターンを一括取得
    - calc_ic(factor_records, forward_records, factor_col, return_col) — Spearman ランク相関（IC）を計算
    - factor_summary(records, columns) — 各ファクター列の count/mean/std/min/max/median を計算
    - rank(values) — タイを平均ランクで処理するランキング実装
  - research パッケージは zscore_normalize を再エクスポート
- Backtest（backtest）
  - simulator.PortfolioSimulator
    - メモリ内でのポートフォリオ管理・擬似約定・スナップショット記録を提供
    - execute_orders: SELL を先、BUY を後で処理。BUY は割当額から株数計算（切り捨て）。
    - スリッページ・手数料モデルを反映（entry/exit に slippage_rate/commission_rate を適用）
    - mark_to_market で DailySnapshot を記録（終値欠損は警告して 0評価）
  - metrics.calc_metrics(history, trades) 等、バックテスト評価指標（CAGR, Sharpe, Max DD, Win rate, Payoff ratio, total trades）
  - engine.run_backtest(conn, start_date, end_date, initial_cash=10_000_000, slippage_rate=0.001, commission_rate=0.00055, max_position_pct=0.20)
    - 本番 DB からインメモリ DuckDB へ必要テーブルをコピーし（signals/positions を汚染しない）
    - 日次ループで generate_signals を呼び出し、Simulator と連携して売買をシミュレーション
    - positions テーブルへの書き戻し、価格取得、signals 読込などのユーティリティを実装
    - デフォルト設定やコピー対象テーブル、エラー時の警告ロギングを実装

Changed
- 新規リリースのため該当なし

Fixed
- 新規リリースのため該当なし

Deprecated
- なし

Removed
- なし

Security
- なし

既知の制約・実装上の注意
- feature_engineering:
  - merged レコードでは avg_turnover をユニバースフィルタに使用するが、features テーブルに avg_turnover 自体は保存しない（フィルタ用のみ）。
- signal_generator:
  - 未実装のエグジット条件:
    - トレーリングストップ（peak_price に依存）と時間決済（entry_date に依存）はコメントとして記載されているが未実装。positions テーブルに peak_price / entry_date が必要。
  - AI スコア未登録の銘柄はニューススコアを中立（0.5）で補完する。
  - ai_scores のサンプル数が _BEAR_MIN_SAMPLES 未満の場合は Bear 判定としない（誤判定防止）。
- config:
  - .env パーサは一般的なケースに対応するが、特殊な .env フォーマット（複雑な改行を含むクォート等）は未検証。
  - OS 環境変数の上書きを防ぐため .env の上書きを制御している（デフォルトは上書き不可、.env.local は override=True）。
- backtest.engine:
  - 本番 DB からのコピーはテーブル単位で例外発生時にスキップするが、欠損データによりバックテスト結果が変わる可能性がある。ログ出力を確認すること。
- テスト・CI:
  - このスナップショットからはテストコードは含まれていないため、テスト実行や継続的インテグレーションの追加を推奨。

公開 API（主な関数・クラス）
- kabusys.settings (Settings インスタンス)
- kabusys.strategy.build_features(conn, target_date)
- kabusys.strategy.generate_signals(conn, target_date, threshold=..., weights=...)
- kabusys.research.calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary / rank
- kabusys.backtest.run_backtest(conn, start_date, end_date, ...)
- kabusys.backtest.PortfolioSimulator, DailySnapshot, TradeRecord, BacktestMetrics, BacktestResult

開発者向けメモ
- テスト環境や一部のユーティリティで自動 .env 読み込みを抑制したい場合:
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定する
- DuckDB を利用した処理はトランザクション（BEGIN/COMMIT/ROLLBACK）で原子性を確保しているが、例外発生時に ROLLBACK に失敗すると WARNING が出力されるためログを確認すること
- weights のユーザー指定は妥当性検査を行い、合計が 1.0 でなければ再スケールされる。負値・非数値は無視される。

貢献・修正提案
- トレーリングストップや時間決済の実装（positions に peak_price / entry_date を持たせる設計）
- .env パースの追加ケース（複数行クォート、特殊文字）
- 単体テストの追加（各モジュールの境界値・欠損データ対応の検証）
- パフォーマンス改善（大規模銘柄数での DuckDB クエリ最適化、バックテスト接続コピーの効率化）

-- END --