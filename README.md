# KabuSys

日本株自動売買システムのリポジトリ（パッケージ名: `kabusys`）。  
本リポジトリは発注エンジン、監視、ポートフォリオ構築、リサーチ、AI ベースのニュース評価などのコンポーネントを含みます。

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要な以下の機能群を提供します。

- 発注実行エンジン（ExecutionEngine）
- システムおよび取引状態の監視（Monitoring）
- ポートフォリオ構築・銘柄選定・ポジションサイジング
- ファクター計算・特徴量探索（DuckDB を利用）
- ニュースの NLP によるセンチメントスコアリング（OpenAI API）
- ペーパートレード向けの完全分離 DB / 検証ツール

設計方針の例:
- 本番・ペーパートレードは SQLite ファイルレベルで分離
- DuckDB を分析用 DB として使用
- 環境変数 / .env による設定管理
- ログはコンソールと日次ローテーションファイルに出力

---

## 主な機能一覧

- 実行エンジン起動スクリプト: `run_execution.py`
  - `KABUSYS_ENV=paper_trading` の場合、モックブローカー（`MockBrokerClient`）を使用し、`data/paper_trading.db` に記録
  - プロセス優先度設定、PID ファイル管理、停止フラグ監視

- 監視ループ起動スクリプト: `run_monitoring.py`
  - System / Trade / Risk モニタをポーリングして監視ログを SQLite に永続化
  - `MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）
  - 監視は環境に関わらず本番用の `sqlite_path` を使用

- 環境設定ウィザード: `config_setup.py`
  - 対話式で `.env` を生成 / 更新

- 設定検証 CLI: `validate_config.py`
  - `.env` と `config/*.yaml`（存在する場合）を事前検証

- Paper Trading 検証レポート: `tools/paper_verification_report.py`
  - ペーパートレード DB から稼働率、注文成功率、レイテンシなどを集計して PASS/FAIL を判定

- ポートフォリオ / リスクモジュール
  - 候補選定、等重・スコア重み、ポジションサイズ計算、セクター制限、レジーム乗数などの純粋関数群

- 研究（research）モジュール
  - Momentum / Volatility / Value 等のファクター計算、将来リターン・IC 計算など（DuckDB 前提）

- AI モジュール（ai）
  - ニュース NLP による銘柄別センチメント（`news_nlp.score_news`）
  - マクロニュース + ETF MA による市場レジーム判定（`regime_detector.score_regime`）

---

## 要件（依存ライブラリ）

少なくとも以下のパッケージが必要になります（一例）:

- Python 3.9+
- duckdb
- psutil
- openai
- PyYAML（`validate_config` が YAML の検証を行う場合に必要）
- その他（標準ライブラリの sqlite3 等は同梱）

インストール例（仮の requirements）:
```
pip install duckdb psutil openai PyYAML
```

requirements.txt を用意している場合は:
```
pip install -r requirements.txt
```

---

## セットアップ手順

1. リポジトリをクローンし、Python 仮想環境を作成して有効化します。

2. 依存パッケージをインストールします（上記参照）。

3. 環境変数の準備
   - 対話式で `.env` を作成するには:
     ```
     python -m kabusys.config_setup
     ```
     ウィザードにしたがって入力するとプロジェクトルートに `.env` が作成されます。

   - 必須環境変数（最低限設定が必要）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD

   - 主要な環境変数（デフォルト値はここで上書き可能）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH: 分析用 DuckDB のパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH: ペーパートレード時の SQLite（デフォルト: data/paper_trading.db）
     - LOG_LEVEL: ログレベル（デフォルト: INFO）
     - OPENAI_API_KEY: OpenAI を利用する場合に必須

4. 設定検証（推奨）
   ```
   python -m kabusys.validate_config
   ```
   必要に応じて `--strict` を付けると警告も失敗として扱います。

---

## 使い方（主要スクリプト）

- 実行エンジン（ExecutionEngine）を起動:
  ```
  python -m kabusys.run_execution
  ```
  - `KABUSYS_ENV=paper_trading` のとき、ペーパートレード専用 DB に記録され、本番 DB と分離されます。
  - 起動時に `data/execution.pid` が書かれ、停止は `data/stop_requested.flag` を作成することで行えます。

- 監視ループを起動:
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 `MONITOR_POLL_INTERVAL`（秒）でポーリング間隔を上書き可能（例: `MONITOR_POLL_INTERVAL=30`）。
  - 監視ループは `data/stop_requested.flag` を検知すると終了します。
  - 監視は settings にある `sqlite_path`（本番用）を使用します（環境に関わらず）。

- Paper Trading 検証レポート生成:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - `--db` オプションで DB パスを指定可能。環境変数 `PAPER_TRADING_SQLITE_PATH` も使用できます。

- 環境設定ウィザード:
  ```
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

---

## 停止・Kill スイッチ

- 実行を外部から停止させたい場合はプロジェクトの `data` ディレクトリにフラグファイルを書きます。
  - 停止要求（run_execution / run_monitoring のループを終了）:
    - data/stop_requested.flag を作成（任意の内容）
  - Kill Switch（ExecutionEngine を停止させる自動判定）のためのファイル:
    - data/kill.flag（`KillSwitch` が作成して ExecutionEngine に停止指示を出す）

- `KILL_FLAG_CLEAR_ON_START` 環境変数（`.env`）を `1` にすると起動時に kill.flag を自動でクリアします（本番では `0` 推奨）。

---

## ログ

- ロギングは `kabusys.utils.logging_setup.setup_logging` を通じて統一管理されます。
- 出力:
  - コンソール（stdout）
  - 日次ローテーションファイル: デフォルト `logs/<app_name>.log`（30 日分保持）
- ログディレクトリは環境変数 `LOG_DIR` または引数で上書き可能。

---

## ディレクトリ構成（主なファイル）

下記はパッケージ内部の主要ファイル / モジュールの抜粋です（`src/kabusys` 配下）。

- kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定読み込み（.env 自動ロード）
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 起動前設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring 起動スクリプト

  - execution/                — 発注実行関連（BrokerFactory, ExecutionEngine, OrderManager, RiskManager, Reconciler 等）
  - monitoring/
    - monitoring_db.py        — 監視用 SQLite 永続化層
    - system_monitor.py       — システム状態・データ鮮度監視
    - trade_monitor.py        — 取引ログ監視（滞留注文等）
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - kill_switch.py          — kill.flag 書き込みユーティリティ
    - monitoring_engine.py    — 各 Monitor を束ねるエンジン
    - alert_manager.py        —（通知管理：LINE 等、実装場所）
  - portfolio/
    - portfolio_builder.py    — 候補選定、重み計算
    - position_sizing.py      — 株数算出・上限・丸めロジック
    - risk_adjustment.py      — セクターキャップ、レジーム乗数
  - research/
    - factor_research.py      — Momentum / Volatility / Value 等のファクター計算（DuckDB）
    - feature_exploration.py  — 将来リターン・IC・統計サマリー
  - ai/
    - news_nlp.py             — ニュースの LLM によるスコアリング（OpenAI）
    - regime_detector.py      — ETF MA + マクロセンチメントでレジーム判定
  - data/                     — （ランタイムで生成される想定のディレクトリ: DB, pid, flag 等）
  - logs/                     — ログ出力先（デフォルト）

---

## ライブラリ / API の利用例（開発者向け）

- ポートフォリオ関連関数（ライブラリとして利用可能）
  - select_candidates, calc_equal_weights, calc_score_weights
  - calc_position_sizes
  - apply_sector_cap, calc_regime_multiplier

- AI:
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - DuckDB 接続を受け取り ai_scores テーブルへ書き込み
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

- 研究:
  - kabusys.research.calc_momentum(conn, date)
  - kabusys.research.calc_volatility(conn, date)
  - kabusys.research.calc_value(conn, date)

---

## 運用上の注意

- 本番（KABUSYS_ENV=live）では設定（LINE 通知先、kill フラグクリア設定など）を十分に確認してください。`validate_config` は live 時の追加チェックを行います。
- OpenAI API を使う機能は API キー（OPENAI_API_KEY）が必須です。API 呼び出しの失敗が発生してもフェイルセーフで処理を継続する設計が多く採用されていますが、料金やレート制限に注意してください。
- ローカル開発時は KABUSYS_ENV=paper_trading を使用すると本番 DB を汚さずテストできます。
- `data` ディレクトリ内のファイル（.db、.pid、.flag）は Git にコミットしないでください（`.env` と同様に機密情報 / 実行環境依存ファイル）。

---

この README はコードベース（`src/kabusys`）の主要な使い方・構成をまとめたものです。実行前に `python -m kabusys.validate_config` で設定検証を行うことを推奨します。必要であれば、インストール手順や CI / デプロイ手順、詳しい API ドキュメントを別途作成できます。