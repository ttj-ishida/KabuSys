CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従って記載しています。  
リリースポリシー: semantic versioning を想定。

Unreleased
----------

（現在なし）

0.1.0 - 2026-03-22
-----------------

Added
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージ情報:
    - src/kabusys/__init__.py にて __version__ = "0.1.0"、主要サブパッケージを __all__ で公開（data, strategy, execution, monitoring）。
- 環境設定/ロード機能（src/kabusys/config.py）
  - .env ファイル（および .env.local）と OS 環境変数から設定を読み込む自動ロード機能を実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - プロジェクトルートの検出は __file__ を起点に .git または pyproject.toml を探索（CWD 非依存）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト等用）。
    - ファイル読み込み失敗時は警告を発行して安全にスキップ。
    - export キーのサポート、クォートやエスケープ、インラインコメント処理などを考慮したパーサ実装。
    - OS 環境変数を保護する protected オプション（.env.local による上書き制御）。
  - Settings クラスを提供し、アプリケーション設定をプロパティ経由で取得:
    - J-Quants / kabuステーション / Slack / データベースパス（duckdb/sqlite）などの必須・既定値項目を用意。
    - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL（DEBUG/INFO/...）のバリデーション。
    - is_live / is_paper / is_dev のブールプロパティを提供。
- 研究（research）モジュール群
  - src/kabusys/research/factor_research.py
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率を計算（prices_daily を参照）。
    - calc_volatility: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を計算（target_date 以前の最新財務データを使用）。
    - 各関数は (date, code) をキーとする辞書リストを返却。欠損やデータ不足時は None を適切に扱う。
  - src/kabusys/research/feature_exploration.py
    - calc_forward_returns: 指定日から各ホライズン（デフォルト [1,5,21]）先の将来リターンを計算。
    - calc_ic: ファクターと将来リターン間の Spearman IC（ランク相関）を計算。サンプル不足時は None。
    - factor_summary: 指定カラム群の count/mean/std/min/max/median を計算。
    - rank: 同順位は平均ランクで扱うランク付けユーティリティ（round による丸めで ties を安定化）。
  - research パッケージ __all__ の整備。
- 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
  - build_features(conn, target_date): research 側の生ファクターを取得し統合、ユニバースフィルタ、Z スコア正規化、±3 でのクリップを実施して features テーブルへ日付単位の置換（冪等）を行う。
    - ユニバースフィルタ: 最低株価（300 円）・20日平均売買代金 5 億円を適用。
    - データ欠損や非有限値は除外。
    - トランザクション＋バルク挿入で原子性を保証し、失敗時はロールバックして警告ログ。
- シグナル生成（src/kabusys/strategy/signal_generator.py）
  - generate_signals(conn, target_date, threshold=0.60, weights=None):
    - features と ai_scores を統合して component スコア（momentum, value, volatility, liquidity, news）を計算。
    - デフォルト重みやユーザ指定 weights の検証・正規化（合計 1.0 に再スケール）。無効なキー/値はスキップ。
    - AI ニューススコア（ai_score）と市場レジーム（regime_score）を利用し、Bear レジーム検出時は BUY を抑制。
    - BUY 生成は閾値超過、SELL はストップロス（-8%）とスコア低下で判定。保有銘柄で features が欠ける場合は score=0 と見なして SELL を検討。
    - SELL 優先ポリシー: SELL 対象は BUY から除外し、ランクを再付与。
    - signals テーブルへ日付単位の置換（トランザクション＋バルク挿入）。
    - ルックアヘッドバイアス回避のため target_date 時点のデータのみ参照。
- バックテストフレームワーク（src/kabusys/backtest/）
  - simulator.py
    - PortfolioSimulator: メモリ内ポートフォリオ管理、BUY/SELL の擬似約定（始値にスリッページ適用、手数料モデル、BUY の資金調整ロジック、SELL は全量クローズ）、mark_to_market で日次スナップショット記録。
    - TradeRecord / DailySnapshot dataclass を定義。
    - 実装上の注意点: SELL は全量クローズのみ（部分エグジット非対応）。欠損価格は WARN を出して 0 評価。
  - metrics.py
    - バックテスト評価指標を計算（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, total_trades）。
    - calc_metrics: history と trades から BacktestMetrics を生成。
  - engine.py
    - run_backtest(conn, start_date, end_date, ...): 本番 DB からインメモリ DuckDB へ必要データをコピーして日次ループでシミュレーションを実行。
      - _build_backtest_conn: 指定期間のテーブルを安全にコピー（features / prices_daily / ai_scores / market_regime 等をフィルタ付きでコピー）。market_calendar は全件コピー。コピー失敗は警告でスキップ。
      - 日次処理フローを実装: 前日シグナル約定 → positions 書き戻し → 時価評価 → generate_signals 呼び出し → ポジションサイジングと買付。
      - DB 汚染を防ぐためインメモリ接続を利用。
    - run_backtest は BacktestResult（history, trades, metrics）を返却。
- 戦略パッケージのエクスポート整備（src/kabusys/strategy/__init__.py）。
- 安全性・運用上の配慮
  - 多くの DB 書き込み操作でトランザクション（BEGIN/COMMIT/ROLLBACK）を使用し、失敗時は ROLLBACK を試行・警告ログ。
  - 入力値検証（weights の数値性チェック、horizons の範囲チェック、環境値の許容値チェックなど）。
  - ログ出力を適切に配置して異常系（価格欠損、読み取り失敗、無効な入力）を通知。

Changed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Security
- 初回リリースのため該当なし。

Known limitations / Notes
- 未実装の戦略ロジック（feature_engineering / signal_generator 内で言及）
  - トレーリングストップ（peak_price に依存）や保有期間による時間決済は未実装（positions テーブル拡張が必要）。
  - PBR・配当利回り等のバリューファクターは現バージョンでは未実装。
- generate_signals の AI ニューススコアは ai_scores が未登録時に中立値 0.5 で補完する実装。regime 判定はサンプル数が不足する場合は Bear とみなさない。
- Simulator の BUY は alloc（資金配分）に基づく整数株数での発注。部分株対応なし。
- 外部依存: DuckDB を主要 DB 層として想定。pandas 等の heavy ライブラリには依存しない設計。
- データ読み込み/コピーで例外が発生したテーブルは警告でスキップするため、バックテスト実行時に欠落データがある場合は挙動に注意。

開発者向けメモ
- 環境変数の自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト実行時に便利です）。
- settings の必須項目（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）は _require() により未設定時に ValueError を投げます。
- Feature/Signal の書き込みは日付単位で完全置換するため、再実行は冪等です。

今後の予定（アイデア）
- 部分利確・部分損切り、トレーリングストップの実装（positions テーブル拡張）。
- PBR / 配当利回りなどバリューファクターの拡充。
- 追加のリスク管理ルール（ポジション上限、個別スリッページモデルの改良）。
- monitoring / execution 層の実装（現在は strategy と backtest が中心）。