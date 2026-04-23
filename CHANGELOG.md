CHANGELOG
=========

すべての変更は Keep a Changelog のフォーマットに従って記載しています。  
（翻訳・推測に基づく要約です。実際のコミット履歴ではありません。）

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-23
-------------------

Added
- 初回リリース: KabuSys v0.1.0 を公開。
- 実行用スクリプトを追加
  - run_execution.py
    - ExecutionEngine を起動する CLI。
    - KABUSYS_ENV=paper_trading 時は paper_trading 専用の SQLite（既定: data/paper_trading.db）を使用し、MockBrokerClient を利用して本番 DB と完全分離して動作する。
    - 起動時にプロセス優先度を "high" に設定するユーティリティ呼び出しを行う。
    - 停止制御のために data/stop_requested.flag を監視し、停止時は Engine.stop() を呼ぶ。
    - 実行中 PID を data/execution.pid に記録する仕組み（pid_file の取り扱い）。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視用 DB 初期化（init_monitoring_db）を行い、duckdb と sqlite 接続を管理する。
    - 監視は環境にかかわらず本番 sqlite_path を使用する点に留意。
    - 停止フラグファイルで優雅にループを抜ける。

- 設定管理
  - kabusys.config: Settings クラスを実装
    - .env 自動読み込み（プロジェクトルートを .git または pyproject.toml から検出）。
    - .env / .env.local の読み込み順序、OS 環境変数保護（protected set）をサポート。
    - .env パーサは export 構文、クォート（シングル/ダブル）、エスケープ、インラインコメント処理に対応。
    - 必須環境変数取得時に未設定なら ValueError を投げる _require 実装。
    - 多数の設定プロパティを提供（DB パス、ログレベル、KABUSYS_ENV 判定、Paper Trading 関連設定等）。
    - PAPER_FILL_MODE の値検証（"instant"|"partial"|"never"|"reject"）。

  - config_setup.py: 対話式ウィザード
    - .env の初期作成・更新を補助する CLI（秘密値はマスク表示）。
    - デフォルトや選択肢、説明を含む対話で .env を生成・保存する機能。

  - validate_config.py: 設定検証 CLI
    - 必須環境変数、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と（PyYAML があれば）パース検証を実施。
    - KABUSYS_ENV=live 時の追加警告（LINE 通知設定や kill_flag_clear_on_start の危険性）。
    - --strict モードで警告を FAIL 扱いにできる。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順・タイブレークに signal_rank を利用して候補選定。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重配分（スコアが全て 0 の場合は等配分へフォールバックし警告）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: 同一セクターの既存保有比率が閾値を超える場合に新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（未知レジームは 1.0 でフォールバック）。
    - ログでのデバッグ・警告を適切に出力。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") に基づく発注株数計算。
    - 単元（lot_size）丸め、1 銘柄上限（max_position_pct）、全体の aggregate cap（available_cash）を超える場合のスケーリング、および残余キャッシュを用いた端数処理を実装。
    - cost_buffer を考慮した保守的見積、価格欠損時のスキップ、ログ出力。

- ユーティリティ
  - utils/logging_setup.py
    - 統一ログ設定ユーティリティ: stdout へ StreamHandler、日次ローテートのファイルハンドラ（TimedRotatingFileHandler）をルートロガーに追加。
    - 既存ハンドラのクリア処理を実装して二重出力を防止。
    - LOG_LEVEL / LOG_DIR の解決順を実装、ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - stdout を利用することで cron 等でのリダイレクト運用を容易に。
  - utils/process_priority.py
    - プラットフォーム差異を吸収してプロセス優先度を設定（Windows, POSIX 対応）。
    - CPU affinity 設定関数 set_cpu_affinity を追加（N コアにピンニング）。
    - 権限不足や未サポート環境では警告を出してスキップ。

- 監視・レポート系
  - monitoring DB 初期化ユーティリティ（init_monitoring_db）と SystemMonitor を呼び出す仕組みを run_monitoring/run_execution で統合。
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加。
    - 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ、リスク却下数などを集計し PASS/FAIL を判定する閾値を定義。
    - --from / --to / --db オプション対応。P95 計算、日付フィルタを ISO8601 形式で扱う。

- リサーチ系（部分実装）
  - research/factor_research.py（ファクター計算モジュール）
    - DuckDB を用いたモメンタムなどのファクター計算基盤を追加（モメンタム、MA200、ATR、出来高系等の計算方針を実装）。
    - 関数 calc_momentum の実装開始（excerpt が途中で切れていますが、DuckDB 接続を受けて prices_daily 等のテーブルを参照する設計）。

Changed
- ログの挙動を統一
  - すべての起動スクリプトが setup_logging を呼び出すことでログ出力のフォーマットとローテーションが統一された。
- .env の自動読み込みロジック
  - プロジェクトルート探索を __file__ 基準で行うため、CWD に依存しない自動ロードに改善。

Fixed
- MONITOR_POLL_INTERVAL に 0 以下や非数が入った場合に time.sleep に渡すと ValueError になる問題を回避するため、値検証とフォールバック処理を run_monitoring に導入。

Known issues / Notes
- portfolio/risk_adjustment.apply_sector_cap:
  - price が欠損（0.0）の場合にエクスポージャーが過少見積りされてしまう可能性があり、将来的に前日終値や取得原価等のフォールバック価格を導入予定（TODO コメントあり）。
- position_sizing は現状すべての銘柄で共通の lot_size（デフォルト 100）を前提としており、将来的に銘柄ごとの lot_map を受け付ける拡張案あり。
- research/factor_research.py はファイル内で途中（excerpt が切れている）になっており、完全な実装は未確認。
- run_monitoring は監視 DB に対して常に本番 sqlite_path を使用する設計のため、テスト目的での分離が必要な場合は運用設定（環境変数や DB パスの切り替え）に注意。

Security
- シークレット（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など）は .env に記載する想定であり、config_setup の出力にも「.env を絶対に Git にコミットしないこと」と明記。

その他
- パッケージバージョンは src/kabusys/__init__.py にて __version__ = "0.1.0" として設定。

-----------------------------------------
注: 本 CHANGELOG は提示されたソースコードからの推測に基づくまとめです。実際のコミットメッセージや運用ドキュメントがある場合はそちらを一次情報として参照してください。