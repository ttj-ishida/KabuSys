# KabuSys

日本株自動売買プラットフォーム（モジュール群）のリポジトリ説明書。  
このプロジェクトは売買実行エンジン、監視・Kill Switch、ポートフォリオ構築、ファクター研究、ニュースNLP を組み合わせた自動売買フレームワークです。各コンポーネントは分離・再利用可能なモジュールとして実装されています。

---

## 概要

KabuSys は以下の機能を備えた、運用を意識した日本株自動売買システムのライブラリ兼実行スクリプト群です。

- 注文発行・約定管理を行う ExecutionEngine（本番 / ペーパートレード切替）
- システム稼働状況・データ鮮度・注文状態・リスクの監視（Monitoring）
- Kill Switch（閾値超過時に停止フラグを書き込み ExecutionEngine を停止）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算・セクター制限）
- ファクター計算・特徴量探索（DuckDB 上の価格・財務データを利用）
- ニュースの LLM（OpenAI）によるセンチメントスコアリングとレジーム推定
- ペーパートレード向け検証レポート生成ツール

設計方針として、データベース（DuckDB / SQLite）を使った分析、外部 API 呼び出しのフェイルセーフ、設定の自動ロードやウィザード等の運用性向上に配慮しています。

---

## 主な機能一覧

- 設定管理
  - .env 自動ロード（プロジェクトルートに基づく）
  - 対話式環境設定ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
- 実行エンジン
  - ExecutionEngine（本番 / paper_trading 切替）
  - ブローカーファクトリ（MockBrokerClient 利用で paper_trading を完全分離）
  - リスクマネージャ、オーダーマネージャ、リコンシリエーション
- 監視
  - SystemMonitor（CPU/メモリ/ディスク、プロセス存在、データ鮮度）
  - TradeMonitor / RiskMonitor（滞留注文、ドローダウン等）
  - MonitoringEngine（各 Monitor を統合しポーリング）
  - KillSwitch（条件に応じて data/kill.flag を書き込み停止）
  - 永続化：SQLite（monitoring.db）を用いた監視ログ
- ポートフォリオ構築
  - 候補選定、均等配分・スコア加重配分
  - リスク調整（セクターキャップ、レジーム乗数）
  - ポジションサイズ計算（ロット丸め、aggregate cap）
- 研究（Research）
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ
- AI（OpenAI）
  - news_nlp: ニュース記事群を LLM でスコアリングして ai_scores に書込
  - regime_detector: ETF MA とマクロニュースで市場レジームを判定
  - API 呼び出しはリトライやフォールバック（失敗時は安全なデフォルト）あり
- 運用ツール
  - paper_verification_report: ペーパートレード DB から検証レポートを生成

---

## 動作要件（推奨）

- Python >= 3.10
- 必要パッケージ（一部は機能利用時のみ）
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証時のみ推奨）
- 標準ライブラリ: sqlite3, logging, threading, argparse 等

インストール例（仮の requirements）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

※ 実行環境によっては追加の依存が必要になる場合があります（例: OS 権限制約で psutil の一部機能が制限されることがあります）。

---

## セットアップ手順

1. リポジトリを取得
   - git clone で取得してください。

2. Python 仮想環境作成と依存インストール
   - 上記「動作要件」を参照して仮想環境を作成し、必要パッケージをインストールします。

3. .env 作成（対話式ウィザード推奨）
   - 対話式に .env を生成・更新する:
     ```
     python -m kabusys.config_setup
     ```
   - 主要な環境変数（必須）
     - JQUANTS_REFRESH_TOKEN（J-Quants API）
     - KABU_API_PASSWORD（kabuステーション API）
   - 運用上重要な変数
     - KABUSYS_ENV: development | paper_trading | live
     - DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH
     - LOG_LEVEL, LOG_DIR
     - OPENAI_API_KEY（AI 機能を使う場合）

   - 自動ロードは既定で有効（プロジェクトルートに .env が存在すれば起動時に読み込まれます）。自動ロードを無効化したい場合は環境変数:
     ```
     KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

4. 設定検証
   - 作成した設定を検証:
     ```
     python -m kabusys.validate_config
     ```
   - --strict を付けると警告も失敗扱いになります:
     ```
     python -m kabusys.validate_config --strict
     ```

5. データベース初期化
   - 監視用 SQLite（デフォルト: data/monitoring.db）はスクリプト起動時に必要なテーブルが自動作成されます（init_monitoring_db）。
   - ペーパートレード用 DB は PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）に格納されます。

---

## 使い方（主要コマンド）

- 実行エンジン（ExecutionEngine）起動
  - 本番 / ペーパートレードは KABUSYS_ENV により切替
  - 起動:
    ```
    python -m kabusys.run_execution
    ```
  - ペーパートレード環境では MockBrokerClient を使用し、専用 DB（data/paper_trading.db）に記録します。

- 監視プロセス起動
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（デフォルト: 60）
    ```
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```
  - 監視は常に本番の sqlite_path（monitoring DB）を使用します（環境に依存せず）。

- 設定ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- ペーパートレード検証レポート（ツール）
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - DB パスは --db オプションまたは環境変数 PAPER_TRADING_SQLITE_PATH で指定可能。

- AI 関連（ライブラリ呼び出し）
  - ニューススコアリング:
    ```
    from kabusys.ai import score_news
    score_news(duckdb_conn, target_date, api_key="...")  # 書き込み件数を返す
    ```
  - レジーム判定:
    ```
    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date, api_key="...")
    ```

- Kill / Stop
  - ExecutionEngine は data/stop_requested.flag や data/kill.flag 等を検査して外部停止を検出します。運用時はこれらフラグファイルで安全停止を行います。

---

## 重要な運用・安全注意点

- KABUSYS_ENV=live の場合は本番環境です。設定や Kill Switch の取り扱いに十分注意してください（validate_config は live 時に追加警告を行います）。
- .env は絶対にバージョン管理にコミットしないでください。
- OpenAI を利用する機能は API キーとコストを伴います。API 呼び出しはリトライロジック・フォールバックを備えていますが、十分な監視を推奨します。
- Process priority: 起動スクリプトはプロセス優先度を "high" に設定しようとします（set_process_priority）。OS 権限や環境により失敗する場合は警告を出して継続します。
- ペーパートレードは本番 DB とは完全に分離されます（PAPER_TRADING_SQLITE_PATH を使用）。

---

## ディレクトリ構成（主なファイル）

（src/kabusys 以下を想定）

- run_execution.py
  - ExecutionEngine を起動するエントリポイント
- run_monitoring.py
  - SystemMonitor のポーリング起動スクリプト
- config.py
  - 環境変数 / Settings 管理、自動 .env ロード
- config_setup.py
  - 対話式 .env 生成ウィザード
- validate_config.py
  - 設定検証 CLI
- __init__.py
  - パッケージ定義 (version 等)
- tools/
  - paper_verification_report.py
- ai/
  - news_nlp.py
  - regime_detector.py
- monitoring/
  - monitoring_db.py
  - system_monitor.py
  - trade_monitor.py (存在する想定)
  - risk_monitor.py
  - kill_switch.py
  - monitoring_engine.py
  - alert_manager.py (存在する想定)
- execution/
  - execution_engine.py
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - broker_factory.py
  - risk_manager.py
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

（上は主要ファイルの抜粋です。実際のツリーは src/kabusys/ 配下を参照してください。）

---

## 開発者向けメモ

- DuckDB 接続は研究・AI モジュールで主に利用されます。prices_daily / raw_financials / raw_news 等のテーブルを前提に設計されています。
- 監視ログは SQLite（monitoring.db）へ永続化されます。init_monitoring_db() は冪等でスキーマ作成・マイグレーションを行います。
- LLM（OpenAI）呼び出しは JSON mode を前提に厳密なレスポンス検証を行います。API エラーはリトライ／フォールバックするよう実装されています。
- 単体関数群（portfolio/*.py、research/*.py）は副作用がなく、ユニットテストが書きやすい設計です。

---

README は以上です。初期セットアップや運用上の疑問があれば、使いたい機能（例: ExecutionEngine の詳細、ブローカー実装、DB スキーマ）を指定していただければ、さらに詳しい手順や解説を追加します。