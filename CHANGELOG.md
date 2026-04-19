CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" and is maintained under
Semantic Versioning.

0.1.0 - 2026-04-19
------------------

Added
- 初回リリースを作成。
- 実行スクリプト:
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV=paper_trading 時は専用の paper_trading DB を使用して本番 DB と完全分離。
    - ブローカークライアントは BrokerClientFactory 経由で生成。
    - ExecutionEngine の起動/停止に PID ファイルと data/stop_requested.flag を使用。
    - デフォルトでプロセス優先度を "high" に設定する処理を組み込み。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出力。
    - Monitoring は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用する設計。
    - 停止は data/stop_requested.flag の存在検知で行う。
- 環境・設定管理:
  - config.py: Settings クラスを導入。
    - .env 自動ロード機能（プロジェクトルートに .git または pyproject.toml がある場合）。
    - .env / .env.local の取り扱い（OS 環境変数は保護し .env.local で上書き可能）。
    - 各種環境変数をプロパティとしてラップ（DB パス、API トークン、閾値、KABUSYS_ENV、ログレベル等）。
    - PAPER_FILL_MODE の検証・許容値チェックを追加。
  - config_setup.py: 対話式ウィザードで .env を作成/更新する CLI を追加。
    - シークレット項目はマスク表示。生成される .env はテンプレート化して書き出す。
- 検証ツール:
  - validate_config.py: 起動前に .env と config/*.yaml を検証する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、LOG_LEVEL、DB パスの親ディレクトリ確認、config YAML の存在・パース検証（PyYAML がインストールされていない場合は YAML 検証をスキップ）。
    - --strict モードで警告を FAIL 扱いにするオプションを実装。
    - 本番環境向けの追加ガード（LINE 設定や KILL_FLAG_CLEAR_ON_START の設定確認）。
- ツール:
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）、リスク却下数などを算出して PASS/FAIL 判定を出力。
    - デフォルト DB パスは data/paper_trading.db。コマンドラインで期間や DB を指定可能。
- ポートフォリオ構築:
  - portfolio/portfolio_builder.py: シグナル選定と等重・スコア重み計算を実装（select_candidates, calc_equal_weights, calc_score_weights）。
    - スコアが全て 0 の場合は等金額配分にフォールバックして警告を出力。
  - portfolio/risk_adjustment.py: セクター集中制限と市場レジーム乗数を実装（apply_sector_cap, calc_regime_multiplier）。
    - セクター上限ロジック、"unknown" セクターは上限適用除外、レジームに応じた乗数（bull/neutral/bear）を提供。
  - portfolio/position_sizing.py: 発注株数決定ロジックを実装（calc_position_sizes）。
    - risk_based / equal / score の配分方式に対応。
    - 単元株丸め（lot_size 単位）、1銘柄上限・aggregate cap（available_cash）によるスケールダウン、cost_buffer による保守的コスト見積もり、端数処理ロジックを実装。
- ユーティリティ:
  - utils/logging_setup.py: ルートロガー設定ユーティリティを追加。
    - stdout 出力用 StreamHandler と 日次ローテーションの TimedRotatingFileHandler（デフォルト logs/<app_name>.log、30 日保持）を設定。
    - 既存ハンドラのクリーンアップ、ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py: クロスプラットフォームでのプロセス優先度・CPU affinity 設定を追加。
    - Windows / POSIX（Linux/Mac/FreeBSD）をサポート。権限不足などの失敗は警告でスキップ。

Changed
- パッケージ初期化:
  - __init__.py に __version__ = "0.1.0" を設定し、主要サブパッケージを __all__ で公開。

Fixed
- .env パーサー（config._parse_env_line）:
  - export KEY=val 形式のサポート、クォート内のバックスラッシュエスケープ対応、インラインコメントの取り扱い、クォート無しの値におけるコメント識別ルールなどを実装してより堅牢に。
- run_monitoring._get_poll_interval:
  - 環境変数値が不正（非整数や 0 以下）の場合にデフォルトにフォールバックして警告を出すように改善（time.sleep に渡す際の ValueError 回避）。
- ロギング設定:
  - ログディレクトリの作成に失敗した場合でもコンソールログで継続するフェイルセーフを導入。
- DB 初期化:
  - run_* スクリプトで init_monitoring_db を呼び出し、監視テーブルが存在することを冪等に保証するようにした。

Notes / Important behavior
- Monitoring DB の扱い:
  - run_monitoring.py は KABUSYS_ENV にかかわらず settings.sqlite_path（本番想定のパス）を使用します。監視データは本番 DB に保存される設計に注意してください。
- Paper Trading の完全分離:
  - run_execution.py は KABUSYS_ENV=paper_trading 時に settings.paper_sqlite_path を使用してペーパートレード用 DB に記録します。paper_trading のデータは本番 DB と分離されます。
- 自動 .env ロード:
  - 起動時（モジュール import 時）にプロジェクトルートが判定できれば .env と .env.local を自動読み込みします。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- Kill / Stop フラグ:
  - 停止制御は data/stop_requested.flag や data/kill.flag 等のフラグファイルで行う運用を想定。KILL_FLAG_CLEAR_ON_START 設定の有効性は本番での危険性があるため validate_config で警告を出す。

Developer / For contributors
- 新しい CLI・スクリプトを追加したため、起動フローや環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABUSYS_ENV, PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL など）を .env に適切に設定してください。
- YAML 設定ファイル（config/*.yaml）は存在が期待されます。validate_config を使って事前検証してください（PyYAML 未導入時は構文検証がスキップされます）。
- ロギングやプロセス優先度設定は OS 権限や環境に依存します。権限不足時は警告が出るようになっています。

---

以上が初回リリース (0.1.0) の主要な変更点です。今後のリリースでは、API クライアント実装、戦略本体、I/O やテストカバレッジの拡充などを予定しています。