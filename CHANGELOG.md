# Changelog

すべての変更は Keep a Changelog の形式に従って記載しています。  
以前のリリースとの比較や導入時の注意点は各項目の説明を参照してください。

全般:
- バージョンはパッケージルートで `__version__ = "0.1.0"` に設定されています。

## [Unreleased]

## [0.1.0] - 2026-04-17

Added
- 初回リリース。以下の主要サブシステム・ユーティリティを実装・追加しました。
  - CLI / 起動スクリプト
    - run_monitoring.py
      - SystemMonitor のポーリングループ起動スクリプトを追加。
      - 環境変数 `MONITOR_POLL_INTERVAL`（秒）でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - 停止制御にプロジェクト直下の `data/stop_requested.flag` を使用。
      - 監視用途の DB は KABUSYS_ENV に関係なく本番用 SQLite パスを使用して初期化。
      - 起動時にプロセス優先度を "high" に設定。
    - run_execution.py
      - ExecutionEngine を起動するスクリプトを追加。
      - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用し、paper_trading 用 SQLite（デフォルト `data/paper_trading.db`）で本番 DB と完全に分離して動作。
      - エンジンはスレッドで実行され、停止フラグにより安全に停止可能。PID ファイルを書き込み。
      - 起動時にプロセス優先度を "high" に設定。
  - 設定関連
    - config.py
      - プロジェクトルート（.git または pyproject.toml）を基に自動で .env を検出・読み込み（`.env` → `.env.local` の順、OS 環境変数優先）。自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
      - .env の行パースを堅牢化（export プレフィックス、引用符付き値のバックスラッシュエスケープ、インラインコメントの扱い等）。
      - Settings クラスを導入し、環境変数取得・検証ロジックを提供（各種パス、しきい値、paper_fill_mode 等のバリデーションを含む）。
      - `settings` の単一インスタンスをエクスポート。
    - config_setup.py
      - 対話式ウィザードで .env を作成・更新する CLI を追加。既存値の再利用、シークレット値のマスク表示、保存確認をサポート。
    - validate_config.py
      - 起動前に .env と `config/*.yaml` を検証する CLI を追加。
      - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、PyYAML を使った YAML パース検証、`KABUSYS_ENV=live` 時の追加ガード等を実施。`--strict` オプションで警告を失敗扱いにできる。
  - ポートフォリオ構成・サイジング（純粋関数群）
    - portfolio/portfolio_builder.py
      - 候補選定（スコア降順）select_candidates、等配分 calc_equal_weights、スコア加重 calc_score_weights を実装。スコア全てが 0 の場合は等分にフォールバック（警告）。
    - portfolio/risk_adjustment.py
      - セクター集中制限 apply_sector_cap を実装。既存ポジションのセクター別エクスポージャー計算や、"unknown" セクター扱い等を実装。
      - 市場レジームに応じた資金乗数 calc_regime_multiplier を実装（bull/neutral/bear マップ、未知レジームはフォールバック）。
    - portfolio/position_sizing.py
      - 発注株数計算 calc_position_sizes を実装。allocation_method に応じた "risk_based" / "equal" / "score" をサポート。
      - lot_size（単元）丸め、per-symbol 上限・aggregate cap（available_cash に基づくスケーリング）、cost_buffer を考慮した保守的見積り、残余キャッシュを用いた端数配分ロジックを実装。
  - ユーティリティ
    - utils/process_priority.py
      - プラットフォーム非依存のプロセス優先度設定（set_process_priority）と CPU アフィニティ設定（set_cpu_affinity）を追加。Windows / POSIX に対応し、権限不足や未対応環境では警告を出してスキップ。
  - 研究・ファクター計算
    - research/factor_research.py
      - DuckDB 接続を使ったモメンタム・ボラティリティ等のファクター計算関数を実装（calc_momentum, calc_volatility 等）。prices_daily テーブルに依存する設計。
  - ツール
    - tools/paper_verification_report.py
      - ペーパートレードの検証レポートを生成する CLI を追加。システム稼働率、注文成功率（Fill/Send）、リスク却下数、レイテンシ（avg/max/P95）を集計し PASS/FAIL 判定を行う。デフォルト DB パスは `data/paper_trading.db`。P95 計算や日付フィルタをサポート。

Changed
- 初版につき「新規追加」が中心。以下は設計上の注意点・挙動（実装に伴う変更ではなく仕様の明示）。
  - run_monitoring は監視データベース初期化を行う（init_monitoring_db を呼出し、監視用テーブルの存在を保証）。
  - run_execution は paper_trading モード時に専用 DB を使用し、本番 DB とデータを分離するよう設計。
  - .env の自動読み込み順序を明確化（OS 環境 > .env.local > .env）。
  - position_sizing のスケーリングロジックは lot_size 単位での丸めを行い、再現性のため残差ソートにコードを二次キーとして使用。

Fixed
- ユーザ入力・外部依存で発生し得る例外・不整合に対する耐性を向上。
  - MONITOR_POLL_INTERVAL に不正な値が設定された場合、デフォルトにフォールバックして警告を出力。
  - .env パーサは引用符内のエスケープ文字やコメントの扱いを正しく処理するよう拡張。
  - calc_score_weights で総スコアが 0 の場合は等金額配分へフォールバック（警告出力）し、ゼロ除算を防止。
  - process_priority/set_cpu_affinity は権限不足や未実装 API に対して例外を出さず警告で処理をスキップ。
  - tools/paper_verification_report はテーブルが存在しない場合に sqlite3.OperationalError を捕捉して N/A 表示するなど堅牢化。

Security
- .env ファイルの取り扱いに関する注意喚起を config_setup の書き出しヘッダに明記（.env を Git にコミットしないよう注意）。

Notes / Migration
- 初期リリースのため破壊的変更はありませんが、以下に注意してください。
  - 本番運用時は必ず .env の必須値（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）を設定してください。validate_config で起動前に検証できます。
  - KABUSYS_ENV によって挙動（paper_trading と live 等）が変わります。paper_trading は専用 DB を使用して本番データと分離しますが、設定ミスに備えて validate_config を使用してください。
  - process_priority や CPU affinity の設定は実行環境の権限に依存します。警告が出た場合は権限や psutil バージョンを確認してください。

[0.1.0]: https://example.com/compare/v0.0.0...v0.1.0  (初回リリース)