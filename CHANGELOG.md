# Changelog

すべての注目すべき変更はこのファイルに記載します。  
このプロジェクトは Keep a Changelog のガイドラインに沿って管理しています。

## [0.1.0] - 2026-04-18

初回リリース。以下の機能群を実装しました。

### Added
- コアアプリケーション
  - パッケージ名: `kabusys`（__version__ = 0.1.0）
  - 実行スクリプト:
    - `run_execution.py` — ExecutionEngine 起動スクリプト（プロセス優先度設定、スレッドでのエンジン実行、停止フラグ監視、PID 管理）。
    - `run_monitoring.py` — SystemMonitor ポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL 環境変数で間隔設定、停止フラグ検知、例外耐性あり）。
  - 設定関連:
    - `config.py` — 環境変数 / .env の読み込み・パースと `Settings` クラスを提供。自動 .env ロード（プロジェクトルート検出）をサポートし、無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` を提供。
    - `config_setup.py` — 対話式ウィザードで .env を作成・更新する CLI。
    - `validate_config.py` — 起動前の設定検証 CLI（必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パスや config/*.yaml の存在チェック、`--strict` オプション）。
- トレード実行関連
  - Execution コンポーネント群（ファクトリ/エンジン/OrderManager/OrderRepository/Reconciler/RiskManager）への組み立て・起動フローを実装（run_execution で使用）。
  - Paper Trading（`KABUSYS_ENV=paper_trading`）時は専用 SQLite（既定: `data/paper_trading.db`）を使用し、本番 DB と分離して動作する設計。
  - Paper Trade 挙動制御: `paper_fill_mode` の取得と検証（有効値: "instant" | "partial" | "never" | "reject"）。
- ポートフォリオ構築（純粋関数群）
  - `portfolio_builder.py`
    - select_candidates（スコア降順選定、タイブレークに signal_rank を使用）
    - calc_equal_weights（等金額）
    - calc_score_weights（スコア重みによる配分、全スコアが 0 の場合は等金額にフォールバック）
  - `risk_adjustment.py`
    - apply_sector_cap（セクター集中上限の適用、売却予定銘柄の除外、"unknown" セクターは除外対象外）
    - calc_regime_multiplier（市場レジームに応じた投下資金乗数、未知レジームは WARNING と共に 1.0 でフォールバック）
  - `position_sizing.py`
    - calc_position_sizes（risk_based / equal / score の割当方式をサポート、損切り・ロット丸め・aggregate cap スケーリング・cost_buffer を考慮）
- リサーチ / ファクター計算
  - `research/factor_research.py`（DuckDB を使ったファクター計算設計。モメンタム / MA200 / ATR / 流動性等の計算を行う方針で実装中／相談用の関数群を含む）
- ツール
  - `tools/paper_verification_report.py` — Paper Trading 検証レポート生成。指定期間の稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）を集計し PASS/FAIL を判定（閾値定義あり）。
- 監視・DB
  - `monitoring_db` 初期化呼び出し（run_execution/run_monitoring の起動時に監視テーブルの存在を保証する冪等初期化を行う）。
- ユーティリティ
  - `utils/logging_setup.py` — 統一的ログ設定ユーティリティ（stdout StreamHandler + 日次ローテートの TimedRotatingFileHandler、LOG_DIR/LOG_LEVEL 解決、既存ハンドラのクリア、ファイルハンドラ作成失敗時のフォールバック）。
  - `utils/process_priority.py` — クロスプラットフォームのプロセス優先度設定（Windows/Linux/Mac を考慮）、CPU affinity 設定ユーティリティ。psutil を利用し、権限不足等は警告でスキップ。

### Changed
- 設計上の分離
  - Paper Trading と Live の DB/クライアント分離を明確化（paper_trading 用の Mock クライアントと専用 SQLite を利用することで本番 DB への影響を避ける設計）。
- ログ出力
  - ログは stdout に出力されるように設定（cron/Task Scheduler での運用を考慮）。ファイル出力はデフォルト `logs/<app_name>.log`、日次ローテーション・30日分保持。

### Fixed / Improved
- .env パーサの強化（`config.py`）
  - `export KEY=val` 形式のサポート、シングル／ダブルクォート内でのバックスラッシュエスケープ対応、インラインコメントの取り扱い（クォートあり/なしでの違いを適切に処理）。
  - .env 読み込み時の上書きルール: OS 環境変数を保護する protected オプションを導入（.env.local は override=True で上書き可能だが OS 環境変数は保持）。
- 設定検証の充実（`validate_config.py`）
  - 必須環境変数の存在チェック、プレースホルダ値検出、KABUSYS_ENV と LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml のパースチェック（PyYAML 未インストール時は警告）。
- 実行時安全装置
  - 停止フラグ（data/stop_requested.flag）を用いた安全停止、run_execution/run_monitoring 共にこのフラグを監視してグレースフルに終了するように実装。
  - `KILL_FLAG_CLEAR_ON_START` による Kill Switch 自動クリアの設定を提供（本番ではデフォルト 0 を推奨）。

### Security
- シークレット管理
  - `config_setup.py` のウィザードでシークレット項目（J-Quants トークンや KABU API パスワード）をマスク表示。`.env` は絶対に Git にコミットしないことをドキュメント化。

### Known issues / TODO
- `position_sizing.calc_position_sizes` で price が欠損（0.0）の場合、現状はスキップしてしまいエクスポージャーが過少見積りされる旨を TODO コメントで記載。将来的に前日終値や取得原価等のフォールバックを検討。
- `research/factor_research.py` ファイル末尾が未完の状態（モメンタム計算関数の続きや他ファクターの完全実装は今後追加予定）。
- 外部依存: `psutil`, `duckdb`, （オプション）`PyYAML` が必要。PyYAML がない場合は YAML 検証はスキップされるが警告が出る。

---

（注記）リリース日やバージョンはコードから推測して設定しています。実際のリリースフローに合わせて日付／バージョンは調整してください。