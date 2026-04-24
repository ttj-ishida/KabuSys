CHANGELOG
=========

この CHANGELOG は "Keep a Changelog" の形式に準拠しています。  
コードベースの内容から推測して変更点・追加機能をまとめています。

フォーマット:
- Unreleased: 今後の変更用（現時点では空）。
- 各リリースはリリース日を付記しています（推測に基づく日付）。

Unreleased
----------

- なし

[0.1.0] - 2026-04-24
--------------------

Added
- 基本アプリケーション構成を初回リリースとして追加。
  - パッケージバージョンを __version__ = "0.1.0" として設定（src/kabusys/__init__.py）。
- 起動スクリプト / デーモン制御
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止はプロジェクト/data/stop_requested.flag によるファイルフラグで制御。
    - 監視用 DB は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する（意図的な運用仕様）。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite（data/paper_trading.db を既定）を使用し、本番 DB と分離。
    - 停止フラグと execution.pid によるプロセス管理、ExecutionEngine のスレッド起動／停止処理を実装。
- 設定管理
  - config.py: 環境変数・設定管理モジュールを追加。
    - プロジェクトルートの自動探索（.git または pyproject.toml を基準）による .env 自動読み込み機能を実装（.env、.env.local の順序でロード。OS 環境変数は保護）。
    - .env の行パースを強化（export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、コメント処理を考慮）。
    - Settings クラスで各種設定値（DB パス、API トークン、環境種別、ログレベル、監視閾値、paper_trading 用パスなど）をプロパティ経由で提供。
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）。
- 設定支援 CLI
  - config_setup.py: .env 作成・更新の対話式ウィザードを追加。
    - 必須項目（J-Quants、kabu API パスワード等）やログレベル、DB パス、Kill Switch の設定を対話形式で生成・書き込み。
  - validate_config.py: 起動前の設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、LOG_LEVEL の妥当性、DB パスの親ディレクトリチェック、config/*.yaml の存在と（PyYAML 利用時の）パース検証、本番環境向けの追加警告（LINE 通知設定・KILL_FLAG_CLEAR_ON_START）を実装。
    - --strict オプションで警告を FAIL 扱いにできる。
- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。
    - コンソール出力（stdout）と日次ローテート（TimedRotatingFileHandler、30 日保持）をルートロガーに設定。LOG_DIR / LOG_LEVEL の環境変数で上書き可能。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py: プロセス優先度と CPU affinity 設定ユーティリティを追加。
    - Windows / POSIX（Linux, macOS, FreeBSD）向けの優先度設定を吸収。set_cpu_affinity によるコア固定機能も実装。
    - 権限不足や未サポート環境では警告を出してスキップ。
- Portfolio（銘柄選定・配分・株数計算）
  - portfolio/portfolio_builder.py:
    - select_candidates: スコア降順で上位 N を選定（同点は signal_rank でブレーク）。
    - calc_equal_weights: 等金額配分（1/N）。
    - calc_score_weights: スコア正規化配分。全スコア 0 の場合は等配分にフォールバック（警告）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中上限チェック。既存保有のセクター時価を基に上限を超えるセクターの候補を除外。unknown セクターは上限適用対象外。
    - calc_regime_multiplier: market レジームに応じた投下資金乗数（bull/neutral/bear）を返す。未知レジームは警告を出してフォールバック 1.0。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method（risk_based, equal, score）に基づく発注株数計算を実装。
      - risk_based: 許容リスク率 / 損切り幅からポジションサイズを計算。
      - equal/score: weight に基づく配分、max_position_pct, max_utilization, lot_size, cost_buffer を考慮。
      - aggregate cap: 利用可能現金を超える場合はスケールダウンし、残余でロット単位の再配分を行う（端数処理を安定化）。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py:
    - Paper Trading の SQLite DB（デフォルト data/paper_trading.db）から各種指標を集計してレポート出力（稼働率、注文成功率、送信率、リスク却下数、API レイテンシ平均/最大/P95）。
    - レポートは閾値判定（稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 latency <= 200ms）に基づき PASS/FAIL を算出。
    - 日付範囲フィルタ（--from / --to）と DB パス指定（--db）をサポート。
- research/factor_research.py
  - DuckDB 接続を受けてファクター（Momentum、Value、Volatility、Liquidity）を計算するモジュールの骨子を追加。モメンタム計算の方針・定数が定義され、calc_momentum の実装開始（途中まで）を含む。

Changed
- なし（初回追加につき "Added" に集約）。

Fixed
- なし（初回追加につき "Fixed" はなし）。

Security
- 環境ファイル (.env) は絶対に Git にコミットしない旨の注意を config_setup に明記（.env は機密情報を含むため）。

Notes / 運用上の重要事項（コードから推測）
- 監視 (run_monitoring) は監視用テーブルを初期化し、KABUSYS_ENV にかかわらず設定された sqlite_path（デフォルト data/monitoring.db）を使用します。テストと本番の DB 分離を運用する際は留意してください。
- 実行エンジン (run_execution) は paper_trading モードで paper_trading 専用 DB を使用し、本番 DB と完全分離する設計（Paper Trading の安全性確保）。
- プロセス優先度や CPU affinity の設定は実行ユーザーの権限に依存します。権限不足時は警告が出力され設定をスキップします。
- .env の自動ロードはプロジェクトルート検出に依存するため、パッケージ配布後やテスト環境で無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- logging_setup はログディレクトリ作成に失敗してもコンソールログで動作を継続する耐障害性を持ちます。

既知の制約 / TODO（コードから読み取れる注記）
- portfolio.position_sizing の lot_size は現状すべての銘柄で固定（将来的に銘柄別 lot_map に拡張予定）。
- apply_sector_cap の既存保有評価では価格欠損（0.0）が過少評価につながる可能性がある旨の TODO コメントあり（フォールバック価格の導入を検討）。
- research/factor_research.calc_momentum はファイル末尾で途中の実装となっている（今後追加実装が必要）。

参考: 主なファイル一覧（今回の初期リリースで追加された主要モジュール）
- src/kabusys/__init__.py
- src/kabusys/config.py
- src/kabusys/config_setup.py
- src/kabusys/validate_config.py
- src/kabusys/run_monitoring.py
- src/kabusys/run_execution.py
- src/kabusys/utils/logging_setup.py
- src/kabusys/utils/process_priority.py
- src/kabusys/portfolio/portfolio_builder.py
- src/kabusys/portfolio/risk_adjustment.py
- src/kabusys/portfolio/position_sizing.py
- src/kabusys/tools/paper_verification_report.py
- src/kabusys/research/factor_research.py

---

（注）上記 CHANGELOG は提示されたコードの内容から推測して作成しています。実際のリリース履歴や日付、追加／変更理由はプロジェクトの履歴管理（git タグやリリースノート）を参照のうえ必要に応じて調整してください。