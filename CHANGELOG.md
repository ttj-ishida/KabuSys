Keep a Changelog
=================

すべての重要な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。

[Unreleased]: https://example.com/compare/v0.1.0...HEAD

0.1.0 - 2026-04-19
------------------

Added
- 全体
  - 初回リリース（バージョン 0.1.0）。
  - パッケージメタ情報を src/kabusys/__init__.py に追加（__version__ = "0.1.0"）。
- 起動スクリプト
  - run_monitoring.py: SystemMonitor をポーリングで実行する監視ループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値は警告を出してデフォルトにフォールバック。
    - 停止制御はプロジェクトの data/stop_requested.flag ファイルで行う。
    - 監視用 DB は環境にかかわらず本番 sqlite_path を使用する設計。
  - run_execution.py: ExecutionEngine を起動する実行スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 専用の SQLite（data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderManager / RiskManager / Reconciler 組立て、スレッド実行によるセッション管理を実装。
    - 停止フラグ（data/stop_requested.flag）検知で安全にエンジンを停止。
- 設定関連
  - src/kabusys/config.py: 環境変数管理クラス Settings を追加。
    - .env 自動読み込み機能 （プロジェクトルートが特定できる場合のみ、優先度: OS環境 > .env.local > .env）。
    - 複数のプロパティを提供（DBパス、API トークン、Paper Trading 設定、閾値等）。
    - パーサは quoted 値および export プレフィックスをサポートし、コメント処理の挙動を考慮。
    - 設定値のバリデーション（PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL 等）。
  - src/kabusys/config_setup.py: .env を対話的に作成・更新するウィザードを追加。
    - 主要な設定項目を対話形式で入力可能。既存 .env の読み込みと Enter による既存値の再利用に対応。
    - 保存時にテンプレート形式で .env を出力。
  - src/kabusys/validate_config.py: 起動前設定検証 CLI を追加。
    - 必須環境変数の存在確認、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在および（PyYAML がある場合の）パース検証を実施。
    - --strict オプションで警告を失敗扱いにできる。
- ロギング・プロセス管理ユーティリティ
  - src/kabusys/utils/logging_setup.py: 統一ロギング設定ユーティリティを追加。
    - stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler（既定 logs/ ディレクトリ）をルートロガーに設定。
    - 既にハンドラが設定されている場合はクリアして再設定。
    - LOG_DIR 無効時やディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - src/kabusys/utils/process_priority.py: プロセス優先度 / CPU affinity 設定ユーティリティを追加。
    - Windows / POSIX 系（Linux, macOS, FreeBSD）を吸収し、"high"/"normal"/"low" レベルを指定して現在プロセスの優先度を設定可能。
    - set_cpu_affinity() による最初の N コアへの固定機能を提供。
    - 権限不足や未対応環境の場合は警告を出して安全にスキップ。
- ポートフォリオ構成（純関数群）
  - src/kabusys/portfolio/portfolio_builder.py:
    - 信号のソートと上位候補選択 select_candidates。
    - 等金額配分 calc_equal_weights。
    - スコア加重配分 calc_score_weights（全スコアが 0 の場合は等配分にフォールバック）。
  - src/kabusys/portfolio/risk_adjustment.py:
    - セクター集中制限 apply_sector_cap（既存保有のセクター比率に応じて新規候補を除外）。
    - 市場レジームに応じた乗数 calc_regime_multiplier（bull/neutral/bear をマップ、未知は警告とフォールバック）。
  - src/kabusys/portfolio/position_sizing.py:
    - 各配分方法（risk_based / equal / score）に基づく発注株数算出 calc_position_sizes。
    - 単元株丸め、position 単位上限、aggregate cap（利用可能現金を超える場合のスケーリング）を実装。
    - cost_buffer による保守的コスト見積り、スケーリング後の小口分配ロジックを含む。
  - src/kabusys/portfolio/__init__.py: 上記関数をエクスポート。
- ツール
  - src/kabusys/tools/paper_verification_report.py:
    - ペーパートレード用 SQLite DB（PAPER_TRADING_SQLITE_PATH）からシステム安定性・注文成功率・レイテンシ等を集計して検証レポートを標準出力に生成するツールを追加。
    - P95 計算、閾値（稼働率・成功率・送信率・P95 レイテンシ）に基づく PASS/FAIL 判定を出力。
    - 日付フィルタ --from / --to と DB パスの指定 --db をサポート。
- リサーチ（部分実装）
  - src/kabusys/research/factor_research.py:
    - ファクター計算モジュールの骨組みを追加（モメンタム等の指標設計、DuckDB を用いた計算方針）。
    - 定数や関数の仕様コメントを含む（モメンタム算出関数 calc_momentum を実装開始、未完の箇所あり）。

Changed
- なし（初回リリースのため既存機能改変は無し）。

Fixed
- なし（初回リリース）。

Deprecated
- なし。

Removed
- なし。

Security
- なし。

Notes / 補足
- .env 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。パッケージ配布後も動作するようプロジェクトルートの検出は __file__ 基準で行う。
- run_monitoring / run_execution はプロセス優先度を起動直後に "high" に設定しようと試みるため、権限や OS によっては警告が出る場合があります（安全にフォールバック）。
- Paper Trading と本番 DB は明確に分離される設計（ExecutionEngine は settings.is_paper に応じた sqlite_path を使用）。
- research/factor_research.py は設計ドキュメント（コメント）に基づく実装途中の箇所が存在します。今後のリリースで完全実装予定。

もし変更内容の表現をより技術的に詳述したい箇所（例: 各関数の引数や返り値、ロジックの厳密な説明）があれば、該当箇所ごとにより詳細なリリースノートを作成します。