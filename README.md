# KabuSys

日本株向け自動売買 / リサーチ基盤 (KabuSys) のリポジトリ向け README。  
この README はリポジトリの主要コンポーネント（実行エンジン、監視、AI 補助、ポートフォリオ構築、リサーチ等）の概要、セットアップ方法、使い方、ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買・リサーチ用のソフトウェア基盤です。特徴として:

- 発注・リスク管理・注文レポジトリを持つ ExecutionEngine（実行エンジン）
- システム稼働状況や注文異常を監視する Monitoring サブシステム（Kill Switch を含む）
- ポートフォリオ構築 (候補選定、重み付け、ポジションサイズ計算、セクター制限 等)
- DuckDB / SQLite を用いた時系列データ・監視ログの処理
- OpenAI を使ったニュース NLP（センチメント付与）やレジーム判定のモジュール
- ペーパートレード用に実装された分離された DB/モックブローカー

設計方針の一部:
- 本番/ペーパートレードを環境変数 `KABUSYS_ENV` で分離
- .env を用いた設定管理（対話ウィザード・検証ツールあり）
- フェイルセーフ（API失敗でのフォールバックや冪等処理）

---

## 主な機能一覧

- Execution
  - ExecutionEngine（発注・注文管理・リコンシリエーション・リスク管理）
  - paper_trading モードでは MockBrokerClient を使用し、本番 DB と分離（デフォルト: `data/paper_trading.db`）
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク、Execution プロセス状態、データ鮮度の監視
  - TradeMonitor: 滞留注文、約定価格の異常チェック
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新
  - KillSwitch: 条件により `data/kill.flag` を書き込み ExecutionEngine を停止させる
  - MonitoringEngine: 各モニタを束ねてポーリング（`MONITOR_POLL_INTERVAL` で間隔変更可）
- AI / ニュース関連
  - news_nlp: OpenAI（gpt-4o-mini 等）を用いたニュースの銘柄別センチメントスコア付与（ai_scores テーブルへ保存）
  - regime_detector: MA とマクロニュースを組み合わせた市場レジーム判定（market_regime テーブルへ保存）
- Research / Factor
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）、将来リターン・IC 計算、統計サマリー
- Portfolio
  - 候補選定、等金額／スコア加重配分、リスクベースのポジションサイズ算出、セクター上限適用、レジーム乗数
- ツール
  - config_setup.py : .env の対話式作成ツール
  - validate_config.py : .env と config/*.yaml の起動前検証ツール
  - tools.paper_verification_report : Paper Trading の検証レポート生成

---

## セットアップ手順

前提: Python 3.10+ を想定（型注釈等のため）。プロジェクトルートは `.git` または `pyproject.toml` を起点に自動検出します。

1. リポジトリをクローン
   - git clone ...

2. 仮想環境の作成と有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - 必要な代表パッケージ:
     - duckdb
     - psutil
     - openai
     - （任意）PyYAML（config 検証で YAML パースを行う場合）
   - 例:
     - pip install duckdb psutil openai PyYAML

   （requirements.txt がある場合は pip install -r requirements.txt）

4. .env を作成
   - 対話ウィザードを利用:
     - python -m kabusys.config_setup
   - または手動でプロジェクトルートに `.env` を作成（.env.example を参照）
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 重要な環境変数（例）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector を使う場合）
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (監視 DB、デフォルト: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (ペーパートレード DB、デフォルト: data/paper_trading.db)
     - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の約定挙動）
     - LOG_LEVEL: DEBUG | INFO | WARNING ...

5. 設定検証（起動前推奨）
   - python -m kabusys.validate_config
   - 警告を厳密に扱う場合:
     - python -m kabusys.validate_config --strict

6. データディレクトリを作成（必要な場合）
   - mkdir -p data

備考:
- .env は絶対に Git にコミットしないでください（secret を含むため）。
- `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動で .env を読み込む処理を無効化できます（テスト用途）。

---

## 使い方（主要コマンド例）

実行はプロジェクトルートで行います。

- ExecutionEngine（実行エンジン）を起動
  - python -m kabusys.run_execution
  - 挙動:
    - `KABUSYS_ENV=paper_trading` のときは MockBroker を使用し、paper_trading 専用 DB に記録します（本番 DB とは分離）。
    - 起動時に `data/stop_requested.flag` が存在すると起動せず終了します。
    - 実行中は `data/execution.pid` が生成されます。停止は `data/stop_requested.flag` を書くことで行えます（run_execution を監視しているモニタと整合）。

- Monitoring（監視ループ）を起動
  - python -m kabusys.run_monitoring
  - 環境変数でポーリング間隔を変更:
    - MONITOR_POLL_INTERVAL（秒）例: export MONITOR_POLL_INTERVAL=30
  - 監視は本番 sqlite_path を使用（環境に依存せず監視は本番 DB を参照する設計）
  - 監視ループの停止: プロジェクトルートの `data/stop_requested.flag` を作成するとループは検知して終了します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db --from 2026-04-01 --to 2026-04-11
  - デフォルト DB は環境変数 `PAPER_TRADING_SQLITE_PATH` または `data/paper_trading.db`

- .env の対話式作成・更新
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict オプションで警告を FAIL 扱いにできます

- AI モジュール（ニュース NLP / レジーム判定）
  - いずれも OpenAI の API キーが必要（OPENAI_API_KEY 環境変数または関数引数で指定）
  - news_nlp.score_news() / regime_detector.score_regime() をアプリケーションから呼び出す形で利用

停止・Kill スイッチについて:
- `data/stop_requested.flag`:
  - run_monitoring/run_execution の各ループはこのファイルの存在を監視し、検出時に安全にシャットダウンします（外部運用でプロセスを停止したい場合に使用）。
- `data/kill.flag`:
  - KillSwitch が条件に合致したとき（例: 大きなドローダウン）に書き込まれるフラグ。ExecutionEngine 側でこのフラグを見て停止処理を行う仕組みを持っています。
- Execution 起動時に kill.flag を自動でクリアしたくない場合:
  - .env の `KILL_FLAG_CLEAR_ON_START=0`（本番推奨）。1 にすると起動時に自動クリアします（開発用の便利機能）。

ログレベル:
- LOG_LEVEL 環境変数で制御（DEBUG/INFO/WARNING/ERROR/CRITICAL）

---

## 設定項目（主要）

- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 実行環境:
  - KABUSYS_ENV: development | paper_trading | live
- DB 関連:
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (paper_trading 用)
- OpenAI:
  - OPENAI_API_KEY（news_nlp / regime_detector を使う場合）
- Paper trading の挙動:
  - PAPER_FILL_MODE: instant | partial | never | reject
- その他:
  - MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔、秒）

config_setup.py を実行すると対話式に .env を作成できます。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要モジュールとファイルです（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / Settings 管理（自動 .env ロード機能含む）
  - config_setup.py              — .env 対話ウィザード
  - validate_config.py           — 起動前検証 CLI
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート生成ツール
  - ai/
    - news_nlp.py                 — ニュース -> センチメント（OpenAI 使用）
    - regime_detector.py          — マクロ + MA による市場レジーム判定
  - monitoring/
    - monitoring_db.py            — SQLite 監視 DB 層（テーブル作成・永続化 API）
    - monitoring_engine.py        — 各 Monitor を束ねるエンジン
    - system_monitor.py           — システム状態・データ鮮度監視
    - trade_monitor.py            — 注文滞留・約定異常監視
    - risk_monitor.py             — ドローダウン・ポジション上限監視
    - kill_switch.py              — Kill Switch（flag ファイル操作）
    - alert_manager.py            — (通知管理: 未記載部分を含む)
  - portfolio/
    - portfolio_builder.py        — 候補選定・重み計算
    - position_sizing.py          — 発注株数算出、aggregate cap のスケーリング
    - risk_adjustment.py          — セクター上限・レジーム乗数
  - research/
    - factor_research.py          — momentum/value/volatility ファクター計算（DuckDB）
    - feature_exploration.py      — IC / 将来リターン / 統計サマリー
  - utils/
    - process_priority.py         — プロセス優先度 / CPU affinity のユーティリティ
  - execution/                     — Execution 関連 (order_manager, broker_factory 等)（詳細な実装ファイルがある想定）
  - data/                          — データディレクトリ (runtime flags, pid, DB 等)

補足:
- monitoring_db.init_monitoring_db() により、必要な監視用テーブルが自動作成・マイグレーションされます（冪等）。
- DuckDB は時系列・分析用のストレージとして用いられます。prices_daily / raw_financials / raw_news などのテーブルを想定しています。

---

## 運用上の注意点

- 本番モード（KABUSYS_ENV=live）は注意深く設定を確認してください。validate_config.py は本番向けガードもチェックします（LINE 通知設定など）。
- .env を誤ってコミットしないように .gitignore を確認してください。
- OpenAI API 使用時はレート制限やエラー（429, 5xx）に対するリトライロジックが実装されていますが、API キー管理とコスト管理を行ってください。
- Paper Trading は本番 DB と分離されます。ペーパートレード DB のパスは環境変数で上書き可能です。
- プロセス優先度や CPU affinity の設定は psutil を用いて行われます。権限不足時は警告となりスキップされます。

---

## 開発・テストのヒント

- モジュール単体の関数（portfolio, research, ai の各関数）は純粋関数で設計されているものが多く、ユニットテストしやすいです（DuckDB 接続をモックしてテスト可能）。
- MonitoringEngine.run_once() を使うとポーリングループを回さずに一回分だけ実行でき、テストに便利です。
- news_nlp._call_openai_api や regime_detector._call_openai_api はテスト時に patch して外部呼び出しを差し替え可能です。

---

## 参考コマンドまとめ（例）

- .env 作成
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
- 実行エンジン起動
  - python -m kabusys.run_execution
- 監視ループ起動
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- 停止フラグ作成（手動でプロセス停止を指示）
  - touch data/stop_requested.flag
- Kill Switch 発動確認（監視/リスク条件に応じて自動書き込み）
  - data/kill.flag の存在を確認

---

README に書かれている内容はコード内のドキュメントストリングや注釈（日本語）に基づいて構成しています。補足や詳細ドキュメント、使い方の追加テンプレート（systemd ユニット、docker-compose 等）が必要であればその用途に合わせて追記します。