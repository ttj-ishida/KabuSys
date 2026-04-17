# KabuSys — 日本株自動売買システム

このリポジトリは日本株向けの自動売買フレームワーク（KabuSys）のコア実装の一部です。  
本 README はコードベース（src/kabusys/*）を対象に、概要・機能・セットアップ手順・使い方・ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は、シグナル生成・ポートフォリオ構築・発注（ExecutionEngine）・監視（Monitoring）・リスク管理・研究/解析（DuckDB ベース）・AI（OpenAI を使ったニュースセンチメント等）を含む自動売買システムの骨組みを提供します。  
設計方針のポイント：

- DuckDB を分析・研究用データベースとして使用（prices_daily / raw_financials 等）。
- SQLite を監視ログ・注文履歴（paper_trading 用は分離）に使用。
- 環境変数ベースの設定（.env サポート、config_setup でウィザード生成可能）。
- 実環境（live）とペーパートレード（paper_trading）を明確に分離。  
- OpenAI を利用したニュースNLP・レジーム判定機能（API キー必須、失敗時は安全側フォールバック）。
- プロセス優先度や CPU affinity の補助ユーティリティ（psutil 必須）。

---

## 主な機能一覧

- Execution
  - ExecutionEngine の起動スクリプト（run_execution.py）
  - Broker クライアントの抽象化（実ブローカー / MockBroker 切替）
  - オーダー管理、リスク管理、注文履歴保存

- Monitoring
  - system_monitor: CPU/メモリ/ディスク/プロセス監視、データ鮮度チェック
  - trade_monitor: 滞留注文・約定価格異常検出
  - risk_monitor: ドローダウン・ポジション上限監視
  - monitoring_engine: 各 Monitor を束ねてポーリング
  - kill_switch / kill.flag による ExecutionEngine 停止トリガー
  - AlertManager: LINE Messaging API による通知（任意）

- Portfolio construction
  - 候補選定・重み付け（等金額・スコア重み）
  - セクター上限適用、レジーム乗数
  - ポジションサイジング（単元株丸め、aggregate cap）

- Research / Data
  - DuckDB を活用したファクター計算（モメンタム/ボラティリティ/バリュー等）
  - 将来リターン計算、IC 計算、ファクター統計サマリー

- AI
  - news_nlp: OpenAI によるニュースの銘柄別センチメント算出・ai_scores 書き込み
  - regime_detector: MA200 とマクロニュースから市場レジーム判定

- ツール
  - 設定ウィザード（config_setup.py）: .env の対話式生成・更新
  - 設定検証 CLI（validate_config.py）
  - Paper Trading 検証レポート生成（tools/paper_verification_report.py）

---

## 必須 / 推奨依存パッケージ

少なくとも以下をインストールしてください（バージョンは利用環境に合わせて調整してください）。

- Python 3.9+
- duckdb
- psutil
- requests
- openai (AI 機能を使う場合)
- PyYAML （config YAML 検証を行う場合）
- （その他プロジェクト固有のライブラリがあれば requirements.txt を参照）

例（pip）:
```
pip install duckdb psutil requests openai PyYAML
```

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ
2. Python 仮想環境を作成・有効化（推奨）
3. 依存パッケージをインストール（上記参照）
4. data ディレクトリを作成（DB ファイルやフラグファイルを保存）
   ```
   mkdir -p data
   ```
5. .env の作成 — 対話式ウィザードを推奨:
   ```
   python -m kabusys.config_setup
   ```
   もしくは手動で `.env` を作成してください（下記「主要な環境変数」参照）。
6. 設定内容を検証:
   ```
   python -m kabusys.validate_config
   ```
   `--strict` を付けると警告も失敗扱いになります。
7. DuckDB / SQLite の初期化は各起動スクリプト（monitoring / execution）で自動的に行われます。

---

## 主要な環境変数（.env 例）

最低限必要な必須キー:
- JQUANTS_REFRESH_TOKEN （J-Quants API 用）
- KABU_API_PASSWORD （kabuステーション API 用）

代表的な設定（デフォルトは括弧内）:
```
KABUSYS_ENV=development            # development | paper_trading | live
JQUANTS_REFRESH_TOKEN=your_token
KABU_API_PASSWORD=your_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
PAPER_FILL_MODE=instant           # instant | partial | never | reject
OPENAI_API_KEY=…                   # AI 機能使用時に必要
LINE_CHANNEL_ACCESS_TOKEN=…        # 任意（通知用）
LINE_USER_ID=…                     # 任意（通知用）
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0         # 本番では 0 推奨
```

補足:
- KABUSYS_ENV によって挙動が変わります。`paper_trading` は MockBroker を使い、Paper 用の SQLite（PAPER_TRADING_SQLITE_PATH）に記録され、本番 DB と分離されます。
- MONITOR_POLL_INTERVAL（監視のポーリング間隔秒）は環境変数で上書き可能（デフォルト 60 秒、run_monitoring で参照）。

---

## 使い方（起動・CLI）

- 環境設定ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- ExecutionEngine を起動（デーモン化は別途プロセスマネージャで実施してください）
  ```
  python -m kabusys.run_execution
  ```
  - 起動時に data/stop_requested.flag が存在すると起動を中止します。
  - 起動後、停止は stop フラグ作成で可能（下記参照）。

- Monitoring を起動（システム監視ポーリング）
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可能（例: MONITOR_POLL_INTERVAL=30）。
  - 監視は常に本番用 sqlite_path を使う（環境に依らず監視 DB に書き込む設計）。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - --db オプションで PAPER_TRADING_SQLITE_PATH を指定可能。

- AI 機能（ニューススコア / レジーム判定）
  - OpenAI API キーを環境変数 OPENAI_API_KEY に設定してください。
  - ニューススコア: kabusys.ai.score_news をプログラムから呼ぶ（API キーまたは引数で指定可能）。
  - レジーム判定: kabusys.ai.regime_detector.score_regime をプログラムから呼ぶ。

停止・フラグ関連:
- run_execution.py / run_monitoring.py はプロジェクトの data/stop_requested.flag を監視しています。運用上の停止要求を行う場合はこのファイルを作成してください（通常は管理スクリプトで生成）。
- kill.flag（Settings.kill_flag_path, デフォルト data/kill.flag）は KillSwitch による自動停止シグナルです。KillSwitch.evaluate() が条件を満たすと書き込まれ、ExecutionEngine はこのフラグを検出して停止します。
- KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアします（本番では 0 を推奨）。

ログレベル:
- LOG_LEVEL 環境変数でログ詳細度を調整できます（DEBUG/INFO/WARNING/ERROR/CRITICAL）。

注意:
- process priority の設定（高優先度）は psutil を使用します。OS により権限が必要になる場合があります。失敗しても警告ログが出てスキップされます。

---

## 主要モジュールと簡単な説明（ディレクトリ構成）

以下は src/kabusys 配下の主要ファイルと概要です。

- kabusys/
  - __init__.py — パッケージ定義
  - config.py — 環境変数読み込み・Settings クラス、自動 .env ロード機能
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前の設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト

- kabusys/ai/
  - news_nlp.py — ニュースを OpenAI でスコアリングして ai_scores に書き込む
  - regime_detector.py — マクロニュースと MA200 を合成して市場レジームを判定

- kabusys/monitoring/
  - monitoring_db.py — SQLite 監視 DB の初期化・読み書きユーティリティ（MonitoringDB）
  - system_monitor.py — CPU/メモリ/ディスク/プロセス/データ鮮度監視
  - trade_monitor.py — 注文滞留・約定価格異常検出
  - risk_monitor.py — ドローダウン / ポジション数監視
  - monitoring_engine.py — 各 Monitor を束ねる
  - kill_switch.py — kill.flag 管理
  - alert_manager.py — LINE 通知（push）

- kabusys/portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - risk_adjustment.py — セクターキャップ・レジーム乗数
  - position_sizing.py — 発注株数計算・aggregate cap
  - __init__.py — エクスポート

- kabusys/research/
  - factor_research.py — モメンタム/ボラティリティ/バリュー等のファクター計算（DuckDB）
  - feature_exploration.py — 将来リターン、IC、統計サマリー等
  - __init__.py — エクスポート

- kabusys/tools/
  - paper_verification_report.py — Paper Trading の検証レポート生成
  - __init__.py

- kabusys/utils/
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
  - __init__.py

その他:
- data/ — DB ファイル・フラグファイル等を置くディレクトリ（プロジェクトルートに作成）
  - data/kabusys.duckdb （デフォルト）
  - data/monitoring.db （デフォルト監視 DB）
  - data/paper_trading.db （ペーパートレード DB）
  - data/execution.pid, data/stop_requested.flag, data/kill.flag など

---

## 運用上の注意・ベストプラクティス

- 本番（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START を 0 にして、kill.flag の自動クリアを防いでください。
- paper_trading モードは本番 DB と完全に分離されるよう設計されていますが、.env の DB パスを必ず確認してください。
- OpenAI まわりは外部 API 呼び出しのため、API キー・コスト・レート制限に注意してください。スロットリングやリトライ方針は実装内にありますが、運用での監視が必要です。
- psutil を使う操作（優先度設定・CPU affinity）は権限が必要になる場合があり、権限不足時は設定がスキップされる（ログ出力される）点に注意してください。
- DuckDB を分析用途で使用する際はデータ更新やスキーマを意識して運用してください（ai/regime などは冪等に書き込む実装になっています）。

---

## 参考コマンドまとめ

- .env 作成（ウィザード）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- Execution 起動
  ```
  python -m kabusys.run_execution
  ```

- Monitoring 起動
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

- Paper Trading レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

README は随時更新してください。実運用・拡張（デーモン化、コンテナ化、サービス監視、CI/CD など）に合わせて設定や起動方法を追記することを推奨します。