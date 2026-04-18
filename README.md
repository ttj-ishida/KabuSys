# KabuSys

KabuSys は日本株向けの自動売買システム（プロトタイプ）です。  
トレード実行・リスク管理・監視・リサーチ・ニュース NLP（OpenAI）などのコンポーネントを含み、開発・ペーパートレード・本番（live）モードを切り替えて動作します。

バージョン: 0.1.0

---

## 概要

主な目的は次のとおりです。

- 戦略に基づく銘柄選定とポートフォリオ構築（weight 計算、ポジションサイジング）
- リスク制御（ドローダウンアラート、ポジション上限監視、リスク拒否ログ）
- ExecutionEngine による発注・注文管理（paper_trading モードで完全分離された DB を利用）
- 監視サブシステム（SystemMonitor / TradeMonitor / RiskMonitor）による定期チェックと Kill Switch
- 研究用モジュール（ファクター計算・特徴量探索）
- ニュースの NLP によるセンチメント集計（OpenAI 使用、ai モジュール）
- 補助ツール: .env ウィザード、設定検証、Paper Trading 検証レポート

---

## 機能一覧

- Execution
  - 本番 / ペーパートレード切替（KABUSYS_ENV）
  - BrokerClientFactory によるブローカークライアント生成（paper_trading 時は Mock を使用）
  - RiskManager（最大ポジション比率・利用率・サーキットブレーカー等）
  - OrderManager / Reconciler による注文管理と突合せ

- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク、プロセス存在、データ鮮度チェック
  - TradeMonitor / RiskMonitor: 滞留注文・約定異常・ドローダウン監視
  - KillSwitch: 条件に応じて `data/kill.flag` を書き込み ExecutionEngine を停止
  - MonitoringEngine: 各モニタを束ねるポーリングループ

- Portfolio
  - 候補選定 (score ベース)
  - 等金額 / スコア加重の重み計算
  - リスク調整（セクター上限、レジーム乗数）
  - ポジションサイズ計算（単元株丸め、aggregation cap）

- Research
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Spearman）等の統計解析

- AI
  - ニュース NLP（OpenAI）で銘柄ごとのセンチメントスコアを生成し `ai_scores` に書き込み
  - 市場レジーム判定（ETF MA200 とマクロセンチメントの合成）

- ユーティリティ
  - 対話式 .env 作成ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
  - Paper Trading 検証レポート生成ツール（kabusys.tools.paper_verification_report）

---

## セットアップ手順

前提
- Python 3.9+（コードは型注釈を使用）
- SQLite（標準ライブラリ）
- DuckDB（duckdb Python パッケージ）
- psutil（プロセス優先度・メトリクス取得）
- OpenAI SDK（ai 機能を使う場合）
- PyYAML（`validate_config` で YAML 検証を行う場合、任意）

推奨インストール例:
```
pip install duckdb psutil openai PyYAML
```
（プロジェクトが requirements.txt を提供している場合はそれを利用してください）

ディレクトリ作成:
- data/ と logs/ ディレクトリを作成しておくと安全です（ログ・DB のデフォルト場所に対応）。
```
mkdir -p data logs
```

.env の作成:
- 対話式ウィザードを使う:
```
python -m kabusys.config_setup
```
- 手動で `.env` を作る場合は .env.example を参考にしてください。

自動環境変数ロード:
- パッケージ初期化時にプロジェクトルート（.git または pyproject.toml）を探して `.env` / `.env.local` を読み込みます。自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須環境変数（最低限）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

AI 機能を使う場合
- OPENAI_API_KEY が必要です（ai.score_news / regime_detector など）。

---

## 環境変数（主なもの）

- KABUSYS_ENV: 実行環境（development / paper_trading / live）。デフォルト: development
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- LOG_DIR: ログ保存先（デフォルト: logs/）
- OPENAI_API_KEY: OpenAI API キー（AI 機能用）
- PAPER_FILL_MODE: ペーパートレードの約定挙動（instant / partial / never / reject）
- KILL_FLAG_PATH: Kill Switch のパス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（0/1。デフォルト 0）
- MONITOR_POLL_INTERVAL: Monitoring ポーリング間隔（秒、run_monitoring が参照。デフォルト 60）

注意:
- Monitoring は KABUSYS_ENV にかかわらず本番の sqlite_path（SQLITE_PATH）を参照しますが、Execution は paper_trading 時に PAPER_TRADING_SQLITE_PATH を使用して DB を完全分離します。

例（.env に書く最小例）
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
```

---

## 使い方（主要コマンド）

- 環境ウィザード（.env の作成・更新）
```
python -m kabusys.config_setup
```

- 設定検証（.env と config/*.yaml の簡易チェック）
```
python -m kabusys.validate_config
# 警告も FAIL 扱いにする:
python -m kabusys.validate_config --strict
```

- ExecutionEngine を起動
  - ペーパートレード:
    ```
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    ```
    → paper_trading の場合は MockBrokerClient を使用し、デフォルトで `data/paper_trading.db` に記録されます。
  - 本番（live）:
    ```
    KABUSYS_ENV=live python -m kabusys.run_execution
    ```

- Monitoring を起動
```
python -m kabusys.run_monitoring
```
- MONITOR_POLL_INTERVAL（秒）でポーリング間隔を上書きできます（デフォルト 60 秒）:
```
MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
```

- Paper Trading 検証レポート（指定期間）
```
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# DB パス指定:
python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
```

- 停止 / Kill
  - 常時ループを止めたい場合、プロジェクトルートの `data/stop_requested.flag` を作成すると `run_monitoring` や `run_execution` のループが検知して終了します。
  - KillSwitch は条件を満たすと `data/kill.flag` を書き込み、ExecutionEngine 側でこれを検知して安全に停止します。
  - `KILL_FLAG_CLEAR_ON_START=1` を設定すると Execution 起動時に kill.flag を自動クリアします（本番環境では推奨されません）。

---

## ログ & DB

- ログ: `kabusys.utils.logging_setup.setup_logging` により stdout と `logs/<app_name>.log`（日次ローテーション、30日保持）に出力されます。
- Monitoring DB: デフォルト `data/monitoring.db`（SQLite）。`kabusys.monitoring.monitoring_db.init_monitoring_db` でテーブルを冪等に作成・マイグレーションします。
- DuckDB: 分析用データベース（デフォルト `data/kabusys.duckdb`）。

---

## 主なファイル / ディレクトリ構成

（src/kabusys をルートとした概略）

- run_monitoring.py — SystemMonitor のポーリングループ起動スクリプト
- run_execution.py — ExecutionEngine 起動スクリプト（paper_trading 時は専用 DB）
- config.py — 環境変数 / Settings 管理（自動 .env ロード、各種設定プロパティ）
- config_setup.py — 対話式 .env ウィザード
- validate_config.py — 設定検証 CLI

- ai/
  - news_nlp.py — ニュースを OpenAI でスコアリングして ai_scores に書き込む
  - regime_detector.py — 市場レジーム判定（MA200 + マクロセンチメント）

- monitoring/
  - monitoring_db.py — SQLite テーブル定義 & MonitoringDB 抽象
  - system_monitor.py — システム・データ鮮度監視
  - risk_monitor.py — ドローダウン / ポジション数監視
  - kill_switch.py — kill.flag の書き込み
  - monitoring_engine.py — 各モニタを束ねるエンジン
  - alert_manager.py — （アラート送信用、コードベースに含まれる想定）

- execution/ (発注関連: BrokerFactory / Engine / OrderManager / RiskManager など)
- portfolio/ (portfolio_builder.py, risk_adjustment.py, position_sizing.py)
- research/ (factor_research.py, feature_exploration.py)
- tools/
  - paper_verification_report.py — ペーパートレードの検証レポート生成

- utils/
  - logging_setup.py — ログ設定ユーティリティ
  - process_priority.py — プラットフォーム非依存の優先度設定ユーティリティ

---

## 実運用上の注意

- KABUSYS_ENV=live は本番です。設定（APIキー・LINE通知など）を十分確認してください。`validate_config` は live 時に追加警告を表示します。
- Kill Switch や stop フラグ類の扱いを運用ルールとして定義してください。`KILL_FLAG_CLEAR_ON_START=1` は本番では危険です。
- データベースは paper_trading と本番で分離する設計ですが、設定ミスにより上書きされないよう .env を注意深く管理してください（.env は Git にコミットしないでください）。
- AI（OpenAI）呼び出しは API のレート制限やコストに注意。エラー時はフェイルセーフで継続する実装になっていますが、運用ポリシーを設けてください。
- ログディレクトリ作成に失敗した場合はコンソールのみの出力にフォールバックします。

---

以上が README.md の要点です。必要があれば、README に
- requirements.txt のサンプル
- よくあるトラブルシューティング（ポート・ファイル権限・DB ロック等）
- 実行時の systemd / supervisor 用のユニット例
を追加します。どの情報を追加しますか？