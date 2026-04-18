CHANGELOG
=========

すべての変更は Keep a Changelog 準拠で記載しています。

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-18
--------------------

Added
- 初回リリース (0.1.0) — KabuSys の基本機能群を追加。
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。KABUSYS_ENV=paper_trading 時はモックブローカを利用し、paper_trading 用 SQLite（デフォルト: data/paper_trading.db）に記録する挙動を実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止はプロジェクトルートの data/stop_requested.flag によって行う。
- 設定管理
  - config.py: 環境変数読み込みと Settings クラスを実装。自動 .env ロード（.env, .env.local）機能を追加（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
  - config_setup.py: 対話式 .env 作成・更新ウィザードを追加（python -m kabusys.config_setup）。シークレット入力・選択肢サポート、保存時のテンプレート出力を提供。
  - validate_config.py: 起動前に .env と config/*.yaml の整合性をチェックする CLI を追加（python -m kabusys.validate_config）。--strict オプションで警告を FAIL 扱いにできる。
- ポートフォリオ構築ライブラリ（純粋関数）
  - portfolio/portfolio_builder.py: シグナル選定と等加重・スコア加重の重み計算を追加（select_candidates, calc_equal_weights, calc_score_weights）。
  - portfolio/risk_adjustment.py: セクター集中制限の適用と市場レジームに応じた乗数（apply_sector_cap, calc_regime_multiplier）を追加。
  - portfolio/position_sizing.py: 株数計算ロジックを追加（risk_based / equal / score の allocation_method、lot_size 丸め、aggregate cap スケーリング等）。
  - portfolio/__init__.py: 上記関数群を公開。
- ユーティリティ
  - utils/logging_setup.py: 共通ロギング設定ユーティリティを追加。標準出力（stdout）用 StreamHandler と日次ローテートする TimedRotatingFileHandler（logs/<app_name>.log）を設定。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみ継続。
  - utils/process_priority.py: Windows/Linux (POSIX) の差分を吸収してプロセス優先度と CPU affinity を設定するユーティリティを追加（set_process_priority, set_cpu_affinity）。アクセス権限不足等の失敗は警告してスキップ。
- モニタリング / DB 初期化
  - monitoring/monitoring_db (利用箇所から初期化呼び出し): 起動時に監視用テーブルの存在を保証する init_monitoring_db 呼び出しを run_execution/run_monitoring で行う（冪等）。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py: ペーパートレード用 SQLite からレポート（稼働率、注文成功率、送信率、レイテンシ等）を生成するツールを追加。閾値 (稼働率99%、注文成功率90% 等) に基づく PASS/FAIL 判定、--from/--to/--db CLI オプションを提供。
- 研究用モジュール
  - research/factor_research.py: DuckDB を用いたファクター計算モジュールの骨組み（モメンタム・ボラティリティ等）を追加（実装途中）。

Changed
- パッケージ情報
  - __init__.py にてバージョンを "0.1.0" に設定。

Fixed / Behavior details
- run_monitoring.py: MONITOR_POLL_INTERVAL が不正（非整数や 0 以下）な場合にデフォルト値（60 秒）へフォールバックし、ログに警告を出すように改善。
- config.py: .env パーサ (_parse_env_line) を強化して以下に対応:
  - export KEY=val 形式のサポート
  - シングル/ダブルクォート内のバックスラッシュエスケープ処理
  - クォートなし値のインラインコメント処理（直前が空白/タブの場合のみ）
- config.py: .env ロード時に OS 環境変数を保護する仕組みを導入（protected set）。.env.local は .env の上書きとして扱う。
- portfolio/calc_score_weights: 全銘柄のスコア合計が 0.0 の場合は等金額配分へフォールバックし、警告ログを出すようにした。
- portfolio/risk_adjustment.apply_sector_cap: セクター不明 ("unknown") な銘柄はセクター上限チェックから除外（既存保有がある場合でもブロックしない）。
- portfolio/position_sizing.calc_position_sizes:
  - 単元株（lot_size）での丸め処理と aggregate cap 超過時のスケーリングロジックを実装。余剰キャッシュを fractional remainder に基づき lot_size 単位で再配分するアルゴリズムを追加。
  - 価格欠損や負値価格はスキップし、ログにデバッグ情報を出す。
- utils/logging_setup.py: stdout を利用することで cron 等からのリダイレクトと相性を良くした（stderr ではなく stdout を使う）。
- utils/process_priority.py: マルチプラットフォーム対応（Windows の HIGH_PRIORITY_CLASS 等は getattr によるフォールバック）、対応不可時は警告してスキップ。

Security
- .env に関する注意を config_setup.py の出力に明記（.env を Git にコミットしない旨）。

Notes / Implementation caveats
- run_monitoring は「Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する」挙動（ドキュメント化された設計）になっています。運用時は意図した DB パスを確認してください。
- run_execution は KABUSYS_ENV=paper_trading のときに paper_trading 用 DB を使う設計です（本番 DB と完全分離することを意図）。
- research/factor_research.py はファクター計算用の骨組みがあり、詳細実装の完了が必要です（ファイル末尾が未完の箇所あり）。
- 一部の TODO や将来的拡張（銘柄ごとの lot_size 管理、価格フォールバック戦略など）がコード内に記載されています。

参考: 主要 CLI
- python -m kabusys.config_setup      （対話式 .env ウィザード）
- python -m kabusys.validate_config   （設定検証 CLI。--strict オプションあり）
- python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

---

今後のリリース案
- research モジュールの完成（ファクター計算フル実装）
- Execution / Broker 実装の詳細とテストカバレッジ向上
- 単体テスト、CI 設定、デプロイ手順の追加
- ログの structured/logging context サポートやメトリクス出力の追加検討