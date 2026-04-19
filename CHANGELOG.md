CHANGELOG
=========

すべての変更は「Keep a Changelog」形式に従って記載しています。
フォーマット:
- Added: 新機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Security: セキュリティ関連

Unreleased
----------

- （現在のスナップショットでは未リリースの変更はありません）

0.1.0 - 2026-04-19
------------------

Added
- 基本アプリケーション構成を追加
  - パッケージバージョンを 0.1.0 に設定 (src/kabusys/__init__.py)。
- 起動スクリプト / 実行エントリを追加
  - 実行エンジン起動スクリプト (src/kabusys/run_execution.py)
    - KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite（data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory を用いてブローカークライアントを生成し、ExecutionEngine をスレッドで起動。
    - 停止フラグ (data/stop_requested.flag) と PID ファイル管理 (_EXECUTION_PID) に対応。停止フラグ検知時に安全に停止処理を行う。
    - 初期化時にプロセス優先度を "high" に設定。
  - 監視ポーリングループ起動スクリプト (src/kabusys/run_monitoring.py)
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値や <=0 の場合はデフォルトにフォールバックして警告を出力。
    - 監視は環境にかかわらず本番用 sqlite_path を使用する旨を明示。
    - 停止フラグ検知でループを終了し、例外発生時には例外ログを出してポーリングを継続。
    - DuckDB 接続も利用。
- 環境設定・検証用 CLI を追加
  - 対話式 .env 作成/更新ウィザード (src/kabusys/config_setup.py)
    - シークレット項目は表示時にマスク。
    - .env の読み書き機能と確認プロンプトを提供。
  - 設定検証ツール (src/kabusys/validate_config.py)
    - 必須環境変数の存在チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パス／config/*.yaml の存在・パースチェックを実装。
    - --strict オプションで警告を FAIL として扱える。
- 環境変数 / 設定管理を強化 (src/kabusys/config.py)
  - .env 自動ロード機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化対応。
  - .env パーサを実装：export プレフィックス対応、クォート値のバックスラッシュエスケープ解釈、インラインコメント処理等をサポート。
  - Settings クラスを追加し、各種設定プロパティ（J-Quants / kabu API / DB パス / PID / Kill Switch / 閾値 等）を提供。env, log_level の検証と is_live/is_paper/is_dev ヘルパーを実装。
  - PAPER_FILL_MODE の妥当性チェック（instant/partial/never/reject）。
- ロギングユーティリティを追加 (src/kabusys/utils/logging_setup.py)
  - StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）をルートロガーにセットアップする setup_logging を提供。
  - ログディレクトリ作成失敗時はファイルハンドラをスキップしてコンソール出力のみ継続。
  - ログレベル解決順とログディレクトリ解決順を明記。
- プロセス優先度 / CPU affinity ユーティリティを追加 (src/kabusys/utils/process_priority.py)
  - set_process_priority(level) により Windows / POSIX の差分を吸収して優先度を設定。
  - set_cpu_affinity(cpu_count) による CPU ピンニングをサポート。権限不足や未対応 OS 時は警告を出してスキップ。
- ポートフォリオ構築ライブラリを追加 (src/kabusys/portfolio/*)
  - 候補選定・重み計算 (portfolio_builder.py)
    - select_candidates: スコア降順で上位 N を選択（同点は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights（スコア総和が 0 の場合は等金額にフォールバック）。
  - セクター集中制限・レジーム乗数 (risk_adjustment.py)
    - apply_sector_cap: 既存ポジションのセクター別時価を計算し、max_sector_pct を超えるセクターの候補を除外。unknown セクターは制限対象外。
    - calc_regime_multiplier: 'bull'/'neutral'/'bear' に応じた乗数（未知レジームは警告を出して 1.0 にフォールバック）。
  - 株数決定・リスク制限・単元丸め (position_sizing.py)
    - allocation_method に応じた株数算出（risk_based / equal / score）。
    - lot_size に基づく丸め、per-stock 上限 (max_position_pct)、aggregate cap（available_cash 超過時スケーリング）を実装。
    - cost_buffer を考慮した保守的見積りと残余キャッシュを使った再分配ロジックを実装。
- Paper Trading 検証レポートツールを追加 (src/kabusys/tools/paper_verification_report.py)
  - SQLite の paper_trading DB を読み、稼働率 (uptime_pct)、注文成功率（Fill/Created）、送信率（Sent/Created）、P95 レイテンシ等を集計し PASS/FAIL 判定を出力。
  - P95 計算、日付フィルタ、閾値の定義（稼働率 99%、成立率 90%、送信率 95%、P95 200ms）を実装。
- リサーチ用ファクター計算モジュールを追加 (src/kabusys/research/factor_research.py)
  - モメンタム・ATR・流動性等の計算を行う設計。DuckDB 経由で prices_daily / raw_financials を参照する方針を採用（calc_momentum 等の実装を含む）。

Changed
- ログ出力先を stdout に統一
  - setup_logging の StreamHandler は stderr ではなく stdout を使用。cron 等からのリダイレクトを考慮した設計。
- .env の読み込み優先順位を明確化
  - OS 環境変数 > .env.local > .env の順で読み込む。既存の OS 環境変数は protected として上書きしない。
- 監視と実行の DB 接続ポリシーを明確化
  - run_monitoring: 監視は常に settings.sqlite_path（本番用 path）を使用する旨を明記。
  - run_execution: paper_trading 時は settings.paper_sqlite_path を使用して本番データと分離。

Fixed
- .env パーサの堅牢化
  - export 接頭辞対応、引用符付き値のバックスラッシュエスケープ処理、インラインコメントの取り扱いを改善して .env の様々な書式に対応。
- ログハンドラの二重登録問題に対処
  - setup_logging は既存ハンドラを flush/close してから再設定することで二重出力を防止。
- process_priority の例外処理を強化
  - 権限不足や未実装メソッドに対して警告を出し、安全にスキップするよう改善。

Security
- config_setup におけるシークレット表示はマスク表示
  - 対話式ウィザードで JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD 等のシークレットは確認画面で "****" 表示にすることで露出を防止。

Notes / その他
- validate_config は PyYAML がない環境でも実行可能（YAML 検証はスキップして警告を出す挙動）。
- 多くの関数は DB 参照を最小化しており（ポートフォリオ/サイズ計算は純粋関数）、ユニットテストが容易な設計になっている。
- 一部ファイル（例: research/factor_research.py）は設計コメントや途中の実装が含まれており、今後の拡張（追加ファクターや最適化）を想定している。

開発者向けヒント
- 自動 .env ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト実行時に便利です）。
- ログレベルは環境変数 LOG_LEVEL で制御できます。ログファイルは既定で logs/<app_name>.log に日次ローテーションで出力されます。
- 実行プロセスの優先度設定・CPU ピンニングは utils.process_priority を通して行ってください（プラットフォーム抽象化済み）。

--- 
この CHANGELOG は、与えられたコードベースの内容から推測して作成しています。必要であれば、リリース日付の調整や追加の「Fixed / Changed」項目を反映して更新します。