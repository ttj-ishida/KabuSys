# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に従って記載しています。  
フォーマット: Unreleased / [0.1.0] - YYYY-MM-DD

## [Unreleased]

## [0.1.0] - 2026-04-19
初回リリース。

### Added
- 基本パッケージ構成を追加
  - パッケージ名: `kabusys`
  - バージョン: `0.1.0`（`src/kabusys/__init__.py`）
- 起動スクリプト / サービス
  - run_monitoring: システム監視ポーリングループ（`src/kabusys/run_monitoring.py`）
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔の上書きをサポート（デフォルト 60 秒）。
    - 監視用途の停止フラグファイル（`data/stop_requested.flag`）検出で安全にループ終了。
    - Monitoring は実行環境にかかわらず本番の `sqlite_path` を使用（監視データは分離されない設計）。
  - run_execution: ExecutionEngine 起動スクリプト（`src/kabusys/run_execution.py`）
    - `KABUSYS_ENV=paper_trading` のときは paper trading 用 DB を使用し、MockBrokerClient を利用して本番 DB と完全分離。
    - 実行中のプロセス停止は停止フラグ（`data/stop_requested.flag`）で制御。PID ファイルサポート。
- 設定・環境変数管理
  - `Settings` クラスによる環境設定管理（`src/kabusys/config.py`）
    - 自動 .env ロード機能（プロジェクトルート検出: `.git` または `pyproject.toml` を起点）。
    - `.env` / `.env.local` の読み込み順序（OS 環境変数を保護）。`KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能。
    - 各種プロパティ（DB パス、API トークン、環境フラグ、モニタ閾値、PID/kill flag パス 等）を提供。
    - `paper_fill_mode` の有効値検証 (`instant|partial|never|reject`)。
- 設定関連 CLI
  - `config_setup`: インタラクティブな .env 生成・更新ウィザード（`src/kabusys/config_setup.py`）
    - 対話式プロンプト、既存値再利用、シークレットマスク表示、保存確認。
  - `validate_config`: 起動前設定検証ツール（`src/kabusys/validate_config.py`）
    - 必須環境変数のチェック、KABUSYS_ENV の妥当性、ログレベル、DB パスの親ディレクトリ存在確認、`config/*.yaml` の存在および（PyYAML があれば）パース検証。
    - `--strict` オプションで警告を FAIL 扱いにできる。
- ロギング / プロセス制御ユーティリティ
  - `setup_logging`: ルートロガーの統一設定（`src/kabusys/utils/logging_setup.py`）
    - stdout StreamHandler と 日次ローテートの TimedRotatingFileHandler（デフォルト `logs/`、30 日保持）を設定。
    - `LOG_LEVEL` / `LOG_DIR` / 引数 `level`/`log_dir` による解決。
    - ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
  - `process_priority`: クロスプラットフォームのプロセス優先度 / CPU affinity 設定（`src/kabusys/utils/process_priority.py`）
    - Windows/Linux/Mac (一部) を吸収して `set_process_priority("high"|"normal"|"low")` を提供。
    - `set_cpu_affinity(n)` による最初の N コアに固定（未許可や未実装プラットフォームは警告でスキップ）。
    - 起動スクリプトから高優先度での起動を行うようになっている。
- ポートフォリオ構築関連（純粋関数群・メモリ計算）
  - portfolio_builder（`select_candidates`, `calc_equal_weights`, `calc_score_weights`）
    - シグナルのソート / 上位 N 選出 / 等金額・スコア加重配分（全スコア0時は等配分へフォールバック）。
  - risk_adjustment（`apply_sector_cap`, `calc_regime_multiplier`）
    - セクター集中制限: 既存ポジションのセクター別時価を計算し上限超過セクターの新規候補を除外（unknown セクターは除外対象外）。
    - レジーム乗数: `"bull"=1.0`, `"neutral"=0.7`, `"bear"=0.3`。未知レジームは 1.0 にフォールバックし警告出力。
  - position_sizing（`calc_position_sizes`）
    - allocation_method: `"risk_based"`, `"equal"`, `"score"` をサポート。
    - リスクベース: risk_pct / stop_loss_pct を用いてベース株数算出、lot_size（単元株）で丸め込み。
    - per-position / aggregate cap を適用し、available_cash を超える場合はスケーリングと端数再配分を行う。
    - cost_buffer による保守的なコスト見積り（スリッページ等）に対応。
- Paper Trading 検証ツール
  - `tools.paper_verification_report`（`src/kabusys/tools/paper_verification_report.py`）
    - Paper Trading の SQLite DB（環境変数 `PAPER_TRADING_SQLITE_PATH`、デフォルト `data/paper_trading.db`）を解析して検証レポートを生成。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等。
    - デフォルト基準値（PASS/FAIL 判定）を導入:
      - 稼働率 >= 99.0%
      - 成立率 >= 90.0%
      - 送信率 >= 95.0%
      - P95 レイテンシ <= 200 ms
    - CLI オプション `--from` / `--to` / `--db` サポート。
- リサーチモジュール（一部）
  - `research.factor_research` を追加（モメンタム等のファクター計算を想定、DuckDB 接続を受ける設計）。（実装が途中で切れている箇所あり）

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Notes / Usage highlights
- .env 自動読み込み
  - プロジェクトルート検出によりアプリケーション実行ディレクトリに依存せず `.env` / `.env.local` を適切に読み込むようにしました。
  - OS 環境変数は保護され、`.env.local` は `.env` の上から上書きされます。
  - 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- Paper Trading の分離
  - 実行エンジンは `KABUSYS_ENV=paper_trading` の場合、`PAPER_TRADING_SQLITE_PATH`（デフォルト `data/paper_trading.db`）を使用して本番 DB と分離します。これによりペーパートレードのログが本番 DB に混ざりません。
- ログ
  - デフォルトで `logs/<app_name>.log` に日次ローテーションで出力します。ログディレクトリ作成に失敗した場合はコンソール出力のみになります。
- プロセス優先度
  - 起動スクリプトは起動直後に `set_process_priority("high")` を呼びます。実行環境により権限不足で設定できない場合は警告を出してスキップします。
- 停止制御
  - 停止フラグファイル（`data/stop_requested.flag`）を用いた外部制御を採用しています。CI / デプロイ環境で停止を指示するのに便利です。

### Environment variables (主なもの)
- 必須 / 重要:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
- 環境切替:
  - KABUSYS_ENV (development | paper_trading | live)
- DB パス:
  - DUCKDB_PATH (デフォルト data/kabusys.duckdb)
  - SQLITE_PATH (監視用デフォルト data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (ペーパートレード用デフォルト data/paper_trading.db)
- ログ / 挙動:
  - LOG_LEVEL, LOG_DIR
  - MONITOR_POLL_INTERVAL (監視ポーリング間隔, 秒)
  - PAPER_FILL_MODE (paper trading の fill モード: instant|partial|never|reject)
  - KILL_FLAG_CLEAR_ON_START
  - KABUSYS_DISABLE_AUTO_ENV_LOAD

### Breaking Changes
- なし（初回リリース）

### Known issues / TODO
- research.factor_research モジュールの実装が途中で切れている部分がある（今後完成予定）。
- position_sizing 内の price が欠損（0.0）の場合の扱いは TODO コメントで示されたフォールバック価格処理の追加が望まれる。
- Logging ファイルハンドラの作成失敗時は StreamHandler のみで継続するが、運用時にこの状況を監視することを推奨。

---

（以上）