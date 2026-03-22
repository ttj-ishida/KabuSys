# Changelog

すべての注目すべき変更点を記録します。本ファイルは Keep a Changelog の形式に準拠しています。  

現在のリリース: 0.1.0 — 2026-03-22

---

## [0.1.0] - 2026-03-22

### 追加 (Added)
- パッケージ基本
  - kabusys パッケージの初期リリース。バージョンは `0.1.0`。

- 設定 / 環境変数管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを追加。
  - 自動 .env ロード機構:
    - プロジェクトルートを `.git` または `pyproject.toml` から探索して特定。
    - OS 環境変数 > .env.local > .env の優先順位で読み込み。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
    - OS の既存環境変数を保護するため protected セットを使用して上書きを制御。
  - .env パーサの実装:
    - export プレフィックス対応、シングル/ダブルクォート内のエスケープ、インラインコメント判定（クォート有無で挙動を分ける）等に対応。
  - Settings が提供する主要プロパティ:
    - JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、KABU_API_BASE_URL（デフォルトローカル）、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID
    - データベースパス: DUCKDB_PATH（デフォルト data/kabusys.duckdb）、SQLITE_PATH（デフォルト data/monitoring.db）
    - 環境種別（KABUSYS_ENV）検証（development / paper_trading / live）
    - LOG_LEVEL 検証（DEBUG, INFO, WARNING, ERROR, CRITICAL）
    - ヘルパー: is_live / is_paper / is_dev

- 研究 (Research) モジュール (src/kabusys/research/)
  - factor_research:
    - calc_momentum: mom_1m / mom_3m / mom_6m、200日移動平均乖離率（ma200_dev）を DuckDB の prices_daily テーブルから計算。
    - calc_volatility: 20日 ATR（atr_20）、相対ATR（atr_pct）、20日平均売買代金（avg_turnover）、出来高比率（volume_ratio）を計算。true_range の NULL 伝播を考慮。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を計算（最新の財務レコードを target_date 以前から取得）。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21] 営業日）で将来リターンを計算。クエリ最適化のため max_horizon の 2 倍の日数でスキャン範囲を限定。
    - calc_ic: スピアマンのランク相関（IC）を計算。有効レコードが 3 未満の場合は None を返す。
    - factor_summary: 指定カラムの count/mean/std/min/max/median を計算（None は除外）。
    - rank: 同順位は平均ランクで計算、浮動小数点の誤差対策に round(..., 12) を利用。
  - research パッケージの __all__ エクスポートを整備。

- 特徴量エンジニアリング (src/kabusys/strategy/feature_engineering.py)
  - build_features(conn, target_date):
    - research の calc_momentum/calc_volatility/calc_value を呼び出して生ファクターを収集。
    - ユニバースフィルタを適用（株価 >= 300 円、20日平均売買代金 >= 5 億円）。
    - 指定の数値カラムを Z スコア正規化（外部 zscore_normalize を利用）、±3 でクリップして外れ値影響を抑制。
    - features テーブルへ日付単位で置換（DELETE + bulk INSERT）することで冪等性と原子性を確保。
    - ロギング（処理行数情報）を出力。

- シグナル生成 (src/kabusys/strategy/signal_generator.py)
  - generate_signals(conn, target_date, threshold=0.60, weights=None):
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum, value, volatility, liquidity, news）を計算。
    - AI ニューススコアは存在すれば sigmoid 変換、未登録時は中立値で補完。
    - デフォルト重みを定義（momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）。ユーザー渡しの weights は検証・補完・正規化。
    - Bear レジーム判定（ai_scores の regime_score の平均が負で、サンプル数が閾値以上の場合）により BUY シグナルを抑制。
    - BUY シグナルは final_score >= threshold で生成（Bear 時は抑制）。
    - SELL（エグジット）条件を実装:
      - ストップロス: 終値 / avg_price - 1 < -8%（最優先）
      - スコア低下: final_score が threshold 未満
      - SELL は保有銘柄の価格欠損時にスキップし、features に存在しない保有銘柄は score=0.0 扱いで SELL 対象化
      - 一部未実装の条件（トレーリングストップ・時間決済）はドキュメント化（positions テーブルに peak_price / entry_date が必要）
    - signals テーブルへ日付単位で置換（DELETE + bulk INSERT）することで冪等性と原子性を確保。
    - ロギング（生成数・Bear 検知など）を出力。

- バックテストフレームワーク (src/kabusys/backtest/)
  - simulator:
    - PortfolioSimulator によるメモリ内ポートフォリオ管理を実装。
    - execute_orders:
      - SELL を先に処理してから BUY（資金確保）。
      - SELL は保有全量クローズ（部分クローズ未対応）。
      - スリッページと手数料モデルを適用（BUY は始値*(1+slippage)、SELL は始値*(1-slippage)）。
      - BUY: alloc から購入株数を計算、手数料込みで現金不足時は株数を再計算。
      - 取引は TradeRecord に記録（BUY は realized_pnl=None、SELL は realized_pnl を計算）。
    - mark_to_market:
      - 終値で時価評価して DailySnapshot を保存。終値欠損時は 0 評価で WARNING ログ。
  - metrics:
    - calc_metrics(history, trades) として以下を計算:
      - CAGR、Sharpe Ratio（無リスク金利=0、年次化: sqrt(252)）、Max Drawdown、Win Rate、Payoff Ratio、total_trades
    - 各内部計算関数を実装（エッジケース処理あり: データ不足/ゼロ除算回避など）。
  - engine:
    - run_backtest(conn, start_date, end_date, initial_cash=10_000_000, slippage_rate=0.001, commission_rate=0.00055, max_position_pct=0.20)
      - 本番 DuckDB からインメモリ DuckDB へデータをコピーしてバックテスト用環境を構築（signals / positions を汚染しない）。
      - コピー対象テーブルは日付範囲で絞り込み（prices_daily, features, ai_scores, market_regime）および market_calendar を全件コピー。
      - 日次ループ:
        1. 前日シグナルを当日の始値で約定（simulator.execute_orders）
        2. positions テーブルへシミュレータの保有を書き戻し（generate_signals の SELL 判定に使用）
        3. 終値で時価評価してスナップショットを記録
        4. generate_signals を呼んで翌日のシグナルを生成
        5. ポジションサイジング（max_position_pct を考慮）して翌日の発注リストを作成
      - run_backtest は BacktestResult(history, trades, metrics) を返す。
    - 内部ユーティリティ:
      - _build_backtest_conn: in-memory にスキーマを初期化してデータをコピー。
      - 価格取得ヘルパー (_fetch_open_prices / _fetch_close_prices)、positions 書き込み、当日 signals 読み取り等を提供。

- パッケージエクスポート整理
  - kabusys.strategy、kabusys.research、kabusys.backtest の __all__ を設定し、主要関数・クラスを公開。

### ドキュメント化 / 設計上の注意点 (Documentation / Notes)
- ルックアヘッドバイアス防止のため、すべての計算は target_date 時点までのデータのみを使用する方針を明示。
- research モジュールは外部ライブラリ（pandas 等）に依存しない実装を目指す。
- トランザクション（BEGIN/COMMIT/ROLLBACK）を用いて features / signals テーブルへの日付単位置換を行い、失敗時に ROLLBACK を試みる実装を追加（ROLLBACK に失敗した場合は警告ログ）。

### 未実装 / 制限 (Known limitations)
- signal_generator のエグジット条件に記載された一部（トレーリングストップ、時間決済）は未実装。positions テーブルに peak_price / entry_date 等の追加が必要。
- 部分利確 / 部分損切りは PortfolioSimulator では未対応（SELL は保有全量クローズ）。
- 一部のデータ/テーブル（例: data.stats の具体実装、data.schema の実装等）はこの差分には含まれておらず、外部モジュール依存が残る。
- run_backtest のポジションサイジング処理はファイル末尾で開始しているが、差分により一部ロジックが省略されている箇所がある（実装の続きに依存）。

### 互換性 / 破壊的変更 (Breaking Changes)
- 初期リリースのためなし。

### セキュリティ (Security)
- 機密情報（API トークン等）は Settings._require による必須チェックで明示。README や .env.example に基づく運用を想定。

---

（注）この CHANGELOG は提供されたコードベースから仕様および実装を推測して作成しています。実際のリリースノートとして公開する際は、リポジトリのコミット履歴やプロジェクトドキュメントと突合して内容を確定してください。