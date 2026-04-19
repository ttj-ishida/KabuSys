# Changelog

すべての変更は Keep a Changelog の仕様に準拠して記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

<!-- Unreleased セクションは存在しません。現在のコードベースから推測される初回リリースを記述しています。 -->

## [0.1.0] - 2026-04-19

初回リリース（コードベース解析に基づく）。日本株自動売買システム "KabuSys" のコアユーティリティ、実行エンジン起動スクリプト、監視、ポートフォリオ構築、設定管理ツールなどを含む。

### Added
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプト。
    - KABUSYS_ENV が `paper_trading` の場合は paper 専用 SQLite を使用し、本番 DB と完全分離。
    - 停止フラグ (data/stop_requested.flag) と PID ファイル管理をサポート。
    - エンジンをバックグラウンドスレッドで実行し、停止フラグ検知時に安全に停止するロジックを実装。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバック。
    - 監視は環境に関わらず本番 sqlite_path を使用する旨の設計。

- 設定管理
  - config.py
    - .env 自動読み込み（プロジェクトルート検出: .git or pyproject.toml）。
    - .env 読み込みの優先順・上書きポリシーを実装（OS 環境変数は保護）。
    - 環境変数のパースロジックを拡張（export プレフィックス、クォート文字列、インラインコメント処理など）。
    - Settings クラスで主要な設定プロパティを提供（DB パス、KABUSYS_ENV 検証、PAPER_FILL_MODE 検証など）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化をサポート。
  - config_setup.py
    - 対話式 .env 作成ウィザード (CLI)。
    - 秘匿値をマスクして表示、既存 .env の読み込み／更新、確認プロンプト、ファイル書き出しをサポート。

- 設定検証ツール
  - validate_config.py
    - .env と config/*.yaml の事前検証 CLI。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性チェック、ログレベルチェック、DB パス親ディレクトリチェック、YAML パースチェック（PyYAML が存在する場合）等を実施。
    - --strict オプションで警告を失敗扱いにできる。

- ログ／プロセスユーティリティ
  - utils/logging_setup.py
    - 統一的なロギング設定ユーティリティ。
    - stdout (StreamHandler) と日次ローテーション (TimedRotatingFileHandler) をルートロガーに設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - LOG_LEVEL / LOG_DIR からの解決、既存ハンドラのクリーンアップを実装。
  - utils/process_priority.py
    - Windows/Linux/Mac の差分を吸収したプロセス優先度設定ユーティリティ。
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。
    - 権限不足や未対応 OS を検出して安全にスキップ。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナル選定 (select_candidates)、等配分 (calc_equal_weights)、スコア重み配分 (calc_score_weights) を実装。
  - portfolio/risk_adjustment.py
    - セクター上限適用 (apply_sector_cap)、市場レジームに応じた乗数 (calc_regime_multiplier) を実装。
    - unknown セクターはセクター上限の対象外とする挙動。
    - 未知レジームに対しては警告を出し 1.0 でフォールバック。
  - portfolio/position_sizing.py
    - 発注株数決定ロジック (calc_position_sizes) を実装。
    - allocation_method: "risk_based", "equal", "score" をサポート。
    - 単元株（lot_size）丸め、1 銘柄上限、全体 aggregate cap、cost_buffer（手数料・スリッページ見積）を考慮したスケーリングロジックを実装。

- 監視／モニタリング DB 初期化
  - monitoring/monitoring_db.init_monitoring_db を起動時に呼び出し、監視用テーブルの存在を保証（冪等）。

- Execution 関連の構成要素（抽象化）
  - BrokerClientFactory（ブローカークライアント生成の抽象化）を導入し、paper_trading ではモッククライアントへ切替可能。
  - OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine といった主要コンポーネントを組み立てて ExecutionEngine を起動する実装を用意。
  - RiskManager の初期設定に broker.get_available_cash() を使用して initial_portfolio_value を決定。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite を解析して検証レポートを生成する CLI。
    - 稼働率・注文成功率・送信率・P95 レイテンシ等を算出し PASS/FAIL 判定を行う。
    - P95 計算、日時フィルタ (--from/--to)、DB パス指定 (--db) をサポート。
    - デフォルト閾値: 稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms。

- 研究用モジュール（着手）
  - research/factor_research.py
    - ファクター計算の骨組み（モメンタム、MA、ATR 等）を実装中。DuckDB 接続を受け取り prices_daily / raw_financials を参照する設計。

### Changed
- 設計/動作の明示
  - 監視（run_monitoring）は環境に依らず本番 sqlite_path を使用するという挙動が明記されている（監視データは production DB に集約される想定）。
  - run_execution は paper_trading 環境時に専用 DB を使用することで発注ロジックのデータ分離を確保。

### Fixed
- .env パーサの堅牢化
  - export プレフィックス、クォート内でのエスケープ、インラインコメントの扱いを改善して .env の誤読を低減。
- ロギングの安全性向上
  - ログディレクトリ作成失敗時の例外を吸収し、コンソールログのみで継続するように修正。

### Security
- シークレット扱いの配慮
  - config_setup の対話表示で機密値（トークン・パスワード）をマスク表示。
  - .env のデフォルトテンプレートに注意書き（.env を Git にコミットしないよう注意喚起）。

### Known issues / Notes
- research/factor_research.py は実装途中でファイル末尾が途切れている（「start_da」で終端）。ファクター計算ロジックはまだ未完成の可能性あり。
- position_sizing.calc_position_sizes の price 欠損時の注記（TODO）が残っている: price が 0.0 の場合のフォールバック価格選択（前日終値等）の扱いは将来的な改善ポイント。
- monitor/engine の例外処理は個別にキャッチしてループ継続するようになっているが、重大エラー時の運用上の通知（LINE等）やエスカレーションは Execution/Monitoring 側の設定に依存する。
- validate_config の YAML 検証は PyYAML がインストールされていない場合はスキップされるため、CI 環境等では PyYAML の存在を確認することを推奨。

### Future ideas / TODO（コード中のコメントより）
- position_sizing: 銘柄ごとの lot_size を stocks マスタから読み取る機能。
- apply_sector_cap: price 欠損時のフォールバック価格ロジック。
- factor_research: ファクター群の完全実装と Z スコア正規化の統合。
- ログおよび監視の通知ルール（LINE 連携）の強化と本番向けガードの追加。

---

Credits: この CHANGELOG は提供されたソースコードから構造・コメント・実装の挙動を解析して推測した変更履歴です。実際のコミット履歴・リリースノートと異なる場合があります。必要であれば、特定のモジュールごとに詳細な変更箇所（関数一覧や TODO まとめ）を作成します。