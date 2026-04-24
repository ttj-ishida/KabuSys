CHANGELOG
=========

すべての重要な変更は Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に従って記載しています。

[Unreleased]
-------------

- なし

[0.1.0] - 2026-04-24
-------------------

Added
- 基本パッケージ初期実装を追加。
  - src/kabusys/__init__.py にバージョン情報を追加（__version__ = "0.1.0"）。
- 起動スクリプト／運用用ユーティリティ
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL（デフォルト 60 秒）でポーリング間隔を上書き可能。無効値時はフォールバックして警告を出力。
    - 停止制御用にプロジェクト直下の data/stop_requested.flag を監視して安全にループを抜ける。
    - Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使用。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（デフォルト data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory を利用しブローカークライアントを注入。ExecutionEngine を別スレッドで実行し、停止フラグでシャットダウン可能。
    - 起動時にプロセス優先度を "high" に設定（set_process_priority）。
- 設定管理・検証・ウィザード
  - config.py: Settings クラスを実装し環境変数をラップ。各種設定（DB パス、J-Quants / kabu API、LINE トークン、閾値、PID/kill フラグパス等）をプロパティで取得可能。
    - 自動 .env ロード機能を実装（プロジェクトルートを .git または pyproject.toml で検出）。読み込み順は OS 環境 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
    - .env のパースはクォート文字・エスケープ・export プレフィックス・インラインコメントなど各種ケースに対応。
    - paper_trading 用設定（PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH など）をサポート。
  - config_setup.py: 対話式の .env 作成／更新ウィザードを追加。既存値読み込み・シークレットマスク表示・確認保存機能あり。
  - validate_config.py: 起動前検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、config/*.yaml の存在＆（PyYAML インストール時は）パース検証、KABUSYS_ENV=live のガード（LINE 通知設定・KILL_FLAG_CLEAR_ON_START の警告）などを実装。
    - --strict オプションで警告を失敗扱いにできる。
- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。
    - stdout 出力用 StreamHandler と日次ローテート（TimedRotatingFileHandler、30 日分保持）をルートロガーに設定。
    - ログディレクトリは引数/環境変数 LOG_DIR/デフォルト logs/ の優先解決。ディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py: プロセス優先度と CPU affinity 設定ユーティリティを追加。
    - Windows / POSIX（Linux/Mac/FreeBSD）を吸収した API。set_process_priority("high"|"normal"|"low")、set_cpu_affinity(n) を提供。
    - 権限不足や未対応 OS の場合は警告を出して安全にフォールバック。
- ポートフォリオ構築関連（純粋関数実装）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルのソート／上位抽出機能。
    - calc_equal_weights / calc_score_weights: 等分配・スコア加重配分ロジック（スコア全0 の場合は等分配にフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中制限（既存ポジション計算、売却予定銘柄の除外、"unknown" セクターの扱い等）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に基づく資金乗数。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") に基づく発注株数計算。
    - 単元（lot_size）、max_position_pct、max_utilization、コストバッファ、aggregate cap（スケーリング）や端数処理（lot 単位での再配分）を実装。
- 解析・検証ツール
  - tools/paper_verification_report.py: Paper Trading 検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均/最大/P95）を算出してレポート出力。
    - P95 計算、期間フィルタ (--from/--to)、DB パスの解決（--db / 環境変数 / デフォルト）をサポート。
    - デフォルトの合格基準（稼働率 >= 99%, 成立率 >= 90%, 送信率 >= 95%, P95 レイテンシ <= 200 ms）を設定し PASS/FAIL 判定を表示。
- research/factor_research.py (一部実装)
  - DuckDB 接続を受けてモメンタム等のファクター計算を行う設計を追加（関数 calc_momentum 等の骨格）。※ファイル末尾は一部切れているが設計方針と定数は含まれる。

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Deprecated
- なし

Removed
- なし

Security
- なし

Notes / その他
- 実運用における注意点を README やデプロイ手順に明記することを推奨:
  - .env は絶対にリポジトリへコミットしないこと。
  - KABUSYS_ENV=live の場合は LINE 通知設定や KILL フラグ動作を事前に確認すること。
  - process priority / cpu affinity の設定は権限や OS に依存するため、適切な権限での実行を行うこと。
- 今後の開発アイデア:
  - factor_research の完全実装（DuckDB SQL + Python 計算の完成）。
  - ブローカーモックの振る舞い（PAPER_FILL_MODE）の詳細拡張とテストカバレッジ強化。
  - 銘柄ごとの lot_size 管理や価格フォールバックロジックの強化（risk_adjustment の TODO に依存）。

---