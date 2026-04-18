CHANGELOG
=========

この変更履歴は「Keep a Changelog」形式に準拠しています。  
日付や分類はコードベースから推測して記載しています。

## [Unreleased]

- 進行中 / 注意事項
  - research/factor_research.py はモメンタム等ファクター計算の実装を開始しているが、途中で切れている（未完）。追加実装が必要。
  - 一部の TODO コメント（価格フォールバックなど）が残っており、将来的な機能拡張・改善の余地あり。

---

## [0.1.0] - 2026-04-18

初回リリースとして以下の機能群を追加・整備しました（コードベースの内容から推測）。

### Added
- 基本アプリケーション情報
  - パッケージバージョンを __version__ = "0.1.0" として定義。

- 環境/設定管理
  - .env 自動読み込み機能:
    - プロジェクトルート（.git または pyproject.toml を探索）を基準に .env/.env.local を自動読込（OS 環境変数優先、.env.local は上書き）。
    - 読み込み無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env パーサ実装:
    - export プレフィックス対応、クォート文字列（シングル/ダブル）内のエスケープ処理、インラインコメント処理をサポート。
    - protected パラメータで OS 環境変数の上書きを防止。
  - Settings クラス:
    - 環境変数アクセスラッパー（J-Quants / kabu / LINE / DB パス / 監視閾値 / 実行環境判定等）。
    - PAPER_FILL_MODE の検証ロジック、paper_trading 用 sqlite パスなどを提供。

- 環境セットアップ & 検証 CLI
  - config_setup.py:
    - 対話式ウィザードで .env を作成・更新する CLI を提供（項目: KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE 設定等）。
    - シークレット項目はマスク表示、保存前確認を実装。
  - validate_config.py:
    - 起動前検証 CLI を提供（必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 値チェック、DB パスの親ディレクトリ存在確認）。
    - config/*.yaml の存在確認および PyYAML があればパース検証を実施。
    - --strict オプションで警告を FAIL 扱いにできる。

- 実行用エントリスクリプト
  - run_execution.py:
    - ExecutionEngine 起動スクリプトを提供。
    - KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite（デフォルト data/paper_trading.db）を使用して本番 DB と完全分離。
    - BrokerClientFactory を用いたブローカクライアント生成（実環境 / モックの切替想定）。
    - PID ファイル管理、停止フラグ（data/stop_requested.flag）による安全停止。
    - スレッドでエンジン実行、停止フラグ検知で engine.stop() を呼び出してシャットダウン。
  - run_monitoring.py:
    - SystemMonitor 用のポーリングループ起動スクリプトを提供。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、1 未満は無効としてフォールバック）。
    - 監視（monitoring）用の DB は環境に関係なく本番 sqlite_path を使用する旨の設計（監視は本番対象）。
    - stop フラグの検知と KeyboardInterrupt ハンドリング、接続クローズを確実に実施。

- ロギング / プロセス管理ユーティリティ
  - utils/logging_setup.py:
    - 共通ロギング初期化関数 setup_logging を提供。
    - stdout への StreamHandler と日次ローテート（TimedRotatingFileHandler）を設定。ログディレクトリ自動作成と失敗時のフォールバックを実装。
    - ログレベル・ログディレクトリ解決ルール（引数 > 環境変数 > デフォルト）。
  - utils/process_priority.py:
    - クロスプラットフォームでのプロセス優先度設定（Windows の priority class / POSIX の nice）。
    - CPU affinity 設定用の set_cpu_affinity 関数を提供（必要に応じて最初 N コアに固定）。
    - 権限不足や未対応 OS の場合は警告を出して安全にスキップ。

- ポートフォリオ構築ロジック（純関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルをスコア降順で上位 N 件選定。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア比率で重み計算（全銘柄スコアが 0 の場合は等金額へフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: 既存保有を考慮したセクター集中上限チェック（上限超過セクターの候補除外）。
    - calc_regime_multiplier: market regime に基づく投下資金乗数（bull/neutral/bear をマッピング、未知レジームはフォールバックと警告）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づき発注株数を計算。
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap（available_cash を超える場合はスケールダウン）を実装。
    - cost_buffer を用いた保守的コスト見積り、残差に基づく再配分ロジック（lot 単位で配分）。

- Paper Trading 用検証ツール
  - tools/paper_verification_report.py:
    - Paper Trading 用 SQLite（デフォルト data/paper_trading.db）からレポートを生成する CLI を提供。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率(send rate）、P95 レイテンシ等。
    - 閾値による PASS/FAIL 判定（稼働率 >= 99%、fill_rate >= 90%、send_rate >= 95%、P95 <= 200ms）。
    - 日付フィルタ（--from / --to）対応、DB 存在チェック、SQL の実行で欠損テーブルを扱えるフォールバック処理。

- monitoring DB 初期化
  - monitoring/monitoring_db.init_monitoring_db を run_* スクリプトから呼び出し、監視テーブルの存在を冪等に保証。

### Changed
- 設計的な決定
  - run_monitoring は KABUSYS_ENV にかかわらず "本番" の sqlite_path を使用して監視データを記録（監視は環境分離しない方針）。
  - run_execution は paper_trading 実行時に本番 DB と分離する設計。

### Fixed / Robustness
- .env 読み込みで I/O エラー時に警告を出して処理継続。
- logging_setup でログディレクトリ作成失敗時にファイル出力をスキップし、標準出力のみで継続するように改善。
- process_priority と CPU affinity の例外ケース（AccessDenied, NotImplementedError 等）を捕捉して警告でスキップするように安全化。
- run_execution/run_monitoring の finally ブロックで DB 接続を確実にクローズするよう実装。

### Notes / Known limitations
- portfolio.position_sizing の価格が欠損（0.0）の場合、現在はスキップするのみで、将来的に前日終値や取得原価でのフォールバックが必要（TODO コメントあり）。
- research/factor_research.py はファクター計算のフレームワークを実装途中で終了しており、完全な動作には追加実装が必要。
- BrokerClientFactory や ExecutionEngine 等の内部実装（発注ロジック、MockBroker の具体挙動）はここに含めたコードからは詳細不明（外部モジュールに依存）。

---

作成者注:
- 上記は配布されているソースコードの内容から推測してまとめた CHANGELOG です。実際のコミット履歴やリリースノートがある場合は、それに合わせて調整してください。