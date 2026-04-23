# KabuSys — 日本株自動売買システム (README)

このリポジトリは日本株自動売買システム「KabuSys」のモジュール群を含みます。戦略の構築・ポートフォリオ計算、実行エンジン、監視、リサーチ、AI を用いたニュース解析などを備えています。本 README はローカル環境での起動・運用に必要な概要、セットアップ、使い方、ディレクトリ構成を日本語でまとめたものです。

注意: 実際の発注を行う機能は本番環境で動くと危険を伴います。KABUSYS_ENV を正しく設定し、設定検証を実行してから起動してください。

---

## プロジェクト概要

- モジュール化された自動売買システム（戦略、ポートフォリオ構築、実行、監視、リサーチ、AI ニュース解析）。
- DuckDB を用いた分析用データベース、SQLite を用いた監視・注文ログ保存。
- 実行エンジンは本番（live）/ペーパートレード（paper_trading）/開発（development）モードをサポート。
- 監視（Monitoring）はプロセス・リソース・データ鮮度・トレード挙動・リスク監視を行い、必要時に kill.flag を書き込んで ExecutionEngine を停止させます。
- OpenAI（gpt-4o-mini）を使ったニュースセンチメント／市場レジーム判定機能を含む（API キー必要）。

---

## 主な機能一覧

- Execution
  - ExecutionEngine を起動して注文発行・管理 (run_execution.py)。
  - paper_trading モードでは MockBrokerClient を使用し、paper_trading 用 SQLite に記録（本番 DB と分離）。
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク、データ鮮度、PID の監視。
  - TradeMonitor / RiskMonitor: 滞留注文、約定異常、ドローダウン・ポジション上限検出。
  - KillSwitch: 条件に応じて data/kill.flag を書き込み ExecutionEngine を停止。
  - MonitoringEngine: これらをまとめてポーリング実行（run_monitoring.py）。
- Portfolio
  - 候補選定、等金額/スコア加重配分、ポジションサイズ計算、セクターキャップ、レジーム乗数等の純粋関数群。
- Research
  - ファクター計算（モメンタム、ボラティリティ、バリュー）、将来リターン、IC 計算、統計サマリ。
  - DuckDB 経由で prices_daily / raw_financials を用いた処理。
- AI
  - news_nlp: raw_news を集約し OpenAI API で銘柄別センチメントを算出して ai_scores に格納。
  - regime_detector: ETF（1321）MA200 乖離 + マクロニュースで日次の市場レジーム判定。
- ツール
  - config_setup.py: .env を対話式に生成・更新するウィザード。
  - validate_config.py: 環境変数・config/*.yaml の検証。
  - tools/paper_verification_report.py: ペーパートレードの検証レポート生成。

---

## 前提（依存ライブラリ）

代表的な依存例（プロジェクトに requirements.txt がある場合はそちらを使用してください）:

- Python 3.9+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（config ファイル検証を行う場合に推奨）

インストール例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

---

## セットアップ手順

1. リポジトリをクローンし、Python 仮想環境を用意する:
   - git clone ...
   - python -m venv .venv
   - source .venv/bin/activate

2. 必要パッケージをインストール（上記参照）。

3. .env を作成する（対話式ウィザード推奨）:
   - python -m kabusys.config_setup
   - 主要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - AI 機能を使う場合:
     - OPENAI_API_KEY（環境変数として設定）

   .env の主なキー（デフォルト値を示す）:
   - KABUSYS_ENV=development | paper_trading | live
   - JQUANTS_REFRESH_TOKEN=...
   - KABU_API_PASSWORD=...
   - KABU_API_BASE_URL=http://localhost:18080/kabusapi
   - DUCKDB_PATH=data/kabusys.duckdb
   - SQLITE_PATH=data/monitoring.db
   - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
   - LOG_LEVEL=INFO
   - LINE_CHANNEL_ACCESS_TOKEN= (任意)
   - LINE_USER_ID= (任意)
   - KILL_FLAG_CLEAR_ON_START=0 (起動時に kill.flag を自動クリアするか)

4. 設定検証（必須）:
   - python -m kabusys.validate_config
   - 問題がある場合は指示に従って .env / config/*.yaml を修正してください。
   - --strict オプションを付けると警告もエラー扱いになります:
     - python -m kabusys.validate_config --strict

5. DB 初期化は各起動スクリプトが行います（init_monitoring_db が冪等にテーブルを作成します）。

---

## 起動・使い方

以下は主要なエントリポイントの使い方例です。

- 実行エンジンを起動（通常はサービスとしてデーモン化して運用）:
  - python -m kabusys.run_execution
  - 注意: KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録されます。本番（live）時は実際のブローカーに発注されます。

- 監視ループを起動:
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位に変更できます（デフォルト 60 秒）。
    - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視プロセスは Settings.sqlite_path（デフォルト data/monitoring.db）に接続します（Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します）。

- 停止制御（Kill Switch / stop フラグ）
  - 監視や外部ツールは data/kill.flag を書き込むことで ExecutionEngine に停止シグナルを送ります。
  - 手動で停止フラグを立てる場合:
    - echo "reason ..." > data/kill.flag
  - ExecutionEngine の起動時に kill.flag を自動でクリアしたい場合は .env に KILL_FLAG_CLEAR_ON_START=1 を設定します（本番では 0 を推奨）。

- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH を上書き）

- AI 機能（ニューススコアリング / レジーム判定）
  - OPENAI_API_KEY を環境変数に設定してから実行してください。
  - 例: python -c "from kabusys.ai.news_nlp import score_news; import duckdb, datetime; conn=duckdb.connect('data/kabusys.duckdb'); score_news(conn, datetime.date(2026,4,1))"
  - ただし上記は内部 API を直接呼ぶ例です。実運用ではスクリプト化されたワークフローで呼んでください。

- ログ
  - デフォルト log ディレクトリ: logs/
  - setup_logging により stdout と日次ローテーションのファイル（logs/<app_name>.log）に出力されます。
  - 環境変数 LOG_DIR で変更可能、LOG_LEVEL でログレベルを指定（例: DEBUG）。

---

## 重要な挙動・運用上の注意

- Monitoring は常に Settings.sqlite_path（通常は本番監視 DB）を使います。paper_trading モードでも監視は本番 DB を参照するため注意してください。
- ペーパートレード時は発注先（MockBrokerClient）と記録先 DB が分離されています（PAPER_TRADING_SQLITE_PATH）。
- kill.flag を不用意にクリアすると本番の Kill Switch が無効化される可能性があるため、KILL_FLAG_CLEAR_ON_START の設定は慎重に。
- OpenAI API を使う機能は API レート制限・コストがかかります。API キーの管理と呼び出し頻度に注意してください。
- validate_config.py は PyYAML がインストールされていない場合、config/*.yaml の内容検証をスキップします（警告が出ます）。

---

## ディレクトリ構成（主なファイル）

以下はソースツリーの主要部分（src/kabusys 以下）を抜粋したものです。

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理（自動 .env ロード）
  - config_setup.py           — .env 対話ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py             — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py      — 市場レジーム判定（OpenAI + MA）
  - monitoring/
    - monitoring_db.py        — SQLite 永続化層（テーブル作成・読み書き）
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py        — （監視用のトレードチェック実装）
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py        — （アラート送信ロジック）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - logging_setup.py        — ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity
    - __init__.py
  - (その他) data/, execution/, strategy/ 等のモジュールや実装ファイル

※ 上記は主要ファイルの抜粋です。実装の詳細は各モジュールの docstring を参照してください。

---

## よくあるコマンドまとめ

- 環境設定ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

## 付録: よく使う環境変数（一覧）

- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 動作モード:
  - KABUSYS_ENV (development | paper_trading | live)
- データベース:
  - DUCKDB_PATH  (default: data/kabusys.duckdb)
  - SQLITE_PATH  (default: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB)
- ログ:
  - LOG_LEVEL (DEBUG/INFO/...)
  - LOG_DIR
- AI:
  - OPENAI_API_KEY (news_nlp / regime_detector を使う場合)
- 監視 / 制御:
  - PID_FILE_PATH (デフォルト data/execution.pid)
  - KILL_FLAG_PATH (デフォルト data/kill.flag)
  - KILL_FLAG_CLEAR_ON_START (0|1)
- 監視ループ間隔:
  - MONITOR_POLL_INTERVAL（run_monitoring で上書き可能）

---

必要に応じて、各モジュールの docstring を参照して詳細な仕様・パラメータを確認してください。運用前には必ず validate_config を実行し、テスト環境（paper_trading）で十分な検証を行ってから live 環境に移行してください。