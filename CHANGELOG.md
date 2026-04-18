# Changelog

すべての重要な変更はこのファイルに記録します。  
このファイルは Keep a Changelog の形式に準拠します（https://keepachangelog.com/ja/）。

## [Unreleased]

（現時点では未リリースの変更はありません）

---

## [0.1.0] - 2026-04-18

初回リリース。コードベースから推測される主要機能・ユーティリティ群をまとめます。

### Added

- 基本メタ
  - パッケージバージョンを `__version__ = "0.1.0"` として追加。

- 実行スクリプト
  - run_execution.py
    - ExecutionEngine 起動用スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は paper 専用の SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成を組み込み、OrderRepository / OrderManager / RiskManager / Reconciler を組み立ててエンジンを別スレッドで実行。
    - 停止制御に stop flag (`data/stop_requested.flag`) と pid ファイル (`data/execution.pid`) を使用。
  - run_monitoring.py
    - SystemMonitor を定期ポーリングする監視プロセス起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き（デフォルト: 60 秒）。
    - 監視側は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計（監視 DB の独立性確保）。
    - 停止フラグ検知でループ終了。

- 設定管理 / ユーティリティ
  - config.py
    - 環境変数を読み込む Settings クラスを提供（J-Quants や kabu API、DB パス、監視しきい値、実行環境判定など）。
    - プロジェクトルート検出（.git または pyproject.toml）に基づく .env 自動読み込み機能を実装（`.env` → `.env.local` の順、OS 環境変数を保護）。
    - 自動ロードを無効化する `KABUSYS_DISABLE_AUTO_ENV_LOAD` フラグを用意。
    - `PAPER_FILL_MODE` の妥当性チェック（allowed: instant/partial/never/reject）などのバリデーション。
  - config_setup.py
    - 対話式 .env 作成ウィザードを追加（`python -m kabusys.config_setup`）。
    - 一連の設定項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、LINE 通知設定、LOG_LEVEL、KILL_FLAG_CLEAR_ON_START など）を対話的に生成・保存。
  - validate_config.py
    - 起動前チェック CLI を追加（`python -m kabusys.validate_config`）。
    - 必須環境変数の存在チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と（PyYAML があれば）パース検証、本番時の追加警告等を実施。
    - `--strict` により警告を FAIL として扱うオプションを提供。

- ロギング / プロセス運用ユーティリティ
  - utils/logging_setup.py
    - ルートロガーの初期化ユーティリティを追加。
    - stdout 出力用 StreamHandler と日次ローテーションの TimedRotatingFileHandler（デフォルト logs/<app_name>.log、30 日分保持）を設定。
    - LOG_LEVEL / LOG_DIR / 引数での上書きに対応。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみへフォールバック。
  - utils/process_priority.py
    - プラットフォーム差（Windows / POSIX）を吸収してプロセス優先度（high/normal/low）を設定するユーティリティを追加。
    - CPU affinity 設定ユーティリティを追加（指定がない場合は何もしない）。psutil を利用し権限不足時は警告でスキップ。

- モジュール: portfolio（ポートフォリオ構築）
  - portfolio/portfolio_builder.py
    - 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
    - スコアが全て 0 の場合は等分配へフォールバックして警告を出す。
  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を実装（当日売却予定銘柄を除外可能、"unknown" セクターは無制限扱い）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear 対応、未知レジームはフォールバック）。
  - portfolio/position_sizing.py
    - 各銘柄の株数算出 calc_position_sizes を実装（allocation_method: risk_based / equal / score）。
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap（available_cash でのスケールダウン）、手数料/スリッページのバッファ考慮、残差配分ロジックを実装。

- 監視 / 監査関連
  - monitoring.monitoring_db (参照されている初期化関数) への呼び出しを run_execution と run_monitoring に組み込み。監視テーブルの存在を起動時に保証（冪等）。
  - SystemMonitor を使った単一チェック（monitor.check_once()）をポーリングループで実行（例外は捕捉してログ化し次ポーリングへ継続）。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加（`python -m kabusys.tools.paper_verification_report`）。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率・送信率、リスク却下数、レイテンシ（平均・最大・P95）を算出して標準出力に整形表示。
    - デフォルト閾値（稼働率 >=99%、成立率 >=90%、送信率 >=95%、P95 <=200 ms）を基準に PASS/FAIL 判定を行う。
    - 日付フィルタや DB パス指定オプションをサポート。

- その他
  - research/factor_research.py の骨組み（モメンタム/Value/Volatility/Liquidity の計算方針と定数群）を追加（DuckDB 接続を受け SQL/Python でファクター算出）。
  - パッケージ export（kabusys/__init__.py）で主要サブモジュールを公開。

### Changed

- （初期リリースのため該当なし）

### Fixed

- （初期リリースのため該当なし）

### Security

- （該当なし）

### Notes / 実装上の注意点（ユーザ向け）

- 環境変数自動読み込み
  - デフォルトでプロジェクトルート（.git または pyproject.toml を基準）から `.env` / `.env.local` を自動読み込みします。自動ロードを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
  - OS 環境変数は保護され、`.env.local` の override 時に上書きされません。
- Paper Trading の分離
  - Paper Trading 実行時にはデータファイルが本番監視 DB と分離されるよう考慮されています（デフォルト: data/paper_trading.db）。
- ログディレクトリ
  - `logs/` ディレクトリの作成に失敗するとファイル出力は無効化され、コンソール出力にフォールバックします。権限やパスを確認してください。
- 権限依存の操作
  - process priority や CPU affinity の設定は OS 権限に依存します。権限不足時は警告が出力され操作はスキップされます。

---

今後の想定改善点（参考）
- research/factor_research の完全実装（ファクター計算ロジックの完成）。
- ExecutionEngine / SystemMonitor のユニットテストとより詳細なログ/メトリクス出力。
- 銘柄別 lot_size のサポートやコスト推定の改善（取引手数料・スリッページの経済的推定）。
- 多環境（コンテナ）でのデフォルト設定や運用ドキュメントの整備。

---

[0.1.0]: 0.1.0-2026-04-18