# KabuSys

日本株の自動売買・リサーチ基盤の一部を構成する Python パッケージ群の README です。本リポジトリはトレード実行・監視・リサーチ・ポートフォリオ構築・AI（ニュース NLP / レジーム判定）などのコンポーネントを含みます。

---

## プロジェクト概要

KabuSys は日本株の自動売買システム向けに設計されたモジュール群です。本コードベースは以下の用途をカバーします。

- 実注文の管理と発注（ExecutionEngine 周辺）
- 監視機能（システム状態、注文滞留、リスク監視、kill switch）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算、セクター制限）
- リサーチ / ファクター計算（DuckDB を用いたファクター群）
- ニュースの NLP によるセンチメント評価（OpenAI API を利用）
- Paper Trading（本番 DB と分離した模擬トレード用 DB）
- ツール類（Paper Trading の検証レポート、Streamlit ダッシュボード等）

設計方針の例:
- DuckDB / SQLite をデータ層に使用（DuckDB は時系列・大規模データの解析用）
- 環境変数 / .env による設定管理（kabusys.config）
- 外部 API 呼び出しは明確に分離し、失敗時にはフォールバックやフェイルセーフを備える

---

## 主な機能一覧

- Execution
  - OrderManager / ExecutionEngine / Reconciler による発注・再同期処理
  - Paper Trading モード（KABUSYS_ENV=paper_trading）で MockBroker を利用しデータを data/paper_trading.db に記録
- Monitoring
  - SystemMonitor: CPU / メモリ / ディスク / 起動プロセス監視、データ鮮度チェック
  - TradeMonitor: 滞留注文（stale）・約定価格異常の検出
  - RiskMonitor: ドローダウン監視、ポジション上限チェック、ダッシュボード更新
  - KillSwitch: kill.flag ファイル作成による ExecutionEngine 停止トリガー
  - AlertManager: LINE Push による通知（クールダウン管理）
  - streamlit ダッシュボード（src/kabusys/monitoring/streamlit_dashboard.py）
- Portfolio
  - 候補選定、等重/スコア重み付け、リスク調整（セクターキャップ・レジーム乗数）
  - ポジションサイズ計算（単元株丸め、利用現金へのスケール調整）
- Research
  - ファクター計算（モメンタム・ボラティリティ・バリュー）
  - 特徴量探索（将来リターン、IC 計算、統計サマリー）
- AI（OpenAI 経由）
  - news_nlp.score_news: ニュースから銘柄ごとのセンチメントを生成して ai_scores に書き込み
  - regime_detector.score_regime: ma200 乖離 + マクロニュースセンチメントで市場レジーム判定
- ツール
  - paper_verification_report: Paper Trading DB を集計して検証レポートを出力

---

## セットアップ手順

前提
- Python 3.10 以上を推奨（型ヒントの union 記法や挙動に依存）
- system パッケージ: duckdb, psutil, requests, openai, streamlit（用途に応じて）

例: 仮想環境を作成して必要パッケージをインストールする

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
pip install duckdb psutil requests openai streamlit
```

必須/推奨の環境変数
- JQUANTS_REFRESH_TOKEN — J-Quants API トークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector を使う場合は必須）
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
  - paper_trading を指定すると paper 用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用
- PAPER_FILL_MODE — Paper Trading の約定モード（instant｜partial｜never｜reject、デフォルト: instant）
- Optional:
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
  - PID_FILE_PATH / KILL_FLAG_PATH / etc.

.env 自動ロード
- プロジェクトルート（.git または pyproject.toml を起点）に .env / .env.local を置くと自動ロードされます
- 自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

初期 DB 作成
- Monitoring 用 SQLite（init_monitoring_db）が起動時に自動作成・マイグレーションします。特別な準備は不要です。

注意
- OpenAI を使う場合は API 利用料が発生します。キーは厳重に管理してください。

---

## 使い方

コマンドラインから各スクリプトを実行できます。パッケージをモジュールとして実行する形を推奨します。

1. Execution（実行エンジン）起動

- 通常（デフォルト環境に従う）:

```bash
python -m kabusys.run_execution
```

- Paper Trading モードで起動する例:

```bash
export KABUSYS_ENV=paper_trading
python -m kabusys.run_execution
```

挙動:
- KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い PAPER_TRADING_SQLITE_PATH に書き込みます（本番 DB と完全分離）
- 実行時に Settings を読み、PID ファイル設定や DB 接続、各コンポーネントを初期化します

2. Monitoring（監視）起動

```bash
python -m kabusys.run_monitoring
```

オプション:
- MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）

挙動:
- SystemMonitor / TradeMonitor / RiskMonitor 等を初期化しポーリングを続けます
- 起動時にプロセス優先度を "high" に設定しようとします（psutil を利用）

3. Streamlit ダッシュボード

開発・運用で監視 DB を可視化するためのダッシュボード:

```bash
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```

4. Paper Trading 検証レポート

paper_verification_report は Paper Trading の SQLite を集計してレポートを出力します:

```bash
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# または DB を明示する
python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
```

5. AI / リサーチ関数の利用（プログラム的に）

- ニューススコア生成（例）:

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 4, 1), api_key="sk-...")
```

- レジーム判定:

```python
from kabusys.ai.regime_detector import score_regime
# conn: duckdb connection
score_regime(conn, target_date=date(2026,4,1), api_key="sk-...")
```

6. ライブラリ的な利用

- ポートフォリオ関連 API:

```python
from kabusys.portfolio import select_candidates, calc_score_weights, calc_position_sizes
```

- リサーチ API:

```python
from kabusys.research import calc_momentum, calc_volatility, calc_value
```

---

## 主要ファイル / ディレクトリ構成

（抜粋 — 主要なモジュールを示します）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数 / .env の自動ロード、Settings クラス
  - run_execution.py
    - ExecutionEngine の起動スクリプト（paper_trading モード対応）
  - run_monitoring.py
    - SystemMonitor のポーリング起動スクリプト
  - execution/
    - order_manager.py, reconciler.py, ... (発注、状態管理、再同期)
  - monitoring/
    - monitoring_db.py (SQLite スキーマ・永続化)
    - system_monitor.py (CPU/メモリ/データ鮮度)
    - trade_monitor.py (滞留注文・価格異常検出)
    - risk_monitor.py (ドローダウン・ポジション上限)
    - kill_switch.py (kill.flag 書込み)
    - alert_manager.py (LINE 通知)
    - monitoring_engine.py (モニタ群の束ね)
    - streamlit_dashboard.py (監視ダッシュボード)
  - portfolio/
    - portfolio_builder.py (候補選定・重み)
    - risk_adjustment.py (セクター制限・レジーム乗数)
    - position_sizing.py (株数計算・丸め・スケール)
  - research/
    - factor_research.py (momentum/volatility/value 等)
    - feature_exploration.py (forward returns / IC / summary)
  - ai/
    - news_nlp.py (ニュース→OpenAI→ai_scores 書込み)
    - regime_detector.py (ma200 + マクロセンチメント → regime)
  - tools/
    - paper_verification_report.py (Paper Trading レポート)
  - utils/
    - process_priority.py (プロセス優先度 / CPU affinity 設定ユーティリティ)

---

## 注意事項 / 運用上のヒント

- 環境変数管理:
  - .env / .env.local に設定を置く場合、OS 環境変数が優先され .env.local は上書き可能です。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます（テスト時に便利）。
- DB 分離:
  - paper_trading モードでは paper 用 SQLite を使い、本番の monitoring.db と書込みを分離します。
- OpenAI 呼び出し:
  - rate limit / 一時エラーに対してリトライやフォールバック（ゼロスコア）を実装していますが、API 利用量やエラー時の挙動を運用で監視してください。
- kill.flag:
  - KillSwitch はデフォルトで data/kill.flag を生成します。ExecutionEngine 起動時にこのファイルがあれば停止信号扱いになる運用設計を念頭に置いてください。
- プロセス優先度:
  - 起動スクリプトは set_process_priority("high") を試みますが、権限や OS により設定に失敗することがあります（警告ログ）。

---

## 貢献 / 拡張案

- stocks マスタを導入して銘柄別の lot_size・セクター情報を外部化
- ポジションサイズ計算のより細かな手数料/スリッページモデルの導入
- Streamlit ダッシュボードの UI 強化（グラフ・フィルター）
- モニタリングのメトリクスを Prometheus / Grafana にエクスポート

---

README に書かれている情報はコードのコメント・ docstring を基にまとめています。実行前に必須の環境変数や設定（特に API キー・kabu API パスワード）を正しく設定してください。質問・追加のドキュメント化リクエストがあればお知らせください。