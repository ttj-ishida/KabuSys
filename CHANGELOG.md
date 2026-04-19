CHANGELOG
=========

この CHANGELOG は Keep a Changelog の形式に準拠しています。  
セマンティックバージョニングを採用しています。

[Unreleased]
-------------

- なし

[0.1.0] - 2026-04-19
--------------------

初回リリース。以下の主要機能とユーティリティを追加しました。

Added（追加）
- 基本パッケージ情報
  - パッケージバージョンを設定: src/kabusys/__init__.py にて __version__ = "0.1.0" を定義。

- 環境・設定管理
  - Settings クラスを追加して環境変数経由の設定取得を一元化（src/kabusys/config.py）。
    - J-Quants / kabuステーション / LINE / DB パス / 監視閾値などをプロパティで取得可能。
    - KABUSYS_ENV / LOG_LEVEL の検証とフラグ判定（is_live / is_paper / is_dev）。
    - PAPER_FILL_MODE の妥当性検証（instant/partial/never/reject）。
    - paper_trading 用のデフォルト SQLite パス（PAPER_TRADING_SQLITE_PATH）。
  - .env 自動読み込み機能を導入（プロジェクトルートの .env / .env.local）。既存 OS 環境変数を保護して上書き制御（src/kabusys/config.py）。
  - .env のパースを強化：export プレフィックス・クォート・エスケープ・インラインコメントに対応。

- 対話式設定ウィザード
  - .env を対話的に作成・更新する CLI を追加（src/kabusys/config_setup.py）。
    - 各キーの説明・デフォルト値表示・シークレットマスク表示。
    - 生成される .env にコメントヘッダを付与し、Git コミット禁止を注意書き。

- 設定検証ツール
  - 起動前チェック用 CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数の存在確認、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ確認、config/*.yaml の存在と YAML パースチェック（PyYAML がある場合）。
    - KABUSYS_ENV=live 時の追加ガード（LINE 通知・KILL_FLAG_CLEAR_ON_START の注意喚起）。
    - --strict オプションで警告をエラー扱いにできる。

- 起動スクリプト
  - ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）
    - KABUSYS_ENV=paper_trading 時は専用の paper_trading DB を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine の起動を実装。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル管理、デーモン的スレッド実行と安全停止ロジック。
    - RiskConfig のデフォルト値（max_position_pct 等）を定義し、初期ポートフォリオ値を broker.get_available_cash() で取得。
  - SystemMonitor 起動スクリプト（src/kabusys/run_monitoring.py）
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出力。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用して監視データを一元管理。
    - stop flag 検知でループを安全終了、例外発生時はログに出力して次回ポーリングまで待機。

- ロギング・プロセス管理ユーティリティ
  - 統一ロギング設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - stdout（StreamHandler）と日次ローテートファイル（TimedRotatingFileHandler）をルートロガーに設定。LOG_DIR / LOG_LEVEL 解決順を実装。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップし、コンソールのみで継続。
  - プロセス優先度 / CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX の差分を吸収して set_process_priority(level) を提供。psutil の権限不足などの失敗はログ警告でスキップ。
    - set_cpu_affinity(cpu_count) により最初の N コアにプロセスをピン留め可能（権限や非対応 OS は警告してスキップ）。

- ポートフォリオ構築（純関数群）
  - 銘柄選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: スコア降順で上位 N を選択（signal_rank によるタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分（スコア全0 の場合は等配分にフォールバック）。
  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 既存保有のセクター比率が上限を超える場合に当該セクターの新規候補を除外（unknown セクターは除外しない）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返却。未知レジームはフォールバックで 1.0。
  - 株数決定・リスク制限・単元丸め（src/kabusys/portfolio/position_sizing.py）
    - allocation_method に応じた発注株数算出（risk_based / equal / score）。
    - per-position 上限・aggregate cap（available_cash に基づくスケーリング）、lot_size（単元）丸め、cost_buffer を用いた保守的見積もり。
  - 上記をパッケージエクスポート（src/kabusys/portfolio/__init__.py）。

- Paper Trading 検証ツール
  - paper_verification_report CLI を追加（src/kabusys/tools/paper_verification_report.py）。
    - system_status / trade_logs / risk_logs から稼働率・注文成功率・送信率・レイテンシ指標を集計してレポート出力。
    - P95 計算、閾値による PASS/FAIL 判定、期間フィルタ（--from, --to）、DB パス指定（--db / 環境変数）に対応。
    - デフォルト閾値は稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms。

- リサーチ（骨組み）
  - ファクター計算モジュールの骨格を追加（src/kabusys/research/factor_research.py）。
    - Momentum 等を計算する方針と定数群、calc_momentum のインターフェース設計を含む（DuckDB 接続で prices_daily を参照する設計）。※実装は一部（ファイル末尾で途切れ）で続きの実装を想定。

Changed（変更）
- .env 自動読み込みの振る舞い
  - 読み込み優先順位を OS 環境変数 > .env.local > .env と定義。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能（テストなどで利用）。
  - .env ロード時に OS 環境変数キーを protected として上書きを防止。

Fixed（修正 / ロバストネス向上）
- 不正な MONITOR_POLL_INTERVAL の安全フォールバック（run_monitoring.py）。
- ログディレクトリ作成失敗時にファイルハンドラ生成をスキップし、stderr に警告を出すことで起動継続を保証（logging_setup.py）。
- init_monitoring_db の冪等呼び出しを run_execution/run_monitoring が行い、監視テーブルの存在を保証（monitoring_db との連携を想定）。
- process_priority の権限不足や未対応 OS に対しては警告ログで安全にフォールバック。

Security（セキュリティ関連）
- .env を絶対に Git にコミットしない旨を config_setup の出力に明記。
- パスワード等の入力はウィザードでシークレットマスク表示（保存時は平文 .env に書き込まれるため取り扱い注意）。

Notes / Migration（備考・移行）
- 初回セットアップ手順の推奨:
  1. python -m kabusys.config_setup で .env を生成
  2. python -m kabusys.validate_config で設定を検証
- paper_trading を使用する場合、PAPER_TRADING_SQLITE_PATH（または KABUSYS_ENV=paper_trading）を用いて本番データベースと分離してください。
- 本番運用時は KABUSYS_ENV=live 設定時の警告に注意し、KILL_FLAG_CLEAR_ON_START は 0 を推奨します。

Acknowledgements（謝辞）
- 本プロジェクトはシンプルな自動売買基盤の初期実装を含みます。今後、ユニットテスト・ドキュメントの拡充、欠損データハンドリングや外部 API のフェイルオーバー強化等を行う予定です。