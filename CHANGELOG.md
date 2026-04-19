CHANGELOG
=========

すべての注目すべき変更点を記録します。  
このドキュメントは「Keep a Changelog」方式に準拠しています。

0.1.0 - 2026-04-19
-----------------

Added
- 初期リリース: kabusys パッケージのベース機能を実装。
- 実行／監視用スクリプト
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - プロセス優先度を高 (high) に設定して起動。
    - KABUSYS_ENV=paper_trading の場合は専用のペーパートレード用 SQLite (デフォルト: data/paper_trading.db) を使用し、本番 DB と分離。
    - BrokerClientFactory 経由でブローカークライアントを生成（テスト用 Mock の切替を想定）。
    - 実行中は daemon スレッドで engine.run_session を実行し、data/stop_requested.flag による外部停止要求を監視。
    - PID ファイル (data/execution.pid) をサポート。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出力。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計。
    - 外部の停止フラグファイル (data/stop_requested.flag) による優雅な終了処理を実装。
- 設定管理
  - config.py
    - .env 自動読み込み機構を実装（プロジェクトルートを .git または pyproject.toml で探索）。
    - .env のパースを robust に実装（export プレフィックス、シングル／ダブルクォート内のエスケープ、インラインコメントの扱い等に対応）。
    - Settings クラスを追加し、環境変数をプロパティ経由で取得（各種パス、閾値、paper_trading 関連設定、PAPER_FILL_MODE の検証など）。
    - is_live / is_paper / is_dev の簡易フラグを提供。
- 設定関連 CLI
  - config_setup.py
    - .env の対話的ウィザードを実装（既存 .env 読み込み、シークレットのマスク表示、保存処理）。
    - .env を自動生成するヘッダとフィールドテンプレートを用意。
  - validate_config.py
    - 起動前検証 CLI を実装（必須環境変数チェック、KABUSYS_ENV 検証、DB パス・YAML ファイルの存在チェック、KABUSYS_ENV=live 時の追加ガード等）。
    - --strict フラグで警告を失敗扱いにできる。
- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py
    - シグナル選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。
    - スコアが全て 0 の場合は等金額配分にフォールバックして警告出力。
  - portfolio/risk_adjustment.py
    - セクター集中制限適用関数 apply_sector_cap を実装（既存保有のセクター比率を計算して新規候補を除外）。
    - 市場レジームに応じた資金乗数 calc_regime_multiplier を実装（bull/neutral/bear をマップ）。
  - portfolio/position_sizing.py
    - position sizing（risk_based / equal / score）を実装。
    - 単元株（lot_size）丸め、1 銘柄上限・aggregate cap（利用可能現金を超える場合のスケーリング）、cost_buffer による保守的見積りを実装。
    - aggregate スケールダウン時に残余キャッシュで端数を lot_size 単位で再配分するロジックを実装。
- ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション）を設定する共通ユーティリティを追加。
    - LOG_DIR/LOG_LEVEL 環境変数や引数による上書きに対応。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
  - utils/process_priority.py
    - Windows / POSIX（Linux/Mac 等）の差分を吸収してプロセス優先度を設定するユーティリティを追加。
    - set_cpu_affinity により最初の N コアに固定する機能を提供（プラットフォームや権限により失敗した場合は警告を出力してスキップ）。
- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成 CLI を追加。稼働率、注文成功率、送信率、P95 レイテンシ等の指標を集計し PASS/FAIL 判定を行う。
    - デフォルト DB パスは data/paper_trading.db。コマンドラインで期間や DB パスを指定可能。
- research
  - research/factor_research.py
    - ファクター計算モジュールの骨格（モメンタム、MA200、ATR、出来高系などの設計と定数）を実装開始。DuckDB を使ったデータ参照を想定。

Changed
- なし（初期リリース）。

Fixed / Robustness
- run_monitoring の MONITOR_POLL_INTERVAL の不正値を検出してデフォルトへフォールバックし、警告を出力するように実装。
- logging_setup: ログディレクトリ作成失敗時でもアプリが起動するように StreamHandler のみで継続する設計にして堅牢化。
- process_priority および set_cpu_affinity: 権限不足や未対応プラットフォーム時に例外で停止しないよう try/except で警告を出す実装に変更。
- init_monitoring_db は冪等に呼べるように配置（monitoring テーブル存在を保証）。

Security
- .env を .git にコミットしない旨を config_setup のヘッダに明記。

Notes / Known issues / TODO
- portfolio/risk_adjustment.apply_sector_cap:
  - price_map に価格が欠損 (0.0) の場合、エクスポージャーが過小見積もりされる可能性あり（コード内に TODO を記載）。前日終値等のフォールバック実装を検討する必要あり。
- portfolio/position_sizing:
  - lot_size は現状グローバル固定。将来的に銘柄別の lot_map を受け取る設計へ拡張する旨の TODO を残している。
- research/factor_research は実装が途中で切れている箇所がある（momentum 計算の続きが未収録）。今後の実装で各ファクター計算ルーチンを完成させる必要あり。
- 一部外部依存（psutil・duckdb・PyYAML 等）が存在する。環境によりインストールと設定が必要。

License
- （リポジトリの LICENSE に従ってください）

--- 

注: 本 CHANGELOG は提供されたソースコードから推測して作成しています。実際のリリースノート作成時は変更差分 (git diff / commit history) に基づいて調整してください。