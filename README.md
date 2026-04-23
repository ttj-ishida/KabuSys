# KabuSys

日本株向け自動売買システムのコアライブラリ群と運用ユーティリティ群です。  
このリポジトリは戦略リサーチ、ポートフォリオ構築、発注エンジン、監視/アラート、AI ベースのニュース解析などを含むモジュール群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の目的を持ったモジュール群を提供します。

- 戦略リサーチ（ファクター計算、特徴量解析）
- ポートフォリオ構築（候補選定、重み計算、株数決定）
- 発注実行エンジン（ExecutionEngine）および注文管理（発注・約定ログ保管）
- 監視（System / Trade / Risk モニタ）と Kill Switch による安全停止
- AI（OpenAI）を用いたニュースセンチメント・レジーム判定
- 運用支援 CLI（.env ウィザード、設定検証、Paper Trading レポート生成）

設計方針の一例:
- データ永続化に DuckDB（分析用）と SQLite（監視・発注ログ）を使用
- 環境変数 / .env による設定管理（自動ロードあり）
- paper_trading モードで本番 DB と分離してペーパートレード可能

---

## 主な機能一覧

- 環境設定管理
  - .env 自動読み込み（プロジェクトルートを検出）
  - 対話式ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）
- 実行系
  - ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
    - KABUSYS_ENV=paper_trading の場合は MockBroker を利用し専用 DB に記録
  - Monitoring 起動スクリプト（python -m kabusys.run_monitoring）
    - システム監視をポーリングしてログ記録・アラート・Kill Switch 評価
- 監視モジュール
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine
  - MonitoringDB: SQLite を用いた永続化（テーブル作成・マイグレーション対応）
  - KillSwitch: 条件に応じて data/kill.flag を書き込み発注エンジンを停止
- ポートフォリオ構築
  - 銘柄選定・重み計算（等金額・スコア加重）
  - セクターキャップ適用、レジーム乗数
  - 株数決定（risk_based / equal / score、単元株丸め、aggregate cap）
- リサーチ（DuckDB）
  - モメンタム / ボラティリティ / バリュー計算
  - 将来リターン計算、IC（Information Coefficient）等
- AI（OpenAI）連携
  - ニュースセンチメント（news_nlp）
  - 市場レジーム判定（regime_detector）
  - API 呼び出しはリトライ・バリデーションを備えフェイルセーフ設計
- 運用ツール
  - Paper Trading 検証レポート生成スクリプト（python -m kabusys.tools.paper_verification_report）

---

## 前提 / 必要パッケージ

実行に必要な主な外部ライブラリ（最低限）:

- python >= 3.8
- duckdb
- psutil
- openai (AI 機能を使用する場合)
- （任意）PyYAML（設定ファイルの内容検証で使用）

pip 例:
```
pip install duckdb psutil openai PyYAML
```

注意: requirements.txt は付属していないため、用途に合わせて必要パッケージをインストールしてください。

---

## セットアップ手順（ローカル）

1. リポジトリをクローン:
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境作成（推奨）:
   ```
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール:
   ```
   pip install duckdb psutil openai PyYAML
   ```

4. 初期設定ファイル（.env）を作成:
   - 対話式ウィザードで作成:
     ```
     python -m kabusys.config_setup
     ```
   - もしくは `.env.example` を参照して `.env` を作成してください。

5. 設定の検証:
   ```
   python -m kabusys.validate_config
   # 警告も失敗扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

---

## 主要な環境変数（抜粋）

- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 運用 / DB:
  - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
    - paper_trading: 発注は MockBroker、DB は PAPER_TRADING_SQLITE_PATH（分離）
  - DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
  - PAPER_FILL_MODE: ペーパートレードでの約定動作（instant|partial|never|reject、デフォルト "instant"）
- ログ:
  - LOG_LEVEL: DEBUG|INFO|...（デフォルト INFO）
  - LOG_DIR: ログ保存先（デフォルト logs/）
- 実行・監視:
  - PID_FILE_PATH: ExecutionEngine の pid ファイルパス（デフォルト data/execution.pid）
  - KILL_FLAG_PATH: Kill Switch の flag（デフォルト data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0|1、デフォルト 0）
  - MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト 60）

- AI:
  - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）

---

## 使い方（起動例）

- 実行エンジン起動（本番 / ペーパートレードは KABUSYS_ENV に依存）:
  ```
  python -m kabusys.run_execution
  ```

  - ペーパートレードで起動する例:
    ```
    export KABUSYS_ENV=paper_trading
    python -m kabusys.run_execution
    ```

  - 起動時、data/execution.pid に PID を書きます。data/stop_requested.flag が存在すると起動しません。
  - 停止信号は data/stop_requested.flag（監視・外部操作で作成）で検出されます。

- 監視プロセス起動:
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（秒）。
  - 監視は常に本番 sqlite_path を使用します（環境にかかわらず）。

- kill.flag（Kill Switch）:
  - RiskMonitor 等が条件を満たすと data/kill.flag に理由を書き込みます。
  - ExecutionEngine は Settings.kill_flag_path（デフォルト data/kill.flag）を参照して安全停止します。
  - 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動クリアされます（本番では注意）。

- Paper Trading 検証レポート生成:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - --db で SQLite パスを指定可能。環境変数 PAPER_TRADING_SQLITE_PATH も使用可能。

- .env の対話編集:
  ```
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```
  python -m kabusys.validate_config
  ```

---

## ログ・データ

- ログ:
  - デフォルト: logs/<app_name>.log（TimedRotatingFileHandler 日次ローテーション、30日保持）
  - コンソール出力は stdout（stderr ではない）

- データ:
  - DuckDB: data/kabusys.duckdb
  - 監視 SQLite: data/monitoring.db
  - ペーパートレード SQLite: data/paper_trading.db
  - フラグ/管理ファイル: data/kill.flag, data/stop_requested.flag, data/execution.pid

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env 自動ロード、Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py            — ニュース NLP / OpenAI インターフェース
    - regime_detector.py     — 市場レジーム判定（OpenAI 併用）
  - monitoring/
    - monitoring_db.py       — SQLite テーブル初期化・永続化 API
    - system_monitor.py      — システム状態・データ鮮度監視
    - trade_monitor.py       — （注文関連監視; 実装あり）
    - risk_monitor.py        — ドローダウン等の監視
    - kill_switch.py         — Kill Switch 実装（flag ファイル）
    - monitoring_engine.py   — 各 Monitor を束ねるループ
  - portfolio/
    - portfolio_builder.py   — 候補選定、重み計算
    - position_sizing.py     — 発注株数計算（risk_based 等）
    - risk_adjustment.py     — セクター制限、レジーム乗数
  - research/
    - factor_research.py     — Momentum/Value/Vol計算（DuckDB）
    - feature_exploration.py — 将来リターン, IC, 統計サマリ
  - utils/
    - logging_setup.py       — 統一的なログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity 設定（psutil）

---

## 開発・拡張のヒント

- DuckDB のクエリは比較的大きな処理を想定しているため、ローカルでのデータ投入と SQL チューニングが重要です。
- OpenAI を利用する機能は API 呼び出しにリトライ・バリデーションを備えていますが、API 利用量・コストに注意してください。
- MonitoringDB は起動時に不足カラムを追加する簡易マイグレーション機能を持ちます（例: latency_ms, peak_value）。

---

## よく使うコマンドまとめ

- .env 作成 / 編集:
  ```
  python -m kabusys.config_setup
  ```
- 設定検証:
  ```
  python -m kabusys.validate_config
  ```
- 実行エンジン起動:
  ```
  python -m kabusys.run_execution
  ```
- 監視起動:
  ```
  python -m kabusys.run_monitoring
  ```
- Paper Trading レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

その他、ソースコード内の docstring / 関数コメントに設計や仕様が詳細に書かれているため、具体的な拡張やデバッグは該当モジュールを参照してください。必要であれば、各モジュールの利用例や API ドキュメント化を追加で作成します。