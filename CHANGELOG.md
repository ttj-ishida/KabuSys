# Changelog

すべての重要な変更点をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

- このリポジトリは初回公開バージョンとして 0.1.0 を記録しています。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-04-17

### Added
- 基本アプリケーション構成
  - パッケージ初期版を追加（kabusys/__init__.py, バージョン 0.1.0）。
- 環境設定・管理
  - Settings クラスを追加（src/kabusys/config.py）。
    - .env ファイルおよび環境変数から設定を自動読み込み（プロジェクトルートを .git または pyproject.toml から検出）。
    - 必須変数の取得ヘルパー、各種パス（DUCKDB_PATH、SQLITE_PATH、PAPER_TRADING_SQLITE_PATH など）や閾値（CPU/MEM/DISK）をプロパティで提供。
    - PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL 等の値検証を実装。
  - 対話式設定ウィザードを追加（src/kabusys/config_setup.py）。
    - .env の初期作成・更新を対話的に行うCLIを提供。シークレットマスク表示、選択肢、デフォルト値のサポート。
- 設定検証ツール
  - validate_config CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数、KABUSYS_ENV 値、ログレベル、DB パス、config/*.yaml の存在とパース（PyYAMLがある場合）などを検証。
    - --strict オプションで警告を失敗扱いにできる。
- 実行・監視用エントリポイント
  - ExecutionEngine 起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading の場合は専用の paper SQLite DB を使用して本番 DB から分離。
    - BrokerClientFactory を使ったブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler 組み立て、実行スレッド起動、停止フラグ監視、PID ファイル管理。
  - SystemMonitor ポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。無効値はデフォルト 60 秒にフォールバックして警告出力。
    - 監視は環境にかかわらず本番の sqlite_path を使用する実装。
    - 停止フラグファイルに応じた安全な終了処理を実装。
- Paper Trading 検証ツール
  - paper_verification_report を追加（src/kabusys/tools/paper_verification_report.py）。
    - ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH）からシステム安定性、注文成功率、送信率、レイテンシ等を集計しレポート出力。
    - P95 計算、各種閾値（稼働率、成功率、送信率、P95 レイテンシ）による PASS/FAIL 判定。
- ポートフォリオ構成ロジック（純粋関数群）
  - portfolio_builder（src/kabusys/portfolio/portfolio_builder.py）
    - 候補選定（select_candidates）、等配分・スコア加重（calc_equal_weights / calc_score_weights）。
  - risk_adjustment（src/kabusys/portfolio/risk_adjustment.py）
    - セクター集中制限の適用（apply_sector_cap）、市場レジームに応じた資金乗数（calc_regime_multiplier）。
  - position_sizing（src/kabusys/portfolio/position_sizing.py）
    - allocation_method（"risk_based", "equal", "score"）に基づく株数計算。
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap（available_cash 超過時のスケールダウン）、cost_buffer を考慮した安全なスケーリングアルゴリズムを実装。
- 研究向けファクタ計算
  - research/factor_research（src/kabusys/research/factor_research.py）
    - DuckDB 接続を利用したモメンタム・ボラティリティ等のファクタ計算（mom_1m/mom_3m/mom_6m、ma200_dev、atr_20、avg_turnover 等）。データ不足時の None 処理。
- プロセス制御ユーティリティ
  - process_priority（src/kabusys/utils/process_priority.py）
    - Windows / POSIX を吸収する set_process_priority(level) を提供（"high" / "normal" / "low"）。
    - CPU affinity 設定 set_cpu_affinity(cpu_count) を追加。
    - 権限不足や未対応 OS に対しては警告出力して安全にフォールバック。

### Changed
- （初回リリース）パッケージの骨格として上記機能をまとめて提供。

### Fixed
- 環境変数パーサの改善（src/kabusys/config.py）
  - .env パーサで以下に対応：
    - export KEY=val 形式のサポート
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - クォートなし値内のインラインコメント処理（直前がスペース/タブの場合のみ）
  - .env 自動読み込みはプロジェクトルートの探索に基づき、CWD に依存しない動作。
  - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を追加（テスト等で使用）。
- MONITOR_POLL_INTERVAL の不正値ハンドリング（src/kabusys/run_monitoring.py）
  - 0 以下や数値以外を検出した場合に警告を出しデフォルトにフォールバック（time.sleep に渡す不正値を回避）。
- Process priority / CPU affinity の例外処理を強化（権限不足・未実装メソッドの安全ハンドリング）。
- Paper verification report 内で DB テーブルが存在しない場合に sqlite3.OperationalError をハンドリングして堅牢化。

### Security
- .env ファイルは生成時に README コメントとして「絶対に Git にコミットしないこと」を明記（config_setup の出力）。機密値はウィザードでマスク表示。

### Notes / Implementation details
- 実行スクリプト（run_execution, run_monitoring）は stop flag（data/stop_requested.flag）を監視して安全にシャットダウンする設計。
- paper_trading 環境は本番 DB と完全に分離されるよう paper_sqlite_path を使用。
- 多くの関数は副作用を持たない純粋関数（ポートフォリオ関連）として設計され、単体テストが容易な構造になっている。
- DuckDB は研究・集計用途に用いられ、prices_daily / raw_financials 等のテーブルを前提とする。

---

この CHANGELOG はコードベースの現状から推測して作成しています。リリースに含める文言や日付は適宜調整してください。