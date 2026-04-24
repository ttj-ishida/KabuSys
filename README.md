# KabuSys

日本株自動売買システムのリポジトリ（ドキュメント版）。  
この README はコードベース（src/kabusys）に含まれる主要機能と実行方法、設定手順、ディレクトリ構成をまとめたものです。

※ 本 README は日本語での利用を想定しています。

---

目次
- プロジェクト概要
- 主な機能一覧
- 必要な依存パッケージ
- セットアップ手順
- 環境変数（.env）と推奨設定例
- 使い方（CLI／起動スクリプト）
- 停止・Kill スイッチについて
- ディレクトリ構成（主要ファイルの説明）

---

## プロジェクト概要

KabuSys は日本株向けの自動売買プラットフォームのコンポーネント群です。  
主な目的は以下:

- 市場データ・ファクター計算（Research / factor calculation）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイジング）
- 発注実行エンジン（実口座 / ペーパートレード切替）
- 監視・アラート（システム状態、注文状況、リスク監視）
- ニュースの NLP によるセンチメント評価（OpenAI 利用）
- 運用支援ツール（設定ウィザード、設定検証、ペーパートレード検証レポート）

設計方針の一部：
- DuckDB を分析用 DB として使用、SQLite を操作ログ / 監視ログに使用
- 環境による本番／ペーパー切替をサポート（KABUSYS_ENV）
- OpenAI API 呼び出しはフェイルセーフを意識して実装
- 外部ライブラリへの依存は必要最小限（テスト容易性を考慮）

---

## 主な機能一覧

- 設定管理
  - .env 自動ロード / config 設定読み込み（src/kabusys/config.py）
  - 対話式設定ウィザード（python -m kabusys.config_setup）
  - 起動前設定検証ツール（python -m kabusys.validate_config）

- 実行エンジン
  - ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）
  - ペーパートレード時は MockBroker を使用しデータを data/paper_trading.db に記録

- 監視
  - System / Trade / Risk Monitor を束ねる MonitoringEngine（src/kabusys/monitoring）
  - run_monitoring.py によりポーリング監視を継続実行
  - 監視ログは SQLite（data/monitoring.db デフォルト）に永続化

- ポートフォリオ構築（純粋関数）
  - 候補選定、重み計算、ポジションサイズ計算、セクター制限・レジーム補正（src/kabusys/portfolio）

- リサーチ
  - ファクター計算（momentum, volatility, value）、将来リターン、IC 計算（src/kabusys/research）

- AI（OpenAI）
  - ニュースを用いた銘柄センチメント評価（src/kabusys/ai/news_nlp.py）
  - マクロ記事 + ETF MA200 による市場レジーム判定（src/kabusys/ai/regime_detector.py）

- ユーティリティ
  - ロギングセットアップ（logs 日次ローテーション）
  - プロセス優先度 / CPU affinity の共通ユーティリティ

- ツール
  - Paper Trading 検証レポート生成スクリプト（python -m kabusys.tools.paper_verification_report）

---

## 必要な依存パッケージ

最低限想定されるパッケージ（例）:

- Python 3.10+
- duckdb
- psutil
- openai
- PyYAML（config ファイルの検証で推奨）
- （sqlite3 は標準ライブラリ）

インストール例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

注意: requirements.txt はリポジトリに含まれていないため、必要に応じてバージョン固定してください。

---

## セットアップ手順

1. リポジトリをクローン／配置
2. Python 仮想環境を作成して有効化
3. 依存パッケージをインストール（上記参照）
4. .env を作成・編集
   - 対話式ウィザードを利用する:
     ```
     python -m kabusys.config_setup
     ```
   - 生成した .env を確認し、必要な機密値（JQUANTS_REFRESH_TOKEN や KABU_API_PASSWORD、OPENAI_API_KEY 等）を設定する
5. 設定検証
   ```
   python -m kabusys.validate_config
   ```
   `--strict` を付けると警告もエラー扱いになります
6. データディレクトリ作成（logs / data）
   ```
   mkdir -p data logs
   ```

---

## 環境変数 / .env（主要項目）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD — kabu ステーション API パスワード

よく使うオプション（デフォルト値）:
- KABUSYS_ENV — 実行環境: development / paper_trading / live（default: development）
- DUCKDB_PATH — 分析用 DuckDB（default: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（default: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR）
- OPENAI_API_KEY — OpenAI 利用時に必要
- LOG_DIR — ログ出力ディレクトリ（default: logs）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動で消す (0/1)（本番では 0 推奨）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、default: 60）

PAPER_FILL_MODE（ペーパートレードの約定挙動）
- instant / partial / never / reject（default: instant）

推奨 .env（例抜粋）
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...
KILL_FLAG_CLEAR_ON_START=0
```

---

## 使い方（起動スクリプト・CLI）

主な CLI / 実行スクリプト:

- 設定ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 実行エンジン（ExecutionEngine）起動
  - 実行:
    ```
    python -m kabusys.run_execution
    ```
  - 備考:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い paper_trading 用 DB（data/paper_trading.db）に記録します
    - プロセス PID は data/execution.pid に書き込まれます
    - 起動前に data/stop_requested.flag が存在する場合は起動しません

- 監視（Monitoring）起動
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）
  - 監視は Settings.sqlite_path（監視 DB）を使用（環境にかかわらず本番の sqlite_path を使う実装）
  - 停止は data/stop_requested.flag を作ることで行えます

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - 引数 --db で SQLite ファイルパスを明示できます（環境変数 PAPER_TRADING_SQLITE_PATH でも可）

- AI / レジーム判定・ニューススコア（ライブラリ関数）
  - ai モジュールは OpenAI API キー（OPENAI_API_KEY）を必要とします
  - これらはライブラリ関数を直接呼ぶ形で利用します（例: kabusys.ai.score_news）

ログ:
- デフォルトで logs/<app_name>.log に日次ローテートで出力されます
- 起動時にロギング設定は共通ユーティリティから行われます（kabusys.utils.logging_setup.setup_logging）

---

## 停止と Kill スイッチ

- 停止フラグ（run_execution / run_monitoring が参照）
  - data/stop_requested.flag — 存在すると run_* スクリプトが安全に停止処理を開始します
- Kill Switch（監視が出す停止信号）
  - data/kill.flag（デフォルト）に理由文字列を書き込むことで ExecutionEngine に停止指示を出します
  - 設定 KILL_FLAG_CLEAR_ON_START=1 にすると起動時に kill.flag を自動でクリアしますが、本番では危険なため 0 を推奨します

---

## ディレクトリ構成（主要ファイルの説明）

以下は src/kabusys 以下の主要モジュールとその役割の抜粋です。

- kabusys/
  - __init__.py — パッケージ定義
  - config.py — 環境変数・.env の自動ロードと Settings クラス
  - config_setup.py — 対話式 .env 作成ウィザード
  - validate_config.py — 起動前設定検証 CLI

- run scripts
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト

- ai/
  - news_nlp.py — ニュースを LLM でセンチメント評価し ai_scores に書き込む
  - regime_detector.py — ETF MA200 とマクロニュースで市場レジームを判定

- monitoring/
  - monitoring_db.py — SQLite ベースの永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py — システム CPU/メモリ/ディスク、データ鮮度、プロセス監視
  - trade_monitor.py —（注文に関する監視、コードベースに含まれるがここでは省略） 
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag の生成 / 管理
  - monitoring_engine.py — 各 Monitor の統合とアラート送出（ポーリング実行用）

- portfolio/
  - portfolio_builder.py — 候補選定、重み（等金額、スコア加重）
  - position_sizing.py — 株数算出、上限・集約キャップ対応
  - risk_adjustment.py — セクター上限適用、レジーム乗数

- research/
  - factor_research.py — momentum / volatility / value 等ファクター計算（DuckDB 経由）
  - feature_exploration.py — 将来リターン、IC、統計サマリー
  - __init__.py — 研究用 API エクスポート

- utils/
  - logging_setup.py — コンソール + 日次ファイルローテーションの共通設定
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

- tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト

data/ および logs/ はリポジトリに含めず、実行環境で作成する想定です（data/** は DB やフラグファイルが配置されます）。

---

## 運用上の注意・ベストプラクティス

- 本番環境では KABUSYS_ENV=live に設定する前に、必須環境変数や通知設定（LINE 等）を確実に設定してください（validate_config の警告を確認）。
- KILL_FLAG_CLEAR_ON_START=1 は本番では推奨されません（意図せず kill.flag を消してしまう可能性があるため）。
- OpenAI を利用する処理は API 負荷やコストを引き起こすため、キーと呼び出し頻度を管理してください。
- ログディレクトリの権限やディスク容量を監視し、ログローテーションや容量監視を適切に運用してください。
- DuckDB / SQLite のバックアップやファイルロック挙動に注意（複数プロセスでの同時書込等）。

---

もし README に追加してほしい内容（例: 具体的な実行例、ユニットテストの実行方法、詳細な設定例ファイルのサンプル等）があれば教えてください。必要に応じて追記します。