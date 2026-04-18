# Changelog

すべての重要な変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。

最新のリリース: 0.1.0

## [Unreleased]


## [0.1.0] - 2026-04-18
初回リリース。本リポジトリに含まれる主要な機能群と CLI ツールをまとめて導入しました。

### Added
- 全体
  - パッケージの初期バージョンを定義（`__version__ = "0.1.0"`）。
  - DuckDB/SQLite を用いたデータ処理・永続化の基盤を追加（設定によりパスを指定可能）。

- 環境設定・管理
  - Settings クラスを実装し、環境変数からアプリケーション設定を取得可能に（`kabusys.config`）。
  - 自動 `.env` ロード機能を実装（プロジェクトルート検出：`.git` または `pyproject.toml` を基準）。`.env` / `.env.local` の読み込み順序をサポートし、OS 環境変数を保護する仕組みを採用。
  - `.env` パースロジックを強化：`export KEY=val`、シングル/ダブルクォート内のエスケープ、行末コメント処理に対応。
  - `config_setup` CLI を追加し、対話式ウィザードで `.env` の初期作成・更新が可能に（`python -m kabusys.config_setup`）。
  - 設定検証コマンド `validate_config` を追加。必須環境変数、KABUSYS_ENV の値、ログレベル、DB パス、config/*.yaml の存在（および PyYAML があればパース検証）などをチェックできる。`--strict` オプションで警告をエラー扱いに可能。

- 実行 / 監視ランナー
  - `run_execution` スクリプトを追加：ExecutionEngine を起動するエントリポイント。`KABUSYS_ENV=paper_trading` 時は paper_trading 専用 SQLite を使用して本番 DB と分離する実装。
    - BrokerClientFactory によるブローカークライアントの抽象化、OrderRepository / OrderManager / RiskManager / Reconciler の組み立てを行い、別スレッドで実行を行う。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）に基づく起動・終了制御を実装。
  - `run_monitoring` スクリプトを追加：SystemMonitor のポーリングループ起動スクリプト。
    - ポーリング間隔を環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。不正な値は警告してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番用の sqlite_path を使用する設計（監視データは本番 DB に記録）。

- ユーティリティ
  - `process_priority` ユーティリティを追加：Windows・POSIX を吸収してプロセス優先度（"high" / "normal" / "low"）や CPU affinity を設定可能（psutil ベース）。権限不足や未対応 OS の場合は警告してスキップ。

- ポートフォリオ構築（純粋関数群）
  - `portfolio.portfolio_builder`：シグナル選定（スコア順）、等金額・スコア基準の重み計算を実装。
  - `portfolio.risk_adjustment`：セクター集中制限（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）を実装。
  - `portfolio.position_sizing`：複数の配分方式（risk_based / equal / score）に基づく株数決定、単元株丸め、aggregate cap によるスケールダウンロジックを実装。手数料・スリッページを考慮する cost_buffer オプションもあり。

- リサーチ / ファクター計算
  - `research.factor_research`：DuckDB を使用したファクター計算モジュールを追加。
    - モメンタム（1M/3M/6M リターン、MA200 乖離）とボラティリティ系（ATR20、相対ATR、20日平均売買代金、出来高比率）を計算。
    - prices_daily テーブルを前提とした SQL 実装で、データ不足時は None を返す設計。

- ツール
  - `tools.paper_verification_report`：Paper Trading の検証レポート生成ツールを追加。
    - システム稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、API レイテンシ（avg/max/P95）などを集計し、PASS/FAIL 判定を出力。
    - 閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）をデフォルトで備え、期間指定（--from / --to）や DB パス指定（--db / 環境変数）に対応。

### Changed
- 設定読み込みの優先度を明確化：OS 環境変数 > .env.local > .env。自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能（テスト用途を想定）。
- `run_execution` / `run_monitoring` で起動時にプロセス優先度を "high" に設定するように変更（呼び出し最初に実行）。
- 環境依存の DB パス挙動：
  - `run_execution` は paper_trading 時に `PAPER_TRADING_SQLITE_PATH`（デフォルト data/paper_trading.db）を使用し、本番 DB と完全分離。
  - `run_monitoring` は監視データを書き込む sqlite は環境にかかわらず Settings.sqlite_path（本番想定）を使用。

### Fixed
- `.env` パーサーでのクォート内エスケープやインラインコメント処理の不備を改善。クォートあり/なしのケースを正しく扱い、エスケープシーケンスを解釈するように修正。
- Settings 側で不正な列挙値（例：PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL）を検出して分かりやすい例外を投げるように改善。
- `process_priority.set_process_priority` が未対応プラットフォームや権限不足で例外を投げてプロセスを落とさないように警告ログにフォールバックする挙動に修正。

### Documentation
- 各モジュールに docstring を充実させ、設計方針・期待する入力・戻り値・注意点（例：データ不足時の挙動、単元株丸めの仕様）を明記。
- CLI（config_setup, validate_config, paper_verification_report）に使用方法とオプションの説明を追加。

### Notes / Known limitations
- 一部の処理は外部データ（prices_daily / raw_financials テーブルやブローカークライアント）に依存するため、実行前に適切な DB と環境変数の設定が必要です。`validate_config` を使って事前チェックを推奨します。
- position_sizing の単元（lot_size）は現在グローバル固定（デフォルト 100）。将来的に銘柄毎の単元をサポートする設計変更を検討。
- apply_sector_cap は価格データ欠損時にエクスポージャーを低めに見積もる可能性があり、将来的にフォールバック価格の導入を検討。

--- 

変更履歴の追加や日付修正などが必要であれば指示してください。