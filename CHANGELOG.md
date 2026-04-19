CHANGELOG
=========

すべての変更は Keep a Changelog の慣例に従って記載しています。
https://keepachangelog.com/ja/

Unreleased
----------

（現在なし）

v0.1.0 — 2026-04-19
-------------------

Added
- 基本アプリケーションの初版をリリース。
  - パッケージメタ情報:
    - バージョン: 0.1.0 (src/kabusys/__init__.py)
- 実行・監視用エントリポイントを追加。
  - run_execution.py
    - ExecutionEngine 起動スクリプト。
    - KABUSYS_ENV に応じて paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory を利用して paper_trading 時は MockBrokerClient を用いる設計（設定により実ブローカに切り替え可能）。
    - 停止フラグ (data/stop_requested.flag) と PID ファイル (data/execution.pid) による制御をサポート。
    - プロセス優先度を最初に "high" に設定して起動。
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出力。
    - 停止フラグ検出で安全にループ終了。
    - 監視は環境に関わらず本番用 sqlite_path を参照して起動（監視データは常に本番 DB を想定）。
- 環境設定・検証関連ツールを追加。
  - config_setup.py
    - 対話式ウィザードで .env ファイルを作成／更新。
    - 対話項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、LOG_LEVEL、Kill Switch 設定など）を網羅。
  - validate_config.py
    - 起動前の設定検証 CLI。
    - 必須環境変数の存在確認、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリチェック、config/*.yaml の存在と（PyYAML があれば）パース検証、KABUSYS_ENV=live 時の追加警告、などを実行。
    - --strict オプションで警告も失敗扱いにできる。
- 環境変数管理モジュールを追加（.env 自動ロード・堅牢なパーサ）。
  - config.py
    - プロジェクトルート（.git または pyproject.toml を基準）を探索し、.env / .env.local を自動読み込み（OS 環境変数が優先、.env.local は上書き）。
    - .env 行のパースはシングル/ダブルクォートやバックスラッシュエスケープ、インラインコメントに対応。
    - Settings クラスを提供し、各種設定（DB パス、PID/kill flag、閾値、環境判定、PAPER_FILL_MODE の検証など）をプロパティで取得可能。
- ロギング・プロセス制御ユーティリティを追加。
  - utils/logging_setup.py
    - 全起動スクリプトで共通利用できるロギング初期化関数 setup_logging を提供。
    - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler、30 日保持）をルートロガーに設定。
    - LOG_DIR 指定／自動作成に失敗した場合はファイルハンドラをスキップして stdout のみで継続。
  - utils/process_priority.py
    - psutil を用いたクロスプラットフォームのプロセス優先度設定（high/normal/low）。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供。
    - 権限不足や未対応 OS の場合は警告を出力して安全にスキップ。
- ポートフォリオ構築関連の純粋関数群を追加（DB を参照しない設計）。
  - portfolio/portfolio_builder.py
    - 候補選定 select_candidates（スコア降順、タイブレークに signal_rank）、
    - 等金額配分 calc_equal_weights、
    - スコア加重配分 calc_score_weights（全スコアが0時に等配分へフォールバック）。
  - portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap（既存保有のセクター時価で上限判定、"unknown" セクターは制限対象外）、
    - レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear およびフォールバック）。
  - portfolio/position_sizing.py
    - position サイズ計算 calc_position_sizes（risk_based / equal / score の各 allocation_method をサポート）。
    - 単元（lot_size）丸め、1 銘柄上限・aggregate 上限、cost_buffer を用いた保守的見積り、利用可能現金超過時のスケールダウンと残余配分ロジックを実装。
- 解析・リサーチ補助モジュール（鳥瞰的実装）を追加。
  - research/factor_research.py
    - DuckDB 接続を受け取り、Momentum/Value/Volatility/Liquidity といったファクター計算の土台を実装予定（prices_daily / raw_financials を参照する設計。モメンタム計算のための定数・設計ノートを含む）。
- 検証レポート生成ツールを追加。
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite を参照して稼働率、注文成功率・送信率、リスク却下数、API レイテンシ（平均/最大/P95）を集計。
    - PASS/FAIL の閾値（稼働率 99%、成功率 90%、送信率 95%、P95 レイテンシ 200ms）を定義し、標準出力に判定付きレポートを出力。
    - 日付フィルタ（--from/--to）と --db オプションをサポート。
- モニタリング用 DB 初期化ユーティリティを導入。
  - monitoring/monitoring_db.py（起動前に監視用テーブルが存在することを保証する init_monitoring_db の使用を各スクリプトで行う）
- パッケージのエクスポートを整理。
  - portfolio の公開 API を __all__ でエクスポート。

Changed
- （初版リリースのため変更なし）

Fixed
- （初版リリースのため修正なし）

Deprecated
- （該当なし）

Removed
- （該当なし）

Security
- （該当なし）

注記 / 運用上の注意
- .env は絶対にリポジトリにコミットしないでください（config_setup が警告を出力）。
- 本番環境（KABUSYS_ENV=live）では LINE 通知設定の未設定や KILL_FLAG_CLEAR_ON_START=1 等に注意するため、validate_config が追加の警告を出します。
- run_execution/run_monitoring は stop flag（data/stop_requested.flag）や PID ファイルを用いるため、運用時は該当ファイルの扱いに注意してください。
- ログは標準で logs/<app_name>.log に日次ローテートで保存されます。ログディレクトリ作成に失敗するとコンソール出力のみになります。

開発者向け
- Settings クラスを通じて環境変数を参照することが推奨されます（直接 os.environ を参照するコードは最小限にする）。
- DuckDB/SQLite を用いるため、データスキーマの変更は monitoring_db や prices_daily/raw_financials の更新が必要です（今後のリリースでスキーマ管理機能を追加予定）。

--- 

（この CHANGELOG は提示されたソースコードの内容に基づいて推測して作成しています。実際のコミット履歴やリリースノートが存在する場合はそちらを優先してください。）