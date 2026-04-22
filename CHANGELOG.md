CHANGELOG
=========

この CHANGELOG は "Keep a Changelog" の形式に準拠しています。  
（コードベースから推測できる変更点・実装内容を元に作成しています。）

Unreleased
----------

- なし

0.1.0 - 初回リリース
-------------------

リリース日: 未設定（スナップショット）

Added
- 基本アーキテクチャ実装
  - 日本株自動売買システム "KabuSys" の初回コードベースを追加。
  - パッケージバージョンを 0.1.0 に設定（src/kabusys/__init__.py）。

- 設定管理
  - Settings クラスを実装（src/kabusys/config.py）。
    - 環境変数経由で各種設定を取得（J-Quants / kabuステーション / DB パス / モード判定 等）。
    - KABUSYS_ENV, LOG_LEVEL 等の検証を実装。
    - paper_trading 用の PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH をサポート。
  - 自動 .env 読み込み機能を実装（プロジェクトルートを .git / pyproject.toml から検出）。
  - .env ファイルの柔軟なパース（export プレフィックス、引用符、コメント処理、保護付き上書き）を追加。

- 環境設定ウィザード CLI
  - 対話式ウィザードで .env を作成・更新するツールを追加（src/kabusys/config_setup.py）。
    - J-Quants トークン、kabu API パスワード、DB パス、ログレベル等の項目を用意。
    - 既存 .env 読み込み・マスク表示・確認後保存機能。

- 設定検証 CLI
  - 起動前に環境変数や config/*.yaml の整合性を検査するツールを追加（src/kabusys/validate_config.py）。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パスの親ディレクトリ存在チェック、YAML パース検査、ライブ環境向けの追加ガード。
    - --strict オプションで警告も失敗扱いに可能。

- 起動スクリプト
  - 監視ループ起動スクリプト（SystemMonitor）を追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を制御（デフォルト 60 秒）。
    - 停止フラグファイル（data/stop_requested.flag）による安全停止。
    - monitoring は環境に関わらず本番用 sqlite_path を使用する旨の実装。
  - ExecutionEngine 起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading の際は専用の MockBrokerClient を使用し、paper_trading 用 DB に記録して本番 DB と分離。
    - PID ファイル管理、停止フラグ検知、デーモン Thread での実行管理。

- ロギング・プロセス制御ユーティリティ
  - 統一ロギング初期化ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - stdout 出力の StreamHandler と 日次ローテート（TimedRotatingFileHandler）をルートロガーに設定。
    - ログディレクトリ自動作成・ファイルハンドラ失敗時のフォールバックに対応。
  - プロセス優先度・CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX を吸収する cross-platform 実装。
    - set_process_priority(level)、set_cpu_affinity(cpu_count) を提供。
    - 権限不足や未対応 OS の場合は警告を出してスキップ。

- データベース / 分析基盤統合
  - SQLite（監視 / paper_trading 用）と DuckDB（分析用）を組み合わせた接続処理を追加（各起動スクリプトで利用）。
  - 監視用 DB 初期化用の init_monitoring_db 呼び出しを組み込み（冪等）。

- Execution コンポーネント（インターフェース準備）
  - BrokerClientFactory、ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager 等の呼び出し・組み立てを run_execution に追加（実装ファイルは別所在）。
  - RiskConfig デフォルト値を設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。
  - ExecutionEngine をスレッドで実行し、停止フラグで安全停止するワークフローを実装。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - 銘柄選定・重み付け（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates、calc_equal_weights、calc_score_weights を実装。
    - スコアが全て 0 の場合のフォールバック警告。
  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap（セクター上限を越える場合候補を除外）を実装。
    - calc_regime_multiplier（bull/neutral/bear の乗数）を実装。
    - 不足データ時の挙動や未知レジームのフォールバックを明記。
  - 株数決定・リスク制限・単元丸め（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes を実装（risk_based / equal / score の複数方式をサポート）。
    - aggregate cap（利用可能現金に応じたスケーリング）や lot_size（単元）丸め、残差の分配アルゴリズムを実装。
    - cost_buffer による保守的見積りをサポート。
    - 将来的な拡張（銘柄ごとの lot_size マップ）に関する TODO コメントあり。

- 研究用ファクター計算（部分実装）
  - DuckDB を使ったモメンタム等のファクター計算モジュールを開始（src/kabusys/research/factor_research.py）。
    - モメンタム、MA200 乖離、ATR、出来高関連を意図した設計（実装は途中）。

- ツール
  - Paper Trading 検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - 稼働率、注文成功率、送信率、レイテンシ統計（avg/max/P95）等を算出して PASS/FAIL 判定を出力。
    - フィルタ期間指定（--from/--to）や DB パス指定オプションをサポート。
    - デフォルトの合格基準（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）を設定。

Changed
- なし（初回公開）

Fixed
- なし（初回公開）

Notes / Implementation details / Known issues
- .env 自動ロードはプロジェクトルートが検出できない場合スキップされる（テスト時には KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
- apply_sector_cap 内で price が欠損（0.0）の場合、エクスポージャーが過小評価される可能性がある旨が TODO コメントで指摘されている（将来のフォールバック価格導入を検討）。
- calc_position_sizes は現状すべての銘柄で同一 lot_size（デフォルト 100）を想定。将来的には銘柄別 lot_map への拡張を予定。
- research/factor_research.py は設計方針と一部定数・関数を定義しているが、ファイル末尾で実装が途中の状態（スナップショット時点）。

Environment variables (代表的なもの・デフォルト)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: （必須）
- KABU_API_PASSWORD: （必須）
- KABU_API_BASE_URL: デフォルト http://localhost:18080/kabusapi
- DUCKDB_PATH: デフォルト data/kabusys.duckdb
- SQLITE_PATH: デフォルト data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: デフォルト data/paper_trading.db
- LOG_LEVEL: デフォルト INFO
- MONITOR_POLL_INTERVAL: 監視ポーリング秒（デフォルト 60）
- PAPER_FILL_MODE: paper_trading の約定挙動（instant/partial/never/reject、デフォルト instant）
- KILL_FLAG_CLEAR_ON_START: 起動時 Kill Flag 自動クリア（0/1、デフォルト 0）
- LOG_DIR: ログ保存先ディレクトリ（デフォルト logs/）

Security
- .env は絶対に Git にコミットしない旨をドキュメント化（config_setup の出力ヘッダ）。

Credits
- このリリースはソースコードの内容から推測して作成された CHANGELOG です。実際のコミット履歴・リリースノート作成時は各コミットメッセージ・テスト結果・公開日等の実情報を反映してください。