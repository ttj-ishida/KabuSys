# KabuSys — 日本株自動売買システム

このリポジトリは日本株向けの自動売買 / リサーチ / モニタリング用の内部ライブラリと起動スクリプト群を含みます。  
README ではプロジェクト概要、主な機能、セットアップ手順、基本的な使い方、ディレクトリ構成を日本語でまとめます。

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群です。

- データパイプライン / DuckDB を使ったファクター計算（research）
- ポートフォリオ構築（候補選定・重み付け・株数決定）
- 発注実行エンジン（実口座 / ペーパートレード切替）
- システム・トレード監視（稼働監視、滞留注文・約定異常・リスク検出）
- AI を使ったニュースセンチメント評価（OpenAI）
- 運用に便利な CLI ツール（.env ウィザード、設定検証、ペーパートレード検証レポート）

設計方針の例：
- DuckDB / SQLite を利用して分析・ログを永続化
- 本番（live）とペーパートレード（paper_trading）を明確に分離（別 SQLite DB）
- LLM 呼び出しは失敗してもフェイルセーフで継続
- 設定は .env または環境変数で管理

---

## 主な機能一覧

- 起動スクリプト
  - run_execution.py — ExecutionEngine を起動（本番 / ペーパートレード対応）
  - run_monitoring.py — SystemMonitor のポーリングループを起動
- 設定管理
  - config_setup.py — 対話式 .env 生成ウィザード
  - validate_config.py — .env / config/*.yaml の起動前検証 CLI
- モニタリング
  - MonitoringEngine（SystemMonitor / TradeMonitor / RiskMonitor の統合）
  - KillSwitch（条件で data/kill.flag を書き込み Execution を停止）
  - MonitoringDB（SQLite ベースの永続化層）
- ポートフォリオ構築（純粋関数）
  - 候補選定、重み付け、ポジションサイズ計算、セクターキャップ適用 など
- リサーチ
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC 計算、統計サマリー
- AI（OpenAI 統合）
  - news_nlp.score_news — ニュース記事を LLM でセンチメント評価して ai_scores に書き込み
  - regime_detector.score_regime — ETF MA とマクロニュースを組合せレジーム判定
- ツール
  - paper_verification_report — ペーパートレードログから検証レポートを生成

---

## 前提 / 必要環境

- Python 3.9+
- 必要な主なライブラリ（最低限）:
  - duckdb
  - psutil
  - openai (AI 機能を使用する場合)
  - pyyaml（設定検証で YAML の中身チェックを行う場合）
- OS: Linux / macOS / Windows（プロセス優先度や CPU affinity は OS に依存する実装あり）

requirements ファイルはリポジトリに含まれていない場合があります。利用する環境に合わせてインストールしてください。

例（最低限）:
```
pip install duckdb psutil openai pyyaml
```

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンして Python 仮想環境を作成
```
git clone <this-repo>
cd <this-repo>
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
```

2. 依存パッケージをインストール
（プロジェクトに requirements.txt があればそれを使う）
```
pip install -r requirements.txt
# ない場合の例:
pip install duckdb psutil openai pyyaml
```

3. .env を作成
対話式ウィザードを使うと便利です:
```
python -m kabusys.config_setup
```
ウィザードで生成された .env は絶対に Git にコミットしないでください。

主要な環境変数（抜粋）:
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 時の DB、デフォルト: data/paper_trading.db）
- OPENAI_API_KEY（AI 機能を使う場合）
- LOG_LEVEL（例: INFO）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔: 秒、デフォルト 60）

4. 設定検証（起動前チェック）
```
python -m kabusys.validate_config
# 警告もエラー扱いにしたい場合:
python -m kabusys.validate_config --strict
```

---

## 使い方（主要コマンド例）

- ExecutionEngine（発注エンジン）を起動
  - 本番 / ペーパートレードは KABUSYS_ENV に依存
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db に記録します
```
python -m kabusys.run_execution
```
実行中に停止フラグを検知すると安全に停止します。停止フラグ:
- data/stop_requested.flag — run_execution/run_monitoring の独自停止フラグ（手動で作ると起動スクリプトが検知して終了）
- data/kill.flag — KillSwitch が書き込む（ExecutionEngine 停止のシグナル）

- Monitoring（ポーリング）を起動
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）
```
# デフォルト 60 秒
python -m kabusys.run_monitoring

# 例えば 30 秒間隔にしたいとき
export MONITOR_POLL_INTERVAL=30
python -m kabusys.run_monitoring
```

- .env の対話式セットアップ
```
python -m kabusys.config_setup
```

- 設定検証
```
python -m kabusys.validate_config
```

- Paper Trading 検証レポート出力
```
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# DB パスを指定する例
python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
```

- AI 機能（ニュースセンチメント / レジーム判定）
  - OPENAI_API_KEY が必要
  - 関数はライブラリ API として提供（kabusys.ai.score_news, kabusys.ai.regime_detector.score_regime）
  - スクリプトとしてのエントリは提供していないため、必要に応じて小さな runner を作成して呼び出してください

ログ:
- デフォルトは logs/<app_name>.log（app_name は "execution" / "monitoring" 等）
- ログ出力ディレクトリは環境変数 LOG_DIR で変更可能
- ログは stdout と日次ローテートされたファイルに出力されます

停止 / 強制停止:
- 実行中のプロセスを優雅に停止したい場合は data/stop_requested.flag を作成する（起動スクリプトが検知して終了）
- KillSwitch により data/kill.flag が作成されると ExecutionEngine に停止シグナルを送ります（KillSwitch の評価は Monitoring 側で行われるのが想定）

---

## 主要コンポーネント説明（概要）

- src/kabusys/config.py
  - 環境変数と .env の自動ロード、Settings クラスによりアプリ設定を提供

- src/kabusys/run_execution.py
  - ExecutionEngine の起動スクリプト
  - paper_trading モード時は専用 SQLite を使用し MockBroker を使う

- src/kabusys/run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト
  - 環境に依らず本番 sqlite_path を使用して監視ログを記録

- src/kabusys/monitoring/
  - monitoring_db.py: SQLite テーブルの初期化・永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py: CPU/MEM/DISK やデータ鮮度、Execution プロセス存在チェック
  - risk_monitor.py: ドローダウン / ポジション上限チェック
  - kill_switch.py: 条件で kill.flag を書き込み
  - monitoring_engine.py: 各 Monitor を束ねて定期実行・アラート発行

- src/kabusys/execution/
  - ExecutionEngine 本体、OrderManager、OrderRepository、RiskManager、Reconciler、BrokerClientFactory 等（発注ロジック）

- src/kabusys/portfolio/
  - portfolio_builder.py: 候補選定・重み計算
  - position_sizing.py: 株数決定、縛り（lot_size、max_position_pct、利用キャッシュ上限）への対応
  - risk_adjustment.py: セクターキャップやレジーム乗数

- src/kabusys/research/
  - factor_research.py: Momentum / Volatility / Value 等のファクター計算（DuckDB を使用）
  - feature_exploration.py: 将来リターン計算、IC、統計サマリー

- src/kabusys/ai/
  - news_nlp.py: raw_news を LLM でスコアリングして ai_scores に書き込み（OpenAI）
  - regime_detector.py: ETF MA と LLM マクロセンチメントを合成してレジーム判定

- src/kabusys/utils/
  - logging_setup.py: ルートロガーのセットアップ（stdout + 日次ファイルローテーション）
  - process_priority.py: プロセス優先度 / CPU affinity 設定ユーティリティ

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 以下の主要ファイル・ディレクトリの一覧と簡単な役割です。

- src/
  - kabusys/
    - __init__.py
    - config.py
    - config_setup.py
    - validate_config.py
    - run_execution.py
    - run_monitoring.py
    - tools/
      - paper_verification_report.py
    - ai/
      - news_nlp.py
      - regime_detector.py
    - monitoring/
      - monitoring_db.py
      - monitoring_engine.py
      - system_monitor.py
      - risk_monitor.py
      - trade_monitor.py (存在する想定: trade の監視ロジック)
      - kill_switch.py
      - alert_manager.py (通知管理の想定)
    - execution/
      - execution_engine.py
      - broker_factory.py
      - order_manager.py
      - order_repository.py
      - risk_manager.py
      - reconciler.py
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - factor_research.py
      - feature_exploration.py
    - utils/
      - logging_setup.py
      - process_priority.py
    - data/ （リポジトリルートに data/ を置く想定）
      - monitoring.db (デフォルト)
      - paper_trading.db (paper_trading 用)
      - kabusys.duckdb (DuckDB)
      - execution.pid, kill.flag, stop_requested.flag など
    - logs/ （デフォルトのログ出力先）

（注）この README はコードベースの主要部分に基づいて作成しています。プロジェクトの細かい実装や追加モジュールはソースツリーを参照してください。

---

## 運用上の注意

- 本番（KABUSYS_ENV=live）では kill_flag_clear_on_start を 0 にすることを推奨します（誤って Kill Switch をクリアしないようにするため）。
- .env は機密情報を含むため絶対に Git にコミットしないでください。
- OpenAI を使う機能は API コストが発生します。API キーは安全に管理してください。
- DuckDB / SQLite のパスは設定可能ですが、権限やバックアップを検討してください。
- psutil を使ったプロセス優先度の設定は OS 権限に依存するため、実行ユーザーに応じて権限不足で警告が出ることがあります。

---

もし README に追加したい内容（例: デプロイ手順、systemd 用ユニットファイルテンプレート、CI 設定、より詳細な API 参照など）があれば教えてください。必要に応じて追記します。