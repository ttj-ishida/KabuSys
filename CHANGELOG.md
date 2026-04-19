CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従います。
このプロジェクトの初回リリース履歴を日本語でまとめています。

[0.1.0] - 2026-04-19
-------------------

Added
- 基本機能
  - 初期パッケージ構成を追加。パッケージバージョンは `kabusys.__version__ = "0.1.0"`。
  - コマンドライン起動スクリプトを実装:
    - run_execution.py: ExecutionEngine の起動ロジック、ブローカー選択（paper_trading 時は専用 Mock）、別スレッドでのセッション実行、停止フラグ・PID 管理、paper_trading 用 DB 分離（デフォルト: data/paper_trading.db）。
    - run_monitoring.py: SystemMonitor のポーリングループ起動、ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する実装。
  - 設定・環境管理:
    - config.py: .env 自動読み込み（プロジェクトルート検出: .git / pyproject.toml を探索）、環境変数パース（export や引用符、インラインコメント処理対応）、Settings クラスによるアプリケーション設定取得を実装。PAPER_FILL_MODE 等の値検証や is_live/is_paper/is_dev の判定を提供。
    - config_setup.py: .env の対話式ウィザード（作成・更新）、既存値の読み込み・マスク表示、保存処理を実装。
    - validate_config.py: 起動前設定検証 CLI。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パスや config/*.yaml の存在確認（PyYAML が無ければ警告）、KABUSYS_ENV=live 時の追加ガード、--strict オプション対応。
  - ロギング・プロセス管理ユーティリティ:
    - utils/logging_setup.py: 共通ロギング設定ユーティリティ。stdout ストリームハンドラと日次ローテーション付きファイルハンドラ（logs/<app>.log、30日保持）をルートロガーに設定。LOG_DIR / LOG_LEVEL の解決順を実装。ログディレクトリ作成失敗時はファイル出力をスキップしコンソールのみで継続。
    - utils/process_priority.py: プラットフォーム差を吸収したプロセス優先度設定（Windows / POSIX の nice 値対応）、CPU affinity 設定ユーティリティを提供。権限不足や未対応 OS では安全にスキップする。
  - ポートフォリオ構築モジュール（純粋関数群、DB 参照なし）:
    - portfolio/portfolio_builder.py: シグナル選定（score 降順、タイブレーク: signal_rank）、等金額配分 calc_equal_weights、スコア加重 calc_score_weights（全銘柄スコアが 0 の場合は等金額にフォールバック）。
    - portfolio/risk_adjustment.py: セクター集中上限チェック apply_sector_cap（既存保有のセクター時価から除外判定）、市場レジームに基づく投下資金乗数 calc_regime_multiplier（"bull"/"neutral"/"bear" 対応、未知レジームは警告出力で 1.0 フォールバック）。
    - portfolio/position_sizing.py: 各銘柄の発注株数算出 calc_position_sizes。allocation_method として "risk_based"/"equal"/"score" をサポート。単元株（lot_size）丸め、1 銘柄上限・総投下上限（aggregate cap）のスケーリング、cost_buffer による手数料・スリッページ見積もり考慮を実装。
  - 研究用ファクタ計算基盤（部分実装）
    - research/factor_research.py: DuckDB 接続を受けてモメンタム等のファクターを計算する骨格を追加（モメンタム期間等の定義、calc_momentum の開始）。（注: ファイルは途中で未完に見える箇所あり）
  - ユーティリティツール
    - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプト。SQLite（PAPER_TRADING_SQLITE_PATH）から稼働率、注文成功率、送信率、レイテンシ（P95 含む）、リスク却下数を集計して PASS/FAIL 判定を出力。期間フィルタ対応（--from / --to）および閾値の定義（稼働率 99%、成功率 90% 等）を含む。

Changed
- なし（初回リリースのためなし）

Fixed
- なし（初回リリースのためなし）

Deprecated
- なし

Removed
- なし

Security
- なし

Notes / 実装上の注意点
- .env 自動読み込みはデフォルトで有効。テスト等で無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定することで自動ロードをスキップ可能。
- run_monitoring は監視データベースに常に Settings.sqlite_path（本番想定）を使用する設計のため、監視実行環境での DB パスに注意が必要。
- run_execution は paper_trading 環境（KABUSYS_ENV=paper_trading）の場合、BrokerClientFactory により MockBrokerClient を生成して paper_trading 用の SQLite に書き込む（本番 DB と明確に分離）。
- process_priority / set_cpu_affinity や logging_setup のファイルハンドラ作成は権限や環境によって失敗する可能性があるが、失敗時は警告を出して処理を継続する安全設計。
- portfolio.apply_sector_cap 内に価格が欠損（0.0）の場合の注意コメントあり（フォールバック価格を使用する改良が検討対象）。
- position_sizing には将来的な拡張 TODO（銘柄ごとの lot_size を stocks マスタから取得する等）が残っている。
- research/factor_research.py は現状で中途になっている箇所があり、完全実装に向けた追加作業が必要。

既知の問題（Known issues）
- research/factor_research.py の一部が未完。calc_momentum 等の実装が途中で切れているため、ファクター計算全機能はまだ完成していない。
- apply_sector_cap の価格欠損に対するフォールバックが未実装のため、実運用時にセクターエクスポージャーの過少見積りが発生する可能性がある。

今後の予定（例）
- research パイプライン（ファクター計算）の完成
- モニタリング・Execution のさらなる堅牢化（詳細なメトリクス収集、アラート連携）
- 単体テストと CI の整備、ドキュメントの充実

以上。