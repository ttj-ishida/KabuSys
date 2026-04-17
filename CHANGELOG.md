# Changelog

すべての notable な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

## [0.1.0] - 2026-04-17

### 追加
- 基本パッケージ初期リリース（機能群をまとめて追加）。
- 環境・設定関連
  - Settings クラス（kabusys.config）を導入。環境変数から各種設定（DB パス、API トークン、監視閾値、実行環境など）を取得する単一インターフェースを提供。
  - 自動 .env 読み込み機能を実装（プロジェクトルートの .env / .env.local を OS 環境変数を保護しつつ読み込む）。自動読み込みを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - config_setup CLI（kabusys.config_setup）を追加。対話式ウィザードで .env を初期作成・更新できる。
  - validate_config CLI（kabusys.validate_config）を追加。起動前に環境変数や config/*.yaml の整合性チェックを行い、--strict で警告を失敗扱いにできる。
- 実行系 / 監視
  - run_execution スクリプト（kabusys.run_execution）を追加。ExecutionEngine を起動するランチャー。以下の動作を実装：
    - 起動時にプロセス優先度を "high" に設定（utils.process_priority）。
    - KABUSYS_ENV に応じて paper_trading 用 DB を分離（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）。
    - BrokerClientFactory により適切なブローカークライアントを生成（paper_trading では Mock を利用）。
    - OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine の組み立てとセッションスレッド起動。停止フラグ（data/stop_requested.flag）で安全停止処理を行う。PID ファイル書き出し。
  - run_monitoring スクリプト（kabusys.run_monitoring）を追加。SystemMonitor のポーリングループ起動用ランチャー。特徴：
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用 sqlite_path を使用する（監視 DB の分離は行わない設計）。
    - 停止フラグ検知でループを終了。check_once() 呼び出しで例外発生時はログを残して次回ポーリングへフォールバック。
- ポートフォリオ構築（純粋関数群）
  - portfolio_builder.py
    - select_candidates: BUY シグナルの上位選定（スコア降順、タイブレークに signal_rank）。
    - calc_equal_weights, calc_score_weights: 等金額配分・スコア加重配分の計算（スコアが全て 0 の場合は等分配にフォールバック）。
  - risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェックにより候補をフィルタ。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear → 1.0/0.7/0.3、未知レジームはフォールバック）。
    - TODO コメント: price が欠損（0.0）の場合のハンドリング改善の余地を明記。
  - position_sizing.py
    - calc_position_sizes: 等分配・スコア加重・リスクベースの株数決定ロジック。単元株（lot_size）丸め、aggregate cap によるスケールダウン、残余配分ロジックを実装。
    - cost_buffer（手数料・スリッページ係数）を加味した保守的見積り。
    - 将来的な拡張点（銘柄別 lot_size の対応）をコメントで記載。
  - portfolio パッケージ __init__ を通じて上記主要関数をエクスポート。
- 研究用ファクター計算
  - research/factor_research.py を追加。DuckDB 接続を受け取り以下を計算：
    - Momentum（1M/3M/6M リターン、MA200 乖離）
    - Volatility（20 日 ATR、ATR 比、20 日平均売買代金、出来高比）
    - 実装は SQL（DuckDB）中心で、足りないデータがある場合は None を返す設計。
- ユーティリティ
  - utils/process_priority.py を追加。プラットフォーム差（Windows / POSIX）を吸収してプロセス優先度設定（set_process_priority）と CPU affinity 固定（set_cpu_affinity）を提供。例外時は警告を出してスキップする安全設計。
- ツール
  - tools/paper_verification_report.py を追加。Paper Trading の検証レポートを SQLite（data/paper_trading.db 等）から生成。出力指標とデフォルトの閾値：
    - 稼働率（Uptime）閾値 99.0%
    - 注文成功率（Fill Rate）閾値 90.0%
    - 送信率（Send Rate）閾値 95.0%
    - P95 レイテンシ閾値 200 ms
  - レポートは期間指定 (--from/--to) をサポートし、データ不足に対する安全フォールバックを備える。

### 変更
- パッケージ初期化
  - kabusys.__init__ にバージョンを追加（__version__ = "0.1.0"）および主要サブパッケージを __all__ で公開。

### 修正（設計上の注意・安全設計）
- DB 接続周り
  - run_monitoring と run_execution でそれぞれ sqlite3 / duckdb の接続を確立し、最終的に必ず close() するように実装（finally ブロックでのクローズ保証）。
- 設定検証
  - validate_config は PyYAML 未インストール時に YAML 検証をスキップし、警告を出すように変更（柔軟な導入を配慮）。
- 環境変数パーサ
  - .env のパース実装でクォート／エスケープ／インラインコメント処理を考慮（export プレフィックスにも対応）。protected 引数により OS 環境変数の上書きを防止。

### 既知の制限（今後の改善候補）
- risk_adjustment.apply_sector_cap:
  - price が欠損（0.0）の場合、エクスポージャーが過少見積もられブロックが外れる可能性がある。前日終値や取得原価をフォールバックとして使う改善を検討。
- position_sizing.calc_position_sizes:
  - 現在 lot_size はグローバル固定（関数引数で指定可だが銘柄別対応は未実装）。将来的に銘柄マスタに lot_size を持たせる設計を想定。
- process_priority / cpu_affinity:
  - 一部 OS では権限不足や未実装 API により設定不能なケースがある。失敗時は警告ログを出力して処理を継続する。
- run_monitoring:
  - ドキュメント上の挙動どおり監視は環境に依存せず本番 sqlite_path を使用するため、テスト実行時の DB 分離を行いたい場合は注意が必要。

### セキュリティ
- .env は .git にコミットしないことを README / config_setup のヘッダで明記。

---

今後のリリースでは、下記のような点を改善予定です：
- price フォールバックロジックの追加（前日終値等）によるセクター露出計算の堅牢化
- 銘柄別 lot_size の導入
- ExecutionEngine や Monitor のより詳細なテストカバレッジ追加
- リモート監視 / アラート（LINE 通知等）の統合テスト強化

（以上）