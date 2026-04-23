# KabuSys

日本株自動売買システム (KabuSys) の README（日本語）。

このリポジトリは、シグナル生成・ポートフォリオ構築・注文実行・監視・解析ツール群を含む自動売買フレームワークです。主要コンポーネントは ExecutionEngine（発注実行）、Monitoring（運用監視）、Research/Portfolio（因子計算・ポートフォリオ構築）、AI（ニュース NLP / レジーム判定）、およびユーティリティ群です。

## 目次
- プロジェクト概要
- 機能一覧
- 必要要件
- セットアップ手順
- 環境変数（主な設定項目）
- 使い方（コマンド/スクリプト）
- 停止・Kill Switch の取り扱い
- ディレクトリ構成（主要ファイルの説明）
- 補足・運用上の注意

---

## プロジェクト概要
KabuSys は日本株向けの自動売買プラットフォームです。戦略部分（因子算出・シグナル生成）やポートフォリオ構築は研究/純粋関数的に実装され、ExecutionEngine がブローカークライアント経由で発注を行います。運用時の監視（リソース、プロセス有無、注文状態、ドローダウン監視）や、AI を使ったニュースセンチメント評価・レジーム判定などの補助機能を備えます。

---

## 機能一覧
- ExecutionEngine（発注エンジン）
  - paper_trading（ペーパートレード）用に MockBrokerClient をサポート
  - 本番とペーパーで SQLite DB を分離（PAPER_TRADING_SQLITE_PATH）
- Monitoring（監視）
  - システム状態（CPU/MEM/DISK）、Execution プロセスの存否、データ鮮度をチェック
  - 注文・約定ログの監視、滞留注文・異常約定等の検出
  - ドローダウン・ポジション上限の監視と Kill Switch 書き込み
- ポートフォリオ構築
  - 候補選定、等重/スコア重み、ポジションサイズ計算（リスクベース含む）
  - セクター制限適用、レジームに応じた投下資金乗数
- Research（因子計算・特徴量解析）
  - モメンタム、ボラティリティ、バリューなどのファクター計算（DuckDB 使用）
  - 将来リターン計算・IC（Information Coefficient）・統計サマリ
- AI（ニュース NLP / レジーム判定）
  - OpenAI（gpt-4o-mini）を利用したニュースセンチメント評価（ai_scores への書込み）
  - ETF + マクロニュースを組み合わせた市場レジーム判定と DB 書き込み
  - エラーハンドリング・リトライ・部分書き込み設計でフェイルセーフ性を確保
- ユーティリティ
  - .env 対話ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - ロギング設定ユーティリティ（TimedRotatingFileHandler）
  - プロセス優先度 / CPU affinity 設定ユーティリティ
  - Paper Trading 検証レポート生成ツール

---

## 必要要件
- Python 3.10 以上（PEP 604 の型表記や型合成を使用）
- 推奨パッケージ（最低限で動かす場合は一部省略可）
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証で任意）
- 標準ライブラリ: sqlite3, threading, logging, datetime, pathlib など

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

（実運用ではバージョン固定した requirements.txt を用意することを推奨します）

---

## セットアップ手順（簡易）
1. リポジトリをクローンして作業ディレクトリへ移動
2. 仮想環境作成・有効化
3. 依存パッケージをインストール（上記参照）
4. 初期設定ファイル `.env` の作成
   - 対話式ウィザード:
     ```bash
     python -m kabusys.config_setup
     ```
   - もしくは直接 `.env` を作成（`.env.example` を参考に）
   - 自動読み込み: デフォルトでプロジェクトルートの `.env` / `.env.local` をロードします。
     自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
5. 設定検証:
   ```bash
   python -m kabusys.validate_config
   # 厳格モード（警告も失敗として扱う）
   python -m kabusys.validate_config --strict
   ```
6. DB は起動時に必要テーブルが自動作成されます（monitoring は init_monitoring_db が実行されます）。

---

## 環境変数（主要）
以下は重要な環境変数とデフォルト値・意味です。

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants API 用トークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
- OPENAI_API_KEY — OpenAI API キー（AI 機能利用時）
- KABUSYS_ENV — 実行環境: development | paper_trading | live （デフォルト: development）
  - paper_trading の場合、run_execution は paper_sqlite_path（デフォルト data/paper_trading.db）を使用
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — 監視用 DB（run_monitoring が使用）: デフォルト data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — paper_trading の専用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL — デフォルト INFO
- LOG_DIR — ログ出力ディレクトリ（デフォルト logs）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE — ペーパートレードの約定モード: instant|partial|never|reject（デフォルト instant）
- KILL_FLAG_CLEAR_ON_START — 本番での自動 kill flag クリア（危険）: 0|1（デフォルト 0）

注意:
- run_monitoring は「環境にかかわらず」settings.sqlite_path（監視 DB）を使用します（監視は常に本番 DB を見る設計）。
- run_execution は KABUSYS_ENV=paper_trading のとき paper_sqlite_path を使用し、本番 DB を汚しません。

---

## 使い方（主要コマンド）
- 設定ウィザード（.env 作成）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```

- ExecutionEngine を起動（発注エンジン）
  ```bash
  python -m kabusys.run_execution
  ```
  - 起動時に `data/execution.pid` を書きます（pid_file）。
  - `data/stop_requested.flag` が置かれると停止します（または Kill Switch による `data/kill.flag` 発動で停止）。

- Monitoring を起動（監視プロセス）
  ```bash
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（秒）。
  - 停止は `data/stop_requested.flag` を作成することで可能。

- Paper Trading 検証レポート（ツール）
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルト DB: `data/paper_trading.db`（`--db` または環境変数 `PAPER_TRADING_SQLITE_PATH` で指定可）

- AI 機能（プログラムから呼び出す）
  - ニュースセンチメント評価:
    ```python
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    n_written = score_news(conn, target_date=date(2026,4,1), api_key="your_openai_key")
    ```
  - レジーム判定:
    ```python
    from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime

    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, target_date=date(2026,4,1), api_key="your_openai_key")
    ```

---

## 停止・Kill Switch の取り扱い
- ExecutionEngine の停止シグナルはファイルベース:
  - 手動停止（監視側・運用者）: `data/kill.flag` を作成すると ExecutionEngine に停止シグナルが送られます（KillSwitch）。
  - run_* スクリプトを即座に停止させたい場合: `data/stop_requested.flag` を作成すると監視・実行スクリプトはループを抜けて終了します。
- KillSwitch はドローダウン超過やポジション上限超過などで自動的に `data/kill.flag` を書き込みます（既に存在する場合は上書きしない）。

起動時に `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に kill.flag を自動で消去しますが、本番環境では危険な設定です（デフォルト 0 を推奨）。

---

## ロギング
- 共通ユーティリティ `kabusys.utils.logging_setup.setup_logging` を通じてログを統一的に設定します。
- ログは stdout にも出力され、日次ローテート（logs/<app_name>.log）で保存されます。デフォルトの保持期間は 30 日。
- `LOG_DIR` でログディレクトリを変更可能。`LOG_LEVEL` でログレベルを指定。

---

## ディレクトリ構成（主要ファイル）
（src/kabusys 以下を抜粋）

- __init__.py
  - パッケージメタ情報（バージョン等）
- config.py
  - Settings クラス: 環境変数の読み取り・検証、自動 .env ロード
- config_setup.py
  - .env の対話式ウィザード（python -m kabusys.config_setup）
- validate_config.py
  - 設定検証 CLI（必須環境変数・YAML ファイル存在等）
- run_execution.py
  - ExecutionEngine 起動スクリプト（発注エンジン）
- run_monitoring.py
  - Monitoring ポーリングループ起動スクリプト
- monitoring/
  - monitoring_db.py : 監視用 SQLite テーブル定義・CRUD ラッパー
  - system_monitor.py : CPU/MEM/DISK、データ鮮度、プロセス監視
  - trade_monitor.py : （注文）監視ロジック（滞留注文・約定異常等の検出）
  - risk_monitor.py : ドローダウン・ポジション上限監視
  - kill_switch.py : kill.flag 操作ユーティリティ
  - monitoring_engine.py : 各モニタを束ねるエンジン
  - alert_manager.py : （アラート送信ロジック: LINE 等）※実装あり
- execution/
  - ブローカー・エンジン関連（EngineConfig, ExecutionEngine, OrderManager, Reconciler, RiskManager 等）
  - broker_factory により本番/モックの切替え
- portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py
  - ポートフォリオ候補選定・重み付け・株数計算・セクター制限
- research/
  - factor_research.py : モメンタム/ボラ/バリュー等の因子計算（DuckDB）
  - feature_exploration.py : 将来リターン・IC・統計サマリ等
- ai/
  - news_nlp.py : ニュースを OpenAI でスコアリングし ai_scores に書き込む
  - regime_detector.py : ETF + マクロニュースを組合せてレジーム判定
- tools/
  - paper_verification_report.py : ペーパートレード結果の検証レポート生成
- utils/
  - logging_setup.py : ログ設定ユーティリティ
  - process_priority.py : プロセス優先度 / CPU affinity 設定ユーティリティ

（その他、data/ や logs/ などの運用用ディレクトリは起動時に作成されます）

---

## 補足・運用上の注意
- 本番（KABUSYS_ENV=live）では kill flag の自動クリアやテスト用 API キーの流用に注意してください。validate_config の出力を必ず確認してください。
- AI 機能は OpenAI API を利用します。API 呼び出しに伴うコストおよびレイテンシを考慮して運用してください。API キーは安全に管理してください。
- run_monitoring は監視用 DB（SQLite）に接続してログを書きます。監視は本番 DB（settings.sqlite_path）に対して実行されます。
- Paper Trading の DB は本番とは別に保持されます（PAPER_TRADING_SQLITE_PATH）。ペーパートレードと本番データが混在しないようにしてください。
- duckdb を使った解析・因子計算はメモリ使用量が増える場合があります。適宜リソースを監視してください。
- プロセス優先度や CPU affinity の設定は psutil に依存します。権限がない環境では警告が出ることがありますが処理は継続します。

---

必要であれば README にサンプル .env テンプレートや systemd / supervisor 用のユニットファイル例、各モジュールのより詳細な API 使用例を追加できます。どの情報を優先して追加したいか教えてください。