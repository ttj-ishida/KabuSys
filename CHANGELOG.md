# Changelog

すべての変更は Keep a Changelog の形式に従って記載しています。  
現在のバージョンはパッケージ metadata に従い v0.1.0 を初回リリースとしてまとめています。

- リリースノートの要約
  - 初期実装: 環境設定、ログ設定、プロセス制御、監視/実行ランナー、ポートフォリオ構築、ポジションサイジング、ペーパートレード検証ツール、設定検証/ウィザード、いくつかのユーティリティ関数などを含む初期機能群を追加。

---

## [Unreleased]
（現在未リリースの変更はありません）

---

## [0.1.0] - 2026-04-23

### Added
- パッケージの初期公開（__version__ = "0.1.0"）
- 環境設定管理
  - Settings クラスを追加（kabusys.config）
    - 環境変数から各種設定を提供（J-Quants, kabuAPI, DBパス, LINE, モニタ閾値等）
    - env / log_level 等の値検証、is_live / is_paper / is_dev の便宜プロパティを提供
    - PAPER_FILL_MODE のバリデーションを実装（instant/partial/never/reject）
  - .env 自動読み込み機能を追加
    - プロジェクトルート（.git または pyproject.toml を基準）を自動検出して `.env` と `.env.local` を読み込む
    - OS 環境変数は保護され、`.env.local` は上書き可能
    - 自動ロードを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート
  - .env パーサーは `export KEY=val`、クォート、インラインコメントの取り扱いをサポート

- 設定関連 CLI / ツール
  - 設定検証 CLI（kabusys.validate_config）
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスや config/*.yaml の存在確認
    - PyYAML がない場合は YAML 検証をスキップする柔軟性
    - --strict オプションで警告を失敗扱いにできる
  - 環境設定ウィザード（kabusys.config_setup）
    - 対話式ウィザードで .env を生成・更新
    - テンプレート書き出し機能（.env の書式を整えて保存）

- ランナー（実際のプロセス起動スクリプト）
  - 監視プロセス起動スクリプト（kabusys.run_monitoring）
    - SystemMonitor を初期化してポーリングループを実行
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
    - 監視は実行環境に依らず本番用 sqlite_path を使用する設計（明示）
    - stop フラグファイルで安全に停止可能
  - 実行エンジン起動スクリプト（kabusys.run_execution）
    - ExecutionEngine を組み立ててスレッドで実行
    - KABUSYS_ENV=paper_trading 時は専用のペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）を使用して本番 DB と分離
    - BrokerClientFactory を利用してブローカークライアントを生成
    - stop フラグと PID ファイルの利用、停止時の安全停止処理を実装

- ポートフォリオ構築関連（kabusys.portfolio）
  - 銘柄選定と重み計算（portfolio_builder）
    - select_candidates: スコア降順で候補を選択（同点は signal_rank でタイブレーク）
    - calc_equal_weights / calc_score_weights を追加（score 全て 0 の場合は等配分にフォールバック）
  - リスク調整（risk_adjustment）
    - apply_sector_cap: セクター集中上限チェック（既存ポジションの時価を参照、unknown セクターは上限適用外）
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear マップ、未知レジームは警告して 1.0 にフォールバック）
  - ポジションサイジング（position_sizing）
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく買付株数算出
    - 単元（lot_size）丸め、1銘柄上限、aggregate cap（利用可能現金）超過時のスケールダウン、残差を使った再配分ロジックを実装
    - cost_buffer で手数料/スリッページを保守的に見積もるオプションあり

- 監視 DB 初期化ユーティリティ
  - init_monitoring_db が各起動時に呼ばれて監視テーブルの存在を保証（冪等）

- ロギングユーティリティ（kabusys.utils.logging_setup）
  - setup_logging 関数を追加
    - stdout への StreamHandler と 日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log）を設定
    - 既存ハンドラをクリアして二重設定を防止
    - LOG_LEVEL / LOG_DIR の環境変数利用、フォールバックに対する堅牢性（ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみ継続）
    - 30 日分のログローテーション設定

- プロセス優先度 / CPU 固定ユーティリティ（kabusys.utils.process_priority）
  - set_process_priority(level) を追加（high/normal/low）
    - Windows/Linux/macOS 等の差分を吸収して適切に nice 値や優先度を設定
    - 権限不足や未サポート環境では警告を出して安全にスキップ
  - set_cpu_affinity(cpu_count) を追加（最初の N コアに固定）

- ペーパートレード検証レポート（kabusys.tools.paper_verification_report）
  - ペーパートレード SQLite を解析して検証レポートを標準出力に出力
  - 指標: 稼働率、注文成功率、送信率、P95 レイテンシ、リスク却下数 など
  - フィルタ期間指定（--from/--to）、DB パス指定（--db）をサポート
  - 基準値（閾値）を定義して PASS/FAIL を判定

- リサーチ（研究）用モジュール（kabusys.research.factor_research）
  - Momentum 等のファクター計算基盤を追加（DuckDB 接続を受け prices_daily / raw_financials を参照）
  - モメンタム指標（1M/3M/6M、MA200乖離など）算出処理の実装を開始（モジュールは更なる実装・完成が必要）

### Changed
- N/A（初回リリースのため既存機能の変更履歴はなし）

### Fixed
- N/A（初回リリース）

### Security
- N/A

---

注記 / 実装上の注意点
- run_monitoring は「監視は環境に関わらず本番 sqlite_path を使用する」ことが明記されているため、デプロイ時の DB パス設定に注意が必要です。
- .env の自動読み込みはプロジェクトルートの検出に依存するため、配布後や異なる配置で動作させる場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して手動で環境変数を設定してください。
- factor_research モジュールの一部は実装途中の箇所が存在します（ファイル末尾が途中で切れているため追加実装が必要）。

---

参考
- この CHANGELOG はソースコード内の実装・docstring・ログメッセージから推測して作成しています。実際のリリースノートとして使用する場合は、リリース日やマイナーな修正内容の追加・確認を行ってください。