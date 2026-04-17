# KabuSys

日本株向け自動売買システムの実装スニペット集（ライブラリ/CLI）。  
このリポジトリは、取引エンジン・監視・ポートフォリオ構築・リサーチ・AI 補助機能などを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要な主要コンポーネントを含むモジュール群です。主な責務は次のとおりです。

- 実行エンジン（ExecutionEngine）による発注管理・リスク管理
- 監視（MonitoringEngine / SystemMonitor / TradeMonitor / RiskMonitor）による稼働監視・アラート・Kill Switch
- ポートフォリオ構築（銘柄選定・配分・サイズ決定）
- リサーチ（ファクター算出・将来リターン・IC 等）
- AI 補助（ニュースのセンチメント評価 → ai_scores、レジーム判定）
- 開発支援ツール（.env ウィザード、設定検証、検証レポート生成）

この README は、主要機能・セットアップ・使い方・ディレクトリ構成をまとめたものです。

---

## 主な機能一覧

- 設定管理
  - .env の自動読み込み（プロジェクトルート検出）
  - 対話式の .env 作成ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）

- 実行 / 発注
  - run_execution.py：ExecutionEngine を起動（KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し paper_trading DB に完全分離して記録）
  - 発注ログ / positions を SQLite に永続化（monitoring DB）

- 監視 / アラート
  - run_monitoring.py：SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔変更可）
  - System / Trade / Risk の監視、LINE へ通知（AlertManager）
  - Kill Switch：重大リスク検出時に data/kill.flag を作成して ExecutionEngine 停止

- ポートフォリオ構築
  - 候補抽出、等金額/スコア加重、セクターキャップ、ポジションサイズ計算（単元株対応、資金上限調整）

- リサーチ
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を利用）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー

- AI
  - ニュースセンチメント評価（OpenAI API を用いる、スコアを ai_scores テーブルへ書込み）
  - マクロ＋ETF MA200 を組み合わせた市場レジーム判定（score_regime）

- ユーティリティ
  - process priority / CPU affinity 設定（psutil 使用）
  - Paper Trading 向け検証レポート生成ツール（tools.paper_verification_report）

---

## 必要条件（概要）

- Python 3.9+（型注釈や一部記法に依存）
- 推奨パッケージ（requirements にまとめる想定）
  - duckdb
  - psutil
  - openai
  - requests
  - PyYAML（設定ファイル YAML 検証用、任意）
- SQLite は標準搭載
- ネットワーク（kabuステーション API / OpenAI へ接続する場合）

※ 実行環境により psutil の優先度設定で権限が必要になる場合があります。

---

## セットアップ手順

1. リポジトリをクローン／展開する

2. 仮想環境を作成して有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install duckdb psutil openai requests PyYAML
   - （実際は requirements.txt を用意して pip install -r requirements.txt が望ましい）

4. .env を作成
   - 対話式ウィザードを使う（推奨）
     - python -m kabusys.config_setup
   - または手動でルートに `.env` を置く（.env.example を参照してください）

5. 設定を検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit code 1）

6. データディレクトリ
   - デフォルトの DB パスは data/ 配下（必要なら手動で作成）
   - run_* スクリプトは自動でファイルやディレクトリを作成することがあるが、権限を確認してください

---

## 環境変数（主要）

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行環境指定
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
    - paper_trading: 実際の発注は行わずペーパートレード用 DB（PAPER_TRADING_SQLITE_PATH）を使用
    - live: 本番運用

- DB / ファイルパス
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（監視用、デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
  - PID_FILE_PATH（実行エンジンの PID ファイル、デフォルト: data/execution.pid）
  - KILL_FLAG_PATH（kill.flag のパス、デフォルト: data/kill.flag）

- AI / 通知
  - OPENAI_API_KEY（AI 機能を使う場合必須）
  - LINE_CHANNEL_ACCESS_TOKEN（通知用、任意）
  - LINE_USER_ID（通知用、任意）

- その他
  - LOG_LEVEL（DEBUG/INFO/...、デフォルト INFO）
  - MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔 秒、デフォルト 60）
  - PAPER_FILL_MODE（paper_trading の約定モード: instant | partial | never | reject、デフォルト instant）
  - KILL_FLAG_CLEAR_ON_START（本番で危険な自動クリアフラグ、0/1）

例（.env の一部例）:
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
OPENAI_API_KEY=sk-...
LOG_LEVEL=INFO
```

---

## 使い方（主要コマンド）

- .env ウィザード
  - python -m kabusys.config_setup
    - 対話形式で .env を生成・更新します。

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 監視ループ起動
  - python -m kabusys.run_monitoring
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更可能
    - 監視は常に本番 sqlite_path（KABUSYS_ENV に依存せず）を使用します
    - 停止は data/stop_requested.flag を作成することで行えます（または Ctrl+C）

- 実行エンジン起動
  - python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用して data/paper_trading.db に記録（本番 DB と分離）
    - 起動時に data/stop_requested.flag が既に存在する場合は起動しません
    - 実行中は data/execution.pid に PID を書きます。停止は stop flag（data/stop_requested.flag）で行います

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH を上書き）
  - 出力: 稼働率、注文成功率、レイテンシ、Pass/Fail 判定

- AI 機能（プログラム呼び出し例）
  - OpenAI API キーが必要（OPENAI_API_KEY）
  - news_nlp.score_news(conn, target_date, api_key=None)
    - conn は DuckDB 接続（duckdb.connect(...)）
  - regime_detector.score_regime(conn, target_date, api_key=None)

- 監視 DB 初期化（内部で自動実行）
  - init_monitoring_db(sqlite_conn) が呼ばれます（冪等でテーブル作成 + マイグレーションを行う）

---

## Kill Switch / 停止制御

- Kill Switch（kill.flag）
  - kabusys.monitoring.kill_switch.KillSwitch が条件に応じて `data/kill.flag` を作成して ExecutionEngine に停止シグナルを送ります。
  - KillSwitch の評価は MonitoringEngine の一部として行われます。
  - ExecutionEngine は起動時や実行中に kill.flag の存在をチェックし、存在すると停止します。

- 手動停止
  - run_monitoring / run_execution は data/stop_requested.flag の存在も監視しており、これが存在するとループを終了します。

---

## ディレクトリ構成（主要ファイル）

以下は主要モジュールの抜粋構成です（src/kabusys 下）。

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings クラス、自動 .env ロード
  - config_setup.py           — .env 対話式ウィザード（python -m kabusys.config_setup）
  - validate_config.py        — 設定検証 CLI（python -m kabusys.validate_config）
  - run_monitoring.py         — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py          — ExecutionEngine 起動スクリプト

  - ai/
    - __init__.py
    - news_nlp.py             — ニュース NLP（OpenAI 経由で ai_scores へ書込）
    - regime_detector.py      — レジーム判定（ETF + マクロニュース）

  - monitoring/
    - monitoring_db.py        — SQLite 監視 DB 層（テーブル作成・CRUD）
    - system_monitor.py       — システム & データ鮮度監視
    - trade_monitor.py        — 注文滞留・約定異常監視
    - risk_monitor.py         — ドローダウン・ポジション上限チェック
    - monitoring_engine.py    — 各モニタを束ねるポーリングエンジン
    - alert_manager.py        — LINE Push 通知ラッパ
    - kill_switch.py          — kill.flag 書込ユーティリティ

  - execution/                — 発注エンジン周り（OrderManager 等） ※詳細はリポジトリの他ファイル
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - monitoring/               — （上記）
  - tools/
    - paper_verification_report.py
    - __init__.py
  - utils/
    - process_priority.py      — psutil を用いたプロセス優先度設定
    - __init__.py

data/ 配下（実行時に利用される典型的ファイル）
- data/kabusys.duckdb (DUCKDB_PATH)
- data/monitoring.db (SQLITE_PATH)
- data/paper_trading.db (PAPER_TRADING_SQLITE_PATH)
- data/execution.pid
- data/stop_requested.flag
- data/kill.flag

---

## 開発上の注意点 / 補足

- .env は決してリポジトリにコミットしないでください（README や .env.example のみ）。
- run_monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使用します（監視データは本番 DB で管理）。
- run_execution は KABUSYS_ENV が paper_trading の場合、paper_trading 専用 DB を使用し本番 DB と分離します。
- AI 機能は外部 API（OpenAI）に依存します。API 利用料金やレート制限に注意してください。429 等は内部でリトライ実装がありますが、限度はあります。
- process priority や CPU affinity の設定はプラットフォーム依存で psutil の権限に依存します。権限不足の場合はログに警告が出てスキップされます。
- DuckDB / SQLite のスキーママイグレーション（軽微な ALTER 等）は init_monitoring_db で処理します。より複雑なマイグレーションは別途ツールが必要です。

---

この README はリポジトリ内の主要スクリプトと API を要約したものです。詳細な設計（StrategyModel.md、PortfolioConstruction.md 等のドキュメント）に基づく実装注釈や、ExecutionEngine / BrokerClient の具体的な挙動は該当ソースとドキュメントを参照してください。質問や追加のドキュメント化希望があればお知らせください。