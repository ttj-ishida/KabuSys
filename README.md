# KabuSys

日本株自動売買システム（KabuSys）のリポジトリ用 README。

この README はコードベース（src/kabusys 以下）から抽出した概要、機能、セットアップ・実行手順、使い方、ディレクトリ構成を日本語でまとめたものです。

注意: 実運用では .env に機密情報を含めたままリポジトリにコミットしないでください。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買・研究プラットフォームです。主な要素は次の通りです。

- ExecutionEngine：ブローカークライアントを通じて注文を発行・管理する実行コンポーネント。paper_trading 環境時は MockBrokerClient を使用して発注を分離。
- Monitoring：システム状態、注文・約定の監視、リスク監視、Kill Switch（閾値到達時に Execution を停止するフラグ）を提供。
- Portfolio コンポーネント：銘柄選定、重み算出、ポジションサイズ計算、セクター制約、レジーム乗数など。
- Research：DuckDB を用いたファクター計算、将来リターン計算、IC 計測、統計サマリ等。
- AI モジュール：ニュースの NLP スコアリング（OpenAI）や市場レジーム判定（OpenAI と市場データの融合）。
- ユーティリティ：環境設定ウィザード、設定検証スクリプト、ログ設定、プロセス優先度設定など。
- ツール：Paper Trading 検証レポート生成など。

---

## 主な機能一覧

- 環境設定ウィザード（.env の対話式生成）
- 設定検証 CLI（.env と config/*.yaml のチェック）
- ExecutionEngine（本番／ペーパートレード対応、リスク管理組込み）
- Monitoring（CPU/メモリ/ディスク/プロセス監視、データ鮮度チェック）
- Kill Switch（ドローダウン等の閾値到達で execution 停止用フラグ作成）
- Trade / Risk ログ永続化（SQLite）
- DuckDB を使ったファクター計算・リサーチ機能
- ニュース NLP（OpenAI を使った銘柄別センチメントスコア）
- 市場レジーム判定（ETF の MA やマクロニュースを利用）
- Paper Trading の検証レポート生成

---

## 前提（依存ライブラリ・推奨）

最低限、以下のパッケージが必要になります（実際の requirements はプロジェクトの packaging に従ってください）。

- Python 3.9+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（config.yaml の中身検証を行う場合）
- （その他：使用するブローカークライアント等）

仮想環境例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順（クイックスタート）

1. リポジトリをクローンしてワークディレクトリへ移動
2. 仮想環境作成・依存インストール（上記参照）
3. .env を作成
   - 対話式ウィザードを使うと簡単です:
     ```
     python -m kabusys.config_setup
     ```
   - もしくは .env を手動で作成（.env.example を参考にしてください）。主要な環境変数は下記参照。
4. 設定検証（起動前チェック）:
   ```
   python -m kabusys.validate_config
   # --strict を付けると警告もエラー扱い
   python -m kabusys.validate_config --strict
   ```
5. データ・ログディレクトリの作成（必要に応じて）
   - デフォルトでは `data/`（SQLite 等）、`logs/`（ログ）を使用します。logging 設定は自動で作成を試みますが、権限等で失敗する場合は手動で作成してください。

---

## 環境変数（代表的なもの）

以下はコードから抽出した主要な環境変数（デフォルト値や用途も併記）。

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY — OpenAI を使う機能（ニュース NLP / レジーム判定）で必要
- PAPER_FILL_MODE — paper_trading 時の約定モード（instant|partial|never|reject、デフォルト: instant）
- KABUSYS_ENV — 実行環境（development | paper_trading | live。デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト: INFO）
- LOG_DIR — ログディレクトリ（デフォルト: logs/）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（1 = yes、開発用。デフォルト: 0）
- MONITOR_POLL_INTERVAL — monitoring のポーリング間隔（秒、デフォルト: 60）
- その他: PID / kill flag のパス等は Settings によるデフォルトを使用

---

## 実行方法（主要スクリプト）

- ExecutionEngine（エンジン起動）
  - paper_trading 環境では MockBrokerClient が使用され、paper DB に記録されます。
  - 起動:
    ```
    python -m kabusys.run_execution
    ```
  - 実行中に停止させたい場合は、リポジトリの data ディレクトリに停止フラグを書き込みます（stop_requested.flag）。実際の Kill Switch は監視側から data/kill.flag を書き込むことで ExecutionEngine に停止シグナルを送ります。

- Monitoring（監視ループ起動）
  - 起動:
    ```
    python -m kabusys.run_monitoring
    ```
  - ポーリング間隔を環境変数で調整:
    ```
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```
  - 停止フラグ: data/stop_requested.flag を作成すると監視ループは終了します。
  - Monitoring は Settings に指定された（本番） sqlite_path を使って監視ログを書き込みます（環境に依存せず本番 DB を参照）。

- 環境設定ウィザード:
  ```
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート（SQLite DB を指定可能）:
  ```
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

---

## Kill Switch / 停止フラグの挙動

- Kill Switch（monitoring.kill_switch）は監視結果（ドローダウン、ポジション上限など）に基づき `data/kill.flag` を作成します。ExecutionEngine は起動時や実行中にこのフラグを検出して安全に停止します。
- 人的にプロセスを停止したい場合は `data/stop_requested.flag` を作成すると run_monitoring/run_execution のループが検出して終了します（それぞれのスクリプトで stop flag の検査が行われます）。
- `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に kill.flag を自動クリアします（本番では通常 0 を推奨）。

---

## ログと DB

- ログ:
  - setup_logging が root ロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション）を設定します。
  - ログディレクトリデフォルト: logs/
  - ファイル名はアプリ名（例: execution.log, monitoring.log）になります。

- DB:
  - DuckDB: データ解析やファクター計算に使用（デフォルト: data/kabusys.duckdb）
  - SQLite: 監視ログやトレードログ等（デフォルト: data/monitoring.db）
  - paper_trading 実行時は paper_trading 用 SQLite（data/paper_trading.db）を別途使用して本番 DB と分離します。

---

## 使い方のワークフロー（簡易）

1. .env を設定（config_setup を推奨）
2. `python -m kabusys.validate_config` でチェック
3. 必要ならデータ（DuckDB / raw_news / prices_daily 等）を準備
4. 監視を起動：`python -m kabusys.run_monitoring`
5. Execution を起動：`python -m kabusys.run_execution`
6. Paper Trading の検証: `python -m kabusys.tools.paper_verification_report`
7. AI 関連（ニューススコア等）を利用する場合は OPENAI_API_KEY を設定

---

## 主要ディレクトリ構成（src/kabusys の概観）

- kabusys/
  - __init__.py — パッケージ定義（バージョン等）
  - config.py — 環境変数・設定管理（Settings クラス）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring ポーリングループ起動スクリプト

  - ai/
    - news_nlp.py — ニュース NLP（OpenAI）で ai_scores を作成
    - regime_detector.py — マーケットレジーム判定（OpenAI + ETF 指標）
  - monitoring/
    - monitoring_db.py — 監視用 DB 永続化層（SQLite）
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — 注文滞留・約定異常チェック（ファイルに一部実装）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 管理
    - alert_manager.py — （アラート送信の管理）
    - monitoring_engine.py — Monitor を束ねる実行ループ
  - execution/
    - execution_engine.py — ExecutionEngine（注文実行ロジック）
    - broker_factory.py — ブローカークライアント生成
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py — 実行系コンポーネント
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数計算、リスク制限、単元丸め
    - risk_adjustment.py — セクターキャップ、レジーム乗数
  - research/
    - factor_research.py — モメンタム/バリュー/ボラティリティ等のファクター計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリ等
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ

（上記は主要ファイルの抜粋です。詳細はソースコードを参照してください。）

---

## 注意点 / 運用上のヒント

- 本番（KABUSYS_ENV=live）では LINE の通知設定（LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID）を必ず確認してください。validate_config で警告されます。
- .env は秘密情報を含むため絶対に Git へコミットしないでください（config_setup でもその旨コメントが付与されます）。
- OpenAI を用いる機能は API コストとレイテンシを考慮して運用してください。API キーは環境変数で渡します。
- monitoring はデフォルトで本番 sqlite を使用します。monitoring が production DB を触る点に注意してください。
- paper_trading 環境は本番データベースと分離されるように設計されています。テスト・検証時は KABUSYS_ENV=paper_trading を利用すると安全です。
- プロセス優先度やログディレクトリ作成に失敗した場合は警告が出ますが、システムは継続動作できる設計です。

---

## 参考コマンドまとめ

- .env 対話式作成:
  ```
  python -m kabusys.config_setup
  ```
- 設定検証:
  ```
  python -m kabusys.validate_config
  ```
- Execution 起動:
  ```
  python -m kabusys.run_execution
  ```
- Monitoring 起動（ポーリング間隔変更例）:
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
- Paper Trading レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

必要があれば README の英語版、より詳細な運用手順（systemd / supervisor / Docker 実行例）や requirements.txt の生成、CI 用チェック手順なども作成できます。どの追加情報が欲しいか教えてください。