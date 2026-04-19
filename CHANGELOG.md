Keep a Changelog に準拠した CHANGELOG.md（日本語）

注意: 以下は提示されたコードベースの内容から推測して作成した変更履歴です。実際のコミット履歴ではなく、機能・設計の要点をリリースノート風にまとめたものです。

All notable changes to this project will be documented in this file.
The format is based on "Keep a Changelog" and this project adheres to
Semantic Versioning.

Unreleased
----------
（現時点の作業中の変更や今後の予定をここに記載します）

[0.1.0] - 2026-04-19
-------------------
Added
- 基本機能群を初期リリースとして導入。
  - 実行スクリプト
    - run_execution.py: ExecutionEngine 起動スクリプトを追加。
      - KABUSYS_ENV=paper_trading 時は paper 用専用 SQLite（data/paper_trading.db）を使用して本番 DB と完全分離。
      - BrokerClientFactory を用いて実際のブローカー／モックを切り替え可能。
      - ExecutionEngine をデーモンスレッドで実行し、外部停止フラグ（data/stop_requested.flag）で安全に停止可能。
      - 実行用 PID ファイルの取り扱い（data/execution.pid）。
    - run_monitoring.py: SystemMonitor 用のポーリングループ起動スクリプトを追加。
      - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - Monitoring は環境にかかわらず本番 sqlite_path を参照して監視テーブルを操作。
      - 停止フラグ検知でループを終了、KeyboardInterrupt による終了処理も実装。
  - 設定・ユーティリティ
    - config.py: 環境変数読み込み・ラッパーを実装。
      - プロジェクトルート検出（.git または pyproject.toml）に基づく .env 自動読み込み（.env / .env.local、OS 環境変数優先）。
      - .env の柔軟なパース（export 形式、クォート・エスケープ、行末コメントの扱いなど）。
      - Settings クラスに多数のプロパティを用意（DB パス、PID パス、しきい値、env 判定、paper_trading 設定など）。
      - PAPER_FILL_MODE 等の入力値検証。
    - config_setup.py: .env 初期作成・対話式ウィザードを追加。
      - デフォルト値、選択肢、シークレット入力対応、保存前確認などを実装。
    - validate_config.py: 起動前設定検証 CLI を追加。
      - 必須環境変数の検出、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスや config/*.yaml の存在・パース検証、KABUSYS_ENV=live 時の追加ガード警告。
      - --strict オプションで警告を失敗扱いにできる。
  - ロギング・プロセス制御
    - utils/logging_setup.py: 統一的ログ設定ユーティリティを追加。
      - stdout 出力（StreamHandler）と日次ローテートされるファイル出力（TimedRotatingFileHandler）をルートロガーに設定。
      - ログディレクトリ作成失敗時はファイル出力を無効化してコンソールのみで継続。
    - utils/process_priority.py: クロスプラットフォームのプロセス優先度/CPU affinity 設定ユーティリティを追加。
      - Windows/Linux/macOS に対応（psutil 利用）。権限不足や未対応 OS の場合は安全にスキップ。
  - ポートフォリオ構成（純関数群）
    - portfolio/portfolio_builder.py: 候補選定・等金額/スコア加重の重み計算を実装。
    - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）および市場レジームに応じた乗数（calc_regime_multiplier）を実装。
    - portfolio/position_sizing.py: 単元丸め・リスクベース／等分配／スコアベースの株数決定ロジックを実装。aggregate cap によるスケーリング、lot_size 単位での再配分ロジックを搭載。
  - ツール
    - tools/paper_verification_report.py: ペーパートレード検証レポート生成スクリプトを追加。
      - システム稼働率、注文成功率（fill rate）、送信率(send rate)、レイテンシ（平均/最大/P95）などを集計して PASS/FAIL 判定を出力。
      - デフォルト DB は data/paper_trading.db。日付フィルタ (--from/--to) に対応。
  - 研究用モジュール
    - research/factor_research.py: モメンタム等のファクター計算（DuckDB を利用）に着手。
      - Momentum (1M/3M/6M)、MA200乖離、ATR、流動性指標などの設計と一部実装（関数スケルトンと定数群を含む）。

Changed
- 初期設計として安全性・運用性を重視した設定。
  - .env 自動ロードの優先順位: OS 環境 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
  - run_monitoring は環境に依らず本番 sqlite_path を使用（監視は環境隔離の対象外にする意図）。
  - run_execution は paper_trading 環境で専用 DB を使用（発注履歴などを本番から分離）。

Fixed / Hardening
- .env パーサーの堅牢化（クォート・エスケープ処理、インラインコメントの扱い、export プレフィックスの対応）。
- logging_setup: ログディレクトリ作成やファイルハンドラ生成に失敗してもプロセスがクラッシュしないようフォールバックを実装。
- process_priority: 設定に失敗した場合は警告ログを出してスキップ（権限不足・未対応 OS に対応）。

Security
- 必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）を Settings.require で厳密に検査。validate_config による起動前チェックを推奨。
- .env ファイルは Git へコミットしない旨を config_setup のテンプレートに明記。

Notes
- ExecutionEngine / RiskManager / Reconciler / OrderManager 等の内部実装は本リリースで利用可能なインターフェースを提供しており、BrokerClientFactory を介して実際のブローカー実装（およびペーパートレード用のモック）を差し替えられる設計です。
- portfolio と position sizing のロジックは現状 global lot_size（全銘柄共通）を想定。将来的に銘柄別 lot_size を導入する拡張点あり（TODO コメントあり）。
- research/factor_research.py は途中で切れている（ソースの一部が未収録）。ファクター計算の完成とテストは今後のタスク。
- MONITOR_POLL_INTERVAL は不正な値（非数値や <= 0）の場合デフォルト（60 秒）にフォールバックする安全措置を実装。

Acknowledgments
- 初期アーキテクチャは運用観点（ログ、プロセス優先度、停止フラグ、設定検証）を重視して設計されています。今後のリリースではテストカバレッジ、ドキュメント、Research モジュールの完成、ExecutionEngine の詳細な動作確認に注力してください。