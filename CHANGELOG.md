# CHANGELOG

すべての変更は Keep a Changelog（https://keepachangelog.com/ja/1.0.0/）に準拠しています。

全般的な方針: 各リリースでは「Added / Changed / Fixed / Deprecated / Removed / Security」カテゴリを用いて変更点を記載します。

---------------------------------------------------------------------
Unreleased
---------------------------------------------------------------------

（現在なし）

---------------------------------------------------------------------
0.1.0 - 2026-04-21
---------------------------------------------------------------------

Added
- 基本パッケージの初期実装を追加。
  - パッケージバージョン: `kabusys.__version__ = "0.1.0"`。

- 起動スクリプト / ランタイム
  - src/kabusys/run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き対応（デフォルト 60 秒）。
    - 停止フラグ `data/stop_requested.flag` を検知して安全にループ終了。
    - Monitoring は実行環境に関わらず本番用の sqlite_path を使用する設計。
  - src/kabusys/run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は Paper Trading 用 DB（`data/paper_trading.db` または環境変数で上書き）を使用し、MockBrokerClient を利用する想定で本番 DB と完全分離。
    - `data/execution.pid` に PID を書き、停止フラグで動的に停止する仕組みを提供。
    - エンジンはスレッドで実行し、停止フラグ存在時に安全に停止する。

- 設定管理 / CLI
  - src/kabusys/config.py
    - .env 自動読み込み機能を追加（プロジェクトルートを .git / pyproject.toml で検出）。
    - .env のパースは引用符・エスケープ・インラインコメント等に対応。
    - OS 環境変数保護（既存環境変数は上書きされない）や `KABUSYS_DISABLE_AUTO_ENV_LOAD` による自動ロード無効化をサポート。
    - Settings クラスを提供し、各種設定（J-Quants / kabu API / DB パス / 監視閾値 / 環境判定 等）へプロパティアクセス可能に。
    - PAPER_FILL_MODE 検証（有効値: instant|partial|never|reject）、paper_trading 用 SQLite パス、閾値（CPU/MEM/DISK）などを規定。
  - src/kabusys/config_setup.py
    - 対話式の .env 作成ウィザードを追加。シークレット項目はマスク表示し、既存 .env の読み込み・編集をサポート。
    - 書き出しは .env テンプレート形式で行い、注意書きを含める。
  - src/kabusys/validate_config.py
    - 起動前に .env と config/*.yaml を検証する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV 値チェック、ログレベルチェック、DB パスの親ディレクトリ存在チェック、YAML パースチェック（PyYAML がある場合）を実施。
    - `--strict` オプションで警告を FAIL 扱いにできる。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - src/kabusys/portfolio/portfolio_builder.py
    - シグナルの候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights)。スコアが全て 0 の場合のフォールバック警告あり。
  - src/kabusys/portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear とフォールバック実装）。
  - src/kabusys/portfolio/position_sizing.py
    - allocation_method（risk_based / equal / score）に対応した株数計算 calc_position_sizes。
    - 単元（lot_size）丸め、1銘柄上限、aggregate cap（available_cash）に基づくスケーリング、cost_buffer を考慮した保守的見積り。
    - 不足価格データや価格 <= 0 のケースはログ出力してスキップ。

- ログ / プロセス管理ユーティリティ
  - src/kabusys/utils/logging_setup.py
    - ルートロガーを統一的に設定する setup_logging を追加。
    - stdout 出力用 StreamHandler と 日次ローテーション（TimedRotatingFileHandler）でのファイル出力（デフォルト logs/）を設定。
    - 既存ハンドラをクリアして二重設定を防止、ログディレクトリ作成失敗時はファイル出力をスキップするフォールバックあり。
  - src/kabusys/utils/process_priority.py
    - プラットフォーム差異を吸収する set_process_priority（high/normal/low）と set_cpu_affinity を追加。
    - Windows と POSIX（Linux/Mac/FreeBSD）に対応。権限不足や未対応環境では警告ログを出してスキップ。

- モニタリング DB 初期化
  - src/kabusys/monitoring/monitoring_db.py（参照インポートあり）
    - run_monitoring / run_execution が起動前に監視テーブルの存在を保証する init_monitoring_db 呼び出しを行う（冪等）。

- Paper Trading 検証ツール
  - src/kabusys/tools/paper_verification_report.py
    - Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）から各種指標（稼働率、注文成功率、送信率、レイテンシ P95 等）を算出してレポート出力する CLI を追加。
    - 基準値（稼働率 99% 等）を定義し PASS/FAIL 判定を行う。日付フィルタ（--from / --to）対応。
    - DB にテーブルが無い場合でも安全に N/A を扱う堅牢性。

- 研究モジュール（ファクター計算）
  - src/kabusys/research/factor_research.py
    - ファクター計算フレームワークを追加（モメンタム / MA200 / ATR / 流動性等を想定）。DuckDB を用いた設計方針を記載。
    - calc_momentum の実装開始（設計と定数定義を追加）。

Changed
- 初回リリースのため該当なし（新規実装中心）。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 該当なし。

Removed
- 該当なし。

Security
- 環境変数の取扱いに注意を促す実装（.env を Git 管理しない注意書き、シークレットのマスク表示等）を追加。

Notes / 注意事項
- .env の自動ロードはプロジェクトルートの自動検出（.git / pyproject.toml）に依存するため、配布後に CWD に依存せず動作する設計ですが、検出できない場合は自動ロードをスキップします。
- 設定値チェックやファイル作成に失敗した場合はログや警告で通知してフォールバックする実装が多く、強固なエラー停止を行わない箇所があります（運用時は validate_config による事前チェックを推奨）。
- research モジュールの一部（calc_momentum 以降の実装）が未完の可能性があります。詳細なファクター実装は今後のリリースで拡充予定です。

---------------------------------------------------------------------
今後予定（Hints）
---------------------------------------------------------------------
- factor_research の完全実装（全ファクター計算の完成）。
- ExecutionEngine / BrokerClient の詳細実装とテスト（MockBroker の挙動・ペーパートレード検証）。
- より詳細なユニットテスト・CI 追加。
- ログ管理・監視の強化（アラート送信など）。

---------------------------------------------------------------------
お問い合わせ・貢献
---------------------------------------------------------------------
バグ報告や改善提案は issue を作成してください。プルリクエスト歓迎。README やドキュメントは随時更新予定です。