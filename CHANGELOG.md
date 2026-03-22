# CHANGELOG

すべての注目すべき変更はこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠します。

## [Unreleased]

## [0.1.0] - 2026-03-22
初期リリース。日本株自動売買システム「KabuSys」のコア機能群を追加しました。主な追加項目は以下の通りです。

### Added
- パッケージ初期化
  - パッケージバージョンを設定（kabusys.__version__ = "0.1.0"）。
  - パッケージの公開 API として data, strategy, execution, monitoring を __all__ に定義。

- 環境設定 / .env 管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを追加。
  - 自動ロードの優先順位: OS 環境変数 > .env.local > .env。プロジェクトルートは .git または pyproject.toml を基準に自動検出。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をサポート。
  - .env パーサ (_parse_env_line) にて:
    - export KEY=val 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応。
    - インラインコメントの扱い（クォートあり/なしの違い）や無効行の無視処理を実装。
  - _load_env_file による保護されたキー（既存 OS 環境変数の保護）と override の挙動。
  - 必須 env を取得する _require と各種設定プロパティ（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）。
  - 環境種別（KABUSYS_ENV）の検証（development, paper_trading, live）や LOG_LEVEL の検証。

- 研究用ファクター計算（kabusys.research.factor_research）
  - モメンタム (calc_momentum): 1M/3M/6M リターン、200 日移動平均乖離率（ma200_dev）。
  - ボラティリティ (calc_volatility): 20 日 ATR、相対 ATR (atr_pct)、20 日平均売買代金、出来高比 (volume_ratio)。
  - バリュー (calc_value): PER（price / EPS）、ROE（raw_financials からの最新値）。
  - いずれも DuckDB の prices_daily / raw_financials テーブルを参照し、データ不足時は None を返す仕様。

- 特徴量探索ツール（kabusys.research.feature_exploration）
  - 将来リターン計算 (calc_forward_returns): 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。
  - IC（Information Coefficient）計算 (calc_ic): factor と forward return の Spearman ランク相関を計算（有効サンプル数 3 未満で None）。
  - ランク関数 (rank) とファクター統計サマリー (factor_summary) を実装。
  - 外部ライブラリに依存せず標準ライブラリのみでの実装を意図。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - build_features(conn, target_date):
    - research の calc_momentum / calc_volatility / calc_value を利用して生ファクターを取得。
    - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 >= 5 億円）を適用。
    - 指定カラムを Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）、±3 でクリップし外れ値を抑制。
    - 日付単位で features テーブルへ置換（トランザクション + バルク挿入で原子性を確保）。
    - ルックアヘッドバイアス対策として target_date 時点のデータのみを使用。

- シグナル生成（kabusys.strategy.signal_generator）
  - generate_signals(conn, target_date, threshold=0.60, weights=None):
    - features と ai_scores を統合して各成分スコア（momentum / value / volatility / liquidity / news）を算出。
    - 各成分は欠損時に中立値 0.5 で補完、AI スコア未登録時は中立として扱う。
    - final_score を重み付き合算（デフォルト重みを定義、与えられた weights は検証・正規化して使用）。
    - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数 >= 3 の場合）では BUY シグナルを抑制。
    - BUY シグナル閾値（デフォルト 0.60）超で BUY を生成、SELL はエグジット条件（ストップロス -8%、スコア低下）を満たす保有銘柄に対して生成。
    - SELL を優先し、SELL 対象は BUY から除外、signals テーブルへ日付単位で置換。
    - トランザクション処理中の例外で ROLLBACK を試行し失敗時は警告ログ。

  - 実装上の注記:
    - STOP_LOSS_RATE = -0.08（-8%）をサポート。
    - トレーリングストップや時間決済は未実装（positions に peak_price / entry_date が必要）。

- バックテストフレームワーク（kabusys.backtest）
  - ポートフォリオシミュレータ（kabusys.backtest.simulator）
    - PortfolioSimulator クラス:
      - execute_orders: SELL を先、BUY を後に処理。SELL は保有全量クローズ。スリッページ・手数料を考慮した約定処理。
      - マーク・トゥ・マーケット（mark_to_market）で DailySnapshot を記録。終値欠損時は 0 として評価し警告ログ。
      - TradeRecord / DailySnapshot のデータモデルを定義。
  - バックテストエンジン（kabusys.backtest.engine）
    - run_backtest(conn, start_date, end_date, ...):
      - 本番 DuckDB から必要データをコピーしてインメモリ DuckDB を構築（_build_backtest_conn）。signals/positions を汚染しない設計。
      - 日次ループ: 前日シグナルを当日始値で約定 → positions テーブルへ書き戻し → 終値で時価評価→ generate_signals による当日シグナル生成 → 発注リスト作成。
      - DB コピーは日付範囲でフィルタし、market_calendar は全件コピー。
      - 取引毎のポジションサイジング（max_position_pct 等を利用）。
  - バックテスト評価指標（kabusys.backtest.metrics）
    - calc_metrics(history, trades) により BacktestMetrics を計算。
    - 指標: CAGR, Sharpe Ratio（無リスク金利=0）、最大ドローダウン、勝率、Payoff Ratio、トレード総数。
    - 計算の仕様（年次化、標本数条件、0 許容の扱い等）を実装。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Removed
- （初期リリースのため該当なし）

### Security
- 環境変数読み込みにおいて OS 側の環境変数を保護する仕組みを導入（protected keys）。

---

注:
- 多くのモジュールが DuckDB 接続（DuckDBPyConnection）を引数として受け取り、prices_daily / features / ai_scores / raw_financials / market_calendar / positions / signals などのテーブルを前提としています。実行にはスキーマ初期化やデータ投入が必要です（kabusys.data.schema 等を参照）。
- design コメントや未実装メモ（例: トレーリングストップ、時間決済）はコード内に記載されています。必要に応じて実装を拡張してください。