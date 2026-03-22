# Changelog

すべての注目すべき変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。

現在のリリース: 0.1.0

### [0.1.0] - 2026-03-22
初回リリース。日本株自動売買ライブラリ「KabuSys」のコア機能を実装しました。

Added
- パッケージ基盤
  - パッケージエントリポイントを追加（kabusys/__init__.py）。バージョンは 0.1.0。
  - public API のエクスポートを定義（strategy, execution, monitoring を想定）。
- 環境設定管理（kabusys/config.py）
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。プロジェクトルート（.git または pyproject.toml）を起点に探索するため、CWD に依存しない動作を実現。
  - .env 自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化可能。
  - .env パーサーの強化:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート内でのバックスラッシュエスケープを正しく処理。
    - インラインコメントの扱い（クォート有無での差異）に対応。
    - ファイル読み込み失敗時は警告を出力して読み込みを継続。
  - Settings クラスを提供し、J-Quants / kabuAPI / Slack / DB パス / 実行環境（development/paper_trading/live）/ログレベルなどの設定を環境変数から取得。必須値は未設定時に明示的なエラーを送出。
  - デフォルト値や入力検証（KABUSYS_ENV, LOG_LEVEL）を実装。
- 戦略（kabusys/strategy）
  - 特徴量エンジニアリング（feature_engineering.build_features）
    - research モジュールで算出した生ファクターをマージして正規化（Zスコア）、±3 でクリップし、features テーブルへ日付単位で UPSERT（DELETE+INSERT）する処理を実装。
    - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）を実装。
    - DuckDB を用いたクエリ設計（休場日や当日欠損を考慮して target_date 以前の最新価格を参照）。
    - トランザクションと例外時のロールバック処理を実装し、原子性を確保。
  - シグナル生成（signal_generator.generate_signals）
    - features と ai_scores を統合して銘柄ごとの final_score を計算。モメンタム/バリュー/ボラティリティ/流動性/ニュース（AI）をコンポーネントとして重みづけする設計を実装。
    - デフォルトの重みとしきい値（BUY 閾値 0.60）を提供。外部から重みを渡せるが、検証・正規化（不正値スキップ、合計が 1 に再スケール）を行う。
    - AI レジームスコアにより Bear 判定を行い、Bear 相場では BUY シグナルを抑制。
    - 保有ポジションに対するエグジット判定（ストップロス -8% およびスコア低下）を実装。SELL シグナルと BUY シグナルは日付単位で置換（DELETE+INSERT）して冪等に保存。
    - SELL 優先ポリシー（SELL 対象は BUY から除外）を適用。
    - ロギングで重要な状態（空の features、価格欠損、無効な weight 値、ROLLBACK 失敗など）を記録。
- Research（kabusys/research）
  - ファクター計算（factor_research）
    - モメンタム（1M/3M/6M リターン、MA200 乖離率）、ボラティリティ（20日 ATR、相対 ATR、平均売買代金、出来高比率）、バリュー（PER, ROE）を DuckDB クエリで算出する関数を提供。
    - 過去データのスキャン範囲（バッファ）を考慮した設計。データ不足時は None を返す挙動を明確化。
  - 特徴量探索（feature_exploration）
    - 将来リターン計算（calc_forward_returns）：複数ホライズン（デフォルト 1,5,21 営業日）に対するリターンを一括で取得する SQL 実装。
    - IC（calc_ic）: スピアマンのランク相関（ties を平均ランクで扱う）を計算。サンプル不足（<3）は None を返す。
    - 統計サマリー（factor_summary）と rank ユーティリティを提供。
  - 研究用ユーティリティ（kabusys/research.__init__）で主要関数をエクスポート。外部依存を最小化（標準ライブラリ + DuckDB）。
- バックテスト（kabusys/backtest）
  - シミュレータ（simulator.PortfolioSimulator）
    - メモリ内でポートフォリオ状態（cash, positions, cost_basis）を管理。BUY/SELL の擬似約定を実装。
    - スリッページと手数料を考慮した約定ロジック（BUY は始値 * (1 + slippage)、SELL は始値 * (1 - slippage)）。
    - SELL を先に処理し全量クローズ（部分利確非対応）。BUY は資金に応じて株数を切り捨てで計算。
    - mark_to_market により終値ベースで DailySnapshot を記録。価格欠損時は 0 評価し WARNING を出力。
    - TradeRecord / DailySnapshot のデータクラスを提供。
  - メトリクス（metrics.calc_metrics）
    - CAGR, Sharpe, Max Drawdown, win rate, payoff ratio, total trades を計算するユーティリティを実装。
  - バックテストエンジン（engine.run_backtest）
    - 本番 DB からインメモリ DuckDB へ必要テーブルをコピー（期間フィルタリング）してバックテスト用接続を構築する機能を提供（signals/positions を汚染しない設計）。
    - 日次ループ: 前日シグナルの約定 → positions 書き戻し → 終値で評価 → generate_signals 実行 → ポジションサイジング（max_position_pct）→ 次日約定の順で処理。
    - _build_backtest_conn で market_calendar を全件コピー、その他必要テーブルは日付範囲でコピー。コピー失敗は警告でスキップ。
    - run_backtest は BacktestResult（history, trades, metrics）を返す。
- トランザクションと堅牢性
  - features / signals への書き込みはトランザクション（BEGIN/COMMIT）で行い、例外時は ROLLBACK を試行。ROLLBACK 失敗時はログ出力。

Changed
- 該当なし（初回リリースのため履歴なし）

Fixed
- 該当なし（初回リリースのため履歴なし）

Known limitations / Notes
- 一部の外部コンポーネント（例: kabusys.data.schema, kabusys.data.stats, kabusys.data.calendar_management）への依存が存在するため、バックエンド DB スキーマ・ユーティリティは別途提供が必要です。
- 一部の戦略ルール（例: トレーリングストップ、時間決済）は設計メモとして言及されているが未実装。
- simulator の BUY は部分的なポジション分割/リバランスや分割株の取扱い等の高度な振る舞いは未対応。
- research モジュールは DuckDB の存在を前提とし、外部ライブラリ（pandas 等）は利用していません。

今後の予定（例）
- 部分利確やトレーリングストップなどエグジットロジックの拡張
- execution 層の実装（kabu API との連携）
- 単体テスト・CI の整備とドキュメント拡充

以下は参照用の主要ファイル一覧（実装済み）
- src/kabusys/config.py
- src/kabusys/strategy/feature_engineering.py
- src/kabusys/strategy/signal_generator.py
- src/kabusys/research/factor_research.py
- src/kabusys/research/feature_exploration.py
- src/kabusys/backtest/simulator.py
- src/kabusys/backtest/metrics.py
- src/kabusys/backtest/engine.py
- src/kabusys/__init__.py

以上。