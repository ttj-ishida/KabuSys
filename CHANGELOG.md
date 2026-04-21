# CHANGELOG

すべての重要な変更は Keep a Changelog の仕様に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

注: 以下の変更点は提供されたソースコードの内容から推測して作成したものです。実際のコミット履歴ではなく、機能実装の概要・設計意図をまとめたリリースノート的な記述です。

## [Unreleased]

- 開発中 / 未リリースの変更はここに記載します。

---

## [0.1.0] - 2026-04-21

初回リリース。シンプルな日本株自動売買システムの基盤機能を実装しました。主な追加点は以下の通りです。

### Added
- 全体
  - パッケージ初期版を追加。パッケージバージョンは `kabusys.__version__ = "0.1.0"`。
  - モジュール群を整備し、実行スクリプト・ユーティリティ・ポートフォリオ構築・リサーチなどの基盤を提供。

- 実行関連スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを実装。
    - KABUSYS_ENV に応じた DB 分離:
      - `paper_trading` 環境では MockBrokerClient を使用し、`data/paper_trading.db`（`PAPER_TRADING_SQLITE_PATH` で上書き可）に記録する設計。
      - 本番環境（live / default）は本番用 SQLite を使用。
    - プロセス優先度を起動時に `high` に設定する処理を組み込み（utils.process_priority）。
    - 停止フラグ（data/stop_requested.flag）による外部停止に対応。PID ファイルの扱いもサポート。

  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプトを実装。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。不正値時にデフォルトへフォールバックするロジックあり。
    - Monitoring は環境にかかわらず本番の sqlite_path を参照する仕様（監視データは本番 DB に集約）。

- 設定管理
  - config.py
    - 環境変数 / .env の自動読み込み機能を実装（プロジェクトルートを .git / pyproject.toml から検出）。
    - `.env` / `.env.local` の読み込み順と OS 環境変数の保護（上書き禁止）を実装。
    - 複数の設定プロパティ（DB パス、API トークン、監視閾値、環境判定など）をラッパークラス Settings として提供。
    - `PAPER_FILL_MODE` の検証、`KABUSYS_ENV` / `LOG_LEVEL` の妥当性チェックなどを実装。

  - config_setup.py
    - 対話式ウィザードで .env を生成・更新する CLI を提供。シークレット項目はマスク表示。生成テンプレートの書き出しに対応。

  - validate_config.py
    - 起動前に .env と config/*.yaml を検証する CLI を提供。
    - 必須環境変数の検出、パス存在チェック、YAML パース（PyYAML があれば内容検証）や、本番環境時の追加ガードチェックを実装。
    - `--strict` オプションで警告を失敗扱いにできる。

- ロギング / プロセス管理ユーティリティ
  - utils/logging_setup.py
    - 全アプリ共通のロギング初期化ユーティリティを実装。
    - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler、30 日保持）をルートロガーに設定。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。
    - LOG_LEVEL / LOG_DIR の環境変数に対応。

  - utils/process_priority.py
    - Windows / POSIX を抽象化したプロセス優先度設定を実装（`set_process_priority("high"|"normal"|"low")`）。
    - CPU affinity 設定ユーティリティ `set_cpu_affinity` を提供（コア数指定で最初の N コアに固定）。
    - 許可エラーや未対応環境は警告でスキップする堅牢性設計。

- ポートフォリオ構築
  - portfolio/portfolio_builder.py
    - 候補選定 (`select_candidates`)、等配分重み (`calc_equal_weights`)、スコア加重 (`calc_score_weights`) を実装。
    - `calc_score_weights` は全スコアが 0 の場合に等配分へフォールバックし警告を出す。

  - portfolio/risk_adjustment.py
    - セクター集中制限 (`apply_sector_cap`) を実装。既存保有のセクター別時価で上限を判定し、上限超過のセクターの新規候補を除外。
    - レジーム乗数 (`calc_regime_multiplier`) を実装（bull/neutral/bear -> 1.0/0.7/0.3、未知レジームはフォールバックして 1.0）。

  - portfolio/position_sizing.py
    - 発注株数算出ロジックを実装（allocation_method: risk_based / equal / score）。
    - 単元（lot_size）丸め、1銘柄上限、aggregate cap（available_cash に基づくスケーリング）、cost_buffer（手数料・スリッページ見積）を考慮した安全なスケーリングアルゴリズムを実装。
    - スケーリング時の端数配分は残差の大きい順に lot_size 単位で配分するロジックを導入。

- リサーチ / ファクター計算
  - research/factor_research.py（基礎実装）
    - Momentum / Value / Volatility / Liquidity 系ファクター計算の設計と一部実装を追加。
    - DuckDB 接続を受け取り prices_daily / raw_financials を参照して計算する方針。
    - P95 計算や移動平均などの計算に対応するユーティリティを実装予定（momentum の実装が作成中）。

- ツール
  - tools/paper_verification_report.py
    - ペーパートレーディング結果検証レポート生成ツールを実装。
    - システム稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）を集計し PASS/FAIL を判定する簡易レポート機能。
    - デフォルト閾値（稼働率 99%、注文成立率 90%、送信率 95%、P95 レイテンシ 200 ms）を設定。
    - 日付フィルタ（--from, --to）と DB パスオプション（--db）に対応。

### Changed
- 設定読み込み
  - .env のパースを改善（`export KEY=val`、クォート内のバックスラッシュエスケープ、インラインコメントの扱い、未設定時のデフォルト挿入などに対応）。
  - 自動 .env ロードはプロジェクトルートが特定できない場合にスキップするように変更（配布後の動作安定化を考慮）。

- ログ出力
  - StreamHandler を stderr ではなく stdout に向ける方針を採用（cron/タスクスケジューラでのリダイレクトを想定）。

### Fixed
- 安全性 / 堅牢性
  - ポーリング間隔環境変数の不正値（0 以下や非数）が指定された場合にデフォルトにフォールバックするようにして、time.sleep に渡して例外が出ることを防止。
  - DB テーブル未作成時に監視テーブルを保証するため init_monitoring_db を呼ぶ処理を追加（冪等的にテーブルを作成）。

### Known limitations / Notes
- research/factor_research.py の一部（momentum 計算の続き）が提供ファイルで途中までの状態です。ファクター計算は設計を含めて実装済みの関数が複数ありますが、完全実装・テストは要確認です。
- position_sizing の lot_size は現状すべての銘柄で共通の想定（デフォルト 100）。将来的に銘柄別単元対応を検討中（TODO コメントあり）。
- apply_sector_cap は `unknown` セクターを上限判定から除外する設計（マスタ未整備の銘柄に対する保守的扱い）。
- 実際のブローカークライアントの振る舞い（Mock / 実ブローカー）や ExecutionEngine の詳細ロジックは別モジュールに依存しており、本 CHANGELOG は公開された API と主要設計に基づく説明に留まります。

---

セマンティックバージョニングに従い、将来の変更は [Unreleased] に追加後、適宜バージョンタグを切って本ファイルを更新してください。