# CHANGELOG

すべての重要な変更点を記録します。本ファイルは Keep a Changelog の形式に準拠しています。  

リリース日はリポジトリ内の現行コードを基に推測して記載しています。

---

## [0.1.0] - 2026-04-19

初回公開リリース。主要な CLI / ランタイムスクリプト、設定管理、ポートフォリオ构築、ユーティリティ群、監視・検証ツールを追加。

### Added
- 全体
  - パッケージ初期バージョンとして基本コンポーネントを実装（src/kabusys/*）。
  - __version__ を 0.1.0 に設定（src/kabusys/__init__.py）。

- 設定関連
  - Settings クラスを実装し、環境変数 / .env を統合的に扱えるように（src/kabusys/config.py）。
    - .env 自動読み込み機能（プロジェクトルートを .git または pyproject.toml で探索）。
    - .env/.env.local の読み込み順と OS 環境変数の保護（上書き制御）。
    - 環境変数のパースは export プレフィックス、クォート、エスケープ、インラインコメント（スペース等）に対応。
    - 各種設定プロパティ（DB パス、KABUSYS_ENV、ログレベル、paper trading 用設定など）を提供。
  - 対話式環境設定ウィザードを追加（python -m kabusys.config_setup）。
    - .env の初期作成・更新を補助、シークレット値はマスクして表示、保存テンプレートを生成（src/kabusys/config_setup.py）。
  - 設定検証 CLI を追加（python -m kabusys.validate_config）。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスや config/*.yaml の存在・パースチェック、KABUSYS_ENV=live 向けのガード検査。
    - --strict オプションで警告を失敗扱いにできる（src/kabusys/validate_config.py）。

- 実行系 / 監視
  - ExecutionEngine 起動スクリプトを追加（src/kabusys/run_execution.py）。
    - 起動時にプロセス優先度を high に設定。
    - KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite（data/paper_trading.db）を使用して本番 DB と完全分離。
    - BrokerClientFactory を用いて環境に応じたブローカークライアントを生成し、OrderManager / RiskManager / Reconciler / ExecutionEngine を組み立て、デーモンスレッドで実行。
    - 停止フラグ (data/stop_requested.flag) を監視して安全に停止。
  - SystemMonitor 起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値（0以下や非数）はデフォルトにフォールバックして警告。
    - 監視側は環境にかかわらず本番 sqlite_path を使用して監視データを記録する設計。
    - 起動時にプロセス優先度を high に設定、停止フラグ検出でループを終了（src/kabusys/run_monitoring.py）。

- ツール
  - Paper Trading 検証レポート生成スクリプトを追加（python -m kabusys.tools.paper_verification_report）。
    - 稼働率、注文成功率（fill）、送信率（send）、P95 レイテンシなどを SQLite の paper_trading DB から集計して判定レポートを出力（src/kabusys/tools/paper_verification_report.py）。
    - 日付フィルタ、閾値（稼働率 99% / 成立率 90% / 送信率 95% / P95 レイテンシ 200ms）を定義。

- ポートフォリオ構築（純関数群）
  - 候補選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: スコア降順、タイブレークに signal_rank を使用。
    - calc_equal_weights / calc_score_weights（スコア全0 の場合は等配分へフォールバック）。
  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 既存ポジションからセクター別エクスポージャを計算し上限超過のセクターの新規候補を除外（unknown セクターは除外対象外）。
    - calc_regime_multiplier: 'bull'/'neutral'/'bear' に応じた乗数（未定義値は警告とともに 1.0 にフォールバック）。
  - ポジションサイズ計算（src/kabusys/portfolio/position_sizing.py）
    - risk_based / equal / score の allocation_method をサポート。
    - lot_size（単元）丸め、1銘柄上限・aggregate cap の適用、cost_buffer を用いた保守的見積り、スケーリング時の端数再配分ロジック。

- ユーティリティ
  - ロギングセットアップユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - stdout StreamHandler と日次ローテーティングのファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。
    - ログディレクトリ作成が失敗した場合はファイル出力をスキップしてコンソール出力のみで継続。
    - LOG_LEVEL / LOG_DIR の解決順を実装。
  - プロセス優先度・CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX（Linux / macOS / FreeBSD）差分を吸収して nice / priority を設定。
    - set_process_priority("high"|"normal"|"low")、set_cpu_affinity(N) を提供。
    - 権限不足や未対応 OS 時は警告を出して安全にスキップ。

- データアクセス
  - DuckDB の接続を受け取って分析処理を行う構成（各所で duckdb 接続を受け渡し）。
  - 監視テーブルの初期化呼び出し（init_monitoring_db）が起動時に実行されることでテーブル存在を保証（冪等処理）。

### Changed
- 設計・運用ルール
  - Paper Trading と本番 DB を明確に分離する方針を採用（Execution 起動時に settings.is_paper を見て専用 SQLite を使用）。
  - 監視（monitoring）は環境に依存せず常に本番用 sqlite_path を用いる旨を明記（run_monitoring）。
  - ログは stdout（cron/Task Scheduler のリダイレクトに配慮）へ出力するようデフォルト設定。

### Fixed / Hardening
- 環境変数パーサ
  - .env のパースでクォート内部のバックスラッシュエスケープと対応する閉じクォートの検出、インラインコメントの扱いを改善（src/kabusys/config.py）。
  - .env の読み込みで OS 環境変数を保護する protected オプションを導入し、意図しない上書きを防止。
- run_monitoring のポーリング間隔
  - MONITOR_POLL_INTERVAL に不正な値（負数・0・非数）が与えられた場合にデフォルトへフォールバックして警告する保護を追加。
- process_priority / cpu_affinity
  - 権限不足や未サポート環境での失敗を安全に扱い、例外を捕捉して警告を出すように修正。
- ロギング
  - ログディレクトリ作成に失敗した場合でも起動を継続できるようにし、ファイルハンドラ作成失敗時にはコンソールのみで動作。

### Notes / Implementation details
- run_execution はエンジンをデーモン・スレッドで実行し、停止フラグを検知したら Engine.stop() を呼んで安全停止を試みる実装。
- RiskManager のデフォルト設定例（max_position_pct, max_utilization, rate limits, circuit breaker 等）を Execution 起動時に組み立てる（初期ポートフォリオ値に broker.get_available_cash() を使用）。
- portfolio のアルゴリズムはドメイン設計文書（PortfolioConstruction.md, StrategyModel.md 等）に基づく旨の注釈をコード内に記載。
- research/factor_research.py はファクター計算の骨格を追加（DuckDB を用いた prices_daily / raw_financials 参照想定）。実装の一部（関数末尾）は未完（今後の実装想定）。

---

今後のリリース案:
- factor_research の完全実装、テストケース追加
- ExecutionEngine / BrokerClient 実装の結合テスト、トランザクションや永続化の強化
- ロギング周りの監視・外部集約（例: filebeat / cloud logging）対応
- .env の暗号化保管やシークレット管理（Vault 等）の導入検討

---

この CHANGELOG はコードから推測して作成しています。実際のコミット履歴や意図した変更点がある場合は適宜更新してください。