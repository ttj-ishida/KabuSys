CHANGELOG
=========

すべての変更は Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に準拠して記載しています。

[0.1.0] - 2026-04-17
-------------------

初期公開リリース。システム全体の起動スクリプト、設定管理、バリデーション、ポートフォリオ構築、ポジションサイジング、リスク調整、プロセスユーティリティ、リサーチ（ファクター計算）、および検証ツール群を含みます。

Added
- 基本 CLI / 起動スクリプト
  - run_execution: ExecutionEngine を起動するエントリポイント。KABUSYS_ENV=paper_trading の場合は専用の paper_trading DB を使用し、MockBrokerClient を利用する分離が組み込まれている。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグファイルを監視して安全に終了する。
- 設定管理とウィザード
  - kabusys.config.Settings: 環境変数から各種設定を取得する集中管理クラス（DB パス、KABUSYS_ENV、ログレベル、閾値等）。
  - kabusys.config_setup: 対話式 .env 作成・更新ウィザード（秘密値マスク、デフォルト表示、ファイル書き出し）。
  - kabusys.validate_config: 起動前の設定検証 CLI（必須環境変数、KABUSYS_ENV、パスの存在チェック、config/*.yaml の存在・パースチェック、live 環境特有のガード等）。
- .env の自動読み込み / パーサ
  - プロジェクトルート（.git または pyproject.toml を基準）から .env/.env.local を自動読み込み（OS 環境変数を上書き保護）。
  - .env パーサは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメントの取り扱いなどに対応。
- データベース初期化・監視
  - 監視用テーブルを保証する init_monitoring_db 呼び出し（冪等）。
  - DuckDB 接続を利用した分析向けパスをサポート（Settings.duckdb_path）。
- Execution / Risk / Order 管理周り（起動時の組み立て）
  - BrokerClientFactory によるブローカークライアント生成を組み込み。
  - OrderRepository / OrderManager / Reconciler / RiskManager / ExecutionEngine を組み合わせてエンジンを起動。
  - RiskManager にデフォルト構成を提供（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。初期ポートフォリオ値に broker.get_available_cash() を使用。
- ポートフォリオ構築（純粋関数）
  - portfolio_builder: select_candidates（スコア順選定）、calc_equal_weights、calc_score_weights（スコア合計 0 の場合に等分にフォールバック）。
  - risk_adjustment: apply_sector_cap（セクター集中制限の適用／除外）、calc_regime_multiplier（市場レジームに対する乗数）。
  - position_sizing: calc_position_sizes（risk_based / equal / score 向けの株数決定、単元株丸め、per-stock 上限、aggregate cap のスケーリングと残余配分ロジック）。
- リサーチ / ファクター計算
  - research.factor_research: DuckDB を用いたモメンタム / ボラティリティ等のファクター計算（calc_momentum, calc_volatility）。
- ユーティリティ
  - utils.process_priority: クロスプラットフォーム（Windows / POSIX）でプロセス優先度や CPU affinity を設定するユーティリティ（権限不足や未対応 OS の場合は警告を出して安全にスキップ）。
- 検証ツール
  - tools.paper_verification_report: ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH）から稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）を集計して PASS/FAIL 判定付きのレポートを標準出力に生成。

Changed
- ログ・運用面の配慮
  - run_execution/run_monitoring の起動時にプロセス優先度を "high" に設定する呼び出しを追加（set_process_priority）。
  - run_monitoring のポーリングループで check_once() 実行中に例外が発生してもループを継続するように例外をキャッチしてログ出力（監視の継続性向上）。
  - run_execution は停止フラグ検知時に安全に Engine.stop() を呼び出してシャットダウンを試みる。
- .env のロード順序と保護
  - OS 環境変数は上書きされないよう保護しつつ .env.local を .env より優先して読み込む実装に変更。
- Settings の検証強化
  - KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE などの値チェックを実装して不正値時は ValueError を送出。

Fixed
- 安全処理・エラーハンドリング
  - MONITOR_POLL_INTERVAL のパースで 0 以下や無効文字列が指定された場合にデフォルトへフォールバックするように修正（time.sleep に不正値を渡さない）。
  - .env ファイル読み込み時にファイル読み取り失敗で警告を出すように変更（例外でプロセスを止めない）。
  - DB 接続のクローズ処理を try/finally で保証（run_execution/run_monitoring）。
  - paper_verification_report: データ欠損時（テーブルが存在しない等）に OperationalError を捕えてデフォルト値にフォールバックするように変更。

Documentation / UX
- config_setup により .env の初期作成手順を対話式で整備、書き出し内容に注意書き（Git にコミットしない等）を追加。
- validate_config に --strict オプションを追加（警告を FAIL として扱う）。

Security
- シークレット（J-Quants トークン、kabu API パスワード、LINE トークン等）は config_setup の表示でマスク表示を行う等の配慮を追加（出力上の取り扱い）。

Removed
- なし

Deprecated
- なし

Notes / その他
- 監視（monitoring）は「環境にかかわらず本番 sqlite_path を使用する」設計になっています（run_monitoring の挙動）。
- run_execution は paper_trading 環境時にデータベースを分離しているため、本番データとペーパー用データは完全に分離できます。
- 本リリースは初期実装のため、将来的に以下の改善が想定されています: 銘柄別 lot_size の拡張、価格フェイルオーバー（前日終値など）の導入、より詳細なログ・メトリクスの出力。

既知の制限
- position_sizing の price 欠損時（price=0.0）はスキップする実装であるため、価格データが欠落している銘柄は見落とされる可能性があります（TODO コメントあり）。
- calc_regime_multiplier は未知レジームで 1.0 にフォールバックする実装。将来的なレジーム定義の拡張が必要な場合あり。

Authors / Contributors
- 初期実装（内部モジュールの集合）。詳細なコミッター情報はリポジトリのコミット履歴を参照してください。

---
この CHANGELOG はコードベースの内容から推測して作成しています。実際のコミットメッセージや問題トラッカーに基づく正式な履歴はリポジトリの履歴を参照してください。