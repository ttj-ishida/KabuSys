CHANGELOG
=========

すべての変更は Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) の慣習に従って記載しています。  
日付はコードベース内のコメント・使用例に基づき推測しています。

[Unreleased]
-------------

- なし

[0.1.0] - 2026-04-22
-------------------

Added
- 基盤: パッケージ初版リリース。
  - パッケージバージョンを src/kabusys/__init__.py にて __version__ = "0.1.0" と定義。
- 実行スクリプト:
  - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時に専用の paper_trading DB を使用する仕組みを導入（PAPER_TRADING_SQLITE_PATH）。
    - BrokerClientFactory により実運用 / ペーパートレードで適切なブローカークライアントを選択。
    - ExecutionEngine をスレッドでデーモン実行し、data/stop_requested.flag による停止制御・PID ファイル管理を実装。
    - RiskManager, OrderManager, Reconciler 等の組み立てロジックを追加（設定値はコード内に明示）。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視処理は環境にかかわらず本番 sqlite_path を用いる（監視 DB の分離方針）。
    - data/stop_requested.flag による停止検知と KeyboardInterrupt を受けた際の整列終了処理を実装。
- 設定管理:
  - src/kabusys/config.py: Settings クラスを追加。
    - .env 自動読み込み機能（.env, .env.local）をプロジェクトルート (.git または pyproject.toml) から探索して実行。KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。
    - .env のパースで export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント等に対応する堅牢な実装。
    - 各種環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, PAPER_FILL_MODE など）をプロパティとして提供。env 値のバリデーションを実装（例: PAPER_FILL_MODE の有効値チェック、KABUSYS_ENV の有効値チェック、LOG_LEVEL 検証）。
    - paper_trading 用に paper_sqlite_path をサポート。
- 設定ツール / 検証:
  - config_setup.py: 対話式ウィザードで .env の初期作成・更新を支援。
    - 既存 .env 読み込み、シークレット項目のマスク表示、確認後に .env を出力。
    - デフォルト値・選択肢の提示、キャンセル時の安全扱いを実装。
  - validate_config.py: 起動前検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、ファイルパスの親ディレクトリ有無チェック、config/*.yaml の存在・パース確認（PyYAML がない場合は警告してスキップ）。
    - --strict モードで警告を FAIL 扱いにできる。
- ポートフォリオ構築ライブラリ (純関数群):
  - portfolio_builder.py:
    - select_candidates: BUY シグナルのスコアソートと上位 N 選定。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重の重み計算。スコア全0時のフォールバックを実装。
  - risk_adjustment.py:
    - apply_sector_cap: セクター集中制限の適用（既存ポジションの時価ベースで判定、"unknown" セクターは除外しない）。
    - calc_regime_multiplier: 市場レジームに応じた資金乗数（bull/neutral/bear、未知レジームは 1.0 でフォールバック）。
  - position_sizing.py:
    - calc_position_sizes: allocation_method (risk_based, equal, score) に基づく注文株数決定、単元株丸め、per-position/max aggregate cap、cost_buffer の考慮によるスケールダウン、残余分の再配分ロジックを実装。
    - risk_based モードでのリスクベース株数計算（risk_pct / stop_loss_pct に基づく）。
    - 将来的な拡張点として銘柄別 lot_size の導入をコメントで記載。
- リサーチ:
  - research/factor_research.py: ファクター計算モジュールの骨組みを追加（モメンタム等の計算方針・定数定義を含む）。（実装の続きあり。コード途中までの実装）
- ユーティリティ:
  - utils/logging_setup.py:
    - 統一ログ設定関数 setup_logging を追加。
    - StreamHandler を stdout に、TimedRotatingFileHandler で日次ローテーション（30日保持）するハンドラをルートロガーに設定。
    - LOG_DIR が作成できない場合はファイル出力をスキップしてコンソール出力へフォールバック。
  - utils/process_priority.py:
    - set_process_priority: Windows / POSIX を吸収して優先度の設定を行うユーティリティを追加。失敗時は警告してスキップ。
    - set_cpu_affinity: 指定コア数への CPU affinity 固定を実装（実行環境で未対応なら警告）。
- モニタリング DB 初期化:
  - monitoring/monitoring_db.py への初期化関数 init_monitoring_db の呼び出しが run_* スクリプトで使われ、監視テーブルの存在を確保（冪等）。
- Paper Trading 向け検証ツール:
  - tools/paper_verification_report.py:
    - Paper Trading の検証レポート生成スクリプトを追加。
    - 稼働率、注文成立率、送信率、リスク却下数、API レイテンシ（平均/最大/P95）を集計し PASS/FAIL 判定（閾値はソースに定義）。
    - P95 計算ロジック、期間フィルタ、DB が存在しない場合のエラーメッセージ等を実装。
- その他:
  - 複数箇所で sqlite3 / duckdb 接続を利用している（monitoring / execution / research 用）。
  - 停止フラグ・PID ファイル管理・ログ出力の整備により運用性を向上。

Changed
- ログ出力:
  - すべての起動スクリプトで setup_logging を呼ぶ想定によりログ挙動を統一。
  - StreamHandler を stdout に出力する決定（cron/Task Scheduler 等でのリダイレクト対策）。
- .env 自動読み込み優先度:
  - OS 環境変数 > .env.local > .env の順で読み込む実装。OS 変数はプロテクトされ上書きされない。

Fixed
- 環境変数パースの堅牢化:
  - export プレフィックスやクォート内のバックスラッシュエスケープ、インラインコメントの扱いなどを正しく処理することで .env のパーサーを改善。
- 監視ループの堅牢化:
  - MONITOR_POLL_INTERVAL が不正な値（0 や負数、非数）を指定された場合はデフォルトにフォールバックして警告を出すようにした（ValueError 回避）。
  - monitor.check_once() で例外が発生しても監視ループを継続する例外ハンドリングを追加。
- ログディレクトリ作成失敗時のフェールセーフ:
  - ログディレクトリ作成に失敗した場合はコンソール出力にフォールバックして起動を継続するようにした。

Security
- .env ファイルに関する注意を明記（config_setup の生成ヘッダ内に .env を絶対に Git にコミットしない旨を記載）。
- 秘匿設定項目は対話ウィザードでマスク表示（保存時は平文だがファイル管理は運用上の注意を促す）。

Known issues / TODO
- research/factor_research.py はモメンタム計算の実装が途中（ファイル末尾付近で実装が途切れている）。完全実装が必要。
- position_sizing.calc_position_sizes:
  - price が欠損（0.0）の場合にエクスポージャー・投資額の過少見積りが発生する可能性があり、将来的に前日終値や取得原価等のフォールバック価格を導入する予定（コメントで明示）。
  - 単元株（lot_size）を銘柄毎に持たせる設計拡張が TODO として残されている。
- 一部の機能は外部依存（psutil, duckdb, PyYAML など）により挙動が左右される。依存ライブラリが欠けている場合は該当チェックをスキップまたは警告で扱う設計。

Notes
- 本 CHANGELOG はソースコードの内容から推測して作成したものであり、実際のコミット履歴とは差異がある可能性があります。必要であればコミット履歴（git log）やリリースノートに基づく正式な差分作成を行ってください。