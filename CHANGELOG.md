CHANGELOG
=========

すべての変更は "Keep a Changelog" に準拠して記載しています。
フォーマットの詳細: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

- ドキュメントやテスト以外の目立った変更はありません（初回リリースに向けた整理済み）。

[0.1.0] - 2026-04-23
--------------------

Added
- 基本アプリケーションパッケージを追加（src/kabusys）。
  - パッケージバージョン: 0.1.0（src/kabusys/__init__.py）
- 起動スクリプトを追加
  - run_execution.py
    - ExecutionEngine 起動スクリプト。
    - KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、Paper Trading 用 SQLite（data/paper_trading.db 既定）を使用することで本番 DB と分離。
    - 起動前にプロセス優先度を "high" に設定。
    - 停止フラグ（data/stop_requested.flag）検出で優雅に停止。
    - 実行中の PID を data/execution.pid に出力（Engine の pid_file を利用）。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV に関係なく本番 sqlite_path を使用する設計。
    - 停止フラグ（data/stop_requested.flag）検出でループ終了。
- 設定管理・ヘルパー
  - config.py
    - 環境変数/ .env の読み込み、Settings クラスを提供。
    - .env 自動ロード機構（プロジェクトルート検出: .git または pyproject.toml）。
    - .env のロード順序: OS 環境 > .env.local > .env。OS 環境の上書きを防ぐ protected 機構を実装。
    - .env の行パーサを独自実装:
      - export KEY=val 形式に対応
      - シングル/ダブルクォート内でのバックスラッシュエスケープに対応
      - インラインコメントの取り扱い（クォートあり/なしの違いに対応）
    - 各種設定プロパティ（DBパス、PID ファイル、しきい値、環境種別チェック等）。
  - config_setup.py
    - 対話式 .env 作成ウィザードを追加（python -m kabusys.config_setup）。
    - 初期値、選択肢、シークレット入力（画面上ではマスク表示）に対応。
    - 生成した .env テンプレートは .git にコミットしないよう注意書きを追加。
  - validate_config.py
    - 起動前に設定を検証する CLI（python -m kabusys.validate_config）。
    - 必須環境変数チェック、KABUSYS_ENV・LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パースチェック（PyYAML があればパース検証）。
    - --strict オプションで警告を失敗扱いにできる。
- ロギング／プロセス管理ユーティリティ
  - utils/logging_setup.py
    - 統一的なロギング設定関数 setup_logging を追加。
    - コンソール（stdout）出力と日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。
    - LOG_DIR 環境変数や引数でログディレクトリを指定可能。ディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみを行うフェールセーフ。
  - utils/process_priority.py
    - プラットフォーム（Windows / POSIX）差分を吸収する process priority 設定ユーティリティを追加。
    - set_process_priority(level) で current process の優先度を high/normal/low に設定（失敗時は警告ログでフォールバック）。
    - set_cpu_affinity(cpu_count) を提供（最初の N コアにプロセスをピン留め、失敗時は警告）。
    - psutil を利用し、Unprivileged 環境でも安全に動作するよう例外処理を実装。
- Portfolio コンポーネント（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: score 降順かつ signal_rank による同点ブレークで候補選定。
    - calc_equal_weights / calc_score_weights: 等金額配分およびスコア加重配分（全スコアが 0 の場合は等額にフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限を適用して候補を除外。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear）を提供。未知レジームは警告出力して 1.0 にフォールバック。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に基づく発注株数計算。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（available_cash）でのスケーリングを実装。
    - cost_buffer を考慮した保守的なコスト見積りと、端数補正アルゴリズム（残差に基づく追加割当て）を実装。
- Research / ファクター計算
  - research/factor_research.py（骨格実装）
    - DuckDB 接続を受ける設計。Momentum / Value / Volatility / Liquidity 等の計算を行う方針を明示。
    - モメンタム計算のパラメタ定数を定義（21/63/126 日等）など。
    - （ファイル末尾で未完の関数があるため、以降の詳細実装は今後のリリースで追加予定）
- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite（デフォルト data/paper_trading.db）から統計を抽出してレポートを生成する CLI。
    - 出力内容: 稼働率（uptime）、注文成功率（fill rate）、送信率、リスク却下数、API レイテンシ（avg/max/P95）。
    - パス/しきい値（稼働率 >= 99% 等）を定義し、PASS/FAIL 判定を行う。
    - --from / --to / --db オプション対応。
- Monitoring DB 初期化フック
  - monitoring.monitoring_db.init_monitoring_db を起動スクリプトから呼び出して監視テーブルの存在を保証する（冪等処理）。

Changed
- なし（初回リリース）。

Fixed
- なし（初回リリース）。

Removed
- なし（初回リリース）。

Notes / ユーザー向けメモ
- .env の自動ロードはデフォルトで有効。テストや特殊環境で無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 本番稼働時は KABUSYS_ENV=live を設定することで追加の注意喚起が validate_config により行われます。
- run_monitoring は監視の設計上、KABUSYS_ENV に関係なく monitoring.db（Settings.sqlite_path）を使用します。run_execution は paper_trading の場合に専用 DB を使用して本番 DB と分離します。
- research/factor_research.py の一部関数は実装継続中です。ファクター計算の完成は次期リリースを予定しています。

貢献・バグ報告
- 不具合や改善提案は Issue を立ててください。README/ドキュメントに沿った PR も歓迎します。