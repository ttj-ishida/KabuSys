# KabuSys

日本株向けの自動売買/リサーチ/監視システムのサンプル実装（モジュール群）。  
このリポジトリは取引実行・監視・リサーチ・AIベースのニューススコアリング等の機能を含みます。

以下はコードベースから抜粋して作成した README です。

---

## 概要

KabuSys は次のような機能を提供するモジュール群です。

- 注文管理・ブローカー連携（Execution）
- ポートフォリオ構築・ポジションサイズ計算（Portfolio）
- ファクター計算・特徴量探索（Research）
- ニュースの NLP スコアリング & 市場レジーム判定（AI）
- 実行プロセスと注文の監視・アラート（Monitoring）
- Paper Trading 用の検証レポート生成ツール

設計上の特徴：

- DuckDB / SQLite をデータ層に使用（分離された本番 / paper_trading DB）
- OpenAI API を用いたニュースセンチメント / マクロセンチメント評価機能
- Monitoring コンポーネントは PID ファイル / kill.flag / ダッシュボードを利用して運用安全性を確保
- .env / 環境変数から設定を読み込む自動ロード機構（プロジェクトルート検出あり）

---

## 主な機能一覧

- Execution
  - Broker クライアントを切り替えて発注（paper_trading ではモックを利用）
  - OrderManager / OrderRepository による注文状態管理
  - Reconciler による起動時の自動復旧（注文・ポジション同期）
  - RiskManager による資金・ポジション制約管理

- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク・プロセスの生存確認・データ鮮度監視
  - TradeMonitor: 滞留注文・約定価格異常検出
  - RiskMonitor: ドローダウン・ポジション上限監視 + ダッシュボード永続化
  - AlertManager: LINE Push による通知（クールダウン管理）
  - KillSwitch: 条件に応じた kill.flag 発行で Execution を安全停止

- Research
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Information Coefficient）、要約統計

- AI
  - news_nlp: raw_news を集約して OpenAI で銘柄ごとにセンチメント評価 → ai_scores に書込
  - regime_detector: ETF（1321）MA200 とマクロニュースセンチメントを合成して日次レジーム判定

- Tools
  - paper_verification_report: Paper Trading DB を元に稼働率・注文成功率・レイテンシ等を集計してレポート出力

---

## セットアップ手順（概略）

必要な Python パッケージ（代表例）：

- python >= 3.10
- duckdb
- psutil
- openai
- requests
- streamlit

※requirements.txt はリポジトリに含まれていないため、上記パッケージを個別にインストールしてください。

例（pip）:
```
pip install duckdb psutil openai requests streamlit
```

環境変数（主なもの）:

- KABUSYS_ENV: 実行環境（development / paper_trading / live）。デフォルト: development
- SQLITE_PATH: monitoring 用 SQLite（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB のパス（デフォルト: data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の約定モード（instant / partial / never / reject。デフォルト: instant）
- PID_FILE_PATH: ExecutionEngine 用 PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
- JQUANTS_REFRESH_TOKEN: （必須）J-Quants API のトークン
- KABU_API_PASSWORD: （必須）kabuステーション API パスワード
- OPENAI_API_KEY: OpenAI API キー（AI モジュールで使用）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用

.env 自動読み込み:
- プロジェクトルート（.git または pyproject.toml を探索）を基準に `.env` と `.env.local` を読み込みます。
- 読み込み順: OS 環境 > .env.local > .env
- 自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

DB 初期化:
- monitoring 用のスキーマは起動スクリプト内で `init_monitoring_db()` により冪等に作成されます。

---

## 使い方（実行例）

ルートをプロジェクトルート（pyproject.toml がある場所）にして以下を実行します。

1. 監視 (Monitoring) を起動
```
# デフォルトは MONITOR_POLL_INTERVAL=60
MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
```
- MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（1 秒以上）。
- Process 優先度を "high" に設定し、monitoring DB（settings.sqlite_path）に書き込みます。

2. 実行エンジン (Execution) を起動
```
# live / development / paper_trading を切替
KABUSYS_ENV=paper_trading python -m kabusys.run_execution
```
- `KABUSYS_ENV=paper_trading` の場合、MockBrokerClient を使用し DB は `data/paper_trading.db` に分離して記録されます。
- `Settings` に従い各コンポーネント（Broker, OrderManager, RiskManager, Reconciler, ExecutionEngine）が組み立てられ実行されます。

3. Streamlit ダッシュボード（監視用）
```
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```
- 監視 DB を読み取り専用で開き、ダッシュボードを表示します。

4. Paper Trading 検証レポート
```
# デフォルト DB: data/paper_trading.db
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# または別ファイル指定
python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
```

5. AI モジュール（プログラムから直接呼ぶ）
- news_nlp.score_news(conn, target_date, api_key=None)
- regime_detector.score_regime(conn, target_date, api_key=None)
- 両者とも OPENAI_API_KEY を引数または環境変数で渡します。
- API 呼び出しはリトライやフェイルセーフ（失敗時はスコア 0.0 等）を備えています。

注意点:
- PID ファイル / kill.flag による運用保護が組み込まれています（デフォルトパスは Settings で指定）。
- paper_trading 実行時は本番 DB を汚さないよう paper 専用 DB を利用します。

---

## 主要ディレクトリ構成

（src/kabusys 以下の概観）

- kabusys/
  - __init__.py
  - config.py                       — 環境変数 / .env 読み込み + Settings クラス
  - run_monitoring.py               — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py                — ExecutionEngine 起動スクリプト
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュース NLP スコアリング（OpenAI連携）
    - regime_detector.py            — 市場レジーム判定（MA200 + マクロ NLP）
  - portfolio/
    - __init__.py
    - portfolio_builder.py          — 候補選定・重み計算
    - position_sizing.py            — 株数算出・スケーリング（ロット丸め等）
    - risk_adjustment.py            — セクター上限・レジーム乗数
  - research/
    - __init__.py
    - factor_research.py            — Momentum/Volatility/Value 等のファクター計算
    - feature_exploration.py        — 将来リターン / IC / 統計要約
  - execution/
    - reconciler.py                 — 再起動時リコンシリエーション
    - order_manager.py              — Order の外向き API（生成・送信・同期）
    - (その他 broker, order_repository 等は実装ファイルあり)
  - monitoring/
    - __init__.py
    - monitoring_db.py              — SQLite スキーマ / 永続化層
    - system_monitor.py             — システム監視（CPU/プロセス/データ鮮度）
    - trade_monitor.py              — 注文滞留 / 約定異常の検出
    - risk_monitor.py               — ドローダウン・ポジション上限監視
    - monitoring_engine.py          — 各 Monitor を束ねる実行ループ
    - alert_manager.py              — LINE Push を使った通知
    - kill_switch.py                — kill.flag の管理
    - streamlit_dashboard.py        — Streamlit ダッシュボード
  - tools/
    - __init__.py
    - paper_verification_report.py  — Paper Trading 検証レポート生成ツール
  - utils/
    - __init__.py
    - process_priority.py           — process priority / cpu affinity ユーティリティ

（上記はリポジトリに含まれる主要なモジュールの抜粋です）

---

## 追加メモ / 運用上の注意

- .env のパースはコメント・クォート・エスケープを比較的堅牢に扱いますが、例に倣って simple な .env を用意してください（.env.example を参考にする想定）。
- OpenAI API を使用する機能は API キーと利用料が必要です。rate-limit / transient error に対するリトライが組み込まれていますが、呼び出し頻度・コストに注意してください。
- Monitoring はデータ鮮度チェック（DuckDB の prices_daily）を行います。prices データの更新運用と合わせて監視してください。
- paper_trading は本番 DB と明確に分離しているため、検証やデバッグ用途に適しています。
- ストリーミングや高頻度注文を行う場合は Broker のレート制限や RiskManager の設定に注意してください（Rate limit / circuit breaker 設定あり）。

---

この README はコードベースの実装から抽出した主要ポイントをまとめたものです。実際の運用やデプロイ時は環境変数や Broker 実装、DB のバックアップ/移行手順などを適宜補ってください。必要であれば各モジュール単位の詳細ドキュメント（API・設定項目一覧・テーブルスキーマ等）を追記します。