# KabuSys

日本株向けの自動売買・リサーチ・監視フレームワーク（プロトタイプ）。  
主に以下の機能群を含み、SQLite / DuckDB をデータ永続化に使い、ブローカー呼び出しや LLM を組み合わせたワークフローを提供します。

- 実行エンジン（ExecutionEngine）
- 注文管理・リコンシリエーション
- ポートフォリオ構築（候補選定・重み付け・株数決定・リスク調整）
- 研究（ファクター計算、特徴量探索）
- AI モジュール（ニュースセンチメント、レジーム判定：OpenAI 使用）
- 監視（System / Trade / Risk モニタ、LINE 通知、Streamlit ダッシュボード）
- Paper Trading 用分離 DB と検証レポート生成ツール

---

## 機能一覧

- Execution
  - 注文生成 → ブローカー送信 → 状態同期（Reconciler による再起動後の復旧）
  - Risk Manager によるポジション制限・利用率制御
- Portfolio
  - シグナルから候補選定（スコア順）
  - 等分配／スコア加重／リスクベースのポジション決定、単元株丸め、セクター上限の適用
- Research
  - Momentum / Volatility / Value 等のファクター計算（DuckDB 上の prices_daily / raw_financials を参照）
  - 将来リターン計算、IC（Information Coefficient）等の解析ユーティリティ
- AI
  - ニュースを LLM（OpenAI）でスコア化して ai_scores に書き込み（バッチ送信・バックオフ対応）
  - マクロニュース + ETF MA200 による市場レジーム判定（market_regime テーブル）
- Monitoring
  - SystemMonitor：CPU/メモリ/ディスク/プロセス/データ鮮度の監視と履歴保存
  - TradeMonitor：滞留注文・約定異常の検出
  - RiskMonitor：ドローダウン・ポジション上限監視と kill.flag 出力
  - AlertManager：LINE Push による通知（クールダウン管理）
  - Streamlit ダッシュボード（監視情報の可視化）
- Tools
  - Paper Trading 検証レポート生成スクリプト（期間指定可）

---

## 必要条件

- Python 3.9+（型アノテーションや一部ライブラリの挙動を想定）
- OS: Linux / macOS / Windows（プロセス優先度設定はプラットフォーム依存で一部機能がスキップされます）
- 外部パッケージ（主なもの）:
  - duckdb
  - psutil
  - openai
  - requests
  - streamlit (ダッシュボードを利用する場合)

推奨：仮想環境（venv / pyenv / poetry 等）

---

## セットアップ手順

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成して有効化（任意）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows (PowerShell / CMD)
   ```

3. 依存パッケージをインストール
   - requirements.txt が無ければ以下を手動でインストールしてください：
     ```bash
     pip install duckdb psutil openai requests streamlit
     ```

4. データディレクトリを作成
   ```bash
   mkdir -p data
   ```

5. 環境変数設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（OS 環境変数が優先）。
   - 必須／重要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN — J-Quants API（必要な場合）
     - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
     - OPENAI_API_KEY — OpenAI を使う場合必須
   - 任意／デフォルト値あり:
     - KABUSYS_ENV — development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH — data/kabusys.duckdb（デフォルト）
     - SQLITE_PATH — data/monitoring.db（デフォルト）
     - PAPER_TRADING_SQLITE_PATH — data/paper_trading.db（paper_trading 用）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE通知用（未設定時は送信をスキップ）
     - PAPER_FILL_MODE — instant | partial | never | reject（paper_trading の約定挙動）
     - MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、デフォルト 60）
     - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START など

   例 .env（最小）
   ```
   KABUSYS_ENV=development
   KABU_API_PASSWORD=your_kabu_password
   OPENAI_API_KEY=sk-...
   ```

6. 初期 DB 作成
   - run_monitoring/run_execution 実行時に監視用テーブルは自動作成（init_monitoring_db）されます。
   - DuckDB 用のテーブル（prices_daily / raw_financials 等）は別途データ投入またはスキーマ準備が必要です。

---

## 使い方

### モニタリングの起動
SystemMonitor のポーリングループを起動します（監視ログは SQLite に保存されます）。
```bash
python -m kabusys.run_monitoring
# または
MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
```
注意:
- MONITOR_POLL_INTERVAL によりポーリング間隔（秒）を上書きできます（デフォルト 60）。
- 実行時にプロセス優先度を高く設定しようとします（psutil の権限に依存）。

### 実行エンジン（ExecutionEngine）の起動
日次セッションを開始しブローカーにアクセスします。
```bash
python -m kabusys.run_execution
```
- KABUSYS_ENV が `paper_trading` の場合、MockBrokerClient を使用し DB は `data/paper_trading.db` に格納されます（本番 DB と隔離）。
- 実行前に必要な環境変数（KABU_API_PASSWORD など）を設定してください。

### Paper Trading 検証レポート
Paper Trading の SQLite DB からサマリレポートを生成します。
```bash
# デフォルト DB を使う場合
python -m kabusys.tools.paper_verification_report

# 期間指定と DB 指定
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db
```

### Streamlit 監視ダッシュボード
監視 DB を読み取り専用で表示します（MonitoringEngine を先に起動してデータを作成してください）。
```bash
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```

### AI モジュール（プログラム経由）
OpenAI キーを環境変数または引数で渡して利用します。例（スクリプト内で利用）:
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
conn = duckdb.connect("data/kabusys.duckdb")
score_news(conn, date(2026, 4, 1), api_key="sk-...")
```
- API キー未設定時は ValueError が発生します。
- レート制限・一時エラーは指数バックオフでリトライします。失敗時はフェイルセーフでスキップ（ゼロフォールバック）する箇所があります。

---

## 主要設定（概要）

- KABUSYS_ENV: development | paper_trading | live
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必要なら）
- KABU_API_PASSWORD: kabu ステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
- DUCKDB_PATH: DuckDB ファイル（prices_daily / raw_financials 等）
- SQLITE_PATH: 監視 DB（monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（paper_trading）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用
- MONITOR_POLL_INTERVAL: 監視ループの秒間隔
- PID_FILE_PATH / KILL_FLAG_PATH: プロセス制御用ファイルパス

設定は .env / .env.local（プロジェクトルート）または環境変数で行えます。プロジェクトは起動時に自動で .env をロードします（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

---

## ディレクトリ構成（抜粋）

（主要ファイル・モジュールを抜粋して示します）

- src/kabusys/
  - __init__.py                — パッケージ定義（バージョン等）
  - config.py                  — 環境変数 / 設定管理（.env 読込含む）
  - run_monitoring.py          — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成 CLI
  - ai/
    - news_nlp.py              — ニュースの LLM センチメントスコアリング
    - regime_detector.py       — マクロ + MA による市場レジーム判定
  - research/
    - factor_research.py       — Momentum / Volatility / Value 等のファクター計算
    - feature_exploration.py   — 将来リターン計算、IC、統計サマリなど
  - portfolio/
    - portfolio_builder.py     — 候補選定・重み計算
    - position_sizing.py       — 株数決定・aggregate cap 管理
    - risk_adjustment.py       — セクター上限・レジーム乗数
  - monitoring/
    - monitoring_db.py         — SQLite 永続化（テーブル作成・操作）
    - system_monitor.py        — システム状態 / データ鮮度監視
    - trade_monitor.py         — 注文滞留・約定異常監視
    - risk_monitor.py          — ドローダウン・ポジション数監視
    - kill_switch.py           — kill.flag の作成 / 管理
    - alert_manager.py         — LINE 通知
    - monitoring_engine.py     — 複数 Monitor を束ねるエンジン
    - streamlit_dashboard.py   — Streamlit ベースの監視ダッシュボード
  - execution/
    - order_manager.py        — 注文ワークフロー管理
    - reconciler.py           — 起動時の注文 / ポジション照合
    - ... （ブローカーファクトリ、リスク管理、リポジトリ等）
  - utils/
    - process_priority.py     — プロセス優先度 / CPU affinity 設定ユーティリティ
  - data/（実行時生成 / 必要データ格納先）
    - kabusys.duckdb
    - monitoring.db
    - paper_trading.db

---

## 運用上の注意

- Paper Trading と Live は DB を分離しています（PAPER_TRADING_SQLITE_PATH を使用）。
- データ鮮度（prices_daily）の欠如は監視で検知されます。DuckDB の prices_daily テーブルに最新データが必要です。
- OpenAI 呼び出しは API 利用料が発生します。API キーと利用制限に注意してください。
- process priority / cpu affinity の設定は OS 権限に依存し、権限不足時は警告を出してスキップされます。
- kill.flag の存在は ExecutionEngine に停止シグナルを送るための簡易仕組みです。用途を理解した上で運用してください。
- SQLite / DuckDB のバックアップ・ローテーションを運用面でご検討ください。

---

この README はコードベースの主要機能と基本的な利用手順をまとめたものです。実行環境やブローカー連携・データ投入手順（prices_daily 等）については別途運用ドキュメントを作成することを推奨します。必要であれば README に追記すべき点（例えばサンプル .env.example、requirements.txt の生成、初期データ投入スクリプト等）を指示してください。