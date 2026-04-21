# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に準拠して記載します。  
このファイルは、リポジトリ内のソースコード内容から推測して作成した初回リリース向けの変更履歴です。

## [Unreleased]

（なし）

---

## [0.1.0] - 初期リリース (推定)

リリース日: 未設定

概要: 日本株自動売買システム "KabuSys" の初期実装。環境設定、監視・実行の起動スクリプト、ポートフォリオ構築／ポジション算出ロジック、ユーティリティ群、検証ツール 等を含む。

### Added（追加）
- 基本パッケージ情報
  - パッケージバージョンを `src/kabusys/__init__.py` に `__version__ = "0.1.0"` として追加。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor を定期ポーリングする監視ループを実装。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止はプロジェクト直下 data/stop_requested.flag によるフラグ検知で実施。
    - 監視用 DB は環境に依らず本番用 sqlite_path を使用して接続。
    - duckdb 接続を併用。
    - monitor.check_once() の例外を捕捉してログ出力しループ継続。

  - run_execution.py
    - ExecutionEngine を起動するスクリプト。
    - KABUSYS_ENV=paper_trading の場合は専用（分離された）SQLite（デフォルト: data/paper_trading.db）を使用。
    - BrokerClientFactory を用いたブローカークライアント生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - PID ファイル / stop フラグ（data/execution.pid、data/stop_requested.flag）を用いた起動・停止制御。
    - エンジンはバックグラウンドスレッドで実行し、停止フラグ検知で安全に停止。

- 設定管理・ウィザード・検証
  - config.py
    - .env の自動読み込み機能（プロジェクトルートの検出: .git または pyproject.toml ベース）。
    - .env のパース強化（export KEY= 値、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理等に対応）。
    - 設定取得ヘルパー `Settings` クラスを提供（各種環境変数のラッパーとバリデーションを実装）。
    - PAPER_FILL_MODE 等の列挙的なバリデーションとパス指定プロパティ（duckdb / sqlite / paper_sqlite 等）。
    - 自動ロードを無効化する `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。

  - config_setup.py
    - .env 用の対話式ウィザードを実装（既存 .env 読み込み、シークレットマスキング、デフォルト提示、保存）。
    - 書き込み時にテンプレート形式で .env を出力（Git コミット禁止の注意喚起を含む）。

  - validate_config.py
    - 起動前チェック用 CLI を提供（必須環境変数、KABUSYS_ENV, LOG_LEVEL, DB パス、config/*.yaml の存在・パース検証等）。
    - PyYAML が無い場合は YAML 検証をスキップして警告出力。
    - --strict オプションで警告を FAIL 扱いにできる。

- ポートフォリオ構築ライブラリ（純粋関数）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルのソートと上位 N 抽出（スコア降順、同点は signal_rank によりブレーク）。
    - calc_equal_weights: 等金額配分を計算。
    - calc_score_weights: スコア加重配分。全銘柄スコアが 0 の場合は等金額にフォールバックして警告。

  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェック（既存保有時価からセクター比率を計算して新規候補を除外）。
      - unknown セクターは上限適用対象外。
      - sell_codes（当日売却予定）をエクスポージャー計算から除外可能。
      - 既知の制約や将来的な価格フォールバックに関する TODO コメントを追加。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear をマッピング、未知値は 1.0 でフォールバック）。

  - portfolio/position_sizing.py
    - calc_position_sizes: 各銘柄の発注株数を計算（allocation_method: risk_based / equal / score）。
      - risk_based: リスク許容率とストップロスを用いた算出。
      - equal / score: 重みに基づく割当て。
      - lot_size（単元株）丸め、per-stock 上限、aggregate cap（利用可能現金を越える場合はスケーリング）を実装。
      - cost_buffer による手数料・スリッページの保守的見積りを考慮。
      - スケール時の端数処理は fractional remainder に基づく再配分で再現性を確保。

- ユーティリティ
  - utils/logging_setup.py
    - 統一ログ設定ユーティリティ（setup_logging）。
    - stdout ストリームハンドラ（StreamHandler）と日次ローテーションの TimedRotatingFileHandler をルートロガーに設定。
    - ログディレクトリ自動作成、作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - ログレベル解決順: 引数 > 環境変数 LOG_LEVEL > デフォルト。
    - ログディレクトリ解決順: 引数 > 環境変数 LOG_DIR > デフォルト (logs/)。
    - ローテーション保存は 30 日分。

  - utils/process_priority.py
    - プロセス優先度設定と CPU affinity 設定を提供（set_process_priority, set_cpu_affinity）。
    - Windows / POSIX（Linux, Darwin, FreeBSD）差分を吸収して動作。psutil を利用。
    - 権限不足・未実装差異は警告でフォールバック。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成ツール。
    - 稼働率、注文成立率（fill rate）、送信率、レイテンシ（平均 / 最大 / P95）等を集計して PASS/FAIL 判定を行う。
    - デフォルト DB は PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）。
    - コマンドライン引数で期間（--from/--to）や DB パス（--db）を指定可能。
    - P95 計算、閾値（稼働率 99%、fill rate 90%、send rate 95%、P95 レイテンシ 200ms）を実装。

- リサーチ基盤（未完）
  - research/factor_research.py
    - ファクター計算モジュールの骨格を追加（モメンタム、MA200 乖離、ATR、流動性等を想定）。
    - DuckDB 接続を受け取り prices_daily / raw_financials テーブルを参照して計算する設計。
    - 実装の一部（calc_momentum の先頭）が存在するが、ファイル末尾は未完（途中で切れていることを確認）。

### Changed（変更）
- 監視/実行スクリプトの挙動
  - 監視ループは MONITOR_POLL_INTERVAL の不正値（0 や文字列など）を検出してデフォルトへフォールバックし、警告ログを出す実装に改善。
  - run_execution は paper_trading 環境時に専用 DB を利用して本番 DB と完全分離する動作を明記・実装。

- 設定読み込みの堅牢化
  - .env のパース挙動を細かく制御（クォート内のエスケープ、インラインコメント処理）して実運用での柔軟性を向上。

### Fixed（修正 / 安全対策）
- プロセスの安全停止処理
  - run_execution と run_monitoring 両方で停止フラグ検知と KeyboardInterrupt をハンドリングして、DB 接続やリソースを確実にクローズするように改善。

- ログ二重設定の回避
  - setup_logging で既存ハンドラを flush/close してから削除し、重複したハンドラ設定を防止。

### Known issues / TODO（既知の問題・今後の課題）
- research/factor_research.py が途中で切れており、モメンタム等の計算ロジックが未完。
- risk_adjustment.apply_sector_cap の価格欠損（price == 0.0）に対するフォールバック（前日終値や取得原価など）が未実装（TODO コメントあり）。
- position_sizing の将来拡張: lot_size を銘柄毎に持たせる設計（stocks マスタの導入など）が検討項目として残る。
- 一部外部ライブラリ依存（psutil, duckdb, PyYAML）が存在し、未インストール時の挙動は警告スキップでフォールバックしているが、完全機能を使うには依存関係の整備が必要。

---

注意:
- 本 CHANGELOG は与えられたソースコードから機能・振る舞いを推測して作成したものであり、実際のリリース履歴やコミット単位の変更履歴とは異なる場合があります。必要に応じて変更履歴をコミット履歴に基づいて更新してください。