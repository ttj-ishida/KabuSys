CHANGELOG
=========

すべての注目すべき変更点はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。

[Unreleased]
-------------

- なし

[0.1.0] - 2026-04-22
--------------------

Added
- 全体
  - プロジェクト初期リリース（バージョン 0.1.0）。
  - パッケージメタ情報を src/kabusys/__init__.py に追加（__version__ = "0.1.0"）。

- 起動スクリプト / 実行制御
  - run_execution.py:
    - ExecutionEngine を起動するためのメインスクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory を経由してブローカークライアントを生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、スレッドで engine.run_session を実行。
    - 停止フラグファイル（data/stop_requested.flag）と PID ファイル（data/execution.pid）によるプロセス管理。
    - RiskConfig のデフォルトパラメータと初期ポートフォリオ値の取得（broker.get_available_cash() を利用）。

  - run_monitoring.py:
    - SystemMonitor ポーリングループ起動用スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）。不正値は警告のうえデフォルトにフォールバック。
    - 監視は環境に関係なく本番 sqlite_path を使用（監視 DB を一元管理）。
    - stop flag による安全なループ終了と KeyboardInterrupt ハンドリング。
    - プロセス優先度を最初に「high」に設定する処理を導入。

- 設定・環境管理
  - config.py:
    - Settings クラスを追加し、環境変数経由で設定値を提供する統一インターフェースを実装。
    - .env の自動読み込み機能を実装（プロジェクトルート推定: .git or pyproject.toml を基準）。
    - .env パースはクォート対応、export プレフィックス、インラインコメントの処理などを考慮した堅牢な実装。
    - 必須項目取得用の _require と env 値の検証（KABUSYS_ENV, LOG_LEVEL 等）。
    - Paper Trading 関連の設定（PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH）をサポート。
    - 各種閾値（cpu/memory/disk 等）や pid/kill flag のパス等をプロパティとして提供。

  - config_setup.py:
    - 対話式ウィザードで .env を作成・更新する CLI を追加。
    - デフォルト値・選択肢・シークレット入力に対応し、既存 .env の読み込みと差分更新をサポート。
    - 書き込み時に .env のテンプレート（コメント付き）を生成。

  - validate_config.py:
    - .env および config/*.yaml（存在する場合）を起動前に検証する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の値チェック、DB パスの親ディレクトリ存在確認、YAML パースチェック（PyYAML がある場合）を実装。
    - --strict オプションで警告も FAIL 扱いにする機能を提供。

- ポートフォリオ構築（pure functions）
  - portfolio/portfolio_builder.py:
    - 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
    - スコアが全て 0 の場合に等金額にフォールバックして警告を出す挙動を実装。

  - portfolio/risk_adjustment.py:
    - セクター集中制限を適用する apply_sector_cap を追加（既存保有時価を元にセクターごとのエクスポージャーを計算し、上限超過セクターの新規候補を除外）。
    - 市場レジームに応じた資金乗数 calc_regime_multiplier を実装（bull/neutral/bear のマッピング、未知レジームはフォールバックと警告）。

  - portfolio/position_sizing.py:
    - 各種配分方式（risk_based / equal / score）に対応した株数計算 calc_position_sizes を実装。
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap（available_cash）によるスケーリング、cost_buffer（手数料・スリッページ見積）をサポート。
    - スケールダウン時に端数の再配分ロジックを実装して再現性を維持。

  - portfolio/__init__.py:
    - 上記関数群を外部公開するエクスポートを追加。

- ユーティリティ
  - utils/logging_setup.py:
    - 統一的なログ初期化ユーティリティを実装。StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日分保持）をルートロガーに設定。
    - ログレベルとログディレクトリの解決順（引数 > 環境変数 > デフォルト）を実装。
    - ログディレクトリ作成に失敗してもコンソール出力は継続するフェイルセーフを用意。

  - utils/process_priority.py:
    - プロセス優先度設定と CPU affinity 設定ユーティリティを追加。
    - Windows/Linux(macOS/FreeBSD 含む) の差分を吸収（psutil を利用）。アクセスが拒否された場合は警告を出してスキップ。
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。

- 監視・モニタリング関連
  - monitoring モジュール連携:
    - run_monitoring.py と run_execution.py の起動時に monitoring_db の初期化（init_monitoring_db）を行い、監視テーブルの存在を保証する（冪等）。
    - SystemMonitor を利用した単回チェック check_once のループ実行の枠組みを提供。

- ツール / レポート
  - tools/paper_verification_report.py:
    - Paper Trading 検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs から稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）などを集計。
    - 基準値（稼働率99%、成立率90%、送信率95%、P95 レイテンシ 200 ms）に基づく PASS/FAIL 判定を実装。
    - 日付フィルタ（--from / --to）や DB パスの指定（--db / 環境変数）に対応。

- リサーチ
  - research/factor_research.py:
    - ファクター計算モジュールの骨格を追加（モメンタム・MA200乖離・ATR・流動性等を計算する設計）。
    - DuckDB 接続を受け取り prices_daily / raw_financials を参照してファクターを計算する方針を実装開始（関数 calc_momentum の導入／設計説明）。

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Notes / 既知の制限
- research/factor_research.py は計算ロジックの実装が途中で終わっている箇所があり、完全実装は今後のリリースで対応予定。
- 一部の TODO コメントが残っており（例: position_sizing の銘柄別 lot_size 対応、price のフォールバック処理など）、将来的に拡張が見込まれます。
- .env 自動読み込みはプロジェクトルートの推定に .git / pyproject.toml を用いているため、配布後の特殊な配置では自動ロードがスキップされる場合があります。
- 権限不足により process priority / cpu affinity の設定が失敗する可能性があるため、警告を出して処理を継続します。

開発者向けメモ
- 実運用前に validate_config.py による設定検証を実行してください。
- 本番運用時は KABUSYS_ENV=live の注意喚起に従い、LINE 通知設定や KILL_FLAG_CLEAR_ON_START の値を確認してください。