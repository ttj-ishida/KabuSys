# KabuSys

日本株向けの自動売買システム（ライブラリおよび実行スクリプト群）

このリポジトリは、発注エンジン、監視（Monitoring）、ファクター/リサーチ、ポートフォリオ構築、AI（ニュースセンチメント・レジーム判定）といった機能を備えた自動売買基盤の一部実装を含みます。  
（本 README は src/kabusys 以下のコードベースに基づいて作成しています）

---

## 概要

KabuSys は以下を目的としたモジュール群を提供します。

- 実際の発注ロジックを含む ExecutionEngine（本番 / ペーパートレード両対応）
- システム安定性、注文滞留、ドローダウンなどを監視する Monitoring コンポーネント
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ決定）
- リサーチ用ファクター計算（モメンタム・ボラティリティ・バリュー等）
- ニュースを用いた NLP スコアリング（OpenAI API を利用）
- 設定ウィザード / 検証 / 解析用ツール類

設計方針として、DB（DuckDB / SQLite）を用いたデータ永続化、外部 API 呼び出しは明示的に分離、ルックアヘッドバイアス防止（日時参照の扱い）などが取り入れられています。

---

## 主な機能一覧

- Execution
  - ExecutionEngine（本番 / paper_trading 切替）
  - BrokerClientFactory によるブローカークライアント生成（paper_trading 時は Mock を利用）
  - OrderRepository / OrderManager / RiskManager / Reconciler 等で発注管理と整合性チェック
- Monitoring
  - SystemMonitor：CPU/メモリ/ディスク/プロセス状態・データ鮮度監視
  - TradeMonitor：滞留注文・約定異常チェック
  - RiskMonitor：ドローダウン・ポジション上限監視（kill flag の発動）
  - MonitoringEngine：上記 Monitor を定期実行しアラート / Kill Switch を評価
  - SQLite ベースの監視 DB 層（monitoring_db）
- Portfolio
  - 候補選定（スコアソート）、等ウエイト・スコア重み付け
  - セクター上限適用、レジーム乗数、ポジションサイズ計算（単元丸め・コストバッファ等）
- Research
  - DuckDB を使ったファクター計算（momentum/value/volatility）
  - 将来リターン、IC（Information Coefficient）、統計サマリー
- AI
  - news_nlp：ニュース記事を集約して OpenAI（gpt-4o-mini）でセンチメントを算出し ai_scores に格納
  - regime_detector：ETF MA とマクロニュースから市場レジームを判定・保存
- ツール / スクリプト
  - 設定ウィザード：python -m kabusys.config_setup
  - 設定検証：python -m kabusys.validate_config [--strict]
  - Paper Trading 検証レポート生成：python -m kabusys.tools.paper_verification_report

---

## 前提 / 必要環境

- Python 3.9+
- 必須パッケージ（使用する機能に応じて）
  - duckdb
  - psutil
  - openai (AI 機能利用時)
  - PyYAML（validate_config が config/*.yaml の中身を検証する場合に必要）
- SQLite（Python 標準ライブラリに含まれるため追加不要）
- ネットワーク接続（本番ブローカー / OpenAI API 利用時）

インストール例（仮）:
```
pip install duckdb psutil openai pyyaml
```
※ 実際のパッケージ管理は pyproject.toml / requirements.txt に依存します（本リポジトリに合わせて調整してください）。

---

## セットアップ手順

1. リポジトリをクローン / 展開

2. 必要パッケージをインストール
   - 例: pip install -r requirements.txt（requirements.txt がある場合）
   - または個別に: pip install duckdb psutil openai pyyaml

3. .env の作成
   - 対話式ウィザード:
     ```
     python -m kabusys.config_setup
     ```
     ウィザードは .env を生成します（※ .env は Git にコミットしないでください）。

   - 最低限必要な環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - OPENAI_API_KEY（AI 機能利用時）
     - KABUSYS_ENV（development / paper_trading / live）
     - 必要に応じて DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH を設定

4. 設定の検証（任意）
   ```
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict  # 警告も失敗扱い
   ```

5. データディレクトリ（例: data/）の作成（必要に応じて）
   - デフォルト DB パス:
     - DuckDB: data/kabusys.duckdb
     - Monitoring SQLite: data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db

---

## 使い方（起動 / 実行）

基本的なエントリポイントはモジュールとして実行する形です。

- 実行エンジン（ExecutionEngine）を起動:
  - 開発 / 本番切替は KABUSYS_ENV 環境変数で制御
  - ペーパートレード時は MockBrokerClient を使い、DB は data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で変更可）
  ```
  python -m kabusys.run_execution
  ```

  - 起動時に data/stop_requested.flag（プロジェクトルートの data ディレクトリ内）を検知している場合は起動せず終了します。
  - エンジンは data/execution.pid に PID を書きます（停止時は削除）。

- 監視ループ（Monitoring）を起動:
  ```
  python -m kabusys.run_monitoring
  ```
  - 動作: SystemMonitor を定期的に呼び出して監視ログを SQLite に保存します。
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）。
  - 監視は Settings に関わらず本番 SQLite（SQLITE_PATH）を使用します（監視用は本番 DB に接続）。
  - 停止は data/stop_requested.flag を作成することで行います。

- Paper Trading 検証レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - --db で SQLite パスを指定するか、PAPER_TRADING_SQLITE_PATH 環境変数を設定します。

- AI 機能（ニューススコア / レジーム判定）
  - OpenAI API キーが必要（環境変数 OPENAI_API_KEY または API 呼び出し時に引数指定）
  - モジュール関数:
    - kabusys.ai.score_news(conn, target_date, api_key=None)
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続を受け取り、結果をテーブルに書き込みます。

- 設定の自動ロード
  - config.py はプロジェクトルート（.git または pyproject.toml）を基に .env/.env.local を自動ロードします。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます。

---

## 主要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading: MockBrokerClient を使用し、発注はペーパートレード DB に記録される
  - live: 本番モード（注意して扱う）
- OPENAI_API_KEY: OpenAI を使う機能の API キー
- DUCKDB_PATH（デフォルト data/kabusys.duckdb）
- SQLITE_PATH（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 専用 DB、デフォルト data/paper_trading.db）
- MONITOR_POLL_INTERVAL（秒、監視ループのポーリング間隔。デフォルト 60）

---

## ディレクトリ構成（src/kabusys の主なファイル・モジュール）

- kabusys/
  - __init__.py
  - config.py — 環境変数 / .env 自動ロード / Settings クラス
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前チェック CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングスクリプト
  - utils/
    - process_priority.py — プロセス優先度・CPU affinity 設定ユーティリティ
  - execution/（発注関連: Engine, OrderManager, Repository 等）
  - monitoring/
    - monitoring_db.py — SQLite ベースの永続化層・API
    - system_monitor.py — システム / データ鮮度監視
    - trade_monitor.py — 注文滞留・約定異常監視
    - risk_monitor.py — ドローダウン等の監視
    - kill_switch.py — kill.flag 操作
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - alert_manager.py — 通知管理（LINE など。実装が別途必要）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - risk_adjustment.py — セクター上限・レジーム乗数
    - position_sizing.py — 発注株数計算（単元丸め・aggregate cap）
  - research/
    - factor_research.py — momentum/value/volatility 等
    - feature_exploration.py — 将来リターン・IC・統計
  - ai/
    - news_nlp.py — ニュースを LLM でスコアリングし ai_scores に書き込む
    - regime_detector.py — ETF MA + マクロニュースでレジーム判定
  - monitoring/（上記に含む）
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成

---

## 注意事項 / トラブルシューティング

- 必須環境変数が未設定だと validate_config でエラーになります。まずは config_setup で .env を作成し、validate_config で確認してください。
- paper_trading モード:
  - 実際の注文は行われません。MockBrokerClient が利用され、データは指定の paper DB に記録されます（SQLITE_PATH とは分離）。
- 監視（run_monitoring）は Settings に関わらず SQLITE_PATH を使用します（監視ログの保存先）。MONITOR_POLL_INTERVAL でポーリング間隔を上書きできます。
- OpenAI API を使う機能は API 利用料金・レートリミットに注意してください。失敗時は一部機能がフェイルセーフでデフォルト値（0 やスキップ）にフォールバックする実装が多くありますが、API キーは必須です。
- psutil によるプロセス優先度や cpu_affinity の設定は権限や OS に依存します。失敗すると警告が出て処理は継続します。
- DuckDB / SQLite のファイルパスの親ディレクトリが存在しない場合、validate_config は警告を出します。起動時に自動作成されるケースもありますが事前に data/ 等を作成しておくと安全です。

---

## よくある操作例

- .env 作成（ウィザード）:
  ```
  python -m kabusys.config_setup
  ```

- 設定チェック:
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 実行エンジン起動:
  ```
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  ```

- 監視ループ起動（ポーリング間隔 30 秒に変更）:
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

- Paper Trading レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

この README はコードベースの主要点をまとめたものです。実運用や拡張時は各モジュールの docstring・実装を参照し、環境（APIキー/ブローカー設定/DBバックアップ等）を適切に管理してください。必要であれば、各コンポーネント（ExecutionEngine、BrokerClient 等）の使い方や設定例も追記できます。