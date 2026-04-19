# KabuSys

日本株自動売買システムの Python コードベース向け README（日本語）

概要、機能、セットアップ手順、使い方、ディレクトリ構成をまとめています。

---

## プロジェクト概要

KabuSys は日本株の自動売買（Execution）とそれを補助する監視（Monitoring）、ポートフォリオ構築、リサーチ、AI（ニュース NLP / レジーム判定）などのコンポーネントを含むモジュール群です。  
主に次のような責務を持つモジュール群で構成されています。

- ExecutionEngine（発注エンジン）と Broker クライアント（本番 / ペーパートレード切替）
- Monitoring（稼働・注文・リスク監視、Kill Switch）
- Portfolio construction（候補選定、重み計算、ポジションサイジング）
- Research（ファクター計算・特徴量探索）
- AI モジュール（ニュースセンチメント / レジーム判定、OpenAI の利用）
- 各種ユーティリティ（設定読み込み、ログ設定、プロセス優先度設定等）
- 運用向けツール（.env 設定ウィザード、設定検証、Paper Trading 検証レポート）

バイナリ配布や Docker ではなく、Python パッケージとして実行する想定です。設定は環境変数（.env）で行います。

---

## 主な機能一覧

- Execution
  - 実際のブローカー（kabuステーション等）または MockBroker を使ったペーパートレード実行
  - Order 管理、リスク管理、Reconciler 等の統合
- Monitoring
  - システム（CPU / メモリ / ディスク）の定期ポーリング
  - データ鮮度チェック（価格データの更新確認）
  - 注文ログ / 約定ログ / リスクログ / ダッシュボード保存（SQLite）
  - Kill Switch（閾値超過時に停止フラグを書き込み、Execution を停止）
  - アラート送信（LINE 等、設定に応じて）
- Portfolio
  - 候補選定、等配分 / スコア加重配分
  - セクター制限、レジーム乗数適用
  - ポジションサイズ計算（単元株丸め、利用可能現金・上限考慮）
- Research
  - Momentum / Volatility / Value 等のファクター計算（DuckDB 使用）
  - 将来リターン計算、IC（情報係数）計算、統計サマリー
- AI
  - ニュースの記事群を OpenAI（gpt-4o-mini）でスコアリングして ai_scores に保存
  - マクロニュース + ETF MA200 の合成による市場レジーム判定（market_regime テーブル）
- 運用ツール
  - .env 対話式ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

---

## 必要条件 / 依存パッケージ

（実際の requirements.txt は含まれていない想定のため、代表的な依存を列挙します）

- Python 3.9+
- duckdb
- psutil
- openai (AI モジュール使用時)
- PyYAML（config/*.yaml の内容検証を行う場合に必要）
- sqlite3（標準ライブラリ）
- そのほか: 標準ライブラリ（logging, pathlib, threading, datetime 等）

インストール例（仮）:
```
pip install duckdb psutil openai pyyaml
```

注: 実運用では仮想環境を作成して依存を固定してください。

---

## 環境変数（重要なもの）

主要設定は環境変数またはプロジェクトルートの `.env` / `.env.local` で行います。自動で `.env` をロードする仕組みが組み込まれています（必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

必須（最低限設定が必要なもの）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

運用上よく使う / 値の例
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
- SQLITE_PATH: data/monitoring.db（デフォルト）
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（ペーパートレード用 DB）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL
- OPENAI_API_KEY: OpenAI 利用時に必要
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知設定
- KILL_FLAG_CLEAR_ON_START: 1 にすると起動時に kill.flag を自動クリア（本番では 0 推奨）
- MONITOR_POLL_INTERVAL: monitoring のポーリング間隔（秒、デフォルト 60）

詳しいキーは `kabusys.config.Settings` を参照してください。

---

## セットアップ手順

1. リポジトリをクローンしてワークディレクトリへ移動
2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb psutil openai pyyaml
   - （必要に応じて他パッケージを追加）
4. 初回設定 (.env) を作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - または `.env.example` を参照して手動作成（リポジトリに例ファイルがある場合）
5. 設定検証（任意）
   - python -m kabusys.validate_config
   - 問題を厳密に扱う場合は --strict を付ける（警告も FAIL 扱い）
6. ディレクトリ作成
   - デフォルトで使う `data/` や `logs/` を自動作成しますが、権限等で失敗する場合は手動で作成してください。

注意:
- OpenAI を使う機能（news_nlp / regime_detector）を使う場合は OPENAI_API_KEY を設定してください。
- ペーパートレードを実行する場合は KABUSYS_ENV=paper_trading と設定すると専用の SQLite（PAPER_TRADING_SQLITE_PATH）へ記録され、本番 DB と分離されます。

---

## 使い方（代表的コマンド）

起動スクリプトはモジュール実行を想定しています。

- Monitoring をデーモン的に動かす（ポーリング）
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（秒、デフォルト 60）
  - 停止: プロジェクトルートの data/stop_requested.flag を作成すると停止ループが検知して終了します

- ExecutionEngine を起動（発注エンジン）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、data/paper_trading.db に記録します（本番 DB と分離）
  - 起動時に data/stop_requested.flag が存在すると起動せずに終了します
  - Engine の停止シグナルは data/stop_requested.flag / data/kill.flag を用いる運用になっています

- .env 対話式ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告もエラー扱いで exit(1)

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  - デフォルト DB パスは PAPER_TRADING_SQLITE_PATH 環境変数または data/paper_trading.db

- ライブラリ（プログラムからの利用）
  - portfolio 関連:
    - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_position_sizes, ...
  - research / ai:
    - from kabusys.research import calc_momentum, calc_volatility, calc_value, ...
    - from kabusys.ai import score_news

---

## 運用上のポイント / トラブルシューティング

- Kill Switch / Stop フラグ
  - data/kill.flag: Kill Switch が発動した理由を記録するフラグファイル（ExecutionEngine 側で検知して停止）
  - data/stop_requested.flag: run_monitoring / run_execution のループ停止に使用
  - 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動消去しますが、本番では 0 推奨

- ログ
  - ログ出力は kabusys.utils.logging_setup.setup_logging で統一管理
  - デフォルトログディレクトリは logs/、ファイル名は app_name に依存（例: logs/execution.log）
  - 環境変数 LOG_DIR で変更可能

- DB マイグレーション
  - monitoring DB の初期化は monitoring_db.init_monitoring_db が冪等に実行（起動スクリプトで呼ばれます）
  - 古い DB に対する軽微なカラム追加（例: peak_value, latency_ms）のマイグレーション処理が含まれています

- OpenAI 呼び出し
  - AI 関連は外部 API 呼び出しが含まれるため、API の失敗（429/5xx/ネットワーク断等）に対してリトライやフェイルセーフ（スコア 0.0 など）を実装済みです
  - テスト時は該当モジュール内の API 呼び出し用関数をモックすることを想定しています

---

## ディレクトリ構成（主要ファイル）

以下はソースツリー（src/kabusys）にある主要モジュールの抜粋です。プロジェクトルートを基準とした相対パスを示します。

- src/kabusys/
  - __init__.py
  - config.py                   — 環境変数 / .env 自動読み込み、Settings クラス
  - config_setup.py             — .env 対話式ウィザード
  - validate_config.py          — 設定検証 CLI
  - run_monitoring.py           — Monitoring ポーリングループ起動スクリプト
  - run_execution.py            — ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - utils/
    - __init__.py
    - logging_setup.py          — ログ初期化ユーティリティ
    - process_priority.py       — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py          — SQLite ベースの永続化層
    - system_monitor.py         — システム状態・データ鮮度監視
    - trade_monitor.py          — （注文関連の監視: ソース参照）
    - risk_monitor.py           — ドローダウン・ポジション上限監視
    - kill_switch.py            — kill.flag 操作用ユーティリティ
    - monitoring_engine.py      — 各 Monitor を束ねる
    - alert_manager.py          — （LINE 等への通知管理: ソース参照）
  - execution/
    - execution_engine.py       — Execution エンジン本体（EngineConfig 等）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
  - portfolio/
    - portfolio_builder.py      — 候補選定 / 重み計算
    - position_sizing.py        — 発注株数計算
    - risk_adjustment.py        — セクターキャップ / レジーム乗数
  - research/
    - factor_research.py        — ファクター計算（momentum, volatility, value）
    - feature_exploration.py    — 将来リターン / IC / 統計サマリー
  - ai/
    - news_nlp.py               — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py        — レジーム判定（MA200 + マクロセンチメント）
  - data/                       — デフォルト DB / flag 等（実行時に使用）
  - logs/                       — ログ出力先（デフォルト）

（注）実際の細かいファイルはリポジトリに従ってください。上記は主要モジュールの概観です。

---

## 開発 / テスト時のヒント

- 自動環境変数ロードは .env / .env.local をプロジェクトルートから見つけて読み込みます。テストで自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI を使うユニットテストは API 呼び出し部分を patch / mock して外部通信を行わないようにしてください（ソース中にモック差替えを前提とした設計箇所あり）。
- DuckDB を使ったリサーチ関数はコネクションを引数に取り、DB のスキーマ（prices_daily, raw_financials 等）を参照します。テスト用 DB を用意して検証してください。

---

この README はコードベースの主要ポイントをまとめたものです。運用ポリシー（本番パスワード管理、APIキーの扱い、ログ保持方針等）は別途運用ドキュメントで管理してください。必要であれば、README に追加したい具体的な運用手順やコマンド例を教えてください。