# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。

## [0.1.0] - 2026-04-21

初回リリース。KabuSys の基本的なランタイム、設定管理、検証、監視、実行、ポートフォリオ構築、ユーティリティ類、および Paper Trading 検証ツールを追加しました。

### 追加 (Added)
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として追加（src/kabusys/__init__.py）。

- 起動スクリプト
  - 実行エンジン起動スクリプト `run_execution.py` を追加。プロセス優先度設定、SQLite/DuckDB 接続、ブローカークライアント生成（paper_trading 時は Mock を利用して専用 DB に記録）、注文管理・リスク管理・Reconciler 組み立て、スレッドでのセッション実行と停止フラグ検出を行う（src/kabusys/run_execution.py）。
  - 監視ループ起動スクリプト `run_monitoring.py` を追加。プロセス優先度設定、監視 DB 初期化、SystemMonitor の周期チェック、MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔上書き、停止フラグ検出処理を実装（src/kabusys/run_monitoring.py）。

- 設定および環境読み込み
  - Settings クラスで環境変数ベースの設定管理を実装。プロパティ経由で各種設定（DB パス、API トークン、監視しきい値、環境判定フラグ等）を取得可能（src/kabusys/config.py）。
  - 自動 .env ロード機能を追加（プロジェクトルート検出：.git または pyproject.toml を基準）。`.env` と `.env.local` の読み込み順・上書きポリシー、OS 環境変数保護、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート（src/kabusys/config.py）。
  - .env の行パーサを実装し、`export KEY=val` 形式、クォート内エスケープ、行内コメントの扱いなどに対応（src/kabusys/config.py）。

- 設定支援 CLI
  - 対話式の環境設定ウィザード `config_setup.py` を追加。`.env` の新規作成・更新を支援し、秘密項目はマスク表示、デフォルト・選択肢対応、保存確認などを実装（src/kabusys/config_setup.py）。
  - 設定検証 CLI `validate_config.py` を追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性検証、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と（PyYAML があれば）パース検証、KABUSYS_ENV=live の追加ガードを行い、--strict モードで警告を失敗扱いにできる（src/kabusys/validate_config.py）。

- ロギング・プロセス制御ユーティリティ
  - ロギング初期化ユーティリティ `setup_logging()` を追加。コンソール出力（stdout）と日次ローテーションファイル出力（TimedRotatingFileHandler）をルートロガーに設定、ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続（src/kabusys/utils/logging_setup.py）。
  - プロセス優先度・CPU affinity 設定ユーティリティを追加（`set_process_priority`, `set_cpu_affinity`）。Windows/Linux/macOS 等の差分を吸収し、権限不足や未対応プラットフォーム時は警告を出してスキップ（src/kabusys/utils/process_priority.py）。

- ポートフォリオ構築モジュール
  - 候補選定・重み計算モジュール（`portfolio_builder.py`）を追加：
    - select_candidates: スコア降順、同点時は signal_rank によるタイブレークで上位 N を選定。
    - calc_equal_weights / calc_score_weights: 等金額配分、スコア比率配分（全スコアが 0 の場合は等分にフォールバック）を実装。
  - セクター集中・レジーム乗数（`risk_adjustment.py`）を追加：
    - apply_sector_cap: 既存保有のセクター別エクスポージャを計算し、上限超過セクターの候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear、未知レジームは警告と 1.0 フォールバック）。
  - ポジションサイジング（`position_sizing.py`）を追加：
    - risk_based / equal / score の配分方式、単元株（lot_size）丸め、1銘柄上限・aggregate cap（available_cash を超える場合のスケーリングと端数の再配分）、cost_buffer による保守的コスト見積りを実装。

- Paper Trading 関連ツール
  - Paper Trading 検証レポート生成スクリプト `tools/paper_verification_report.py` を追加。SQLite（デフォルト: data/paper_trading.db）から指標（稼働率、注文成功率、送信率、P95 レイテンシ等）を集計してレポート出力。閾値による PASS/FAIL 判定を行う。P95 計算ユーティリティ、日付フィルタ対応、コマンドライン引数（--from/--to/--db）対応を実装。

- Research（骨組み）
  - ファクター計算モジュール（`research/factor_research.py`）のスケルトンを追加。DuckDB 経由での Momentum / Value / Volatility / Liquidity 計算方針を記載し、calc_momentum のインターフェースを作成（実装は一部）。

- DB 初期化
  - 監視用 DB 初期化ユーティリティ（init_monitoring_db）を各起動スクリプトから呼ぶことでテーブル存在保証（冪等）を行う箇所を追加（複数スクリプトで使用）。

### 変更 (Changed)
- ロギング既定動作
  - stdout を StreamHandler に使う方針を明確化（stderr ではなく stdout を利用）。これは Task Scheduler / cron 等で stdout/stderr をまとめてリダイレクトする運用を想定（src/kabusys/utils/logging_setup.py）。

- DB の扱い
  - 監視プロセスは KABUSYS_ENV にかかわらず監視用の sqlite_path（デフォルト: data/monitoring.db）を使用するように明記（src/kabusys/run_monitoring.py）。
  - 実行エンジンは paper_trading 環境であれば paper_sqlite_path（デフォルト: data/paper_trading.db）を使用することで本番 DB と分離（src/kabusys/run_execution.py）。

### 修正 / 安全策 (Fixed / Security)
- 環境変数読み込みの安全化
  - 自動 .env ロード時に OS 環境変数を保護するため、既存の OS 環境変数キーは上書き対象から除外（protected 機構の導入）。また KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化を実装（src/kabusys/config.py）。
  - .env パーサで不正な行やコメント、クォート内のエスケープを安全に扱うように実装（src/kabusys/config.py）。

- ポーリング間隔の堅牢化
  - MONITOR_POLL_INTERVAL が不正な値（非数値・0 以下等）の場合にデフォルト（60 秒）へフォールバックし、警告ログを出すように実装（src/kabusys/run_monitoring.py）。

- 実行中停止対応の堅牢化
  - 停止フラグ（data/stop_requested.flag）を監視して安全にループ/スレッドを止める処理を各スクリプトに実装（run_monitoring, run_execution）。PID ファイル管理・タイムアウト join 等で暴走を防止（src/kabusys/run_execution.py, src/kabusys/run_monitoring.py）。

- 権限・未対応環境時のフォールバック
  - process priority / CPU affinity 設定は権限不足や未対応 OS の場合に警告を出してスキップ（src/kabusys/utils/process_priority.py）。
  - ログディレクトリ作成やファイルハンドラ生成が失敗した場合は、コンソール出力のみで継続するフォールバックを実装（src/kabusys/utils/logging_setup.py）。

### 既知の制限 / 注意点 (Known issues / Notes)
- research/factor_research.py の calc_momentum はファイル末尾で途中（スニペットが切れている）で、実装が未完の箇所があります。今後のリリースで完成予定。
- position_sizing の注釈で、価格欠損時のフォールバック（前日終値など）を将来的に追加する旨をコメントで示しています（現状は価格が欠落すると対象から除外される）。
- config_setup が生成する .env ファイルは機密情報を含むため、絶対に Git 等にコミットしないよう注意喚起を記載（.env ヘッダに警告を付与）。

### マイグレーション / 操作上の注意 (Migration / Upgrade notes)
- 初回セットアップ手順（推奨）
  1. `.env` を作成: `python -m kabusys.config_setup`
  2. 設定を検証: `python -m kabusys.validate_config`
  3. Paper Trading の検証には: `python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD`
- 本番（KABUSYS_ENV=live）での運用時には、`KILL_FLAG_CLEAR_ON_START` を `0` にして自動クリアを無効にすることを強く推奨します（validate_config による警告）。

---

今後の予定（未リリース）
- research/factor_research の完全実装（ファクター算出ロジックの完成）。
- 戦略・データ取得・ブローカー連携周りの追加テスト・堅牢化。
- 単体テストおよび CI を整備し、現行のユーティリティ群のカバレッジを向上。