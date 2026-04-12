# KabuSys

日本株向け自動売買システムのモジュール群（ライブラリ＋ランタイム用スクリプト群）。

本リポジトリは取引エンジン、監視（Monitoring）、ポートフォリオ構築、リサーチ、AI（ニュース NLP / レジーム判定）等の機能を含むモジュール化されたコードベースです。

---

## プロジェクト概要

- 目的: 日本株の自動売買運用を支援するためのコンポーネント群（注文管理、リスク監視、ポートフォリオ構成、ファクター計算、ニュースセンチメント評価など）を提供します。
- 設計方針:
  - DB（SQLite / DuckDB）や外部 API（kabu API / J-Quants / OpenAI）を明確に分離。
  - 本番と Paper Trading（モックブローカー）を環境変数 `KABUSYS_ENV` で切替可能。
  - 多くの処理は純粋関数または副作用を限定したクラスとして実装されており、テスト容易性を重視。
  - .env ファイル自動読み込み機能あり（プロジェクトルートの `.env` / `.env.local`）。

---

## 主な機能一覧

- 実行（Execution）
  - 発注フロー管理（OrderManager、OrderRepository、Reconciler）
  - RiskManager によるリスク制御・レート制限等
  - Broker クライアントの抽象化（本番 / モック切り替え）

- 監視（Monitoring）
  - SystemMonitor: CPU / メモリ / ディスク / PID / データ鮮度の監視
  - TradeMonitor: 滞留注文・約定異常の検出
  - RiskMonitor: ドローダウン・ポジション上限監視と kill flag 出力
  - AlertManager: LINE Push による通知（クールダウン付き）
  - Streamlit ダッシュボード（読み取り専用で監視 DB を可視化）
  - Monitoring DB（SQLite）テーブルの初期化・抽象化

- ポートフォリオ構築（portfolio）
  - 候補選定、等配分／スコア加重、ポジションサイズ計算、セクターキャップ、レジーム乗数

- リサーチ（research）
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー

- AI（ai）
  - ニュース NLP（OpenAI を用いた銘柄別センチメントスコアの算出と ai_scores への書込み）
  - レジーム判定（ETF の MA とマクロニュースセンチメントを合成して daily regime を計算・保存）

- ツール
  - Paper Trading 検証レポート生成スクリプト（期間指定で paper_trading DB を集計）

---

## セットアップ手順（開発環境向け）

前提: Python 3.10+（型注釈で union と Path 互換を利用しているため推奨）

1. リポジトリをクローン
   - git clone ...（プロジェクトルートに `.git` / `pyproject.toml` を置くことで .env 自動読み込みが有効になります）

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate (Unix) / .venv\Scripts\activate (Windows)

3. 依存パッケージをインストール（例）
   - pip install duckdb psutil requests openai streamlit
   - 実際のプロジェクトでは requirements.txt / pyproject.toml を参照してください

4. 環境変数 / .env
   - プロジェクトルートに `.env` を置くと自動で読み込まれます（OS 環境変数を保護）。
   - 自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
   - 必須環境変数（例）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 任意 / デフォルト（主なもの）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - SQLITE_PATH: monitoring DB パス（デフォルト: data/monitoring.db）
     - DUCKDB_PATH: DuckDB パス（デフォルト: data/kabusys.duckdb）
     - PAPER_TRADING_SQLITE_PATH: paper trading 用 SQLite（デフォルト: data/paper_trading.db）
     - OPENAI_API_KEY: OpenAI 呼び出しに必須（ai モジュール使用時）
     - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）
     - PID_FILE_PATH, KILL_FLAG_PATH, LOG_LEVEL, CPU/MEM/DISK 閾値 等

5. データディレクトリ作成
   - mkdir -p data

注意:
- set_process_priority() は psutil を使い OS に依存した操作を行います。権限が必要な場合があります。
- Paper Trading モードでは本番 DB と分離され、`data/paper_trading.db` を使用します。

---

## 使い方（主要な起動コマンド）

以下はモジュールをパッケージとして実行する例です。

- 監視（Polling）を起動
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（デフォルト 60）
  - python -m kabusys.run_monitoring

- Execution Engine を起動（実際の取引 / Paper Trading 切替は KABUSYS_ENV）
  - KABUSYS_ENV=paper_trading を指定すると MockBroker を使い paper DB に書き込みます
  - python -m kabusys.run_execution

- Paper Trading 検証レポート（CLI）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - または --db PATH で DB を直接指定（環境変数 PAPER_TRADING_SQLITE_PATH でも可）

- Streamlit 監視ダッシュボード（読み取り専用）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- AI モジュールの利用例（Python から直接呼び出す）
  - OpenAI API キーを設定（環境変数 OPENAI_API_KEY）
  - 例: score_news を実行する（DuckDB コネクションを渡す）
    - from datetime import date
    - import duckdb
    - from kabusys.ai.news_nlp import score_news
    - conn = duckdb.connect('data/kabusys.duckdb')
    - score_news(conn, date(2026, 4, 10))  # 戻り値: 書き込んだ銘柄数
  - 同様に regime 判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, date(2026, 4, 10))

注意点:
- ai モジュールは OpenAI API を呼び出します。API キーと適切な料金設定が必要です。
- news_nlp/regime_detector は外部 API の失敗に対してフェイルセーフ（スコアを 0 にする等）を備えていますが、実行環境のレート制限やタイムアウトに注意してください。

---

## 主要な環境変数（抜粋）

- KABUSYS_ENV: development | paper_trading | live（default: development）
- JQUANTS_REFRESH_TOKEN: J-Quants 用トークン（必須）
- KABU_API_PASSWORD: kabu API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（ai 機能で必須）
- SQLITE_PATH: 監視 DB（default: data/monitoring.db）
- DUCKDB_PATH: DuckDB DB（default: data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: paper trading DB（default: data/paper_trading.db）
- PAPER_FILL_MODE: instant | partial | never | reject（default: instant）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、default: 60）
- PID_FILE_PATH, KILL_FLAG_PATH, LOG_LEVEL, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT

---

## ディレクトリ構成（概要）

以下はソースツリー（`src/kabusys`）の主要ファイル/ディレクトリの抜粋です。

- src/
  - kabusys/
    - __init__.py
    - config.py                         — 環境変数 / 設定読み込み
    - run_monitoring.py                 — SystemMonitor のポーリングループ起動スクリプト
    - run_execution.py                  — ExecutionEngine 起動スクリプト
    - tools/
      - __init__.py
      - paper_verification_report.py    — Paper Trading 検証レポート CLI
    - monitoring/
      - __init__.py
      - monitoring_db.py                — SQLite テーブル初期化・永続化層
      - system_monitor.py               — システム監視
      - trade_monitor.py                — 注文監視
      - risk_monitor.py                 — ドローダウン / ポジション上限監視
      - kill_switch.py                  — kill.flag 書込みユーティリティ
      - alert_manager.py                — LINE 通知
      - monitoring_engine.py            — 各 Monitor を束ねるランナ
      - streamlit_dashboard.py          — Streamlit ダッシュボード
    - execution/
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - execution_engine.py (他ファイル群)...
    - portfolio/
      - __init__.py
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - utils/
      - __init__.py
      - process_priority.py
    - data/ (外部ファイル想定: DuckDB/SQLite にデータ保存)

---

## 運用・監視上の注意点

- Monitoring は常に本番用の sqlite_path を参照します（run_monitoring は KABUSYS_ENV に依存せず本番パスを使用する実装です）。Paper Trading を分離したい場合は run_execution の挙動に注意してください（run_execution は KABUSYS_ENV=paper_trading の場合 paper_sqlite_path を使います）。
- kill.flag（Settings.kill_flag_path）で ExecutionEngine を安全停止できます。kill.flag の自動クリアは Settings.kill_flag_clear_on_start を参照してください。
- Process priority / CPU affinity の設定は psutil を利用します。権限不足で設定が失敗する場合がありますが、失敗してもプロセスは継続します（警告ロギング）。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われます。テスト時に自動ロードを止めたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 追加情報 / 開発者向けヒント

- DB のスキーマ初期化は init_monitoring_db() が行います。起動時に呼ばれるため通常は手動マイグレーション不要ですが、スキーマ変更時は既存 DB に対するマイグレーション処理が実装されていることを確認してください（monitoring_db.py 内にいくつかの互換処理あり）。
- ai.news_nlp と ai.regime_detector の OpenAI 呼び出しはリトライロジック・JSON 検証が組み込まれています。テストでは _call_openai_api をモックすることを推奨します。
- portfolio や research の関数群は副作用を持たない純粋関数群として設計されており、ユニットテストが容易です。

---

必要であれば、README に以下を追記できます:
- 依存パッケージの正確なバージョン一覧（requirements.txt/pyproject.toml ベース）
- 例: .env.example のサンプル内容
- デプロイ / systemd サービス化の手順（run_monitoring/run_execution を systemd で運用する例）
- 詳細な API ドキュメント（各モジュールの public API、戻り値仕様等）

追記したい項目があれば教えてください。