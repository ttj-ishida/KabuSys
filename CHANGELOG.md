# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

※ 本リポジトリの現状は初回リリース相当の実装（バージョン 0.1.0）を反映しています。

## [Unreleased]
（未リリースの変更はここに記載）

## [0.1.0] - 2026-03-22
初回リリース — 日本株自動売買ライブラリ「KabuSys」ベーシック機能を実装。

### Added
- パッケージの初期リリース
  - パッケージ名: kabusys
  - バージョン: 0.1.0

- 環境設定 / ロード機能（kabusys.config）
  - プロジェクトルート自動検出: `.git` または `pyproject.toml` を基準に探索する _find_project_root を追加。パッケージ配布後も CWD に依存せず .env を扱えるように設計。
  - .env ファイルパーサ実装: export 形式対応、シングル/ダブルクォート、エスケープ、インラインコメントの扱い等を考慮した _parse_env_line。
  - .env 自動ロード順序: OS 環境変数 > .env.local > .env（`.env.local` は上書き）。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - 環境変数強制取得ユーティリティ _require、設定クラス Settings を提供。以下の設定プロパティを実装:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN（必須）
    - SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト data/monitoring.db）
    - KABUSYS_ENV の検証（development / paper_trading / live のみ有効）
    - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - ヘルパー: is_live / is_paper / is_dev

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - build_features(conn, target_date) を追加。research モジュールで計算した raw factors を統合して features テーブルへ日付単位で置換（冪等）する処理を実装。
  - ユニバースフィルタ: 株価 >= 300 円、20日平均売買代金 >= 5億円。
  - 正規化: 指定カラムを zscore_normalize で正規化し、±3 でクリップして外れ値の影響を抑制。
  - トランザクション + バルク挿入で atomic な日付置換を実施。

- シグナル生成（kabusys.strategy.signal_generator）
  - generate_signals(conn, target_date, threshold=0.60, weights=None) を追加。features / ai_scores / positions を参照し BUY/SELL シグナルを作成して signals テーブルへ日付単位で置換（冪等）する。
  - スコア計算:
    - モメンタム、バリュー、ボラティリティ、流動性、ニュース（AI）の各コンポーネントスコア算出（シグモイド・平均等）。
    - 欠損コンポーネントは中立値 0.5 で補完。
    - user 指定の weights は既定値とマージし合計が 1 でない場合は再スケール。未知キーや無効値は無視。
  - Bear レジーム検知: ai_scores の regime_score 平均が負かつサンプル数閾値（デフォルト 3）を満たす場合、BUY を抑制。
  - SELL 条件:
    - ストップロス（終値 / avg_price - 1 < -8%）
    - final_score が閾値未満
    - SELL 判定には positions と当日の最新価格を参照（価格欠損時は警告を出して判定をスキップまたは慎重に扱う）。
  - 各処理でログ出力と警告を行い、ROLLBACK 失敗時は警告。

- リサーチ用ユーティリティ（kabusys.research）
  - calc_forward_returns(conn, target_date, horizons=None): LEAD を利用して複数ホライズンの将来リターン（デフォルト [1,5,21]）を一度のクエリで取得。
  - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンのランク相関を実装（同順位は平均ランク、有効レコード < 3 の場合は None）。
  - factor_summary(records, columns): 各列の count/mean/std/min/max/median を算出。
  - rank(values): 同順位は平均ランク、丸め処理により ties 判定の信頼性を向上。

- ファクター計算（kabusys.research.factor_research）
  - calc_momentum(conn, target_date): mom_1m / mom_3m / mom_6m / ma200_dev を計算。200日移動平均のデータ不足は None を返す。
  - calc_volatility(conn, target_date): 20日 ATR（atr_20）、相対ATR（atr_pct）、20日平均売買代金、出来高比率等を計算。入力 NULL の扱いに注意。
  - calc_value(conn, target_date): raw_financials から直近財務データを取得し PER / ROE を計算（EPS が 0/欠損の場合は PER=None）。

- バックテストフレームワーク（kabusys.backtest）
  - run_backtest(conn, start_date, end_date, initial_cash=10_000_000, slippage_rate=0.001, commission_rate=0.00055, max_position_pct=0.20)
    - 本番 DB から指定期間の必要テーブルを in-memory DuckDB にコピーしてバックテスト用環境を構築（signals / positions を汚染しない）。
    - 日次ループ: 前日シグナルを始値で約定 → positions テーブルへ書き戻し → 終値で時価評価 → generate_signals による翌日シグナル生成 → ポジションサイジングと注文作成。
    - データコピーは tables: prices_daily, features, ai_scores, market_regime（期間フィルタ）と market_calendar（全件）。
  - PortfolioSimulator（kabusys.backtest.simulator）
    - メモリ内のポートフォリオ状態管理（cash / positions / cost_basis / history / trades）。
    - execute_orders: SELL を先に処理してから BUY（SELL は保有全量クローズ、部分利確非対応）。始値にスリッページを適用（BUY は +、SELL は -）。
    - 手数料は約定金額 × commission_rate、BUY は cash から手数料を差し引いて平均取得単価を更新。
    - mark_to_market: 終値で評価し DailySnapshot を記録。終値欠損は警告し 0 で評価。
    - TradeRecord / DailySnapshot のデータクラスを提供。
  - バックテストメトリクス（kabusys.backtest.metrics）
    - calc_metrics(history, trades) により CAGR, Sharpe Ratio（無リスク=0）、Max Drawdown、Win Rate、Payoff Ratio、Total Trades を計算。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Deprecated
- 初回リリースのため該当なし。

### Removed
- 初回リリースのため該当なし。

### Security
- 初回リリースのため該当なし。

---

## 既知の制限・注意事項
- エグジット条件のうち「トレーリングストップ」や「時間決済（保有日数ベースの強制決済）」は未実装（コード内に未実装旨のコメントあり）。
- PortfolioSimulator の SELL は保有全量をクローズする設計であり、部分利確・部分損切りは未サポート。
- generate_signals は ai_scores を target_date で参照する。AI スコア未登録銘柄はニューススコアを中立（0.5）で扱う。
- positions テーブルへは market_value を NULL で書き込む（現バージョンでは参照しない）。
- .env 読み込みは自動で行うが、テスト等で無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定することで抑止可能。
- 環境変数の必須事項（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）は未設定時に ValueError を送出する。

---

必要であれば、各リリース注記をより細かく分割（モジュール別のサブセクション追加）したり、将来の Unreleased セクションに開発予定の項目を追記できます。どの粒度で記載するか指定してください。