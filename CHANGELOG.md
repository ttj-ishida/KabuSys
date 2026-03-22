# Changelog

すべての、ユーザーに見える変更点はこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠します。

注: 日付はリリース日を示します。

## [Unreleased]

（現在未リリースの変更はここに記載します）

## [0.1.0] - 2026-03-22

初回リリース。日本株の自動売買・リサーチ・バックテストの基本機能を提供します。

### Added
- パッケージ初期化
  - kabusys パッケージ（__version__ = 0.1.0）。主要サブパッケージとして data / strategy / execution / monitoring を公開。

- 設定管理（kabusys.config）
  - .env または環境変数からの設定読み込みを実装（プロジェクトルートを .git または pyproject.toml で検出）。
  - 自動ロード順序: OS 環境変数 > .env.local > .env。環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - 複数種の環境変数パース対応（export 形式、シングル/ダブルクォート・エスケープ、コメント処理など）。
  - 必須設定取得ヘルパー _require と Settings クラスを提供。主要プロパティ:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（必須）
    - KABUSYS_ENV（development / paper_trading / live の検証）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）
    - DUCKDB_PATH / SQLITE_PATH の既定値サポート

- リサーチ（kabusys.research）
  - factor_research: モメンタム / ボラティリティ / バリューファクター計算
    - calc_momentum(conn, target_date): mom_1m / mom_3m / mom_6m / ma200_dev を計算。
    - calc_volatility(conn, target_date): atr_20 / atr_pct / avg_turnover / volume_ratio を計算。
    - calc_value(conn, target_date): per / roe を計算（raw_financials と prices_daily を参照）。
  - feature_exploration: 将来リターンや統計解析ユーティリティ
    - calc_forward_returns(conn, target_date, horizons): 翌日/翌週/翌月等の fwd リターンを一括取得。
    - calc_ic(factors, forwards, factor_col, return_col): スピアマンランク相関（IC）を計算。
    - factor_summary(records, columns): 各ファクターの基本統計量（count/mean/std/min/max/median）。
    - rank(values): 同順位を平均ランクで扱うランク化ユーティリティ。
  - すべて DuckDB を用いた SQL + Python 実装。外部依存を最小化。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - build_features(conn, target_date): research モジュールから生ファクターを取得し、
    - ユニバースフィルタ（最低株価: 300 円、20日平均売買代金 >= 5億円）適用、
    - 指定数値カラムの Z スコア正規化（±3 でクリップ）、
    - features テーブルへ日付単位の置換（トランザクション／バルク挿入により冪等性を確保）。
  - 正規化ユーティリティは kabusys.data.stats の zscore_normalize を使用。

- シグナル生成（kabusys.strategy.signal_generator）
  - generate_signals(conn, target_date, threshold=0.60, weights=None)
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を算出。
    - final_score を重み付き合算（デフォルト重み: momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）。weights 引数で上書き（不正値は無視、合計はリスケール）。
    - Bear レジーム判定（ai_scores の regime_score の平均が負かつサンプル数 >= 3 の場合）により BUY を抑制。
    - BUY: final_score >= threshold の銘柄。SELL: 保有ポジションのストップロス（-8%）またはスコア低下を検出して生成。
    - signals テーブルへ日付単位の置換（トランザクションで冪等）。
    - 関数は features/ai_scores/positions を参照するが発注 API には依存しない。

- バックテストフレームワーク（kabusys.backtest）
  - simulator: ポートフォリオシミュレータ（PortfolioSimulator）
    - 日次スナップショット DailySnapshot、約定記録 TradeRecord。
    - execute_orders(signals, open_prices, slippage_rate, commission_rate): SELL を先に処理、BUY は引数の alloc で株数を計算（切り捨て）。スリッページ・手数料モデル実装。
    - mark_to_market(trading_day, close_prices): 終値で評価し history に DailySnapshot を記録（終値欠損時は 0 として WARNING）。
  - metrics: バックテスト評価指標計算（calc_metrics）
    - CAGR、Sharpe（無リスク=0、年次化: √252）、Max Drawdown、Win Rate、Payoff Ratio、total_trades を計算。
  - engine: run_backtest(conn, start_date, end_date, ...)
    - 本番 DB から必要テーブルを日付範囲でインメモリ DuckDB にコピー（signals/positions を汚染しない）。
    - 日次ループ: 前日シグナルを当日始値で約定 → positions を書き戻し → 終値で時価評価 → generate_signals() で翌日分シグナル生成 → ポジションサイジングして注文作成。
    - デフォルトパラメータ: initial_cash=10_000_000、slippage_rate=0.001、commission_rate=0.00055、max_position_pct=0.20。
    - 戦略ロジック（signal_generator）と連携する運用フローを提供。

- DB 操作に関する設計
  - features / signals / positions テーブルへの書き込みは「日付単位の置換」を行い、トランザクション + バルク挿入で原子性と冪等性を確保。
  - バックテスト用に market_calendar を全件コピー、その他は日付フィルタで必要範囲のみコピー（パフォーマンス考慮）。

- ロギングとエラーハンドリング
  - 主要処理で logger を使用し、警告やトランザクション失敗時の挙動（ROLLBACK の試行）を実装。

### Changed
- 新規リリースのため該当なし

### Fixed
- 新規リリースのため該当なし

### Removed
- 新規リリースのため該当なし

### Security
- 新規リリースのため該当なし

---

注記 / 既知の制限・未実装事項
- 一部機能は意図的に未実装または今後の拡張対象:
  - トレーリングストップおよび時間決済（positions に peak_price / entry_date 等が必要）。
  - PBR・配当利回りなどの追加バリューファクターは未実装。
  - signal_generator の SELL 条件に関する一部仕様（ピークベースのトレーリング等）は未実装（コード内にコメントあり）。
- research モジュールは外部依存（pandas 等）を避ける設計。大規模データ処理時は DuckDB の利用とメモリに注意。
- .env パーサーは多くの一般的ケースをカバーしていますが、特殊なフォーマットの .env 行に対しては期待と異なる動作をする可能性があります。
- バックテストは本番 DB からのコピー処理で一部テーブルのコピーをスキップすることがある（コピー失敗時は警告ログを出力して進行）。

開発・改善予定
- 追加ファクター（PBR、配当利回りなど）の実装
- signal_generator のさらなる EXIT 条件（トレーリング・時間決済）
- execution 層との統合テストと本番接続の検証
- テストカバレッジの拡充と CI 設定

----

参考: 主な公開 API（抜粋）
- kabusys.config.settings (Settings)
- kabusys.strategy.build_features(conn, target_date) -> upsert count
- kabusys.strategy.generate_signals(conn, target_date, threshold=0.60, weights=None) -> signal count
- kabusys.backtest.run_backtest(conn, start_date, end_date, ... ) -> BacktestResult

（詳細は各モジュールの docstring を参照してください）