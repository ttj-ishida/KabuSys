CHANGELOG
=========

すべての注目すべき変更点をこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠しています。

Unreleased
----------

- （なし）

0.1.0 - 2026-03-22
------------------

Added
- パッケージ初期リリース: kabusys 0.1.0
  - 日本株自動売買システムのコアライブラリを追加。

- 環境設定管理（kabusys.config）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動読み込みする仕組みを実装。OS 環境変数は保護され、.env.local は .env をオーバーライド可能。
  - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - 行パーサーは export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントの扱いに対応。
  - Settings クラスを提供し、以下の必須/既定設定をプロパティで取得可能:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（既定: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN（必須）
    - SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH（既定: data/kabusys.duckdb）
    - SQLITE_PATH（既定: data/monitoring.db）
    - KABUSYS_ENV（valid: development, paper_trading, live）
    - LOG_LEVEL（valid: DEBUG, INFO, WARNING, ERROR, CRITICAL）
    - ライフサイクル判定用の is_live / is_paper / is_dev プロパティ

- 研究（research）モジュール
  - ファクター計算（kabusys.research.factor_research）
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev を計算（200日移動平均はデータ不足時 None）。
    - calc_volatility: 20日 ATR、相対ATR（atr_pct）、20日平均売買代金、出来高比率を計算。true_range の NULL 伝播を厳密に扱う。
    - calc_value: raw_financials テーブルから直近の財務指標を取得し PER / ROE を計算（EPS が 0/欠損の時は PER=None）。
    - 全関数は DuckDB 接続（prices_daily / raw_financials）を受け取り、外部 API や DB 書き込みを行わない純粋関数設計。
  - 特徴量探索（kabusys.research.feature_exploration）
    - calc_forward_returns: 指定日から複数ホライズン（デフォルト [1,5,21] 営業日）の将来リターンをまとめて取得。
    - calc_ic: ファクターと将来リターンの Spearman（ランク相関）IC 計算（有効レコードが 3 件未満の場合 None を返す）。
    - factor_summary: 指定カラムの count/mean/std/min/max/median を算出（None を除外）。
    - rank: 同順位は平均ランクで扱い、浮動小数点誤差対策として round(..., 12) で丸めてからランク付け。
  - research パッケージの __all__ を整備して主要関数をエクスポート。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - build_features(conn, target_date)
    - research モジュールから生ファクターを取得し、ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
    - 指定の数値カラムを Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）、±3 でクリップして外れ値を抑制。
    - features テーブルへ日付単位で置換（DELETE→INSERT をトランザクションで実施）することで冪等性を担保。
    - 参照価格は target_date 以前の最新終値を使用（ルックアヘッド回避、休場日対応）。

- シグナル生成（kabusys.strategy.signal_generator）
  - generate_signals(conn, target_date, threshold=0.60, weights=None)
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算し、重み付き合算で final_score を算出。
    - デフォルト重みは momentum:0.40, value:0.20, volatility:0.15, liquidity:0.15, news:0.10。weights 引数は妥当性チェック・スケーリングを行う。
    - AI ニューススコアは未登録時に中立 0.5 で補完。欠損コンポーネントは中立 0.5 で補完して不当な降格を防止。
    - Bear レジーム判定: ai_scores の regime_score 平均が負（かつ十分なサンプル数）で BUY を抑制。
    - BUY 判定は threshold（デフォルト 0.60）以上、SELL 判定は positions と現在価格を参照してストップロス（-8%）またはスコア低下で判定。
    - signals テーブルへ日付単位の置換（DELETE→INSERT、トランザクション処理）で冪等性を担保。
    - ロギングによる警告: features が空の場合や位置情報・価格欠損時の挙動を明示。

- バックテストフレームワーク（kabusys.backtest）
  - ポートフォリオシミュレータ（kabusys.backtest.simulator）
    - PortfolioSimulator: メモリ内で cash/positions/cost_basis を管理、SELL を先に処理してから BUY（資金確保）、BUY は配分に基づいて株数を算出・手数料・スリッページを適用。
    - mark_to_market で終値評価・DailySnapshot を記録。終値欠損時は 0 評価で WARNING を出力。
    - TradeRecord / DailySnapshot のデータモデルを提供。
  - バックテストエンジン（kabusys.backtest.engine）
    - run_backtest(conn, start_date, end_date, initial_cash=10_000_000, slippage_rate=0.001, commission_rate=0.00055, max_position_pct=0.20)
      - 本番 DuckDB から日付範囲をフィルタしてインメモリ DuckDB にデータをコピー（prices_daily, features, ai_scores, market_regime, market_calendar 等）。signals/positions を汚さずにテスト可能。
      - 日次ループ: 前日シグナルを当日の始値で約定 → positions を DB に書き戻し → 終値評価でスナップショット → generate_signals を呼び出して翌日のシグナルを生成 → シグナルに基づき発注量を決定して次ループへ。
      - get_trading_days（calendar_management）を使用して営業日列を取得。
  - バックテスト指標（kabusys.backtest.metrics）
    - calc_metrics(history, trades) を通じて以下を算出:
      - CAGR、Sharpe Ratio（無リスク金利=0）、Max Drawdown、Win Rate、Payoff Ratio、Total Trades
    - 内部実装では年次化のため 365 日／252 営業日等を使用。エッジケース（データ不足、分母ゼロ等）に対する安全ガードを実装。

- パッケージエクスポート
  - strategy と backtest の主要 API を __init__ でエクスポート（build_features, generate_signals, run_backtest 等）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Known limitations / Notes
- _generate_sell_signals 内で設計上言及されている未実装のエグジット条件:
  - トレーリングストップ（peak_price に基づく -10%）
  - 時間決済（保有 60 営業日超過）
  これらは positions テーブルに peak_price / entry_date が必要で、現状未実装。
- calc_value は現時点で PBR・配当利回りをサポートしていない（将来拡張予定）。
- research.feature_exploration は pandas 等の外部ライブラリに依存せず標準ライブラリ＋DuckDBで実装されているため、大規模データの一部操作ではパフォーマンスチューニングの余地あり。
- build_features / generate_signals は DuckDB のスキーマ（features, ai_scores, positions, signals, prices_daily 等）を前提としている。スキーマ初期化用のユーティリティ（kabusys.data.schema.init_schema 等）と組み合わせて使用すること。

開発者向けメモ
- 環境自動読み込みはプロジェクトルート検出に __file__ の親ディレクトリ列挙を使用するため、配布/インストール後も CWD に依存せず動作するよう設計。
- トランザクション処理: features / signals の日付単位置換は BEGIN/COMMIT/ROLLBACK を使用して原子性を確保。ROLLBACK 失敗時は警告ログを出力。
- 重みの取り扱い: generate_signals の weights パラメータは部分的に指定しても既定値で補完され、合計が 1.0 でない場合は再スケールされる。無効なキーや負値・非数値は無視して警告を出す。

ライセンス
- （省略）パッケージのライセンス情報は別途参照してください。