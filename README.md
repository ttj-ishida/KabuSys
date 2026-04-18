# KabuSys

日本株自動売買システム (KabuSys) のリポジトリ用 README。  
この README にはプロジェクト概要、主要機能、セットアップ手順、基本的な使い方、およびディレクトリ構成を日本語でまとめています。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システム（研究・シミュレーション・ペーパートレード・本番対応）です。  
主な設計方針は以下の通りです。

- DuckDB / SQLite を用いたデータ集計と監視ログ永続化
- J-Quants / kabuステーション などの外部 API を利用したデータ取得・発注（設定により切替）
- Paper Trading（仮想発注）と Live（実口座発注）の明確な分離
- LLM（OpenAI）を使ったニュースセンチメント評価やレジーム判定機能
- 単体機能が純粋関数で実装されており、研究関数と実行エンジンが分離されている

---

## 機能一覧

- 環境設定ウィザード（.env の対話式作成 / 更新）
- 設定検証 CLI（.env / config/*.yaml の事前チェック）
- ExecutionEngine（発注エンジン）起動スクリプト
  - KABUSYS_ENV が `paper_trading` の場合は MockBroker を使用し、専用 DB に記録
  - 本番（live）/ 開発（development）を切替え
- Monitoring（監視）プロセス
  - システム状態、データ鮮度、滞留注文・リスク監視、Kill Switch（停止フラグ）の管理
- 監視 DB（SQLite）読み書き層（冪等なテーブル初期化を含む）
- ポートフォリオ構築関数群（候補選定・重み付け・ポジションサイズ計算、セクター制約など）
- リサーチ用モジュール（ファクター計算、特徴量探索、IC 計算など） — DuckDB を利用
- AI モジュール
  - ニュース NLP（OpenAI を使った銘柄別センチメントスコア）
  - 市場レジーム判定（MA とマクロニュースの LLM センチメント合成）
- ツール
  - Paper Trading 検証レポート生成スクリプト
- ユーティリティ
  - ロギング設定、プロセス優先度設定、環境ロード等

---

## 前提・依存関係

主に次のパッケージを使用します（環境に合わせて pip 等でインストールしてください）:

- Python 3.9+（型ヒント等を考慮）
- duckdb
- psutil
- openai
- PyYAML（config/*.yaml の構文チェック用、必須ではない）
- （SQLite は標準ライブラリ）

推奨インストール例（requirements.txt が用意されていればそれを使用）:
```
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリに移動します。

2. Python 仮想環境を作成して有効化（任意）:
```
python -m venv .venv
source .venv/bin/activate   # macOS / Linux
.venv\Scripts\activate      # Windows
```

3. 依存パッケージをインストール:
```
pip install duckdb psutil openai PyYAML
```

4. 環境変数（.env）を用意する:
   - 対話式ウィザードで作成・更新できます。
```
python -m kabusys.config_setup
```
   - 最低限必要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV: development | paper_trading | live
     - OPENAI_API_KEY（AI 機能を使う場合）

5. 設定検証（起動前チェック）:
```
python -m kabusys.validate_config
# 警告をエラー扱いにする場合:
python -m kabusys.validate_config --strict
```

注意:
- .env の自動読み込みはデフォルトで有効。プロジェクトルートに `.env` / `.env.local` を置いておくと起動時に読み込まれます。
- .env は絶対に Git にコミットしないでください（config_setup でも注意喚起あり）。

---

## 使い方

以下は主要なスクリプト／コマンドの使い方です。

1. ExecutionEngine（発注エンジン）の起動:
```
python -m kabusys.run_execution
```
- KABUSYS_ENV = `paper_trading` の場合は MockBrokerClient を使用し、データは `data/paper_trading.db`（PAPER_TRADING_SQLITE_PATH で上書き可）に保存されます。
- 実行中は PID ファイル（デフォルト: data/execution.pid）が作成されます。
- 停止はモジュール間で `data/stop_requested.flag` を検知して安全に停止します（監視プロセスから停止指示を送るなど）。

2. Monitoring（監視ループ）の起動:
```
# デフォルトは 60 秒間隔
python -m kabusys.run_monitoring

# 環境変数でポーリング間隔を変更（秒）
export MONITOR_POLL_INTERVAL=30
python -m kabusys.run_monitoring
```
- Monitoring は KABUSYS_ENV に関わらず本番用の sqlite_path（デフォルト `data/monitoring.db`）を使用します（監視ログは本番 DB に保存する想定）。
- 停止フラグ（`data/stop_requested.flag`）が存在すると監視ループは終了します。

3. Paper Trading 検証レポート生成:
```
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# DB パス指定:
python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
```
- 簡易的に稼働率、注文成功率、レイテンシなどを算出し PASS/FAIL 判定を行います。

4. AI 関連（ニュースセンチメント / レジーム判定）
- OpenAI API を使用するため、`OPENAI_API_KEY` を .env または環境変数で設定してください。
- 関数はライブラリ API としても利用可能（例: kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime）。

5. Kill Switch（強制停止）:
- KillSwitch は `data/kill.flag` を書き込むことで ExecutionEngine に停止命令を与えます（Monitoring が条件判定して書く、または手動でファイルを書いてもよい）。
- 実行エンジンは起動時に kill flag のクリア動作を設定（KILL_FLAG_CLEAR_ON_START）できますが、本番では自動クリアしないことが推奨されています。

6. ログ
- ログはデフォルトで `logs/` に出力され、ファイルは日次ローテーション（30日保持）されます。ログ設定は `kabusys.utils.logging_setup.setup_logging` で統一されています。
- 環境変数 `LOG_DIR`、`LOG_LEVEL` で制御できます。

---

## よく使う環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE（paper_trading の約定挙動: instant|partial|never|reject、デフォルト: instant）
- OPENAI_API_KEY（AI 機能利用時）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング秒。デフォルト 60）
- LOG_LEVEL（DEBUG/INFO/...）
- LOG_DIR（ログ出力ディレクトリ）

---

## ディレクトリ構成（概要）

以下は主要なファイル / モジュールの一覧と簡単な説明です（src/kabusys 以下）。

- __init__.py
  - パッケージ定義、バージョン情報

- config.py
  - 環境変数 / 設定の読み込み・検証
  - 自動 .env ロード機能（プロジェクトルート判定を含む）
  - Settings クラス（各種設定プロパティ）

- config_setup.py
  - .env 対話式ウィザード（初期作成 / 更新）

- validate_config.py
  - CLI ベースの設定検証ツール（必須環境変数やファイル存在等のチェック）

- run_execution.py
  - ExecutionEngine（発注エンジン）起動スクリプト
  - BrokerFactory、OrderManager、RiskManager、Reconciler 等を組み立てて実行

- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト
  - MONITOR_POLL_INTERVAL で間隔変更可能

- monitoring/
  - monitoring_db.py : SQLite に監視用テーブルを作成・読み書きする永続化層
  - system_monitor.py  : システムリソース・データ鮮度・プロセス PID チェック
  - trade_monitor.py   : （注文関連のチェック、滞留注文など）
  - risk_monitor.py    : ドローダウン・ポジション上限監視
  - kill_switch.py     : kill.flag の作成 / クリアロジック
  - monitoring_engine.py : 複数 Monitor を束ねてアラート/kill 評価を行う
  - alert_manager.py   : 通知（LINE 等）管理（存在）

- portfolio/
  - portfolio_builder.py : 候補選定、重み付け
  - position_sizing.py   : 株数決定、資金配分ロジック
  - risk_adjustment.py   : セクターキャップ、レジーム乗数

- research/
  - factor_research.py      : Momentum / Volatility / Value などファクター計算（DuckDB）
  - feature_exploration.py  : 将来リターン計算、IC 計算、統計サマリ
  - __init__.py             : 公開 API（zscore_normalize 等をインポート）

- ai/
  - news_nlp.py       : ニュースを集約して OpenAI に送りセンチメントを ai_scores に書き込む
  - regime_detector.py: MA とマクロニュースの LLM センチメントを合成して market_regime を書き込む

- utils/
  - logging_setup.py      : ルートロガー設定（console + TimedRotatingFileHandler）
  - process_priority.py   : プラットフォーム横断でのプロセス優先度 / CPU affinity 設定

- tools/
  - paper_verification_report.py : Paper Trading の簡易検証レポートを生成する CLI

- data/ (実行時生成・デフォルト)
  - monitoring.db（SQLite）
  - paper_trading.db（Paper Trading 用 DB）
  - kill.flag / stop_requested.flag / execution.pid 等の制御ファイル

---

## 運用上の注意点

- 本番環境（KABUSYS_ENV=live）では設定ミスによる誤発注が致命的になるため、validate_config による事前チェックを必ず行ってください。
- .env は絶対にリポジトリにコミットしないでください。
- Monitoring は監視ログの永続化先に本番 DB を使用する設計です。監視データは常に production 用 sqlite_path に保存されます（run_monitoring の仕様）。
- OpenAI を用いる機能は API 呼び出し回数・応答フォーマットに依存します。API キー・コストに注意してください。
- process priority / CPU affinity の設定は OS 権限に依存します。AccessDenied の場合は警告を出してスキップします。

---

## 開発・拡張のヒント

- 研究用の関数群（research/*、portfolio/*）は副作用を持たない純粋関数として設計されており、ユニットテストが書きやすくなっています。
- AI モジュールの API 呼び出し部分は個別関数で分離しているため、テスト時はモックしやすくなっています（例: _call_openai_api のパッチ）。
- DuckDB のクエリは SQL を多用して性能を稼いでいます。データスキーマ（prices_daily / raw_financials 等）を合わせることで簡単に検証できます。

---

必要なら以下を提供できます:
- requirements.txt の推奨内容
- サンプル .env.example
- 主要機能ごとの使用例（実際のコマンド例やユースケース）  

ご希望があれば追記します。