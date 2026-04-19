# Changelog

All notable changes to this project will be documented in this file.

The format is based on "Keep a Changelog" and this project adheres to Semantic Versioning.

## [0.1.0] - 初期リリース
（初回公開。コードベースの機能追加をまとめています）

### Added
- 基本パッケージ構成を実装
  - パッケージ名: kabusys
  - バージョン: __version__ = "0.1.0"

- 環境設定・管理
  - Settings クラス（kabusys.config）を実装し、環境変数から各種設定値を取得する仕組みを提供。
    - J-Quants / kabuステーション / LINE / DB パス / 監視閾値 等のプロパティを用意。
    - KABUSYS_ENV, LOG_LEVEL 等の値チェックと変換を行う。
    - is_live / is_paper / is_dev のユーティリティプロパティを提供。
  - .env 自動読み込み機能を実装
    - プロジェクトルート（.git または pyproject.toml）を基準に .env / .env.local を自動ロード。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - .env パーサ（引用符・export・行末コメント対応）を実装し、より堅牢に環境変数を読み込むようにした。

- 対話式設定ウィザード
  - kabusys.config_setup: .env の初期作成・更新を対話式で支援する CLI を追加。
    - 一連の設定項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DB パス 等）を対話で入力し .env を生成。
    - 秘匿項目はマスク表示、既存値の再利用、保存確認を実装。

- 設定検証ツール
  - kabusys.validate_config: 起動前に .env および config/*.yaml の妥当性をチェックする CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV 値チェック、ログレベルチェック、DB パスの親ディレクトリチェック、YAML パースチェック（PyYAML がある場合）など。
    - --strict モードで警告をエラー扱いにできる。

- 実行エンジン起動スクリプト
  - run_execution.py を追加。
    - プロセス優先度を設定（High）。
    - 環境に応じて paper_trading 用の専用 SQLite（data/paper_trading.db）を使用し、本番 DB と分離。
    - DuckDB 接続を確保。
    - BrokerClientFactory によるブローカークライアント生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler の組み立てを行い、ExecutionEngine をスレッドで起動。
    - stop フラグ（data/stop_requested.flag）検出時に Engine を停止する仕組みを実装。
    - 実行中の PID を記録する PID ファイルのサポート。

- 監視プロセス起動スクリプト
  - run_monitoring.py を追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告してデフォルトへフォールバック。
    - 監視は環境に関係なく本番用の sqlite_path を使用して監視 DB を初期化。
    - SystemMonitor を用いた polling ループ、停止フラグ検出、例外捕捉および後始末（DB クローズ）を実装。

- ロギング基盤
  - kabusys.utils.logging_setup.setup_logging を実装。
    - stdout へ StreamHandler、日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log）をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR / 引数による上書きをサポート。
    - ログディレクトリ作成失敗時はファイルハンドラをスキップしてコンソール出力のみで継続。

- プロセス優先度・CPU affinity ユーティリティ
  - kabusys.utils.process_priority を実装。
    - set_process_priority(level) で Windows / POSIX を吸収した優先度設定を試みる（失敗時は警告でスキップ）。
    - set_cpu_affinity(cpu_count) で最初の N コアにプロセスを固定する機能（許可がない場合は警告でスキップ）。
    - クロスプラットフォーム対応（Windows/Linux/macOS/FreeBSD 等を考慮）。

- ポートフォリオ構築（純粋関数群）
  - kabusys.portfolio パッケージを追加。
    - portfolio_builder: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア配分（calc_score_weights）を実装。スコアが全て 0 の場合は等分配にフォールバック。
    - risk_adjustment: セクター上限適用（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。未知レジームはフォールバックと警告。
      - セクター不明（"unknown"）は上限判定の対象外とする仕様。
    - position_sizing: 株数計算（calc_position_sizes）を実装。
      - allocation_method="risk_based" / "equal" / "score" をサポート。
      - lot_size（単元株）で丸め、1 銘柄上限・合計投下上限（available_cash）を考慮。
      - cost_buffer を用いた保守的コスト見積り、投下超過時のスケーリングと端数分配ロジックを実装。

- リサーチ / ファクター計算（骨子）
  - kabusys.research.factor_research にモメンタム等のファクター計算モジュールを追加（DuckDB を用いた prices_daily/raw_financials の参照を前提）。
    - モメンタム計算（calc_momentum）の設計と定数（1M/3M/6M、MA200、ATR など）を定義。
    - （ファイルは設計コメントと一部実装が含まれるが、calc_momentum の実装は続きがある想定）

- ペーパートレード検証レポート
  - kabusys.tools.paper_verification_report を追加。
    - PAPER_TRADING_SQLITE_PATH（または --db）から DB を読み、システム稼働率・注文成功率・送信率・レイテンシ（P95 等）・リスク却下数を集計して標準出力レポートを生成。
    - 閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）で PASS/FAIL 判定を行う。
    - P95 計算や期間フィルタ（ISO8601 UTC 形式）を実装。

- DB 初期化ユーティリティ
  - monitoring 用 DB テーブルの初期化（init_monitoring_db）を run 系スクリプトから適切に呼び出すことで冪等に初期化する処理を組み込んでいる（実装ファイルは別モジュールに存在）。

### Changed
- なし（初期リリース）

### Fixed
- なし（初期リリース）

### Notes / Implementation details
- run_monitoring と run_execution は共にプロセス優先度を最初に set_process_priority("high") してから各種初期化を行う設計になっています。
- run_execution は paper_trading モードでは専用の SQLite を使用することで本番 DB と完全分離を図っています。
- .env の読み書きは Git へコミットしない旨の注記を config_setup に含めています。
- ログ出力は stdout へ流すようにしているため、cron や Task Scheduler 等で stdout/stderr を一本化して使う運用に配慮しています。
- 一部関数や箇所に TODO コメント（例: price フォールバック、銘柄別 lot_size など）が残っており将来の拡張方針が示されています。

---

今後のリリースでは以下を想定しています（例）:
- research.factor_research の完全実装とテスト追加
- ExecutionEngine / BrokerClient の詳細実装・テストケース
- CI/CD、型チェック、より詳細なドキュメントの追加

もし CHANGELOG に特に含めたい追加点（例: リリース日や特定のコミット参照）があれば教えてください。必要に応じて日付やセクションを更新します。