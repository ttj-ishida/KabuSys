# KabuSys — 日本株自動売買フレームワーク

このリポジトリは日本株向けの自動売買 / リサーチ基盤「KabuSys」の一部（コアモジュール群）です。  
モジュールは可能な限り「純粋関数」「DB/外部API呼び出しを分離」した設計を志向しており、バックテスト・リサーチ・本番発注・監視までのワークフローを想定しています。

## 概要
KabuSys は以下の責務を持つモジュール群で構成されています（抜粋）:
- 環境設定読み込み（.env サポート）
- ポートフォリオ構築（候補選定、重み付け、株数算出）
- ファクター / ファーチャーリサーチ（DuckDB ベース）
- ニュースの LLM（OpenAI）センチメントスコアリング
- 市場レジーム判定（ETF + マクロニュース + LLM）
- 実行エンジン（Order 管理、Reconciliation、KillSwitch）
- 監視機能（System / Trade / Risk の監視、LINE 通知、Streamlit ダッシュボード）
- SQLite / DuckDB への永続化用ユーティリティ

各コンポーネントはなるべく副作用を限定し、テストしやすいように設計されています。

## 主な機能一覧
- 環境変数・.env 自動読み込み（プロジェクトルート検出）
- ポートフォリオ関連
  - シグナル選定（選出上位 N）
  - 等金額 / スコア重み配分
  - リスクベースのポジションサイズ算出（単元丸め・集約上限対応）
  - セクターキャップ適用、レジーム乗数
- リサーチ
  - Momentum / Volatility / Value 等のファクター計算（DuckDB）
  - 将来リターン計算、IC（スピアマン）計算、統計サマリー
- AI（OpenAI）連携
  - ニュースをまとめて LLM に送り銘柄別センチメントを ai_scores テーブルへ書き込み
  - 市場レジーム判定（ETF MA + マクロニュース + LLM）
  - 再試行・エラー耐性・レスポンス検証ロジック付き
- Execution（発注）
  - OrderState マシンと DB 永続化（クラッシュ安全性を考慮した二相永続化）
  - Reconciler による再起動時の自動同期
  - Push ドレイン / KillSwitch / Gate チェックによる安全停止
- Monitoring
  - SQLite ベースの監視 DB（system_status, trade_logs, positions, risk_logs, dashboard）
  - System / Trade / Risk の監視ロジックとアラート
  - LINE Push 通知（cooldown 管理）
  - Streamlit ダッシュボードで可視化

## セットアップ手順（開発向け・簡易）
以下はローカルで動かすための最小手順の例です。

1. Python（推奨: 3.10+）を用意
2. リポジトリをクローンしてソースツリーに移動
3. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
4. 依存ライブラリをインストール（必要に応じて pyproject.toml / requirements.txt を用意してください）
   - pip install duckdb openai requests psutil streamlit
   - （テスト用: pytest 等を追加）
5. 環境変数を用意
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` / `.env.local` を置くと、自動的にロードされます（優先度: OS環境 > .env.local > .env）。
   - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

### 主要な環境変数（抜粋）
必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API 用パスワード
（OpenAI 関連は score_news / score_regime 呼び出し時に api_key 引数で渡すことも可）

任意 / 推奨:
- OPENAI_API_KEY — OpenAI API キー（ai.score_news / regime 判定で使用）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — 監視アラート送信用（未設定でも動作）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB パス（デフォルト: data/monitoring.db）
- PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH — Paper trading の設定
- KABUSYS_ENV (development | paper_trading | live)
- LOG_LEVEL (DEBUG | INFO | ...)

サンプル .env（プロジェクトルートに配置）:
```
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_kabu_password
OPENAI_API_KEY=sk-...
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

## 使い方（代表的な例）

- DuckDB を使ったファクター計算（リサーチ）
```python
import duckdb
from datetime import date
from kabusys.research import calc_momentum, calc_volatility, calc_value

conn = duckdb.connect("data/kabusys.duckdb")
target = date(2026, 3, 20)
mom = calc_momentum(conn, target)
vol = calc_volatility(conn, target)
val = calc_value(conn, target)
```

- OpenAI を使ったニューススコアリング（ai_scores への書き込み）
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, date(2026, 3, 20), api_key="sk-...")
print(f"書き込み件数: {n_written}")
```

- 市場レジーム判定（score_regime）
```python
from kabusys.ai.regime_detector import score_regime
# duckdb_conn を渡し、target_date と api_key を指定
score_regime(duckdb_conn, date(2026, 3, 20), api_key="sk-...")
```

- 監視 DB 初期化と Streamlit ダッシュボード起動
```python
import sqlite3
from kabusys.monitoring.monitoring_db import init_monitoring_db

conn = sqlite3.connect("data/monitoring.db")
init_monitoring_db(conn)
# ダッシュボードはコマンドラインから起動:
# streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```

- ExecutionEngine の起動（本番では各実装（broker, repo, risk_manager, order_manager）を組み合わせて使用）
  - ExecutionEngine は多くの依存（BrokerAPI 実装、OrderRepository、RiskManager など）を注入する設計です。単体テスト時はモックを渡して run_session / run_once を実行してください。

## 自動 .env 読み込みの挙動
- プロジェクトルートはこのパッケージのファイル位置（__file__）を起点に `.git` または `pyproject.toml` を見て探索します。見つからない場合は自動読み込みをスキップします。
- 読み込み順序:
  1. OS 環境変数（既に存在するキーは保護される）
  2. .env （override=False: OS 環境に無いキーのみ設定）
  3. .env.local（override=True: .env の値を上書き。ただし OS 環境のキーは保護される）
- 自動ロードを完全に無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

## ディレクトリ構成（主要ファイル・モジュール）
- src/kabusys/
  - __init__.py — パッケージ定義
  - config.py — 環境変数 / .env 読み込みと Settings クラス
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算（select_candidates, calc_equal_weights, calc_score_weights）
    - position_sizing.py — 株数計算（calc_position_sizes）
    - risk_adjustment.py — セクターキャップ・レジーム乗数（apply_sector_cap, calc_regime_multiplier）
  - research/
    - factor_research.py — Momentum, Volatility, Value 等の計算
    - feature_exploration.py — 将来リターン計算、IC、統計サマリー
  - ai/
    - news_nlp.py — ニュース -> OpenAI -> ai_scores 書き込み
    - regime_detector.py — ETF MA + マクロニュース + LLM で市場レジーム判定
  - monitoring/
    - monitoring_db.py — SQLite スキーマ定義・MonitoringDB ラッパー
    - system_monitor.py — CPU/メモリ/データ鮮度監視
    - trade_monitor.py — 注文滞留・約定異常監視
    - risk_monitor.py — ドローダウン／ポジション上限監視
    - alert_manager.py — LINE 通知（cooldown）
    - kill_switch.py — フラグファイルによる停止
    - monitoring_engine.py — 監視ループ統括
    - streamlit_dashboard.py — Streamlit ダッシュボード（起動スクリプト）
  - execution/
    - broker_api.py — Broker API のデータモデル・Protocol・例外
    - order_manager.py — Order state machine の外向き API
    - execution_engine.py — Signal pull 型発注エンジン（セッション管理）
    - reconciler.py — 再起動時の注文・ポジション再照合
    - （その他: order_repository.py, order_record.py 等はリポジトリ内に存在する想定）
  - その他ユーティリティ（data pipeline / stats 等: 一部参照あり）

（上記はコードベース内の一部ファイル抜粋に基づく構成です。実際のリポジトリ全体はさらに多くのモジュールを含むことがあります）

## 注意事項 / 運用メモ
- OpenAI などの外部 API キーは必ず安全に管理してください（.env やシークレット管理を利用）。
- ニューススコアリング / レジーム判定は LLM 呼び出しに依存します。API 失敗時のフォールバックやスロットリングに配慮していますが、運用時はレートやコストに注意してください。
- ExecutionEngine / OrderManager はクラッシュ耐性を考慮した設計をしていますが、本番運用前に必ず統合テスト・ドライランを行ってください。
- 監視・KillSwitch 関連は発注停止や全キャンセルを実行します。テスト環境と本番でのフラグ管理に注意してください（KILL_FLAG_CLEAR_ON_START など）。

---

この README はコードベースの主要部分をまとめた簡易ドキュメントです。実際の導入・運用時は各モジュールの docstring・型注釈・テストケースを参照してください。必要であれば README にサンプルワークフロー（初期データ投入、DuckDB スキーマ、OrderRepository 初期化方法など）を追加します。どの情報を追記したいか教えてください。