CHANGELOG
=========

すべての変更は Keep a Changelog の形式に概ね準拠しています。
日付はこのコードベースのスナップショット作成日 (2026-04-20) を使用しています。

Unreleased
----------

（現時点なし）

0.1.0 - 2026-04-20
-----------------

Added
- 初期リリース: KabuSys 自動売買システムのコア機能群を追加。
  - 実行・監視ランナー
    - run_execution.py
      - ExecutionEngine を起動する CLI スクリプトを追加。
      - KABUSYS_ENV が `paper_trading` の場合は専用のペーパートレーディング用 SQLite（data/paper_trading.db）を使用し、本番 DB と分離。
      - BrokerClientFactory によるブローカクライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、デーモンスレッドでのセッション実行、停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）管理を実装。
    - run_monitoring.py
      - SystemMonitor をポーリングする監視ループ起動スクリプトを追加。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60秒）。
      - 監視は環境に関わらず本番 sqlite_path を使用して監視データを保存。
      - 停止フラグによる安全終了処理、例外時のログ記録を実装。
  - 設定管理
    - config.py
      - .env 自動ロード（.env, .env.local）機能を実装。OS 環境変数を保護する仕組みあり（保護されたキーは上書きされない）。
      - プロジェクトルートの自動検出（.git または pyproject.toml 基準）。
      - 各種設定プロパティを提供（J-Quants / kabu API / DB パス / PID/kill フラグ / モニタ閾値 / KABUSYS_ENV 等）。
      - PAPER_FILL_MODE の妥当性チェック、KABUSYS_ENV / LOG_LEVEL の妥当性検査を実装。
    - config_setup.py
      - .env を対話式に生成・更新するウィザードを実装。秘密値のマスク表示、デフォルト値、選択肢サポート、保存前確認を実装。
    - validate_config.py
      - 起動前に .env と config/*.yaml を検証する CLI を追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL/DB パスのチェック、YAML パースチェック（PyYAML 未インストール時は警告）や本番ガード（KABUSYS_ENV=live 時の追加チェック）を実装。--strict オプションで警告を FAIL 扱いにできる。
  - ポートフォリオ構築（純関数ライブラリ）
    - portfolio/portfolio_builder.py
      - 候補選定（select_candidates）、等分配（calc_equal_weights）、スコア加重（calc_score_weights）を実装。
    - portfolio/risk_adjustment.py
      - セクター集中抑制（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。
      - 未知レジームに対するフォールバックやログ警告を実装。
    - portfolio/position_sizing.py
      - position sizing（株数決定）ロジックを実装。risk_based / equal / score の配分方式に対応。
      - 単元株（lot_size）丸め、1銘柄上限・aggregate cap（利用可能現金に対するスケーリング）を実装。cost_buffer を加味した保守的なコスト見積りとリマインダ処理での余剰配分アルゴリズムを実装。
      - 将来拡張用の TODO（銘柄別 lot_size など）を明記。
  - 解析・レポート系
    - tools/paper_verification_report.py
      - ペーパートレード用 SQLite から運用検証レポートを生成する CLI を実装（期間指定 --from / --to / DB パス --db 指定可）。稼働率、注文成功率・送信率、リスク却下数、レイテンシ（avg/max/P95）を算出し PASS/FAIL 判定を行う。基準値（稼働率 99% 等）を定義。
    - research/factor_research.py（ファクター計算の土台を追加）
      - DuckDB 接続を受けて Momentum / Value / Volatility / Liquidity などの計算を行う設計を追加。モメンタム関連定数・calc_momentum のインターフェース（部分実装）が含まれる（詳細実装は続きが必要）。
  - ユーティリティ
    - utils/logging_setup.py
      - 統一的なログ設定ユーティリティを追加。stdout ストリームハンドラと日次ローテーション (TimedRotatingFileHandler) をルートロガーに設定。ログディレクトリ作成失敗時はファイル出力を無効化して継続。環境変数 LOG_LEVEL / LOG_DIR に対応。
    - utils/process_priority.py
      - Windows / POSIX を吸収するプロセス優先度設定と CPU affinity 設定ユーティリティを追加。権限不足や未対応 OS の場合は安全にスキップして警告（ログ）を出力。

Changed
- N/A（初回リリースのため変更履歴はありません）

Fixed
- N/A

Deprecated
- N/A

Removed
- N/A

Security
- 環境変数ファイル (.env) をデフォルトで Git 管理しない旨を config_setup のヘッダに明記（セキュリティ指針）。

Notes / Known limitations
- research/factor_research.calc_momentum はファイル内で途中までの記述が含まれており、完全実装には追加作業が必要です（スナップショットの一部として含まれている）。
- apply_sector_cap 内に価格欠損時の挙動に関する TODO コメントがあり、前日終値などのフォールバック価格を使う拡張が想定されています。
- position_sizing は現状すべての銘柄で同一の lot_size（デフォルト 100）を想定しており、将来的に銘柄別単元対応へ拡張する予定です（TODO コメントあり）。
- プロセス優先度や CPU affinity の設定は OS/権限に依存するため、失敗した場合は警告ログを出して処理を継続する実装です。
- .env 自動ロードはプロジェクトルート検出に依存するため、配布パッケージ化後や特殊な配置では自動検出が失敗する可能性があります（その場合は自動ロードをスキップ）。

開発者向けメモ
- 起動スクリプト（run_execution / run_monitoring）は setup_logging と set_process_priority を最初に呼び、ログ出力とプロセス優先度の統一を行っています。
- DB は SQLite（監視／紙トレード）と DuckDB（分析用）を併用する設計になっています。monitoring 用テーブルの初期化関数 init_monitoring_db が呼ばれる点に注意してください。
- validate_config により起動前に環境の妥当性を検査できるため、CI / デプロイ前チェックとして利用することを推奨します。

--- 

今後のリリースでは以下を検討してください:
- research モジュールの完成（ファクター計算の SQL/実装完了）
- 銘柄別 lot_size サポート、price フォールバックロジック強化
- より詳しいログ・メトリクス出力（Prometheus / JSON ログなど）
- 単体テスト・統合テストの追加（各純関数・CLIs）