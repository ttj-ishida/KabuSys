# CHANGELOG

すべての変更は「Keep a Changelog」形式に準拠して記載しています。  
フォーマットの詳細: https://keepachangelog.com/ja/1.0.0/

注: 以下は提供されたコードベースから推測して作成した変更履歴です。

## [Unreleased]

なし

## [0.1.0] - 2026-04-21

Added
- プロジェクト初回リリース相当の機能群を追加。
  - 基本パッケージ情報
    - パッケージバージョンを `__version__ = "0.1.0"` として定義（src/kabusys/__init__.py）。
  - 環境設定・管理
    - .env 自動ロード機構を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。OS 環境変数を優先し、`.env` → `.env.local` の順でロード（src/kabusys/config.py）。
    - .env のパース機能強化：`export` プレフィックス、シングル／ダブルクォート、エスケープ、インラインコメント処理に対応（src/kabusys/config.py）。
    - Settings クラスを提供して設定値を型付きに取得可能（各種パス、環境判定フラグ、しきい値、Paper Trading 設定等）（src/kabusys/config.py）。
    - 対話型環境設定ウィザード CLI を追加（`.env` の初期作成・更新支援）：`python -m kabusys.config_setup`（src/kabusys/config_setup.py）。
    - 設定検証 CLI を追加（`.env` と config/*.yaml の検証、--strict オプション）：`python -m kabusys.validate_config`（src/kabusys/validate_config.py）。
      - 必須環境変数チェック（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）。
      - DB パス、ログレベル、config/*.yaml の存在・パース確認（PyYAML 未インストール時は警告）。
      - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定や Kill Switch の安全性確認）。
  - ロギング・プロセス管理ユーティリティ
    - 統一ロギング設定ユーティリティを追加：コンソール (stdout) と日次ローテートのファイルハンドラをルートロガーに設定（ログディレクトリ作成失敗時はファイル出力を無効化）（src/kabusys/utils/logging_setup.py）。
    - プロセス優先度・CPU affinity 設定ユーティリティを追加：Windows/Linux/macOS を吸収して優先度を設定、psutil ベースでアクセス失敗時は警告でスキップ（src/kabusys/utils/process_priority.py）。
  - 実行・監視エントリスクリプト
    - ExecutionEngine 起動スクリプトを追加：プロセス優先度設定、Paper Trading と本番での DB 分離、BrokerClientFactory によるブローカ抽象化、ExecutionEngine の起動/停止管理（`data/execution.pid`, `data/stop_requested.flag` を使用）（src/kabusys/run_execution.py）。
      - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、Paper Trading 用 DB（data/paper_trading.db 既定）を使用する設計を想定。
    - SystemMonitor ポーリングループ起動スクリプトを追加：ポーリング間隔を環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）、停止フラグ検知で安全に終了（src/kabusys/run_monitoring.py）。
      - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する旨の実装注記あり。
  - Execution サブシステム関連（実行時の主要コンポーネントの組み立て）
    - OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine 構成（`EngineConfig`, `RiskConfig` によりリスク制御パラメータや target_date を設定）（src/kabusys/run_execution.py と参照モジュール）。
  - ポートフォリオ構築ライブラリ（純粋関数群）
    - 候補選定 / 重み計算（等分配・スコア加重）：select_candidates, calc_equal_weights, calc_score_weights（src/kabusys/portfolio/portfolio_builder.py）。
      - スコアが全て 0 の場合に等重配分へフォールバックする警告あり。
    - セクター集中制限・レジーム乗数：apply_sector_cap（セクター過集中が閾値を超える候補除外）、calc_regime_multiplier（bull/neutral/bear の乗数）（src/kabusys/portfolio/risk_adjustment.py）。
    - ポジションサイズ計算（単元丸め、リスクベース／等分配／スコアベースの割当、aggregate cap によるスケーリング、コストバッファ反映）：calc_position_sizes（src/kabusys/portfolio/position_sizing.py）。
      - lot_size（単元）や cost_buffer を考慮した安全な丸めロジックを実装。
    - portfolio パッケージのエクスポートを提供（src/kabusys/portfolio/__init__.py）。
  - 研究・ファクター計算基盤（開始）
    - DuckDB を用いたファクター計算モジュールの骨組みを追加（モメンタム等の計算規定と calc_momentum の実装開始。ファイルは部分的に提供）（src/kabusys/research/factor_research.py）。
      - DuckDB 接続を受け取り prices_daily / raw_financials を参照してファクターを計算する設計。
  - ツール
    - Paper Trading 検証レポート生成スクリプトを追加：
      - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等を算出して PASS/FAIL 判定（閾値定義あり）。
      - SQLite DB（デフォルト data/paper_trading.db）から集計してコンソールにレポート出力（src/kabusys/tools/paper_verification_report.py）。

Changed
- 初期リリースのため「Changed」相当の履歴はなし（初回導入）。

Fixed
- 初期リリースのため「Fixed」相当の履歴はなし。

Security
- 初期リリースのため特記事項なし。

Notes / 備考
- 設定値やパスのデフォルト:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
  - LOG_DIR: logs/
- 監視ループは停止フラグファイル（data/stop_requested.flag）を用いるため、運用時はこのファイルの存在管理に注意してください。
- .env は機密情報を含むため Git 管理から除外することが README や生成ウィザード内で明記しています。
- 一部モジュールは外部依存（psutil, duckdb, PyYAML など）を前提としており、環境により機能制限や警告が出ます（validate_config や logging_setup が該当）。

今後の改善候補（推測）
- factor_research の完全実装（ファクター算出ロジックの完成）。
- 各コンポーネントの単体テストと CI 統合。
- 銘柄ごとの lot_size や価格フォールバック処理の実装強化（注記あり）。
- ExecutionEngine 周りの詳細なエラーハンドリング・メトリクス集計の拡張。

---  
参照: 各ファイルの実装・コメントを元に CHANGELOG を作成しました。追加のリリース履歴や日付の修正、より詳細な項目分割が必要であれば指示してください。