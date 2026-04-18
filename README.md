# KabuSys

日本株向け自動売買システムのコアライブラリ群と運用用スクリプト群です。  
本リポジトリは注文エンジン起動スクリプト、監視（Monitoring）機能、ポートフォリオ構築・ポジションサイズ計算、リサーチ（ファクター計算）、AI（ニュース NLP / レジーム判定）などを含みます。

バージョン: 0.1.0

---

## 目次

- プロジェクト概要
- 主な機能一覧
- 前提条件 / インストール
- セットアップ手順
- 実行方法（使い方）
- 主要環境変数
- ディレクトリ構成
- 運用上の注意 / トラブルシューティング

---

## プロジェクト概要

KabuSys は日本株自動売買を支援するためのモジュール群です。  
設計上の特徴:

- 実行環境（development / paper_trading / live）に応じた挙動切替（ペーパートレード用 DB 分離など）
- DuckDB（分析用）と SQLite（監視・注文ログ用）の併用
- モニタリング（システム稼働・注文ログ・リスク監視）と Kill Switch による安全停止機能
- ポートフォリオ構築（候補選定・重み付け）・ポジションサイズ計算・セクター制約などの純粋関数実装
- OpenAI を利用したニュース NLP（銘柄ごとのセンチメント付与）やレジーム判定の実装（API 呼び出しはオプション）
- 実行・監視プロセスは PID / フラグファイルを使って外部から制御可能

---

## 主な機能一覧

- 実行エンジン起動スクリプト
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV=paper_trading の場合は MockBroker を使用して data/paper_trading.db に記録）
- 監視スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループを実行（MONITOR_POLL_INTERVAL で間隔調整）
- 設定ユーティリティ
  - config_setup.py: .env を対話式に生成・更新
  - validate_config.py: .env と config/*.yaml の前提チェック（--strict オプションあり）
- モニタリング
  - monitoring_engine, system_monitor, trade_monitor, risk_monitor, kill_switch, monitoring_db
- ポートフォリオ / シグナル処理
  - portfolio: 候補選定、重み付け、ポジションサイズ計算、セクター制約、レジーム乗数
- リサーチ
  - research.factor_research: momentum / value / volatility 等のファクター計算（DuckDB）
  - research.feature_exploration: 将来リターン計算、IC 計算、統計サマリ
- AI
  - ai.news_nlp: raw_news を LLM に送って銘柄ごとにセンチメントを算出し ai_scores テーブルへ保存
  - ai.regime_detector: ma200 とマクロニュース NLP を合成して市場レジーム（bull/neutral/bear）を判定
- 運用ツール
  - tools.paper_verification_report: Paper Trading の動作検証レポートを生成

---

## 前提条件 / インストール

推奨 Python バージョン: 3.10+

主要依存パッケージ（最低限）:
- duckdb
- psutil
- openai
- PyYAML（validate_config で YAML のパースを行う場合）
- （標準ライブラリ）sqlite3, threading, logging など

例（仮想環境を作る場合）:
```
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb psutil openai pyyaml
```

requirements.txt がない場合は上記パッケージを個別にインストールしてください。

---

## セットアップ手順

1. リポジトリのクローン / 作業ディレクトリへ移動
2. 仮想環境の作成（任意）
3. 依存パッケージのインストール（上記参照）
4. .env の作成
   - 対話式で作る: `python -m kabusys.config_setup`
   - あるいは `.env.example` を参照して手動作成
5. 設定検証: `python -m kabusys.validate_config`
   - 問題があれば表示されるエラー/警告を確認・修正
6. 必要なディレクトリを作成:
   - data/（SQLite ファイル・フラグファイル等）
   - logs/（ログ出力先。デフォルトは logs/）
   - 実行スクリプトは起動時にディレクトリを作ることもありますが、権限に注意してください

---

## 実行方法（使い方）

主な起動方法（プロセス毎にログ設定・プロセス優先度設定が行われます）:

- 監視ループを起動（デーモン的にポーリング）
```
python -m kabusys.run_monitoring
```
- ポーリング間隔を環境変数で上書き（秒）
```
MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
```
- ExecutionEngine を起動（本番/ペーパー切替は KABUSYS_ENV で制御）
```
python -m kabusys.run_execution
```
- .env を対話式に作成 / 更新
```
python -m kabusys.config_setup
```
- 設定検証
```
python -m kabusys.validate_config
# strict: 警告も異常とみなす
python -m kabusys.validate_config --strict
```
- Paper Trading の検証レポートを生成
```
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# DB パスを指定する場合:
python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
```

プログラムから利用する例:
- AI スコア付与を呼ぶ（DuckDB 接続を渡す）
```py
from kabusys.ai.news_nlp import score_news
# conn: duckdb connection, target_date: datetime.date, api_key: str（省略時は環境変数 OPENAI_API_KEY を使用）
count = score_news(conn, target_date, api_key="sk-...")
```

重要な実行挙動:
- run_monitoring は Monitoring 用の SQLite（Settings.sqlite_path）を環境にかかわらず使用します（監視は本番 DB を見る設計）。
- run_execution は KABUSYS_ENV=paper_trading の場合、paper_sqlite_path（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離します。
- 実行スクリプト起動時にプロセス優先度を "high" に設定しようと試みます（権限がない場合は警告を出して継続します）。
- 停止制御:
  - data/stop_requested.flag により起動中のループを終了可能
  - Kill Switch は data/kill.flag を生成して ExecutionEngine 停止をトリガーします

---

## 主な環境変数（抜粋）

- KABUSYS_ENV: 実行環境（development / paper_trading / live）。デフォルト: development
- JQUANTS_REFRESH_TOKEN: （必須）J-Quants API トークン
- KABU_API_PASSWORD: （必須）kabuステーション API パスワード
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール使用時に必要）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒。デフォルト 60）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

より詳細な設定項目は `kabusys.config.Settings` クラスを参照してください。

---

## ディレクトリ構成

リポジトリはパッケージ構成で `src/kabusys` 下にコードがあります（重要なファイル・モジュールの説明を記載します）。

- src/kabusys/
  - __init__.py              — パッケージ定義（バージョン等）
  - config.py                — 環境変数・設定管理（Settings クラス、自動 .env ロード）
  - config_setup.py          — .env を対話式に作成・更新するウィザード
  - validate_config.py       — 起動前チェック CLI（必須変数・ファイル等の検証）
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成スクリプト
  - portfolio/
    - portfolio_builder.py    — 候補選定・重み計算
    - position_sizing.py      — 発注株数計算・上限・スケーリング
    - risk_adjustment.py      — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py      — Momentum/Value/Volatility 等のファクター計算（DuckDB）
    - feature_exploration.py  — 将来リターン・IC 等の解析ユーティリティ
  - ai/
    - news_nlp.py             — ニュースを LLM に投げて銘柄ごとのスコアを作成
    - regime_detector.py      — ma200 とマクロ NLP を合成してレジーム判定
  - monitoring/
    - monitoring_db.py        — 監視用 SQLite のテーブル作成・永続化 API
    - monitoring_engine.py    — 各 Monitor を束ねるエンジン
    - system_monitor.py       — CPU/メモリ/ディスク・データ鮮度・プロセス監視
    - risk_monitor.py         — ドローダウン・ポジション数監視
    - kill_switch.py          — kill.flag の生成・管理
    - ... (trade_monitor, alert_manager など)
  - utils/
    - logging_setup.py        — ロギング初期化（stdout + 日次ローテートファイル）
    - process_priority.py     — クロスプラットフォームでの優先度設定（psutil 使用）
  - data/ (実行時に使用される想定場所)
    - monitoring.db           — 監視 DB（SQLITE_PATH）
    - paper_trading.db        — ペーパー用 DB（PAPER_TRADING_SQLITE_PATH）
    - kill.flag / stop_requested.flag / execution.pid — フラグ / PID ファイル
  - logs/ (デフォルトログ出力先)

---

## 運用上の注意 / トラブルシューティング

- Python バージョン: type union `|` を利用しているため Python 3.10+ が必要です。
- OpenAI を利用する機能（news_nlp, regime_detector）は `OPENAI_API_KEY` が必要です。未設定の場合は例外を投げます（モジュールごとに伝搬の仕方が異なるため注意）。
- validate_config:
  - PyYAML がインストールされていない場合、config/*.yaml の内容検証をスキップします（警告）。
- run_monitoring:
  - MONITOR_POLL_INTERVAL に 0 や負の値を設定すると警告を出してデフォルト（60秒）を使用します。
- ログ:
  - デフォルトで stdout にログを出力し、さらに `logs/<app_name>.log` に日次ローテーションで保存します。ログディレクトリ作成に失敗した場合はコンソール出力のみになります。
- 権限:
  - process priority の設定は OS や権限に依存します。権限不足の場合は警告を出してスキップされます。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db は冪等で複数回呼べます。既存テーブルへ必要なカラムが足りない場合は自動で ALTER などを行いますが、重大な schema 変更は想定していません。
- Kill Switch:
  - `data/kill.flag` を生成すると ExecutionEngine に停止信号を送ります。`KILL_FLAG_CLEAR_ON_START=1` は本番では危険（デフォルト 0 を推奨）。

---

必要であれば README にサンプル .env のテンプレートや各主要モジュールの API 使用例（コードスニペット）を追加できます。どのセクションを拡張したいか教えてください。