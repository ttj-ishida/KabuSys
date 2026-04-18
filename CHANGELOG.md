# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に従います。  
このプロジェクトのバージョン付けは [SemVer](https://semver.org/) に準拠します。

## [0.1.0] - 2026-04-18

### 追加
- 全体
  - 初期リリースを追加。パッケージ `kabusys` のバージョンを 0.1.0 に設定。
- 起動スクリプト
  - `run_execution.py`：ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV に応じて paper_trading 用の専用 SQLite を使用（環境変数 / Settings による切替）。
    - MockBrokerClient を使用する場合は paper_trading 用 DB（デフォルト: data/paper_trading.db）へ記録し、本番 DB と分離。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）をサポート。
    - スレッドで Engine を実行し、停止フラグ検出時に安全に停止させるループを実装。
    - 起動時にプロセス優先度を "high" に設定。
  - `run_monitoring.py`：SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用 sqlite_path を使用して初期化。
    - 停止フラグ（data/stop_requested.flag）検出でループ終了。KeyboardInterrupt をハンドルしてクリーンに終了。
    - 起動時にプロセス優先度を "high" に設定。
- 設定管理
  - `config.py`：Settings クラスを追加。
    - .env の自動読み込み（プロジェクトルートの `.env` / `.env.local`）をサポート。ただし `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - `.env` 自動検索は __file__ を起点にプロジェクトルート（`.git` または `pyproject.toml`）を探索して行うため、CWD に依存しない。
    - 環境変数のパース・検証ロジック（PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL 等）を備える。
    - DB パス（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH）や監視系設定（pid_file_path, kill_flag_path, 各閾値）用プロパティを提供。
- 設定ユーティリティ / CLI
  - `config_setup.py`：対話式 .env 作成ウィザードを追加。
    - 主要設定項目のプロンプト、既存 .env の読み込み/再利用、シークレットのマスク表示、保存確認を実装。
    - 保存時にはテンプレート付きの .env を生成（Git コミット禁止の注意書きを含む）。
  - `validate_config.py`：設定検証 CLI を追加。
    - 必須環境変数の存在チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、`config/*.yaml` の存在確認（PyYAML があればパース検証）等を実施。
    - `--strict` オプションで警告を失敗扱いにできる。
- ログ / プロセスユーティリティ
  - `utils/logging_setup.py`：統一的なログ設定ユーティリティを追加。
    - stdout への StreamHandler と日次ローテート（TimedRotatingFileHandler、30 日保持）をルートロガーに設定。
    - LOG_DIR / LOG_LEVEL 環境変数または引数で上書き可能。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - `utils/process_priority.py`：プロセス優先度 / CPU affinity 設定ユーティリティを追加。
    - Windows と POSIX(Linux/macOS/FreeBSD) の差分を吸収して優先度設定（"high" / "normal" / "low"）を提供。
    - CPU affinity 固定機能を提供（core 数指定）。権限不足や未対応環境では警告を出してスキップ。
- ポートフォリオ構築（純粋関数群）
  - `portfolio/portfolio_builder.py`：
    - シグナル選定（select_candidates: スコア降順、タイブレークは signal_rank）。
    - 等金額配分（calc_equal_weights）。
    - スコア加重配分（calc_score_weights） — 全銘柄スコアが 0 の場合は等金額にフォールバックし WARNING を出力。
  - `portfolio/risk_adjustment.py`：
    - セクター集中制限（apply_sector_cap）：既存保有のセクター比率が上限を超える場合、そのセクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - レジーム乗数（calc_regime_multiplier）：regime label に応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3）。未知レジームは 1.0 にフォールバックして WARNING。
  - `portfolio/position_sizing.py`：
    - position size 計算ロジックを実装（allocation_method: "risk_based" / "equal" / "score"）。
    - 単元株（lot_size）で丸め、1 銘柄上限、aggregate cap（available_cash）を考慮したスケーリング、余りキャッシュを fractional 残差順に lot 単位で配分するアルゴリズムを実装。
    - 手数料・スリッページ見積り用の cost_buffer を導入。
- Paper Trading 検証ツール
  - `tools/paper_verification_report.py`：
    - ペーパートレード用 SQLite を集計して検証レポートを生成する CLI を追加。
    - 主要指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、レイテンシ（avg/max/P95）、リスク却下数。
    - P95 計算、期間フィルタ（--from/--to）、閾値による PASS/FAIL 判定を実装。
    - デフォルト DB パスは data/paper_trading.db。環境変数 PAPER_TRADING_SQLITE_PATH または --db で上書き可能。
- 研究 / ファクター計算
  - `research/factor_research.py`（スケルトン/実装開始）：
    - Momentum / Value / Volatility / Liquidity 系ファクターを計算する設計を導入。DuckDB を用いた prices_daily / raw_financials テーブル参照の方針を明示。
    - モメンタム計算（calc_momentum）の関数シグネチャと定数を追加（実装は継続）。

### 変更
- なし（初期公開）

### 修正
- なし（初期公開）

### 注意事項 / 既知の制約
- `.env` 自動読み込みはプロジェクトルート検出に依存する（`.git` または `pyproject.toml`）。ルート検出に失敗すると自動ロードはスキップされる。
- `config/*.yaml` の内容検証は PyYAML がインストールされている場合のみ行われる（未インストール時は警告）。
- `process_priority` / `set_cpu_affinity` は OS や実行権限に依存し、設定に失敗すると警告を出してスキップする。
- 一部モジュール（research/factor_research.py の一部など）は実装途中またはスケルトンとして存在するため、機能拡張や検証が必要。

### セキュリティ
- シークレット（トークン・パスワード）は .env に明記して管理する設計。`.env` を Git にコミットしないことを強く推奨（config_setup のヘッダに注意書きあり）。

---

今後の予定（例）
- factor_research のファクター実装完了・テスト追加
- ExecutionEngine / Broker の統合テスト、MockBroker の充実
- モニタリング関連のメトリクス拡充とアラート（LINE）連携
- 単体テスト・CI の整備

もし特定の変更点（例: 追加した関数、挙動の詳細）をより細かく記載したい場合は、対象モジュールを指定してください。