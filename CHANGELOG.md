CHANGELOG
=========

すべての変更は Keep a Changelog（https://keepachangelog.com/ja/1.0.0/）の形式に準拠して記載しています。  
記載内容は提供されたコードベースの内容から推測した変更点・機能一覧です。

Unreleased
----------

追加 / 改良
- 環境変数読み込みの強化（kabusys.config）
  - プロジェクトルート検出ロジックを導入して、.env / .env.local を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
  - .env パース処理を強化（export プレフィックス対応、シングル/ダブルクォート内のエスケープ対応、インラインコメント処理）。
  - 環境変数読み込み時に OS 環境変数を保護する protected オプションを採用。

- 対話式環境設定ウィザードの追加（kabusys.config_setup）
  - .env の初期作成／更新を支援する CLI ウィザードを追加。
  - 主要設定項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、LOG_LEVEL 等）を対話的に設定可能。
  - シークレット値のマスク表示、保存前の確認を実装。

- 設定検証ツールの追加（kabusys.validate_config）
  - .env と config/*.yaml の基本チェックを行う CLI を追加。
  - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、YAML のパース検証（PyYAML インストール有無に依存）を実装。
  - --strict オプションで警告を失敗扱いにできる。

- ロギング設定ユーティリティの追加（kabusys.utils.logging_setup）
  - ルートロガーに StreamHandler（stdout 出力）と TimedRotatingFileHandler（日次ローテーション、30世代保持）を設定する共通ユーティリティを追加。
  - LOG_LEVEL / LOG_DIR の優先解決、既存ハンドラの安全なクリーンアップ処理を実装。
  - ログディレクトリ作成失敗時はファイルハンドラをスキップしてコンソール出力のみ継続。

- プロセス優先度 / CPU affinity ユーティリティ（kabusys.utils.process_priority）
  - Windows / POSIX の差分を吸収してプロセス優先度を設定する set_process_priority を追加。
  - CPU コア数制限を行う set_cpu_affinity を追加（未指定時は影響なし）。
  - 権限不足など失敗時は警告でスキップする堅牢な実装。

- 実行系と監視起動スクリプト（run_execution.py / run_monitoring.py）
  - 起動時に set_process_priority("high") を呼び出してプロセス優先度を上げる。
  - run_execution:
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite を使用（settings.paper_sqlite_path）し、本番 DB と分離。
    - BrokerClientFactory を用いてブローククライアントを生成（Mock の利用を想定）。
    - ExecutionEngine をデーモンスレッドで起動し、data/stop_requested.flag による外部停止制御、実行用 PID ファイル管理を行う。
    - RiskManager にデフォルト設定を組み込んで起動。
  - run_monitoring:
    - 監視は環境に関わらず本番 sqlite_path を使用する（監視データの一元化）。
    - MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔上書き（デフォルト 60 秒）。無効値は警告してデフォルトにフォールバック。
    - 停止フラグの検出、check_once() の例外を安全にハンドリングしてループ継続。

- 監視 DB 初期化ユーティリティの導入（monitoring.monitoring_db 参照）
  - 起動時に監視用テーブルが存在することを保証する初期化処理を呼び出す（冪等）。

- ポートフォリオ構築モジュール（kabusys.portfolio）
  - 候補選定と重み計算（portfolio.portfolio_builder）
    - buy_signals をスコア降順かつ signal_rank タイブレークでソートする select_candidates。
    - 等分配 calc_equal_weights、スコア比例配分 calc_score_weights（スコア合計が 0 の場合は等分配にフォールバック）。
  - リスク調整（portfolio.risk_adjustment）
    - セクター集中制限 apply_sector_cap（既存ポジションと価格情報に基づく除外処理、"unknown" セクターは除外対象外）。
    - 市場レジームに応じた乗数 calc_regime_multiplier（bull/neutral/bear をマップ。未知レジームは 1.0 で警告フォールバック）。
  - ポジションサイジング（portfolio.position_sizing）
    - allocation_method として "risk_based" / "equal" / "score" をサポート。
    - 損切り幅・リスク率からリスクベースの株数を計算、単元株（lot_size）丸め、1 銘柄上限および aggregate cap（available_cash）によるスケーリングを実装。
    - cost_buffer を使った手数料・スリッページの保守的推定、スケーリング時の端数再配分ロジックを搭載。

- Paper Trading 検証レポート生成ツール（kabusys.tools.paper_verification_report）
  - Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）から集計し、稼働率、注文成功率・送信率、リスク却下数、API レイテンシ（平均 / 最大 / P95）を出力する CLI を追加。
  - P95 は独自実装で計算、レポートに PASS/FAIL 判定ロジック（閾値: uptime 99%、fill 90%、send 95%、P95 latency <= 200ms）を導入。
  - 日付フィルタ（--from / --to）のサポート、DB 存在チェックと sqlite エラー時のフォールバックを実装。

その他
- パッケージメタ情報に __version__ = "0.1.0" を設定（kabusys.__init__）。
- モジュールのエクスポート整理（kabusys.portfolio.__init__ で公開 API を集約）。

[0.1.0] - 2026-04-18
--------------------

初期リリース（コードベースの主要機能群を実装）

追加（主要機能）
- 環境設定管理
  - Settings クラスにより環境変数の取得 / バリデーションを実装（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）。
  - .env 自動ロード（.env / .env.local）機能を実装。
- 実行・監視インフラ
  - ExecutionEngine 起動スクリプト（run_execution.py）と SystemMonitor 起動スクリプト（run_monitoring.py）を提供。
  - 停止フラグ、PID ファイル、監視 DB 初期化の取り扱いを実装。
- ロギングとプロセス管理
  - 共通ロギングセットアップ（stdout と 日次ローテートファイル）を実装。
  - プロセス優先度設定（Windows / POSIX 対応）および CPU affinity 関連ユーティリティを実装。
- ポートフォリオ構築
  - 候補選定、重み付け、ポジションサイズ計算、セクター制限、レジーム乗数を実装。
- 検証・運用ツール
  - 環境設定ウィザード（config_setup.py）。
  - 設定検証 CLI（validate_config.py）。
  - Paper Trading 検証レポート生成ツール（tools/paper_verification_report.py）。
- 研究用ファクター計算（research/factor_research.py）: モメンタム等のファクター計算機能の実装を着手（モジュール骨子と定数定義を含む）。

変更
- なし（初回リリースのため）

修正
- なし（初回リリースのため）

セキュリティ
- なし

注記
- .env は絶対にリポジトリにコミットしないように注意喚起。config_setup にもその旨を明記。
- Paper Trading と本番 DB は明示的に分離する設計（paper_trading 用 DB を別ファイルに保存）。
- 一部の外部依存（psutil, duckdb, PyYAML など）は実行環境でのインストールが必要。validate_config と各モジュールの起動時に依存存在チェック・エラーハンドリングを行う。

--- 

（必要であれば、各ファイル変更履歴や関数単位の詳細な説明・既知の制限事項・今後の改善予定を追記できます）