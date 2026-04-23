# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の方針に従って記載しています。

## [0.1.0] - 2026-04-23

初回リリース

### 追加 (Added)
- 実行/監視ランチャーを追加
  - src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告出力。
    - 停止はプロジェクト直下の data/stop_requested.flag の存在で検知。
    - 起動時にプロセス優先度を設定し、SQLite（監視 DB）と DuckDB に接続して監視処理を実行。例外発生時はログ出力して次ポーリングへ継続。
  - src/kabusys/run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は専用の paper_trading DB（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory を用いてブローカークライアントを生成、OrderRepository/OrderManager/Reconciler/RiskManager を組み立てて Engine を起動。
    - 停止フラグ（data/stop_requested.flag）検知による安全停止、PID ファイル管理（data/execution.pid）を想定。

- 設定読み込み・管理
  - src/kabusys/config.py
    - プロジェクトルート（.git または pyproject.toml）を自動検出して .env, .env.local を自動読み込み（OS 環境変数は上書き保護）。
    - .env の行パーサーを実装（export プレフィックス、クォート文字列、エスケープ、インラインコメントの扱いに対応）。
    - Settings クラスを追加し、アプリケーションで使用する環境変数をプロパティとして提供（DB パス、LINE 構成、閾値、env 判定等）。
    - PAPER_FILL_MODE / KABUSYS_ENV / LOG_LEVEL 等のバリデーションを実装。

- 設定ウィザードと検証 CLI
  - src/kabusys/config_setup.py
    - 対話式ウィザードにより .env の初期作成・更新を支援。シークレット項目はマスク表示、デフォルト値や選択肢で促す。
    - 書き込み時に .env のテンプレート形式で保存。
  - src/kabusys/validate_config.py
    - 起動前に環境変数や config/*.yaml、DB パス、"live" 実行時のガードなどを検証する CLI を追加。
    - --strict モードで警告も失敗扱いにできる。PyYAML がない場合は YAML 検証をスキップして警告出力。

- ポートフォリオ構築関連（純粋関数群）
  - src/kabusys/portfolio/portfolio_builder.py
    - 銘柄候補選定（スコア降順、タイブレーク仕様）と等重・スコア重み算出を実装。
  - src/kabusys/portfolio/risk_adjustment.py
    - セクター集中上限の適用（既存保有を考慮）と市場レジームに基づく投下資金乗数（bull/neutral/bear）を実装。
  - src/kabusys/portfolio/position_sizing.py
    - allocation_method（risk_based / equal / score）に基づく株数計算を実装。
    - 単元株（lot_size）での丸め、1 銘柄上限・aggregate cap（利用可能現金に基づくスケーリング）、コストバッファの考慮、残差分の優先配分ロジックを実装。

- ユーティリティ
  - src/kabusys/utils/logging_setup.py
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション）を設定する共通ロギングユーティリティを追加。
    - ログディレクトリ自動作成、作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - src/kabusys/utils/process_priority.py
    - psutil を利用したプロセス優先度設定ユーティリティ（Windows / POSIX 差分を吸収）を追加。
    - CPU affinity を最初の N コアに固定する機能を提供（権限やプラットフォーム制約は警告でスキップ）。

- ツール
  - src/kabusys/tools/paper_verification_report.py
    - Paper Trading 用 SQLite (data/paper_trading.db 等) を解析して検証レポートを生成するスクリプトを追加。
    - 稼働率（uptime）、注文成功率、送信率、リスク却下数、レイテンシ（avg/max/P95）を算出し PASS/FAIL 判定（閾値はソース内定義）を行う。
  - src/kabusys/tools/__init__.py を追加（ツールパッケージ初期化）。

- リサーチ基盤の骨組み
  - src/kabusys/research/factor_research.py
    - モメンタム等ファクター計算モジュールの骨組みを追加（DuckDB 接続を受け取り prices_daily / raw_financials を参照する設計）。モジュール内に定数と calc_momentum のサインを記載（実装途中あり）。

- パッケージメタ
  - src/kabusys/__init__.py にバージョン __version__ = "0.1.0" を設定。

### 変更 (Changed)
- ログ出力の統一
  - 全起動スクリプトやユーティリティは setup_logging を利用して一貫したログ構成を使用することを想定。
- .env 自動読み込みの動作
  - プロジェクトルート自動検出（.git / pyproject.toml）に基づき .env/.env.local をロードする方式に変更。テスト時等に自動ロードを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数をサポート。

### 修正 (Fixed)
- .env パースの堅牢化
  - export プレフィックス、シングル/ダブルクォート内のエスケープ、インラインコメントの扱い、上書き制御（protected）などを正しく処理するように改善。
- 起動時の安全措置
  - run_execution/run_monitoring で起動直後にプロセス優先度を設定するようにして、優先度設定失敗時は警告でスキップする挙動に統一。

### 注意事項 (Notes)
- 監視（run_monitoring）は説明どおり「Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用」します（運用上の意図的設計）。
- paper_trading 環境では発注処理は本番 DB と分離され paper_trading 用の SQLite を使用するため、本番データに影響を与えません。
- .env は機密情報を含むため絶対にリポジトリにコミットしないでください（config_setup 内にも注意書きを記載）。
- 一部モジュール（例: research/factor_research.py）は実装途中の箇所があります。必要に応じて追加実装・テストを行ってください。
- system/monitoring/engine 周りの詳細な動作（例: BrokerClient の具体実装、ExecutionEngine の内部処理、SystemMonitor の詳細）は該当モジュールの実装に依存します。運用前に validate_config.py による検証を実行してください。

---

今後のリリースでは以下を予定しています（例）:
- factor_research の完全実装とテスト
- ブローカークライアント実装の拡充（API モックと実装の検証）
- 単体テスト・CI 設定の追加
- ドキュメント（Architecture / Operation / PortfolioConstruction）の整備

もし CHANGELOG に追記したい変更点や、日付の修正、リリース方針（Unreleased セクションなど）の希望があれば教えてください。