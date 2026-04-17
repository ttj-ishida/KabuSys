# CHANGELOG

すべての notable な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠しています。  
日付はコードベースから推測して付与しています。実際のリリース日付は適宜差し替えてください。

全般的な注意
- 本リポジトリは日本株自動売買システム「KabuSys」の初期リリース相当の内容を含みます。
- 環境変数による設定が多く、デフォルト値や挙動は Settings クラスおよび各 CLI/スクリプトのドキュメント文字列に従います。
- データベースは SQLite と DuckDB を組み合わせて使用します。paper_trading 環境では SQLite が本番 DB と切り分けられます。

[0.1.0] - 2026-04-17
====================

Added
-----
- 基本構成・エントリポイント
  - パッケージ初期化 (kabusys.__init__.py) にバージョン `0.1.0` を追加。
- 設定管理
  - kabusys.config
    - .env 自動読込機能を提供（プロジェクトルートの .env および .env.local を読み込む。OS 環境変数は優先）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読込を無効化可能。
    - 複雑な .env パースロジックを実装（export 前置、クォート内のバックスラッシュエスケープ、インラインコメント処理等）。
    - Settings クラスを提供し、環境変数アクセスをラップ（J-Quants / kabuステーション / DB パス / 監視しきい値 等）。
    - paper_trading 用の PAPER_TRADING_SQLITE_PATH / PAPER_FILL_MODE 等の設定をサポート。
- 環境設定ウィザード CLI
  - kabusys.config_setup: 対話式ウィザードで .env を生成 / 更新するツールを追加。
    - デフォルト値・選択肢・シークレット入力対応。
    - .env 書き込み時に注意文を付与（.env を Git にコミットしない旨）。
- 設定検証 CLI
  - kabusys.validate_config: .env や config/*.yaml の存在・形式チェック、必須環境変数チェックを行うツールを追加。
    - --strict オプションで警告を FAIL 扱い（exit(1)）にできる。
    - PyYAML 未インストール時は YAML 検証をスキップして警告を出す。
    - 本番（KABUSYS_ENV=live）向けの追加ガード（LINE 通知設定やキルフラグ設定の確認）。
- 実行 / 監視スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプト。起動時にプロセス優先度を high に設定。
    - paper_trading 環境では MockBrokerClient を使用し、専用の SQLite（デフォルト: data/paper_trading.db）へ記録して本番と分離。
    - stop フラグファイル (data/stop_requested.flag) による安全停止、実行中 PID ファイル管理。
    - ExecutionEngine の依存コンポーネント（BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler）を組み立ててスレッドで実行。
    - RiskManager にデフォルトの RiskConfig を設定（max_position_pct=0.20 等、初期資金は broker.get_available_cash() を使用）。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。プロセス優先度を high に設定。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバックして警告を出す。
    - 監視 DB は環境にかかわらず production 相当の sqlite_path を使用する（monitoring は分離しない設計）。
    - stop フラグファイルによりループを終了。
- ユーティリティ
  - kabusys.utils.process_priority
    - Windows / POSIX の差を吸収してプロセス優先度設定（high/normal/low）を行うユーティリティを追加。
    - CPU affinity を設定する set_cpu_affinity(api) を提供。
    - psutil による権限失敗を安全に無視してログで通知する実装。
- ポートフォリオ構築（純粋関数群）
  - kabusys.portfolio.portfolio_builder
    - select_candidates: BUY シグナルをスコア降順にソートして上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等金額配分およびスコア加重配分（スコア全て 0 の場合は等配分にフォールバック）。
  - kabusys.portfolio.risk_adjustment
    - apply_sector_cap: セクター集中を制限し、上限超過セクターの候補を除外（unknown セクターは除外対象外）。
    - calc_regime_multiplier: market regime に基づく投下資金乗数（bull/neutral/bear マッピング）。未知のレジームは 1.0 にフォールバックして警告。
  - kabusys.portfolio.position_sizing
    - calc_position_sizes: allocation_method に応じて発注株数を計算（risk_based / equal / score）。
    - 単元株単位（lot_size）で丸め、ポートフォリオ aggregate cap を満たすようスケールダウンと残余分配を行うアルゴリズムを実装。
    - cost_buffer による手数料・スリッページの保守的見積りをサポート。
- リサーチ / ファクター計算
  - kabusys.research.factor_research
    - DuckDB 接続を使って Momentum / Volatility 等のファクター計算関数（calc_momentum, calc_volatility 等）を実装（prices_daily テーブル参照）。
    - 長期移動平均や ATR などを計算するための SQL + window 関数を活用。データ不足時は None を返す仕様。
- Paper Trading 検証ツール
  - kabusys.tools.paper_verification_report
    - Paper Trading の検証レポート生成スクリプトを追加。
    - 各種閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200 ms）に基づき PASS/FAIL を判定。
    - 日付フィルタ（--from / --to）および DB パス指定（--db / 環境変数）をサポート。
    - P95 計算や N/A 表示（データなし）に対応。
- その他
  - monitoring_db 初期化呼び出しを各スクリプトが起動時に行い、監視テーブルの存在を保証（冪等）。
  - 各所にログ出力・例外ハンドリングを追加。

Changed
-------
- 初期リリースのため「変更」は特にありません（ベースラインを確立）。

Fixed
-----
- 初期リリースのため「修正」は特にありません。ただし各機能でエラー時にログ出力して安全に継続/終了する設計が組み込まれています（例: monitor.check_once() の例外捕捉、psutil の権限エラーの警告スキップなど）。

Deprecated
----------
- なし

Removed
-------
- なし

Security
--------
- 環境変数内のシークレットは .env ウィザードでマスク表示される（出力時は **** 表示）。
- .env は絶対に Git にコミットしない旨を .env 生成ロジックのヘッダに明記。

補足（実装上の注意点・既知の挙動）
- .env パーサはクォート内のバックスラッシュエスケープを解釈しますが、完全な shell 互換解析器ではありません。極端なケースは想定外となる可能性があります。
- apply_sector_cap の価格フォールバックは未実装（price が 0 の場合、エクスポージャーが過少評価される可能性あり）。将来的に前日終値等のフォールバックを検討する旨の TODO コメントあり。
- calc_position_sizes の lot_size は現状 global（全銘柄共通）で、将来的に銘柄別 lot_map を受け取る拡張が検討されています。
- run_monitoring / run_execution は stop フラグファイル (data/stop_requested.flag) を使ったシグナル方式を採用しており、デプロイ時はファイル配置と権限に注意してください。
- Settings._require は必須環境変数がない場合に ValueError を送出するため、実運用では起動前に validate_config を実行して不備を検出することを推奨します。

今後の予定（参考）
- 異常系でのより詳細なメトリクス収集・アラート機能の強化
- 銘柄別 lot_size 対応、価格フォールバックの改良
- DuckDB を使ったファクターパイプラインのさらなる最適化
- ユニットテスト、CI、デプロイ用のスクリプト整備

---
この CHANGELOG はコードベースの内容から推測して作成しています。実際のリリースノートでは日付や細部を実運用の記録に合わせて調整してください。