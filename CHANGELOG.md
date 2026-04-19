CHANGELOG
=========

すべての重要な変更点を記録します。本ファイルは Keep a Changelog の形式に準拠しています。
日付はリポジトリ内の現行コードから推測して付与しています。

[Unreleased]
-------------

- （現行作業中 / 未リリースの変更点はありません）

[0.1.0] - 2026-04-19
-------------------

Added
- 全体
  - 初期リリース。日本株自動売買システム「KabuSys」の基本コンポーネントを追加。
  - パッケージバージョンを __version__ = "0.1.0" として設定。

- 起動スクリプト / 実行系
  - run_execution.py
    - ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV=paper_trading 時は paper-trading 専用 SQLite（data/paper_trading.db）を使用し、本番 DB と分離する仕組みを実装。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立てを行い ExecutionEngine をスレッドで起動。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）を監視して安全に停止する仕組みを追加。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker など）を提供し、initial_portfolio_value を broker.get_available_cash() で初期化。

  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計（監視データは一貫した DB に保存）。
    - 停止フラグ（data/stop_requested.flag）を検知してループを終了。KeyboardInterrupt にも対応。
    - check_once() 呼び出し時の例外を捕捉して次ポーリングへフォールバック。

- 設定管理 / ユーティリティ
  - config.py
    - 環境変数読み込みと Settings クラスを実装。
    - .env 自動ロード機能：プロジェクトルート（.git または pyproject.toml）を探索して .env/.env.local を読み込む。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env パースは export プレフィックス、クォート文字（シングル/ダブル）、バックスラッシュエスケープ、インラインコメントに対応。
    - Settings に多くのプロパティを提供（J-Quants / kabu API / LINE / DB パス / PID/Kill flag / 閾値 / 環境種別検証など）。
    - PAPER_FILL_MODE に対するバリデーション（instant/partial/never/reject）。
    - env 値の妥当性チェック（KABUSYS_ENV、LOG_LEVEL 等）を実装。

  - config_setup.py
    - .env 初期作成・更新の対話式ウィザードを実装。
    - 各設定項目のラベル、説明、選択肢、シークレット取り扱いをサポート。
    - 既存 .env の読み込みと Enter による既存値再利用、保存前の確認ダイアログを実装。

  - validate_config.py
    - 起動前に .env と config/*.yaml の整合性を検証する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL 検証、DB パスの親ディレクトリ確認、config/*.yaml の存在とパース（PyYAML があればパースする）を実行。
    - --strict オプションで警告を FAIL 扱いにできる。

  - utils/logging_setup.py
    - 統一的なログ設定ユーティリティを追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）をルートロガーに設定。
    - ログレベル/ログディレクトリの解決順を定義（引数 > 環境変数 > デフォルト）。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続するフォールバックを実装。

  - utils/process_priority.py
    - クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定を実装（set_process_priority）。
    - CPU affinity を制限する set_cpu_affinity を追加。アクセス権限不足や未サポート環境では警告を出してスキップ。

- ポートフォリオ / リスク / ポジションサイズ
  - portfolio/portfolio_builder.py
    - select_candidates、calc_equal_weights、calc_score_weights を追加。スコアが全て 0 の場合は等重にフォールバック。
  - portfolio/risk_adjustment.py
    - apply_sector_cap によるセクター集中抑制ロジックを追加（当日売却予定の銘柄を除外可能、"unknown" セクターはチェック除外）。
    - calc_regime_multiplier によるレジーム乗数を提供（bull/neutral/bear）。
    - 未取得価格（0.0）の扱いや未知レジームのフォールバックについてログと注記を追加。
  - portfolio/position_sizing.py
    - calc_position_sizes を実装。allocation_method として "risk_based" / "equal" / "score" をサポート。
    - lot_size（単元）丸め、per-position 上限、aggregate cap（available_cash 超過時のスケールダウン）、cost_buffer による保守的見積り、残差処理のための再配分ロジックを実装。
    - 価格欠損時のスキップやゼロ値保護、将来的な銘柄別 lot_size 拡張に関する TODO コメントを追加。

- モニタリング / レポート
  - monitoring.monitoring_db（初期化呼び出しを run_* スクリプトから行う整合性）を利用して監視テーブルの存在を保証（init_monitoring_db を idempotent に呼ぶ）。
  - tools/paper_verification_report.py
    - ペーパートレード検証用レポート作成スクリプトを追加。
    - システム稼働率、注文成功率（fill）、送信率（send）、リスク却下数、API レイテンシ（avg/max/P95）を集計して判定（PASS/FAIL）する。
    - P95 計算、日付フィルタ、各種閾値（稼働率 99%、fill 90%、send 95%、P95 200ms）を実装。
    - DB 存在チェックとエラーメッセージ整備、コマンドラインオプション（--from/--to/--db）を提供。

Changed
- DB/初期化
  - 監視用 DB 初期化は起動時に冪等に呼ばれるように整理（init_monitoring_db を各起動スクリプトで呼出し）。
- ログ出力
  - コンソール出力は stdout を使用（stderr ではなく）し、タスクスケジューラや cron からのリダイレクト運用を考慮。
- .env 読み込み優先度
  - OS 環境変数 > .env.local > .env の順で読み込む仕様を明示（.env.local は既存値を上書き）。

Fixed
- run_monitoring.py
  - MONITOR_POLL_INTERVAL に不正な値（非整数や 0/負値）が与えられた場合にデフォルト（60秒）へフォールバックし、警告を出すように修正（time.sleep に渡せない値の回避）。
- config.py/.env パーサ
  - export プレフィックスやクォート内のエスケープ、インラインコメントの扱いなどを堅牢化。無効行や空キーの扱いを明確化。

Known issues / Notes
- research/factor_research.py はファイル末尾が途中で切れている（start_da で中断）。ファクター計算の実装が未完了（将来的な追加対象）。
- risk_adjustment.apply_sector_cap: price_map に価格が欠損（0.0）の場合にエクスポージャーが過少見積もられる可能性があり、将来の価格フォールバック戦略を検討する TODO が残る。
- position_sizing: 銘柄ごとの単元（lot_size）を将来サポートする旨の TODO コメントあり。

Security
- 本リリースでは特にセキュリティ脆弱性に関する注記はないが、.env ファイルは絶対に Git にコミットしない旨の注意を README/生成ヘッダに記載。

Footer
- この CHANGELOG はコードベースの内容から推測して作成しています。実際のコミット履歴や意図したリリースノートと差異がある場合がありますので、リリース時には実際の変更内容に合わせて調整してください。