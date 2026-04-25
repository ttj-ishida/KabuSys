CHANGELOG
=========

この CHANGELOG は Keep a Changelog の形式に準拠しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

- なし（次回リリースに向けた変更はここに記載します）

[0.1.0] - 2026-04-25
-------------------

初回公開リリース。

Added
- 基本構成
  - パッケージ初期バージョンを `__version__ = "0.1.0"` として追加。
- 設定管理
  - kabusys.config
    - .env の自動読み込み機能を実装（プロジェクトルートを .git / pyproject.toml から探索）。
    - .env ファイルのパースを強化（export プレフィックス対応、クォート・エスケープ、インラインコメント処理）。
    - 環境変数取得ユーティリティ Settings を実装。J-Quants / kabu API / DB パス /ログ設定 /監視閾値などをプロパティで提供。
    - 環境値の検証（KABUSYS_ENV, LOG_LEVEL 等）とデフォルトの設定を含む。
    - PAPER_FILL_MODE 等の設定を検証し、不正値は例外を発生させる仕様。
- 設定補助 CLI
  - kabusys.config_setup
    - 対話式ウィザードで .env を初期作成・更新する機能を実装。
    - デフォルト値提示、シークレット値のマスク表示、確認プロンプト、.env の書き出しをサポート。
- 設定検証 CLI
  - kabusys.validate_config
    - .env および config/*.yaml の事前検証ツールを実装。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在確認、YAML パース（PyYAML が利用可能な場合）等。
    - --strict オプションで警告を FAIL 扱いにできる。
- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL で間隔上書き（デフォルト 60 秒）。
    - 停止フラグファイル（data/stop_requested.flag）検知で安全にループ終了。
    - 監視用 DB 接続は環境に関わらず本番 sqlite_path を使用して起動。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の際は専用の paper_trading DB（data/paper_trading.db デフォルト）を使用し、本番 DB と分離。
    - ブローカーファクトリ経由で BrokerClient を生成し ExecutionEngine をバックグラウンドスレッドで実行。停止フラグで安全停止。
- ユーティリティ
  - kabusys.utils.logging_setup
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）を設定する共通初期化を実装。
    - LOG_DIR の作成に失敗した場合はファイル出力をスキップして stdout のみで継続する安全なフォールバックを実装。
  - kabusys.utils.process_priority
    - cross-platform（Windows / POSIX）でプロセス優先度設定と CPU affinity 設定を行うユーティリティを追加。
    - アクセス権や未対応 OS の場合は警告を出してスキップする耐障害性を持つ。
- Portfolio モジュール（純粋関数群）
  - kabusys.portfolio.portfolio_builder
    - 候補選定（スコア降順、signal_rank によるタイブレーク）、等配分・スコア加重配分の計算を実装。
    - スコアが全て 0 の場合は等配分にフォールバックして警告を出す。
  - kabusys.portfolio.risk_adjustment
    - セクター集中制限 apply_sector_cap を実装（当日売却予定銘柄の除外、"unknown" セクターは除外しない等）。
    - レジームに基づく投下資金乗数 calc_regime_multiplier（bull/neutral/bear をマップし、未知レジームはフォールバック）を実装。
  - kabusys.portfolio.position_sizing
    - position sizing を実装（allocation_method: risk_based / equal / score）。
    - 単元株丸め（lot_size）、per-position と aggregate のキャップ、cost_buffer（手数料・スリッページ見積）を考慮したスケーリングロジックを実装。
    - 不足データや価格不在時はログを出してスキップする堅牢性を備える。
- ツール
  - kabusys.tools.paper_verification_report
    - Paper Trading 用 SQLite を読み取り、システム稼働率 / 注文成功率 / 送信率 / P95 レイテンシなどの指標を集計・レポート出力する CLI を実装。
    - 期間指定 (--from / --to)、DB パス指定 (--db) をサポート。閾値に基づき PASS/FAIL 判定を行う。
- モジュール骨格
  - kabusys.research.factor_research
    - ファクター計算モジュール（Momentum / Value / Volatility / Liquidity）を作成。モメンタム計算関数の実装開始（prices_daily を参照する設計）。
  - パッケージのエクスポートを整備（kabusys.portfolio などの __all__）。

Changed
- .env 自動読み込みの仕様
  - OS 環境変数優先で .env/.env.local を読み込む順序を明確化。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能。
- ログ設定
  - StreamHandler を stdout に向けることで、cron / OS スケジューラでのリダイレクト運用を想定。
- DB 初期化
  - init_monitoring_db を idempotent（何度呼んでも安全）に呼び出すように起動スクリプトで保証。

Fixed
- .env パーサーの曖昧さを解消
  - export 付き行、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの取り扱いを改善。
- run_execution/run_monitoring の停止ハンドリング
  - stop flag 検知時のログを追加し、安全に終了/停止するよう改善。

Security
- config_setup による .env ファイル生成時、コメントで「.env を Git にコミットしないこと」を明記。

Deprecated
- なし

Removed
- なし

Breaking Changes
- なし（本リリースは新規追加中心）

Notes / ヒント
- Paper Trading と本番 DB は明確に分離されています。KABUSYS_ENV=paper_trading を設定すると実行エンジンは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用します。誤って本番 DB を上書きしないよう注意してください。
- 環境変数の必須設定（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）を忘れると validate_config や Settings のプロパティアクセスでエラーになります。config_setup での初期化と validate_config での検証を推奨します。
- ロギングディレクトリ作成に失敗した場合はコンソールのみでログが出力されます（ファイル出力は無効化されます）。ログディレクトリの権限やパス設定を確認してください。

今後の予定（例）
- factor_research のファクター計算の完成とテストケースの追加
- ExecutionEngine / BrokerClient の追加実装と統合テスト強化
- より詳細なドキュメント（PortfolioConstruction.md 等）のパッケージ内添付

---