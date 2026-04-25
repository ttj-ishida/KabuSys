# KabuSys

日本株向けの自動売買システム（ライブラリ＋起動スクリプト群）。  
取引エンジン（Execution）、監視（Monitoring）、ポートフォリオ構築、研究（Research）、AI（ニュースセンチメント／レジーム判定）などのコンポーネントを含みます。

---

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 使い方
  - 環境設定ウィザード（.env生成）
  - 設定検証
  - 実行エンジン起動 (ExecutionEngine)
  - 監視ループ起動 (SystemMonitor / MonitoringEngine)
  - Paper Trading 検証レポート
  - AI関連（ニューススコア・レジーム判定）
  - 停止・Kill Switch
- ディレクトリ構成
- 参考・補足

---

## プロジェクト概要

KabuSys は日本株の自動売買を想定したモジュール群および起動スクリプト群です。  
設計上の特徴：
- Execution（発注）と Monitoring（監視）は分離され、監視から Kill Switch により Execution を停止できる仕組みを提供
- Paper Trading モード（擬似発注）をサポートし、本番 DB と分離
- DuckDB を用いた分析フレームワーク（ファクター計算等）
- OpenAI を利用したニュースのセンチメント評価や市場レジーム判定（必要な場合）
- 設定管理は .env ベース。プロジェクトルート自動検出・読み込み機能を備える

---

## 主な機能

- Execution
  - ブローカークライアントの抽象化（実ブローカー / モック）
  - OrderManager / RiskManager / Reconciler を組み合わせた ExecutionEngine
  - paper_trading 環境では MockBrokerClient を使い data/paper_trading.db に記録

- Monitoring
  - SystemMonitor: CPU/MEM/Disk・プロセス生存・データ鮮度をチェック
  - TradeMonitor: 注文ログの滞留・約定異常などの検出（実装ファイル群参照）
  - RiskMonitor: ドローダウン・ポジション上限監視、リスクログ記録
  - KillSwitch: しきい値到達で data/kill.flag を書き込んで Execution を停止
  - MonitoringEngine: 上記モニタを束ねるポーリングループ

- Portfolio
  - 候補選定、等金額 / スコア加重ウェイト計算
  - セクター集中制限の適用
  - 株数決定（リスクベース・等金額等）、単元株丸め、集約キャップ処理

- Research
  - DuckDB 接続を用いたファクター計算（モメンタム・ボラティリティ・バリュー等）
  - 将来リターン、IC（Information Coefficient）、特徴量統計

- AI
  - ニュース NLP（OpenAI）で銘柄単位のセンチメントを ai_scores に書き込み
  - レジーム判定（ETF MA + マクロニュースを合成）
  - API 呼び出しはリトライ/バックオフ・バリデーションを備える

- ツール
  - 設定ウィザード（.env 作成）
  - 設定検証 CLI
  - Paper Trading 検証レポート生成スクリプト

---

## セットアップ手順

前提
- Python 3.10 以上（型注釈で | を使用）
- SQLite は標準ライブラリで利用
- 環境によっては root 以外でログや data ディレクトリへの書き込み権限が必要

推奨手順（例: Unix 系）

1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate

2. 必要パッケージのインストール
   - 必須:
     - duckdb
     - psutil
   - AI 機能を使う場合:
     - openai
   - 設定 YAML 検証（任意）:
     - PyYAML

   例:
   ```
   pip install duckdb psutil
   pip install openai        # AI機能を利用する場合
   pip install pyyaml        # config 検証を行う場合
   ```

   （プロジェクトに requirements.txt がある場合は pip install -r requirements.txt）

3. プロジェクトルートの確認
   - リポジトリをクローンした場合、pyproject.toml または .git があるディレクトリが自動でプロジェクトルートとして検出されます。
   - 自動で .env がロードされる（OS 環境変数 > .env.local > .env）。自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

4. 環境変数の初期化
   - 対話式ウィザードで .env を作成:
     ```
     python -m kabusys.config_setup
     ```
   - あるいは .env を手動で作成（下記サンプル参照）。

5. 設定検証（任意だが推奨）
   ```
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict
   ```

---

## 使い方

ここでは主要な起動コマンドと一般的なワークフローを示します。

### 環境設定ウィザード（.env 作成）
```
python -m kabusys.config_setup
```
対話式に必要項目の入力を促します。完了するとプロジェクトルートに .env を保存します。

サンプル .env（抜粋）
```
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
KABU_API_BASE_URL=http://localhost:18080/kabusapi
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0
```

### 設定検証
.env と config/*.yaml（存在する場合）をチェックします。
```
python -m kabusys.validate_config
python -m kabusys.validate_config --strict  # 警告も失敗扱い
```

### 実行エンジン起動（Execution）
ExecutionEngine を起動します。Paper Trading モードでは専用 DB を使います。
```
python -m kabusys.run_execution
```
- KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します。
- 起動時に data/stop_requested.flag が存在する場合は起動せず終了します。
- 実行中に data/stop_requested.flag を作成するとエンジンを停止します。
- PID ファイルは Settings.pid_file_path（デフォルト data/execution.pid）に書き込みます。

### 監視ループ起動（Monitoring）
SystemMonitor のポーリングループを起動します。
```
python -m kabusys.run_monitoring
```
- ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）。
- Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（Settings.sqlite_path）を使用します。
- 停止はプロジェクトルート data/stop_requested.flag を作成することで検知して終了。

### Paper Trading 検証レポート
過去期間の Paper Trading DB を集計して PASS/FAIL 判定を行います。
```
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db
```
- DB パスは --db または 環境変数 PAPER_TRADING_SQLITE_PATH で指定可能（デフォルト data/paper_trading.db）。

### AI（ニューススコア / レジーム判定）
- ニュースセンチメントスコア生成:
  - 関数: kabusys.ai.score_news（内部で OpenAI を呼ぶ）
  - 実行には OPENAI_API_KEY が必要
- レジーム判定:
  - 関数: kabusys.ai.regime_detector.score_regime（同様に API キー必要）
- これらは直接モジュール関数として呼び出すことを想定しており、スクリプト化して運用できます。
- API キーは引数で渡すか環境変数 OPENAI_API_KEY を利用します。

### 停止・Kill Switch
- Monitoring の KillSwitch は一定条件（ドローダウン超過、ポジション上限超過等）で data/kill.flag を作成し、ExecutionEngine はこれを検知して停止します。
- kill.flag を手動で消去するには:
  - 実装に応じてファイルを削除（例: rm data/kill.flag）
  - 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動クリアしますが、本番では 0 を推奨

---

## 主要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
- KABUSYS_ENV (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)（デフォルト: INFO）
- LOG_DIR (デフォルト: logs/)
- OPENAI_API_KEY（AI機能使用時に必要）
- MONITOR_POLL_INTERVAL（監視ポーリング間隔 秒、デフォルト 60）
- PAPER_FILL_MODE（paper_trading の埋め方: instant|partial|never|reject、デフォルト: instant）

詳細は kabusys.config.Settings のプロパティコメントを参照してください。

---

## ディレクトリ構成

以下はソースツリー（src/kabusys）のおおまかな構成です。

- src/kabusys/
  - __init__.py
  - config.py                # 環境変数読み込み・Settings
  - config_setup.py          # .env 対話式ウィザード
  - validate_config.py       # 設定検証 CLI
  - run_execution.py         # ExecutionEngine 起動スクリプト
  - run_monitoring.py        # SystemMonitor 起動スクリプト
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
    - alert_manager.py
  - execution/
    - execution_engine.py
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py
  - data/                    # ランタイムで生成される DB / フラグ / PID 等（デフォルト）
  - logs/                    # デフォルトログ出力先

（上記は実装ファイルの一部抽出です。実際のリポジトリではさらにファイルが存在する可能性があります）

---

## 参考・補足

- ロギング:
  - kabusys.utils.logging_setup.setup_logging を全スクリプトの最初で呼ぶことで、コンソール（stdout）＋日次ローテーティングファイル（logs/<app_name>.log）に統一して出力します。
- プロセス優先度:
  - 起動スクリプトは set_process_priority("high") を呼び出します（psutil が必要）。権限不足時は警告となり処理は継続します。
- DB:
  - monitoring 用の SQLite（Settings.sqlite_path）と分析用の DuckDB（Settings.duckdb_path）を併用します。
- Paper Trading:
  - KABUSYS_ENV=paper_trading の場合、発注はモック化され本番 DB と分離されます（PAPER_TRADING_SQLITE_PATH 使用）。
- テスト:
  - OpenAI 呼び出し部分は _call_openai_api をモックしてテスト可能な設計になっています。

---

不明点や README に追記してほしい内容（例えば詳細な環境変数一覧や実運用のデプロイ手順）があれば教えてください。必要に応じて .env.example の自動生成や systemd / supervisor 用のユニットファイル例も作成します。