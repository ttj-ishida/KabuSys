# KabuSys

日本株自動売買システム（ライブラリ / 実行・監視ツール群）

このリポジトリは、戦略研究・ポートフォリオ構築・発注エンジン・監視基盤・AI 補助モジュールを含む日本株自動売買システムの実装例です。モジュール設計はテスト容易性・フェイルセーフ性・ルックアヘッドバイアス防止を重視しています。

---

## プロジェクト概要

主な目的：
- 研究（ファクター計算、特徴量探索）
- ポートフォリオ構築（候補選定・重み付け・株数決定）
- 発注実行（ExecutionEngine、OrderManager、Reconciler）
- 監視（System/Trade/Risk Monitor、Streamlit ダッシュボード、LINE 通知）
- AI 補助（ニュースのセンチメント評価、マーケットレジーム判定）
- Paper Trading 用の分離された DB と検証ツール

設計上の特徴：
- 設定は環境変数 / .env ファイルから読み込む（自動ロードを提供）
- paper_trading 環境は本番 DB と完全分離（data/paper_trading.db を使用）
- DuckDB を分析用（prices_daily, raw_financials 等）、SQLite を運用ログ（監視・注文ログ）に使用
- OpenAI API を利用する AI 部分はキー必須だが、API エラーはフェイルセーフで扱う設計

---

## 主な機能一覧

- 実行（Execution）
  - ExecutionEngine（起動・セッション実行）
  - Broker クライアント抽象化（本番 / モック切替）
  - OrderManager（注文生成・送信・状態同期）
  - Reconciler（再起動時の注文/ポジション同期）

- 監視（Monitoring）
  - SystemMonitor（CPU / メモリ / ディスク / pid ファイル / データ鮮度）
  - TradeMonitor（滞留注文 / 約定価格異常監視）
  - RiskMonitor（ドローダウン・ポジション上限監視）
  - KillSwitch（フラグファイルで ExecutionEngine 停止シグナル）
  - AlertManager（LINE Push による通知）
  - Streamlit ダッシュボード（監視情報可視化）
  - monitoring DB 初期化 / 永続化（SQLite）

- 研究・特徴量（Research）
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン、IC 計算、統計サマリー

- ポートフォリオ（Portfolio）
  - 候補選定、等重・スコア重み付け
  - リスク調整（セクター上限、レジーム乗数）
  - ポジションサイズ計算（ロット丸め、利用可能現金に応じたスケーリング）

- AI（OpenAI 連携）
  - ニュースセンチメント（kabusys.ai.news_nlp.score_news）
  - レジーム判定（kabusys.ai.regime_detector.score_regime）

- ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）
  - Streamlit ダッシュボード起動スクリプト

---

## セットアップ手順

前提
- Python 3.10+
- SQLite（標準で含まれます）
- DuckDB（Python パッケージ）
- ネットワーク接続（OpenAI を使用する場合）

推奨: 仮想環境を作成してからインストールしてください。

例（venv + pip）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
# 必要なパッケージの例
pip install duckdb psutil requests openai streamlit
# 開発/テスト用にパッケージをプロジェクトルートから利用する場合
# PYTHONPATH を通すかパッケージを editable インストール
pip install -e .
```

.env の自動読み込み
- プロジェクトルート（.git または pyproject.toml がある場所）に `.env` / `.env.local` を置くと自動で読み込みます。
- 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須（または重要な）環境変数（代表例）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須な機能がある場合）
- KABU_API_PASSWORD: kabuステーション API パスワード（Execution 本番連携時）
- OPENAI_API_KEY: OpenAI API を使用する場合に必要
- KABUSYS_ENV: 環境。`development` / `paper_trading` / `live` のいずれか
- LOG_LEVEL: ログレベル（例: INFO）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知を有効にする場合

PAPER_FILL_MODE（paper_trading 時の挙動）
- 有効値: "instant" / "partial" / "never" / "reject"
- デフォルト: "instant"

注意: Settings モジュールは .env のパースを独自実装しており、quoted value のエスケープや inline コメント処理などに対応しています。

---

## 使い方（実行例・コマンド）

Python モジュール形式で実行できます（プロジェクトルートにて PYTHONPATH=src を設定するか pip install -e . してください）。

1. ExecutionEngine（実取引 or Paper Trading）
```bash
# 本番/指定環境は KABUSYS_ENV による
export KABUSYS_ENV=paper_trading
python -m kabusys.run_execution
```
- `paper_trading` の場合は MockBrokerClient を使用し、記録先は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）になります。
- 起動時に PID ファイルを書き、stop シグナルは data/kill.flag で制御されます（Paths は Settings により上書き可）。

2. 監視プロセス（SystemMonitor のポーリング）
```bash
# 監視ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で秒指定（デフォルト 60）
export MONITOR_POLL_INTERVAL=60
python -m kabusys.run_monitoring
```
- Monitoring は KABUSYS_ENV にかかわらず production の sqlite_path を使用して記録します（監視ログは本番 DB に保存される設計）。
- プロセス優先度を High に設定しようとします（psutil が必要、失敗時は警告でスキップ）。

3. Streamlit ダッシュボード（監視 UI）
```bash
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```
- デフォルトは `data/monitoring.db`（読み取り専用 URI で開く）。

4. Paper Trading 検証レポート
```bash
# デフォルト DB: data/paper_trading.db
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# または明示的に DB 指定
python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
```
- 稼働率・注文成功率・送信率・P95 レイテンシなどを出力します。

5. AI モジュール（プログラム的利用）
- ニューススコアリング:
  - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
- レジーム判定:
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
- どちらも OpenAI API キーが必要（api_key 引数または環境変数 OPENAI_API_KEY）。

6. 簡単な使い方（ライブラリ呼び出し）
- 研究用途:
  - from kabusys.research import calc_momentum, calc_value, calc_volatility
- ポートフォリオ構築:
  - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_position_sizes

---

## 動作上の注意点 / オペレーション

- .env の自動ロードはプロジェクトルートを .git または pyproject.toml で検出して行います。テスト等で自動ロードを避ける場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Paper Trading は本番 DB と分離することを強く推奨します（Settings.is_paper を参照）。
- AI 呼び出しはレート制限やネットワーク障害に対してリトライやフォールバックを実装していますが、API キーやクォータに注意してください。
- KillSwitch は監視がトリガーしたときに kill.flag を作成します。ExecutionEngine は起動時にこのフラグをクリアする設定（Settings.kill_flag_clear_on_start）を持っています。
- プロセス優先度や CPU affinity の設定は psutil に依存します。権限不足や未対応 OS の場合は警告で継続します。

---

## ディレクトリ構成（抜粋）

以下は主なファイル・モジュールのツリーです（src/kabusys 配下）:

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数 / 設定管理
  - run_execution.py                — ExecutionEngine 起動スクリプト
  - run_monitoring.py               — SystemMonitor ポーリングスクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py  — Paper Trading 検証レポート
  - data/                            — （DuckDB / データパイプライン等は別モジュール想定）
  - portfolio/
    - __init__.py
    - portfolio_builder.py           — 候補選定 / 重み計算
    - risk_adjustment.py             — セクター上限・レジーム乗数
    - position_sizing.py             — 株数決定・スケーリング
  - research/
    - __init__.py
    - factor_research.py             — Momentum / Volatility / Value
    - feature_exploration.py         — 前方リターン / IC / 統計
  - ai/
    - __init__.py
    - news_nlp.py                    — ニュースセンチメント（OpenAI）
    - regime_detector.py             — マーケットレジーム判定（OpenAI）
  - execution/
    - reconciler.py
    - order_manager.py
    - ...                            — Broker API / OrderRepository 等（抜粋あり）
  - monitoring/
    - __init__.py
    - monitoring_db.py               — SQLite スキーマと永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - utils/
    - __init__.py
    - process_priority.py            — psutil を使った優先度/affinity 設定

（注）実際のリポジトリには上記以外の補助モジュール・テスト・ドキュメントが含まれる場合があります。

---

## 開発者向け補足

- Settings クラスはプロセス全体で共有される単一の読み取り専用インターフェースを提供します（settings = Settings()）。
- DuckDB の接続オブジェクトは research / ai モジュールへ引き渡して SQL でデータ処理を行う設計です。
- MonitoringDB はシンプルな CRUD を提供し、スキーマの互換性維持のためマイグレーション処理（カラム追加）を備えています。
- OpenAI SDK の呼び出しはラッパー関数で行われ、テスト時はモック置換が容易にできる設計になっています。

---

README の内容やサンプルコマンドについて不明点や実行環境に合わせた具体的な手順（systemd ユニット、Dockerfile、CI 構成など）が必要であれば、利用環境（OS、Python バージョン、実行方式）を教えてください。必要に応じて systemd サービス定義例や Docker ベースの起動手順も用意します。