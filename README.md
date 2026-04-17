# KabuSys

日本株自動売買システムのコードベース。戦略の研究（ファクター計算・特徴量解析）、ポートフォリオ構築、発注実行（ExecutionEngine）、監視（Monitoring）および関連ツール・ユーティリティ群を含みます。

---

プロジェクト内の実装は、外部の実口座・APIへ直接命令を出さない設計（ペーパートレードや検証環境での分離）と、ルックアヘッドバイアス防止の方針を重視しています。

主な特徴・コンポーネント、セットアップ／起動方法、ディレクトリ構成を以下にまとめます。

## 機能一覧（概要）
- Execution（発注エンジン）
  - ExecutionEngine による発注セッション管理
  - BrokerClientFactory により実口座／Mock（ペーパートレード）を切替
  - OrderRepository / OrderManager / RiskManager / Reconciler 等の構成
- Monitoring（監視）
  - SystemMonitor: プロセス生存確認、CPU/メモリ/ディスク、データ鮮度チェック
  - TradeMonitor: 滞留注文（stale orders）、約定価格の異常検出
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新
  - KillSwitch: 条件に応じた停止フラグ（data/kill.flag）作成
  - MonitoringEngine: 各 Monitor を束ねてポーリング/アラート送出
- Portfolio（ポートフォリオ構築）
  - 候補選定（スコア順）、等金額／スコア加重配分
  - セクター集中制限、レジームに応じた投下資金乗数
  - ポジションサイズ計算（単元株丸め、リスク制限、aggregate cap）
- Research（研究用）
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
  - DuckDB を利用した高性能な時系列処理
- AI（ニュース NLP / レジーム判定）
  - OpenAI（gpt-4o-mini 想定）でニュースをスコアリングし ai_scores に保存
  - マクロニュース＋ETF MA を合成して市場レジーム（bull/neutral/bear）判定
- Tools
  - Paper Trading 検証レポート作成スクリプト（kabusys.tools.paper_verification_report）
- 設定関連
  - .env 自動読み込み（プロジェクトルート検出）
  - 対話式 .env 作成ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）

---

## 必要条件（推奨）
- Python 3.10+（型ヒントで Union 表記や match 等を使用していないが、3.10 以降が望ましい）
- 必須パッケージ（例）
  - duckdb
  - psutil
  - openai
- 任意（機能に応じてインストール）
  - PyYAML（config/*.yaml の構文チェックに使用。なければ警告）
- インストール例:
  - pip install duckdb psutil openai PyYAML

（requirements.txt は本リポジトリに含まれていない場合があるため、必要に応じて上記を手動でインストールしてください。）

---

## 環境変数（主なもの）
以下は Settings クラス / config_setup ウィザードで扱う主な環境変数とデフォルトの例：

- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 実行環境
  - KABUSYS_ENV — "development" | "paper_trading" | "live"（デフォルト: development）
    - paper_trading: MockBrokerClient を使用し、paper_trading DB に記録（本番 DB と分離）
    - live: 実際に発注される本番モード
- DB / ファイルパス
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB、デフォルト: data/paper_trading.db）
  - PID_FILE_PATH（エンジンの PID ファイル、デフォルト: data/execution.pid）
  - KILL_FLAG_PATH（Kill Switch flag、デフォルト: data/kill.flag）
- ログレベル等
  - LOG_LEVEL（"DEBUG" / "INFO" / ...、デフォルト: INFO）
- AI
  - OPENAI_API_KEY — OpenAI API キー（AI モジュールを利用する際に必要）

その他の設定項目は config_setup.py のウィザード / Settings クラスのプロパティを参照してください。

---

## セットアップ手順（推奨ワークフロー）
1. リポジトリをクローン / 配布物を配置
2. 仮想環境を作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate
3. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML
4. 対話式に .env を作成
   - python -m kabusys.config_setup
   - もしくは .env を手動で作成（.env.example を参考に）
5. 設定検証
   - python -m kabusys.validate_config
   - 問題があれば修正。--strict を指定すると警告も失敗扱いになります。
6. データディレクトリの作成（必要に応じて）
   - mkdir -p data

---

## 使い方（主要スクリプト / コマンド例）

- 実行エンジン（ExecutionEngine）を起動
  - 簡単起動:
    - python -m kabusys.run_execution
  - ペーパートレードで起動するには:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - ペーパートレード時はデフォルトで data/paper_trading.db に記録され、本番 DB と分離されます。
  - 停止方法:
    - data/stop_requested.flag を作成すると起動中の run_execution / run_monitoring が終了処理を行います。
    - Kill Switch（条件に応じた自動停止）によって data/kill.flag が書き込まれると ExecutionEngine は停止します。

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数で変更可能:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    - デフォルト 60 秒
  - 監視は常に本番用 sqlite_path（Settings.sqlite_path）を参照します（環境にかかわらず）。

- .env 対話式セットアップ
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗（exit 1）になります。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  - デフォルトの DB パスは環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db。

- AI（ニュース NLP / レジーム判定）をプログラムから利用
  - 例: ニューススコアリング
    - from datetime import date
      import duckdb
      from kabusys.ai.news_nlp import score_news
      conn = duckdb.connect("data/kabusys.duckdb")
      score_news(conn, date(2026, 4, 11), api_key="sk-...")
    - api_key を省略すると環境変数 OPENAI_API_KEY を参照します。
  - 例: レジーム判定
    - from kabusys.ai.regime_detector import score_regime
      score_regime(conn, date(2026, 4, 11), api_key="sk-...")

注意: OpenAI を使う処理は API キーおよび通信のコストが発生します。テスト時はモック化（unittest.mock.patch）して呼び出しを置き換えられます。

---

## 実行時のファイル・フラグ
- data/execution.pid — 実行エンジンの PID（存在しない場合はプロセス未起動扱い）
- data/stop_requested.flag — 管理者が作成すると run_* スクリプトが安全に停止
- data/kill.flag — KillSwitch による自動停止要求（ExecutionEngine 起動時に設定に応じて消去される場合あり）
- デフォルト DBパス:
  - DuckDB: data/kabusys.duckdb
  - Monitoring SQLite: data/monitoring.db
  - Paper trading SQLite: data/paper_trading.db

---

## ディレクトリ構成（抜粋）
（src/kabusys 配下の主要モジュールを示します）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (監視アラート管理の実装箇所)
  - execution/                — Execution 関連コンポーネント群（OrderManager など）
  - data/                     — スクリプト実行で使われるデータファイル格納想定（data/*.db, pid, flag）
  - utils/
    - process_priority.py     — プロセス優先度 / CPU affinity ユーティリティ
    - __init__.py

（上記は実装ファイルの一部抜粋です。詳細はソースツリーを参照してください。）

---

## 実運用時の注意点
- KABUSYS_ENV を "live" に設定する場合は、LINE 通知設定や Kill Switch の動作等を十分に確認してください（validate_config で警告を表示します）。
- .env は機密情報（API トークン等）を含むため、絶対に Git へコミットしないでください。
- OpenAI の呼び出しにはレート制限や一時的エラーがあります。AI モジュールはリトライ・フェイルセーフ実装を備えていますが、運用時は API 使用量・コストに注意してください。
- run_* スクリプトは起動時にプロセス優先度を high に設定しようとしますが、OS や権限によっては設定に失敗する場合があります（警告ログが出ます）。

---

## トラブルシューティング
- 設定検証で必須環境変数のエラーが出る:
  - python -m kabusys.config_setup で .env を作成し、python -m kabusys.validate_config で確認
- DuckDB / SQLite ファイルの親ディレクトリが存在しない:
  - 起動時に自動作成される場合がありますが、必要に応じて data ディレクトリを手動作成してください。
- OpenAI API 呼び出しで失敗する:
  - OPENAI_API_KEY が設定されているか確認。レート制限・ネットワークエラーはログにリトライ情報が出ます。

---

この README は概略を示すものです。各モジュールの詳細な仕様や設計背景は、ソースコード内の docstring コメントや注釈（日本語コメント）に記載されています。運用・開発時は該当モジュールのドキュメント（ソース内コメント）を参照してください。