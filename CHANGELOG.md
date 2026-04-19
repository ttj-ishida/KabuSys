CHANGELOG
=========

このファイルは「Keep a Changelog」の形式に準拠しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

全般
----
- 本リリースはコードベースから推測して作成した変更履歴です。実際のコミット履歴ではなく、ソース内容（追加されたモジュール・機能・振る舞い・安全対策など）に基づいてまとめています。

[0.1.0] - 2026-04-19
--------------------

Added
- 基本機能の追加（初期リリース想定）
  - 実行・監視の起動スクリプトを追加
    - run_execution.py: ExecutionEngine を起動する CLI スクリプト（スレッド実行、停止フラグ & PID ファイル管理、Paper Trading 用 DB 分離）。
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト（環境変数 MONITOR_POLL_INTERVAL による間隔上書き、停止フラグ検出）。
  - 設定・環境処理
    - config.py: .env 自動ロード（プロジェクトルート検出）、.env のパースロジック（export対応、クォート/エスケープ/インラインコメント処理）、Settings クラスによる型付き/検証済み設定アクセス。
    - config_setup.py: 対話式ウィザードで .env を作成・更新する CLI。
    - validate_config.py: 起動前の設定検証 CLI（--strict オプションで警告を失敗と扱う）。必須変数チェック・YAML ファイル存在/パースチェック・本番環境向けガードを実装。
  - ポートフォリオ構築ライブラリ（純粋関数群）
    - portfolio.portfolio_builder: 候補選定と重み（等金額・スコア加重）。
    - portfolio.risk_adjustment: セクター集中制限（apply_sector_cap）、市場レジームに応じた乗数（calc_regime_multiplier）。
    - portfolio.position_sizing: 発注株数計算（risk_based / equal / score、単元株丸め、aggregate cap のスケールダウンと再配分ロジック）。
  - ユーティリティ
    - utils/logging_setup.py: 統一ログ設定（コンソール stdout + 日次ローテーションファイル、ログディレクトリ自動作成・失敗時のフォールバック）。
    - utils/process_priority.py: クロスプラットフォームのプロセス優先度/nice/cpu affinity 設定（Windows / POSIX 対応、権限不足時の安全なフォールバック）。
  - ツール
    - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプト（DB から稼働率・注文成功率・レイテンシ等を集計して PASS/FAIL 判定）。CLI 引数 --from/--to/--db をサポート。
  - データベース連携
    - DuckDB と SQLite の両対応（duckdb 接続と sqlite3 接続を利用）。監視用テーブル初期化関数 init_monitoring_db を起動フローで呼び出してテーブル存在を保証。

Changed
- ログと運用に関する設計
  - 全スクリプトは setup_logging() を呼び出して統一的なログ出力を行うように変更（コンソールを stdout にし、ファイルは日次ローテーション）。
  - run_execution / run_monitoring は起動時にプロセス優先度を "high" にセットするように設定（set_process_priority を使用）。
  - Paper Trading の DB は本番 DB と分離（PAPER_TRADING_SQLITE_PATH を使うか settings.is_paper により切り替え）。

Fixed / Robustness improvements
- .env 読み込みの堅牢化
  - export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント取り扱い、空行/コメント行スキップに対応。
  - プロジェクトルート検出は .git または pyproject.toml を基準にしており、CWD に依存しない実装。
  - 自動 .env ロードを KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能（テスト用）。
- ログ出力のフォールバック
  - ログディレクトリ作成に失敗した場合でもコンソール出力を維持し、ファイルハンドラ作成失敗時は警告を出して継続する。
- 環境変数の検証強化
  - Settings クラス内で KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE 等の検証を行い、不正値は例外を発生させる。
  - validate_config で必須環境変数のプレースホルダ値チェック、本番環境向けの警告（LINE 設定未指定や Kill Switch の注意喚起）を実装。
- 実行時安全策
  - run_execution/run_monitoring はプロセス開始時に停止フラグ（data/stop_requested.flag）をチェックし、既に立っていれば起動を中止・早期終了する。
  - monitoring のポーリング間隔は環境変数 MONITOR_POLL_INTERVAL を受け付けるが、1 未満や非整数など不正な値はデフォルト 60 秒にフォールバックして警告を出す（time.sleep の ValueError を防止）。
  - init_monitoring_db() を実行時に呼び出して監視用テーブルの存在を冪等に保証。
- ポートフォリオ/リスクロジックの安全対策
  - calc_score_weights: 全スコア合計が 0.0 の場合は警告を出して等金額配分にフォールバック。
  - apply_sector_cap: セクターが "unknown" の銘柄はセクター上限の対象外として扱う（除外されない）。
  - calc_regime_multiplier: 未知のレジーム値は警告を出して 1.0 にフォールバック。
  - calc_position_sizes:
    - 単元株（lot_size）単位での丸め処理を導入。
    - 全銘柄合計コストが利用可能現金を超える場合はスケールダウンし、端数（fractional remainder）順に単位ロットを追加配分する再配分ロジックを実装して利用可能資金を有効活用。
    - 価格欠損（None/<=0）の銘柄はスキップしてデバッグログを出力。
- process_priority / cpu affinity
  - Windows・POSIX の差を吸収する実装。権限不足や非対応 OS 時には警告を出して処理をスキップする安全な設計。

Documentation / CLI usability
- config_setup: 対話式ウィザードで既存 .env を読み込み、シークレットはマスクして表示。保存前にまとめて確認を行い、--env-file で出力先指定可能。
- validate_config: 結果を INFO/WARNING/ERROR で表示し、--strict で警告を失敗扱いにできる。
- paper_verification_report: レポートに P95 レイテンシ、稼働率、成功率、送信率、リスク却下数を含め PASS/FAIL を判定するしきい値を定義（稼働率 99%、成立率 90%、送信率 95%、P95 200ms）。

Notes / Known limitations
- research/factor_research.py はファクター計算用のモジュールとして設計され、モメンタム等の定義や定数が含まれますが、ファイル末尾が途中で切れている（実装継続が示唆される）。完全実装は今後の作業が必要です。
- 一部の TODO コメント（例: position_sizing の銘柄ごとの lot_size 管理や price のフォールバック）に示される拡張ポイントが残っています。
- Paper Trading の振る舞い（MockBrokerClient の実装詳細、fill_mode の挙動）は実装ファイル群に依存するため、本 changelog は起動スクリプトの記述や設定から推測した範囲に留まります。

セキュリティ
- 本リリースで特記すべきセキュリティ修正はソース内に明示されていません。機密トークンは .env に保存する設計のため、.env を Git へコミットしない運用上の注意が README 等で明示される必要があります（config_setup のヘッダにも明示あり）。

Deprecated
- なし（初期リリース想定）。

Removed
- なし（初期リリース想定）。

Security
- なし（ソースのみからの推測）。