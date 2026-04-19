# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
このファイルはコードベースから推測できる機能追加・挙動を基に記載しています。

※ これは推測に基づく初回リリース向けのまとめです。実際のリリースノートと差異がある場合があります。

## [Unreleased]

## [0.1.0] - 2026-04-19

### 追加 (Added)
- 基本パッケージ初期リリース: KabuSys 日本株自動売買システムの初期実装を追加。
  - パッケージバージョン: `__version__ = "0.1.0"`。

- 起動スクリプト
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - プロセス優先度を起動時に "high" に設定するフローを導入。
    - KABUSYS_ENV が `paper_trading` の場合は Paper Trading 用の専用 SQLite DB（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine の起動とスレッド管理（停止フラグ検知時の停止処理）を実装。
    - 実行中は data/execution.pid に PID を書き込む想定。

  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバック。
    - 監視（monitoring）は KABUSYS_ENV にかかわらず本番用の sqlite_path を使用する設計（監視DBは環境に依存しない）。
    - 停止フラグ（data/stop_requested.flag）検知で安全にループを終了。

- 設定管理
  - config.py:
    - .env ファイルの自動読み込み実装（プロジェクトルートが特定できる場合、`.env` を読み込み、`.env.local` を上書きロード）。自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - .env パーサーは export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、行末コメント（クォートなしで直前が空白の場合）などを考慮した堅牢な実装。
    - Settings クラスを提供。主要な環境変数をプロパティで取得（J-Quants、kabu API、DB パス、PID/kill flag パス、閾値、環境判定など）。
    - PAPER_FILL_MODE のバリデーション、有効値チェック（instant/partial/never/reject）。
    - 環境（KABUSYS_ENV）とログレベル（LOG_LEVEL）に対する入力検証。

  - config_setup.py:
    - 対話式ウィザードで .env を初期作成 / 更新する CLI を提供。
    - 必要項目・説明・デフォルト・シークレット入力・選択肢をサポートし、最終的に .env を書き込む。
    - 書き込みテンプレートは .env ファイルにコメント付きで出力。

  - validate_config.py:
    - 起動前に .env や config/*.yaml の問題を検出する CLI を提供。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の検証、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と YAML パース検証（PyYAML がない場合はパース検証をスキップ）、本番環境向けのガード（LINE 通知・KILL_FLAG_CLEAR_ON_START の注意）を実装。
    - `--strict` オプションで警告を失敗扱いにできる。

- ロギングユーティリティ
  - utils/logging_setup.py:
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション、30日保持）を設定する汎用関数 `setup_logging()` を追加。
    - ログレベル・ログディレクトリは引数 > 環境変数 > デフォルトの順で解決。既存ハンドラがあればクリアして再設定する。
    - ログディレクトリ作成失敗やファイルハンドラ作成失敗時は警告を出し、コンソール出力のみで継続。

- プロセス管理ユーティリティ
  - utils/process_priority.py:
    - プラットフォーム差分を吸収してプロセス優先度（high/normal/low）を設定する `set_process_priority()` を追加。Windows と POSIX（Linux/Mac/FreeBSD）での実装を分岐。
    - CPU affinity を設定する `set_cpu_affinity()` を追加（N コアにピン留め）。権限不足や未サポート環境では警告を出してスキップ。
    - アクセス権限エラー等を安全にハンドリング。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py:
    - BUY シグナルの候補選定 select_candidates（スコア降順・タイブレークに signal_rank）を実装。
    - 等金額配分 calc_equal_weights と スコア加重 calc_score_weights（全スコアが 0 の場合は等金額にフォールバック）を実装。

  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中上限（max_sector_pct）をチェックし、既存保有比率が上限を超えるセクターの新規候補を除外するロジックを実装。unknown セクターは制限対象外。
    - calc_regime_multiplier: market レジーム（bull/neutral/bear）に応じて投下資金乗数を返す（デフォルト: bull=1.0, neutral=0.7, bear=0.3）。未知レジームは 1.0 にフォールバック（警告出力）。

  - portfolio/position_sizing.py:
    - calc_position_sizes: 各銘柄の発注株数を計算する主要ロジックを実装。
      - allocation_method に応じて "risk_based" / "equal" / "score" をサポート。
      - リスクベース計算（risk_pct, stop_loss_pct）や per-position, aggregate 上限（max_position_pct, max_utilization）を考慮。
      - 単元株（lot_size）で丸め、cost_buffer を用いた保守的コスト見積り、aggregate cap 超過時のスケールダウンと残余ロットの割当て（fractional remainder に基づく）を実装。
      - 価格欠損時のスキップやデバッグログ出力を含む。
      - 将来的な拡張（銘柄別 lot_size の導入）に関する TODO コメントあり。

- リサーチ / ファクター計算（骨格）
  - research/factor_research.py:
    - Momentum / Value / Volatility / Liquidity 等のファクター計算モジュールの骨格を追加。
    - DuckDB 接続を受け取り、prices_daily / raw_financials テーブルを参照して計算する設計方針を記載。
    - モメンタム系 calc_momentum の実装開始（注: ファイル末尾で実装が途中で切れている箇所あり。以降の関数は継続実装が必要）。

- ツール
  - tools/paper_verification_report.py:
    - Paper Trading 用検証レポート生成スクリプトを追加。
    - デフォルト DB パスは PAPER_TRADING_SQLITE_PATH または data/paper_trading.db。
    - 指標: 稼働率 (uptime_pct)、注文成功率 (fill_rate)、送信率 (send_rate)、レイテンシ（avg, max, P95）などを集計して表示。
    - 判定基準（閾値）を定義:
      - 稼働率 >= 99.0%
      - 注文成功率 >= 90.0%
      - 送信率 >= 95.0%
      - P95 レイテンシ <= 200 ms
    - 日付フィルタ（--from, --to）と P95 計算ロジックを実装。DB テーブルが存在しない場合は安全にハンドリングして N/A として扱う。

- 監視 DB 初期化ヘルパー
  - monitoring/monitoring_db.init_monitoring_db を起動スクリプトから呼び出して監視テーブルの存在を保証（冪等）する処理を導入。

### 変更 (Changed)
- なし（初回リリース想定）

### 修正 (Fixed)
- なし（初回リリース想定）

### 削除 (Removed)
- なし

### 注意事項 / 既知の制約 (Notes)
- run_monitoring は「監視用途の DB」を環境にかかわらず settings.sqlite_path（デフォルト data/monitoring.db）で扱うため、paper_trading 環境でも同じ監視 DB を参照する設計になっています（意図的な分離が必要な場合は設定で見直してください）。
- config.py の自動 .env ロードはプロジェクトルートの検出に .git または pyproject.toml を使用します。配布パッケージなどでプロジェクトルートが検出できない場合は自動ロードがスキップされます。
- research/factor_research.py の一部関数が未完（ファイル末尾で途中）であり、完全なファクター計算は今後の実装が必要。
- position_sizing や risk_adjustment 内に幾つかの TODO コメントあり（例: 価格欠損時のフォールバック、銘柄別 lot_size の対応など）。
- process_priority と CPU affinity の設定は権限やプラットフォームにより失敗する場合があり、その場合は警告を出してスキップします。
- ログディレクトリ作成やファイルハンドラ作成に失敗した場合はコンソール出力のみで継続する設計になっています。

### セキュリティ (Security)
- 本リリースで特に明示されたセキュリティ修正はありません。環境変数（API トークン等）は .env に平文で保存されるため、.env の取り扱い（Git へのコミット禁止等）に注意してください（config_setup.py にも同様の注意書きあり）。

---

作成者注: 上記はコードの構造・コメント・実装内容から推測してまとめた CHANGELOG です。実際のリリースノートとして公開する際は、コミット履歴や実際の変更一覧に基づいた確認・追記を推奨します。