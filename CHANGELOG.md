# CHANGELOG

すべての重要な変更を保守的に記録します。フォーマットは「Keep a Changelog」に準拠しています。

注: 以下の履歴は与えられたコードベースから推測して作成した初期リリース向けの変更履歴です。

## [Unreleased]

- なし

## [0.1.0] - 2026-04-21

初期公開リリース。

### 追加 (Added)

- 基本構成・バージョン
  - パッケージバージョンを 0.1.0 に設定（src/kabusys/__init__.py）。

- 実行用エントリスクリプト
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - プロセス起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用の専用 SQLite（デフォルト data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory 経由でブローカークライアントを生成（paper_trading の場合はモックを想定）。
    - ExecutionEngine を別スレッドで起動し、data/stop_requested.flag により安全に停止可能。
    - エンジン用 PID ファイルを data/execution.pid に出力する設計をサポート。

  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視（monitoring）データベースは環境にかかわらず本番 sqlite_path を使用する仕様。
    - 停止フラグ（data/stop_requested.flag）検出時にループを終了。
    - 例外発生時はログを残して次のポーリングへ回復する設計。

- 設定管理
  - Settings クラス（src/kabusys/config.py）を導入。
    - .env 自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - 自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD により抑止可能。
    - 各種環境変数取得プロパティを提供（J-Quants / kabu API / DB パス / PID/Kill フラグ設定 / 監視門限など）。
    - PAPER_FILL_MODE のバリデーション（"instant", "partial", "never", "reject"）。
    - KABUSYS_ENV のバリデーション（"development", "paper_trading", "live"）。
    - LOG_LEVEL のバリデーション。

  - .env ウィザード CLI（src/kabusys/config_setup.py）を追加。
    - 対話式で .env の初期作成・更新を支援。
    - J-Quants トークンや kabu API パスワードの入力（シークレットマスク）をサポート。
    - 書き込み前に入力内容を確認して保存。

  - 設定検証 CLI（src/kabusys/validate_config.py）を追加。
    - 必須環境変数や KABUSYS_ENV、ログレベル、DB パス、config/*.yaml の存在・パース等を検証。
    - --strict オプションにより警告を FAIL 扱い（exit 1）にできる。
    - PyYAML 未インストール時に YAML 検証をスキップする旨の警告を出力。

- ロギング・プロセスユーティリティ
  - logging_setup: 共通ログ設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、デフォルト 30 日保持）をルートロガーへ設定。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップし、コンソール出力のみで継続。
    - LOG_LEVEL / LOG_DIR の優先解決をサポート。

  - process_priority: プロセス優先度・CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows と POSIX(Linux/Mac/FreeBSD) の差分を吸収して優先度を設定。
    - CPU affinity を最初の N コアに固定する機能を提供。
    - psutil による実装。権限不足等の場合は警告を出してフォールバック。

- ポートフォリオ構築モジュール（src/kabusys/portfolio）
  - portfolio_builder:
    - select_candidates: BUY シグナルのスコア降順選出（signal_rank によるタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重の重み計算（スコアが全て 0 の場合は等分配へフォールバック）。

  - risk_adjustment:
    - apply_sector_cap: セクター集中上限チェック（max_sector_pct）に基づく候補除外ロジック。売却予定銘柄はエクスポージャー計算から除外。
    - calc_regime_multiplier: 市場レジーム ("bull"/"neutral"/"bear") に基づく投下資金乗数を返す（未知レジームは警告とともに 1.0 にフォールバック）。

  - position_sizing:
    - calc_position_sizes: 各銘柄の発注株数計算（allocation_method: "risk_based" / "equal" / "score"）。
    - 単元株丸め（lot_size、デフォルト 100）、per-position 上限、aggregate cap（available_cash）を考慮。
    - cost_buffer による保守的コスト見積りを反映し、投資合計が available_cash を超える場合はスケーリングと残差に基づく追加配分処理を実装。

- リサーチ・ツール
  - tools/paper_verification_report.py:
    - Paper Trading 検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs などの集計から稼働率、注文成功率、送信率、レイテンシ (avg/max/P95) を算出。
    - デフォルト閾値を定義（稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200 ms）。
    - コマンドライン引数で期間指定 (--from, --to) と DB パス指定 (--db) をサポート。

- DB 関連
  - duckdb と sqlite3 を併用する設計を採用。
    - DuckDB は分析（prices_daily 等）や一部リサーチで使用。
    - SQLite は監視・取引ログなどの永続化に使用。ExecutionEngine は paper_trading の場合に専用 SQLite を使用し分離。

### 変更 (Changed)

- なし（初期リリース）

### 修正 (Fixed)

- なし（初期リリース）

### 既知の制約・注意点 (Known issues / Notes)

- research/factor_research.py の実装が途中（ファイル末尾で関数が途中終了している箇所あり）。完全実装は今後のリリース予定。
- position_sizing の価格欠損（price が 0.0）の場合、現在は単純にスキップするだけでエクスポージャーが過少見積りされる可能性がある（TODO コメントあり）。将来的にフォールバック価格の導入を検討。
- process_priority / set_cpu_affinity は権限不足や非対応プラットフォームで例外を出さず警告でフォールバックする。必要に応じて起動環境の権限設定を確認してください。
- logging_setup はログディレクトリ作成に失敗した場合にファイル出力を無効化します。コンテナや一部環境では書き込み権限の確認が必要。

### セキュリティ (Security)

- なし（初期リリース）

---

参照:
- 主要 CLI:
  - python -m kabusys.config_setup    （.env ウィザード）
  - python -m kabusys.validate_config （設定検証）
  - python -m kabusys.run_execution   （ExecutionEngine 起動）
  - python -m kabusys.run_monitoring  （SystemMonitor 起動）
  - python -m kabusys.tools.paper_verification_report （Paper Trading レポート生成）

この CHANGELOG はコードベースから推測して作成しています。追加の変更点やリリース日付の修正があれば更新してください。