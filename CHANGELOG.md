CHANGELOG
=========
All notable changes to this project will be documented in this file.

フォーマットは "Keep a Changelog" に準拠しています。  
リリースはセマンティックバージョニングに従います。

[Unreleased]
------------

- なし

[0.1.0] - 2026-03-22
--------------------

Added
- 基本パッケージ構成を追加（kabusys）
  - パッケージバージョン: 0.1.0

- 環境設定 / 自動 .env ロード機能（kabusys.config）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動読み込み
  - OS 環境変数の上書きを防ぐ protected 機構を実装
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - .env のパースは export プレフィックス、クォート、エスケープ、インラインコメントの扱いに対応
  - Settings クラスで主要設定をプロパティとして公開:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN（必須）
    - SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
  - 必須変数未設定時は ValueError を送出して明示的にエラーを通知

- 戦略: 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - research で算出された raw factor を取り込み、ユニバースフィルタ／正規化／クリップを行い features テーブルへ UPSERT
  - ユニバースフィルタ条件:
    - 株価 >= 300 円
    - 20日平均売買代金 >= 5億円
  - Z スコア正規化（対象カラム: mom_1m, mom_3m, atr_pct, volume_ratio, ma200_dev）、±3 でクリップ
  - DuckDB トランザクションで日付単位の置換（DELETE -> bulk INSERT）、失敗時は ROLLBACK を試行

- 戦略: シグナル生成（kabusys.strategy.signal_generator）
  - 正規化済み features と ai_scores を統合して final_score を計算し BUY / SELL を生成
  - コンポーネントスコア:
    - momentum, value, volatility, liquidity, news（AI）
  - デフォルト重みと閾値:
    - momentum:0.40, value:0.20, volatility:0.15, liquidity:0.15, news:0.10
    - BUY 閾値: 0.60
    - stop_loss: -8%
  - 重みは渡された辞書で上書き可能（検証・正規化済み）
  - Bear レジーム検出（ai_scores の regime_score 平均が負の場合かつサンプル >= 3）で BUY を抑制
  - エグジット判定（positions と最新価格を参照）
    - ストップロス判定、final_score の閾値割れ
  - signals テーブルへ日付単位の置換（トランザクション保証）
  - 欠損データへの寛容設計（欠損コンポーネントは中立 0.5 で補完、features が存在しない保有銘柄は score=0 と扱う等）
  - ログでの詳細な警告・情報出力により運用時の原因特定を容易に

- research モジュール（kabusys.research）
  - factor_research:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日データ不足時は None）
    - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio（ウィンドウ不足時は None）
    - calc_value: per, roe（raw_financials から target_date 以前の最新レコードを参照）
    - SQL ベースで DuckDB のみ参照、外部 API 非依存
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト 1/5/21 営業日）に対する将来リターン計算
    - calc_ic: スピアマンのランク相関（IC）計算（有効レコード < 3 の場合は None）
    - factor_summary: count/mean/std/min/max/median の計算
    - rank: 同順位は平均ランクで処理（丸めにより ties 検出の安定化）
  - zscore_normalize ユーティリティを re-export（kabusys.data.stats 経由）

- バックテストフレームワーク（kabusys.backtest）
  - simulator:
    - PortfolioSimulator によるメモリ内約定処理（BUY は配分に応じた株数を取得、SELL は保有全量クローズ）
    - スリッページ/手数料モデルを考慮
    - mark_to_market による日次スナップショット記録（終値欠損は 0 として評価し WARNING）
    - TradeRecord / DailySnapshot の dataclass 定義
  - metrics:
    - calc_metrics による CAGR / Sharpe / MaxDrawdown / WinRate / PayoffRatio / total_trades 計算
    - 実装は明確な数理定義に基づく（年次化、252 営業日等）
  - engine:
    - run_backtest: 本番 DB からインメモリ DuckDB に必要データを日付範囲でコピーして日次シミュレーションを実行
    - コピー対象: prices_daily, features, ai_scores, market_regime（期間フィルタ）および market_calendar（全件）
    - positions を生成して generate_signals の SELL 判定と整合させるためにシミュレータの保有状況を positions テーブルに書き戻す機能を提供
    - デフォルトパラメータ: initial_cash=10_000_000, slippage_rate=0.001, commission_rate=0.00055, max_position_pct=0.20

- パブリック API のエクスポート
  - kabusys.strategy: build_features, generate_signals
  - kabusys.research: calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank
  - kabusys.backtest: run_backtest, BacktestResult, DailySnapshot, TradeRecord, BacktestMetrics

Security
- .env 読み込みは OS 環境変数を上書きしないデフォルト動作。明示的に .env.local を優先して上書きできるが、OS 環境は protected として上書きから保護される。

Notes / Known limitations
- signal_generator の一部のエグジット条件（トレーリングストップ、時間決済）は未実装（positions テーブルに peak_price / entry_date が必要）。
- calc_value は PBR・配当利回りを未実装。
- positions テーブルの market_value カラムはシミュレータからは NULL として挿入（将来的に利用可能）。
- generate_signals は ai_scores が未登録の場合に中立処理を行う設計だが、AI スコアの品質に依存するため実運用ではモニタリング推奨。
- バックテスト用データコピー時にテーブルコピーで例外が発生した場合は警告ログを出してスキップする（堅牢化のため）。

Breaking Changes
- なし（初回リリース）

閉じる
- 初期リリースとして、戦略研究・シグナル生成・バックテストの一通りのワークフローを実装しました。今後は運用で得られた知見に基づき、未実装のエグジット条件や資金管理、より高度なリスク管理機能の追加・改善を行っていきます。