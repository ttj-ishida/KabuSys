KEEP A CHANGELOG
All notable changes to this project will be documented in this file.

フォーマットは Keep a Changelog に準拠しています。  
解釈や実装の詳細はソースコードの docstring / コメントを参照してください。

Unreleased
---------
- なし

0.1.0 - 2026-04-23
------------------
Added
- 実行用スクリプトを追加
  - run_execution.py
    - ExecutionEngine を起動するエントリポイントを提供。
    - KABUSYS_ENV に応じて paper_trading 用の専用 SQLite（data/paper_trading.db）を使用する分離を実装。
    - BrokerClientFactory 経由でブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立ててエンジンをスレッドで実行。
    - 停止フラグ (data/stop_requested.flag) の検知によるセーフシャットダウン、PID ファイルの利用、プロセス優先度設定を実装。
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はロギング後デフォルトへフォールバック。
    - 監視は環境に関係なく production 用 sqlite_path を使用する設計。
    - 停止フラグ検知・例外耐性・duckdb 接続のクローズ処理を実装。

- 設定関連
  - config.py
    - Settings クラスを追加：各種環境変数をプロパティとして取得（DB パス、KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE など）。
    - .env 自動読み込み機能を追加（プロジェクトルートの .env/.env.local をロード、OS 環境変数優先）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
    - .env のパース処理を堅牢化（export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理など）。
    - PAPER_FILL_MODE の検証（有効値: instant/partial/never/reject）と paper_sqlite_path プロパティを追加。
    - 各種閾値プロパティ（cpu/memory/disk）や kill_flag 関連プロパティを追加。

- 設定・検証 CLI
  - config_setup.py
    - 対話式ウィザードを追加。.env の初期作成・更新を支援する。
    - デフォルト値表示・既存値利用（Enter で継続）・シークレットのマスク表示・保存確認を実装。
  - validate_config.py
    - 環境変数と config/*.yaml ファイルの検証 CLI を追加。
    - 必須環境変数のチェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェックを実装。
    - PyYAML がある場合は YAML のパースチェックを行う。--strict オプションで警告を FAIL 扱いにできる。
    - KABUSYS_ENV=live における本番向けガード（LINE 通知設定や Kill Switch 設定の警告）を追加。

- レポートツール
  - tools/paper_verification_report.py
    - ペーパートレード結果検証レポート生成ツールを追加。
    - system_status / trade_logs / risk_logs などから稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）を算出。
    - P95 計算、日付フィルタ、閾値（稼働率 99%、成功率 90%、送信率 95%、P95 200 ms）に基づく PASS/FAIL 判定を実装。
    - コマンドライン引数 --from/--to/--db をサポート。

- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py
    - 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
    - calc_score_weights は全てのスコアが 0 の場合に等配分へフォールバック。
  - portfolio/risk_adjustment.py
    - セクター集中上限適用（apply_sector_cap）を実装。既存保有からセクター別エクスポージャを算出し、上限超過セクターの新規候補を除外。
    - unknown セクターは上限判定から除外して除外しない挙動とした。
    - 市場レジームに応じた乗数（calc_regime_multiplier）を実装（bull:1.0, neutral:0.7, bear:0.3）。未知レジームは警告を出して 1.0 にフォールバック。
  - portfolio/position_sizing.py
    - allocation_method（risk_based / equal / score）に応じた株数計算を実装。
    - risk_based: ポジション当たりのリスクベースで目標株数を計算（risk_pct, stop_loss_pct を使用）。
    - equal/score: weight に基づく割当。
    - lot_size（単元）で丸め、1 銘柄上限（max_position_pct）、aggregate cap（available_cash）を考慮したスケーリング、cost_buffer を使った保守的見積り、端数調整（残余キャッシュで lot 単位の再配分）を実装。

- ユーティリティ
  - utils/logging_setup.py
    - 統一的なログ初期化を提供する setup_logging() を追加。
    - stdout への StreamHandler（stdout を使用）と日次ローテーションの TimedRotatingFileHandler（ログディレクトリ作成失敗時はファイル出力を無効化）を設定。
    - ログレベル・ログディレクトリの解決順を定義。
  - utils/process_priority.py
    - クロスプラットフォーム（Windows / POSIX）でプロセス優先度設定を行う set_process_priority(level) を実装。
    - CPU affinity を設定する set_cpu_affinity(cpu_count) を追加。
    - psutil を用い、権限や未対応 OS の場合は警告を出してスキップする安全設計。

- パッケージ情報
  - __init__.py に __version__ = "0.1.0" を追加。

Changed
- ロギングのデフォルト挙動
  - ログは stdout に出力するように統一（cron / Task Scheduler からの起動での扱いやすさのため）。
  - ログファイルはデフォルト logs/ に日次ローテーションで出力。ディレクトリ作成失敗時はコンソールのみで継続。
- .env 読み込み順序は OS 環境 > .env.local > .env とし、OS 環境変数は保護（上書き不可）に変更。
- run_monitoring / run_execution でプロセス優先度を起動直後に High に設定するよう共通化。

Fixed
- calc_score_weights: 全銘柄スコアが 0 の場合に 0 除算や不正な重み分配が発生するのを防止し、等金額配分へフォールバックするよう修正。
- _get_poll_interval(): MONITOR_POLL_INTERVAL の不正値（0 以下や非整数）を検出して警告を出しデフォルト 60 秒にフォールバック。
- apply_sector_cap: unknown セクターの扱いを明確化（既存設計：unknown は除外判定対象外）。
- logging_setup: ログディレクトリ作成に失敗した場合も、StreamHandler のみで安全に継続するよう改善。
- process_priority: 未対応 OS や権限不足による例外をキャッチして警告を出すよう改善。

Known limitations / Notes
- research/factor_research.py はファクター計算の骨子（momentum 等の定義、DuckDB 接続を前提）を含むが、ファイル末尾が途中で切れており実装が未完了（スキャフォールド段階）。
- 一部の TODO コメント（例: position_sizing の銘柄別 lot_size サポート、price フォールバック）あり。将来的に拡張を予定。
- 実行時に必要な外部依存 (psutil, duckdb, PyYAML 等) は環境にインストールしておく必要がある。validate_config は PyYAML 未導入時に YAML 検証をスキップする。

License
- プロジェクトのライセンス表記はソースに含まれていません。配布前に LICENSE を追加してください。