# KabuSys

日本株自動売買システムの Python コードベース（簡易版）。  
このリポジトリは注文実行エンジン、監視・アラート、ポートフォリオ構築、リサーチ（ファクター計算）、LLM ベースのニュース NLP などのコンポーネントを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要な主要コンポーネントを分離して実装したシステムです。主な目的は以下:

- Signal → Order の安全な発注フロー（クラッシュ耐性を考慮した永続化）
- 発注の自動リコンシリエーション（再起動後の整合性復旧）
- 監視（プロセス生存、システムリソース、注文滞留・約定異常、ドローダウン等）と通知
- ポートフォリオ構築（候補選定・配分・株数決定・セクター制約）
- DuckDB を用いたファクター計算・リサーチ機能
- OpenAI を使ったニュースセンチメント評価 & 市場レジーム判定（オプション）

設計方針として、ビジネスロジックと永続化を明確に分離し、フェイルセーフ／冪等性を重視しています。

---

## 機能一覧

- Execution
  - Signal を DB から読み出して発注（ExecutionEngine）
  - OrderManager: 発注→送信→状態遷移の管理（2相永続化などの耐障害設計）
  - Reconciler: 再起動時に未確定注文の同期・ポジション差分の検出
  - RiskManager（制限・レート制御・サーキットブレーカー）
- Monitoring
  - SystemMonitor: CPU/Mem/Disk、プロセス PID、データ鮮度の監視
  - TradeMonitor: 注文滞留、約定価格異常の検出
  - RiskMonitor: ドローダウンやポジション上限の監視
  - KillSwitch: 条件を満たしたら flag ファイルを書き ExecutionEngine を停止させる仕組み
  - AlertManager: LINE Push による通知（クールダウン管理）
  - Streamlit ダッシュボードで簡易 UI を提供
- Portfolio
  - 候補選定（スコア順）、等金額/スコア加重配分、リスクベース株数計算、セクター上限適用
- Research
  - DuckDB を用いた momentum/volatility/value ファクター計算、将来リターン計算、IC や統計サマリ
- AI
  - ニュースの LLM ベースセンチメントスコアリング（OpenAI 使用）
  - マクロニュース + ETF MA200 による市場レジーム判定
- Utils
  - プロセス優先度 / CPU affinity 設定ユーティリティ（psutil ベース）
- 設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出）と Settings クラス

---

## セットアップ手順

※ Python 3.9+ を想定しています。

1. リポジトリをクローンして作業ディレクトリに入る
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージ（代表例）をインストール
   必須 / 推奨パッケージ:
   - duckdb
   - psutil
   - requests
   - openai
   - streamlit (ダッシュボード実行時)
   - (テスト用に pytest 等)

   例:
   ```
   pip install duckdb psutil requests openai streamlit
   ```

4. データディレクトリを作成
   デフォルトでは `data/` 下に DB 等を作成します。
   ```
   mkdir -p data
   ```

5. 環境変数設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動ロードされます（OS の環境変数を上書きする場合は `.env.local`）。
   - 自動ロードを無効化する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

---

## 主要な環境変数（主なもの）

- KABUSYS_ENV: 起動環境。`development` / `paper_trading` / `live`（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- LINE_CHANNEL_ACCESS_TOKEN: LINE 通知用トークン（任意）
- LINE_USER_ID: LINE 通知先ユーザ ID（任意）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の約定動作（instant|partial|never|reject。デフォルト: instant）
- PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: KillSwitch 用フラグファイル（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒。デフォルト: 60）

例（.env）
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_kabu_password
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
```

---

## 使い方

以下は基本的な実行方法の例です。パッケージがトップレベルのモジュールとしてインポート可能である前提（`python -m kabusys.run_execution` 等）。

- ExecutionEngine を起動（本番/テストに応じて KABUSYS_ENV を設定）
  ```
  # 例: 開発モード
  export KABUSYS_ENV=development
  python -m kabusys.run_execution
  ```

  - `KABUSYS_ENV=paper_trading` の場合、MockBrokerClient を使い `PAPER_TRADING_SQLITE_PATH` に記録します（本番 DB と分離）。

- Monitoring のポーリングループを起動
  ```
  # デフォルトは 60 秒間隔。MONITOR_POLL_INTERVAL で変更可能
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```

  - 監視は環境に関わらず（KABUSYS_ENV に依らず）本番 sqlite_path を使用してログを永続化します。

- Streamlit ダッシュボード（監視ビュー）
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- AI 機能（ニューススコア / レジーム判定）
  - `kabusys.ai.score_news(conn, target_date, api_key=None)` を呼ぶ。
  - `kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)` を呼ぶ。
  - どちらも OpenAI API キー（引数または環境変数）が必要です。API の失敗はフォールバック動作を行うよう設計されています。

---

## 実行時の挙動 / 運用上の注意

- Process priority: 起動時にプロセス優先度を "high" に設定します（psutil を利用）。権限により設定できない場合は警告でスキップされます。
- KillSwitch: 重大リスク（ドローダウン、ポジション上限等）でフラグファイル（デフォルト data/kill.flag）を書き込み、ExecutionEngine 起動時に検知して停止させる仕組みがあります。ExecutionEngine 起動時にフラグをクリアするオプション（Settings.kill_flag_clear_on_start）があります。
- DB
  - DuckDB: 時系列・ファクターデータ等の分析用（data/kabusys.duckdb）
  - SQLite (monitoring): 監視ログ（data/monitoring.db）
  - Paper trading 用には別 SQLite（data/paper_trading.db）を使い本番 DB と切り離します。
- 冪等性: 監視 DB 初期化（init_monitoring_db）は冪等です。マイグレーション処理（dashboard に peak_value カラム追加）も含まれます。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py — パッケージ定義（__version__）
- config.py — Settings クラス（.env 自動ロード、各種設定）
- run_execution.py — ExecutionEngine 起動スクリプト（__main__）
- run_monitoring.py — SystemMonitor（ポーリング）起動スクリプト
- utils/
  - process_priority.py — プロセス優先度・CPU affinity ユーティリティ
- execution/
  - execution_engine.py — ExecutionEngine（主制御）
  - order_manager.py — 発注状態管理
  - order_repository.py — （別ファイル）DB 永続化（Orders DB）
  - reconciler.py — 起動時リコンシリエーション
  - risk_manager.py — リスクチェック（設定は Engine 側で組立）
  - broker_factory.py / broker_api.py — ブローカー抽象と生成（Mock 実装等）
- monitoring/
  - monitoring_db.py — SQLite テーブル初期化 + MonitoringDB ラッパー
  - system_monitor.py — システム/データ鮮度監視
  - trade_monitor.py — 注文滞留・約定異常監視
  - risk_monitor.py — ドローダウン / ポジション上限監視
  - kill_switch.py — kill.flag 書き込み/管理
  - alert_manager.py — LINE 通知
  - monitoring_engine.py — 各 Monitor を束ねるポーリング実装
  - streamlit_dashboard.py — Streamlit での可視化
- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 株数決定・集約上限処理
  - risk_adjustment.py — セクター制限・レジーム乗数
- research/
  - factor_research.py — momentum/volatility/value の計算（DuckDB）
  - feature_exploration.py — forward returns / IC / 統計サマリ
- ai/
  - news_nlp.py — ニュースの LLM スコアリング（OpenAI）
  - regime_detector.py — ETF MA + マクロニュースでレジーム判定

（その他、execution 配下に broker 実装や order_record 等の補助モジュールがあります）

---

## 開発者向けメモ・注意点

- .env のパースは独自実装をしており、`.git` または `pyproject.toml` を基準にプロジェクトルートを自動検出します。テスト等で自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB クエリは大量データに対して最適化されており、時間ウィンドウや行数に注意してクエリを書いています（例: スキャン範囲にバッファを設ける等）。
- OpenAI API 呼び出しはリトライ・バックオフやレスポンス検証を行っていますが、API バージョンや戻りフォーマットの変更に備えてテスト時に API 呼び出し関数をモックできるよう設計されています。
- Execution のクラッシュ安全設計:
  - OrderSent 状態を永続化してから broker 呼び出しを行う など、途中クラッシュしても後で Reconciler により回復可能な設計になっています。
- Streamlit ダッシュボードは監視 DB を読み取り専用で開くことを推奨します（実行コマンドは README の通り）。

---

## ライセンス / 責務

この README はソースコードからの読み取りに基づく概要説明です。実運用する場合は各 API（kabuステーション、OpenAI、J-Quants 等）の利用規約・制限および金融規制に従ってください。

---

追加で README に記載したい運用例や CI/テスト手順、requirements.txt の生成など必要があれば教えてください。