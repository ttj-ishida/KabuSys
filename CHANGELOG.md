CHANGELOG
=========

すべての変更は Keep a Changelog: https://keepachangelog.com/ja/ に準拠しています。

Unreleased
----------

なし

0.1.0 - 2026-04-23
------------------

Added
- 基本パッケージ初期実装を追加
  - パッケージバージョン: `kabusys` __version__ = "0.1.0"（src/kabusys/__init__.py）。

- 起動スクリプト / デーモン類
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV が `paper_trading` の場合は専用のペーパートレード用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - ブローカークライアントは BrokerClientFactory 経由で生成。
    - ExecutionEngine をスレッドで起動し、data/stop_requested.flag により外部から停止可能。
    - 起動時にプロセス優先度を "high" に設定（utils/process_priority）。
    - 実行時 PID を data/execution.pid に書き込む想定（pid_file を使用）。

  - システム監視ポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60 秒）。不正値はデフォルトにフォールバック。
    - 監視（monitoring）は KABUSYS_ENV に関係なく本番 sqlite_path（デフォルト: data/monitoring.db）を使用する設計。
    - 停止フラグ（data/stop_requested.flag）を検知してループ終了。
    - SystemMonitor インスタンスを用いた単一ポーリング実行（monitor.check_once()）で例外はログ化して次ポーリングに継続。

- 環境設定 / 検証関連 CLI
  - .env 対話式ウィザードを追加（src/kabusys/config_setup.py）。
    - 対話で .env を生成/更新。J-Quants トークン、kabu API パスワード、DB パス、ログレベル等の主要項目を扱う。
    - 生成された .env は Git にコミットしない旨の注釈を出力。
    - 使用例: python -m kabusys.config_setup

  - 設定検証ツールを追加（src/kabusys/validate_config.py）。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パース検証（PyYAML が存在しない場合は警告してスキップ）。
    - --strict オプションで警告を FAIL 扱いにできる。
    - 使用例: python -m kabusys.validate_config

- 環境設定管理
  - Settings クラスを追加（src/kabusys/config.py）。
    - .env 自動ロード機能（プロジェクトルート検出: .git または pyproject.toml を探索）。
    - OS 環境変数 > .env.local > .env の優先順位で読み込み。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード無効化可能。
    - 各種プロパティ提供: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DB パス（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH）、paper_fill_mode 検証、PID/KILL フラグパス、しきい値（CPU/MEM/DISK）、環境判断（is_live/is_paper/is_dev）など。
    - 環境変数パースは引用符・エスケープ・コメントにも堅牢に対応。

- ロギング / プロセス制御ユーティリティ
  - 統一ロギングセットアップを追加（src/kabusys/utils/logging_setup.py）。
    - stdout に出力する StreamHandler と、日次ローテーション（TimedRotatingFileHandler）でファイル出力（logs/<app_name>.log、30 日保持）をルートロガーに設定。
    - 既存ハンドラをクリアして再設定することで二重設定を防止。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップして stdout のみで継続。

  - プロセス優先度および CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX の差を吸収して set_process_priority("high"|"normal"|"low") を提供。psutil を用いる（権限不足や未サポート環境では警告を出してスキップ）。
    - set_cpu_affinity(cpu_count) によるコア固定をサポート（None は設定しない）。

- ポートフォリオ構築関連ライブラリ
  - 銘柄選定・重み算出（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: スコア降順（同点は signal_rank）で候補選定。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア比率で重み付け（全スコア 0 の場合は等分にフォールバック）。
  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 既存保有のセクター比率が閾値を超える場合、同セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market_regime に応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3）、未知レジームは警告して 1.0 でフォールバック。
  - 発注株数決定（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes:
      - risk_based / equal / score の allocation_method をサポート。
      - リスクベースでは risk_pct, stop_loss_pct に基づき基準株数を計算。
      - per-stock 上限（max_position_pct）と aggregate 上限（available_cash）を考慮。
      - lot_size（単元）に合わせた丸めと、利用可能現金を超える場合のスケールダウン処理（端数配分は残差順に lot 単位で追加配分）。
      - cost_buffer によりスリッページ/手数料を概算して保守的に見積もる。

- Paper Trading 検証ツール
  - レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - 指標: 稼働率（uptime%）、注文成功率（fill_rate）、送信率（send_rate）、API レイテンシ（avg/max/P95）、リスク却下数。
    - パス/フェイル基準を定義（デフォルト: uptime >=99%, fill_rate >=90%, send_rate >=95%, P95 <=200ms）。
    - 日付フィルタ (--from, --to) と DB パス指定 (--db) をサポート。
    - データ不足やテーブル不存在時に N/A を扱う堅牢な実装。

- 研究用ファクター計算モジュール（骨組み）
  - src/kabusys/research/factor_research.py を追加（モメンタム／ボラティリティ等の計算方針を実装予定）。
    - DuckDB 接続を受け、prices_daily / raw_financials からファクターを算出する方針。
    - （注）ソースは途中で切れており、一部未実装の関数が存在（calc_momentum が途中で終端）。

Changed
- n/a（初回リリース）

Fixed
- n/a（初回リリース）

Removed
- n/a（初回リリース）

Security
- n/a（初回リリース）

Notes / Usage
- .env 自動読み込みはプロジェクトルートが検出できる場合にのみ動作します（.git または pyproject.toml を探索）。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 実行エンジンと監視は外部ファイル（data/stop_requested.flag）で安全に停止できます。Kill Switch 等の設定は Settings の kill_flag 系プロパティで制御可能。
- ログはデフォルトで logs/<app_name>.log に日次ローテートで保存されます。ログディレクトリ作成に失敗した場合はコンソールのみで動作します。

Known issues / TODO
- src/kabusys/portfolio/risk_adjustment.py 内で price が欠損（0.0）の場合に exposure を過少見積りする問題が注記されており、前日終値や取得原価でのフォールバックなどの拡張が想定されています。
- position_sizing の将来的な拡張点として、銘柄ごとの単元情報（lot_size）を外部マスタで渡す設計への変更が記載されています（現状は全銘柄共通の lot_size）。
- src/kabusys/research/factor_research.py は未完（calc_momentum 実装途中）。研究用モジュールは現状「骨組み」段階。
- 一部外部依存（psutil, duckdb, PyYAML）が必要。PyYAML 不在時は config YAML のパースチェックをスキップする仕様。

Developer / Operator Tips
- 設定検証: python -m kabusys.validate_config
- 環境作成ウィザード: python -m kabusys.config_setup
- Paper レポート: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- 監視起動: python -m kabusys.run_monitoring
- 実行エンジン起動: python -m kabusys.run_execution

If you want, I can:
- 追記として各 CLI の出力例や .env のサンプルを CHANGELOG に付け加えます。
- factor_research の未実装部分の実装プランを作成します。