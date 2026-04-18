KEEP A CHANGELOG
All notable changes to this project will be documented in this file.

フォーマットは「Keep a Changelog」準拠。  
https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-04-18

初回リリース。主要機能とユーティリティをまとめて追加。

### Added
- 一般
  - パッケージ初期バージョンを 0.1.0 として公開。 (src/kabusys/__init__.py)
  - プロジェクトルート検出ロジックを追加（.git / pyproject.toml を基準）。自動 .env 読み込みでカレントディレクトリに依存しない実装。 (src/kabusys/config.py)

- 設定管理
  - Settings クラスを追加し、環境変数経由で設定を一元管理。複数の便利プロパティ（duckdb/sqlite パス、KABUSYS_ENV 判定、paper_trading 切替、各種閾値など）を提供。 (src/kabusys/config.py)
  - .env ファイル自動読み込み機能を実装（.env → .env.local の順で読み込み、OS 環境変数は保護）。export KEY=val 形式・クォートやエスケープ、インラインコメントへの対応を含む堅牢なパーサを実装。 (src/kabusys/config.py)
  - 環境設定ウィザード CLI を追加し、対話的に .env を生成・更新できるようにした（python -m kabusys.config_setup）。出力テンプレートと既存値の読み取り/マスク表示をサポート。 (src/kabusys/config_setup.py)

- 設定検証
  - validate_config CLI を追加。必須環境変数や KABUSYS_ENV、ログレベル、DB パス、config/*.yaml の存在とパース（PyYAML があれば内容検証）等を検査し、errors/warnings/infos を報告。--strict オプションで警告を FAIL 扱いに可能。 (src/kabusys/validate_config.py)

- 実行/監視ランナー
  - 実行エンジン起動スクリプトを追加（run_execution.py）。
    - 起動時にプロセス優先度を high に設定。
    - paper_trading モードの際は paper 専用 SQLite DB を使用して本番 DB と分離。
    - BrokerClientFactory を経由したブローカークライアント取得、OrderRepository/OrderManager/RiskManager/Reconciler を組み立てて ExecutionEngine を起動。停止フラグ（data/stop_requested.flag）による安全停止をサポート。 (src/kabusys/run_execution.py)
  - 監視ループ起動スクリプトを追加（run_monitoring.py）。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番用 sqlite_path を使用して監視テーブルを初期化。停止フラグでループ終了。 (src/kabusys/run_monitoring.py)

- ロギング・プロセスユーティリティ
  - ロギング設定ユーティリティを追加（setup_logging）。
    - stdout への StreamHandler と日次ローテートの TimedRotatingFileHandler（デフォルト logs/<app_name>.log、30 日保持）をルートロガーに設定。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールログのみで継続。 (src/kabusys/utils/logging_setup.py)
  - プロセス優先度 / CPU affinity 設定ユーティリティを追加（set_process_priority / set_cpu_affinity）。
    - Windows と POSIX（Linux/Mac 等）を吸収する実装。権限不足や未対応 OS の場合は警告してスキップ。 (src/kabusys/utils/process_priority.py)

- ポートフォリオ構築（純粋関数群）
  - 候補選定と重み計算: select_candidates, calc_equal_weights, calc_score_weights（スコアゼロ時は等分配にフォールバック）。 (src/kabusys/portfolio/portfolio_builder.py)
  - セクター集中制限とレジーム乗数: apply_sector_cap（既存保有を考慮してセクター上限をチェック）、calc_regime_multiplier（bull/neutral/bear に対する乗数）を実装。 (src/kabusys/portfolio/risk_adjustment.py)
  - 発注株数決定（丸め・上限・aggregate cap）: calc_position_sizes。risk_based / equal / score の配分方式に対応し、単元株（lot_size）で丸め、合計金額が利用可能現金を上回る場合はスケーリングして端数を残差順に配分するロジックを実装。cost_buffer による保守的コスト見積りにも対応。 (src/kabusys/portfolio/position_sizing.py)
  - ポートフォリオパッケージ __init__ で主要関数をエクスポート。 (src/kabusys/portfolio/__init__.py)

- 研究用途（ファクター計算）
  - ファクター計算モジュールの骨組みを追加。モメンタム（1M/3M/6M リターン、MA200 乖離）、ATR、出来高系等を想定した定数と calc_momentum のインタフェースを整備。DuckDB 接続を受け取り SQL+Python で計算する方針。 (src/kabusys/research/factor_research.py)

- ツール
  - Paper Trading 検証レポート生成スクリプトを追加（python -m kabusys.tools.paper_verification_report）。
    - SQLite（paper_trading DB）から稼働率、注文成功率、送信率、P95 レイテンシ等を集計して PASS/FAIL 判定を出力。
    - CLI で期間フィルタ（--from / --to）と DB 指定（--db）をサポート。データ欠損に対する堅牢な処理を実装。 (src/kabusys/tools/paper_verification_report.py)

### Changed
- （初回リリースのため該当なし）

### Fixed
- .env 読み込み処理
  - export プレフィックス、クォート中のバックスラッシュエスケープ、インラインコメントの扱いなどを正しく処理することで既存の単純なパーサの不具合を回避。 (src/kabusys/config.py)
- ログ設定
  - ログディレクトリ/ファイル作成失敗時にプロセスがクラッシュしないようフォールバックを実装。 (src/kabusys/utils/logging_setup.py)

### Security
- .env ファイルに関する注意を README/ウィザードのメッセージで明示（.env を絶対に Git にコミットしない旨）。 (src/kabusys/config_setup.py)

### Notes / その他
- run_monitoring は監視用 DB 初期化（init_monitoring_db）および duckdb 接続を行う実装となっているため、監視用スキーマの初期化が行われることに注意。 (src/kabusys/run_monitoring.py, src/kabusys/monitoring/monitoring_db.py (参照))
- run_execution は paper_trading モード時にデータベースを分離することでテスト用の影響を本番 DB に及ぼさない設計。 (src/kabusys/run_execution.py)
- process_priority / cpu_affinity の呼び出しは権限による失敗を警告してスキップするため、コンテナやシステム権限の低い環境でも安全に起動可能。 (src/kabusys/utils/process_priority.py)
- validate_config の YAML 検証は PyYAML がインストールされている場合に有効化される。インストールされていない場合は警告を出して YAML 検証をスキップする。

### Breaking Changes
- 初回リリースのためなし。

---

今後の予定（例）
- ファクター計算モジュールの完全実装（momentum の SQL 実装等）
- ExecutionEngine / BrokerClient の詳細実装と統合テスト
- tests ディレクトリの追加と CI 設定
- strategy / data モジュールの充実化

（以上）