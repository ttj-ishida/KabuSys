# KabuSys

KabuSys は日本株向けの自動売買システム（プロトタイプ）です。本リポジトリは、発注実行エンジン、監視・アラート基盤、ポートフォリオ構築・リスク制御ロジック、研究用ファクター計算、LLM を使ったニュース NLP などを含みます。

以下はこのコードベースの概要・セットアップ・使い方・ディレクトリ構成の README です。

---

## プロジェクト概要

主な目的は「データ駆動の日本株自動売買」を安全に運用するためのコンポーネント群を提供することです。設計方針としては以下を重視しています。

- 実行エンジンと監視は分離（監視はプロセス優先度変更や kill flag による安全停止機構を持つ）
- Paper Trading（疑似環境）と Live 環境を明確に分離（DB も分離）
- DuckDB を使った研究・ファクター計算、SQLite を監視ログや発注ログに使用
- OpenAI（gpt-4o-mini）を利用したニュースセンチメントやレジーム判定（フェイルセーフ実装）
- ストリームリットによる監視ダッシュボード（読み取り専用）

---

## 主な機能一覧

- Execution（発注実行）
  - ブローカークライアントの抽象化（実口座 / モック切替）
  - OrderManager / OrderRepository による注文管理
  - Reconciler による起動時の自動リコンシリエーション
  - RiskManager による発注前チェック（レート制限・最大ポジション等）

- Monitoring（監視）
  - SystemMonitor：CPU/メモリ/ディスク/プロセス/データ鮮度監視
  - TradeMonitor：滞留注文・約定異常の検出
  - RiskMonitor：ドローダウン・ポジション上限の検出
  - KillSwitch：閾値超過時にフラグファイルを書き ExecutionEngine を停止させる
  - AlertManager：LINE Push による通知（クールダウン管理）
  - Streamlit ダッシュボード（読み取り専用）

- Portfolio（ポートフォリオ構築）
  - 候補選定 / 等配分・スコア加重配分
  - セクター上限適用、レジームによる資金乗数
  - ポジションサイズ計算（単元株丸め、aggregate cap のスケーリング）

- Research（研究用）
  - Momentum / Volatility / Value 等のファクター計算（DuckDB 上で SQL 実行）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー

- AI（LLM 連携）
  - ニュース記事を LLM でセンチメント評価して ai_scores に保存
  - マクロニュースと ETF MA200 を使った市場レジーム判定

- Tools
  - Paper Trading 検証レポート生成（過去期間の稼働率・注文成功率・レイテンシ等の集計）

---

## セットアップ手順（開発 / 実行）

以下はローカル環境で動かすための基本手順です。Python のバージョンは 3.10+ を想定してください（typing でのモダンな表記あり）。

1. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - requirements.txt がない場合は最低限以下を用意してください:
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit
   例:
   - pip install duckdb psutil requests openai streamlit

3. データディレクトリを作成
   - mkdir -p data

4. 環境変数設定（.env 推奨）
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（OS 環境変数優先）。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   例（.env の最小例）:
   ```
   KABUSYS_ENV=development
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_api_password
   OPENAI_API_KEY=sk-...
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
   LINE_CHANNEL_ACCESS_TOKEN=
   LINE_USER_ID=
   PID_FILE_PATH=data/execution.pid
   KILL_FLAG_PATH=data/kill.flag
   PAPER_FILL_MODE=instant
   ```

5. DB 初期化
   - 監視用 SQLite はスクリプト実行時に `init_monitoring_db()` によって冪等に作成されます。手動で空ファイルを作る必要はありませんが `data/` に書き込み権限が必要です。

---

## 主要な環境変数（重要）

- KABUSYS_ENV: `development` | `paper_trading` | `live`（デフォルト: development）
  - `paper_trading` ではモックブローカーを使用し、Paper Trading 用の別 SQLite を使います。
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PID_FILE_PATH: ExecutionEngine の PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
- PAPER_FILL_MODE: paper_trading の約定モード（instant | partial | never | reject）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）

---

## 実行方法（使い方）

- 監視ループを起動（Monitoring）:
  - python -m kabusys.run_monitoring
  - 説明: プロセス優先度を "high" に設定し、監視用 SQLite（settings.sqlite_path）と DuckDB に接続してポーリングを継続します。
  - 注意: 監視は KABUSYS_ENV に関係なく監視用の sqlite_path（productions path）を使用します。

- 実行エンジンを起動（ExecutionEngine）:
  - python -m kabusys.run_execution
  - 説明: Settings に基づきブローカークライアントを作成し、ExecutionEngine を構築してセッションを実行します。
  - Paper Trading:
    - KABUSYS_ENV=paper_trading にするとモックブローカーが使用され、DB は PAPER_TRADING_SQLITE_PATH（data/paper_trading.db）に分離されます。

- Streamlit ダッシュボード（監視閲覧）:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 説明: 監視用 SQLite を読み取り専用で開き、ダッシュボード（Overview / Positions / Orders / System）を表示します。

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH  （PAPER_TRADING_SQLITE_PATH 環境変数の代替）
  - レポートは稼働率・注文成功率・送信率・P95 レイテンシ等を出力します。

---

## 注意事項 / 運用上のポイント

- プロセス優先度と CPU affinity:
  - run_* スクリプトは起動時に set_process_priority("high") を呼びます（psutil が必要）。アクセス権や OS により設定できない場合はログに警告が出ます。

- KillSwitch:
  - RiskMonitor 等が条件を満たすと KillSwitch が kill.flag を書き込み、ExecutionEngine 停止のトリガーに使われます。ExecutionEngine 側で kill.flag の存在を検知して停止する実装になっている想定です。

- DB マイグレーション:
  - init_monitoring_db はテーブル作成と簡単なカラム追加（既存 DB にないカラムを追加）を行うため、冪等に安全に呼べます。

- LLM 呼び出し:
  - OpenAI API 呼び出しはリトライやフェイルセーフが組み込まれています（429 / ネットワーク / 5xx に対する指数バックオフ等）。
  - API キーがない場合は関数が ValueError を投げます（score_news / score_regime など）。

- Paper Trading と Live の分離:
  - Paper Trading は DB を分離し、MockBrokerClient を用いて実行します。これにより本番 DB／ブローカーとの混同を防ぎます。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env 読み込み / Settings
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - utils/
    - __init__.py
    - process_priority.py    — psutil を使った優先度 / CPU affinity ユーティリティ
  - monitoring/
    - __init__.py
    - monitoring_db.py       — SQLite を使った監視ログ永続化層
    - system_monitor.py      — CPU/メモリ/ディスク/データ鮮度監視
    - trade_monitor.py       — 滞留注文 / 約定異常監視
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — kill.flag 書き込みユーティリティ
    - alert_manager.py       — LINE Push 通知ユーティリティ
    - monitoring_engine.py   — 複数 Monitor を束ねるランナー
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - execution/
    - order_manager.py
    - reconciler.py
    - ... （ブローカー周り・リスク管理・エンジン本体は別ファイル群）
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み計算
    - risk_adjustment.py     — セクター上限・レジーム乗数
    - position_sizing.py     — 発注株数計算
    - __init__.py
  - research/
    - factor_research.py     — Momentum / Volatility / Value 等の計算
    - feature_exploration.py — 将来リターン・IC・統計ユーティリティ
    - __init__.py
  - ai/
    - news_nlp.py            — ニュース記事の LLM スコアリング
    - regime_detector.py     — マクロ + MA200 によるレジーム判定
    - __init__.py
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading 検証レポート

- data/
  - monitoring.db            — 監視用 SQLite（デフォルト）
  - paper_trading.db         — Paper Trading 用 SQLite（paper_trading 環境時）
  - kabusys.duckdb           — DuckDB（価格やマスタ、raw_news 等）

---

## よくある操作例

- 監視をデバッグ的に 1 回だけ実行（テスト用）
  - MonitoringEngine を直接組み立て test 用の run_once() を呼ぶ（ユニットテストやスクリプトから利用）

- Paper Trading のレポート（期間指定）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- Streamlit ダッシュボードをローカルで確認
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

---

## 開発・拡張のヒント

- DuckDB の SQL は module 内で直接組み立てているため、prices_daily / raw_financials / raw_news 等のスキーマに合わせてデータを投入すれば Research 機能を利用可能です。
- LLM 部分（news_nlp / regime_detector）はテスト容易性のため API 呼び出し関数をモックできるよう設計されています。
- order / broker 周りは抽象化されているため、新しいブローカー実装を追加することで切り替え可能です。

---

この README はコードベースの主要部分を把握するための要約です。実際の運用では環境変数の管理（秘密情報の保護）、ロギング設定、プロセス監視（systemd / pm2 等）やバックアップ/監査ポリシーを追加してください。必要であれば各モジュール（ExecutionEngine、OrderRepository、BrokerClient 等）の詳細 README を追記します。