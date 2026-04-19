# CHANGELOG

すべての変更は Keep a Changelog の理念に従って記載しています。セマンティックバージョニングを想定しています。

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-19
初回リリース。システムの起動スクリプト、設定管理、ポートフォリオ構築/リスク調整、ユーティリティ、検証ツール類を実装しました。

### 追加 (Added)
- コア情報
  - パッケージメタ情報を追加（kabusys.__version__ = "0.1.0"）。（src/kabusys/__init__.py）

- 起動スクリプト
  - SystemMonitor ポーリングループ用の起動スクリプトを追加。環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能。監視は常に本番 sqlite_path を使用。（src/kabusys/run_monitoring.py）
  - ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading 時はペーパートレード用 DB / MockBrokerClient を使用し、本番 DB と分離して運用可能。（src/kabusys/run_execution.py）

- 設定管理・検証
  - 環境変数/.env 自動読み込みと Settings クラスを実装。デフォルト値・バリデーションを備えたプロパティ群を提供（DBパス、ログレベル、環境種別、Paper Trading 用設定等）。（src/kabusys/config.py）
  - .env の対話式セットアップウィザードを実装。既存 .env の読み込み・編集・保存をサポート。（src/kabusys/config_setup.py）
  - 起動前設定検証 CLI を実装。必須環境変数、KABUSYS_ENV、ログレベル、DBパス、config/*.yaml の存在/パース検証（PyYAML が存在する場合）や本番環境向けの注意喚起を行う。（src/kabusys/validate_config.py）

- ポートフォリオ構築（純粋関数群、DB参照なし）
  - 候補選定・重み算出関数を実装（候補のソート/上位N選定、等金額配分、スコア加重配分）。スコア全0時のフォールバック挙動を含む。（src/kabusys/portfolio/portfolio_builder.py）
  - セクター集中制限とレジームに応じた乗数を実装。既存保有からセクター暴露を計算し、上限を超えるセクターの新規候補を除外。（src/kabusys/portfolio/risk_adjustment.py）
  - 株数決定ロジック（allocation_method: "risk_based" / "equal" / "score"）を実装。単元株丸め、ロット単位でのスケーリング、aggregate cap（利用可能現金に合わせたスケールダウン）、コストバッファ考慮を実装。（src/kabusys/portfolio/position_sizing.py）
  - portfolio パッケージのエクスポートを整理。（src/kabusys/portfolio/__init__.py）

- ユーティリティ
  - 一貫したログ設定ユーティリティを実装。stdout への StreamHandler と日次ローテートする TimedRotatingFileHandler（デフォルト logs/<app_name>.log、30日保持）をルートロガーへ設定。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみ継続。（src/kabusys/utils/logging_setup.py）
  - プロセス優先度・CPU affinity 設定ユーティリティを実装。Windows と POSIX 系を吸収し、AccessDenied 等の例外を安全にハンドリング。set_process_priority と set_cpu_affinity を提供。（src/kabusys/utils/process_priority.py）

- 運用ツール
  - Paper Trading の検証レポート生成スクリプトを追加。SQLite の paper_trading DB から稼働率、注文成功率（fill/send）、リスク却下数、レイテンシ（平均/最大/P95）を集計し、閾値に基づく PASS/FAIL 判定を出力。（src/kabusys/tools/paper_verification_report.py）
    - 既定の判定閾値（稼働率、注文成功率、送信率、P95 レイテンシ）を定義。
    - コマンドライン引数で期間（--from / --to）や DB パス（--db）を指定可能。

- 研究用モジュール（骨組み）
  - ファクター計算モジュールの骨組みを追加（モメンタム、移動平均乖離、ATR、流動性等の計算方針と定数を定義）。DuckDB 接続を使って prices_daily / raw_financials を参照する設計。実装は一部（ファイル末尾で切れている）。（src/kabusys/research/factor_research.py）

### 変更 (Changed)
- なし（初回リリース）

### 修正 (Fixed)
- なし（初回リリース）

### 既知の挙動・注意点 (Notes)
- .env の自動読み込みはデフォルトで有効。テスト等で無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。（src/kabusys/config.py）
- run_monitoring は停止制御にプロジェクトルート/data/stop_requested.flag を参照します。run_execution も同様に停止フラグと execution.pid を使用します。
- Logging 設定は stdout に出力する設計です（cron 等で stdout/stderr を一本化する運用を想定）。
- process_priority の設定は OS によっては権限不足により失敗することがあります。その場合は警告ログを出し処理を継続します。
- Paper Trading は production DB と完全に分離する設計になっています。KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を使用します。
- portfolio の position sizing は単元 (lot_size) の丸めや aggregate cap のためのスケールダウンロジックを含みます。今後、銘柄別 lot_size 対応や価格フォールバック（前日終値等）の拡張が検討されています。

### 互換性 / マイグレーション (Migration)
- 既存の設定: .env 形式は export 文、クォート、インラインコメント等に耐性のあるパーサを実装していますが、手動で編集した .env に特殊文字がある場合は config_setup で再確認を推奨します。
- 本番運用時は KABUSYS_ENV を正しく設定し、LINE 通知設定等の本番ガードを validate_config で確認してください。

---

今後の予定（例）
- factor_research の完全実装と単体テスト追加
- execution 系コンポーネント（ExecutionEngine / BrokerClientFactory / OrderManager 等）の統合テスト・ドキュメント整備
- ポートフォリオ関連の銘柄別 lot_size 対応、価格フォールバック実装
- モニタリング・アラート機能の強化（LINE 通知の統合など）

--- 
（本 CHANGELOG はコード内容から推測した変更点を基に作成しています。実際のリリースノートとして利用する場合は必要に応じて加筆・修正してください。）