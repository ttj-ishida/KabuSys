# KabuSys

日本株向け自動売買システム（ライブラリ部）。  
このリポジトリにはポートフォリオ構築、ポジションサイズ計算、ファクター/リサーチ、ニュースNLP（LLM）、市場レジーム判定、監視系（監視DB / アラート）、および発注エンジン周りの主要ロジックが実装されています。

## 概要
- モジュール群は「純粋関数」や「DB読み書き層」「APIクライアント層」に分離して実装されています。
- DuckDB を用いた時系列・財務データのファクター計算/リサーチ。
- OpenAI（gpt-4o-mini）を利用したニュースセンチメント評価（銘柄別）とマクロセンチメント評価を実装。
- SQLite（Monitoring DB）を用いた運用監視ログ（稼働状況・リスクイベント・トレードログ等）。
- ExecutionEngine / OrderManager による信頼性を考慮した発注ワークフロー、再同期（Reconciler）、監視（KillSwitch）などの運用機能。

## 主な機能一覧
- 環境変数管理（.env 自動読み込み、キー保護）
- ポートフォリオ候補選定・重み計算（等金額・スコア加重）
- セクター集中制限、レジームに応じた資金乗数
- ポジションサイズ計算（リスクベース、lot丸め、aggregate cap）
- ファクター計算（Momentum / Volatility / Value 等） — DuckDB 上で完結
- 将来リターン計算、IC（Information Coefficient）等の探索用ユーティリティ
- ニュースを LLM でスコアリングして ai_scores に書き込み
- マクロニュース + ETF MA に基づく市場レジーム判定と永続化
- 監視基盤（MonitoringDB, SystemMonitor, TradeMonitor, RiskMonitor, AlertManager）
- Streamlit ダッシュボード（監視情報表示）
- 発注フロー（OrderManager, ExecutionEngine）、ブローカー抽象化（BrokerAPI Protocol）
- 起動時リコンシリエーション（Reconciler）

## 動作前提 / 推奨環境
- Python 3.10 以上
- 主な外部依存ライブラリ:
  - duckdb
  - openai
  - psutil
  - requests
  - streamlit (ダッシュボード利用時)
  - sqlite3 は標準ライブラリ

例:
pip install duckdb openai psutil requests streamlit

（requirements.txt がある場合はそれを使用してください）

## セットアップ手順（ローカル開発向け）
1. リポジトリをクローン
2. 仮想環境作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要ライブラリをインストール
   - pip install duckdb openai psutil requests streamlit
4. 環境変数を設定
   - プロジェクトルートに `.env` として配置するか、OS の環境変数で設定します。
   - 自動読み込み：モジュール import 時にプロジェクトルート（.git または pyproject.toml の存在するディレクトリ）を探索し `.env` → `.env.local` の順で読み込みます。
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

### 主要な環境変数（抜粋）
- 必須（ライブラリの一部で _require() により必須扱い）
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン
  - KABU_API_PASSWORD — kabuステーション API パスワード
- AI / 外部 API
  - OPENAI_API_KEY — OpenAI 呼び出しに必要（news_nlp / regime_detector）
- 通知 / 監視
  - LINE_CHANNEL_ACCESS_TOKEN — AlertManager（LINE）用
  - LINE_USER_ID — 通知先 user id
- DB / ファイルパス（デフォルトあり）
  - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（Paper Trading 用 DB、デフォルト data/paper_trading.db）
  - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START
- 動作モード
  - KABUSYS_ENV — development | paper_trading | live（デフォルト development）
  - LOG_LEVEL — DEBUG | INFO | WARNING | ERROR | CRITICAL

（詳細は src/kabusys/config.py の Settings を参照してください）

## 使い方（代表的な例）

- 環境設定の利用
```python
from kabusys.config import settings
print(settings.kabu_api_base_url)
```

- DuckDB 接続してファクター計算（例: Momentum）
```python
import duckdb
from datetime import date
from kabusys.research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, date(2026, 3, 20))
# records は [{"date": ..., "code": "...", "mom_1m": ..., ...}, ...]
```

- OpenAI を用いたニューススコア付け（ai_scores テーブルへ書き込み）
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
count = score_news(conn, date(2026, 3, 20), api_key="sk-...")
```

- 市場レジーム判定（market_regime テーブルへ永続化）
```python
from kabusys.ai.regime_detector import score_regime
score_regime(conn, date(2026,3,20), api_key="sk-...")
```

- 監視 DB 初期化
```python
import sqlite3
from kabusys.monitoring.monitoring_db import init_monitoring_db

conn = sqlite3.connect("data/monitoring.db")
init_monitoring_db(conn)
```

- Streamlit ダッシュボード起動
```bash
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```

- ExecutionEngine の利用（概要）
  - 実運用では BrokerAPI の実装、OrderRepository（SQLite）、RiskManager、OrderManager、Reconciler を組み合わせて ExecutionEngine をインスタンス化し run_session() を呼びます。
  - このエンジンは PID / kill.flag の管理、WebSocket push の取り扱い、Gate1/2/3 による安全チェック、発注の永続化順序（クラッシュ耐性）などを実装しています。
  - 実行には本番ブローカークライアント実装が必要です。

## .env の取り扱い
- プロジェクトルートを基に自動で .env/.env.local を読み込みます（OS 環境変数が優先）。
- 読み込み優先順位:
  - OS 環境変数 → .env → .env.local（.env.local は上書き）
- 保護機能: OS 環境変数に既に存在するキーは .env / .env.local の上書き対象から保護されます。
- キーのパースはシェル互換（export KEY=..., 引用文字列、コメント扱い等）を考慮しています。

## 主要なディレクトリ構成
（抜粋、重要なモジュールのみ記載）

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュースを LLM でスコアリング
    - regime_detector.py           — 市場レジーム判定
  - portfolio/
    - __init__.py
    - portfolio_builder.py         — 候補選定・重み計算
    - position_sizing.py           — 株数計算・aggregate cap
    - risk_adjustment.py           — セクターキャップ、レジーム乗数
  - research/
    - __init__.py
    - factor_research.py           — Momentum/Volatility/Value 等
    - feature_exploration.py       — forward returns / IC / summary
  - monitoring/
    - __init__.py
    - monitoring_db.py             — SQLite スキーマ + MonitoringDB
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - alert_manager.py
    - kill_switch.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - execution/
    - broker_api.py                — ブローカープロトコル・データモデル・例外
    - order_manager.py             — 発注ワークフロー（DB 永続化を含む）
    - reconciler.py                — 起動時リコンシリエーション
    - execution_engine.py          — Signal Queue Pull 型発注エンジン
  - monitoring/ (監視系は上記)
  - portfolio/ (ポートフォリオ系は上記)
  - research/ (リサーチ系は上記)

（その他 data, strategy, execution など上位エクスポートが存在しますが、ここでは主要コンポーネントに絞っています）

## 運用上の注意 / 備考
- OpenAI キー未設定時、news_nlp.score_news / regime_detector.score_regime は ValueError を投げます。AI 機能を使わない場合は呼び出さないでください。
- ExecutionEngine は kill.flag・PID・DB 書き込み・外部ブローカー通信など多数の副作用を持つため、実運用前にモック・ステージングで十分な検証を行ってください。
- MonitoringDB のスキーマ変更時の簡単なマイグレーション処理（例: dashboard.peak_value の追加）を含んでいますが、大きなスキーマ改変には適切な移行手順を用意してください。
- 自動読み込みされる .env の挙動や Settings のプロパティ（値の検証）は src/kabusys/config.py を確認してください。

---

さらに詳しい利用例や運用手順は各モジュール内の docstring を参照してください。必要であれば README を特定ワークフロー（例: ローカルバックテスト、Paper Trading、Production のデプロイ手順）向けに拡張できます。どのワークフロー向けに追記しますか？