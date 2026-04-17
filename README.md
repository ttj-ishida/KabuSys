# KabuSys

日本株向けの自動売買 / 研究基盤ライブラリ群および実行・監視スクリプト群です。  
このリポジトリはトレード実行エンジン、監視（Monitoring）、ポートフォリオ構築・ポジションサイズ算出、ファクター計算・リサーチ、ニュース NLP を用いた AI スコアリング等を含みます。

※ 本 README はコードベースに含まれる主要モジュールの説明・セットアップ・使い方をまとめたものです。

---

## 概要（Project overview）

KabuSys は以下の目的を持つモジュール群です。

- 日次または当日リアルタイムでの発注・発注管理（ExecutionEngine）
- システム状態・注文状況・リスク指標のポーリング監視（Monitoring）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算）
- ファクター計算 / 特徴量探索（DuckDB を用いた時系列計算）
- ニュース記事からの LLM（OpenAI）を使ったセンチメント評価・レジーム判定
- ペーパートレード用の分離された DB と検証ツール
- .env 対話式セットアップ・設定検証 CLI

設計方針の一例：
- DuckDB を分析に、SQLite を軽量な永続ログ（監視・注文ログ）に使用
- Paper Trading は本番 DB と完全分離（`PAPER_TRADING_SQLITE_PATH`）
- LLM 呼び出しはリトライ・検証ロジックを備えフェイルセーフ化

---

## 主な機能（Features）

- Execution
  - 実際のブローカークライアント or MockBroker を切り替えて実行可能（KABUSYS_ENV に依存）
  - 発注履歴・約定ログ管理（SQLite）
  - 停止フラグ（Kill Switch）による安全停止機構

- Monitoring
  - SystemMonitor：CPU / メモリ / ディスク / プロセス・データ鮮度監視
  - TradeMonitor：滞留注文・約定異常の検出
  - RiskMonitor：ドローダウン・ポジション数の監視・アラートログ
  - MonitoringEngine：各モニタを束ねて定期実行（ポーリング）

- Portfolio
  - 候補選定（スコア順取捨選択）
  - 等金額 / スコア加重の重み計算
  - ポジションサイズ計算（リスクベース・上限管理・単元丸め）
  - セクター集中制限・レジーム乗数の適用

- Research
  - Momentum / Volatility / Value 等のファクター計算（DuckDB SQL ベース）
  - 将来リターン・IC（Information Coefficient）・統計サマリ

- AI
  - ニュース記事の銘柄別センチメント評価（OpenAI, gpt-4o-mini を想定）
  - マクロニュース + ETF MA を用いた市場レジーム判定
  - API レスポンス検証・リトライ・部分成功の保護（DB 書き込みの冪等処理）

- CLI / ユーティリティ
  - .env 対話式ウィザード（config_setup）
  - 設定検証（validate_config）
  - Paper Trading 検証レポート生成スクリプト
  - プロセス優先度 / CPU affinity の設定ユーティリティ

---

## セットアップ手順（Setup）

前提
- Python 3.10+（typing の一部機能や f-strings、型ヒントの為に 3.10 以上を想定）
- SQLite は標準ライブラリに含まれます

推奨依存ライブラリ（最低限）:
- duckdb
- psutil
- openai
- PyYAML（config の検証を行う場合に必要）

インストール例（仮に venv を使う場合）:
```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install duckdb psutil openai pyyaml
```

初期設定:
1. プロジェクトルートで .env を生成／編集します。対話式で作る場合:
   ```bash
   python -m kabusys.config_setup
   ```
   主要な環境変数（抜粋）:
   - JQUANTS_REFRESH_TOKEN （必須）
   - KABU_API_PASSWORD （必須）
   - KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（監視用: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB: data/paper_trading.db）
   - OPENAI_API_KEY（AI 機能利用時に必要）
   - LOG_LEVEL（INFO 等）
   - KILL_FLAG_CLEAR_ON_START（本番では 0 推奨）

2. 設定検証:
   ```bash
   python -m kabusys.validate_config
   # 警告も厳密にチェックする場合:
   python -m kabusys.validate_config --strict
   ```

3. データディレクトリを用意（必要に応じて）:
   ```bash
   mkdir -p data
   ```

備考:
- Paper Trading は本番 DB と分離され、`KABUSYS_ENV=paper_trading` のとき `PAPER_TRADING_SQLITE_PATH` を使います。
- OpenAI を使う機能は `OPENAI_API_KEY` を環境変数で設定してください。

---

## 使い方（Usage）

エントリポイント（代表的なコマンド）:

- ExecutionEngine（売買実行）
  - 通常実行:
    ```bash
    python -m kabusys.run_execution
    ```
  - Paper Trading 実行（.env で KABUSYS_ENV=paper_trading を設定）
    - Paper Trading 時は MockBrokerClient を使用し、データは `data/paper_trading.db`（または `PAPER_TRADING_SQLITE_PATH`）に書き込まれます。
  - 停止方法:
    - `data/stop_requested.flag` の存在検知で Engine を順次停止します。
    - Kill Switch（監視側から）により `data/kill.flag` が生成されると停止トリガーとなります。

- Monitoring（監視ループ）
  - 起動:
    ```bash
    python -m kabusys.run_monitoring
    ```
  - ポーリング間隔:
    - 環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能（デフォルト 60 秒）。
  - 監視は常に本番の sqlite_path を使用（環境に関わらず監視ログは production sqlite を想定）。

- .env ウィザード
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-10
  # DB 指定:
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI / リサーチ系関数
  - ニューススコアリングやレジーム判定はモジュール関数として呼び出します（例: kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime）。実行には OPENAI_API_KEY が必要です。
  - 例（簡単なスクリプト内で）
    ```python
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date, api_key="sk-...")
    ```

環境変数（重要なもの・デフォルト）
- KABUSYS_ENV=development | paper_trading | live (default: development)
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
- OPENAI_API_KEY (AI 機能利用時)
- MONITOR_POLL_INTERVAL (監視ポーリング秒)
- PAPER_FILL_MODE (paper_trading の約定挙動: instant | partial | never | reject)
- LOG_LEVEL (INFO 等)

注意点:
- Monitoring は監視ログを記録・リスクイベントを log_risk_event で永続化します。kill.flag の自動クリアは `KILL_FLAG_CLEAR_ON_START` により制御されます（本番では OFF を推奨）。
- ExecutionEngine 側は起動時に `data/execution.pid` を作成し、SystemMonitor が存在確認する仕組みです。

---

## ディレクトリ構成（Directory structure）

リポジトリ内の主要ファイル／モジュールと概略:

- src/kabusys/
  - __init__.py — パッケージ定義（__version__ 等）
  - config.py — 環境変数 / Settings 管理（.env 自動読み込み機能含む）
  - config_setup.py — .env 対話式ウィザード CLI
  - validate_config.py — 起動前の設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor 単体ポーリングスクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成ツール
  - ai/
    - news_nlp.py — ニュース記事の LLM ベースのセンチメント評価
    - regime_detector.py — マクロ+ETF MA による市場レジーム判定（LLM 使用）
  - monitoring/
    - monitoring_db.py — SQLite ベースの監視 DB 初期化・ラッパー
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - system_monitor.py — CPU/MEM/DISK/プロセス・データ鮮度チェック
    - trade_monitor.py — 注文滞留・約定異常チェック
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag の生成・評価ロジック
    - alert_manager.py — （アラート送信ロジック、未完の箇所あり）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数計算・上限・aggregate cap
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — momentum / volatility / value 等のファクター計算
    - feature_exploration.py — 将来リターン・IC・統計関数
  - monitoring/ (既述)
  - utils/
    - process_priority.py — プロセス優先度・CPU affinity ユーティリティ

付属:
- data/ — データ・DB を置くディレクトリ（実行時に生成される想定）
  - monitoring.db（デフォルト SQLite 監視DB）
  - kabusys.duckdb（デフォルト DuckDB）
  - paper_trading.db（ペーパートレード用 SQLite、KABUSYS_ENV=paper_trading 時に使用）
  - execution.pid / stop_requested.flag / kill.flag などの制御ファイル

---

## 追加メモ / トラブルシューティング

- PyYAML が無いと config/*.yaml のパース検証はスキップされます（validate_config が警告を出します）。設定ファイルを検証したい場合は PyYAML をインストールしてください。
- OpenAI 呼び出しにはネットワークの安定性やレート制限の対処（リトライ）を組み込んでありますが、API キーは厳重に管理してください。ローカル開発時は短期キーやモックを使うことを推奨します。
- Paper Trading と本番 DB は明示的に分離されています。Paper 環境で本番 DB を上書きしないよう `KABUSYS_ENV` と各パスを確認してください。
- MONITOR_POLL_INTERVAL が不正な値（整数でない、0 以下など）の場合はデフォルト 60 秒にフォールバックします。
- 監視と実行をそれぞれ別プロセスで動かすことを想定しています。監視は実行プロセスを pid ファイルで検知します。

---

この README はコードに含まれる意図・挙動をまとめたものです。実際のデプロイ時は .env / config/*.yaml の内容、API キー、DB のバックアップ方針、ログ・監視ポリシーを運用ルールに従って適切に設定してください。必要であれば各モジュールの詳細ドキュメント（関数レベルの docstring）を参照してください。