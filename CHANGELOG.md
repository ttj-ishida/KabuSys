CHANGELOG
=========

すべてのリリースは Keep a Changelog の形式に準拠します。
https://keepachangelog.com/ja/1.0.0/

Unreleased
----------
- 現在未リリースの変更はありません。

[0.1.0] - 2026-04-19
-------------------
初期公開リリース。

Added
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV=paper_trading 時は paper_trading 専用の SQLite（data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory を利用して実行環境に応じたブローカークライアントを切り替え。
    - ExecutionEngine を別スレッドで実行し、data/stop_requested.flag を監視して安全に停止可能。
    - 起動時にプロセス優先度を設定（set_process_priority("high")）。
  - run_monitoring.py
    - SystemMonitor のポーリングループを実行するエントリポイント。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバック。
    - 監視は環境にかかわらず本番用 sqlite_path を使用する設計。
    - 停止フラグ（data/stop_requested.flag）を検知してループ終了。
    - 起動時にプロセス優先度を設定（set_process_priority("high")）。
- 設定管理
  - config.py
    - .env 自動読み込み機能（プロジェクトルート検出 (.git / pyproject.toml) に基づく）。
    - .env/.env.local の読み込みルール（OS 環境変数を保護しつつ .env.local で上書き可能）。
    - .env 行パーサの強化（export プレフィックス対応、クォート文字列中のエスケープ、インラインコメントの扱い）。
    - Settings クラスを提供し、各種設定をプロパティとして取得（検証付き: env / LOG_LEVEL / PAPER_FILL_MODE など）。
  - config_setup.py
    - 対話式ウィザードで .env を作成・更新する CLI。
    - シークレット入力のマスク表示、選択肢、デフォルト、保存確認をサポート。
- 設定検証ツール
  - validate_config.py
    - .env と config/*.yaml の基本的な存在・形式チェックを行う CLI。
    - --strict モードで警告も失敗扱いにできる。
    - PyYAML の未インストールを検出して YAML 検証をスキップするロバスト設計。
- ポートフォリオ/資金配分ライブラリ（純粋関数）
  - kabusys.portfolio
    - portfolio_builder.py: select_candidates, calc_equal_weights, calc_score_weights（スコア全0 の場合のフォールバック含む）。
    - risk_adjustment.py: apply_sector_cap（セクター集中制限）、calc_regime_multiplier（市場レジームに応じた乗数）。
    - position_sizing.py: calc_position_sizes（risk_based / equal / score の allocation_method、lot_size 単位丸め、aggregate cap のスケーリング、cost_buffer を考慮した安全な配分）。
- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプト（SQLite を直接クエリして稼働率、注文成功率、レイテンシ等を集計）。
    - P95 計算、閾値に基づく PASS/FAIL 判定を実装。
- ユーティリティ
  - utils/logging_setup.py
    - 統一ロギング設定ユーティリティ。標準出力（stdout）への StreamHandler と日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみでフォールバック。
    - 既存ハンドラを安全にクリーンアップして二重設定を回避。
  - utils/process_priority.py
    - Windows / POSIX の差を吸収してプロセス優先度（nice / priority class）を設定するユーティリティ。
    - CPU affinity 設定関数 set_cpu_affinity を提供（コア数指定で最初の N コアに固定）。
    - 権限不足や未対応環境時は警告を出してスキップする安全策を実装。
- パッケージ情報
  - __init__.py に __version__ = "0.1.0" を追加。

Changed
- （初期リリースのため変更履歴は無し）

Fixed
- .env パーサの挙動改善
  - export プレフィックスのサポート、クォート中のバックスラッシュエスケープ処理、インラインコメント判定の厳密化により .env 解析の堅牢性を向上。
- ロギング
  - stdout を主に使用するように変更（cron/タスクスケジューラでのリダイレクト考慮）。
  - ログディレクトリ作成失敗時やファイルハンドラ作成失敗時にフォールバックしてアプリを継続できるように改善。

Security
- config_setup にて生成される .env に関して
  - シークレット項目は対話中はマスク表示される（表示・保存時は実際の値）。README 等へ .env を Git にコミットしない旨を明記して出力。

Notes / Known issues
- research/factor_research.py はファクター計算ロジックを実装中（ソースに途中で切れた箇所あり）。本リリースでは部分実装または未完の可能性があります。今後のリリースで完了予定。
- 一部の TODO コメント（例: position_sizing の銘柄別 lot_size サポート、apply_sector_cap の価格フォールバック等）が残っており、将来の改善対象です。
- run_monitoring の設計上「監視は環境にかかわらず本番 sqlite_path を使用する」ため、開発環境での運用時は意図しない DB を更新しないよう注意してください。

導入方法 / 使い方（抜粋）
- .env 初期作成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config
- 実行エンジン起動: python -m kabusys.run_execution
- 監視プロセス起動: python -m kabusys.run_monitoring
- Paper Trading 検証レポート: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

ライセンス、貢献、その他のメタ情報はリポジトリの README を参照してください。