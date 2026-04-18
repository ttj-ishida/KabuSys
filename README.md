# KabuSys

日本株向け自動売買システムのリポジトリ（ライブラリ風構成）。
この README はコードベース（src/kabusys/**）を基にした概要、機能、セットアップ、使い方、ディレクトリ構成の説明です。

注意: 実際に本番運用する前に必ず `.env` を正しく設定し、`python -m kabusys.validate_config` で検証してください。

---

## プロジェクト概要

KabuSys は日本株の自動売買・研究・監視を行うためのモジュール群を含むプロジェクトです。主な構成要素は以下：

- ExecutionEngine（発注・オーダー管理・リスク管理）
- Monitoring（システム稼働・注文・リスクの定期チェックとアラート／Kill Switch）
- Portfolio construction（候補選定、配分、ポジションサイズ計算、セクター制限）
- Research（ファクター算出、将来リターン、IC 等）
- AI 支援（ニュースの NLP スコアリング、マーケットレジーム判定）
- 各種ユーティリティ（設定読み込み、ログ設定、プロセス優先度、CLI ツール）

設計方針の一部：
- DuckDB と SQLite をデータ格納に使用（分析用 / 監視用に分離）
- .env ベースの設定（`config_setup` でウィザード生成、`validate_config` で検査）
- Paper trading と Live を分離（paper_trading は専用 SQLite を使用）
- AI 部分は OpenAI API（gpt-4o-mini等）を利用（APIキー必須）

---

## 主な機能一覧

- 実行（Execution）:
  - Broker クライアント抽象化（本番／モック切替）
  - OrderManager / Reconciler / RiskManager による発注と整合性管理
  - ExecutionEngine によるセッション駆動の実行ループ

- 監視（Monitoring）:
  - SystemMonitor: CPU/メモリ/ディスク/プロセス稼働・データ鮮度監視
  - TradeMonitor: 注文の滞留・約定異常などの監視（該当コードが存在）
  - RiskMonitor: ドローダウン・ポジション上限検出とログ
  - KillSwitch: 条件に応じて `data/kill.flag` を書き込み、ExecutionEngine 停止シグナルを送出
  - MonitoringEngine: 上記モニタを束ねたポーリングループ

- ポートフォリオ構築:
  - 候補選定（スコア順）、等金額 / スコア加重配分
  - セクターキャップ適用、レジーム乗数
  - ポジションサイズ計算（単元株丸め、リスクベース配分、aggregate cap）

- 研究（Research）:
  - モメンタム・ボラティリティ・バリュー等のファクター算出（DuckDB を利用）
  - 将来リターン・IC 計算、ファクター統計サマリー

- AI（OpenAI）:
  - ニュース NLP による銘柄別センチメントスコア算出（ai_scores への書込）
  - マクロニュース＋ETF MA を使った市場レジーム判定（market_regime テーブルへ書込）
  - リトライ、レスポンス検証、部分成功の安全な DB 書き込みを含む

- ツール:
  - `.env` 対話ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成（tools/paper_verification_report）

---

## セットアップ手順（ローカル開発向け）

1. Python 環境
   - Python 3.10+ を推奨（プロジェクトの型ヒント等に合わせてください）
   - 仮想環境を作成：
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要ライブラリのインストール
   - requirements.txt がない場合は主に以下が必要になります：
     - duckdb, psutil, openai, pyyaml (任意: config YAML チェック)
   - 例：
     - pip install duckdb psutil openai PyYAML

3. プロジェクトルート（.git または pyproject.toml があるディレクトリ）に移動してから `.env` を作成
   - 対話ウィザードで生成：
     - python -m kabusys.config_setup
   - あるいは手動で `.env` を作成（例は下記）

4. 設定検証
   - python -m kabusys.validate_config
   - 必須環境変数等が正しく設定されているかチェックします。

5. データディレクトリ作成（通常は自動作成されますが最初に準備しておくと安全）
   - mkdir -p data logs

6. OpenAI を使う機能を使う場合：
   - 環境変数 OPENAI_API_KEY を設定

必須の主な環境変数（Settings クラス参照）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- OPENAI_API_KEY（AI 機能使用時必須）
- KABUSYS_ENV（development / paper_trading / live、デフォルト development）
- DUCKDB_PATH（デフォルト data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト data/paper_trading.db）
- LOG_LEVEL（DEBUG/INFO/...）

簡易 .env 例:
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
OPENAI_API_KEY=sk-...
LOG_LEVEL=INFO
```

---

## 使い方（起動・実行例）

- 設定ウィザード:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - 警告も失敗にしたい場合は `--strict` を付ける

- 監視プロセス起動（Monitoring）:
  - python -m kabusys.run_monitoring
  - 環境変数でポーリング間隔を変更:
    - export MONITOR_POLL_INTERVAL=30
  - 監視は常に本番の sqlite_path（Settings.sqlite_path）を使用します（環境に依らず）。

- 実行エンジン起動（ExecutionEngine）:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を設定しておくと MockBroker を使用し、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録されます。
  - run_execution は `data/stop_requested.flag` を監視しており、存在すると起動・継続を停止します。

- 停止方法:
  - プロセス自体を Ctrl+C で割り込み可能
  - 運用系の停止シグナルはプロジェクトの data/stop_requested.flag（停止要求）や data/kill.flag（Kill Switch）を使用
    - run_monitoring / run_execution はそれぞれ stop フラグの存在を見て終了します。
  - KillSwitch（監視側）によって `data/kill.flag` が書き込まれると ExecutionEngine は停止するよう設計されています。

- Paper Trading 検証レポート生成:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - `--db` で別 DB を指定可能。環境変数 PAPER_TRADING_SQLITE_PATH が優先されます。

- AI 機能（プログラム的呼び出し例）
  - ニューススコアリング:
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key=None)
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key=None)
  - いずれも OPENAI_API_KEY 環境変数を使うことができます。

ログ:
- ログはデフォルト `logs/` に日次ローテーションで保存されます（kab usys.utils.logging_setup）。

注意点:
- Paper trading と Live は DB を分離しています。誤って本番 DB にペーパートレードの記録を混ぜないように注意してください。
- AI 呼び出し（OpenAI）はコストやレスポンスの不安定さがあるため、失敗時はフェイルセーフ（スコア 0 / スキップ等）になる設計です。

---

## 主要 CLI / スクリプト一覧

- python -m kabusys.config_setup
  - .env を対話式に生成・更新

- python -m kabusys.validate_config [--strict]
  - .env / config/*.yaml / DB パス等の事前チェック

- python -m kabusys.run_monitoring
  - SystemMonitor をポーリングして monitoring DB にログ、KillSwitch 評価等を行う

- python -m kabusys.run_execution
  - ExecutionEngine を起動（paper_trading 時は MockBroker を使用）

- python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - Paper trading の検証レポートを標準出力に生成

---

## ディレクトリ構成

以下は src/kabusys 以下の代表的なファイル／ディレクトリ構成（抜粋）です：

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/設定読み込み
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_monitoring.py        — Monitoring 起動スクリプト
  - run_execution.py         — Execution 起動スクリプト

  - ai/
    - news_nlp.py            — ニュース NLP スコアリング
    - regime_detector.py     — 市場レジーム判定
  - monitoring/
    - monitoring_db.py       — SQLite テーブル作成 / 永続層
    - system_monitor.py      — CPU/メモリ/PID/データ鮮度監視
    - trade_monitor.py       — (注文監視: code に依存する)
    - risk_monitor.py        — ドローダウン／ポジション制限監視
    - kill_switch.py         — kill.flag 書き込みロジック
    - monitoring_engine.py   — 複数 Monitor を束ねるエンジン
    - alert_manager.py       — （存在すれば）アラート送信管理
  - execution/
    - execution_engine.py    — 実行エンジン（注文ループ等）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py      — Broker クライアント生成（Mock/Real）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - data/                     — 実行時生成（DBファイル・pid/flag等）

実行スクリプトはプロジェクトルート（src/ の親）を起点に `data/` や `logs/` を参照/作成します。

---

## DB / マイグレーション

- monitoring_db.init_monitoring_db(conn) が初回実行時にテーブルを作成し、簡易マイグレーション（カラム追加）を行います。
- DuckDB は分析用データ（prices_daily, raw_financials, raw_news 等）を格納する想定です。

---

## 追加の注意・運用上のポイント

- 本番（KABUSYS_ENV=live）では LINE 通知等の設定が未設定だとアラートが届かない点に注意。validate_config で確認してください。
- `KILL_FLAG_CLEAR_ON_START` が `1` に設定されていると起動時に kill.flag を自動でクリアしますが、本番では `0` を推奨します。
- プロセス優先度設定（psutil を使用）を行います。権限により設定失敗する場合がありますが、警告ログで継続します。
- OpenAI API 呼び出しではレート制限・5xx・タイムアウトを考慮したリトライ実装がありますが、コスト管理に注意してください。

---

必要であれば、この README をベースに「運用手順（デプロイ / systemd ユニット例）」「監視アラート設定」「API / DB スキーマ詳細」のセクションを追加できます。どの情報を優先して追加しますか？