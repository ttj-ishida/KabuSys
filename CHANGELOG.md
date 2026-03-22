Keep a Changelog
=================

すべての注目すべき変更をバージョン別に記録します。  
このファイルは Keep a Changelog のフォーマットに準拠しています。

v0.1.0 - 2026-03-22
-------------------

Added
- パッケージ基盤: kabusys 初期実装
  - パッケージエントリポイント (src/kabusys/__init__.py) を追加。__version__ = "0.1.0"。__all__ に data, strategy, execution, monitoring を公開。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを追加。
  - 自動 .env ロード機能:
    - プロジェクトルートを .git または pyproject.toml で探索して自動読み込み（CWD に依存しない実装）。
    - 読み込み順序: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env のパースは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントなどに対応。
    - 読み込み時に既存 OS 環境変数を保護する protected 機構を実装。
  - 必須変数取得用の _require()、環境値検証（KABUSYS_ENV, LOG_LEVEL）を実装。
  - Settings で J-Quants / kabu ステーション / Slack / DB パス等のプロパティを公開（デフォルト値や Path の展開含む）。

- 戦略: 特徴量エンジニアリング (src/kabusys/strategy/feature_engineering.py)
  - build_features(conn, target_date): research モジュールで計算した生ファクターを取得し、正規化・合成して features テーブルへ UPSERT（ターゲット日単位で削除→挿入の冪等処理）する処理を実装。
  - 処理フロー: momentum/volatility/value の取得 → ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円） → Z スコア正規化（対象カラム指定）→ ±3 でクリップ → トランザクション＋バルク挿入で原子性保証。
  - 休場日や当日の欠損に対応するため、target_date 以前の最新価格を参照するロジックを実装。

- 戦略: シグナル生成 (src/kabusys/strategy/signal_generator.py)
  - generate_signals(conn, target_date, threshold=0.60, weights=None):
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - Z スコアをシグモイドで [0,1] に変換、欠損は中立 0.5 で補完。
    - デフォルト重みを定義し、ユーザー指定 weights のバリデーション・正規化（合計 1.0 に再スケール）を行う。
    - Bear レジーム判定（ai_scores の regime_score 平均が負 → BUY を抑制）。サンプル不足時の誤判定防止（最小サンプル数閾値あり）。
    - BUY（閾値 0.60 以上）および SELL（エグジット判定）を生成。SELL 判定にはストップロス（終値/avg_price -1 < -8%）とスコア低下を実装。
    - positions テーブル読み取りに依存する SELL 判定を考慮し、signals テーブルへの日付単位置換をトランザクションで実行（冪等）。
    - ロギングや不正な weights の警告を実装。
  - 実装上の既知事項: トレーリングストップや時間決済は未実装（コメントで明示）。

- Research モジュール (src/kabusys/research/)
  - factor_research.py:
    - calc_momentum(conn, target_date): mom_1m/mom_3m/mom_6m、ma200_dev を SQL ベースで計算。200 日未満のウィンドウは None を返す。
    - calc_volatility(conn, target_date): ATR（20 日平均）、atr_pct、avg_turnover、volume_ratio を計算。true_range の NULL 伝播を正確に制御。
    - calc_value(conn, target_date): raw_financials から最新財務データを取得し PER, ROE を計算（EPS が 0/欠損 の場合は PER=None）。
  - feature_exploration.py:
    - calc_forward_returns(conn, target_date, horizons=[1,5,21]): 将来リターンをまとめて取得（LEAD を利用）。horizons の検証あり（1〜252）。
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンのランク相関（IC）を実装。サンプル不足時は None。
    - factor_summary(records, columns): count/mean/std/min/max/median を算出（None を除外）。
    - rank(values): 同順位は平均ランクで扱うランク化ユーティリティ。浮動小数誤差対策の丸めあり。
  - research パッケージ __all__ に主要関数を公開。

- Backtest フレームワーク (src/kabusys/backtest/)
  - simulator.py:
    - DailySnapshot, TradeRecord の dataclass を導入。
    - PortfolioSimulator: メモリのみでポートフォリオ状態を管理するシミュレータを実装。execute_orders() は SELL→BUY の順で処理、BUY の割当て調整、スリッページと手数料適用、約定記録の作成、mark_to_market による日次評価と履歴保存を提供。
    - ログ出力による価格欠損や保有なしのハンドリング。
  - metrics.py:
    - BacktestMetrics dataclass と calc_metrics(history, trades) を実装。CAGR, Sharpe, MaxDrawdown, WinRate, PayoffRatio, total_trades を算出。
  - engine.py:
    - run_backtest(conn, start_date, end_date, ...): 本番 DB からインメモリ DuckDB へデータをコピーしてバックテストを実行するエンジンを実装。
    - コピー対象テーブルの絞り込み（prices_daily, features, ai_scores, market_regime は日付フィルタ、market_calendar は全件コピー）。start_date - 300 日のバッファを設定。
    - 日次ループ: 前日シグナル約定→positions 書き戻し→時価評価→generate_signals 呼出→ポジションサイジング→次日約定準備の流れを実装。
    - ユーティリティ: _fetch_open_prices / _fetch_close_prices / _write_positions / _read_day_signals を実装。
    - BacktestResult 型を返却（history, trades, metrics）。

- データ層依存・ユーティリティ
  - DuckDB を前提とした SQL ベースの集計・ウィンドウ処理を多用。zscore_normalize は kabusys.data.stats から利用。
  - 外部依存を最小化する方針（research の一部は pandas 等に依存しない実装）。

Changed
- 初版リリースのため該当なし。

Fixed
- 初版リリースのため該当なし。

Removed
- 初版リリースのため該当なし。

Security
- 初版リリースのため該当なし。

Notes / Known limitations
- feature_engineering や signal_generator の一部ロジックはコメントで TODO（トレーリングストップ、時間決済、PBR・配当利回り等未実装）として残っている。
- generate_signals は ai_scores が存在しない場合に中立値を採用する設計。ai_scores の欠損やサンプル不足時のレジーム判定ロジックに注意。
- positions テーブルへ挿入される market_value は NULL（nullable）で書き戻される。将来的な拡張で利用想定。
- .env パーサは多くのケースに対応しているが、特殊なフォーマットの .env がある場合は注意が必要。

作者
- kabusys プロジェクト 初版 (v0.1.0)

---

この CHANGELOG はコードベースのコメント・実装から推測して作成しています。実際の変更履歴（コミット単位や日付など）との差異がある可能性がある点にご注意ください。