# CHANGELOG

すべての変更は Keep a Changelog の慣例に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/

注意: 以下はリポジトリ内のソースコードから機能・変更点を推測して作成した初期の変更履歴です。

## [Unreleased]

- ドキュメントやテストの追加予定
- factor_research の残り実装（モメンタム等の計算ロジックの完成）
- その他リファクタ・最適化

---

## [0.1.0] - 2026-04-19

### Added
- 基本アプリケーション構成を追加
  - パッケージ初期バージョン (src/kabusys/__init__.py: __version__ = "0.1.0")
- 起動スクリプト
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）
    - ExecutionEngine の起動、スレッド管理、停止フラグ検出、paper_trading 時の専用 DB 分離（data/paper_trading.db）
    - BrokerClientFactory を使用したブローカークライアント生成
    - PID ファイル管理および高優先度プロセス設定の統合
  - 監視（SystemMonitor）ポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
    - 停止フラグファイル検出、DB 初期化、duckdb 接続
- 環境設定・検証ツール
  - 対話式 .env 作成ウィザードを追加（src/kabusys/config_setup.py）
    - .env の読み込み・既存値再利用、各設定項目の対話入力、保存機能
  - 起動前設定検証 CLI を追加（src/kabusys/validate_config.py）
    - 必須環境変数チェック、KABUSYS_ENV 検証、DB パス・YAML ファイル存在確認、--strict モード
- 設定管理
  - Settings クラスによる環境変数ラッパーを追加（src/kabusys/config.py）
    - 自動 .env ロード機構（プロジェクトルート判定: .git / pyproject.toml を探索）
    - .env パースの強化（export 形式やクォート、インラインコメント対応）
    - 各種プロパティ（J-Quants / kabu API / DB パス / paper_trading 設定 / 監視閾値 等）
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化
- ロギング・プロセスユーティリティ
  - 統一ログ設定ユーティリティ（src/kabusys/utils/logging_setup.py）
    - stdout 出力 + 日次ローテートファイル出力（TimedRotatingFileHandler）、LOG_DIR/LOG_LEVEL に対応
    - ハンドラ重複防止のため既存ハンドラをクリアして再設定
  - プロセス優先度 / CPU affinity ユーティリティ（src/kabusys/utils/process_priority.py）
    - Windows/Linux/macOS に対応した優先度設定と CPU affinity 固定（psutil 利用）
    - 権限不足や未対応 OS 時は警告を出してフォールバック
- ポートフォリオ構築モジュール（純粋関数群）
  - 候補選定・重み付け（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates, calc_equal_weights, calc_score_weights
  - リスク調整（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap（セクター集中制限）、calc_regime_multiplier（レジームに基づく乗数）
  - ポジションサイジング（src/kabusys/portfolio/position_sizing.py）
    - risk_based / equal / score の配分方式対応、lot_size（単元）丸め、aggregate cap スケーリング、cost_buffer を反映
  - これらをまとめてエクスポート（src/kabusys/portfolio/__init__.py）
- Paper Trading 検証ツール
  - 検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）
    - 稼働率、注文成功率、送信率、レイテンシ（平均 / 最大 / P95） の集計・判定ロジック
    - CLI オプションで期間指定（--from / --to）および DB パス指定（--db）
    - 判定閾値（稼働率、成功率、P95 レイテンシ等）を定義
- 研究用ファクタモジュールの骨格
  - factor_research の初期コード（src/kabusys/research/factor_research.py）
    - Momentum / Value / Volatility / Liquidity 計算方針と定数を定義（DuckDB ベース想定）
    - （実装途中の関数あり）

### Changed
- .env の読み込み順を明確化（OS環境変数 > .env.local > .env）。既存の OS 環境変数は保護して上書きされないように実装（src/kabusys/config.py）。
- logging の挙動: コンソール出力は stdout に統一（stderr ではない）（src/kabusys/utils/logging_setup.py）。
- Execution/Monitoring 起動時にプロセス優先度を最初に設定するようにし、起動ログに環境名を出力（run_execution.py, run_monitoring.py）。

### Fixed
- MONITOR_POLL_INTERVAL のパースで 0 以下や不正値に対してデフォルトにフォールバックし、警告を出す処理を実装（src/kabusys/run_monitoring.py）。
- .env パーサでクォート内のエスケープ文字やインラインコメントを正しく処理するよう改善（src/kabusys/config.py）。
- ログディレクトリ作成に失敗した場合も、ファイルハンドラをスキップしてコンソール logging にフォールバックするように堅牢化（src/kabusys/utils/logging_setup.py）。

### Security
- .env ファイル生成ウィザードで注意書きを明記（.env を Git にコミットしないこと）（src/kabusys/config_setup.py）。
- 必須環境変数が未設定の場合、validate_config で明示的にエラーとするチェックを導入（src/kabusys/validate_config.py）。

### Notes / Misc
- DB 関連:
  - monitoring 用の SQLite は環境に依らず本番 sqlite_path を使用（監視・ログ用）（run_monitoring.py）。
  - paper_trading 環境では paper 用専用 SQLite を使用して本番 DB と分離（run_execution.py）。
  - duckdb は分析用途で起動スクリプトから接続（run_execution.py, run_monitoring.py）。
- 多くの機能は外部コンポーネント（ExecutionEngine, SystemMonitor, BrokerClientFactory, OrderManager, Reconciler, RiskManager 等）に依存しており、それらの実装は別モジュールで提供される想定。

---

今後の予定（推測）
- factor_research の完全実装（各種ファクター計算）
- テストスイートの追加
- ドキュメント（設計書・使用例）の充実
- CI/Release ワークフロー構築

---

（注）上記 CHANGELOG は提供されたコードの内容から機能や意図を推測して作成しています。実際のリリース履歴に合わせて必要に応じて調整してください。