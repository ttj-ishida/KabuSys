# Changelog

すべての重要な変更点はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを採用します。

現在の日付: 2026-03-22

## [Unreleased]
（現時点で未リリースの変更はありません）

---

## [0.1.0] - 2026-03-22
初回リリース。日本株の自動売買プラットフォーム「KabuSys」のコア機能群を実装しました。主な実装内容は以下の通りです。

### 追加 (Added)
- パッケージ基盤
  - パッケージ初期化（kabusys.__init__）に __version__ を定義（0.1.0）。
  - パブリックモジュール群を __all__ で公開: data, strategy, execution, monitoring（execution は空のパッケージとして配置）。

- 設定・環境変数管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む自動ローダを実装。
  - プロジェクトルート検出: .git または pyproject.toml を起点にルートを探索（CWD 非依存）。
  - .env パーサ実装（コメント行、export プレフィックス、シングル/ダブルクォートおよびエスケープ対応、インラインコメントの処理含む）。
  - .env の読み込み優先順位: OS 環境 > .env.local（上書き） > .env（非上書き）。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト等で利用可能）。
  - Settings クラスを提供し、必要な環境変数取得メソッドを実装:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（デフォルト data/monitoring.db）
    - KABUSYS_ENV（development/paper_trading/live のバリデーション）
    - LOG_LEVEL（DEBUG/INFO/... のバリデーション）
    - is_live / is_paper / is_dev のヘルパープロパティ

- 研究（research）モジュール
  - factor_research:
    - Momentum ファクター計算（mom_1m, mom_3m, mom_6m, ma200_dev）
    - Volatility / Liquidity ファクター計算（atr_20, atr_pct, avg_turnover, volume_ratio）
    - Value ファクター計算（per, roe） — raw_financials と prices_daily 組合せ
    - DuckDB を利用した SQL ベースの高性能集計実装（営業日ウィンドウ・欠損管理を考慮）
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns）。複数ホライズン（デフォルト: 1,5,21営業日）に対応。入力の妥当性チェックを実装（horizons 範囲制限）。
    - IC（Information Coefficient）計算（Spearman の ρ）実装（ランク付けは同順位の平均ランク対応）。
    - ファクター統計サマリー（count/mean/std/min/max/median）を計算するユーティリティ。
    - rank ユーティリティ（丸めを使った同値処理を含む）。
  - research パッケージ __all__ に上記関数群を公開。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - build_features(conn, target_date) を実装:
    - research モジュールで計算した生ファクターを取得（calc_momentum/calc_volatility/calc_value）。
    - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 >= 5 億円）を適用。
    - 指定カラムを Z スコア正規化（kabusys.data.stats.zscore_normalize を使用）、±3 でクリップ。
    - features テーブルへ日付単位の置換（DELETE + bulk INSERT、トランザクションで原子性確保）を実施。
    - 欠損・非有限値の扱い、ログ記録を含む。

- シグナル生成（kabusys.strategy.signal_generator）
  - generate_signals(conn, target_date, threshold=0.6, weights=None) を実装:
    - features と ai_scores を統合し、momentum/value/volatility/liquidity/news の各コンポーネントスコアを算出。
    - Z スコア→シグモイド変換や、欠損値を中立値 0.5 で補完するポリシーを採用。
    - final_score の重み付け合算（デフォルト重みは StrategyModel.md の値を反映）。
    - ユーザ指定 weights のバリデーション、補完、再スケール処理を実装（未知キーや負値・NaN を無視）。
    - Bear レジーム判定（ai_scores の regime_score 平均が負の場合かつサンプル数閾値を満たす）を実装し、Bear 時は BUY を抑制。
    - BUY シグナル閾値（デフォルト 0.60）での BUY 生成、SELL シグナルは _generate_sell_signals にて:
      - ストップロス（-8%）判定
      - スコア低下（final_score < threshold）
    - signals テーブルへ日付単位置換（トランザクションで原子性確保）。
    - SELL 優先ポリシー（SELL 対象は BUY から除外しランク再付与）。
    - 詳細なログ出力を実装。

- バックテストフレームワーク（kabusys.backtest）
  - simulator:
    - PortfolioSimulator（初期現金管理、positions/cost_basis 管理、履歴とトレード記録の保持）。
    - execute_orders（SELL 先行、BUY 後処理、スリッページ・手数料考慮、約定株数の再計算ロジック）。
    - mark_to_market（終値評価、欠損終値時の警告と0評価）。
    - TradeRecord / DailySnapshot のデータクラス定義。
  - metrics:
    - バックテスト評価指標計算（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, total_trades）。
    - 実務での安定化処理（入力不足時に 0.0 を返す等）。
  - engine:
    - run_backtest(conn, start_date, end_date, ...) を実装:
      - 本番 DB からインメモリ DuckDB へ必要データをコピーする _build_backtest_conn（signals/positions を汚染しない）。
      - 日次ループ: 約定（前日シグナルを当日始値で執行）→ positions 書き戻し → 時価評価 → generate_signals 呼び出し → ポジションサイジング→ 次日シグナル組立て。
      - 各種補助関数: _fetch_open_prices, _fetch_close_prices, _write_positions, _read_day_signals。
    - get_trading_days（market_calendar を利用）との連携を想定した実装。
  - backtest パッケージ __all__ に主要 API を公開（run_backtest, BacktestResult, DailySnapshot, TradeRecord, BacktestMetrics）。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- 環境変数未設定時に明示的な ValueError を発生させることで、機密トークンや API パスワードの未設定を分かりやすく扱う実装を追加。

### ドキュメント / 設計ノート
- モジュール内に各処理フロー・設計方針・参照すべきドキュメント（StrategyModel.md, BacktestFramework.md 等）をコメントとして明示。
- 研究用 (research) と本番用（execution / strategy / backtest）の責務分離を明記。

### 既知の制限 / 未実装 (Known limitations / Unimplemented)
- 特に以下の機能はコメントで未実装として明示されています:
  - トレーリングストップ（positions テーブルに peak_price / entry_date が必要）: _generate_sell_signals 内で未実装。
  - 時間決済（保有 60 営業日超過）: 未実装。
  - PBR・配当利回りなど一部バリューファクターは未実装。
- execution パッケージは空のマーカーとして存在しており、実際の発注 API 連携は別途実装が必要。
- monitoring モジュールの実装（Slack 連携など）は Settings にトークンがあるが、本コード内では明示的な通知機能は未実装。

---

今後の予定（例）
- execution 層の実装（kabu API / 実際の発注処理の追加）。
- monitoring（Slack 通知・監視ダッシュボード）機能の追加。
- factor の追加（PBR・配当利回り等）、AI スコア周りの強化。
- ユニットテストと CI の整備（KABUSYS_DISABLE_AUTO_ENV_LOAD を利用したテスト容易化）。

---
（注）本 CHANGELOG は提供されたソースコードの内容から推測して作成しています。リリースノートの文言は実装状況に基づく要約であり、実際のリリース手順や外部ドキュメントと差異がある可能性があります。必要に応じて日付・文言の調整を行ってください。