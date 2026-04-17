# KabuSys

KabuSys は日本株の自動売買システム（モジュール群）です。戦略の研究・ファクター計算、ポートフォリオ構築、発注エンジン、監視・アラート、Paper Trading 検証、LLM を使ったニュース NLP など、一連の機能をモジュール化して提供します。

以下はこのリポジトリの概要、主要機能、セットアップ方法、使い方、ディレクトリ構成の説明です。

---

## プロジェクト概要

- 目的：日本株向けの自動売買基盤を構築するためのライブラリ／ツール群。
- 構成：
  - execution：注文管理・ブローカークライアント・実行エンジン（ExecutionEngine）
  - monitoring：システム監視、アラート、ダッシュボード、Kill Switch（停止シグナル）
  - research：ファクター計算・特徴量探索ユーティリティ
  - portfolio：候補選定・配分・ポジションサイジング・セクター制限
  - ai：ニュース NLP（OpenAI）・レジーム判定
  - tools：Paper Trading 検証レポート等のユーティリティスクリプト
  - utils：プロセス優先度設定などのユーティリティ
  - data：ランタイムで使う DB / フラグ / pid ファイル（例: data/monitoring.db, data/paper_trading.db）
- 設計方針：
  - DuckDB/SQLite をデータ層に利用（分析/監視は読み書き専用）
  - 環境変数 / .env による設定管理（自動ロード機能あり）
  - Paper Trading と本番は DB を分離して安全に検証可能
  - LLM（OpenAI）呼び出しはリトライ・検証など堅牢化済み

---

## 主な機能一覧

- Execution（発注）
  - OrderManager / ExecutionEngine / Reconciler による発注管理と再起動時の同期（自動復旧）
  - BrokerClientFactory により実口座／Mock（paper_trading）を切り替え
  - リスク管理（RateLimit, 最大ポジション比率、ドローダウン等）

- Monitoring（監視）
  - SystemMonitor：CPU / メモリ / ディスク / プロセス生存 / データ鮮度を監視
  - TradeMonitor：滞留注文・約定価格異常の検出
  - RiskMonitor：ドローダウン・保有上限監視とリスクログ
  - KillSwitch：閾値超過時に data/kill.flag を書き込んで ExecutionEngine を停止
  - AlertManager：LINE Messaging API によるプッシュ通知
  - Streamlit ダッシュボード（監視情報の可視化）

- Research / Portfolio
  - ファクター計算（Momentum, Volatility, Value）
  - 将来リターン計算、IC 計算、統計サマリ
  - 銘柄選定、等配分・スコア加重配分、リスクベースのポジションサイジング
  - セクター集中制限・レジーム乗数

- AI（OpenAI）
  - news_nlp.score_news: raw_news を集約し LLM で銘柄別センチメントを算出して ai_scores に格納
  - regime_detector.score_regime: ETF（1321）の MA200 とマクロニュースの LLM センチメントを合成して市場レジームを判定・保存

- Tools
  - paper_verification_report: Paper Trading の検証レポートを生成（稼働率、注文成功率、レイテンシなど）

---

## 必要条件（想定）

- Python 3.9+（typing の union 演算子や path API を想定）
- 必要パッケージ（代表例）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボード利用時)
- OS: Linux / macOS / Windows（process priority の一部は OS に依存）

（プロジェクトに requirements.txt があればそちらを使用してください。なければ上記パッケージを pip で導入します）

例：
```
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install duckdb psutil requests openai streamlit
```

---

## 環境変数（主なもの）

このプロジェクトは .env/.env.local / 環境変数で設定を読み込みます（Settings クラス）。

重要な環境変数（抜粋）：

- JQUANTS_REFRESH_TOKEN — J-Quants API トークン（必須）
- KABU_API_PASSWORD — kabu API パスワード（必須）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY — OpenAI API キー（ai モジュール使用時）
- LINE_CHANNEL_ACCESS_TOKEN — LINE 通知用トークン（任意）
- LINE_USER_ID — LINE 通知先ユーザー ID（任意）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — Paper Trading の約定挙動（instant|partial|never|reject、デフォルト: instant）
- PID_FILE_PATH — ExecutionEngine の pid ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — KillSwitch が書き込むフラグ（デフォルト: data/kill.flag）
- KABUSYS_ENV — 環境 ("development" | "paper_trading" | "live")（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）

注意：
- 自動で .env をロードする機能があり、プロジェクトルートに .env/.env.local があればそれを読みます。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

---

## セットアップ手順（手順例）

1. リポジトリをクローンしてワークディレクトリへ移動
2. Python 仮想環境を作成・有効化
3. 必要パッケージをインストール（上記参照）
4. プロジェクトルートに .env を作成（.env.example を参照して必要なキーを設定）
   - 例: KABUSYS_ENV=paper_trading, OPENAI_API_KEY=..., KABU_API_PASSWORD=...
5. data ディレクトリを作る（実行時に自動作成される場合もある）
```
mkdir -p data
```
6. DuckDB / SQLite の初期化は多くの起動スクリプトで自動的に行われます（init_monitoring_db が呼び出されます）。Paper Trading 用 DB は data/paper_trading.db に自動で作成される想定です。

---

## 動かし方（代表的なコマンド）

- ExecutionEngine を起動（本番/ペーパーは KABUSYS_ENV に依存）
```
# パッケージを sys.path に通して実行可能であれば
python -m kabusys.run_execution

# またはスクリプトを直接指定
python src/kabusys/run_execution.py
```
- Monitoring を起動（監視ループ）
```
python -m kabusys.run_monitoring
# ポーリング間隔を上書きする場合:
MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
```
- Streamlit ダッシュボードを起動（監視 DB を指定する）
```
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```
- Paper Trading 検証レポートを生成
```
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-10
# DB を明示する場合:
python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
```
- AI 系（スコア計算）を直接呼ぶ（Python REPL / スクリプト内）
```
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
conn = duckdb.connect("data/kabusys.duckdb")
score_news(conn, date(2026,4,1), api_key="YOUR_OPENAI_KEY")
```
- レジーム判定
```
from kabusys.ai.regime_detector import score_regime
score_regime(conn, date(2026,4,1), api_key="YOUR_OPENAI_KEY")
```

停止／制御関連：
- 実行スクリプトはプロジェクトルートの data/stop_requested.flag を監視しており、ファイルが存在すると監視／実行ループを終了します。
- KillSwitch は data/kill.flag を書き込んで ExecutionEngine に停止指示を出します（Execution 側は KILL_FLAG_PATH を参照している設計）。
- PID ファイル: data/execution.pid に PID を書くことでプロセス生存チェックを行います。

---

## 注意点 / 運用メモ

- Paper Trading 環境（KABUSYS_ENV=paper_trading）はモックブローカーを使用し、DB を data/paper_trading.db に分離して運用します。実口座とデータを混ぜないための保護機構です。
- OpenAI を使うモジュールは API キーが必須です。API エラー時はフェイルセーフ（デフォルト値）で継続する部分があるものの、結果の信頼性を踏まえて運用してください。
- process priority 設定（set_process_priority）は OS 権限により失敗することがあります。ログに警告が出たら権限設定を確認してください。
- DuckDB / SQLite の書き込みは排他制御やバージョン差異（DuckDB の executemany の仕様等）に注意しています。DB のバックアップを定期的に行ってください。

---

## ディレクトリ構成（主要ファイルの説明）

- src/kabusys/
  - __init__.py — パッケージ定義
  - config.py — 環境変数/.env のロードと Settings クラス
  - run_execution.py — ExecutionEngine を起動するエントリポイント
  - run_monitoring.py — SystemMonitor をポーリング実行するエントリポイント

  - execution/
    - order_manager.py — 発注フロー（OrderManager）
    - reconciler.py — 再起動時の突合せ・リコンシリエーション
    - order_repository.py — 注文 DB レイヤ（SQLite、別ファイル群あり）
    - execution_engine.py — 実行エンジン（EngineConfig, run_session など）
    - broker_factory.py, broker_api.py など — ブローカー関連抽象化

  - monitoring/
    - monitoring_db.py — SQLite 監視ログの作成・CRUD
    - system_monitor.py — システム状態・データ鮮度チェック
    - trade_monitor.py — 注文滞留・約定異常検出
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 書き込みロジック
    - alert_manager.py — LINE 通知ラッパー
    - monitoring_engine.py — 各 Monitor を束ねるポーリングエンジン
    - streamlit_dashboard.py — Streamlit による監視ダッシュボード

  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 発注株数算出（リスク制限・単元丸め・スケーリング）
    - risk_adjustment.py — セクターキャップ・レジーム乗数

  - research/
    - factor_research.py — Momentum/Volatility/Value ファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン・IC・統計サマリ

  - ai/
    - news_nlp.py — raw_news を LLM で銘柄別スコア化して ai_scores に保存
    - regime_detector.py — MA200 と LLM マクロ評価を合成し market_regime を保存

  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成スクリプト

  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定ヘルパ

- data/ — ランタイムで使用する SQLite/DuckDB/フラグ/pid ファイル（例: data/monitoring.db, data/kabusys.duckdb, data/execution.pid, data/kill.flag）

---

## 開発者向けメモ

- 単体関数群（portfolio, research, ai 内の計算処理）は副作用が少なくテストしやすい構成を意識しています。ユニットテストを書く際は DuckDB のメモリ接続やモックを利用してください。
- .env のパースは本家 dotenv と異なる細かい挙動を実装しています（引用符・エスケープ・インラインコメントの扱い等）。必要なら .env を手動で整えてください。
- run_monitoring/run_execution は stop フラグ（data/stop_requested.flag）を監視して優雅に停止できます。手動停止用にファイルを作成してください。

---

もし README に追加したい内容（例：requirements.txt の正確な内容、デプロイ手順、systemd ユニットファイル例、CI 流れ、テストコマンドなど）があれば、必要な情報を教えてください。README をそれに合わせて拡張します。