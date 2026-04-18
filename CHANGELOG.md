# Changelog

すべての注目すべき変更を記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

現在のリリース履歴:

## [0.1.0] - 2026-04-18

### 追加 (Added)
- 初回リリース。システム全体の主要コンポーネントとユーティリティを追加。
- 実行スクリプト／エントリポイントを追加:
  - run_execution.py: ExecutionEngine 起動スクリプト（KABUSYS_ENV に応じて本番 DB / ペーパートレード DB を分離して使用）。
  - run_monitoring.py: SystemMonitor 用ポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き可能、デフォルト 60 秒）。
- 設定関連 CLI を追加:
  - config_setup.py: インタラクティブな .env 作成・更新ウィザード（対話式質問、シークレットマスク、保存機能）。
  - validate_config.py: 起動前設定検証ツール（必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DBパス/設定ファイル存在確認、--strict モード）。
- 設定管理モジュールを追加:
  - config.py: Settings クラスと自動 .env ロード機能（プロジェクトルート探索、.env/.env.local の読込順、OS 環境変数保護）。
  - .env パースの強化（クォート処理、export 形式対応、インラインコメント処理、保護付き上書き）。
  - Settings に PAPER_TRADING 用の paper_sqlite_path / PAPER_FILL_MODE 等のプロパティを追加。
- ロギング・プロセス管理ユーティリティを追加:
  - utils/logging_setup.py: 一貫したログ設定関数 setup_logging を追加（stdout 出力 + 日次ローテートファイル出力、ログディレクトリ作成失敗時はファイル出力をスキップ、30 日保持）。
  - utils/process_priority.py: プラットフォーム差分を吸収するプロセス優先度設定と CPU affinity 設定を追加（Windows / POSIX 対応、権限不足時は警告でスキップ）。
- ポートフォリオ構築関連の純粋関数群を追加（DB 参照なし、メモリ内計算）:
  - portfolio/portfolio_builder.py: 候補選定 (select_candidates)、等配分 / スコア配分 (calc_equal_weights / calc_score_weights)。
  - portfolio/position_sizing.py: 発注株数計算（risk_based / equal / score、単元株丸め、aggregate cap スケールダウン、cost_buffer 対応）。
  - portfolio/risk_adjustment.py: セクター集中制限 (apply_sector_cap)、レジーム乗数 (calc_regime_multiplier)。
- Paper Trading 検証ツールを追加:
  - tools/paper_verification_report.py: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）から各種指標（稼働率／注文成功率／送信率／レイテンシ(P95)／リスク却下数）を集計してレポート出力。閾値判定を行い PASS/FAIL を表示。
- 研究用モジュールの雛形を追加:
  - research/factor_research.py: DuckDB 接続を受け取ってファクター計算を行う設計（モメンタム等の定義と計算方針のドキュメントを含む）。
- パッケージ初期化:
  - __init__.py にバージョン情報 __version__ = "0.1.0" を追加。

### 変更 (Changed)
- DB 周りの分離設計:
  - run_execution は KABUSYS_ENV=paper_trading の場合、paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番データベースと完全に分離。
  - run_monitoring は環境にかかわらず本番の sqlite_path（監視 DB）を使用して監視データを一元管理。
- ログ振る舞いの標準化:
  - ログ出力はデフォルトで stdout に StreamHandler を設定（cron/Task Scheduler からの起動時のリダイレクト運用を考慮）。
  - ログレベル解決順: 関数引数 → 環境変数 LOG_LEVEL → デフォルト "INFO"。
  - ログディレクトリ解決順: 関数引数 → 環境変数 LOG_DIR → デフォルト "logs/"。
- プロセス優先度設定の順序:
  - 起動スクリプトの最初で set_process_priority("high") を呼び出すようにして優先度を高く設定する。
- .env 自動読み込みの挙動:
  - プロジェクトルート検出（.git または pyproject.toml を基準）に基づき .env / .env.local を自動読み込み。OS 環境変数は保護され、必要に応じて .env.local で上書き可能。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。

### 修正 (Fixed)
- run_monitoring の MONITOR_POLL_INTERVAL 取り扱い:
  - 環境変数からの読み取りで数値変換エラーや 0/負数指定時に警告を出しデフォルト（60 秒）へフォールバックするようにして time.sleep での ValueError を回避。
- run_execution / run_monitoring の停止制御:
  - data/stop_requested.flag の検出により安全にループまたはエンジンを停止する仕組みを導入。実行中は pid_file を管理し、スレッド join の待機タイムアウトを入れてクリーンな終了を図る。
- validate_config の堅牢化:
  - 設定ファイルの存在・パース検査を追加。PyYAML 未インストール時は YAML 検証をスキップして警告を出す。
  - --strict フラグで警告も失敗扱いにできるようにした。
- Paper Trading レポート:
  - latency の P95 計算、平均・最大レイテンシの算出、データ欠損時の安全なフォールバック（N/A 表示）を実装。
- 環境変数パースの改善:
  - export プレフィックス、シングル/ダブルクォート内のエスケープ処理、インラインコメントの扱いを正しく処理するようにして .env の互換性を向上。

### 既知の注意点 / 制約 (Known issues / Notes)
- process_priority・cpu_affinity は権限不足やプラットフォーム差異により失敗する可能性があり、その場合は警告を出して処理をスキップします（アプリケーションは継続します）。
- apply_sector_cap は price_map に価格が欠損している場合にエクスポージャーを過少見積もる可能性があり、将来的にフォールバック価格（前日終値や取得原価）を導入する予定。
- position_sizing の単元株（lot_size）は現状共通値（デフォルト 100）で動作。将来的に銘柄別単元をサポートする予定。

### セキュリティ (Security)
- なし（このリリースで報告されたセキュリティ修正はありません）。

---

今後のリリースでは、テストカバレッジの拡充、銘柄別 lot_size の導入、価格フォールバックの改善、より詳細な監視アラート/通知連携（LINE など）の実装を予定しています。