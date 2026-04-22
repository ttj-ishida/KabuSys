CHANGELOG
=========

すべての注目すべき変更点を記録します。フォーマットは "Keep a Changelog" に準拠しています。

[Unreleased]
------------

- なし

0.1.0 - 2026-04-22
------------------

Added
- 基本アプリケーション構成と初期機能を追加。
  - パッケージバージョンを 0.1.0 に設定（src/kabusys/__init__.py）。
- 実行・監視プロセス起動スクリプトを追加。
  - ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）
    - KABUSYS_ENV が paper_trading の場合は paper_trading 用の専用 SQLite（data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成と、OrderRepository/OrderManager/RiskManager/Reconciler 等の組み立て。
    - エンジンを別スレッドで起動し、data/stop_requested.flag による外部停止制御と実行中 PID 管理（data/execution.pid）に対応。
  - SystemMonitor 起動スクリプト（src/kabusys/run_monitoring.py）
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）。
    - 監視は環境に関わらず本番 sqlite_path を使用する（監視データの中央化）。
    - 起動時にプロセス優先度を高に設定し、停止フラグ検知でループ終了。
- 設定管理機能を追加。
  - Settings クラスで環境変数を型/値チェック付きでラップ（src/kabusys/config.py）。
    - .env 自動読み込み（プロジェクトルート検出）と .env/.env.local の読み込み順、OS 環境変数保護対応。
    - 各種プロパティ（DB パス、PAPER_FILL_MODE のバリデーション、閾値設定、env/log_level 判定など）。
    - settings インスタンスをエクスポート。
  - 対話式環境設定ウィザード（.env 生成）を追加（src/kabusys/config_setup.py）。
    - 入力項目定義、既存 .env 読込、秘密値マスク、保存確認、.env ファイル書き込み。
  - 設定検証 CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリチェック、config/*.yaml の存在と YAML パースチェック（PyYAML 未インストール時は警告）。
    - --strict モードで警告を fail 扱いにできる。
- ロギングとプロセス制御ユーティリティを追加（src/kabusys/utils）。
  - 統一ログ設定ユーティリティ（src/kabusys/utils/logging_setup.py）
    - stdout StreamHandler と 日次ローテートファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。
    - LOG_DIR/LOG_LEVEL の解決順、ログディレクトリ作成失敗時のフォールバック（コンソールのみ）対応。
  - プロセス優先度 / CPU affinity 設定（src/kabusys/utils/process_priority.py）
    - Windows/Linux(Mac/FreeBSD 含む) の差分吸収、psutil を使用した優先度設定（high/normal/low）と CPU affinity 固定。
    - 権限不足や未対応環境での安全なフォールバック（警告出力）。
- ポートフォリオ構築関連の純粋関数群を追加（src/kabusys/portfolio）。
  - 候補選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates（スコア降順で上位 N を選択）
    - calc_equal_weights / calc_score_weights（スコアが全て 0 の場合はフォールバックして等配分）
  - セクター上限適用 / レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap（既存ポジションを考慮したセクター集中防止フィルタ）
    - calc_regime_multiplier（"bull"/"neutral"/"bear" に基づく乗数。未知レジームは警告後 1.0 でフォールバック）
  - 株数決定・丸め・上限スケーリング（src/kabusys/portfolio/position_sizing.py）
    - allocation_method: "risk_based" / "equal" / "score" に対応
    - lot_size（単元株）単位での丸め、per-position 上限、aggregate cap（available_cash を超える場合のスケールダウン）と再配分ロジック、cost_buffer（コスト見積り）考慮。
  - portfolio パッケージのエクスポートを用意（src/kabusys/portfolio/__init__.py）。
- Paper Trading 検証レポート生成ツールを追加（src/kabusys/tools/paper_verification_report.py）
  - SQLite（paper_trading DB）から稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）等を集計し PASS/FAIL 判定を出力。
  - デフォルト閾値を定義（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）。
  - --from/--to/--db コマンドラインオプションをサポート。
- DuckDB を分析用に利用する設計を導入（複数スクリプトで duckdb.connect を使用）。

Changed
- なし（初期リリースのため新規追加中心）。

Fixed
- なし（初リリース）。

Deprecated
- なし。

Removed
- なし。

Security
- なし。

Known issues / Notes
- src/kabusys/research/factor_research.py の実装はモジュール設計および定数定義、関数 docstring 等が含まれており、モメンタム算出の calc_momentum を実装開始しているもののソースが途中で切れている箇所があり（ファイル末尾の未完了コード断片）完全実装ではありません。利用時は注意してください。
- 一部のファイルは外部ライブラリ（psutil, duckdb, PyYAML 等）に依存します。CI / 実行環境にこれらが存在することを確認してください。
- .env ファイルは機密情報を含むため Git にコミットしないでください（config_setup.py のヘッダにも注意喚起あり）。

----- 

このリリースは、KabuSys のコア機能（設定管理、起動スクリプト、ログ管理、プロセス制御、ポートフォリオ構築、Paper Trading 検証ツール）を整備するための初期リリースです。今後は research モジュールの完成、監視/実行の堅牢化、テスト・ドキュメントの拡充を予定しています。