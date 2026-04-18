# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に従います。

## [0.1.0] - 2026-04-18

初回リリース — KabuSys 基本コア機能を実装しました。主な追加点は以下の通りです。

### Added
- 全体
  - パッケージ基盤を追加。バージョンは `__version__ = "0.1.0"`。
  - デフォルトのデータ・ログパスや環境変数を利用する設定管理を実装（`kabusys.config.Settings` / `settings`）。
  - プロジェクトルート自動検出と `.env` 自動読み込み機能（`.env`, `.env.local` を OS 環境変数を保護してロード）。自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。

- 実行スクリプト
  - run_execution: 実行エンジンスクリプトを追加（`src/kabusys/run_execution.py`）。
    - 起動時にプロセス優先度を "high" に設定。
    - `KABUSYS_ENV=paper_trading` 時は paper_trading 専用 SQLite（デフォルト `data/paper_trading.db`）を使用し、本番 DB と分離（MockBrokerClient の利用を想定）。
    - 停止制御用のフラグファイル（`data/stop_requested.flag`）および PID ファイル（`data/execution.pid`）の取り扱い。
    - ExecutionEngine の起動/監視をスレッドで実行し、停止フラグ検出時に安全に停止。

  - run_monitoring: システム監視ポーリングループ起動スクリプトを追加（`src/kabusys/run_monitoring.py`）。
    - デフォルトポーリング間隔は 60 秒。環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（不正な値は警告してデフォルトにフォールバック）。
    - 監視は環境にかかわらず本番の `sqlite_path` を使用して DB を初期化。
    - 停止フラグ（`data/stop_requested.flag`）検知でループを終了。

- 設定関連 CLI
  - 設定ウィザード（`python -m kabusys.config_setup`）を追加。
    - 対話式に `.env` を作成・更新可能。シークレット項目はマスク表示。
    - デフォルト・選択肢・説明テキストを含む設定項目一覧を提供。
  - 設定検証 CLI（`python -m kabusys.validate_config`）を追加。
    - 必須環境変数チェック、`KABUSYS_ENV`/`LOG_LEVEL` 等の妥当性チェック、DB パスの親ディレクトリ存在チェック、`config/*.yaml` の存在と YAML パース検証（PyYAML がインストールされている場合）。
    - `--strict` オプションで警告を FAIL 扱いにできる。

- Portfolio（銘柄選定・配分・発注数算出）
  - 銘柄選定・重み計算（`kabusys.portfolio.portfolio_builder`）
    - select_candidates: スコア降順で上位 N 件を選択（同スコア時は signal_rank でタイブレーク）。
    - calc_equal_weights: 等金額配分（1/N）。
    - calc_score_weights: スコア正規化による加重配分。全銘柄スコアが 0 の場合は等金額にフォールバック（警告）。
  - セクター上限・レジーム乗数（`kabusys.portfolio.risk_adjustment`）
    - apply_sector_cap: 既存保有のセクター比率が上限を超える場合、そのセクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（"bull"=1.0、"neutral"=0.7、"bear"=0.3、未知は 1.0 にフォールバック）。
  - 株数計算（`kabusys.portfolio.position_sizing`）
    - calc_position_sizes: `risk_based` / `equal` / `score` の配分方式に対応。lot_size（単元）単位で丸め、個別上限・全体上限（available_cash）を考慮。コストバッファ（手数料・スリッページ推定）を加味したスケーリングと、残余キャッシュに対する端数配分ロジックを実装。

- ユーティリティ
  - ロギング設定ユーティリティ（`kabusys.utils.logging_setup.setup_logging`）
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）を設定。既存ハンドラは再設定時にクリア。
    - ログレベルとログディレクトリは引数 > 環境変数 > デフォルト（"INFO"/"logs"）の順に解決。
    - ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
  - プロセス優先度・CPU affinity ユーティリティ（`kabusys.utils.process_priority`）
    - set_process_priority(level): Windows と POSIX（Linux/Mac 等）を吸収する実装。アクセス権限や未対応 OS の場合は警告してスキップ。
    - set_cpu_affinity(cpu_count): 指定コア数に固定（権限不足等は警告してスキップ）。

- Research（解析）
  - ファクター計算のスケルトン（`kabusys.research.factor_research`）を追加。
    - Momentum / Value / Volatility / Liquidity 等の計算方針・定数を定義。DuckDB の `prices_daily` / `raw_financials` を想定して計算する設計。モメンタム計算関数（calc_momentum）の実装開始（営業日ウィンドウ設定等）。

- ツール
  - Paper Trading 検証レポート生成スクリプトを追加（`kabusys.tools.paper_verification_report`）。
    - Paper Trading 用 SQLite（環境変数 `PAPER_TRADING_SQLITE_PATH`、デフォルト `data/paper_trading.db`）から各種指標を集計してレポート出力。
    - 集計指標: 稼働率（uptime_pct）、注文成功率（fill_rate）、送信率（send_rate）、リスク却下数、レイテンシ（avg/max/P95）等。
    - 基準値を定義し、PASS/FAIL 判定を出力（稼働率 >= 99%、fill_rate >= 90%、send_rate >= 95%、P95 latency <= 200ms）。
    - 日付フィルタ（--from / --to）と DB パス指定（--db）をサポート。

### Changed
- 環境変数周りの扱いを明確化
  - `.env` パーサを独自実装し、`export KEY=val` 形式やクォート文字列（エスケープ含む）、インラインコメントの扱いに対応。
  - `.env.local` を `.env` の上書き（ただし OS 環境変数は保護）として読み込むことで、ローカル上書きの優先順位を実現。

### Fixed
- なし（初回リリース）

### Notes / Usage tips
- 起動スクリプトはいずれも起動直後にプロセス優先度を "high" に設定しようとしますが、権限がない環境では警告が出て処理を継続します。
- Paper Trading と本番データベースは分離されています。`KABUSYS_ENV=paper_trading` により `PAPER_TRADING_SQLITE_PATH`（デフォルト `data/paper_trading.db`）が使用されます。
- `.env` の自動読み込みはプロジェクトルートが検出できた場合に行われます。プロジェクトルート検出は `.git` または `pyproject.toml` を基準とします。
- ログは標準出力（stdout）および `logs/<app_name>.log` に日次ローテーションで出力されます。`LOG_DIR` 環境変数で変更可能です。
- 設定検証ツール（validate_config）は `--strict` を付けると警告でも非ゼロ終了するため、CI 等での事前チェックに便利です。

今後予定（例）
- factor_research の完全実装（Momentum / Value / Volatility / Liquidity の具体的計算）。
- ExecutionEngine / BrokerClient 実装のテストと MockBroker の詳細動作確認。
- 単体テスト・CI ワークフローの整備。

---

（注）本 CHANGELOG はソースコードの現状から挙動を推測して作成しています。実際の変更履歴や設計方針はリポジトリの commit 履歴や設計文書を参照してください。