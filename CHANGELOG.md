# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠します。  
日付の表記は YYYY-MM-DD 形式です。

## [0.1.0] - 2026-04-21

### Added
- 全体
  - 初回リリース。日本株自動売買システム「KabuSys」の基本機能群を実装。
  - パッケージバージョンを `__version__ = "0.1.0"` として設定。

- 起動スクリプト / 実行関連
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。不正値時はデフォルトにフォールバックして警告を出力。
    - 監視プロセス停止用フラグファイル（data/stop_requested.flag）を監視して安全にループを終了。
    - 監視用 DB は環境にかかわらず本番用 SQLite パスを使用する設計を採用（監視データは本番 DB に記録）。
    - 起動時にプロセス優先度を "high" に設定。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は paper_trading 専用 SQLite（data/paper_trading.db）を使用し、本番 DB と分離（MockBroker を利用する想定）。
    - 起動時にプロセス優先度を "high" に設定し、PID ファイルの管理と停止フラグによる安全停止を実装。
    - ExecutionEngine を別スレッドで実行し、停止フラグを検知したら engine.stop() を呼び出して終了処理を行う。

- 設定管理
  - config.py
    - 環境設定を集約する `Settings` クラスを実装（プロパティ方式で各種環境変数を取得・検証）。
    - .env 自動ロード機能を実装（プロジェクトルートの特定: .git または pyproject.toml を探索）。OS 環境変数優先、`.env.local` は上書き可能。
    - .env のパースは以下をサポート:
      - `export KEY=val` 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの取り扱い。
    - PAPER_FILL_MODE の妥当性チェック（`instant|partial|never|reject`）を実装。
    - 各種しきい値（CPU/MEM/DISK 閾値）やパス、PID/KILL フラグの設定を提供。
  - config_setup.py
    - 対話式ウィザードにより .env ファイルを初期作成・更新する CLI を実装。
    - 秘密値は表示時にマスク、既存値の再利用、選択肢のバリデーション、.env の書き出しテンプレートを提供。
    - 生成された .env に関する注意書き（Git にコミットしない等）を含む。

- 設定検証ツール
  - validate_config.py
    - .env および config/*.yaml の設定整合性を起動前に検証する CLI を提供。
    - 必須環境変数未設定やプレースホルダ値の警告、KABUSYS_ENV の妥当性チェック、ログレベル検証、DB パス親ディレクトリチェックを実装。
    - PyYAML がインストールされていれば config/*.yaml のパース検証を行い、存在しないファイルやパースエラーを適切に報告。
    - `--strict` オプションにより警告も失敗扱いにできる。

- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（1日毎・30 日保持）を設定するユーティリティを追加。
    - ログレベル・ログディレクトリは引数／環境変数／デフォルトの順で解決。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみ継続。
  - utils/process_priority.py
    - Windows と POSIX 系（Linux/macOS 等）の差分を吸収したプロセス優先度設定ユーティリティを追加。
    - `set_process_priority(level)`：`high|normal|low` をサポート。権限不足などで失敗しても警告を出してスキップ。
    - `set_cpu_affinity(cpu_count)`：プロセスを最初の N コアにピン留めする機能を実装（権限や未対応 OS の場合は警告）。

- ポートフォリオ構築（純粋関数群、DB 非依存）
  - portfolio/portfolio_builder.py
    - 候補選定（スコア降順・タイブレーク）、等分配・スコア加重配分計算を実装。スコアがすべて 0 の場合は等分配にフォールバックし警告を出す。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）: 既存ポジションのセクター比率が上限を超える場合、新規候補の除外を行う。unknown セクターは上限適用外。
    - レジームに応じた投下資金乗数（calc_regime_multiplier）: `bull=1.0`, `neutral=0.7`, `bear=0.3`。不明レジームは 1.0 にフォールバックして警告。
  - portfolio/position_sizing.py
    - ポジション株数決定ロジックを実装（allocation_method: `risk_based` / `equal` / `score`）。
    - 単元株（lot_size）で丸め、1 銘柄上限や aggregate cap（available_cash）でスケールダウン。cost_buffer を用いた保守的コスト見積もりを考慮。
    - スケールダウン時に小数点端数の優先度（fractional remainder）に基づいて lot 単位で追加配分するロジックを実装。
    - 価格欠損時は該当銘柄をスキップする安全策を実装。

- 監視・レポートツール
  - monitoring.monitoring_db: 起動スクリプトから監視 DB の初期化（init_monitoring_db）が呼ばれることで監視テーブルの整合性を保証（冪等）。
  - tools/paper_verification_report.py
    - ペーパートレード結果を集計してレポートを生成する CLI を追加。
    - 稼働率（uptime）、注文成功率（fill rate）、送信率、P95 レイテンシなどの指標を計算して PASS/FAIL を判定する基準を搭載。
    - データ不足やテーブル未存在時に適切に N/A を扱い、SQLite ファイルパスは引数・環境変数・デフォルトの優先順で解決。

- 解析 / 研究
  - research/factor_research.py
    - DuckDB を用いたファクター計算フレームワーク（モメンタム、移動平均乖離、ATR、出来高系等）を開始実装。prices_daily / raw_financials テーブルを参照し、結果を (date, code) ベースの dict リストで返す設計。

### Changed
- 設計決定
  - 監視（monitoring）は環境変数に依存せず「本番の sqlite_path を使用する」設計を明確化（監視データは常に本番 DB に記録されることを想定）。一方、Execution は paper_trading 環境で専用 DB を使用して本番データと分離。

### Security
- .env の取り扱いに関する注意書きを config_setup の生成ファイルに明記（.env を Git にコミットしないことを強調）。

### Notes / Known limitations
- research/factor_research.py は計算ロジックの主要部分を含むが、外部に依存しない実装設計のため、DuckDB 内のテーブル構造（prices_daily / raw_financials）に依存する。実データ投入前にスキーマ準備が必要。
- position_sizing の価格欠損（price が 0.0）の扱いは現状スキップとしているが、将来的に前日終値等のフォールバックが必要と考えられる（TODO コメントあり）。
- 一部機能は外部ライブラリ（psutil, duckdb, PyYAML 等）に依存。環境によっては機能が制限され、その場合は警告を出してフォールバックする設計。

---

今後の予定（例）
- 戦略シグナル生成 / ExecutionEngine 本体の完成度向上、テストカバレッジ追加
- DuckDB を使ったバッチ解析パイプラインの強化
- 監視アラート（LINE 通知等）統合の実装強化