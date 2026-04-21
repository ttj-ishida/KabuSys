# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に従います。  
このファイルはコードベースから推測して作成しています（実装コメント・挙動・ファイル構成に基づく記述）。

現在のバージョン: 0.1.0

## [Unreleased]

（未リリースの変更はありません）

## [0.1.0] - 2026-04-21

初回リリース。本リポジトリは日本株自動売買システム KabuSys のコアユーティリティ群と実行・監視用スクリプト、ポートフォリオ構築ロジック、検証ツールなどを含みます。

### Added
- 基本パッケージ情報
  - パッケージメタ情報を追加（src/kabusys/__init__.py, __version__="0.1.0"）。

- 実行用スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視実行時はモニタリング用 DB を初期化（init_monitoring_db 呼び出し）。
    - 停止フラグ（data/stop_requested.flag）検知で安全にループ終了。
    - 例外発生時は例外をログに出力して次のポーリングへ継続。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計。

  - run_execution.py
    - ExecutionEngine を起動するスクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合、Paper Trading 用 SQLite（data/paper_trading.db 相当）を使用し、本番 DB と分離。
    - BrokerClientFactory を使ってブローカークライアントを生成（モック/本番切替）。
    - PID ファイル管理（data/execution.pid）と停止フラグ検知による安全停止。
    - ExecutionEngine を別スレッドで動かし、停止フラグで engine.stop() を呼び出して終了。

- 設定管理・検証・ウィザード
  - config.py
    - .env 自動読み込み機能（プロジェクトルートを .git / pyproject.toml で判定）。
    - .env / .env.local の読み込みルール（OS環境変数を保護して上書き制御）。
    - .env の行パーサ（export 形式、クォート、エスケープ、インラインコメント等に対応）。
    - Settings クラスを提供し、環境変数の型変換／バリデーション（env, log_level, PAPER_FILL_MODE 等）を実装。
    - paper_sqlite_path / sqlite_path / duckdb_path など各種パス取得ユーティリティを提供。

  - config_setup.py
    - 対話式 .env 作成・更新ウィザードを追加。
    - 入力項目一覧（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH 等）を定義し、既存 .env の読み込み／マスク表示、確認後保存機能を実装。
    - .env ファイル書き込み時のテンプレートコメントを整備。

  - validate_config.py
    - 起動前チェック CLI を追加（必須環境変数の存在確認、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パス・config YAML ファイルの確認、live 環境向けの追加ガードなど）。
    - --strict オプションで警告を FAIL 扱いにする機能。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py
    - すべての起動スクリプトで共通利用可能なロギング設定を提供。
    - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler、30日保持）を設定。
    - LOG_DIR / LOG_LEVEL の解決順、既存ハンドラのクリア等を実装。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続するフェイルセーフを導入。

  - utils/process_priority.py
    - プロセス優先度（"high"/"normal"/"low"）をクロスプラットフォームに設定するユーティリティを追加（Windows の priority class / POSIX の nice）。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供。
    - 権限不足時や未対応 OS の場合は警告を出してスキップする堅牢な設計。

- ポートフォリオ構築モジュール（純粋関数群、メモリ処理）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコアでソートして上位 N を選択。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア加重配分（スコア総和が 0 の場合は等金額にフォールバックし警告）。

  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限を適用して候補を除外するロジック（unknown セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた資金乗数を返す（未知レジームは警告を出してフォールバック）。

  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づく発注株数計算。
    - 単元（lot_size）丸め、1銘柄上限、aggregate cap（available_cash）でのスケーリング、cost_buffer を考慮した安全なスケールダウン実装を追加。
    - ログ出力で価格欠損時にスキップする旨を通知。

  - portfolio/__init__.py で主要関数を再エクスポート。

- リサーチ / ファクター計算
  - research/factor_research.py
    - DuckDB を用いるファクター計算モジュールを追加（モメンタム／MA200偏差／ATR／流動性等を想定）。
    - モメンタム計算関数 calc_momentum の雛形と定数を実装（実装途中の箇所あり）。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）から検証指標（稼働率、注文成功率、送信率、レイテンシ P95 等）を集計してレポート表示する CLI を追加。
    - デフォルトしきい値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200 ms）を定義し PASS/FAIL 判定を実装。
    - 日付フィルタ（--from / --to）や --db オプションをサポート。

- 監視 DB 初期化の共通化
  - monitoring.monitoring_db.init_monitoring_db を実行して監視用テーブルが存在することを保証（冪等）。

- DuckDB 統合
  - 実行・監視・リサーチで DuckDB 接続を利用する設計（duckdb_path 設定で管理）。

### Changed
- 設計上の注意点・デフォルト振る舞いを明確化
  - run_monitoring は環境変数 KABUSYS_ENV にかかわらず本番 sqlite_path を監視対象として使用する旨の注記を追加（運用上の安全措置/設計判断として明示）。
  - run_execution は paper_trading モード時に paper_sqlite_path を使用して本番 DB と完全分離する設計を採用。

### Fixed
- エラーハンドリングとフェイルセーフ強化
  - MONITOR_POLL_INTERVAL の不正な値（0, 負数, 非整数）に対して警告を出しデフォルト値にフォールバックする処理を実装（run_monitoring）。
  - logging_setup でログディレクトリ作成失敗時にファイル出力をスキップし、コンソール出力を継続するように変更（ファイル作成権限がない環境での堅牢化）。
  - process_priority の優先度設定で権限不足や未実装 API を捕捉して警告ログを出すようにしてクラッシュを回避。

### Security
- 秘匿情報の扱い
  - config_setup の対話ウィザードでシークレット項目（J-Quants リフレッシュトークン、kabu API パスワード 等）をマスク表示して管理。
  - .env 作成時に「.env は絶対に Git にコミットしないこと」を明示。

### Notes / Known limitations
- research/factor_research.calc_momentum の実装は途中の箇所（ソース末尾が途切れている）があります。完全なファクター計算を行うには追加の実装が必要です。
- position_sizing の lot_size は現状グローバル固定（デフォルト 100）。将来的に銘柄別単元サポートを検討する旨の TODO コメントあり。
- apply_sector_cap は price_map に欠損（0.0）がある場合にエクスポージャーが過少見積りされる可能性があるという注意書きがあり、将来的にフォールバック価格の導入を検討する設計。

---

今後のリリース案内（例）
- 0.1.x: factor_research の完実装、ユニットテスト追加、CI／パッケージング改善
- 0.2.0: ExecutionEngine の詳細実装、OrderManager / Reconciler の拡張、戦略モデル連携

（この CHANGELOG はコードベースの実装内容から推測して作成しています。実際の変更履歴やリリースノートはプロジェクトの Git 履歴に基づいて更新してください。）