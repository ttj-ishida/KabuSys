# Changelog

すべての注目すべき変更点をこのファイルで管理します。
フォーマットは「Keep a Changelog」に準拠しています。

なお、この CHANGELOG はリポジトリ内のソースコードから動作・仕様を推測して作成しています。実際の変更履歴と異なる可能性があります。

## [Unreleased]

## [0.1.0] - 2026-04-24
初回公開リリース（推定）。以下の主要機能・ユーティリティ群を実装しています。

### 追加 (Added)
- 全体
  - パッケージ初期バージョンを導入。メタ情報は `kabusys.__version__ = "0.1.0"`。
  - DuckDB / SQLite を用いた分析・監視基盤をサポート（`duckdb_path`, `sqlite_path` の設定）。
  - .env 自動読み込み機能（プロジェクトルート（.git または pyproject.toml）を探索して `.env` / `.env.local` を読み込む）。

- 設定管理 (`src/kabusys/config.py`)
  - 環境変数抽象化クラス `Settings` を提供。各種設定（J-Quants、kabuステーション、LINE、DB、監視閾値、実行環境など）をプロパティとして取得。
  - `PAPER_FILL_MODE`（paper trading のモックの約定動作）に対応。許容値: "instant" / "partial" / "never" / "reject"。
  - `PAPER_TRADING_SQLITE_PATH` によるペーパートレード専用 DB パスをサポート。
  - 環境変数の自動ロードを無効化する `KABUSYS_DISABLE_AUTO_ENV_LOAD` を提供。

- .env パーサ（内蔵）
  - `.env` の各行パース機能を強化:
    - `export KEY=val` 形式に対応
    - クォート（シングル/ダブル）内のバックスラッシュエスケープ対応
    - クォート無しの値におけるインラインコメント処理（`#` 前が空白/タブの場合はコメント）
  - `_load_env_file` は既存 OS 環境変数の保護や上書き制御（override / protected）機能を持つ。

- ログ設定ユーティリティ (`src/kabusys/utils/logging_setup.py`)
  - `setup_logging(app_name, log_dir, level)` を導入。
  - stdout へ出力する StreamHandler と、日次ローテーション（30日保存）の TimedRotatingFileHandler をルートロガーに設定。
  - ログディレクトリの自動作成を試み、失敗した場合はファイルハンドラをスキップしてコンソール出力のみ継続。

- プロセス優先度 / CPU affinity (`src/kabusys/utils/process_priority.py`)
  - `set_process_priority(level)` により Windows / POSIX を吸収してプロセス優先度（high/normal/low）を設定。
  - `set_cpu_affinity(cpu_count)` によりカレントプロセスを先頭 N コアに固定する機能を追加。
  - psutil を用い、アクセス拒否等の例外はログ警告で安全にスキップ。

- 実行・監視エントリポイント
  - 実行エンジン起動スクリプト `run_execution.py`
    - ExecutionEngine の起動フローを実装。依存コンポーネント（BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler）を組み立ててエンジンをスレッドで実行。
    - `KABUSYS_ENV=paper_trading` の場合は専用の paper SQLite DB（`PAPER_TRADING_SQLITE_PATH`）を使い、本番 DB と完全分離。
    - 起動前に停止フラグ（data/stop_requested.flag）をチェックし、既に立っていれば起動を行わない。
    - 実行中は停止フラグを監視し、検知時にエンジンを安全に停止。
  - 監視ループ起動スクリプト `run_monitoring.py`
    - SystemMonitor を初期化しポーリングループを実行。
    - ポーリング間隔を環境変数 `MONITOR_POLL_INTERVAL`（デフォルト 60 秒）で上書き可能。無効値はデフォルトへフォールバックし警告を出す。
    - 監視は環境にかかわらず本番用の sqlite_path を使用する（監視用 DB を統一）。
    - 停止フラグ（data/stop_requested.flag）検知でループを終了。KeyboardInterrupt に対応して適切にクローズ。

- 構成ウィザード・検証ツール
  - `config_setup.py`：対話式ウィザードで `.env` を生成/更新する CLI を追加。主要な環境項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、LINE トークン等）をガイド付きで入力可能。
  - `validate_config.py`：`.env` や `config/*.yaml` の事前検証 CLI を追加。`--strict` フラグで警告も失敗（exit(1)）扱いにできる。YAML のパース検証は PyYAML が存在する場合に実施。

- Paper Trading 検証レポート (`src/kabusys/tools/paper_verification_report.py`)
  - ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）から各種指標（稼働率、注文成功率、送信率、P95 レイテンシ等）を集計し、判定（PASS/FAIL）を出力する CLI を追加。
  - P95 の計算、フィルタ（日時範囲）、各種閾値（稼働率 99%、成功率 90% 等）を標準実装。
  - CLI オプション `--from`, `--to`, `--db` をサポート。

- ポートフォリオ構築関連（純粋関数群）
  - `portfolio.portfolio_builder`
    - 候補選定（スコア降順 + signal_rank tiebreak）、等重/スコア重み計算を提供。
  - `portfolio.risk_adjustment`
    - セクター集中（最大セクター比率）を適用する `apply_sector_cap`。
    - レジームに基づく資金乗数を返す `calc_regime_multiplier`（"bull"/"neutral"/"bear" をサポート）。
  - `portfolio.position_sizing`
    - 各配分方式（risk_based / equal / score）に基づく株数算出 `calc_position_sizes`。
    - 単元株（lot_size）丸め、per-stock 上限（max_position_pct）、aggregate cap（available_cash を超えた場合のスケールダウン）を実装。
    - cost_buffer を用いた保守的コスト見積りと、残余キャッシュを使った補正ロジックあり。

- 研究用ファクター計算（着手中）
  - `research.factor_research`：DuckDB の prices_daily / raw_financials を参照して Momentum、Value、Volatility、Liquidity 等を計算する設計。モジュールは主要定数と momentum 計算関数の骨子を実装（詳細実装は作業中でファイル末尾が途中の状態）。

### 変更 (Changed)
- ログ出力の標準化
  - すべての起動スクリプトで `setup_logging` を呼ぶようにしてログ運用を統一。
- DB 初期化
  - `init_monitoring_db` を使用して起動時に監視テーブルの存在を保証（冪等に実行）。

### 修正 (Fixed)
- 環境変数読み込みの堅牢化
  - クォートやエスケープ、コメントの扱いに起因する読み取りミスを軽減。

### 既知の問題・TODO
- research.factor_research.py が途中で終端している（関数実装が不完全）。ファクター計算の完全実装が必要。
- position_sizing の価格フォールバック処理に TODO があり、価格欠損時の扱いが限定的（将来的に前日終値などを利用する案あり）。
- 一部のファイル・機能（例: BrokerClientFactory、ExecutionEngine、SystemMonitor 等）は本 CHANGELOG の元となるソース内に依存実装があるが、ここでは振る舞いを推測して記載している。実装の詳細・副作用は実コードを参照のこと。

### セキュリティ (Security)
- 本リリースで特定のセキュリティ修正は記載なし。ただし `.env` ファイルを絶対にリポジトリへコミットしない旨を `config_setup` の出力で明示。

---

将来のリリースでは、未実装のファクター計算、より細かなエラーハンドリング、テスト追加、ドキュメント整備（API ドキュメント、操作手順）などの追補を予定してください。必要であれば、各ファイルごとにさらに詳細な変更点（関数仕様、例外処理、環境変数の完全リスト等）も生成できます。どの粒度で出力するか指定してください。