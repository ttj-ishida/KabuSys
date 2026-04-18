# Changelog

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。  
なお、本チャンジログは提示されたコードベースの内容から推測して作成しています。

皆項目は大きく「Added / Changed / Fixed / Removed / Security」などで分類しています。  

## [Unreleased]

### Added
- 開発用ユーティリティ・CLIを追加
  - 対話式の .env 作成/更新ウィザード（kabusys.config_setup）
    - 各種設定項目定義（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE など）
    - 既存 .env 読み込み・シークレットマスク表示・保存機能を実装
  - 設定検証 CLI（kabusys.validate_config）
    - 必須環境変数・KABUSYS_ENV の妥当性・ログレベル・DB パス・config/*.yaml の存在と YAML パース（PyYAML が存在する場合）・本番時のガードチェックを実施
    - --strict オプションで警告も失敗扱いにできる
  - Paper Trading 検証レポート生成ツール（kabusys.tools.paper_verification_report）
    - 稼働率、注文成功率（fill/send）、リスク却下数、レイテンシ（平均・最大・P95）を集計して PASS/FAIL を判定
    - 日付フィルタと DB パス指定オプションをサポート

- 起動スクリプトを追加
  - run_execution.py: ExecutionEngine の起動スクリプト
    - KABUSYS_ENV による paper_trading モードの DB 分離（paper_trading 時は別 SQLite に記録）
    - BrokerClientFactory を用いたブローカークライアント生成、OrderManager / RiskManager / Reconciler 構成、ExecutionEngine のデーモンスレッド実行
    - 起動時にプロセス優先度を "high" に設定、停止フラグ（data/stop_requested.flag）と PID ファイルを利用して安全に停止可能
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプト
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
    - 監視は常に本番用 sqlite_path を使用して初期化（環境にかかわらず監視 DB を保証）
    - 停止フラグ検知でループ終了、例外発生時のロギングとリトライ処理を実装

- 設定管理 / 自動 .env ロード機能（kabusys.config）
  - プロジェクトルートを .git / pyproject.toml から自動検出して .env / .env.local を読み込む（OS 環境変数が優先）
  - .env の読み込みロジック
    - export KEY=val 形式やクォート、エスケープ、インラインコメントを考慮した堅牢なパーサを実装
    - override と protected（既存 OS 環境変数保護）オプションをサポート
    - 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート
  - Settings クラスによるプロパティ化された設定取得（ログレベル・env 判定・DB パス・paper_trading 用設定・監視閾値など）
    - PAPER_FILL_MODE のバリデーション、有効値の列挙
    - env/log_level の許容値チェックとエラー報告

- ロギングユーティリティ（kabusys.utils.logging_setup）
  - ルートロガーへ StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）を統一的に設定
  - LOG_LEVEL / LOG_DIR / app_name で出力先・レベルを解決
  - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続

- プロセス優先度ユーティリティ（kabusys.utils.process_priority）
  - Windows / POSIX(Linux/Mac/FreeBSD) を抽象化してプロセス優先度（high/normal/low）を設定
  - CPU affinity を最初 N コアに固定する set_cpu_affinity を提供
  - 権限不足や未対応 OS に対してはワーニングを出して安全にスキップ

- ポートフォリオ構築モジュール（kabusys.portfolio）
  - 銘柄選定・重み計算（portfolio_builder）
    - select_candidates（スコア降順・タイブレークに signal_rank を利用）
    - calc_equal_weights / calc_score_weights（スコアが全て 0 の場合に等分配へフォールバック）
  - セクター集中制限・レジーム乗数（risk_adjustment）
    - apply_sector_cap（既存保有からセクター別エクスポージャーを計算し上限超過セクターの新規候補を除外）
    - calc_regime_multiplier（"bull"/"neutral"/"bear" に応じて乗数を返す。未知のレジームは 1.0 でフォールバック）
  - 株数決定・リスク制限・単元丸め（position_sizing）
    - allocation_method: "risk_based" / "equal" / "score" をサポート
    - risk_based: 損切り幅と risk_pct に基づく株数計算、lot_size 単位で丸め
    - aggregate cap と cost_buffer を考慮したスケーリング処理、スケール後の端数配分アルゴリズムを実装
    - price 欠損時のスキップや上限チェックを実装

- 研究用ファクターモジュール（kabusys.research.factor_research）
  - DuckDB 接続を受けてモメンタム（1m/3m/6m）、MA200乖離、ATR、流動性指標などを計算するための骨組みを実装（設計・定数・関数インターフェースを含む）
  - （注）ファイル末尾が途中で切れているため、実装は継続中（未完成のセクションあり）

### Changed
- 既存の監視/実行起動処理において、起動直後にプロセス優先度を "high" に設定する仕様を採用
- ログ出力は stdout に統一（stderr ではなく）して、Task Scheduler / cron などで扱いやすくした

### Fixed
- （該当コードから明確なバグ修正の履歴は推測できません。今後実装中の不具合対応に注意してください。）

### Notes / Known issues
- factor_research モジュールはファイル末尾が途中で切れている（未完成）。本番利用前に完成・テストが必要。
- 一部の処理で price が欠損（0.0）だとエクスポージャー/ポジション計算が過小評価される旨の TODO コメントあり。将来的に価格フォールバック実装が推奨されている。
- process_priority の設定は権限やプラットフォームに依存する。権限不足時はワーニングを出してスキップする設計。

---

## [0.1.0] - 2026-04-18

初回リリース。上記「Added」に記載の主要機能を含む。

- CLI/ツール群
  - config_setup（.env ウィザード）、validate_config（設定検証）、tools.paper_verification_report（Paper Trading 検証レポート）
- 起動スクリプト
  - run_execution（ExecutionEngine 起動）、run_monitoring（SystemMonitor 起動）
- 設定管理
  - Settings クラス、.env 自動ロード（.env / .env.local）と堅牢なパーサ
- ロギング / プロセス制御
  - 統一ロギングセットアップ（stdout + 日次ファイルローテーション）、プロセス優先度/CPU affinity ユーティリティ
- ポートフォリオ構築ライブラリ
  - 銘柄選定・重み・セクター制限・レジーム乗数・ポジションサイズ計算
- 研究モジュール（実装進行中）
  - factor_research: モメンタム・ボラティリティ等の計算設計を実装開始

変更の詳細や設計背景は各モジュールの docstring / コメントに記載しています。運用前に validate_config による設定検証と config_setup による .env の整備を推奨します。

---

（注）この CHANGELOG はコードの静的内容からの推測に基づいて作成しています。リポジトリの実際のコミット履歴や既存のリリースノートがある場合は、それに合わせて調整してください。