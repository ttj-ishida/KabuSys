# KabuSys

日本株自動売買システムのモジュール群。ポートフォリオ構築、発注/リコンシリエーション、監視、研究/ファクター計算、AI を使ったニュースセンチメント評価などを含みます。

---

## プロジェクト概要

KabuSys は、以下の主要コンポーネントで構成される自動売買プラットフォームです。

- ExecutionEngine：ブローカーとやり取りして注文を作成・管理する実行エンジン
- Monitoring：システム状態、注文滞留、ドローダウン等の監視とアラート
- Portfolio construction：シグナルに基づく候補選定、重み付け、株数決定
- Research：DuckDB を使ったファクター計算・特徴量解析ユーティリティ
- AI：OpenAI を利用したニュースセンチメント評価 / 市場レジーム判定
- Tools：Paper Trading 検証レポート生成、Streamlit ダッシュボードなど

設計方針の一部：
- DuckDB / SQLite によるローカル DB 保持（本番 DB と paper_trading は分離）
- 外部 API 呼び出し（ブローカー / OpenAI 等）は明示的に扱う（フェイルセーフ有り）
- ルックアヘッドバイアス対策（日時参照の扱いに注意）

---

## 主な機能一覧

- システム監視（CPU/メモリ/ディスク、プロセス生存、データ鮮度）
- 注文監視（滞留注文、約定価格の異常検出）
- リスク監視（ドローダウン、ポジション数上限）
- Kill Switch（条件を満たしたらフラグを書き込み ExecutionEngine を停止）
- LINE によるアラート送信（AlertManager）
- ExecutionEngine の起動・停止制御、再起動時のリコンシリエーション
- Portfolio 創出（候補抽出・等重/スコア重み・株数決定・セクター制約）
- Research：モメンタム・ボラティリティ・バリュー等のファクター計算、IC / 統計サマリ
- AI：ニュースを LLM（gpt-4o-mini）でスコアリングし ai_scores に保存
- Paper Trading 用の検証レポート生成スクリプト
- Streamlit による監視ダッシュボード

---

## 前提条件（開発環境の例）

- Python 3.10+
- 必要パッケージ（例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボード利用時)
  - その他（標準ライブラリの sqlite3 等）

推奨：仮想環境を作成して依存をインストールしてください。

例：
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil requests openai streamlit
```

（実運用では requirements.txt を用意して pip install -r することを推奨します）

---

## セットアップ手順

1. ソースをクローン／配置
2. 仮想環境を作成して依存をインストール（上記参照）
3. data ディレクトリ等の作成（必要に応じて）
   - `data/` はデフォルトの SQLite / DuckDB / pid/flag を置く場所
4. 環境変数を用意（.env または環境変数）
   - 自動で .env / .env.local をプロジェクトルートから読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）
5. DB 初期化は各起動スクリプトで行われます（init_monitoring_db が冪等で DB スキーマを作成）

---

## 重要な環境変数（主なもの）

- KABUSYS_ENV: "development" | "paper_trading" | "live"（デフォルト: development）
  - paper_trading 時は ExecutionEngine は MockBroker を利用し、Paper 用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録します
- JQUANTS_REFRESH_TOKEN: （必須）J-Quants API トークン
- KABU_API_PASSWORD: （必須）kabuステーション API パスワード
- OPENAI_API_KEY: OpenAI を利用する機能で必要（news_nlp / regime_detector）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知のため（未設定時は送信をスキップ）
- SQLITE_PATH: 監視 DB（monitoring.db）のパス（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB のファイルパス（デフォルト: data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の約定挙動（instant/partial/never/reject）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒。デフォルト 60）
- PID_FILE_PATH / KILL_FLAG_PATH 等は監視設定で使用

.env の例（最低限の必須値）:
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=...
KABU_API_PASSWORD=...
OPENAI_API_KEY=...
```

---

## データディレクトリとフラグファイル

- data/monitoring.db (デフォルト): 監視ログ（system_status / trade_logs / positions / risk_logs / dashboard）
- data/paper_trading.db: paper_trading 時の発注履歴（本番 DB と分離）
- data/execution.pid: 実行エンジンの PID（存在しない／stale を検出すると警告）
- data/kill.flag: KillSwitch が書き込む停止フラグ。ExecutionEngine 起動時に削除するオプション有り
- data/stop_requested.flag: run_* スクリプトが監視して停止するための外部停止フラグ

注意：
- monitoring は KABUSYS_ENV にかかわらず「本番 sqlite_path（SQLITE_PATH）」を使用します（監視 DB は一貫した参照先を想定）。
- paper_trading の発注記録は PAPER_TRADING_SQLITE_PATH に出力され、本番 DB と完全に分離されます。

---

## 実行方法（主なスクリプト）

- 監視ループ起動（SystemMonitor 単体）
```bash
python -m kabusys.run_monitoring
# MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（秒、デフォルト 60）
```

- 実行エンジン起動（ExecutionEngine）
```bash
# 本番/開発/ペーパートレードは KABUSYS_ENV で切替
KABUSYS_ENV=paper_trading python -m kabusys.run_execution
# paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db に記録されます
```

- Streamlit ダッシュボード（監視 DB の可視化）
```bash
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```

- Paper Trading 検証レポート生成（コマンドライン）
```bash
# デフォルト DB: data/paper_trading.db
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# --db オプションで別 DB を指定可能
```

- プログラム的に AI スコアリングを実行（例）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
score_news(conn, target_date=date(2026,4,1), api_key="YOUR_OPENAI_KEY")
```

- 市場レジーム評価（programmatic）
```python
from kabusys.ai.regime_detector import score_regime
# DuckDB 接続と target_date を渡して実行
```

---

## 運用上の注意・補足

- プロセス優先度設定：run_monitoring / run_execution は起動時に set_process_priority("high") を試みます。psutil による権限エラーは警告して処理を継続します。
- Kill Switch：RiskMonitor が条件を満たすと KillSwitch が data/kill.flag を書き込み、ExecutionEngine 側がこれを検知して停止します（冪等・理由付き）。
- DB マイグレーション：monitoring_db.init_monitoring_db は冪等でスキーマを作成・簡易マイグレーション（列追加）を行います。
- Paper Trading：実運用のブローカーと本番 DB を混在させないために paper_trading モードを用意しています。動作確認には paper_trading を推奨します。
- OpenAI API：429・ネットワーク断・タイムアウト・5xx は指数バックオフでリトライする実装がありますが、API キーの管理とコストに注意してください。

---

## 開発者向け / テスト

- 各コンポーネントはモジュールとしてインポートして単体テストしやすく設計されています（例：MonitoringEngine.run_once、RiskMonitor.check_once、portfolio 関数群は純粋関数）。
- OpenAI 呼び出し部分はテストでモック可能（内部で呼んでいる _call_openai_api をパッチする設計）。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）から行われます。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して自動ロードを無効にできます。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下の主要ファイルを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                         — 環境変数 / Settings 管理
  - run_monitoring.py                 — SystemMonitor ポーリング起動スクリプト
  - run_execution.py                  — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py    — paper_trading 検証レポート CLI
  - monitoring/
    - monitoring_db.py                — monitoring DB 層（SQLite）
    - system_monitor.py               — システム・データ鮮度監視
    - trade_monitor.py                — 注文滞留・約定異常監視
    - risk_monitor.py                 — ドローダウン／ポジション上限監視
    - kill_switch.py                  — Kill Switch（flag ファイル操作）
    - alert_manager.py                — LINE プッシュ通知
    - monitoring_engine.py            — 各 Monitor を束ねるエンジン
    - streamlit_dashboard.py          — Streamlit ダッシュボード
  - execution/
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - execution_engine.py
    - broker_factory.py
    - ... (注文関連ロジック)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py                      — ニュースセンチメント（OpenAI）
    - regime_detector.py               — 市場レジーム判定（ML + MA）
  - data/ (ランタイムで使用される想定ディレクトリ)
    - monitoring.db
    - paper_trading.db
    - kabusys.duckdb
    - execution.pid
    - kill.flag
    - stop_requested.flag

---

## ライセンス / 貢献

（このリポジトリ内に LICENSE があれば追記してください）

貢献は PR と Issue を通じてお願いします。設計・安全性・運用面に関する議論歓迎です。

---

もし README に追加したいスクリーンショット、サンプル .env.example、requirements.txt のテンプレート、あるいは具体的な運用手順（systemd ユニット例、Dockerfile など）が必要であれば教えてください。必要に応じて追記・整形します。