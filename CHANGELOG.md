# Changelog

すべての重要な変更を記録します。本ファイルは「Keep a Changelog」準拠の形式を採用しています。

注意: バージョン番号はパッケージ定義 (kabusys.__version__ = "0.1.0") に合わせています。

## [Unreleased]

（未リリースの変更はここに記載してください）

## [0.1.0] - 2026-04-18

初回公開リリース。

### Added
- 基本アプリケーション構成
  - パッケージメタ情報: `kabusys.__version__ = "0.1.0"` を導入。
- 起動スクリプト / サービス
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止制御はプロジェクトの data/stop_requested.flag を監視。
    - 監視（monitoring）用 DB 接続は環境に依らず本番の sqlite_path を使用。
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は paper_trading 専用 SQLite を使用し、MockBrokerClient（BrokerClientFactory 経由）で発注を分離。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル管理を実装。
- 設定管理・ユーティリティ
  - `kabusys.config.Settings` クラスを実装し、環境変数／.env 自動ロード、各種設定プロパティ（DB パス、ログレベル、しきい値等）を提供。
    - 自動読み込み: プロジェクトルートを .git / pyproject.toml から検出して `.env` / `.env.local` を適切な優先順でロード（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能）。
    - PAPER_FILL_MODE のバリデーション（有効値: instant, partial, never, reject）。
  - `.env` ファイル用の対話式ウィザード CLI (`kabusys.config_setup`) を提供。
    - 主要な環境変数項目の入力支援、および `.env` ファイルの生成/更新機能。
  - 設定検証 CLI (`kabusys.validate_config`) を追加。
    - 必須環境変数の存在、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスや config/*.yaml の存在チェック、live 環境向けガード等を実装。
    - `--strict` オプションで警告を失敗扱いにできる。
- ロギング / プロセス制御ユーティリティ
  - `kabusys.utils.logging_setup.setup_logging`
    - stdout への StreamHandler と日次ローテーションの FileHandler（logs/<app_name>.log）をルートロガーに設定。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみで継続。
  - `kabusys.utils.process_priority`
    - Windows / POSIX（Linux, Darwin, FreeBSD）に対応したプロセス優先度設定（high/normal/low）と CPU affinity 設定ユーティリティを追加。
    - 権限不足や未対応プラットフォーム時は警告ログを出して安全にスキップ。
- ポートフォリオ構築関連（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`
    - 銘柄選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
    - 全銘柄のスコアが 0 の場合は等配分へフォールバック（警告ログ）。
  - `kabusys.portfolio.risk_adjustment`
    - セクター集中上限の適用（apply_sector_cap）と市場レジームに応じた資金乗数（calc_regime_multiplier）を実装。
    - 未知のレジームはログを出して 1.0 にフォールバック。
  - `kabusys.portfolio.position_sizing`
    - 発注株数算出ロジックを実装（risk_based / equal / score）。
    - 単元株（lot_size）丸め、1 銘柄上限、利用可能資金に対する aggregate スケーリング（残差配分ロジック含む）を実装。
- Research / 分析
  - `kabusys.research.factor_research`（モメンタム等ファクター計算の基盤を実装：momentum, MA200, ATR 等の設計・定数定義。関数は DuckDB 接続を受け取る設計）
- 運用ツール
  - `kabusys.tools.paper_verification_report`
    - ペーパートレード DB を解析して稼働率、注文成功率、送信率、レイテンシ（P95 など）を集計・判定するレポートを CLI で出力。
    - DB が存在しない／テーブルがない場合にも graceful にエラー／N/A を出力。
    - 判定閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）を定義。

### Changed
- （初版のため該当なし）

### Fixed / Robustness improvements
- .env パーサの堅牢化
  - `export KEY=val` 形式に対応。
  - シングル / ダブルクォート内のバックスラッシュエスケープ処理を考慮した値抽出。
  - クォートなしの値に対するインラインコメント解釈を改善（`#` の前が空白/タブの場合のみコメントとみなす）。
  - `.env` 読み込み時に OS 環境変数を保護する protected セットを実装（上書き回避）。
- 起動スクリプトの安全停止
  - run_monitoring / run_execution ともにプロジェクトの stop_requested.flag を監視して安全にループ／スレッドを終了する機構を実装。
- DB 分離
  - 実行エンジンは paper_trading モード時に paper_trading 専用 SQLite（デフォルト data/paper_trading.db）を使用し、本番データと明確に分離。
  - 監視用の init_monitoring_db を呼び出して監視テーブルの冪等な初期化を保証。
- ロギングの安全性
  - ログディレクトリ作成やファイルハンドラ生成に失敗してもコンソール出力で継続するようフォールバック。
- process_priority / cpu_affinity は権限不足・未対応環境で例外を吸収して警告ログを出すよう変更（実運用での安定化）。

### Security
- 起動ウィザードおよび .env 書き出し時にシークレット項目はマスクして表示（画面上のみ）。`.env` 自体は出力されるため、必ず Git などにコミットしない旨をドキュメントに明記。

### Notes / 設定・運用メモ
- 環境変数の自動読み込みはデフォルトで有効。テストや特殊な起動方法で無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- run_monitoring は監視 DB 接続に settings.sqlite_path を常に使用します（環境にかかわらず本番監視 DB を想定）。
- run_execution は paper_trading 時に settings.paper_sqlite_path を使用します（paper_trading と本番 DB を完全分離）。
- ログ出力先はデフォルトで logs/<app_name>.log。`LOG_DIR` 環境変数や setup_logging の引数で変更可能。
- `validate_config` を使って起動前に設定不備をチェックしてください。`--strict` オプションで警告を失敗扱いにできます。
- Paper Trading レポートは `PAPER_TRADING_SQLITE_PATH` 環境変数または `--db` 引数で DB を指定できます。

今後の改善候補（TODO）
- stocks マスタに個別単元株数（lot_size）を持たせる等、position_sizing の銘柄別ロット対応。
- price の欠損時に前日終値や取得原価でフォールバックする処理の追加（risk_adjustment 内の TODO）。
- factor_research の関数群の完全実装とテストカバレッジ拡充。

--- 

（以上）