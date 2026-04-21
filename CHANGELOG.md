CHANGELOG
=========

すべての変更は Keep a Changelog 構成に従って記載しています。  
日付はコードベースから推測したリリース日を使用しています。

フォーマット:
https://keepachangelog.com/ja/1.0.0/

Unreleased
----------
- なし（現時点のコードベースは初期リリース相当の内容を含みます）

[0.1.0] - 2026-04-21
-------------------

Added
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` に設定。
- 起動スクリプト / 実行系
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使用し、本番 DB と分離した `data/paper_trading.db` を利用する。
    - PID ファイル管理、停止フラグ (data/stop_requested.flag)、スレッドでのエンジン実行と安全なシャットダウン処理を実装。
    - ExecutionEngine 周辺の組み立て: BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler、Reconciler 連携。
    - RiskManager のデフォルト設定（max_position_pct 等）を実装。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番の sqlite_path を使用して監視データを記録。
    - 停止フラグ検出および例外発生時のロギングと継続処理を実装。
- 設定管理 / ユーティリティ
  - config.py: 環境変数・設定管理モジュールを追加。
    - プロジェクトルート自動探索（.git または pyproject.toml を基準）に基づく .env の自動ロード (オプトアウト可能)。
    - .env のパース機能（export プレフィックス対応、クォート文字・エスケープ、インラインコメント処理など）。
    - 各種設定プロパティ（DB パス、KABUSYS_ENV、ログレベル、paper_trading 用設定等）。
  - config_setup.py: 対話式 .env 作成ウィザードを追加。
    - 各設定項目の説明・デフォルト・シークレットマスク表示、保存機能を提供。
  - validate_config.py: 設定検証 CLI を追加。
    - 必須環境変数の存在チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスや config/*.yaml の存在・パースチェック（PyYAML がない場合は警告）。
    - --strict オプションで警告を失敗扱いにする機能。
- 監視 DB 初期化
  - monitoring.monitoring_db.init_monitoring_db を呼び出して監視用テーブルが存在することを保証（冪等）。
- ポートフォリオ構築ロジック（純粋関数群）
  - portfolio.portfolio_builder:
    - select_candidates: スコア降順で候補抽出（タイブレークに signal_rank）。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分（スコア合計が 0 の場合は等金額にフォールバック）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中上限チェック（売却予定銘柄を除外する考慮あり）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear 他）。
  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく株数算出。単元株丸め、max_position, max_utilization, cost_buffer を考慮した aggregate cap とスケールダウン・端数配分ロジックを実装。
- ログ / プロセス制御ユーティリティ
  - utils.logging_setup.setup_logging: stdout ストリーム + 日次ローテートファイルハンドラをルートロガーに設定。ログディレクトリ作成失敗時はファイル出力をスキップして継続。
  - utils.process_priority:
    - set_process_priority: Windows/Linux(Mac 等) を吸収したプロセス優先度設定（psutil ベース）。失敗時は警告を出して安全にフォールバック。
    - set_cpu_affinity: 指定コア数での CPU affinity 設定（失敗時は警告）。
- 分析・検証ツール
  - tools/paper_verification_report.py: Paper Trading 結果の検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率、送信率、リスク却下数、API レイテンシ (平均/最大/P95) を集計して PASS/FAIL 判定。
    - CLI 引数 --from/--to/--db と環境変数 PAPER_TRADING_SQLITE_PATH をサポート。
- Research
  - research.factor_research: ファクター計算基盤を追加（モメンタム等の定数・設計方針・calc_momentum の骨組みを含む）。DuckDB 接続を受け取り prices_daily / raw_financials を参照してファクターを算出する設計。

Changed
- なし（初期実装のため該当なし、ただし内部設計には将来的な拡張ポイントを注記）。

Fixed
- 初期リリースでの堅牢性強化
  - 各種ファイル IO / DB 接続 / psutil 呼び出しで例外を捕捉し、ログ出力のうえ処理継続または安全終了する実装により運用上の堅牢性を確保。
  - .env 読み込みに失敗した場合は警告を出してスキップ（テストや配布後の動作を想定）。

Deprecated
- なし

Removed
- なし

Security
- なし（ただしシークレット値は対話式ウィザード・.env においてマスクして表示する等の配慮あり）

Notes / 注意事項
- .env の自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をセットすることで無効化可能（テスト用途）。
- run_monitoring は監視用 DB として Settings.sqlite_path を常に使用する設計で、本番/ペーパーの混同を避けるための意図的な選択がある。
- Paper Trading 関連は本番 DB と分離される（PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）。
- 一部モジュール（例: research.factor_research）は計算ロジックの骨組みを含み、実運用前に追加のテスト・検証が推奨される。

作者注
- CHANGELOG はコード構成と docstring・コメントから推測して作成しました。実際のリリースノートは運用ポリシーやリリース日付、追加の変更履歴にあわせて調整してください。