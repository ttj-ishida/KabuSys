# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

（現在未リリースの作業はありません）

## [0.1.0] - 2026-04-18

初回リリース。日本株自動売買システム「KabuSys」の基本機能を多数実装しました。

### Added
- 全体
  - パッケージの初期バージョンを 0.1.0 に設定。パッケージメタ情報は `src/kabusys/__init__.py` に記載。
  - dotenv 風の .env 自動ロード機能を実装。プロジェクトルート（.git または pyproject.toml を起点）を探索して `.env` / `.env.local` を読み込む（`src/kabusys/config.py`）。
  - 環境設定ウィザード CLI を追加。対話式で .env を作成・更新できる `python -m kabusys.config_setup`（`src/kabusys/config_setup.py`）。
  - 起動前チェック CLI を追加。`.env` と config/*.yaml の基本的な検証を行う `python -m kabusys.validate_config`（`src/kabusys/validate_config.py`）。
  - 実行用と監視用の起動スクリプトを追加:
    - 実行エンジン起動スクリプト（`src/kabusys/run_execution.py`）
    - 監視（SystemMonitor）ポーリングループ起動スクリプト（`src/kabusys/run_monitoring.py`）
  - Paper Trading 用検証レポート生成スクリプトを追加（`src/kabusys/tools/paper_verification_report.py`）。期間指定で稼働率・注文成功率・レイテンシなどを集計し PASS/FAIL 判定を行う。
- データベース / ファイル関連
  - DuckDB パス・SQLite パス等を環境変数で設定可能（`DUCKDB_PATH`, `SQLITE_PATH`, `PAPER_TRADING_SQLITE_PATH` をサポート。`src/kabusys/config.py`）。
  - 実行エンジン起動時、paper_trading 環境は専用の paper_trading DB（`data/paper_trading.db` デフォルト）を使用し、本番 DB と完全分離（`run_execution.py`）。
  - 監視（monitoring）は KABUSYS_ENV にかかわらず本番用の sqlite_path を使用する旨を明記（`run_monitoring.py`）。
  - 停止フラグ / PID 管理の仕組みを実装（`data/stop_requested.flag`, `data/execution.pid` を利用）。
- ロギング / プロセス制御
  - 統一ロギング設定ユーティリティを追加。コンソール（stdout）と日次ローテートファイルをルートロガーに設定（`src/kabusys/utils/logging_setup.py`）。
    - ログディレクトリ作成に失敗した場合はファイルハンドラをスキップし、コンソール出力のみで継続するフォールバックあり。
    - stdout を利用することで cron 等でのリダイレクトと親和性を高める設計。
  - プロセス優先度 / CPU affinity 設定ユーティリティを追加。Windows / POSIX の差分を吸収する（`src/kabusys/utils/process_priority.py`）。
- ポートフォリオ構築（純粋関数群）
  - 候補選定と重み算出（等配分・スコア加重）（`src/kabusys/portfolio/portfolio_builder.py`）。
  - セクター集中制限、レジーム乗数（`src/kabusys/portfolio/risk_adjustment.py`）。
  - 株数算出・単元丸め・投下資金上限の処理（`src/kabusys/portfolio/position_sizing.py`）。
  - 上記をまとめて公開するパッケージインターフェース（`src/kabusys/portfolio/__init__.py`）。
- 研究 / ファクター計算
  - DuckDB に対するファクター計算モジュールの骨組みを追加（モメンタム / MA200 / ATR / ボラティリティ等）（`src/kabusys/research/factor_research.py`）。
- 実行系（ExecutionEngine）周辺（スケルトン）
  - ブローカーファクトリ、ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager 等の起動・組み立てフローを run_execution スクリプトに実装（依存コンポーネントの組み立てが一通り動作する設計）。

### Changed
- 環境変数読み込み挙動
  - .env のパースロジックでクォートや export 形式、行末コメントの取り扱いを細かく実装し、より実運用に耐える仕様に（`src/kabusys/config.py`）。
  - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により無効化可能。

### Fixed
- .env パーサー
  - シングル／ダブルクォート内のバックスラッシュエスケープに対応し、インラインコメントを誤認しないよう改善（`src/kabusys/config.py`）。
- ロギング初期化
  - 既存ハンドラを安全に flush/close してから削除することで二重登録を防止（`src/kabusys/utils/logging_setup.py`）。
- ポートフォリオ重み算出
  - スコア合計が 0 の場合に等金額配分へフォールバックするようにし、異常値でのゼロ除算を回避（`src/kabusys/portfolio/portfolio_builder.py`）。
- 実行・監視ループの安全停止
  - 停止フラグ（stop_requested.flag）検知で安全にループを抜ける処理を実装（`run_execution.py`, `run_monitoring.py`）。
  - monitor.check_once() 内で例外が発生してもループを継続するように例外捕捉を実装（`run_monitoring.py`）。

### Removed
- （今回のリリースで削除された機能はありません）

### Security
- .env を絶対にリポジトリにコミットしない旨をウィザード出力に明記（`src/kabusys/config_setup.py`）。

### Notes / Known limitations
- `src/kabusys/research/factor_research.py` はファクター計算ロジックの骨組みを含みますが、環境やテーブルスキーマに依存する部分の実装／テストが必要です。
- 一部の機能（ブローカークライアントや ExecutionEngine の内部実装、DuckDB のスキーマ等）は外部実装や設定ファイル（config/*.yaml）に依存します。`validate_config` で検出できる設定不足を確認してください。
- process priority / cpu affinity の設定は権限や OS により失敗することがあります（その場合は警告ログ出力でスキップします）。

---

以上がコードベースから推測して作成した CHANGELOG.md です。必要であれば、さらに細かいコミット単位や担当者・関連 Issue などを付加できます。どの粒度で記載するか指示があれば調整します。