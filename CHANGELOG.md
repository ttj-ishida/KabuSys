CHANGELOG
=========

すべての変更は Keep a Changelog 準拠の形式で記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------
（現在のコードベースに対する未リリースの変更はありません）

0.1.0 - 2026-04-19
-----------------
Initial release — 日本株自動売買システム KabuSys の初期実装を追加しました。以下はコードベースから推測して記載した主要な追加点・動作仕様です。

Added
- 基本構成・設定
  - Settings クラスを実装（src/kabusys/config.py）。
    - .env 自動ロード機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - .env のパースロジックを独自実装（export 形式、クォート文字列、末尾コメント処理を考慮）。
    - 各種設定プロパティを提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH, PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU/MEM/DISK 閾値, KABUSYS_ENV, LOG_LEVEL 等）。
    - 環境値の妥当性チェック（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE の有効値チェック）。

- 環境設定ツール
  - 対話式 .env 作成ウィザードを追加（src/kabusys/config_setup.py）。
    - よく使う項目を対話的に設定し .env を生成・更新可能。
    - シークレット項目はマスク表示。生成後に保存確認。
    - デフォルト値や選択肢を提示。

- 設定検証ツール
  - validate_config CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数の存在チェック、KABUSYS_ENV と LOG_LEVEL の妥当性、DB パスの親ディレクトリ確認、config/*.yaml の存在と PyYAML によるパース検証、KABUSYS_ENV=live 時の追加ガードなど。
    - --strict オプションで警告を FAIL 扱いにできる。

- 起動スクリプト
  - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory を用いてブローカークライアントを生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine の組み立てとバックグラウンドスレッドでの実行制御。
    - data/stop_requested.flag により安全に停止可能。PID ファイル管理（data/execution.pid）。
    - 起動時にプロセス優先度を "high" に設定。

  - 監視ループ起動スクリプト（src/kabusys/run_monitoring.py）。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックし警告ログを出力。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path（Settings.sqlite_path）を使用する設計（監視専用 DB を想定）。
    - stop_requested.flag による停止検知、例外捕捉でループ継続。

- 監視 DB 初期化ユーティリティ （init_monitoring_db の利用箇所を追加）。
  - run_execution/run_monitoring 起動時に監視テーブルが存在することを保証。

- ログ・プロセス管理ユーティリティ
  - ロギングセットアップユーティリティ（src/kabusys/utils/logging_setup.py）。
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30 日分保持）をルートロガーに設定。
    - LOG_DIR が作れない・ファイルハンドラ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。
    - デフォルトログディレクトリ: logs/
    - stdout を使用（stderr ではなく） — スケジューラからのリダイレクトを想定。

  - プロセス優先度 / CPU affinity 設定ユーティリティ（src/kabusys/utils/process_priority.py）。
    - Windows と POSIX 系を吸収して set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。
    - psutil を使用し、権限不足や未対応環境では警告ログでスキップ。

- ポートフォリオ構築モジュール（src/kabusys/portfolio/）
  - portfolio_builder.py:
    - select_candidates: スコア降順・signal_rank でのタイブレークにより候補選定。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア加重配分（スコア合計が 0 の場合は等配分にフォールバックし警告）。
  - risk_adjustment.py:
    - apply_sector_cap: セクター集中上限（max_sector_pct）を超える場合に候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market regime に基づく投下資金乗数（bull/neutral/bear -> 1.0/0.7/0.3）、未知レジームは 1.0 にフォールバックして警告。
  - position_sizing.py:
    - calc_position_sizes: allocation_method に応じて個別株数を計算（"risk_based", "equal", "score" をサポート）。
    - 単元株（lot_size）丸め、per-stock 上限（max_position_pct）、aggregate cap（available_cash）でスケールダウンするロジックを実装。
    - cost_buffer を加味した保守的見積り、スケールダウン時の残差処理（lot 単位での配分調整）を実装。

- リサーチ / ファクター計算（部分実装、src/kabusys/research/factor_research.py）
  - モメンタム / MA200 / ATR / ボリューム等の計算を行う設計（DuckDB を入力として利用）。（ファイルは途中まで実装されていることを確認）

- ツール
  - Paper Trading 検証レポート生成スクリプト（src/kabusys/tools/paper_verification_report.py）。
    - Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH / デフォルト: data/paper_trading.db）から統計を集計してレポート出力。
    - 指標: 稼働率（uptime_pct）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシなど。
    - Pass/Fail 基準の定数を定義（稼働率 >= 99%、fill_rate >= 90%、send_rate >= 95%、P95 <= 200 ms）。
    - コマンドライン引数 --from/--to/--db をサポート。

- パッケージ初期化
  - __version__ = "0.1.0"（src/kabusys/__init__.py）。
  - package export 定義（__all__）に主要サブパッケージを含める。

Behavior / Safety notes
- run_execution/run_monitoring は起動時にプロセス優先度を "high" に設定（set_process_priority を呼び出す）。
- 停止フラグ（data/stop_requested.flag）を配置することでループや実行中エンジンを安全に停止できる。
- run_execution は paper_trading 環境時に別 DB に記録するため本番 DB と分離される設計。
- .env 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。自動検出できない場合はスキップする。
- ログ出力は標準で stdout へ出力し、可能ならファイルへ日次ローテーションで保存する。ログディレクトリ作成失敗時はファイル出力を行わず継続する。

Fixed / Robustness improvements
- .env パーサーはクォート中のエスケープや行内コメントの扱いを改善（より堅牢な読み込み）。
- モニターポーリング間隔の環境変数 MONITOR_POLL_INTERVAL に不正値が設定された場合、安全にデフォルト値にフォールバックして警告を出す。
- process_priority / cpu_affinity は権限不足や未対応プラットフォームで例外を吸収し警告を出力することで起動を妨げないように設計。

Deprecated
- なし

Removed
- なし

Security
- 秘密値の扱い:
  - config_setup の対話時にシークレットはマスク表示。
  - .env は絶対に Git にコミットしないことを README に明記（config_setup の出力ヘッダに注記あり）。

Migration notes
- 既存のシステムがある場合:
  - paper_trading を利用する場合は KABUSYS_ENV を "paper_trading" に設定し、PAPER_TRADING_SQLITE_PATH を指定して本番 DB と物理的に分離してください。
  - 本番運用では KILL_FLAG_CLEAR_ON_START は 0 を推奨（validate_config でも警告を出します）。

補足
- 本 CHANGELOG はソースコードの実装内容を元に推測してまとめたものであり、実際の意図や未公開の設計文書と差異がある可能性があります。必要であれば、より詳細なリリースノート作成のために追加のコンテキスト（設計文書、要求仕様、差分履歴）を提供してください。