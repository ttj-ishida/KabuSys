# Changelog

すべての重要な変更点をここに記録します。フォーマットは「Keep a Changelog」に準拠しています。

全般:
- このリポジトリは日本株の自動売買システム "KabuSys" の初期実装を含みます（バージョン 0.1.0）。
- 実装は発注実行層（kabuステーション等）への直接接続を最小限にし、研究用モジュール・バックテストフレームワーク・シグナル生成ロジックを中心に構成されています。
- データ処理は主に DuckDB を利用します。

## [0.1.0] - 2026-03-22 (Initial release)

### Added
- パッケージ基本情報
  - `kabusys.__version__ = "0.1.0"` を追加。
  - パッケージ公開 API：`data`, `strategy`, `execution`, `monitoring`（__all__ に登録）。

- 環境設定管理 (`src/kabusys/config.py`)
  - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装。
  - プロジェクトルート検出ロジック：`_find_project_root()` は `.git` または `pyproject.toml` を探索してルートを特定。
  - .env パーサー：`_parse_env_line()` は export プレフィックス、クォート、バックスラッシュエスケープ、インラインコメント処理などに対応。
  - .env 読み込み順序：OS 環境 > .env.local > .env（.env.local は override=True）。
  - 自動ロード無効化フラグ：`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - 必須環境変数チェック：`_require()` を介して未定義時は ValueError を送出。
  - Settings クラスを公開（プロパティ：`jquants_refresh_token`, `kabu_api_password`, `kabu_api_base_url`, `slack_bot_token`, `slack_channel_id`, `duckdb_path`, `sqlite_path`, `env`, `log_level`, `is_live`, `is_paper`, `is_dev`）。
  - 環境値検証：`KABUSYS_ENV` と `LOG_LEVEL` の許容値チェック。

- 戦略（feature engineering / signal generation）
  - 特徴量作成 (`strategy/feature_engineering.py`)
    - 研究環境で計算した raw ファクターを取得して正規化・合成し、`features` テーブルへ UPSERT（日付単位で置換）する `build_features(conn, target_date)` を実装。
    - ユニバースフィルタ（最低株価 = 300 円、20日平均売買代金 >= 5 億円）を実装。
    - 数値ファクターを Z スコア正規化（`kabusys.data.stats.zscore_normalize` を利用）、±3 でクリップ。
    - トランザクションで DELETE→INSERT を行い原子性を担保。失敗時は ROLLBACK を試行し、失敗ログを出力。
  - シグナル生成 (`strategy/signal_generator.py`)
    - `generate_signals(conn, target_date, threshold=0.60, weights=None)` を実装。
    - `features` と `ai_scores` を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を算出、重み付き合算で final_score を作成（デフォルト重みは StrategyModel.md に準拠）。
    - シグモイド変換、欠損値は中立 0.5 で補完する処理を実装。
    - Bear レジーム（AI の regime_score の平均が負の場合）検知により BUY を抑制するロジックを実装（サンプル閾値あり）。
    - SELL（エグジット）判定ロジック：
      - ストップロス（終値が avg_price 比で -8% 以下）を最優先。
      - final_score が閾値未満の場合にエグジット。
      - 価格欠損時は判定をスキップして警告ログ出力。features にない保有銘柄は score=0 として SELL へ。
    - signals テーブルへ日付単位で置換（トランザクション＋バルク挿入）。

- 研究用モジュール (`research/`)
  - ファクター計算群 (`research/factor_research.py`)
    - momentum（1/3/6 ヶ月リターン、MA200乖離）、volatility（20日ATR・相対ATR、20日平均売買代金、出来高比率）、value（PER/ROE）を実装。
    - prices_daily / raw_financials テーブルのみ参照する形で実装。
  - 特徴量探索 (`research/feature_exploration.py`)
    - 将来リターン計算（任意ホライズン：デフォルト [1,5,21]）`calc_forward_returns`。
    - スピアマンのランク相関による IC 計算 `calc_ic`（有効データが 3 未満なら None）。
    - factor_summary（count/mean/std/min/max/median）とランク計算ユーティリティ `rank`。
    - pandas 等に依存せず標準ライブラリのみで実装。
  - 研究モジュールのエクスポートを package-level へ追加。

- バックテストフレームワーク (`backtest/`)
  - メトリクス計算 (`backtest/metrics.py`)
    - CAGR、Sharpe（無リスク金利=0）、Max Drawdown、Win Rate、Payoff Ratio、Total Trades を計算する `calc_metrics` 実装。
  - ポートフォリオシミュレータ (`backtest/simulator.py`)
    - `PortfolioSimulator`：メモリ内で約定処理・保有管理を行う。
    - 売りを先に処理、売却は保有全量をクローズする設計。
    - スリッページと手数料を考慮した約定計算、約定記録を `TradeRecord` として保持。
    - 終値評価で `DailySnapshot` を記録（終値欠損は 0 で評価して警告）。
  - バックテストエンジン (`backtest/engine.py`)
    - `run_backtest(conn, start_date, end_date, ...)` を実装。
    - 本番 DB から必要テーブルのみをインメモリ DuckDB へコピーしてバックテストを実行（signals/positions を汚染しない）。
    - コピー対象テーブル（`prices_daily`, `features`, `ai_scores`, `market_regime`）について日付範囲フィルタでコピー。`market_calendar` は全件コピー。
    - 日次ループで順に（前日シグナルを当日始値で約定 → positions テーブルに書き戻す → 終値で評価 → generate_signals を呼び出し → signals を読み取り発注割合を決定 → 次日へ繰り返し）。
    - positions の書き戻しを行うユーティリティ `_write_positions`（冪等）、signals 読み取りユーティリティ `_read_day_signals` を実装。

- パッケージエクスポート
  - backtest / strategy の主要関数・型を package-level で公開（__all__ に登録）。

### Changed
- （初期リリースのため "Added" のみ）

### Fixed
- （初期リリースのため該当なし）

### Removed
- （初期リリースのため該当なし）

### Notes / Known limitations
- 一部仕様未実装
  - トレーリングストップ（直近最高値から -10%）や保有日数に基づく時間決済は未実装（positions に peak_price / entry_date が必要）。
  - calc_value では PBR や配当利回りは未実装。
- 実行上の安全措置
  - 多くの箇所で価格欠損時に処理をスキップして警告ログを出すようにしており、誤発注や不適切なエグジットを防ぐ設計。
  - DB 書き込みは可能な限りトランザクション（BEGIN/COMMIT/ROLLBACK）で原子性を保証。ROLLBACK に失敗した場合は警告ログを出力する。
- 重みの取り扱い
  - generate_signals の weights パラメータはデフォルト重みでフォールバックされる。ユーザー提供値は検証され、無効なキーや負値/非数値/NaN/Inf は無視される。合計が 1 でなければ正規化される。
- 環境変数
  - 必須キー（例）：JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID。未設定時は Settings のプロパティアクセスで例外が発生する。
  - デフォルトパス：`DUCKDB_PATH` -> data/kabusys.duckdb、`SQLITE_PATH` -> data/monitoring.db。
- Backtest のデータコピー
  - コピー時に例外が発生すると該当テーブルのコピーをスキップして警告（本番 DB の一部欠損に対する寛容性を持つ実装）。
  - バックテスト用のコピーデータは start_date - 300 日まで取得しており、特徴量や移動平均の計算に必要な履歴を確保する。

---

貢献・バグ報告
- バグや改善要望があれば Issue を作成してください。実装方針や設計文書（StrategyModel.md, BacktestFramework.md 等）を参照して拡張・修正を行ってください。