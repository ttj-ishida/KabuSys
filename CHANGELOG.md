# CHANGELOG

すべての重要な変更を Keep a Changelog の形式に従って記載します。  
バージョン番号はパッケージ内の __version__ に合わせて 0.1.0 としています。

## [0.1.0] - 2026-04-19

初回リリース。本リリースで導入された主な機能・CLI・ユーティリティ、既知の制約や設計上の注意点をまとめます。

### 追加 (Added)
- 基本アプリケーション構成
  - パッケージ初期化とバージョン情報を追加（kabusys.__version__ = "0.1.0"）。
- 環境設定関連
  - Settings クラスを実装（src/kabusys/config.py）。
    - 環境変数から各種設定を取得（J-Quants トークン、kabuステーション API、DB パス、紙トレードモード等）。
    - 環境自動読み込み機能: プロジェクトルート（.git または pyproject.toml）を基に .env / .env.local を自動読み込み。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - env 値検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）。
  - 対話式 .env ウィザード CLI を追加（src/kabusys/config_setup.py）。
    - .env の初期作成・更新を対話形式で支援。
  - 設定検証 CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数や config/*.yaml の存在・パースチェック、運用環境ガードの警告表示（--strict オプションで警告を失敗扱いにできる）。
- 実行・監視起動スクリプト
  - 実行エンジン起動スクリプト run_execution（src/kabusys/run_execution.py）を追加。
    - KABUSYS_ENV=paper_trading の場合は MockBroker を利用し、paper_trading 用 SQLite（data/paper_trading.db をデフォルト）を使用して本番 DB と完全分離。
    - プロセス優先度を起動直後に "high" に設定（utils.process_priority を使用）。
    - 停止フラグファイル（data/stop_requested.flag）検出で安全に停止。
    - 実行中の PID を data/execution.pid に記録する仕組み（設定値に依存）。
  - 監視ポーリング起動スクリプト run_monitoring（src/kabusys/run_monitoring.py）を追加。
    - 環境にかかわらず監視は本番の sqlite_path（デフォルト: data/monitoring.db）を使用して起動。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出す。
    - 停止フラグ（data/stop_requested.flag）でループを終了。
- 監視 DB 初期化
  - init_monitoring_db の呼び出しにより、必要な監視テーブルが存在することを保証（冪等操作）。
- ログ設定ユーティリティ
  - 統一ログ設定関数 setup_logging を追加（src/kabusys/utils/logging_setup.py）。
    - stdout への StreamHandler と日次ローテートの TimedRotatingFileHandler をルートロガーに設定。
    - LOG_DIR 環境変数/引数でログ出力先を指定可能。ディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - 既存ハンドラの二重設定を避けるため一度クリアしてから再設定。
- プロセス優先度・CPU 制御ユーティリティ
  - set_process_priority / set_cpu_affinity を追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX の差分を吸収。psutil を利用し、権限不足や未実装 OS に対しては警告を出してスキップ。
- ポートフォリオ構築（純関数モジュール）
  - 候補選定 / 重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates, calc_equal_weights, calc_score_weights（スコア合計が 0 の場合は等分配にフォールバック）。
  - セクター集中リスクとレジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap（セクター別上限を超える場合に新規候補を除外。unknown セクターは上限適用除外）。
    - calc_regime_multiplier（regime に応じた投下資金の乗数。未知のレジームは 1.0 にフォールバック）。
  - 株数決定・リスクベース配分（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes: allocation_method により "risk_based", "equal", "score" をサポート。lot_size（単元）丸め、aggregate cap によるスケールダウン、cost_buffer を考慮。
    - 合わせて様々なデフォルトパラメータ（risk_pct, stop_loss_pct, max_position_pct, max_utilization 等）を設定。
- Paper Trading 検証レポート
  - paper_verification_report CLI（src/kabusys/tools/paper_verification_report.py）を追加。
    - paper_trading の SQLite を読み、稼働率、注文成功率、送信率、P95 レイテンシ等を集計して PASS/FAIL 判定（閾値はスクリプト内定義）。
    - 日付フィルタと --db オプションをサポート。DB が存在しない場合はエラーメッセージを出力。
- リサーチ用ファクター計算（研究用）
  - factor_research モジュールを追加（src/kabusys/research/factor_research.py）。
    - DuckDB 接続を受け取り、Momentum / Value / Volatility / Liquidity 等の計算を行う設計（prices_daily / raw_financials テーブルを参照する前提）。（モジュールは部分実装の状態で含まれる）

### 変更 (Changed)
- （初版のため変更履歴はなし）

### 修正 (Fixed)
- （初版のため修正履歴はなし）

### 破壊的変更 (Breaking Changes)
- （初版のためなし）

### 既知の制約・注意点 (Known issues / Notes)
- 設定・起動
  - Settings._find_project_root は .git または pyproject.toml を探してプロジェクトルートを特定するため、配布後の環境でこれらが存在しない場合は .env 自動ロードをスキップする可能性がある。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD で制御する。
  - 必須環境変数: JQUANTS_REFRESH_TOKEN と KABU_API_PASSWORD。未設定時は Settings 内で ValueError を投げるまたは validate_config でエラーとなる。
- run_monitoring
  - 監視は「環境にかかわらず」本番 sqlite_path（Settings.sqlite_path）を参照して起動する実装となっている。テスト用途においては監視 DB の分離が必要であれば運用側でパスを変更すること。
- run_execution
  - paper_trading モードでは paper_trading 専用 DB を使用するため、本番データと混在しない設計。ただし paper_trading 用 DB のパスは PAPER_TRADING_SQLITE_PATH 環境変数で変更可能。
- position_sizing
  - price が 0.0/欠損のとき target_shares 計算がスキップされる設計になっており、将来的には前日終値や取得原価などのフォールバック価格を導入する旨の TODO コメントあり。
  - 単元 lot_size は現状グローバルに共通で扱う。将来的に銘柄ごとの単元対応を検討中（TODO）。
- risk_adjustment
  - sector_map に存在しないコードは "unknown" 扱いでセクター上限の対象外になるため、マスタデータの充実が重要。
  - calc_regime_multiplier は未知のレジームでフォールバック値 1.0 を返し、警告ログを出力する。
- ロギング
  - ログディレクトリ作成に失敗した場合はファイル出力を行わず stdout のみで継続する（設定ミス等でプロセスが止まりにくい設計）。
- 依存関係
  - process_priority および CPU affinity 機能は psutil に依存。psutil 非対応環境や権限不足では警告を出してスキップされる。
  - validate_config は PyYAML が未インストールの場合、config/*.yaml の内容検証はスキップ（警告表示）。
- 不完全実装
  - research.factor_research モジュールは設計と一部実装が含まれるが、完全なファクター計算ロジックの実装が継続課題。

### マイグレーション / 利用開始メモ (Upgrade / Getting started)
- 必須環境変数を設定してください:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
- .env 初期化:
  - python -m kabusys.config_setup を使って .env を生成・更新できます。
- 設定検証:
  - python -m kabusys.validate_config で起動前チェックを行ってください。--strict を付けると警告も失敗扱いになります。
- 実行・監視:
  - 監視プロセス: python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL でポーリング間隔を変更可能（秒）。不正値はデフォルト 60 秒にフォールバックします。
  - 実行エンジン: python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合は紙トレード専用 DB を使用します。
- Paper Trading 検証:
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
  - --db で DB を指定するか、環境変数 PAPER_TRADING_SQLITE_PATH を設定してください。

### セキュリティ (Security)
- .env ファイルは絶対にリポジトリにコミットしないでください（config_setup のヘッダーにも注意喚起を記載）。
- 実行環境（KABUSYS_ENV=live）の場合は LINE アラート設定（LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID）や KILL_FLAG_CLEAR_ON_START の値を慎重に確認してください（validate_config にて警告を出します）。

---

今後の予定（例）
- research.factor_research の完全実装とユニットテストの充実
- position_sizing の価格フォールバックロジック追加（前日終値・取得原価など）
- 銘柄別 lot_size 対応（stocks マスタの導入）
- 監視・実行のより細かい分離と運用監視アラート（LINE/外部通知）の強化

ご要望や不具合報告は issue を作成してください。