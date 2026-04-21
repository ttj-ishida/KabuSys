# CHANGELOG

すべての注目すべき変更を記録します。フォーマットは「Keep a Changelog」に準拠しています。

## [0.1.0] - 2026-04-21

### 追加 (Added)
- 初期リリースとして以下の主要機能・モジュールを追加しました。
  - 環境設定・読み込み
    - 自動 .env ロード機能を実装（プロジェクトルートを自動検出して `.env` / `.env.local` を読み込む）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動読み込みを無効化可能。
    - .env パーサーを実装（`export` プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いに対応）。
    - Settings クラスを提供し、環境変数経由でアプリ設定を型付きプロパティとして取得可能（DB パス、API トークン、ログレベル、環境判定など）。
  - 設定支援 / 検証 CLI
    - 対話式ウィザード `kabusys.config_setup` を追加し、`.env` の作成/更新を支援（選択肢表示・シークレットマスク・確認保存）。
    - `kabusys.validate_config` CLI を追加し、.env や `config/*.yaml` の存在・基本整合性を検証（`--strict` オプションで警告も失敗扱いにできる）。
  - 実行関連スクリプト
    - `run_execution` スクリプト（ExecutionEngine 起動）を追加。
      - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全に分離。
      - BrokerClientFactory によるブローカークライアント初期化、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、Engine の起動・停止制御を実装。
      - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）に対応。
    - `run_monitoring` スクリプト（SystemMonitor のポーリングループ）を追加。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値時は警告してデフォルトを使用。
      - 監視は環境にかかわらず本番用 sqlite_path を使用する設計。
      - 停止フラグ検出、例外からの回復ログ、プロセス優先度設定、接続クローズ処理を実装。
  - ロギング・プロセス制御ユーティリティ
    - `kabusys.utils.logging_setup` を追加。
      - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション）を設定。
      - ログディレクトリ作成失敗時はファイル出力をスキップするフォールバック実装。
      - 既存ハンドラをクリアして二重出力を防止。
    - `kabusys.utils.process_priority` を追加。
      - Windows / POSIX の差分を吸収してプロセス優先度（high/normal/low）と CPU affinity を設定するユーティリティを提供。
      - 権限不足や未対応 OS の場合は警告してスキップ。
  - ポートフォリオ構築（純関数群）
    - `kabusys.portfolio` パッケージを追加（エクスポート: select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier）。
    - portfolio_builder:
      - シグナルのソート/候補選定、等配分・スコア加重配分の実装（スコアが全て 0 の場合は等配分にフォールバックして警告）。
    - risk_adjustment:
      - セクター集中制限（apply_sector_cap）と市場レジーム乗数（calc_regime_multiplier）を実装（未知レジームはフォールバック）。
    - position_sizing:
      - 発注株数算出ロジックを実装（allocation_method: "risk_based" / "equal" / "score" 対応、lot_size 切り捨て、aggregate cap によるスケールダウン、cost_buffer を考慮した分配ロジックなど）。
  - 研究・ツール
    - `kabusys.research.factor_research` の骨組みを追加（DuckDB を用いたモメンタム等のファクター計算を想定）。実装は一部（続き実装予定）。
    - `kabusys.tools.paper_verification_report` を追加。Paper Trading の検証レポート生成 (稼働率、注文成功率、送信率、レイテンシ P95 など)、しきい値判定とテキスト出力を実装。DB が存在しない／テーブルがない場合に耐性あり。
  - その他
    - パッケージバージョンを __version__ = "0.1.0" に設定。

### 変更 (Changed)
- ロギング:
  - StreamHandler を stdout に出力するように変更（cron/Task Scheduler などで stdout/stderr を統一する運用想定）。
  - 日次ローテーションのログファイルはデフォルトで logs/ ディレクトリに保存し、30 日分のバックアップを保持するように設定。
  - 既存ハンドラをフラッシュ・クローズしてから削除することで多重ハンドラ設定を防止。
- DB 接続ポリシー:
  - `run_monitoring` は KABUSYS_ENV に関係なく監視用の本番 sqlite_path を使用する仕様（監視データは本番 DB に記録されることを明示）。
  - `run_execution` は paper_trading 実行時に専用の paper_sqlite_path を使ってデータ分離する仕様。
- .env 読み込み順:
  - OS 環境 > .env.local > .env の順で解決。OS 環境（既存のキー）は保護され、強制上書きを防止。

### 修正 (Fixed)
- MONITOR_POLL_INTERVAL の不正値に対して ValueError を避け、警告ログを出して既定値にフォールバックするように修正。
- .env パーサー:
  - クォート内のバックスラッシュエスケープや、コメントの扱い（クォート有無での違い）を正しく処理するよう改良。
- `validate_config`:
  - PyYAML 未インストール時は YAML 検証をスキップして警告を出すようにして、依存がない環境でもコマンド実行可能にした。
- `paper_verification_report`:
  - DB 内のテーブルが存在しない場合でも例外で停止しないよう try/except により耐性を追加し、空データ扱いにフォールバック。

### 注意事項 / 既知の制限 (Known issues)
- research/factor_research は実装の途中（ファイル末尾が未完）。ファクター計算の詳細実装は今後のリリースで追加予定。
- apply_sector_cap は price が欠損（0.0）だとエクスポージャーが過少評価されるリスクがあり、将来的にフォールバック価格の導入を検討。
- process_priority や set_cpu_affinity は権限やプラットフォームによって失敗する可能性があります（失敗時は警告でスキップ）。

### 文書化 (Documentation)
- 各 CLI スクリプト（config_setup, validate_config, tools.paper_verification_report）の使い方をソースドキュメントに記載。
- PortfolioConstruction.md / StrategyModel.md 等の参照がソース内コメントで記載されており、設計指針を明示。

---

今後の予定:
- research/factor_research の完成、ファクター計算のカバレッジ拡張。
- SystemMonitor / ExecutionEngine 周りのテスト追加と堅牢化。
- トレード実行・ブローカークライアントのモック拡張、ペーパートレード導線の改善。

（この CHANGELOG はソースコードから推測して作成しています。実際の変更履歴やリリースノートと差異がある場合があります。）