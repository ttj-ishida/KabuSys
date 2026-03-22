CHANGELOG
=========
すべての重要な変更点を記録します。フォーマットは "Keep a Changelog" に準拠しています。

[0.1.0] - 2026-03-22
--------------------

Added
- パッケージ初期リリース。kabusys として以下の主要コンポーネントを実装・公開しました。
  - パッケージ初期化
    - src/kabusys/__init__.py にてバージョン "0.1.0" を設定。
    - パッケージ公開 API に data, strategy, execution, monitoring を含める（execution, monitoring は現時点では薄いスタブ）。
  - 設定・環境変数管理（src/kabusys/config.py）
    - .env / .env.local の自動読み込みを実装（プロジェクトルートを .git または pyproject.toml から探索）。
    - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
    - .env パーサ:
      - 空行 / コメント行（#）の取り扱い、export プレフィックス対応。
      - シングル/ダブルクォート内のバックスラッシュエスケープ対応と閉じクォート検出。
      - クォート無しの場合のインラインコメント処理（'#' の直前が空白/タブの場合にコメントと判定）。
    - .env 読み込み優先順: OS環境変数 > .env.local > .env。OS 環境変数は保護され上書きされない。
    - Settings クラスで各種必須設定の取得を提供（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）。
    - DB パスの既定値: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"。
    - KABUSYS_ENV 値検証（development, paper_trading, live のみ許容）および LOG_LEVEL 検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
    - is_live / is_paper / is_dev ユーティリティプロパティを提供。
  - 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
    - research モジュールで計算した生ファクターを取り込み、正規化・合成して features テーブルへ保存する build_features(conn, target_date) を実装。
    - 処理フロー: momentum/volatility/value の取得 → ユニバースフィルタ（株価 >= 300 円、20日平均売買代金 >= 5億円） → Z スコア正規化（対象列: mom_1m, mom_3m, atr_pct, volume_ratio, ma200_dev） → ±3 でクリップ → 日付単位で置換（DELETE + bulk INSERT）をトランザクションで実施（冪等）。
    - 価格参照は target_date 以前の最新価格を使用し、休場日等の欠損に対応。
  - シグナル生成（src/kabusys/strategy/signal_generator.py）
    - features と ai_scores を統合して final_score を算出し、signals テーブルへ書き込む generate_signals(conn, target_date, threshold, weights) を実装。
    - コンポーネントスコア:
      - momentum: momentum_20, momentum_60, ma200_dev のシグモイド平均
      - value: PER に基づく 1/(1 + per/20)（per が不正なら None）
      - volatility: atr_pct の符号反転をシグモイドに適用（低ボラ高評価）
      - liquidity: volume_ratio のシグモイド
      - news: ai_scores.ai_score をシグモイド（未登録時は中立）
    - final_score は重み付け合算（デフォルト重み: momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）。weights 引数は検証・補正（既知キーのみ、非数値/負値は無視、合計が 1 でない場合は再スケール）。
    - BUY シグナル閾値デフォルト 0.60。Bear レジーム（ai_scores の regime_score の平均が負でサンプル数閾値以上）の場合は BUY を抑制。
    - SELL 条件:
      - ストップロス: 現在終値 / avg_price - 1 <= -0.08（最優先）
      - スコア低下: final_score < threshold
      - positions テーブルに peak_price / entry_date 等が無いため、トレーリングストップや時間決済は未実装（TODO）。
    - signals テーブルへの書き込みも日付単位の置換（トランザクション＋バルク挿入）。
  - 研究（research）モジュール群（src/kabusys/research/）
    - factor_research:
      - calc_momentum(conn, target_date): mom_1m/3m/6m、ma200_dev を計算（MA200 は200行以上で有効）。
      - calc_volatility(conn, target_date): 20日 ATR、atr_pct、20日平均売買代金、volume_ratio を計算。true_range の NULL 伝播を制御し、部分窓でも正しく処理。
      - calc_value(conn, target_date): raw_financials の target_date 以前の最新値を使って per（price / eps）と roe を計算。
    - feature_exploration:
      - calc_forward_returns(conn, target_date, horizons): 指定ホライズン（デフォルト [1,5,21]）の将来リターンを LEAD を用いて一度に取得。horizons の検証（1〜252）を実施。
      - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンの ρ をランク（平均ランク tie 処理）で計算。有効サンプル < 3 の場合は None。
      - factor_summary(records, columns): count/mean/std/min/max/median を返す（None 値は除外）。
      - rank(values): 同順位は平均ランク、比較前に round(v, 12) で丸めて tie 検出漏れを防止。
    - research パッケージ __all__ を整備。
  - バックテストフレームワーク（src/kabusys/backtest/）
    - simulator:
      - PortfolioSimulator: メモリ内でポートフォリオ状態を管理。BUY/SELL 約定ロジック、スリッページ（BUY:+, SELL:-）・手数料モデル、SELL は保有全量クローズのみ、SELL を先に処理する（資金確保のため）。
      - mark_to_market(trading_day, close_prices) で DailySnapshot を記録。終値欠損時は警告と 0 評価。
      - TradeRecord, DailySnapshot の dataclass 定義。
    - metrics:
      - calc_metrics(history, trades) を提供し、CAGR, Sharpe (無リスク=0), Max Drawdown, Win Rate, Payoff Ratio, total_trades を計算。
      - データ不足やゼロ分散等のガード（不足時は 0.0）を実装。
    - engine:
      - run_backtest(conn, start_date, end_date, ...): 本番 DuckDB からインメモリ DuckDB へ必要データをコピーして日次シミュレーションを実行するエントリポイントを実装。
      - コピー対象: prices_daily, features, ai_scores, market_regime（指定日範囲）および market_calendar（全件）。コピーに失敗したテーブルは警告ログを出してスキップする耐障害性を実装。
      - _build_backtest_conn は init_schema(":memory:") を使用してインメモリ環境を初期化。
      - 日次ループ:
        1. 前日シグナルを当日始値で約定（simulator.execute_orders）
        2. simulator の positions を positions テーブルに書き戻し（generate_signals の SELL 判定に必要）
        3. 終値で時価評価・スナップショット記録
        4. generate_signals(bt_conn, target_date=trading_day) を呼び出し翌日シグナルを生成
        5. signals テーブルを読み出し（_read_day_signals）、ポジションサイジングを行って翌日約定リストを構築
      - パラメータ: slippage_rate（デフォルト 0.001）、commission_rate（デフォルト 0.00055）、max_position_pct（デフォルト 0.20）。
- パッケージの __all__ 整備（backtest, research, strategy 等で公開 API を定義）。

Fixed
- （初回リリースのため該当なし）

Changed / Deprecated / Removed
- （初回リリースのため該当なし）

Security
- （初回リリースのため該当なし）

注意事項 / 既知の制限
- execution と monitoring パッケージは現時点では実質的な発注 API との接続実装を含んでいません（スタブ / プレースホルダ）。本番発注ロジックは別レイヤで実装予定です。
- SELL の高度なエグジット条件（トレーリングストップ、時間決済）は未実装。これらは positions テーブルに peak_price / entry_date 等の追加情報が必要です（コード内に TODO コメントあり）。
- AI スコア（ai_scores）が未登録の銘柄は中立値（news コンポーネントは 0.5）で補完されます。
- 一部のユーティリティは外部 data パッケージ（例: kabusys.data.stats.zscore_normalize, kabusys.data.schema.init_schema, kabusys.data.calendar_management.get_trading_days）に依存します。これらが利用可能であることが前提です。
- バックテスト用データコピー処理では、コピーに失敗したテーブルをスキップして継続するため、テーブル欠如時は挙動が制限される可能性があります（警告ログ出力）。

開発者向けメモ
- .env の複雑なクォート／エスケープシーケンスを意識したパーサ実装により、配布版でも堅牢に動作するよう配慮しています。テスト環境で自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。
- StrategyModel.md / BacktestFramework.md 等のドキュメントに準拠した設計方針・定数の注釈をコード内に記載しています。将来的なパラメータチューニングは strategy 層の weights/threshold 等で調整可能です。

今後の予定（例）
- execution 層での実際の発注インテグレーション実装（kabu API 等）。
- signals → execution の自動実行ワークフロー、monitoring の実装強化（Slack 通知等）。
- エグジット条件（トレーリングストップ、時間決済）の実装とそれに伴う positions スキーマ拡張。
- テストカバレッジの追加。README と運用ドキュメントの整備。