# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠して記載しています。日付はリリース日です。

## [0.1.0] - 2026-04-19

### 追加 (Added)
- 実行用エントリポイントスクリプトを追加
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。起動時にプロセス優先度を高に設定し、BrokerClientFactory を用いてブローカークライアントを生成して ExecutionEngine をスレッドで実行します。停止フラグ（data/stop_requested.flag）や PID ファイル（data/execution.pid）に対応。（ファイル: src/kabusys/run_execution.py）
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。Monitoring は環境に依らず本番 sqlite_path を使用します。（ファイル: src/kabusys/run_monitoring.py）

- 環境設定・起動支援 CLI を追加
  - config_setup.py: .env ファイルを対話式に生成・更新するウィザードを追加。よく使う設定項目を対話で入力して .env を生成します。（ファイル: src/kabusys/config_setup.py）
  - validate_config.py: 起動前の設定検証ツールを追加。必須環境変数、KABUSYS_ENV の妥当性、DB パスの親ディレクトリ存在確認、config/*.yaml の存在と（PyYAML がインストールされている場合の）パース検証を行います。--strict フラグで警告をエラー扱いにできます。（ファイル: src/kabusys/validate_config.py）

- Paper Trading 向けユーティリティを追加
  - tools/paper_verification_report.py: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）から各種指標（稼働率、注文成功率、送信率、レイテンシ、リスク却下数）を集計し、PASS/FAIL 判定付きの検証レポートを生成する CLI を追加。期間指定オプション（--from / --to）と DB パス指定オプションをサポート。（ファイル: src/kabusys/tools/paper_verification_report.py）

- ポートフォリオ構築関連の純粋関数群を追加
  - portfolio_builder.py: シグナル選定（select_candidates）、等配分（calc_equal_weights）、スコア加重（calc_score_weights）を実装。（ファイル: src/kabusys/portfolio/portfolio_builder.py）
  - risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）を実装。未知レジームに対するフォールバックとログ出力あり。（ファイル: src/kabusys/portfolio/risk_adjustment.py）
  - position_sizing.py: 発注株数決定ロジック（risk_based / equal / score）、単元株丸め、aggregate cap によるスケーリング、コストバッファ考慮などを実装。（ファイル: src/kabusys/portfolio/position_sizing.py）
  - portfolio パッケージのエクスポートを整理して公開関数をまとめた __init__.py を追加。（ファイル: src/kabusys/portfolio/__init__.py）

- 設定管理機能を強化
  - config.py: .env 自動ロード機能を追加（プロジェクトルート自動検出、.env / .env.local の読み込み順、OS 環境変数の保護）。._parse_env_line により export プレフィックス、クォート付き値、エスケープ、インラインコメントを正しく処理します。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。Settings クラスで各種設定値（DB パス、ペーパートレード DB、PAPER_FILL_MODE の検証、閾値、env/log_level 判定など）を提供。（ファイル: src/kabusys/config.py）

- ログ・プロセス管理ユーティリティを追加
  - utils/logging_setup.py: ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30 日保持）を設定するユーティリティを追加。ログディレクトリ作成失敗時のフォールバックとログレベル解決ロジックを実装。（ファイル: src/kabusys/utils/logging_setup.py）
  - utils/process_priority.py: Windows / POSIX の差分を吸収してプロセス優先度（high/normal/low）を設定する set_process_priority を実装。CPU affinity を設定する set_cpu_affinity も追加。権限不足や未対応プラットフォーム時に安全にスキップします。（ファイル: src/kabusys/utils/process_priority.py）

- 研究用ファクター計算の骨子を追加
  - research/factor_research.py: DuckDB 接続を受けて各種ファクター（Momentum, Value, Volatility, Liquidity）を計算するための設計・定数群とモメンタム計算関数の枠組みを追加（実装途中）。（ファイル: src/kabusys/research/factor_research.py）

- パッケージメタ情報
  - __init__.py にバージョン情報と主要サブパッケージの __all__ を追加（バージョン 0.1.0）。（ファイル: src/kabusys/__init__.py）

### 変更 (Changed)
- なし（初回リリースのため主要な追加が中心）

### 修正 (Fixed)
- なし（該当なし）

### 内部 (Internal)
- monitoring と execution の DB/ログ周りの実行フローを整理
  - monitoring は環境にかかわらず本番 sqlite_path を使う旨を明示。（ファイル: src/kabusys/run_monitoring.py）
  - execution は KABUSYS_ENV=paper_trading の場合に paper_sqlite_path を使用し、本番 DB と分離する設計を実装。（ファイル: src/kabusys/run_execution.py）
- 設定ファイル生成・検証の UX を改善
  - config_setup が既存 .env を読み込んで Enter で再利用できるようにし、secret 項目は表示をマスクする等の操作性向上を実施。（ファイル: src/kabusys/config_setup.py）
  - validate_config は PyYAML がなければ YAML 検証をスキップし警告を出す柔軟な挙動に。（ファイル: src/kabusys/validate_config.py）
- ログ出力を stdout に統一してデーモン／cron から使いやすくした（StreamHandler を stdout に設定）。（ファイル: src/kabusys/utils/logging_setup.py）

### 既知の問題 / TODO
- portfolio.risk_adjustment.apply_sector_cap: price が欠損（0.0）の場合にエクスポージャーが過少評価される可能性があり、フォールバック価格（前日終値等）を導入する TODO が残っています。
- position_sizing: 将来的に銘柄別の lot_size を導入する計画（README/PortfolioConstruction.md を参照）があります。
- research/factor_research.py は一部実装が途中でファイル末尾が切れており、完全実装には続きが必要です。

---

今後のリリースでは、ExecutionEngine/OrderManager/リスク管理の詳細実装、ブローカークライアントの Mock と実ブラウザの統合、研究用ファクター計算の完成、テスト・ドキュメントの充実などを予定しています。