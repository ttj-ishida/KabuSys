# KabuSys

日本株向けの自動売買・研究・監視フレームワーク。  
モジュール設計により、発注実行（ExecutionEngine）、監視（MonitoringEngine）、ファクター計算、ポートフォリオ構築、AI（ニュースセンチメント・レジーム判定）などの機能を個別に利用・検証できます。

以下はこのリポジトリに含まれる主要な機能、セットアップ手順、使い方、ディレクトリ構成の概要です。

---

## プロジェクト概要

- 発注エンジン（ExecutionEngine）とブローカークライアントの抽象化により、本番（kabuステーション連携）および Paper Trading（モックブローカー、専用DB）を切り替え可能。
- 監視コンポーネントでプロセス生存・リソース使用率・データ鮮度・注文の異常検出・ドローダウン等を継続的に記録・通知。
- DuckDB を用いた研究向けファクタ計算（モメンタム・ボラティリティ・バリュー等）や特徴量探索ツール群を提供。
- OpenAI API を利用したニュースセンチメント（ai.score_news）および市場レジーム判定（ai.score_regime）機能を搭載（APIキー利用）。
- Streamlit ベースの監視ダッシュボードを提供（読み取り専用モードで SQLite の監視DBを参照）。

---

## 主な機能一覧

- Execution
  - 起動スクリプト: src/kabusys/run_execution.py
  - BrokerClientFactory による本番/ペーパートレード切替
  - OrderManager / OrderRepository / Reconciler（起動時自動復旧）

- Monitoring
  - 起動スクリプト: src/kabusys/run_monitoring.py
  - SystemMonitor: CPU/メモリ/Disk・データ鮮度・プロセス監視
  - TradeMonitor: 滞留注文・約定異常価格検出
  - RiskMonitor: ドローダウン・ポジション上限監視
  - KillSwitch: 停止フラグの書き込みによる ExecutionEngine 停止
  - AlertManager: LINE Push による通知
  - Streamlit ダッシュボード: src/kabusys/monitoring/streamlit_dashboard.py

- Research / Portfolio
  - ファクター計算: src/kabusys/research/factor_research.py
  - 特徴量探索 / IC 計算等: src/kabusys/research/feature_exploration.py
  - ポートフォリオ構築: select_candidates, weight 計算（score/equal）
  - ポジションサイズ計算・セクター制約・レジーム乗数

- AI
  - news_nlp: OpenAI を用いたニュースの銘柄別スコアリング（ai_scores）
  - regime_detector: ETF MA とマクロニュースを合成した市場レジーム判定

- ユーティリティ
  - 設定ロード（.env 自動読み込み）: src/kabusys/config.py
  - プロセス優先度 / CPU affinity ユーティリティ: src/kabusys/utils/process_priority.py
  - 各種 DB 初期化 / 永続化層（monitoring_db）

- ツール
  - Paper Trading 検証レポート生成スクリプト: src/kabusys/tools/paper_verification_report.py

---

## 前提 / 推奨環境

- Python 3.10 以上（PEP 604 の型記法等を使用）
- システム依存ライブラリ（例: psutil の動作によりプラットフォーム差あり）
- 必要な Python パッケージ（例）
  - duckdb
  - psutil
  - openai
  - requests
  - streamlit
- SQLite / DuckDB を利用（SQLite は標準ライブラリに含まれる）

インストール例（venv 推奨）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai requests streamlit
```
（requirements.txt がある場合は `pip install -r requirements.txt` を推奨）

---

## 環境変数（主なもの）

Settings クラスは .env / .env.local / OS環境変数から値をロードします。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

重要な変数（抜粋）:
- KABUSYS_ENV: 起動環境。development / paper_trading / live（既定: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須となる箇所あり）
- KABU_API_PASSWORD: kabuステーション API パスワード（本番連携時）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector 用）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用（省略時は通知スキップ）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の約定挙動（instant|partial|never|reject、デフォルト: instant）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト: 60）
- PID_FILE_PATH / KILL_FLAG_PATH: 各種フラグ・PID ファイルパス
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）

注意:
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われます。
- .env.local は .env の上書き（OS 環境変数は保護される）。

---

## セットアップ手順（簡易）

1. リポジトリをクローン
2. 仮想環境を作成して依存パッケージをインストール（上記参照）
3. data ディレクトリを作成（必要なら）
   ```
   mkdir -p data
   ```
4. .env を作成（例: .env.example を参照）して必須値を設定
5. DuckDB / SQLite DB 初期化は各起動スクリプトが必要に応じて行います（監視DBは init_monitoring_db が自動作成）

---

## 使い方（実行例・コマンド）

- 監視ループを起動（デフォルト MONITOR_POLL_INTERVAL=60 秒）
```
python src/kabusys/run_monitoring.py
```
- ポーリング間隔を変更:
```
MONITOR_POLL_INTERVAL=30 python src/kabusys/run_monitoring.py
```
- Execution エンジンを起動（本番 / paper_trading は KABUSYS_ENV に依存）
  - 本番（デフォルト development -> live に設定して本番動作）
```
KABUSYS_ENV=live python src/kabusys/run_execution.py
```
  - Paper Trading（MockBroker を使用し、PAPER_TRADING_SQLITE_PATH に記録）
```
KABUSYS_ENV=paper_trading python src/kabusys/run_execution.py
```

- Paper Trading 検証レポート生成
```
python -m kabusys.tools.paper_verification_report
# 日付範囲指定
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# DB パス指定
python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
```

- Streamlit ダッシュボード（監視DB を読み取り専用で表示）
```
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```

- AI スコアリング / レジーム判定（ライブラリ API として利用）
  - news_nlp.score_news, regime_detector.score_regime を直接呼ぶ（DuckDB 接続を渡す）
  - OpenAI キーは引数で渡すか、環境変数 OPENAI_API_KEY を設定

- 停止方法（ExecutionEngine の停止）
  - kill flag を設定（KillSwitch が評価しているパスにファイルを作成）
  - もしくはプロセスを直接 kill
  - run_* スクリプトは data/stop_requested.flag の存在も検出して自発終了する実装あり

---

## 運用上の注意

- Monitoring は常に（KABUSYS_ENV にかかわらず）本番用 sqlite_path を利用して監視ログを記録します。Paper Trading の注文ログは PAPER_TRADING_SQLITE_PATH に分離されます。
- run_execution は起動時に stop flag が既に存在する場合、起動せず終了する保護機構を持っています。
- Run スクリプト起動直後にプロセス優先度を "high" に設定する試みを行いますが、権限不足等で失敗することがあります（ログ警告のみ）。
- OpenAI など外部 API 呼び出しはリトライやフェイルセーフ（失敗時のフォールバック）を備えていますが、APIキー管理やレート制限に注意してください。
- .env の自動ロードはプロジェクトルートの検出に基づきます。テスト等で自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数/設定の集中管理
  - run_execution.py          — ExecutionEngine 起動用スクリプト
  - run_monitoring.py         — Monitoring 起動用スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - utils/
    - process_priority.py      — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py         — SQLite による監視ログ永続化層
    - system_monitor.py        — CPU/メモリ/Disk/プロセス/データ鮮度監視
    - trade_monitor.py         — 注文滞留・約定価格異常検出
    - risk_monitor.py          — ドローダウン・ポジション上限監視
    - kill_switch.py           — 停止フラグ書き込みユーティリティ
    - alert_manager.py         — LINE Push 通知
    - monitoring_engine.py     — 各 Monitor を束ねる実行ループ
    - streamlit_dashboard.py   — Streamlit 監視ダッシュボード
  - execution/
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - execution_engine.py      — 実行エンジン（起動・セッション管理）
    - broker_factory.py
    - broker_api.py
    - ...（OrderRecord 等）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py              — ニュースセンチメントスコアリング（OpenAI）
    - regime_detector.py       — 市場レジーム判定（ETF MA + マクロニュース）
  - data/                     — 実行時に使う DB / フラグファイル（git 管理対象外推奨）

---

## 開発・拡張ポイント（メモ）

- position_sizing や portfolio_builder は純粋関数群でユニットテストが書きやすい設計です。
- ai モジュールには OpenAI 呼び出し箇所が集約されていて、テスト時はそれらをモック可能です（コード内で案内あり）。
- monitoring_db はスキーママイグレーションを最低限サポート（列追加を自動実行する処理あり）。
- streamlit ダッシュボードは読み取り専用 URI を使って安全に監視DBを表示します。

---

README に書かれている以外の細かな仕様や API の使い方は各モジュールの docstring を参照してください。必要であれば README に含める具体的な例（環境変数テンプレート、systemd 用ユニットファイル例、CI/テスト方法など）を追加で作成します。どの情報を優先して追加しますか？