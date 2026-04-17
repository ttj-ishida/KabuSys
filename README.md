# KabuSys

日本株自動売買システムの一部（モニタリング、エンジン起動、ポートフォリオ構築、リサーチ、AI連携ツール等）。  
このリポジトリは、取引エンジンの実行管理・監視・検証・研究ツール群を含みます。

## 概要
- ExecutionEngine（発注実行）の起動スクリプトと補助コンポーネント（OrderManager / Reconciler / RiskManager 等）
- Monitoring（システム稼働監視、注文異常検出、リスク監視、Alert通知）
- Portfolio 構築ユーティリティ（候補選定、重み計算、サイズ決定）
- Research 用ファクター計算・特徴量探索モジュール（DuckDB を使った処理）
- AI モジュール（ニュース NLP によるセンチメント、レジーム判定）
- 運用補助ツール（Paper Trading 検証レポート、Streamlit ダッシュボード）

設計上の特徴：
- 設定は環境変数および .env/.env.local から読み込む（自動読み込み、Settings クラス）
- Paper Trading（KABUSYS_ENV=paper_trading）は本番 DB と分離（data/paper_trading.db）
- OpenAI 連携は明示的に API キーが必要（環境変数または引数で指定）
- モジュールは副作用を最小化し、DB 初期化やマイグレーションを冪等に実行

---

## 主な機能一覧
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動・監視（KABUSYS_ENV により paper/live を切替）
  - run_monitoring.py: SystemMonitor のポーリングループ（監視ログを SQLite に保存）
- モニタリング
  - SystemMonitor: CPU/メモリ/Disk、実行プロセス存在確認、価格データ鮮度確認
  - TradeMonitor: 滞留注文・約定価格異常を検出
  - RiskMonitor: ドローダウン、ポジション上限を監視（ダッシュボード更新 / リスクログ）
  - MonitoringEngine: 上記モニタをまとめてポーリング、KillSwitch/AlertManager と連携
  - AlertManager: LINE プッシュ通知（クールダウン管理）
  - KillSwitch: 条件に応じて data/kill.flag を書き込み Execution 停止をトリガー
  - Streamlit ダッシュボード（監視情報の可視化）
- Execution サブシステム
  - OrderManager, OrderRepository, Reconciler, RiskManager（発注・同期・復旧ロジック）
- ポートフォリオ構築
  - 候補選定（select_candidates）、重み付け（equal/score）、単元丸め／サイズ算出（calc_position_sizes）
  - セクターキャップ・レジーム乗数
- Research（DuckDB）
  - ファクター計算（momentum/value/volatility）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ
- AI
  - news_nlp.score_news: raw_news を LLM でスコア化して ai_scores に書き込み
  - regime_detector.score_regime: ma200 とマクロセンチメントの合成で市場レジーム判定
- 運用ツール
  - tools/paper_verification_report.py: Paper Trading DB から検証レポート生成

---

## 必要要件（概略）
- Python 3.10+
- 主要依存パッケージ（例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（ダッシュボード使用時）
- SQLite（標準ライブラリに同梱）
- ネットワークアクセス（LINE API / OpenAI 利用時）

インストール例:
```bash
python -m pip install -U pip
python -m pip install duckdb psutil requests openai streamlit
```
（プロジェクトに requirements.txt / pyproject.toml がある場合はそれに従ってください）

---

## セットアップ手順（ローカル運用）
1. リポジトリをチェックアウト
2. Python 仮想環境を作成して有効化
3. 依存ライブラリをインストール（上記参照）
4. 環境変数を設定（.env/.env.local をプロジェクトルートに置くか、OS 環境変数を利用）
   - 重要（必須）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - よく使う設定例 / デフォルト:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - SQLITE_PATH: data/monitoring.db（Monitoring 用 DB）
     - DUCKDB_PATH: data/kabusys.duckdb
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）
     - OPENAI_API_KEY: OpenAI API キー（AI モジュール使用時）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager 用
     - LOG_LEVEL: DEBUG | INFO | ...
     - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、run_monitoring で参照）
5. データディレクトリ作成:
```bash
mkdir -p data
```
（初回起動で DB 初期化が行われます）

注意: src レイアウトを直接実行する場合は PYTHONPATH を通すか、パッケージを editable インストールしてください:
```bash
# プロジェクトルートで
python -m pip install -e .
# または
export PYTHONPATH=./src:$PYTHONPATH
```

---

## 使い方（実行例）

- ExecutionEngine を起動（通常 / paper_trading 切替）
```bash
# 本番っぽく起動（KABUSYS_ENV=live とする場合は注意して）
export KABUSYS_ENV=live
python -m kabusys.run_execution

# Paper Trading（ブローカーは Mock を使用し、data/paper_trading.db に記録）
export KABUSYS_ENV=paper_trading
python -m kabusys.run_execution
```
代替: ファイルを直接実行する場合（PYTHONPATH に注意）
```bash
python src/kabusys/run_execution.py
```

- Monitoring（SystemMonitor のポーリング）
```bash
# ポーリング間隔は MONITOR_POLL_INTERVAL で上書き可能（秒）
export MONITOR_POLL_INTERVAL=30
python -m kabusys.run_monitoring
```

- Streamlit ダッシュボード
```bash
# デフォルト DB: data/monitoring.db を読み取り専用で開く
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```

- Paper Trading 検証レポート生成
```bash
# 指定期間のレポート（DB パスは --db または PAPER_TRADING_SQLITE_PATH 環境変数で指定）
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db
```

- AI スコアリング / レジーム判定（ライブラリ API として使用）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
n = score_news(conn, target_date=date(2026,4,10), api_key="sk-...")
r = score_regime(conn, target_date=date(2026,4,10), api_key="sk-...")
```

- 強制停止 / 停止フラグ
  - モニタリング・エンジンのポーリングループはプロジェクトルート/data/stop_requested.flag の存在を検知してループを終了します（run_execution/run_monitoring）。
  - KillSwitch により data/kill.flag が書き込まれると ExecutionEngine 側で停止シグナルとして扱う運用設計です。KillSwitch クラスは条件に応じて自動で書き込みます。
  - フラグ削除:
```bash
rm -f data/stop_requested.flag data/kill.flag
```

---

## 環境変数（主なもの）
- KABUSYS_ENV: development | paper_trading | live（default: development）
- SQLITE_PATH: monitoring DB（default: data/monitoring.db）
- DUCKDB_PATH: prices / research 用 duckdb（default: data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 専用 DB（default: data/paper_trading.db）
- PAPER_FILL_MODE: instant | partial | never | reject（default: instant）
- OPENAI_API_KEY: OpenAI API Key（AI モジュール使用時必須）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START: 実行管理に関連

Settings クラス（kabusys.config.Settings）で多くの設定値とバリデーションを管理しています。`.env.example` を参考に .env を作成してください。

---

## ディレクトリ構成（主要ファイル）
（src をルートとして記載）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env 読み込みと Settings
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポートスクリプト
  - monitoring/
    - __init__.py
    - monitoring_db.py       — SQLite スキーマ / DB 層
    - monitoring_engine.py   — 各 Monitor を束ねる
    - system_monitor.py      — CPU/Memory/Disk/データ鮮度/プロセス監視
    - trade_monitor.py       — 注文滞留・異常約定検出
    - risk_monitor.py        — ドローダウン・ポジション上限
    - kill_switch.py         — フラグ書き込みによる停止トリガー
    - alert_manager.py       — LINE 通知
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - execution/
    - order_manager.py
    - reconciler.py
    - ... （OrderRepository, EngineConfig 等が存在）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py            — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py     — 市場レジーム判定（ma200 + マクロセンチメント）
    - __init__.py
  - utils/
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
    - __init__.py
  - data/                    — 実行時に生成される（DB, pid, flag など）

（上記は主要ファイル群の抜粋です。細かい実装は各モジュールを参照してください。）

---

## 運用上の注意 / ベストプラクティス
- KABUSYS_ENV により挙動（特にブローカーと DB パス）が変わります。実運用時は live と paper_trading を混同しないよう注意してください。
- Paper Trading は本番 DB と完全分離されています（デフォルト: data/paper_trading.db）。
- OpenAI API を使う処理は外部請求が発生します。API キー管理とコストに注意ください。テストでは API 呼び出し関数をモック可能（ユニットテスト想定）。
- run_execution / run_monitoring は起動直後にプロセス優先度を上げようとします（プラットフォーム差分は psutil で吸収）。権限不足だと警告でスキップされます。
- 監視ループ / エンジンはそれぞれ data/stop_requested.flag の存在を検知して終了します。Graceful shutdown を行うためにこのフラグを使ってください。
- DB スキーマは init_monitoring_db() により冪等で作成／マイグレーションされますが、バックアップは適宜取得してください。

---

## 開発者向けメモ
- DuckDB を利用したリサーチ・AI モジュールは外部 API を使わず DB 内で完結する設計です（ただしニュースセンチメント等は外部 LLM を利用します）。
- テストしやすいように外部 API 呼び出し (_call_openai_api 等) をパッチすることでユニットテスト化が容易です。
- Settings._find_project_root() は .git または pyproject.toml を基準にプロジェクトルートを検出します。パッケージ配布後も動作するよう設計済みです。

---

必要であれば以下を追記できます：
- 具体的な .env.example（サンプル）
- systemd / supervisor 用のサービスユニット例
- 詳細な DB スキーマ定義（テーブル説明）  
ご希望があれば追記します。