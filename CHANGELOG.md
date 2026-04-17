# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に従って記載しています。  
このファイルはリポジトリのコード内容から推測して作成した初期リリース向けの変更履歴です。

## [Unreleased]

（現時点のコードでは未リリースの変更はありません）

## [0.1.0] - 2026-04-17

初回公開リリース。システム全体のコア機能とユーティリティを実装しました。

### 追加 (Added)
- コアパッケージ構成
  - kabusys パッケージの基本セットを追加（__version__ = 0.1.0）。
  - エントリポイント・ツール・モジュールを多数実装。

- 設定管理
  - .env ファイルと環境変数を柔軟に読み込む Settings クラスを実装（src/kabusys/config.py）。  
    - 自動 .env ロード（プロジェクトルート検出: .git または pyproject.toml）。  
    - 読み込み優先度: OS環境変数 > .env.local > .env。  
    - 必須値チェック用の _require() 実装（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）。  
    - 各種設定プロパティ（DB パス、PID ファイル、しきい値、環境フラグ等）を提供。
  - 対話式環境設定ウィザードを追加（src/kabusys/config_setup.py）。  
    - .env の初期作成・更新を支援。シークレット表示はマスク、既存値の再利用が可能。

- 設定検証 CLI
  - 起動前チェックツールを追加（src/kabusys/validate_config.py）。  
    - 必須環境変数、KABUSYS_ENV、ログレベル、DBパスの親ディレクトリ、config/*.yaml 存在・パース（PyYAML が利用可能な場合）などを検証。  
    - --strict オプションをサポート（警告を失敗扱い）。

- 実行エンジン起動スクリプト
  - ExecutionEngine 起動ロジックを追加（src/kabusys/run_execution.py）。  
    - プロセス優先度を高に設定（utils/process_priority.set_process_priority）。  
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite を使用し、本番 DB と分離。  
    - BrokerClientFactory を使ったブローカー切替。OrderRepository / OrderManager / RiskManager / Reconciler の組立てと Engine 起動。  
    - 停止フラグ（data/stop_requested.flag）・実行 PID ファイル管理・デモンストレッドでの安全停止処理を実装。

- 監視（Monitoring）起動スクリプト
  - SystemMonitor ポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。  
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。  
    - 監視は環境にかかわらず本番 sqlite_path を使用し監視テーブルを初期化。停止フラグでループ終了。  
    - 例外時はログに出力して次のポーリングまで待機。

- ポートフォリオ構築関連（純関数群）
  - 銘柄選定・配分（src/kabusys/portfolio/portfolio_builder.py）:
    - select_candidates（スコア降順で候補選択）
    - calc_equal_weights（等金額配分）
    - calc_score_weights（スコア比率に基づく配分、全スコアが 0 の場合は等金額にフォールバック）
  - リスク調整（src/kabusys/portfolio/risk_adjustment.py）:
    - apply_sector_cap（セクター集中上限適用、当日売却予定銘柄を除外可能）
    - calc_regime_multiplier（市場レジームに基づく投下資金乗数）
  - ポジションサイズ計算（src/kabusys/portfolio/position_sizing.py）:
    - calc_position_sizes（risk_based / equal / score の allocation_method をサポート、単元株丸め、aggregate cap と cost_buffer を考慮）

- プロセス制御ユーティリティ
  - process_priority ユーティリティを追加（src/kabusys/utils/process_priority.py）。  
    - Windows / POSIX の差を吸収してプロセス優先度（high/normal/low）を設定。psutil を使用。  
    - CPU affinity 固定機能 set_cpu_affinity を提供。権限不足や未サポート環境では警告を出してスキップ。

- リサーチ / ファクター計算
  - factor_research モジュールを追加（src/kabusys/research/factor_research.py）。  
    - DuckDB 接続を受け取り prices_daily / raw_financials を参照して Momentum / Volatility 等の定量ファクターを計算する機能（calc_momentum, calc_volatility 等）。  
    - P95 等の集計や窓計算を SQL + Python で実装。

- Paper Trading 検証レポート
  - paper_verification_report スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。  
    - ペーパートレード DB（デフォルト data/paper_trading.db）から稼働率、注文成功率、送信率、レイテンシ（P95 など）を集計してレポート出力。  
    - 基準値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms）に基づく PASS/FAIL 判定を実装。

- DB 初期化ユーティリティ
  - 監視用 DB テーブル初期化関数 init_monitoring_db を参照して使用（monitoring モジュール側に実装される前提で起動時に呼び出し、冪等にテーブルを保証）。

- CLI エントリポイント
  - python -m kabusys.config_setup（環境ウィザード）
  - python -m kabusys.validate_config（設定検証）
  - python -m kabusys.tools.paper_verification_report（ペーパートレード検証レポート）

### 変更 (Changed)
- なし（初版リリース）

### 修正 (Fixed)
- .env パーサーの堅牢化（src/kabusys/config.py）:
  - export プレフィックス対応、クォート文字内でのエスケープ処理、コメントの扱いに細かなルールを導入し現実の .env フォーマットに対応。
  - .env 読み込み時に OS 環境変数を保護するロジック（protected set）を追加。

- ポジション計算の丸めとスケールダウンロジック（src/kabusys/portfolio/position_sizing.py）:
  - 単元株（lot_size）での丸め、aggregate cap 超過時のスケーリングと端数配分（残余キャッシュでの追加配分）を実装し、発注量の安定性と再現性を向上。

### 注意事項 / 既知の問題 (Known issues)
- process_priority/set_cpu_affinity は psutil の API と OS 権限に依存します。権限不足や未サポート OS では警告を出して処理をスキップします。
- apply_sector_cap 内の price が欠損（0.0）の場合、エクスポージャーが過少評価される可能性があり、将来的に前日終値等でのフォールバックを検討する旨を TODO コメントで記載しています。
- monitoring の挙動:
  - MONITOR_POLL_INTERVAL に不正値（0 以下や数値でない文字列）が与えられた場合、デフォルト 60 秒にフォールバックして警告をログ出力します。
  - 監視は環境設定にかかわらず settings.sqlite_path（本番監視 DB）を使用します。ペーパートレードと監視 DB を完全分離したい場合は構成の見直しが必要です。

### ドキュメント
- 各モジュールに使用法・設計意図を示す docstring コメントを追加。特にポートフォリオ構築・リスク調整・ポジションサイズ計算は外部ドキュメント（PortfolioConstruction.md 等）に基づく旨を記載。

---

今後のリリースでは、以下を予定しています（例）:
- モジュール間のユニットテスト追加と CI 設定
- monitoring/system_monitor の詳細実装とアラート送信（LINE 連携）
- BrokerClient の実装拡充と実取引安全性向上のためのガード強化
- config の型検証・schema ベースの config/*.yaml 検証追加

（この CHANGELOG はコードベースから推測して作成したものであり、実際の変更履歴と差異がある場合があります。）