# KabuSys

日本株向け自動売買システム（KabuSys）のコードベース README（日本語）。

このリポジトリはアルゴリズム取引のコア機能（シグナル・ポートフォリオ構築・発注実行・監視・研究ツール・ニュースNLP 等）を含むモジュール群で構成されています。

---

## 概要

KabuSys は以下の責務を持つモジュール群から構成された自動売買フレームワークです。

- 発注エンジン（ExecutionEngine）: ブローカークライアント経由で注文を発行／管理。paper_trading モードで MockBroker を使用し本番 DB と分離。
- 監視（Monitoring）: システム状態・注文状況・リスク（ドローダウン・ポジション上限）を定期チェックしログ・アラートを出す。
- ポートフォリオ構築: 候補選定、重み計算、ポジションサイズ決定、セクター上限・レジーム補正などの純粋関数群。
- 研究（Research）: DuckDB を用いたファクター・将来リターン・IC 計算等の分析ツール。
- AI モジュール: ニュースのセンチメントスコアリング（OpenAI）や市場レジーム判定（LLM + テクニカル）を提供。
- ユーティリティ: 設定読み込み、ログ設定、プロセス優先度設定など共通ユーティリティ。
- 管理ツール: .env 対話式セットアップ（config_setup）、起動前設定検証（validate_config）、検証レポート生成ツール等。

設計上のポイント:
- 環境変数 / .env による設定管理（Settings クラス）
- paper_trading と live を切り替えて DB を分離
- DuckDB を分析・研究用に利用、SQLite を監視/発注ログ用に利用
- LLM 呼び出しはキーの注入・リトライ・レスポンス検証を行い失敗時は安全側にフォールバック

---

## 主な機能一覧

- 設定管理
  - .env 自動読み込み（プロジェクトルートを探索）
  - 対話式ウィザード: python -m kabusys.config_setup
  - 設定検証 CLI: python -m kabusys.validate_config
- 実行（Execution）
  - ExecutionEngine 起動: python -m kabusys.run_execution
  - paper_trading モードで MockBrokerClient 使用（paper DB: data/paper_trading.db）
  - Kill Switch（data/kill.flag）による安全停止
- 監視（Monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - run_monitoring スクリプト: python -m kabusys.run_monitoring
  - ポーリング間隔を環境変数 MONITOR_POLL_INTERVAL で制御（デフォルト 60 秒）
  - stop_requested.flag による監視停止
- ポートフォリオ構築
  - 候補選定、等分配／スコア配分、リスクベースのポジションサイズ計算、セクターキャップ、レジーム乗数
- 研究・分析
  - DuckDB 接続を受け取るファクター計算（モメンタム・ボラティリティ・バリュー等）
  - 将来リターン・IC・統計サマリ
- AI（ニュースNLP・レジーム判定）
  - OpenAI（gpt-4o-mini）でニュースのセンチメント評価（ai_scores テーブルへ保存）
  - マクロニュース＋MA200乖離で市場レジーム判定（market_regime テーブルへ保存）
- ツール
  - Paper Trading 検証レポート生成（python -m kabusys.tools.paper_verification_report）
  - 各種 DB / ログ操作ユーティリティ

---

## 要件（推奨）

- Python 3.10 以上（ソースの型注釈で | を使用）
- 必要なパッケージ（代表例）
  - duckdb
  - psutil
  - openai
  - （任意）PyYAML（設定ファイル YAML のパース検証に利用）
- SQLite3（標準ライブラリ）
- （実行環境により）kabuステーション API 等への接続設定

requirements.txt はリポジトリに無い場合があるため、必要パッケージを pip で個別にインストールしてください。

例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順（クイックスタート）

1. リポジトリをクローンし、仮想環境を作成して必要パッケージをインストール。

2. 対話式に .env を作成:
```
python -m kabusys.config_setup
```
ウィザードは J-Quants / kabu API / DB パス等を聞きます。生成された .env は Git にコミットしないでください。

3. 設定検証:
```
python -m kabusys.validate_config
# 厳格モード（警告も失敗扱い）:
python -m kabusys.validate_config --strict
```

4. ログディレクトリ確認:
- デフォルトは `logs/`。`LOG_DIR` 環境変数で変更可能。
- ログ出力は daily ローテーション（30 日保存）。

5. DB 初期化
- 実行スクリプト起動時に必要テーブルは自動で作成される（monitoring.db 等）。
- Paper trading の専用 DB は `PAPER_TRADING_SQLITE_PATH`（デフォルト: data/paper_trading.db）。

---

## 環境変数（主なもの）

- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading 時の約定モード（instant / partial / never / reject）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログ保存ディレクトリ（デフォルト: logs/）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合必須）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（任意）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング秒数（デフォルト: 60）

---

## 使い方（主要コマンド）

- .env ウィザード（対話式）
```
python -m kabusys.config_setup
```

- 設定検証
```
python -m kabusys.validate_config
```

- 監視ループ起動（SystemMonitor）
```
python -m kabusys.run_monitoring
# ポーリング間隔を上書き:
MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
```
注意: run_monitoring は data/stop_requested.flag の存在を検知すると終了します。Monitoring は本番 sqlite_path を使用（環境に依らず）。

- Execution エンジン起動
```
python -m kabusys.run_execution
```
- KABUSYS_ENV=paper_trading のときは MockBrokerClient を使い `data/paper_trading.db` に記録します（本番 DB と分離）。

- Paper Trading 検証レポート生成
```
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# DB 指定:
python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
```

- AI 機能（プログラム内 API）
  - ニュースセンチメント: kabusys.ai.score_news(conn, target_date, api_key=None)
  - レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

---

## 停止・Kill Switch

- ExecutionEngine 停止要求（外部からの安全停止）は `data/kill.flag` を書き込むことで実行可能（KillSwitch）。
- Monitoring 停止要求は `data/stop_requested.flag`（run_monitoring が検知してループ終了）。
- run_execution は起動時に `data/stop_requested.flag` が存在する場合、起動を行わず終了します。

---

## ログ

- ログは stdout とファイルに出力されます。
- デフォルトのログファイル: logs/<app_name>.log（app_name 例: execution, monitoring）
- 日次ローテート・30日保持
- ログレベルは環境変数 LOG_LEVEL または setup_logging の引数で変更可能

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 配下の主要モジュールと簡易説明です。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理（自動 .env ロード含む）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（監視テーブル）
    - system_monitor.py      — システム状態 / データ鮮度監視
    - trade_monitor.py       — （注文監視、ファイル内で参照あり）
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — kill.flag 管理
    - monitoring_engine.py   — 各 Monitor を束ねる
    - alert_manager.py       — （アラート送信管理、ファイル内で参照あり）
  - execution/
    - execution_engine.py    — ExecutionEngine（エンジン本体）
    - broker_factory.py      — ブローカークライアント生成（Mock / 実ブローカ）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み計算
    - position_sizing.py     — 株数決定・スケーリング
    - risk_adjustment.py     — セクター上限・レジーム乗数
  - research/
    - factor_research.py     — Momentum / Volatility / Value ファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン・IC・統計サマリ
  - ai/
    - news_nlp.py            — ニュースの LLM スコアリング（ai_scores 書込）
    - regime_detector.py     — 市場レジーム判定（MA200 + LLM）
  - data/                    — 実行時に使用する DB / flag / pid 等（config でパスを変更可）
  - logs/                    — デフォルトログ保存先

（実際のファイル数はリポジトリ全体を参照してください。上は主要モジュールの抜粋です）

---

## 実運用上の注意

- KABUSYS_ENV=live の場合は十分に設定を確認してから起動してください（validate_config の警告に注意）。
- .env は秘密情報を含むため絶対にリポジトリにコミットしないでください。
- OpenAI キーを使う機能は API コスト・レイテンシ・利用制限に注意して運用してください。失敗時はフェイルセーフでスコア 0.0 等にフォールバックしますが、設計上は外部依存点です。
- paper_trading は実際の発注文を行わず分離 DB に記録するため、安全に動作確認ができます。

---

## 開発 / 貢献

- コードの設計方針や詳細はソース内の docstring / コメントを参照してください。
- 新しい機能追加やバグ修正はユニットテストおよび手動検証を行ってください。
- config/*.yaml（システム設定等）が必要な場合は `scripts/generate_config.py` 等の補助スクリプトを利用してください（存在する場合）。

---

README に収まりきらない内部挙動や API の詳細は、各モジュール（特に ai/*.py、monitoring/*.py、portfolio/*.py、research/*.py、execution/*.py）の docstring を参照してください。必要ならば特定モジュールに対するより詳しいドキュメントを生成しますので、どの部分を深掘りしたいか教えてください。