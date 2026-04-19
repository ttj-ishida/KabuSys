CHANGELOG
=========

すべての変更は "Keep a Changelog" の方針に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/

Unreleased
----------

- なし

0.1.0 - 2026-04-19
------------------

Added
- 基本パッケージ初期実装を追加
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止は project/data/stop_requested.flag によるフラグ検知で行う。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（デフォルト: data/monitoring.db）を使用して初期化。
    - sqlite3 と DuckDB の接続管理と終了処理を実装。
    - 例外発生時はロギングで例外情報を出力して次ポーリングへ継続。

  - run_execution.py
    - ExecutionEngine 起動スクリプト。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite DB を使用（data/paper_trading.db、環境変数で上書き可）。本番 DB と分離。
    - BrokerClientFactory を経由してブローカークライアントを作成（paper_trading では MockBrokerClient を想定）。
    - スレッドでエンジンを起動し、停止フラグ（data/stop_requested.flag）検知でエンジン停止を実行。
    - PID ファイル保存機能を想定（pid ファイルパス指定可）。

- 設定管理 / ユーティリティ
  - config.py
    - Settings クラスで環境変数ベースの設定を提供（各種デフォルト値を含む）。
    - .env 自動ロード機能を実装（プロジェクトルートを .git または pyproject.toml から検出）。
    - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env 読み込み時に OS 環境変数を保護（既存の OS 環境変数を上書きしない/保護リスト）。
    - .env パースの仕様:
      - export KEY=val 形式対応
      - シングル/ダブルクォートを考慮したバックスラッシュエスケープ処理
      - クォートなしの場合は '#' の前にスペース/タブがあればインラインコメントとして無視
    - 各種 getter を通じて型変換・バリデーション（env 値の候補チェックや数値変換等）。

  - config_setup.py
    - 対話式ウィザードで .env の作成・更新を支援する CLI。
    - 秘匿値は入力時にマスク表示、デフォルト値/選択肢を提示して Enter で既存値を再利用可。
    - 生成される .env に注意書きを付与（Git にコミットしない旨）。
    - 保存前に内容確認プロンプトあり。

  - validate_config.py
    - 起動前の設定検証 CLI。
    - 必須環境変数の未設定チェック、プレースホルダ値チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック。
    - DUCKDB/SQLITE のパスに対する親ディレクトリ存在チェック（存在しない場合は警告）。
    - config/*.yaml の存在確認と、PyYAML がある場合はパース検証（PyYAML 未導入ならスキップして警告）。
    - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の危険設定を警告）。
    - --strict オプションで警告も FAIL 扱いにできる。

- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py
    - setup_logging 関数を提供。
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション、30日保持）を設定。
    - 既存ハンドラは再設定時に安全にクリア。
    - ログレベルとログディレクトリは引数 > 環境変数 > デフォルト の順で解決。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。

  - utils/process_priority.py
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。
    - Windows / POSIX の差分を吸収して nice 値や Windows の優先度クラスに設定を行う（psutil 利用）。
    - 権限不足や未対応 OS では警告を出してスキップ。
    - set_cpu_affinity は最初の N コアに固定（未指定なら何もしない）。

- Portfolio 構築ライブラリ（純粋関数群: DB 非依存）
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順＋タイブレークで上位 N を選択。
    - calc_equal_weights: 等金額配分（1/N）。
    - calc_score_weights: スコア比率で重みを付与。全スコアが 0 の場合は等配分にフォールバックして警告ログ。

  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限（max_sector_pct）を超える場合、該当セクターの新規候補を除外（unknown セクターは除外対象外）。
    - calc_regime_multiplier: market_regime に応じた投下資金乗数（bull=1.0 / neutral=0.7 / bear=0.3）。未知レジームは 1.0 でフォールバックし警告ログを出力。

  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に対応した発注株数算出。
    - 単元株数（lot_size）で丸め、max_position_pct（銘柄上限）、max_utilization（全体利用率）を考慮。
    - risk_based: 損切り幅 stop_loss_pct と risk_pct に基づく株数算出。
    - aggregate cap（available_cash）を超える場合はスケールダウンし、余剰キャッシュを残差の大きい順に lot 単位で再配分。
    - cost_buffer を考慮して手数料/スリッページを保守的に見積もる。

- paper trading / 検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成スクリプト。
    - SQLite（PAPER_TRADING_SQLITE_PATH または --db）からデータを集計し、稼働率、注文成功率、送信率、レイテンシ（avg、max、P95）などを算出。
    - デフォルトの判定基準（しきい値）を定義:
      - 稼働率 >= 99.0%
      - 注文成功率 >= 90.0%
      - 送信率 >= 95.0%
      - P95 レイテンシ <= 200 ms
    - 日付フィルタ指定（--from / --to）に対応。
    - データ不足時に N/A で表示し、PASS/FAIL を判定して出力。

- Execution / Monitoring 各種統合点
  - Execution 起動時に monitoring テーブルの存在を保証する init_monitoring_db 呼び出しを追加（冪等）。
  - Execution の RiskManager 初期化で RiskConfig のデフォルト値を設定し、initial_portfolio_value を broker.get_available_cash() から取得する設計。

Notes / Known issues
- research/factor_research.py はファイル末尾が途中で切れている（"start_da" で未完）。モメンタム等のファクター計算モジュールは設計コメントや定数等が用意されているが、実装は完了していないか途中で途切れています。
- 一部 TODO コメントあり（例: position_sizing の銘柄別 lot_size サポート、risk_adjustment の price 欠損ハンドリングなど）。将来的な拡張の余地を残す。
- 実際のブローカークライアント実装（本番/モックの具体的な差異）は BrokerClientFactory の実装に依存。ここでは factory 呼び出しと paper_trading 分離の設計が導入されている。

Security
- .env ファイルは生成時に「絶対に Git にコミットしないこと」を明示。機密情報は .env に保存する想定。

Deprecated
- なし

Removed
- なし

Fixed
- なし

以上（初期リリースの主要な追加点と注意事項）