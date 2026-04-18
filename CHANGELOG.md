# Changelog

すべての notable な変更をここに記載します。本ファイルは "Keep a Changelog" の形式に従います。  
比較対象がないため、このリリースはコードベースから推測した初期リリースの変更点をまとめたものです。

フォーマット:
- Unreleased: 今後の変更（現状なし）
- 0.1.0 - 2026-04-18: 初期リリース（コードベースから推測してまとめた機能・改良・修正）

---

## [Unreleased]
（現時点で未リリースの変更はありません）

---

## [0.1.0] - 2026-04-18

### Added
- 基本アプリケーション
  - kabusys パッケージの初期構成（__version__ = 0.1.0）。
  - ポートフォリオ構築、ポジションサイズ計算、リスク調整などの純粋関数群を提供する portfolio モジュールを追加。
    - portfolio_builder: 候補選定（スコア降順、タイブレーク）、等金額配分、スコア加重配分（スコア合計が0なら等配分にフォールバック）。
    - position_sizing: risk_based / equal / score の allocation を実装。単元（lot_size）整形、aggregate cap によるスケーリング、手数料等を見積もる cost_buffer を考慮。
    - risk_adjustment: セクター集中上限（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）を実装。
- 実行・監視系スクリプト
  - run_execution: ExecutionEngine を起動するスクリプトを追加。
    - KABUSYS_ENV が paper_trading の場合は専用の paper DB を使用して本番 DB と分離する挙動を実装。
    - BrokerClientFactory を介してブローカークライアントを生成。
    - OrderRepository、OrderManager、RiskManager（デフォルト設定あり）、Reconciler を組み合わせて実行エンジンを起動。PID ファイル管理、停止フラグ検出、スレッドによる run_session の実行と安全停止処理を実装。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値（0以下／非数）はデフォルトにフォールバックして警告を出す。
    - 監視は実行環境にかかわらず本番用 sqlite_path を使用する設計（監視データの保存先の一貫性確保）。
- 設定関連 CLI
  - config_setup: .env の対話式ウィザードを追加。既存 .env の読み込み、シークレットマスク表示、デフォルト値・選択肢の提示、保存確認・書き込み機能を提供。
  - validate_config: 起動前に .env および config/*.yaml を検証する CLI を追加。必須環境変数チェック、KABUSYS_ENV／LOG_LEVEL の妥当性チェック、DB パスや YAML ファイルの存在・パースチェック、本番（live）向けの追加警告を提供。--strict オプションで警告をエラー扱いにできる。
- utils
  - config モジュール: .env 自動読み込み機能（プロジェクトルート検出、.env / .env.local の読み込み、エクスポート形式・クォート対応のパーサ）と Settings クラスを追加。PAPER_FILL_MODE のバリデーション、各種パス・しきい値・環境フラグをプロパティで提供。
  - logging_setup: 一貫したログ設定ユーティリティを追加。stdout 出力用 StreamHandler と日次ローテーション（TimedRotatingFileHandler）を Root ロガーに設定、ログディレクトリ作成のフォールバック処理を実装。
  - process_priority: クロスプラットフォームでプロセス優先度（high/normal/low）と CPU affinity を設定するユーティリティを追加。Windows / POSIX 対応、権限エラーは警告でスキップ。
- monitoring / DB
  - init_monitoring_db 呼び出しにより監視用テーブルの初期化を保証（冪等性確保）。
- tools
  - tools/paper_verification_report: ペーパートレード用の検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率（fill_rate）、送信率（send_rate）、API レイテンシ（avg/max/P95）などを集計。
    - デフォルト閾値（稼働率 >= 99%、fill_rate >= 90%、send_rate >= 95%、P95 <= 200 ms）を定義し、Pass/Fail 判定を出力。
    - 日付フィルタ（--from/--to）、DB パスのオーバーライド（--db / 環境変数）に対応。
- research
  - research/factor_research のスケルトンを追加（モメンタム、ボラティリティ、バリュー、流動性等を計算する方針と定数を定義）。

### Changed
- ログの既定動作
  - logging_setup は既存ハンドラをクリーンアップしてから再設定するため、スクリプト間での二重ログ出力を防止。
  - ログ出力は標準エラーではなく標準出力（stdout）へ出力するように明示。cron やスケジューラからの起動時のリダイレクト運用を意識した設計。
- .env 読み込み優先度
  - OS 環境変数 > .env.local > .env の順に読み込み。既存 OS 環境変数はデフォルトで保護される（上書き禁止）。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。

### Fixed / Robustness
- .env パーサの強化
  - export KEY=val 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、コメント処理の改善により .env の多様な書式を正しく扱うようにした。
- ポーリング間隔の取り扱い
  - MONITOR_POLL_INTERVAL の不正値（非数、0 や負値）に対して警告を出し、time.sleep に渡して例外を出さないようデフォルトにフォールバックする安全策を実装。
- DB 初期化の冪等性
  - run_execution/run_monitoring で init_monitoring_db を呼び、監視用テーブルが未作成でも起動時に作成されるようにして起動失敗を回避。
- ファイル・ディレクトリ操作の耐障害性
  - logging_setup がログディレクトリ作成に失敗した場合はファイルハンドラをスキップして stdout のみで継続。config_setup や他のファイル書き込みでも例外を考慮した扱いを行う設計。process_priority・set_cpu_affinity も権限不足や未実装 API を安全にスキップ。
- Execution の安全停止
  - run_execution は外部の停止フラグ（data/stop_requested.flag）を監視し、検出時に Engine.stop() を呼ぶことで安全にシャットダウンするループを実装。

### Documentation / UX
- config_setup の対話式入力でシークレットはマスク表示、既存値を Enter で継続、選択肢チェックや中断時の動作を整備。ウィザード終了時に .env 保存の確認を行う。
- validate_config は errors/warnings/infos を区別して出力し、--strict オプションで警告を失敗に昇格できる。YAML パーサ（PyYAML）が無い場合は該当チェックをスキップして警告を出す。

### Known limitations / Notes
- research/factor_research はファクター計算の方針・定数を定義しているが、ファイル末尾が途中で切れており実装の続きが必要（prices_daily テーブル参照の SQL/処理が未完）。
- position_sizing の単元サイズ（lot_size）は現状グローバル共通の想定（将来的に銘柄別対応への拡張検討）。
- apply_sector_cap は sector_map に存在しない銘柄を "unknown" 扱いとしており、unknown セクターに対する上限適用は行わない。そのため price 欠損時の過少見積りによる不整合に関する TODO コメントが残されている。
- 一部の外部ライブラリ（psutil、duckdb、PyYAML）が必須／任意で使用されるため、環境に応じたインストールが必要。

---

参照:
- 各実行スクリプト: run_execution.py, run_monitoring.py
- 設定関連: config.py, config_setup.py, validate_config.py
- ユーティリティ: utils/logging_setup.py, utils/process_priority.py
- ポートフォリオ構築: portfolio/*
- ツール: tools/paper_verification_report.py
- 研究用スケルトン: research/factor_research.py

（以上は提供されたソースコードの内容から推測して記述しています）