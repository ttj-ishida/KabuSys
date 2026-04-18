# KabuSys

日本株向け自動売買システム（KabuSys） — 戦略計算、ポートフォリオ構築、発注実行、監視、研究ツール、AI ニューススコアリングを含むモジュール群のリポジトリ。

バージョン: 0.1.0

---
## 概要
KabuSys は以下の機能を備えたモジュール式の自動売買フレームワークです。

- データ処理・リサーチ（DuckDB ベースのファクター計算）
- ポートフォリオ構築（候補選定、重み付け、単元丸め）
- ポジションサイズ計算（リスクベース、等分配など）
- ExecutionEngine（kabuステーション等のブローカークライアントを通じた発注）
  - `KABUSYS_ENV=paper_trading` の場合は MockBroker を利用し DB を分離
- 監視（SystemMonitor / TradeMonitor / RiskMonitor）と Kill Switch（フラグファイル）
- AI モジュール（OpenAI を用いたニュースセンチメント評価 / レジーム判定）
- 運用ユーティリティ（.env ウィザード、設定検証、ペーパートレード検証レポート 等）

設計方針は「モジュール化」「本番データとペーパートレードの分離」「ルックアヘッドバイアス回避」「フェイルセーフ（API失敗時の安全動作）」などです。

---
## 機能一覧（主なもの）
- 設定管理
  - .env の自動読込 / 対話型ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
- 実行系
  - run_execution: ExecutionEngine を起動（本番／ペーパー切替）
  - ブローカー抽象化（BrokerClientFactory）
  - OrderManager / Reconciler / RiskManager を備えた実行パイプライン
- 監視系
  - run_monitoring: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で制御可）
  - MonitoringEngine: 各モニタの束ね、KillSwitch の評価、AlertManager への通知
  - MonitoringDB（SQLite）: system_status / trade_logs / positions / risk_logs / dashboard の永続化
- ポートフォリオ
  - 候補選定、等分配・スコア加重、リスク調整（セクターキャップ、レジーム乗数）、ポジションサイズ計算
- リサーチ
  - DuckDB 接続でのファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターン、IC 計算、統計サマリー
- AI
  - news_nlp: OpenAI でニュースをスコアリングして ai_scores に保存
  - regime_detector: ETF MA とマクロニュースを組み合わせたレジーム判定
- ツール
  - paper_verification_report: ペーパートレード DB を基に PASS/FAIL 判定付きレポート生成

---
## 必要条件（依存ライブラリ）
主な依存（抜粋）:
- Python 3.10+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（設定検証で config/*.yaml の内容をチェックする場合に推奨）
その他は setup に記載されている要件ファイル（存在する場合）を参照してください。

pip での一例:
```
pip install duckdb psutil openai pyyaml
```

---
## セットアップ手順（基本）
1. リポジトリをクローン／展開
2. Python 仮想環境を作成して依存をインストール
3. .env を作成
   - 対話式ウィザード（推奨）
     ```
     python -m kabusys.config_setup
     ```
   - 生成後、必須環境変数（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）を確認
4. 設定を検証
   ```
   python -m kabusys.validate_config
   # 警告もエラー扱いにする場合:
   python -m kabusys.validate_config --strict
   ```
5. ログディレクトリ作成（デフォルト: logs/。自動作成されますが権限等で失敗する場合あり）
6. 必要に応じて DuckDB / SQLite の DB ファイルパスや OPENAI_API_KEY を .env に設定

.env の主要項目（例）
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABU_API_BASE_URL=http://localhost:18080/kabusapi
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
PAPER_FILL_MODE=instant
KILL_FLAG_CLEAR_ON_START=0
```

注意:
- .env は決してバージョン管理にコミットしないでください。
- KABUSYS_ENV は `development` / `paper_trading` / `live` のいずれか。

---
## 使い方（起動・運用）
### ExecutionEngine（発注エンジン）起動
- 通常起動:
```
python -m kabusys.run_execution
```
- `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を用い、デフォルトで `data/paper_trading.db` に記録されます（本番 DB と完全に分離）。
- 起動前に kill flag (data/kill.flag) を手動で作成すると起動を抑止します。起動時に KILL_FLAG_CLEAR_ON_START=1 を設定していると自動でクリアされるため、本番では `0` を推奨します。
- 実行中、`data/stop_requested.flag` の作成で実行ループは終了します。`data/execution.pid` に PID が書き込まれます。

### Monitoring（監視）起動
- デフォルトのポーリング間隔は 60 秒。環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（例: 30 秒）。
```
MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
```
- 監視は MonitoringDB（SQLite）へ状態を記録します。監視モジュールは KABUSYS_ENV にかかわらず本番 sqlite_path（`SQLITE_PATH`）を使用します（監視ログは環境に関係なく同じ DB を使う設計）。
- 監視ループは `data/stop_requested.flag` によって停止できます。

### AI モジュール
- ニューススコアリング（news_nlp）・レジーム判定（regime_detector）は OpenAI API を使います。`OPENAI_API_KEY` を .env に設定するか、関数引数で渡してください。
- これらは直接関数を呼ぶ形で使うことを想定（例: スケジューラ / バッチジョブ経由）。

### ペーパートレード検証レポート
```
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# DBファイルを指定する場合:
python -m kabusys.tools.paper_verification_report --db /path/to/data/paper_trading.db
```
出力は期間内の稼働率、注文成功率、レイテンシ等のサマリと PASS/FAIL 判定を表示します。

---
## 運用上の注意
- ライブ本番環境（KABUSYS_ENV=live）では `KILL_FLAG_CLEAR_ON_START` を `0`（デフォルト）にしておくことを推奨します。validate_config でライブ環境用のガードチェックがあります。
- ログは `logs/<app_name>.log` に日次ローテーションで保存（30 日分保持）。ログディレクトリは `LOG_DIR` 環境変数や `setup_logging` の引数で変更できます。
- 監視（Monitoring）と実行（Execution）は DB の使用が競合しないように設計されていますが、バックアップ・保守は慎重に行ってください。
- AI 系（OpenAI）呼び出しはレート制限や一時的障害に対するリトライ実装がありますが、API キーや利用制限の管理は運用者が行ってください。
- `MONITOR_POLL_INTERVAL` は正の整数で指定してください。不正な値はデフォルト（60 秒）にフォールバックします。

---
## ディレクトリ構成（抜粋）
以下は主要なファイルとディレクトリの概観（リポジトリルートが `src/` 下にパッケージ化されている想定）。

- src/kabusys/
  - __init__.py  — パッケージ定義（バージョン）
  - config.py  — 環境変数 / Settings クラス、.env 自動ロードロジック
  - config_setup.py  — 対話式 .env ウィザード（python -m kabusys.config_setup）
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - utils/
    - logging_setup.py — 一貫したログ設定ユーティリティ
    - process_priority.py — プロセス優先度・CPU アフィニティ設定ユーティリティ
  - monitoring/
    - monitoring_db.py — SQLite persist 層（init + MonitoringDB クラス）
    - system_monitor.py — システム状態 & データ鮮度監視
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - monitoring_engine.py — 各モニタの束ね & アラート判定
    - kill_switch.py — フラグによる停止シグナル管理
    - ...（TradeMonitor, AlertManager 等）
  - execution/
    - execution_engine.py — ExecutionEngine 本体
    - broker_factory.py — BrokerClient の生成ファクトリ（実ブローカ/Mock 切替）
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py 等
  - portfolio/
    - portfolio_builder.py — 候補選定 / 重み付け
    - position_sizing.py — 発注株数計算
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — モメンタム/ボラ/バリュー等
    - feature_exploration.py — forward returns / IC / summary
  - ai/
    - news_nlp.py — ニュースセンチメントスコアリング（OpenAI）
    - regime_detector.py — 市場レジーム判定（ETF MA + マクロニュース）
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成

その他:
- data/ — デフォルトで使われる DB・フラグファイル（例: data/monitoring.db, data/paper_trading.db, data/kill.flag, data/stop_requested.flag, data/execution.pid）
- logs/ — ログファイル（logs/execution.log, logs/monitoring.log など）

---
## 開発 / テストのヒント
- .env の自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で抑止できます（ユニットテスト等で便利）。
- DuckDB や SQLite のスキーマはコード内で初期化・マイグレーション処理が行われます（例: init_monitoring_db）。
- AI 呼び出し部は内部で API 呼び出しラッパーを使っており、テストでは該当関数をモックして外部依存を排除できます（コード内にモック用の注記あり）。

---
## 参考コマンドまとめ
- .env ウィザード
  ```
  python -m kabusys.config_setup
  ```
- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```
- 実行エンジン起動
  ```
  python -m kabusys.run_execution
  ```
- 監視起動（ポーリング間隔 60 秒デフォルト）
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
- ペーパートレード検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

--- 
もし README に追加したい内容（例: docker 構成、systemd ユニット例、より詳細な運用手順、API の仕様書など）があれば教えてください。必要に応じてサンプル systemd ユニットや docker-compose 設定も作成します。