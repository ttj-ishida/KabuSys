CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

[Unreleased]
------------

- （現状なし）

[0.1.0] - 2026-04-24
-------------------

Added
- 基本機能を実装した初回リリース。
  - 実行用スクリプト
    - run_execution: ExecutionEngine の起動スクリプトを追加。KABUSYS_ENV に応じて paper_trading 用 DB を分離して使用（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）。停止フラグ検出、PID ファイル管理、スレッド実行/停止処理を実装。
    - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境に関わらず本番 sqlite_path を使用する仕様。
  - 設定管理
    - config.py: 環境変数 / .env 自動読み込み機能を実装。プロジェクトルートを .git または pyproject.toml から探索して .env / .env.local を読み込みる（OS 環境変数を保護）。Settings クラスを導入し、各種設定（DB パス、API トークン、監視閾値、環境判定等）をプロパティとして提供。
    - config_setup: .env の対話式ウィザードを追加。よく使う設定項目（KABUSYS_ENV、API トークン、DB パス、LOG_LEVEL、Kill Switch 等）の作成・更新を支援し .env を安全に書き込む。
    - validate_config: 起動前チェック CLI を追加。必須環境変数の確認、KABUSYS_ENV/LOG_LEVEL の検証、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在および（PyYAML がある場合）パース検証、本番環境向けガード（LINE 通知・Kill Switch 設定）などの検査を行う。--strict オプションで警告を FAIL 扱いにする。
  - ポートフォリオ構築（純粋関数群）
    - portfolio.portfolio_builder: シグナル選定（スコア降順, tie-break に signal_rank）、等重配分、スコア重み配分（全スコア 0 の場合は等配分へフォールバック）。
    - portfolio.risk_adjustment: セクターの集中制限適用（既存保有を集計し上限超過セクターの候補除外）、市場レジームに応じた投下資金乗数（bull/neutral/bear）を実装。
    - portfolio.position_sizing: 発注株数計算（risk_based / equal / score）、単元株丸め、1 銘柄上限・aggregate cap、コストバッファを考慮したスケーリングと残差処理ロジックを実装。
  - リサーチ / ファクター
    - research.factor_research: モメンタム等のファクター計算モジュールを追加（duckdb 接続を受け prices_daily / raw_financials を参照する設計）。（モジュール冒頭の設計方針と定数を含む。）
  - ツール
    - tools.paper_verification_report: Paper Trading 用の検証レポート生成ツールを追加。期間指定 (--from / --to) や DB パス指定 (--db / 環境変数) に対応。稼働率、注文成功率、送信率、P95 レイテンシ等を集計し PASS/FAIL を判定する閾値を定義。
  - ユーティリティ
    - utils.logging_setup: 統一的なログ設定ユーティリティを実装。stdout への StreamHandler と日次ローテート（TimedRotatingFileHandler）を持つ。ログディレクトリ自動作成、既存ハンドラのクリーンアップ、LOG_LEVEL / LOG_DIR の解決順をサポート。ファイル作成に失敗した場合はコンソール出力のみで継続。
    - utils.process_priority: psutil を用いたプロセス優先度設定と CPU affinity 設定を実装。Windows と POSIX（Linux/Mac 等）の差分を吸収し、権限不足等の場合は警告でスキップ。
  - DB 統合
    - DuckDB と SQLite を併用する設計。duckdb は分析用途（prices 等）向け、SQLite は監視・トレードログ等の永続化に使用。
  - 監視関連
    - monitoring 側の DB 初期化を保証する init_monitoring_db 呼び出しを run 系スクリプトに追加（冪等にテーブルを用意することで起動安全性を向上）。

Changed
- 環境読み込みの堅牢化
  - .env パーサで export プレフィックス対応、クォート（シングル/ダブル）内のバックスラッシュエスケープ、インラインコメント処理、空行やコメント行のスキップを実装。これにより多様な .env フォーマットに対応。
  - .env 自動読み込みの優先度を OS 環境変数 > .env.local > .env に明確化。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化を追加（テスト用途想定）。
- run_monitoring/run_execution の振る舞い
  - 起動時にプロセス優先度を最優先で "high" に設定する呼び出しを追加。
  - 停止フラグ（data/stop_requested.flag）を検出して安全にループ/エンジンを終了する制御を実装。
  - run_monitoring: check_once() の例外を捕捉してログ出力し、次ポーリングに継続する耐障害性を確保。
- Settings API の明確化
  - paper_fill_mode のバリデーション（allowed: instant, partial, never, reject）や各種閾値（CPU/MEM/DISK）がプロパティで提供されるよう整理。
  - is_paper / is_live / is_dev のユーティリティプロパティを追加。

Fixed
- ログ設定の安全化
  - 既存ハンドラを重複して登録する問題に対処するため、setup_logging() で既存ハンドラを flush/close の上削除してから再設定するよう修正。
  - ログファイル出力先のディレクトリ作成に失敗した場合は例外で停止せず、コンソール出力のみで継続する仕組みに変更。
- process_priority の例外ハンドリング強化
  - psutil の権限エラーやプラットフォーム差異による AttributeError/NotImplementedError を捕捉して警告出力するように改善。

Notes / Implementation details
- Paper Trading（paper_trading）環境は本番 DB と分離され、専用 SQLite（デフォルト data/paper_trading.db）を使用する設計になっています。MockBrokerClient を使用することで実環境への影響を回避します。
- run_monitoring は MONITOR_POLL_INTERVAL に 0 以下や非整数が設定された場合にデフォルト 60 秒へフォールバックする安全策を備えています。
- portfolio モジュールは副作用を持たない純粋関数群（メモリ内計算）として実装されており、ユニットテストで単体検証しやすい設計です。
- validate_config は PyYAML が未インストールの場合に YAML 内容検証をスキップして警告を出します（導入環境で依存を柔軟に扱えるようにするため）。

Acknowledgements
- この CHANGELOG は現行コードベースの内容から推測してまとめたものであり、実際のコミット履歴やリリースノートと若干の齟齬がある可能性があります。必要ならば個々の機能・変更点についてさらに詳細な項目（影響範囲、マイグレーション手順、既知の制約など）を追記します。