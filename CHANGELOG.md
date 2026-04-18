# Changelog

すべての変更は Keep a Changelog の形式に従い、セマンティックバージョニングを使用します。
このファイルは人間向けの変更履歴です。

フォーマットの要点: 変更はカテゴリ別に整理（Added / Changed / Fixed / Deprecated / Removed / Security）。
各項目は該当するモジュール・スクリプトや振る舞いを簡潔に記載しています。

## [Unreleased]

（現在のベースは初回リリース v0.1.0 の内容です。今後の変更はここに記載してください）

## [0.1.0] - 2026-04-18

初回公開リリース。

### Added
- 基本アプリケーションパッケージを追加:
  - kabusys パッケージ本体（__version__ = "0.1.0"）。
- 環境設定・管理:
  - `kabusys.config`:
    - .env / .env.local の自動ロード（プロジェクトルートを .git または pyproject.toml で検出）。
    - .env のパース実装（export プレフィックス、クォート、インラインコメント対応、エスケープ処理）。
    - Settings クラスにより環境変数をラップ。J-Quants / kabuAPI / DB / ログ / 監視しきい値など多数のプロパティを提供。
    - `PAPER_FILL_MODE` 検証（instant/partial/never/reject の検査）。
    - 環境（KABUSYS_ENV）とログレベル（LOG_LEVEL）の検証ロジック。
  - `kabusys.config_setup`:
    - 対話式ウィザードで .env を作成・更新する CLI（複数項目、シークレット入力、デフォルト提示）。
- 設定検証ツール:
  - `kabusys.validate_config` CLI:
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL/DB パスの検証、config/*.yaml の存在チェック（PyYAML が無ければ警告）。
    - `--strict` オプションで警告を失敗扱いにできる。
- 実行系スクリプト:
  - `kabusys.run_execution`:
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV=paper_trading の場合、paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカクライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler/ExecutionEngine の組立て。
    - PID ファイル、停止フラグ（data/stop_requested.flag）検知とクリーンシャットダウン処理。
    - 起動時にプロセス優先度を "high" に設定。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を導入。
  - `kabusys.run_monitoring`:
    - SystemMonitor ポーリングループを起動するエントリポイント。
    - 環境にかかわらず監視は本番用 sqlite_path を使用することを明記。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出す。
    - プロセス優先度を "high" に設定、停止フラグ検知でループ終了。
    - SQLite / DuckDB の接続管理（起動時に monitoring テーブル初期化）。
- ユーティリティ:
  - `kabusys.utils.logging_setup`:
    - ルートロガーに対して StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション）を設定。
    - ログディレクトリ作成ロジック、ログレベル解決順（引数 > 環境変数 > デフォルト）。
    - ファイルハンドラ作成に失敗した場合は標準出力のみで継続。
    - デフォルト保持日数: 30 日。
  - `kabusys.utils.process_priority`:
    - Windows / POSIX の差分を吸収したプロセス優先度設定（high/normal/low）。
    - CPU affinity 設定ユーティリティ（最初の N コアにピン固定）。
    - 権限不足や未対応 OS でのフォールバックと警告。
- ポートフォリオ構築関連（純粋関数群）:
  - `kabusys.portfolio.portfolio_builder`:
    - select_candidates（スコア降順で候補選定、タイブレークルールあり）。
    - calc_equal_weights（等金額配分）。
    - calc_score_weights（スコア正規化、全スコアが 0 の場合は等配分にフォールバック）。
  - `kabusys.portfolio.risk_adjustment`:
    - apply_sector_cap（セクター集中制限、既存ポジションの時価から除外/ブロック処理、"unknown" セクターは除外しない）。
    - calc_regime_multiplier（market レジームに応じた投下資金乗数: bull/neutral/bear、未知レジームは警告のうえ 1.0 にフォールバック）。
  - `kabusys.portfolio.position_sizing`:
    - calc_position_sizes（allocation_method: risk_based / equal / score に対応）。
    - 単元株（lot_size）丸め、1 銘柄上限・aggregate cap（available_cash）によるスケールダウン、cost_buffer を考慮した安全なスケーリングと残差処理ロジックを実装。
    - 価格欠損時のスキップやログ出力。
- モニタリング/検証ツール:
  - `kabusys.tools.paper_verification_report`:
    - Paper Trading 用 SQLite を参照して検証レポートを生成する CLI。
    - 稼働率、注文成功率、送信率、リスク却下件数、レイテンシ（avg/max/P95）を集計。
    - 基準値（稼働率 99%、成功率 90%、送信率 95%、P95 レイテンシ 200ms）に基づく PASS/FAIL 判定。
    - 日付フィルタ（--from/--to）および DB ファイル指定（--db）に対応。
- Research（試験的）:
  - `kabusys.research.factor_research`:
    - ファクター計算モジュールのコード骨子を追加（モメンタム/MA/ATR/ボラティリティ等の定義、DuckDB 参照前提）。（一部実装は継続中）

### Changed
- 初回リリースのため、既存の振る舞いをまとめたドキュメント的説明をソース内に多数追加（モジュール説明、設計方針、TODO コメント等）。

### Fixed
- 初回リリース。目立ったバグ修正履歴はありません（以後のバージョンで追跡予定）。

### Deprecated
- なし。

### Removed
- なし。

### Security
- .env は絶対に Git にコミットしないよう README / config_setup のヘッダに明記。
- Settings._require() による必須環境変数未設定時の明示的な例外投げを採用。

---

注記:
- 実行系は本番（live）とペーパー（paper_trading）を明確に分離する設計になっています。ペーパートレード時は専用 SQLite（デフォルト: data/paper_trading.db）を利用し、本番 DB とは互いに影響しないようにしています。
- ロギングは stdout を基準にしつつ日次ローテーションでファイル出力を行うため、cron 等からの起動時でも一貫したログ入手が可能です。
- 今後のリリースでは factor_research の完全実装、ExecutionEngine / SystemMonitor の詳細なテストカバレッジ、及び broker client 周りのインタフェース安定化を予定しています。