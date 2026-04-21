CHANGELOG
=========

すべての日付は YYYY-MM-DD 形式で記載しています。  
この CHANGELOG は Keep a Changelog の形式に準拠しています（https://keepachangelog.com/ja/）。

バージョンポリシー: 現時点では初回リリースを 0.1.0 としています。

Unreleased
----------
（未リリースの変更はここに記載）

[0.1.0] - 2026-04-21
-------------------

Added
- パッケージ初期版を追加（__version__ = 0.1.0）。
- 実行用エントリスクリプトを追加
  - run_execution.py: ExecutionEngine を起動する CLI。起動時にプロセス優先度を "high" に設定し、バックグラウンドスレッドで engine.run_session を実行。停止は data/stop_requested.flag により制御。KABUSYS_ENV=paper_trading 時は paper_trading 用の専用 SQLite DB を使用（デフォルト: data/paper_trading.db）。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視用 DB は環境に依らず本番 sqlite_path を使用。
- 設定・環境管理
  - config.py: .env 自動ロード機能（プロジェクトルート検出による .env / .env.local の読み込み）、.env のパース（引用符・エスケープ・インラインコメント対応）、Settings クラス（各種環境変数のラッパーとバリデーション）を実装。PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL 等の検証ロジックを含む。
  - config_setup.py: 対話式ウィザードで .env を作成/更新する CLI を提供。複数の項目 (KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, など) をサポートし、シークレット/デフォルト/選択肢表示・確認・保存処理を実装。
  - validate_config.py: 起動前に .env と config/*.yaml を検証する CLI。必須環境変数の存在チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、YAML のパース検証（PyYAML がある場合）を行い、エラー/警告/情報を出力。--strict オプションで警告を失敗扱いできる。
- ログ・プロセス管理ユーティリティ
  - utils/logging_setup.py: 共通ログ設定ユーティリティ。stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler、バックアップ 30 日）をルートロガーに設定。ログディレクトリ作成失敗時はファイルハンドラ無効化して stdout のみで継続するフェイルセーフを実装。
  - utils/process_priority.py: Windows/Linux/macOS を抽象化したプロセス優先度設定（set_process_priority）と CPU affinity 設定（set_cpu_affinity）。psutil を用い、権限不足や未対応 OS の場合は警告を出してスキップする。
- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py: シグナル選択（select_candidates）、等分配（calc_equal_weights）、スコア加重（calc_score_weights）を実装。スコアが全て 0 の場合は等分配へフォールバック。
  - portfolio/risk_adjustment.py: セクター集中制限適用（apply_sector_cap）と市場レジームに基づく投下資金乗数（calc_regime_multiplier）。未知レジーム時は警告を出して 1.0 にフォールバック。
  - portfolio/position_sizing.py: 銘柄ごとの発注株数計算（risk_based / equal / score の allocation_method をサポート）。単元（lot_size）丸め、per-position 上限・aggregate cap、cost_buffer を使った保守見積り、スケールダウン時の remainder による追加配分ロジックなどを実装。
  - portfolio/__init__.py: 上記関数をパブリック API としてエクスポート。
- 解析・レポートツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成 CLI。指定期間（--from, --to）または DB（--db / 環境変数 PAPER_TRADING_SQLITE_PATH）からデータを集計し、稼働率、注文成功率・送信率、リスク却下数、レイテンシ（平均/最大/P95）を算出して PASS/FAIL 判定を出力。P95 計算関数と各種閾値（稼働率 99%、成立率 90%、送信率 95%、P95 <= 200ms）を定義。
- 監視・実行周辺の DB 初期化支援
  - monitoring_db.init_monitoring_db の呼び出しにより、起動時に監視用テーブル存在を保証（冪等に作成）。
- Research（ファクター計算）モジュールの追加（開発中）
  - research/factor_research.py: DuckDB 接続を受けてモメンタムや MA200 乖離率などのファクターを計算するための関数群（calc_momentum など）の実装が始まっています（prices_daily / raw_financials 参照の設計）。（注: 提供ソースは途中で切れており、実装完了部分と WIP 部分が混在します）

Changed
- （初回公開のため該当なし）

Fixed
- （初回公開のため該当なし）

Deprecated
- （初回公開のため該当なし）

Removed
- （初回公開のため該当なし）

Security
- 環境変数ファイル (.env) の生成において「.env を絶対に Git にコミットしないこと」を明記（config_setup.py の出力ヘッダ）。

Notes / Implementation details
- 環境自動ロード:
  - プロジェクトルートは __file__ を基点に .git または pyproject.toml を探索して決定。見つからない場合は自動ロードをスキップします。
  - OS 環境変数は保護され、.env の上書きから除外されます。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
- .env パーサの挙動:
  - export KEY=val 形式を許可。シングル/ダブルクォート内のバックスラッシュエスケープと閉じクォート処理をサポート。クォートなしの場合、'#' が先頭または直前が空白/タブのとき以降をコメントとして無視。
- Execution と Monitoring の停止制御:
  - data/stop_requested.flag（またはプロジェクト内 data 以下の stop ファイル）により安全に停止可能。ExecutionEngine は停止検知で engine.stop() を呼ぶ。
- ロギング:
  - stdout へ出力する StreamHandler を用いる設計（cron/Task Scheduler での stdout/stderr のリダイレクト想定）。ログファイルへの書き込みに失敗してもプロセスは継続する。
- Paper Trading の分離:
  - KABUSYS_ENV=paper_trading 時、実行用 DB は paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番監視 DB と分離する設計。
- エラーハンドリング:
  - ロングラン監視ループ中の monitor.check_once() で例外が発生してもループを継続して次のポーリングに移行する耐障害設計（例外はロギング）。
- WIP / TODO:
  - research/factor_research.py はファクター計算の骨子があるものの、提供ソースは途中で切れており完全実装ではない箇所があります（今後の実装完了が必要）。
  - position_sizing.calc_position_sizes の price 欠損時のフォールバック（前日終値や取得原価の利用など）は将来的に改善予定の旨コメントあり。

Breaking Changes
- なし（初版リリース）

Acknowledgements / External libs
- psutil: プロセス優先度・CPU affinity の設定に使用
- duckdb: 分析用 DB に利用（research / エンジン等）
- PyYAML: validate_config.py の YAML 検証で任意依存（未インストール時は YAML 検証をスキップ）

---

今後の提案（メモ）
- research/factor_research の完成とテスト追加
- 単体テスト（特に portfolio / position_sizing / risk_adjustment）の追加
- CI による config の検証自動化（--strict モードの運用）
- ログの JSON 出力オプションや構造化ログ対応の検討
- lot_size を銘柄別に持たせるための stocks マスタ対応

以上