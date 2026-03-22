# CHANGELOG

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠しています。

## [0.1.0] - 2026-03-22
初回公開リリース。日本株自動売買システム kabusys のコア機能を実装しました。主要な機能群（設定管理、ファクター計算、特徴量生成、シグナル生成、バックテストフレームワーク、研究用ユーティリティ）を提供します。

### Added
- パッケージ初期化
  - src/kabusys/__init__.py にて version を "0.1.0" として公開。data, strategy, execution, monitoring を __all__ に設定。

- 環境変数・設定管理
  - src/kabusys/config.py
    - .env / .env.local の自動読み込み（プロジェクトルートを .git または pyproject.toml で探索）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 による自動ロード無効化。
    - export 形式やクォート付き値、インラインコメントのパース対応。
    - OS 環境変数を保護する protected オプション（.env.local は上書き可能だが既存 OS 環境変数は保護）。
    - Settings クラスで各種必須設定をプロパティとして提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など）。
    - 設定値の簡易バリデーション（KABUSYS_ENV の許容値, LOG_LEVEL の許容値）。
    - デフォルトの DB パス設定（DUCKDB_PATH, SQLITE_PATH）。

- 特徴量エンジニアリング
  - src/kabusys/strategy/feature_engineering.py
    - research モジュールで計算した生ファクターをマージ・正規化して features テーブルへ UPSERT。
    - ユニバースフィルタ（最低株価、20日平均売買代金）を実装。
    - Zスコア正規化（kabusys.data.stats.zscore_normalize を利用）、±3 でクリップ。
    - 日付単位での置換（DELETE + BULK INSERT）により冪等性と原子性を確保（トランザクション使用）。

- シグナル生成
  - src/kabusys/strategy/signal_generator.py
    - features と ai_scores を統合し、各銘柄のコンポーネントスコア（momentum, value, volatility, liquidity, news）を計算。
    - final_score を重み付き平均で算出（デフォルト重みを定義、ユーザー指定 weights をマージ・正規化）。
    - BUY シグナル閾値（デフォルト 0.60）超過で BUY、保有ポジションに対してはエグジット（STOP-LOSS / スコア低下）で SELL。
    - Bear レジーム（ai_scores の regime_score 平均が負）検知により BUY を抑制。
    - 欠損値補間方針（コンポーネントが None の場合は中立値 0.5 で補完）による頑健性。
    - signals テーブルへ日付単位での置換（冪等、トランザクション）。

- 研究用ファクター計算 / 探索
  - src/kabusys/research/factor_research.py
    - Momentum（1M/3M/6M リターン、MA200 乖離率）計算。
    - Volatility（20日 ATR、ATR の相対値、20日平均売買代金、出来高比率）計算。
    - Value（PER、ROE）計算（raw_financials の最新レコードを参照）。
    - prices_daily/raw_financials のみ参照する設計。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）。
    - IC（Spearman の ρ）計算（ランク相関、同順位は平均ランクで処理）。
    - factor_summary（count/mean/std/min/max/median）を提供。
    - pandas 等外部依存なしで実装。
  - src/kabusys/research/__init__.py にて上記関数をエクスポート。

- バックテストフレームワーク
  - src/kabusys/backtest/simulator.py
    - PortfolioSimulator 実装（メモリ内でポジション／cost_basis 管理、BUY/SELL 約定ロジック、スリッページ・手数料モデル）。
    - DailySnapshot / TradeRecord dataclass 定義。
    - execute_orders: SELL 先行処理、BUY は割当て資金で株数を算出（手数料を考慮した再計算ロジック含む）、部分利確は未対応（全量クローズ）。
    - mark_to_market は終値が欠損の場合に 0 で評価し Warning を出力。
  - src/kabusys/backtest/metrics.py
    - バックテスト評価指標の計算（CAGR, Sharpe, Max Drawdown, Win rate, Payoff ratio, total trades）。
  - src/kabusys/backtest/engine.py
    - run_backtest 実装（本番 DB からインメモリ DuckDB へデータをコピーし日次ループでシミュレーション）。
    - _build_backtest_conn で必要テーブルを日付範囲でフィルタしてコピー（market_calendar は全件コピー）。
    - ポジションを書き戻す _write_positions、signals 読み取り、open/close 価格取得ユーティリティを提供。
    - デフォルトのスリッページ/手数料/最大ポジション比率のパラメータ。
  - src/kabusys/backtest/__init__.py にて主要型・関数をエクスポート。

- API エクスポート
  - src/kabusys/strategy/__init__.py で build_features, generate_signals を公開。
  - backtest/ と research/ の主要関数・型を __all__ で公開。

### Changed
- （初回リリースのため変更履歴はありません）

### Fixed
- （初回リリースのため修正履歴はありません）

### Deprecated
- なし

### Removed
- なし

### Security
- なし

---

## 既知の制約・未実装点（注意）
- エグジット条件の一部未実装:
  - トレーリングストップ（直近最高値からの % 減少）や時間決済（保有 60 営業日超）は未実装。これらは positions テーブルに peak_price / entry_date 等の情報が必要となります（ソース内に TODO コメントあり）。
- positions テーブルの market_value カラムはシミュレータから NULL で書き込まれる（現状 SELL 判定では参照しないため問題ないが将来的な機能拡張で利用予定）。
- research パッケージは外部ライブラリ（pandas, numpy 等）に依存しない実装のため、最適化や高速化の余地がある。
- features テーブルには avg_turnover をフィルタ用途で参照するが保存はしていない（設計上の意図的選択）。
- 一部の SQL クエリは DuckDB に依存（環境によってはバージョン差分に注意）。

もし特定の機能について詳細な変更点や例（使用方法、環境変数一覧、既定重みや閾値の調整方法など）をCHANGELOGに追記したい場合は、追ってバージョン別に分けて記載できます。