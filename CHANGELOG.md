# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に準拠して記載しています。  
バージョン番号はパッケージの __version__（src/kabusys/__init__.py）に準拠しています。

## [Unreleased]

### 追加
- なし

### 変更 / 修正
- なし

---

## [0.1.0] - 初回リリース
初回公開。日本株自動売買システム KabuSys のコアユーティリティ・実行スクリプト・ポートフォリオ構築ロジック・ツール類をまとめて提供します。

### 追加
- 実行・運用用スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading 時はペーパートレード用の DB を使用し MockBrokerClient を使うことを想定（data/paper_trading.db に記録）。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境に依らず本番 sqlite_path を使用する実装。
- 設定・環境変数管理
  - config.py: Settings クラスを追加。.env ファイルの自動読み込み機能（プロジェクトルート検出 .git / pyproject.toml）、詳細な .env パーサ（クォート、エスケープ、インラインコメント処理）を実装。環境値の検証（KABUSYS_ENV、PAPER_FILL_MODE、LOG_LEVEL など）を含む。
  - config_setup.py: 対話式 .env 作成ウィザードを追加（対話入力・既存 .env 読み込み・保存）。
  - validate_config.py: 起動前設定検証 CLI を追加。必須環境変数、KABUSYS_ENV の妥当性、DB パスの親ディレクトリ確認、config/*.yaml の存在/パース検査（PyYAML がある場合）等をチェック。--strict オプションで警告を FAIL 扱いにできる。
- ポートフォリオ構築モジュール（純粋関数群）
  - portfolio.portfolio_builder: 候補選定と配分（select_candidates, calc_equal_weights, calc_score_weights）。
  - portfolio.risk_adjustment: セクター集中制限 apply_sector_cap、レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear のマッピング、未知レジームはフォールバック警告）。
  - portfolio.position_sizing: 発注株数計算 calc_position_sizes。allocation_method は "risk_based", "equal", "score" を想定。単元株（lot_size）丸め、per-position 上限、aggregate cap（available_cash に収めるためのスケーリングと残差処理）を実装。
  - portfolio パッケージのエクスポートを整備。
- ユーティリティ
  - utils.logging_setup: 統一的なログ設定関数 setup_logging を追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30 日分保持）をルートロガーに設定。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils.process_priority: プロセス優先度設定（set_process_priority）と CPU affinity 設定（set_cpu_affinity）を追加。Windows と POSIX（Linux/Mac/FreeBSD）を抽象化し、権限不足等の例外は警告で安全にスキップする。
- モニタリング関連
  - monitoring 初期化呼び出し（init_monitoring_db を run_* スクリプトから呼ぶことで監視用テーブルを保証）。
  - SystemMonitor（参照）を利用するランナー実装（run_monitoring）。
- ペーパー・トレード検証ツール
  - tools.paper_verification_report: ペーパートレードの検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）等を計算して PASS/FAIL 判定を出力。閾値定義（稼働率 99.0%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）。
- 研究用モジュール（ファクター計算）
  - research.factor_research: DuckDB を利用したファクター計算モジュールの骨組みを追加（モメンタム・MA200乖離・ATR・流動性等の計算を想定）。（注: 一部実装が続く形で存在）

### 変更
- なし（初回リリース）

### 修正 / 考慮点（ドキュメント的に注記）
- .env 自動ロードはテスト用途等のために KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- run_monitoring は監視 DB として環境に依らず sqlite_path（監視用 DB）を使用する設計。run_execution は paper_trading の場合に限り paper_sqlite_path を使用して本番 DB と分離する。
- logging_setup は標準出力に stdout を採用（cron 等からのログリダイレクトで扱いやすくするための設計判断）。
- process_priority / cpu_affinity は権限不足や未対応 OS を安全にスキップする実装（警告出力）。

### 既知の制限 / TODO
- portfolio.position_sizing: price が欠損（0.0）の場合にエクスポージャーが過少見積もられる旨の注記あり。将来、前日終値等のフォールバック価格を導入する予定。
- research.factor_research: ファイル末尾で calc_momentum の実装が途中で切れている（継続実装が必要）。
- config/*.yaml の検証は PyYAML の有無に依存。PyYAML 未導入環境では内容検証をスキップする（警告出力）。

---

セキュリティ関連の修正や後方互換を破る変更がある場合は別途 Unreleased セクションに記載し、リリース時にここに移動していきます。