# Changelog

すべての変更は Keep a Changelog の形式に従って記載しています。  
このプロジェクトはセマンティックバージョニング (http://semver.org/) を採用しています。

## [0.1.0] - 2026-04-18

### 追加 (Added)
- 実行スクリプト: 起動用スクリプトを追加・整備
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止制御はプロジェクト内 `data/stop_requested.flag` により行う。
    - 起動時にプロセス優先度を "high" に設定。
    - monitoring 用 DB 初期化 (`init_monitoring_db`) と DuckDB 接続を行う（Monitoring は環境にかかわらず本番 `sqlite_path` を使用する設計）。
    - エラー発生時は例外ログを記録し次のポーリングまで待機、KeyboardInterrupt を捕捉して正常終了する。

  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合、MockBrokerClient（BrokerClientFactory により生成）を使用し、Paper Trading 用 SQLite（`data/paper_trading.db`）に記録して本番 DB と分離。
    - 起動時にプロセス優先度を "high" に設定、PID ファイル管理、停止フラグ検出による安全停止処理を実装。
    - ExecutionEngine をデーモンスレッドで実行し、停止フラグ検出で engine.stop() を呼び出して安全終了する。

- 設定管理・対話式ウィザード・検証ツール
  - config.py
    - プロジェクトルート自動検出（.git / pyproject.toml）に基づく `.env` 自動読み込みを実装（環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。
    - `.env` パーサーを強化（`export` プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱いなど）。
    - 環境設定をラップする `Settings` クラスを提供。多くのプロパティで入力値検証を実施（`KABUSYS_ENV`、`LOG_LEVEL`、`PAPER_FILL_MODE` 等）。
    - Paper Trading 用 DB パス (`paper_sqlite_path`)、監視閾値（CPU/MEM/DISK）や PID / kill flag 関連設定をプロパティとして提供。

  - config_setup.py
    - 対話式 `.env` ウィザードを追加。シークレット入力、選択肢、既存値の再利用、ファイル保存をサポート。テンプレートヘッダ付きの `.env` を生成。

  - validate_config.py
    - 起動前チェック用 CLI を追加。必須環境変数確認、`KABUSYS_ENV` / `LOG_LEVEL` の妥当性チェック、DB パスの親ディレクトリ存在確認、`config/*.yaml` の存在と PyYAML があればパース検証を実施。
    - `--strict` オプションで警告を FAIL 扱いにできる。
    - 本番環境（`KABUSYS_ENV=live`）向けの追加ガード（LINE 通知設定確認、`KILL_FLAG_CLEAR_ON_START` に関する警告）を実装。

- 運用ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率（Filled/Created）、送信率、リスク却下数、API レイテンシ（平均/最大/P95）を解析・出力。
    - 判定基準（しきい値）を定義し PASS/FAIL を判定する（デフォルトのしきい値をコード内に定義）。

- ポートフォリオ構築関連モジュール（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナルの候補選定（スコア降順、タイブレークは signal_rank）`select_candidates`。
    - 等配分・スコア加重の重み計算 `calc_equal_weights`, `calc_score_weights`（スコア合計が 0 の場合は等配分にフォールバック）。

  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する `apply_sector_cap`。既存ポジションのセクター別時価を計算して上限超過セクターの新規候補を除外。
    - 市場レジームに応じた投下資金乗数 `calc_regime_multiplier`（"bull"/"neutral"/"bear" をマップ、未知レジームは 1.0 にフォールバック）。

  - portfolio/position_sizing.py
    - 各銘柄の発注株数計算 `calc_position_sizes` を実装。
    - allocation_method として "risk_based" / "equal" / "score" をサポート。損切り率、リスク率、最大ポジション比率、利用可能現金に基づく算出。
    - 単元株（lot_size）丸め、aggregate cap によるスケーリング、余剰キャッシュに対する再配分ロジックを実装。
    - cost_buffer による保守的なコスト見積り考慮。

- ユーティリティ
  - utils/logging_setup.py
    - 統一ログ設定ユーティリティを追加。コンソール（stdout）と日次ローテーション（TimedRotatingFileHandler）をルートロガーに設定。既存ハンドラの二重設定防止、ログディレクトリ作成失敗時のフォールバック対応などを実装。

  - utils/process_priority.py
    - クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定 `set_process_priority`、CPU affinity 固定 `set_cpu_affinity` を追加。psutil を利用しアクセス権限不足等の例外は警告ログでスキップ。

- パッケージ初期設定
  - src/kabusys/__init__.py にバージョン `0.1.0` を設定。

### 変更 (Changed)
- 監視サブシステムの DB 接続方針を明確化
  - run_monitoring が環境 (`KABUSYS_ENV`) に依存せず、本番用 `sqlite_path` を使用する方針を採用（Monitoring データは環境に依存しない単一 DB を想定）。

- .env 自動読み込みの挙動
  - 自動読み込みの優先順位を OS 環境変数 > .env.local > .env と明記し、OS 環境変数は保護（上書き禁止）する実装に変更。

### 修正 (Fixed)
- .env パーサーの堅牢化
  - export プレフィックス、クォート内のエスケープ、インラインコメントの扱いなどを正しく処理するよう修正。

- ログハンドラ管理
  - setup_logging で既存ルートハンドラを安全に flush/close/削除してから再設定することで、複数回初期化時の二重出力を防止。

### 既知の問題 (Known Issues)
- research/factor_research.py の実装が途中で切れている（calc_momentum の実装冒頭が未完）。ファクター計算モジュールの一部が未完成のため、DuckDB を使ったファクター算出の完全実装は今後の作業が必要。
- position_sizing, risk_adjustment 内に記載された TODO（価格欠損時のフォールバックや銘柄別 lot_size 拡張）が残っている。
- 一部外部ライブラリ（psutil, duckdb, PyYAML 等）に依存。これらが環境に存在しない場合は関連機能が制限されます（validate_config は PyYAML がない場合は YAML 検証をスキップする等のフォールバックあり）。

### ドキュメント / 補足 (Notes)
- config_setup による .env 生成後は `python -m kabusys.validate_config` による検証を推奨。
- Paper Trading 検証レポートはデフォルトで `data/paper_trading.db` を参照する。別ファイルを使う場合は環境変数 `PAPER_TRADING_SQLITE_PATH` か `--db` オプションで指定可能。
- 監視ループ・エンジン起動の停止はプロジェクトルートの `data/stop_requested.flag` により統制されます。起動時に存在する場合は起動を行わない挙動になっています。

---
この CHANGELOG はソースコードから推測して作成しています。実際の変更履歴やリリースノートが別途存在する場合は、そちらを優先してください。必要であれば各変更項目についてより詳細な説明（影響範囲、設定例、運用手順）を追記します。