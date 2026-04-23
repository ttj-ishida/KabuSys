CHANGELOG
=========

すべての変更は「Keep a Changelog」形式に従って記載しています。  
セマンティックバージョニングを採用しています。  

[0.1.0] - 2026-04-23
-------------------

Added
- 初回リリースを追加。KabuSys の基礎機能群を実装。
  - パッケージメタ情報
    - src/kabusys/__init__.py に __version__ = "0.1.0" を追加。
  - 実行エントリ / 実行系・監視
    - src/kabusys/run_execution.py
      - ExecutionEngine を起動するスクリプトを追加。
      - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite（data/paper_trading.db 既定）を使用して本番 DB と完全分離する設計。
      - 起動時にプロセス優先度を high に設定。
      - 停止制御: data/stop_requested.flag を監視し、検知時にエンジンを停止。
      - 実行中 PID を data/execution.pid に記録するための pid_file を利用。
    - src/kabusys/run_monitoring.py
      - SystemMonitor のポーリングループ起動スクリプトを追加。
      - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバックし、警告を出す。
      - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（data/monitoring.db 既定）を使用する仕様。
      - 停止制御: data/stop_requested.flag を検知してループを終了。
  - 設定管理 / 初期化 / 検証
    - src/kabusys/config.py
      - Settings クラスを導入し、環境変数をプロパティで扱う統一 API を提供。
      - .env 自動ロード機能:
        - プロジェクトルート（.git または pyproject.toml を探索）を基準に .env/.env.local を読み込む。
        - OS 環境変数を保護するための上書きポリシーを実装。
        - 自動ロードを無効化するための環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
      - .env 行のパースで export プレフィックス、引用符（エスケープ処理含む）、インラインコメント判定をサポートする堅牢なパーサを実装。
      - 各種設定プロパティを提供（例: duckdb_path, sqlite_path, paper_sqlite_path, pid_file_path, kill_flag_path, cpu/memory/disk のしきい値等）。
      - PAPER_FILL_MODE の妥当性チェック（instant/partial/never/reject）を実装。
    - src/kabusys/config_setup.py
      - .env 作成・更新のための対話式ウィザードを追加。
      - シークレット入力のマスク表示、既存 .env の読み込み、保存前の確認ダイアログを搭載。
      - 書式付きの .env ヘッダ（Git にコミットしない注意書き等）を出力。
    - src/kabusys/validate_config.py
      - 起動前に .env と config/*.yaml の基本的な健全性検証を行う CLI を追加。
      - 必須/任意環境変数のチェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、ファイルパスの親ディレクトリ存在チェック、YAML のパース検証（PyYAML 未インストール時はスキップして警告）を実装。
      - --strict オプション（警告も FAIL 扱い）を追加。
  - ロギング / プロセス制御ユーティリティ
    - src/kabusys/utils/logging_setup.py
      - 全アプリケーションで共通利用するログ設定ユーティリティを追加。
      - stdout への StreamHandler（標準出力）および日次ローテーション（TimedRotatingFileHandler、デフォルト logs/）を設定。
      - ログディレクトリ作成失敗時はファイル出力をスキップし、標準出力のみで継続するフォールバックを実装。
      - ログレベル解決順やログディレクトリ解決順を明記。
    - src/kabusys/utils/process_priority.py
      - クロスプラットフォームでのプロセス優先度設定と CPU affinity 設定ユーティリティを追加。
      - Windows / POSIX（Linux/Mac/FreeBSD）に対応するマッピングを実装し、権限不足等の例外は警告にフォールバック。
  - ポートフォリオ構築（純粋関数群）
    - src/kabusys/portfolio/portfolio_builder.py
      - 候補選定 select_candidates、等金額/スコア加重重み計算 calc_equal_weights / calc_score_weights を実装。
      - スコア総和が 0 の場合に等金額にフォールバックし警告を出す挙動を実装。
    - src/kabusys/portfolio/risk_adjustment.py
      - セクター集中制限 apply_sector_cap を実装（既存ポジションのセクター別エクスポージャ計算、上限超過セクターの候補除外）。
      - レジームに応じた乗数 calc_regime_multiplier を実装（bull/neutral/bear マッピング、未知値は 1.0 にフォールバック）。
    - src/kabusys/portfolio/position_sizing.py
      - 発注株数決定ロジック calc_position_sizes を実装（risk_based / equal / score 配分方式、lot_size 単位丸め、aggregate cap スケーリング、cost_buffer を考慮）。
      - 手数料/スリッページ等を想定した保守的見積りのための cost_buffer を導入。
    - src/kabusys/portfolio/__init__.py に主要関数をエクスポート。
  - Paper Trading 検証レポート
    - src/kabusys/tools/paper_verification_report.py
      - ペーパートレード用 SQLite（既定 data/paper_trading.db）を参照して検証レポートを生成する CLI を追加。
      - レポート指標:
        - 稼働率 (uptime_pct)、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシなど。
      - デフォルトしきい値を定義（稼働率 99%、成功率 90%、送信率 95%、P95 レイテンシ 200 ms）。基準未達で FAIL と判定。
      - コマンドライン引数: --from / --to（YYYY-MM-DD）/ --db（DB パス指定）。
  - リサーチ（基礎）
    - src/kabusys/research/factor_research.py
      - DuckDB 経由で各種ファクター（Momentum/Value/Volatility/Liquidity）を計算するための基礎実装（モメンタム周りの定数設定と calc_momentum の雛形を追加、DuckDB 接続を受け取る設計）。
  - そのほか
    - utils パッケージの初期化ファイル、tools パッケージの初期化ファイルを追加。
    - 各モジュールに docstring と使用例、注意点を充実させた。

Changed
- （初回リリースのため履歴上の変更はありません）

Fixed
- （初回リリースのため履歴上の修正はありません）

Security
- .env の取り扱いに関する注記を config_setup のヘッダに明記（.env は絶対に Git にコミットしないこと）。

注意・移行メモ
- 必須環境変数
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD は必須。validate_config で未設定の場合は FAIL。
- .env 自動ロード
  - プロジェクトルートが検出できない場合は自動ロードをスキップします。テスト等で自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Paper Trading と Live の DB 分離
  - paper_trading 環境では PAPER_TRADING_SQLITE_PATH（Settings.paper_sqlite_path）で指定された専用 DB を使用します。運用環境では誤って本番 DB を上書きしないよう注意してください。
- ログ
  - デフォルトのログディレクトリは logs/、ファイルは日次ローテーションで 30 日分保持します。ログディレクトリ作成に失敗した場合はコンソール出力のみで継続します。
- 停止フラグ / Kill Switch
  - run_execution / run_monitoring は data/stop_requested.flag を用いて安全に停止できます。KILL_FLAG_CLEAR_ON_START（Settings.kill_flag_clear_on_start）により起動時に自動的に Kill Flag をクリアする挙動を切替可能（本番では 0 を推奨）。
- CLI
  - 主要な CLI:
    - python -m kabusys.config_setup — .env の対話的作成/更新
    - python -m kabusys.validate_config — 設定検証（--strict オプションあり）
    - python -m kabusys.run_execution — ExecutionEngine 起動スクリプト
    - python -m kabusys.run_monitoring — SystemMonitor ポーリングスクリプト
    - python -m kabusys.tools.paper_verification_report — Paper Trading 検証レポート生成

今後の改善予定（例）
- factor_research の各ファクター計算の完成（Value/Volatility/Liquidity の詳細実装）。
- 銘柄別 lot_size 対応（stocks マスタへ lot_size を持たせる拡張）。
- run_monitoring/run_execution のユニットテストとプロセス監視の強化（再起動監視等）。
- エラーロギング/アラート（LINE 通知連携）の実装拡張（validate_config のガードに基づく設定補助の強化）。

[0.1.0]: https://example.com/releases/0.1.0 (初回リリース)