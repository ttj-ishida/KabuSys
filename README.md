KabuSys
======

日本株向けの自動売買システム（ライブラリ＋実行スクリプト群）の一部を収めたコードベースです。本 README はローカル開発・ペーパートレード・本番での起動に必要な概要、セットアップ、使い方、ディレクトリ構成を日本語でまとめたものです。

概要
---
KabuSys は次の主要機能を持つモジュール群で構成されています。

- Execution Engine：発注管理、注文リポジトリ、リスク管理、再整合（reconciler）などを含む発注実行系。
- Monitoring：プロセス・システム状態、注文滞留や約定異常、リスク（ドローダウン・ポジション上限）監視と Kill Switch。
- Portfolio Construction：候補選定、重み計算、ポジションサイズ計算、セクター制約やレジーム補正。
- Research：ファクター計算（モメンタム/バリュー/ボラティリティ）、将来リターン計算、IC 等の統計解析ユーティリティ。
- AI：ニュースの NLP によるセンチメントスコアリング（OpenAI）や市場レジーム判定（LLM とETF MA の融合）。
- ツール：ペーパートレード検証レポートや設定ウィザード / 検証 CLI。
- ユーティリティ群：設定読み込み、プロセス優先度設定、DB ヘルパー等。

主な設計方針（抜粋）
- 本番 DB とペーパートレード DB は分離（PAPER_TRADING_SQLITE_PATH）。
- 可能な限り「ルックアヘッドバイアス」を避ける設計（日時参照の扱いに注意）。
- フェイルセーフ：外部 API（OpenAI など）失敗時はスキップやフォールバックで継続。
- .env を用いた環境変数管理。自動ロード機能あり（プロジェクトルート検出）。

機能一覧
---
- 設定ウィザード：python -m kabusys.config_setup（対話式 .env 作成）
- 設定検証：python -m kabusys.validate_config（.env と config/*.yaml の基本チェック）
- 実行エンジン起動：python -m kabusys.run_execution（本番 / ペーパー両対応）
- 監視ループ起動：python -m kabusys.run_monitoring（SystemMonitor をポーリング）
- ペーパートレード検証レポート生成：python -m kabusys.tools.paper_verification_report
- AI モジュール：ニュースセンチメント付与（kabusys.ai.news_nlp.score_news）、レジーム判定（kabusys.ai.regime_detector.score_regime）
- ポートフォリオ構築：候補選定・重み付け・ポジションサイズ計算・セクターキャップ適用
- モニタリング永続化：SQLite に system_status / trade_logs / risk_logs / positions / dashboard を永続化
- ユーティリティ：プロセス優先度設定（psutil ベース）、CPU affinity 設定

セットアップ手順
---
1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. Python 仮想環境
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - requirements.txt が用意されている場合:
     - pip install -r requirements.txt
   - 主要なライブラリ（ソース中の import 参照）:
     - duckdb, psutil, openai, PyYAML（config 検証時）
   - 例（個別インストール）:
     - pip install duckdb psutil openai PyYAML

4. 環境変数の設定 (.env)
   - 対話式ウィザードを推奨:
     - python -m kabusys.config_setup
   - 必須環境変数（最低限）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 主要な環境変数（任意 / デフォルト有り）
     - KABUSYS_ENV (development | paper_trading | live) — default: development
     - DUCKDB_PATH — default: data/kabusys.duckdb
     - SQLITE_PATH — default: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH — default: data/paper_trading.db
     - LOG_LEVEL — default: INFO
     - OPENAI_API_KEY — AI 機能利用時に必要
     - PAPER_FILL_MODE — paper_trading 時の約定挙動（instant | partial | never | reject）
     - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag をクリアするか（0/1）

   - .env は決して Git にコミットしないでください。

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いにできます。

使い方（実行例）
---
- 実行エンジン（ExecutionEngine）起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV が paper_trading の場合、MockBrokerClient を使い data/paper_trading.db に記録します（本番 DB と完全分離）。
  - 起動時に data/execution.pid を書きます。停止は data/stop_requested.flag または monitoring の kill.flag を使います。

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更可能（デフォルト 60 秒）。
  - 監視は本番 sqlite_path（Settings.sqlite_path）を使用します（環境にかかわらず本番 DB を参照）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 例: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH と同等）。

- 設定ウィザード・検証
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config [--strict]

- AI 機能の利用（プログラムから）
  - ニューススコア付与:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="...")  # api_key を渡すか OPENAI_API_KEY を設定
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="...")

停止／Kill Switch について
---
- monitoring.kill_switch は条件成立時に data/kill.flag を書き込み、ExecutionEngine に停止シグナルを与えます。
- ExecutionEngine/run_execution は起動時・ループ中に data/stop_requested.flag を監視して終了します。
- Settings.kill_flag_clear_on_start を 1 に設定すると起動時に kill.flag を自動クリアしますが、本番環境では 0 を推奨します。

設定の動作差（KABUSYS_ENV）
---
- development: 開発用（発注なし等の制約）
- paper_trading: ペーパートレード。MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH に記録する
- live: 本番。実際のブローカークライアントが使用されます（LINE 通知等の設定を要確認）

注意点 / トラブルシューティング
---
- psutil を使ってプロセス優先度設定や CPU affinity を行います。権限不足で設定に失敗することがありますが、警告を出してスキップする設計です。
- OpenAI を使う機能は OPENAI_API_KEY（または関数引数）を必ず設定してください。API 呼び出しはリトライ・バックオフを実装していますが、料金・レート制限に注意してください。
- DuckDB / SQLite のパスに指定した親ディレクトリが存在しない場合、警告が出ます。起動スクリプトや Monitoring が自動でディレクトリを作成する場合もありますが、権限に注意してください。
- .env の自動ロードはプロジェクトルート検出に基づきます。CWD に依存せずに __file__ を起点に親ディレクトリの .git / pyproject.toml を探索します。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ディレクトリ構成（主要ファイル）
---
src/kabusys/
- __init__.py
- config.py                      — 環境変数 / Settings
- config_setup.py                — .env 対話式ウィザード（CLI）
- validate_config.py             — 設定検証 CLI
- run_execution.py               — ExecutionEngine 起動スクリプト
- run_monitoring.py              — SystemMonitor ポーリング起動スクリプト

src/kabusys/ai/
- news_nlp.py                    — ニュース NLP（OpenAI）と ai_scores 書込み
- regime_detector.py             — 市場レジーム判定（MA + LLM）
- __init__.py

src/kabusys/monitoring/
- monitoring_db.py               — SQLite テーブル初期化 + MonitoringDB ラッパー
- system_monitor.py              — CPU/メモリ/ディスク/プロセス/データ鮮度監視
- trade_monitor.py               — 注文滞留・約定異常監視
- risk_monitor.py                — ドローダウン・ポジション上限監視
- kill_switch.py                 — kill.flag 書き込みユーティリティ
- monitoring_engine.py           — 各 monitor を束ねるループ
- alert_manager.py               — （アラート送信管理。未表示の詳細あり）

src/kabusys/execution/                 — Execution 系（OrderManager, Engine 等） ※詳細ファイルあり
src/kabusys/portfolio/                 — ポートフォリオ構築関連（builder / sizing / risk_adjustment）
src/kabusys/research/                  — ファクター計算・特徴量解析
src/kabusys/tools/                      — 補助ツール（paper_verification_report など）
src/kabusys/utils/                      — プロセス優先度などのユーティリティ

data/
- データベースやフラグファイル保存先（例: data/monitoring.db, data/paper_trading.db, data/kabusys.duckdb, data/execution.pid, data/kill.flag）

サンプル .env（最小）
---
# 必須
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_kabu_password_here

# 環境
KABUSYS_ENV=development
LOG_LEVEL=INFO

# DB パス（必要なら変更）
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db

# OpenAI（AI 機能を使う場合）
OPENAI_API_KEY=sk-...

最後に
---
この README はコードベースの主要機能と使い方を簡潔にまとめたものです。実際の運用・デプロイ前に python -m kabusys.validate_config により設定チェックを行い、.env（機密情報）の取り扱いには十分ご注意ください。質問やドキュメントの補足が必要であれば教えてください。