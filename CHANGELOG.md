# Changelog

すべての重要な変更をここに記録します。本ファイルは「Keep a Changelog」形式に準拠します。  

注意: バージョン番号はパッケージ内の `kabusys.__version__` に合わせてあります。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-21

初回公開リリース。システム全体の起動スクリプト、設定管理、検証ツール、ポートフォリオ構築ロジック、ユーティリティ群、および Paper Trading 向け検証レポート機能を追加しました。

### Added
- 基本パッケージ情報
  - `src/kabusys/__init__.py` にてパッケージを定義。バージョン `0.1.0` を設定。

- 起動スクリプト
  - `src/kabusys/run_monitoring.py`
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止制御にプロジェクト配下 `data/stop_requested.flag` を利用。
    - 起動時にプロセス優先度を "high" に設定。
    - 監視DBは KABUSYS_ENV に関係なく本番用の `sqlite_path` を使用。
  - `src/kabusys/run_execution.py`
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合はペーパートレード用 DB（`data/paper_trading.db` デフォルト）を使用し、本番 DB と分離（MockBrokerClient を使用する想定）。
    - 停止フラグ（`data/stop_requested.flag`）と PID 管理（`data/execution.pid`）に対応。
    - 起動時にプロセス優先度を "high" に設定。

- 設定管理 / ウィザード / 検証
  - `src/kabusys/config.py`
    - .env 自動読み込み機構（プロジェクトルート探索 `.git` または `pyproject.toml`）。
    - 柔軟な .env パース（`export KEY=val`、クォートとエスケープ、インラインコメント対応）。
    - `Settings` クラスで主要な環境変数をプロパティ化（DB パス、KABUSYS_ENV、ログレベル、paper_trading 関連等）。
    - `paper_fill_mode` の検証、環境判定ヘルパ（is_live / is_paper / is_dev）。
  - `src/kabusys/config_setup.py`
    - 対話式 .env 作成ウィザードを追加。主要設定項目のプロンプト、既存 .env の取り込み、保存機能を提供。
  - `src/kabusys/validate_config.py`
    - 起動前の設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスや `config/*.yaml` の存在・パース検証（PyYAML が無ければ警告）、`live` 環境向けガード等を実装。
    - `--strict` オプションで警告も失敗扱いにできる。

- ポートフォリオ構築（純粋関数群）
  - `src/kabusys/portfolio/portfolio_builder.py`
    - シグナル選定 (`select_candidates`) と重み計算 (`calc_equal_weights`, `calc_score_weights`) を追加。スコア全0時は等重でフォールバック。
  - `src/kabusys/portfolio/risk_adjustment.py`
    - セクター集中制限 (`apply_sector_cap`) とマーケットレジームに応じた投下資金乗数 (`calc_regime_multiplier`) を追加。
    - `apply_sector_cap` は既存保有の時価を元にセクター上限を判定し、超過セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - `calc_regime_multiplier` は `bull/neutral/bear` に対してそれぞれ `1.0/0.7/0.3` を返し、未知のラベルは警告して `1.0` にフォールバック。
  - `src/kabusys/portfolio/position_sizing.py`
    - 発注株数算出ロジックを実装（allocation_method: `risk_based`, `equal`, `score` をサポート）。
    - 単元株（lot_size）に従う丸め、銘柄ごとの上限（max_position_pct）、総投入資金の aggregate cap、cost_buffer（手数料・スリッページ見積り）による保守的見積り、スケーリングおよび残余キャッシュによる再配分ロジックを実装。

- Paper Trading 向けツール
  - `src/kabusys/tools/paper_verification_report.py`
    - ペーパートレード結果の検証レポート生成スクリプトを追加。
    - 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等を算出して PASS/FAIL 判定を行う。
    - デフォルトの DB パスは `data/paper_trading.db`。コマンドライン引数で期間指定（--from / --to）や DB パス（--db）を指定可能。
    - 基準値（例: uptime >= 99.0%, fill_rate >= 90% 等）を定義し、判定結果を分かりやすく出力。

- ユーティリティ
  - `src/kabusys/utils/logging_setup.py`
    - 統一的なログ設定ユーティリティを追加。Console (stdout) と日次ローテーションファイル（TimedRotatingFileHandler）をルートロガーに設定。
    - ログディレクトリの作成失敗時にファイル出力をスキップしてコンソールのみで動作。
    - 環境変数 `LOG_LEVEL` / `LOG_DIR` を考慮。
  - `src/kabusys/utils/process_priority.py`
    - プロセス優先度設定と CPU affinity 設定を跨プラットフォームで提供（Windows / POSIX（Linux, macOS, FreeBSD）対応を想定、psutil 利用）。
    - `set_process_priority(level)`（high/normal/low）と `set_cpu_affinity(cpu_count)` を追加。権限不足などは警告でフォールバック。

- 研究用モジュール（ファクター計算）
  - `src/kabusys/research/factor_research.py`
    - ファクター計算モジュールを追加（モメンタム等の指標算出を想定）。DuckDB 接続を受けて prices_daily / raw_financials を参照する設計。
    - モメンタム計算（calc_momentum）に関する定数と処理方針を実装開始。

### Changed
- 初期リリースのため既存コードの大幅な変更はなし（新規追加が中心）。

### Fixed
- 初回リリースのため特定のバグ修正履歴はなし。

### Notes / Important behavior
- 監視コンポーネントは環境（KABUSYS_ENV）に関係なく監視用の本番 sqlite パスを使用する設計になっています。ペーパートレード用の分離 DB は実行コンポーネント（ExecutionEngine）の側で `KABUSYS_ENV=paper_trading` を判定して切り替えます。
- .env 自動ロードはプロジェクトルートが検出できた場合のみ行われ、OS 環境変数はデフォルトで保護されます。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- ログは stdout とファイルの両方へ出力されますが、ログディレクトリ作成に失敗した場合はファイル出力を無効化して stdout のみで継続します。
- process priority / CPU affinity は権限やプラットフォームにより動作しない場合があります。その場合は警告を出してスキップします。

---

今後の予定（参考）
- research/factor_research の完全実装（各ファクター算出ロジックの完成）。
- ExecutionEngine / Broker 周りの詳細実装とテスト。
- 追加の CLI、メトリクス出力、より細かいログ設定オプション等。

（以上）