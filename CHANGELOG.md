# Changelog

すべての重要な変更点を記録します。本ファイルは Keep a Changelog の形式に準拠しています。
今後のリリースではセクションを追加して更新してください。

フォーマット:
- Added: 新機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Security: セキュリティ修正

## [Unreleased]
- 今後のマイナー改善やドキュメント整備を予定

## [0.1.0] - 2026-04-19
初回公開リリース。自動売買システム KabuSys の基礎機能を実装しました。

### Added
- 全体
  - パッケージ初期バージョンを追加（__version__ = 0.1.0）。
  - DuckDB/SQLite を用いたデータ保存・分析基盤を統合。
  - 環境変数および .env 管理機能を追加（kabusys.config）。
    - プロジェクトルート自動検出（.git または pyproject.toml を探索）。
    - .env/.env.local の自動読み込み（OS 環境変数を保護）。
    - クォートやエスケープ、インラインコメントに対応した .env パーサー実装。
  - 対話式環境設定ウィザードを追加（kabusys.config_setup）。
    - .env の初期作成・更新を対話形式で実施可能。
  - 設定検証 CLI を追加（kabusys.validate_config）。
    - 必須環境変数チェック、DB パス・YAML 設定ファイルの存在/パース検証。
    - --strict モードにより警告を失敗扱いにできる。
  - 起動スクリプト群を追加
    - run_execution: ExecutionEngine の起動スクリプト（本番 / paper_trading の DB 分離対応）。
    - run_monitoring: SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL による調整）。
  - Execution 系
    - ExecutionEngine の起動フローを実装（依存コンポーネントの組み立て、デーモン スレッドでの実行）。
    - BrokerClientFactory による本番/ペーパートレード切替（paper_trading 時は MockBrokerClient と専用 SQLite を使用）。
    - OrderRepository / OrderManager / RiskManager / Reconciler 等の初期的な実装と既定設定を追加。
    - RiskConfig によるリスク制約（最大ポジション比率、利用率、レートリミット、サーキットブレーカー等）。
  - Monitoring 系
    - SystemMonitor の起動および監視結果格納のための DB 初期化ユーティリティを実装。
    - stop フラグ（data/stop_requested.flag）による安全停止機構を採用。
  - ポートフォリオ構築（純粋関数群）
    - 銘柄選定・重み算出（select_candidates, calc_equal_weights, calc_score_weights）。
    - セクター集中制限・レジーム乗数（apply_sector_cap, calc_regime_multiplier）。
    - 位置サイズ計算（calc_position_sizes）：リスクベース / 等配分 / スコア加重方式、lot サイズ丸め、aggregate cap によるスケーリング実装。
  - リサーチ / ファクター計算
    - DuckDB を用いるファクター計算モジュールのスケルトンを追加（momentum 等の指標を計算予定）。
  - ユーティリティ
    - 統一ログ設定ユーティリティを追加（kabusys.utils.logging_setup）。
      - stdout 出力（StreamHandler）と日次ローテーションのファイルハンドラを設定。
      - ログディレクトリ作成失敗時にファイル出力をスキップするフォールバックを実装。
    - プロセス優先度・CPU affinity 設定ユーティリティを追加（kabusys.utils.process_priority）。
      - Windows / POSIX（Linux, Darwin, FreeBSD）向けの差分吸収。
      - アクセス権限や未対応 OS 時のフォールバック/警告を実装。
  - ツール
    - Paper Trading 向け検証レポート生成スクリプトを追加（kabusys.tools.paper_verification_report）。
      - 稼働率、注文成功率、送信率、P95 レイテンシ等を計算し PASS/FAIL 判定。
      - 日付レンジフィルタ、P95 計算、データ欠損時の N/A 表示対応。

### Changed
- 起動時のプロセス優先度をデフォルトで "high" にセットする方針を採用（run_monitoring / run_execution）。
- ログ設定の既定値と解決順（引数 > 環境変数 > デフォルト）を明確化。

### Fixed
- .env パースにおけるクォート・エスケープ処理とインラインコメント認識を強化。これにより複雑な値やコメント付き行の誤読を回避。
- ログディレクトリ作成失敗時に起動が停止する問題を回避し、標準出力のみで継続するように修正。
- 不正な MONITOR_POLL_INTERVAL 値（0 以下や非数値）を検出した際にデフォルトにフォールバックするように修正（監視ループの ValueError 回避）。
- Execution 起動時に paper_trading 環境で本番 DB を誤って使用するリスクを排除（paper_trading は paper_sqlite_path を使用）。

### Security
- 特になし

---

注意:
- 本 CHANGELOG はコードベースから推測して記載したものであり、実際のコミット履歴やリリースノートとは差異がある可能性があります。必要に応じて日付・バージョンや個別の修正内容を実際の履歴に合わせて調整してください。