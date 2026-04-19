# CHANGELOG

すべての日付はリリース日を示します。フォーマットは「Keep a Changelog」に準拠します。

## [0.1.0] - 2026-04-19

初回リリース。KabuSys のコアユーティリティ、実行/監視スクリプト、ポートフォリオ構築、設定管理、検証ツール、およびペーパートレード用レポート等を導入しました。

### 追加 (Added)
- 基本パッケージ情報
  - パッケージのバージョンを `__version__ = "0.1.0"` として追加。

- 実行・監視ランチャー
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory 経由のブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て、ExecutionEngine の起動/停止ロジック（スレッド駆動）を実装。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止フラグ（data/stop_requested.flag）検知による安全終了処理。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境設定に関わらず本番用 sqlite_path を使用する設計（監視 DB を分離しない方針）。
    - 起動時にプロセス優先度を "high" に設定、停止フラグ検知で安全終了。

- 設定管理・読み込み
  - config.py: 環境変数 / .env 自動読み込み機能を追加。
    - プロジェクトルートを .git または pyproject.toml で検出し、.env / .env.local を適切な優先順位で読み込む（OS 環境変数を保護）。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD` により自動読み込み停止可能。
    - Settings クラスで各種設定値をプロパティとして提供（DB パス、API トークン、Paper Trading モード、しきい値類、KABUSYS_ENV/LOG_LEVEL 検証等）。
    - `paper_fill_mode` に対する入力検証（有効値: instant|partial|never|reject）。
    - `is_live` / `is_paper` / `is_dev` のヘルパープロパティを提供。

- 設定ウィザード & 検証 CLI
  - config_setup.py: 対話式の .env 作成/更新ウィザードを追加（対話入力、既存値読み込み、ファイル書込）。
  - validate_config.py: 起動前の設定検証ツールを追加。
    - 必須環境変数の存在チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック。
    - config/*.yaml の存在確認（PyYAML があればパース検証を実行）。
    - `--strict` オプションで警告を失敗として扱うモードを提供。

- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。
    - stdout への StreamHandler と日次ローテートの TimedRotatingFileHandler（デフォルト logs/<app>.log、30日保持）を設定。
    - LOG_LEVEL / LOG_DIR の環境変数または引数で上書き可能。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
  - utils/process_priority.py: プラットフォーム差分を吸収したプロセス優先度（nice / Windows 優先度）および CPU affinity 設定ユーティリティを追加。
    - set_process_priority(level: "high"|"normal"|"low")
    - set_cpu_affinity(cpu_count: int | None)

- ポートフォリオ構築モジュール
  - portfolio/portfolio_builder.py
    - 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を追加。
    - スコアが全て 0 の場合は等金額配分にフォールバック（警告ログ）。
  - portfolio/risk_adjustment.py
    - セクター集中制限適用 (apply_sector_cap)、市場レジームに応じた乗数計算 (calc_regime_multiplier) を追加。
    - 未知レジームは 1.0 にフォールバックし警告ログを出力。
  - portfolio/position_sizing.py
    - position sizing ロジックを実装（allocation_method: "risk_based" / "equal" / "score"）。
    - 単元株（lot_size）丸め、1銘柄上限・集約上限・cost_buffer 考慮、スケールダウンロジック（割合スケーリング + 端数補正）を実装。

- 研究 / ツール
  - research/factor_research.py: DuckDB を用いたファクタ計算モジュールの雛形とモメンタム指標計算ロジックの導入（モジュール構造・定数を含む）。※ファイル末尾は一部未完（続き実装予定）。
  - tools/paper_verification_report.py: ペーパートレード検証レポート生成スクリプトを追加。
    - 集計指標: 稼働率 (uptime)、注文成功率・送信率、リスク却下数、レイテンシ（avg/max/P95）。
    - 判定閾値を定義（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）。
    - CLI 引数で期間指定 (--from / --to) と DB パス指定 (--db) をサポート。

- データベース初期化
  - monitoring/monitoring_db.py の init_monitoring_db 呼び出しを各ランチャーで使用し、監視テーブルの初期化を保証（冪等）。

### 変更 (Changed)
- 監視の DB 利用方針
  - run_monitoring は KABUSYS_ENV に依らず本番用の sqlite_path を参照する旨を明記（監視データは本番 DB を使用するデザイン）。一方で run_execution は paper_trading 時に専用 DB を用いることで発注履歴等を分離。

- ロギング挙動
  - 既にハンドラが設定されている場合は一度クリアしてから再設定することで二重ログ出力を防止。

### 修正 (Fixed)
- 環境変数パーサの堅牢性向上
  - config._parse_env_line にてクォート内のバックスラッシュエスケープ処理、行内コメントの扱い、export プレフィックス対応等を実装し .env の多様な書式に対応。

- ポジションサイズ計算の安定化
  - aggregate cap 超過時のスケーリング処理で端数配分アルゴリズム（fractional remainder）を導入し、残余資金を効率的に配分。

- プロセス優先度 / CPU affinity のフォールバック
  - 対応できない OS / 権限不足の場合に警告を出してスキップするようにし、起動失敗を防止。

### 注意事項 (Important)
- 自動 .env ロードはデフォルトで有効。テスト等で無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- run_monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使用します。監視データを分離したい場合は設計に留意してください。
- config.validate_config の --strict モードは警告を FAIL 扱いにするため、本番導入時のチェック運用に有効です。
- research/factor_research.py は一部実装が続く可能性があります（末尾が未完の状態のため、現状はモジュール内の一部機能のみ利用可能）。

### 既知の未実装 / 予定 (Unreleased / Todo)
- factor_research.py の完全実装（ファクター計算の SQL/集計ロジックの最終化）。
- ブローカークライアント実装の詳細（Mock / 実ブローカーの具体的実装は別モジュールで管理）。
- 銘柄別 lot_size のサポート（将来的にマスタ情報を参照する設計を想定）。

---

以上が初回リリース (0.1.0) の主な変更点です。リリース後のフィードバックに基づき、ドキュメント・検証や安定化を進めていきます。