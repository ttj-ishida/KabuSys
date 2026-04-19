# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
現在のバージョン: 0.1.0 — 2026-04-19

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-19

初回リリース。KabuSys 自動売買フレームワークの基礎機能を実装しました。以下の主要な機能・ユーティリティ・CLI を含みます。

### 追加 (Added)
- 基本パッケージとバージョン情報
  - src/kabusys/__init__.py にて __version__ = "0.1.0" を設定。

- 環境設定・読み込み
  - config モジュール（src/kabusys/config.py）
    - .env 自動読み込み（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - .env パース機能（クォート付き値、エクスポート形式、インラインコメント処理などに対応）。
    - 環境変数の取得ユーティリティ Settings クラス（各種設定プロパティ、バリデーション含む）。
    - PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL などの検証とデフォルト値を提供。
    - production / paper_trading 用の DB パスの分離（paper_trading 用 DB パス: PAPER_TRADING_SQLITE_PATH）。

- .env 設定ウィザード CLI
  - src/kabusys/config_setup.py
    - 対話式ウィザードで .env の生成・更新をサポート。
    - シークレット値はマスク表示、選択肢・デフォルト値の提示、保存前の確認あり。
    - 保存時に .env を適切なテンプレートで出力（.env を Git にコミットしない旨の注記）。

- 設定検証 CLI
  - src/kabusys/validate_config.py
    - 必須環境変数やファイル存在、KABUSYS_ENV の妥当性などを検査。
    - --strict モード（警告を FAIL 扱い）を提供。
    - YAML パーサ（PyYAML）がない場合は YAML 検証をスキップして警告表示。

- 実行・監視用起動スクリプト
  - src/kabusys/run_execution.py
    - ExecutionEngine 起動スクリプト。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory 経由でブローカークライアント生成。ExecutionEngine をデーモンスレッドで実行し、stop flag による安全停止をサポート。
    - PID ファイルおよび停止フラグの扱いを実装。
  - src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境に関わらず本番 sqlite_path を使用（監視用 DB の初期化を行う init_monitoring_db 呼び出し）。

- モニタリング DB 初期化フック（参照）
  - init_monitoring_db の呼び出しにより監視テーブルの存在を保証（冪等）。

- ユーティリティ
  - ロギング設定ユーティリティ（src/kabusys/utils/logging_setup.py）
    - StreamHandler（stdout）＋ TimedRotatingFileHandler（日次・30世代保持）をルートロガーに設定。
    - ログレベル・ログディレクトリの解決順を実装（引数 > 環境変数 > デフォルト）。
    - ログディレクトリ作成失敗時はファイルハンドラをスキップしてコンソール出力を継続。
  - プロセス優先度 / CPU affinity 設定ユーティリティ（src/kabusys/utils/process_priority.py）
    - Windows / POSIX の差分を吸収して set_process_priority を実装（"high"/"normal"/"low"）。
    - set_cpu_affinity によるコア固定をサポート（利用可能コア数のチェック、エラー時は警告でスキップ）。

- ポートフォリオ構築関連（純粋関数群）
  - src/kabusys/portfolio/portfolio_builder.py
    - select_candidates（スコア降順、同点時は signal_rank を使用したタイブレーク）。
    - calc_equal_weights、calc_score_weights（スコア全て0のとき等配分にフォールバック）。
  - src/kabusys/portfolio/risk_adjustment.py
    - apply_sector_cap（セクター集中上限のチェック。unknown セクターは制限対象外）。
    - calc_regime_multiplier（regime に応じた投下資金乗数。未知レジームは 1.0 でフォールバック）。
  - src/kabusys/portfolio/position_sizing.py
    - calc_position_sizes（allocation_method="risk_based"|"equal"|"score" に対応）。
    - lot_size（単元）丸め、per-position と aggregate のキャップ、cost_buffer を加味した保守的見積り、スケーリング＆端数配分ロジックを実装。

- 解析 / レポート
  - src/kabusys/tools/paper_verification_report.py
    - Paper Trading 検証レポート生成 CLI。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等を集計し PASS/FAIL を判定（デフォルト閾値を定義）。
    - 日付フィルタ、DB パス指定（環境変数/オプション）対応。
    - P95 計算ユーティリティを実装。

- 研究用モジュール（部分実装）
  - src/kabusys/research/factor_research.py
    - モメンタム・ボラティリティ等の計算方針と定数を実装（DuckDB 接続前提）。一部関数は実装途中（ファイルは追加済み）。

### 変更 (Changed)
（初回リリースにつき「追加」が中心。設計上の重要な挙動について記載します）
- .env 自動読み込みの優先順と保護
  - OS 環境変数を保護して .env.local（override=True）→ .env（override=False）で読み込む設計により、CI/システム環境を上書きしないようにしています。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用）。
- ログ出力
  - コンソールは stdout を使用（stderr ではない）。
  - 既にハンドラが設定されている場合は一旦クリアして再設定（多重ロギング防止）。
- Execution / Monitoring の DB 接続方針
  - run_execution: paper_trading の場合は paper_sqlite_path（分離）を使用。
  - run_monitoring: 監視は環境に依存せず本番 sqlite_path を使用するよう明確化。
- 停止フラグ（stop_requested.flag / kill.flag）の扱いを明確化
  - スクリプト起動中に停止フラグを検知した際、ループを終了または ExecutionEngine を停止する挙動を実装。

### 修正 (Fixed)
- 環境変数パースの堅牢化
  - クォート付き文字列内のバックスラッシュエスケープや、クォート無し時のインラインコメント扱いの改善を実装。
- ログディレクトリ作成失敗時のフォールバック
  - ディレクトリ作成に失敗した場合はファイルハンドラをスキップし、コンソール出力で継続するように修正（例外でクラッシュしない）。
- プロセス優先度設定の安全化
  - 権限不足・未実装 API 等で失敗しても警告を出して処理を継続するように変更。
- DB 接続のクローズ処理を finally で保証
  - run_execution / run_monitoring で sqlite3/duckdb 接続を確実にクローズするように保証。
- validate_config
  - PyYAML 未インストール環境で YAML チェックをスキップ、警告を出すように変更（依存性がなくても実行できる）。

### 既知の問題 / TODO
- apply_sector_cap 内で price が 0.0 の場合に露出を過少見積もる可能性がある点をコメントで指摘（将来的に前日終値や取得原価でのフォールバックを検討）。
- position_sizing: 将来的な拡張（銘柄別 lot_size のサポート）に関する TODO を残しています。
- research/factor_research.py はファイル末尾で実装が途中で切れている（calc_momentum 等の一部が未完）。研究系機能は今後の実装予定。
- ExecutionEngine / 実際のブローカークライアント（BrokerClientFactory, ExecutionEngine, OrderManager 等）はこのリリースで参照されているが、実装詳細や外部 API との連携の挙動は注意が必要（テスト推奨）。

### セキュリティ (Security)
- .env を絶対にリポジトリにコミットしないよう明記（config_setup のヘッダに注意書き）。
- シークレット環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）は Settings._require で必須化しているが、取り扱いには注意が必要。

---

今後のリリースでは、研究モジュールの実装完了・ユニットテスト追加、ブローカー接続のモック/実装改善、性能・エラー観測強化を予定しています。必要があれば、この CHANGELOG を英語版に翻訳することも可能です。