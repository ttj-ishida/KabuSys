# KabuSys

日本株自動売買システム（KabuSys）のリポジトリ向け README。  
本ドキュメントはリポジトリ内の主要スクリプト・モジュールを基に、導入手順、使い方、機能概観、ディレクトリ構成をまとめています。

---

## プロジェクト概要

KabuSys は日本株の自動売買／リサーチ基盤です。  
主な役割は次の通りです。

- 戦略に基づく銘柄選定・配分・株数決定（Portfolio construction）
- 発注エンジン（ExecutionEngine）による発注管理（実口座／ペーパートレード対応）
- 監視（Monitoring）および Kill Switch（異常発生時に発注エンジンを停止）
- DuckDB を使った分析・ファクター計算、Research ツール群
- ニュースの LLM を使った NLP スコアリング（OpenAI 利用、オプション機能）
- ペーパートレード検証レポート生成ツールなどのユーティリティ

設計思想としては、本番とペーパートレードを明確に分離し、環境変数/.env による設定管理、SQLite/DuckDB による簡易永続化、ロギングとプロセス優先度管理を重視しています。

---

## 機能一覧（抜粋）

- Execution
  - 実際のブローカークライアントとペーパートレード用 Mock クライアントを切り替え可能（KABUSYS_ENV）
  - リスク管理（RiskManager）、注文管理、照合（Reconciler）を含む ExecutionEngine
- Monitoring
  - システム状態（CPU/メモリ/ディスク）、データ鮮度、約定・注文の監視
  - Kill Switch（データ・ポジション不整合やドローダウンが閾値を超えた場合に停止フラグを書き込む）
  - 監視結果は SQLite（monitoring.db）へ記録
- Portfolio
  - 候補選定、等重／スコア重み、ポジションサイズ計算、セクター上限処理、レジーム乗数
- Research
  - DuckDB 上でのファクター計算（Momentum / Volatility / Value 等）
  - 将来リターン計算、IC 計算、統計サマリ
- AI（オプション）
  - ニュースのセンチメントスコアリング（OpenAI を利用）
  - レジーム判定（ETF + マクロニュースの合成）
- ツール
  - .env を対話式に生成する `config_setup`
  - 設定の事前検証をする `validate_config`
  - ペーパートレード検証レポート生成スクリプト

---

## 前提・依存関係（主なもの）

- Python 3.9+（型表記などの使用から推定）
- 外部ライブラリ（例）
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（config/*.yaml の中身検証を行う場合、optional）
- 標準ライブラリ: sqlite3, logging, threading, pathlib など

requirements.txt は本リポジトリに含まれていない場合があるため、上記パッケージを pip でインストールしてください。

例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

---

## 環境変数（重要）

必須（起動前に .env 等で設定）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主要な環境変数（代表例）:
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
  - paper_trading: 発注は MockBrokerClient に切り替え、ペーパートレード用 DB に記録
  - live: 本番発注（注意して使用）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- OPENAI_API_KEY: OpenAI を使う場合に必要
- PAPER_FILL_MODE: ペーパートレードでのフィルモード（instant | partial | never | reject）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒。run_monitoring で参照。デフォルト: 60）

注意: .env は絶対に Git にコミットしないでください（config_setup でも注意喚起あり）。

---

## セットアップ手順（クイックスタート）

1. リポジトリをクローン
```
git clone <repo-url>
cd <repo-dir>
```

2. 仮想環境を作成・有効化して依存関係をインストール
```
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install duckdb psutil openai pyyaml
```

3. .env ファイルを対話式で作成（推奨）
```
python -m kabusys.config_setup
```
- ウィザードは既存 .env を読み込み、各項目を確認・入力できます。

4. 設定の検証
```
python -m kabusys.validate_config
# 厳格モード（警告も失敗扱い）
python -m kabusys.validate_config --strict
```

5. 必要ディレクトリ（data, logs 等）を作成（`setup_logging` が自動で作りますが明示的に）:
```
mkdir -p data logs
```

---

## 使い方（主要スクリプト）

- ExecutionEngine（発注エンジン）起動
  - 実行（パッケージモジュールとして）:
    ```
    python -m kabusys.run_execution
    ```
  - 説明:
    - KABUSYS_ENV が `paper_trading` の場合、MockBrokerClient を使用して data/paper_trading.db に記録します（本番 DB と分離）。
    - 起動時に `data/stop_requested.flag` が存在すると起動を中止します。
    - Engine はデーモンスレッドで走り、同ディレクトリの `data/execution.pid` に PID を書くようになっています（設定で上書き可）。

- Monitoring（監視ループ）起動
  - 実行:
    ```
    python -m kabusys.run_monitoring
    ```
  - 説明:
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を秒数で上書き可能（デフォルト 60 秒）。
    - 監視は本番 sqlite_path（Settings.sqlite_path）を使用して永続化します（環境に関係なく本番 DB を参照する設計）。
    - 停止は `data/stop_requested.flag` を作成することで行います（監視ループはこのファイルの存在を見て終了）。

- .env の生成
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- ペーパートレード検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - `--db` で DB パスを指定可能。環境変数 `PAPER_TRADING_SQLITE_PATH` も利用できます。

- AI 機能（ニューススコアリング / レジーム判定）
  - OpenAI API キーが必要（環境変数 `OPENAI_API_KEY`）。
  - プログラム API を呼ぶ形で使用（例: `kabusys.ai.score_news` を呼び出して DuckDB 接続と日付を渡す）。

---

## 運用上の注意

- KABUSYS_ENV を `live` にすると実際に発注が行われます。設定（LINE 通知、Kill Switch 等）を十分確認してください。
- Kill Switch（`data/kill.flag`）や停止フラグ（`data/stop_requested.flag`）によってエンジンを安全に停止できます。`KILL_FLAG_CLEAR_ON_START` を `1` にすると起動時に kill.flag を自動クリアしますが、本番では `0` を推奨します。
- ログは `logs/<app_name>.log` に日次ローテーションで保存されます（デフォルト 30 日分保持）。
- `run_monitoring` は監視データを永続化します。必要に応じてバックアップ・保全の運用を行ってください。
- OpenAI 利用部分は API のレートやコストに注意。失敗時はフェイルセーフ（デフォルトでスコア 0 やスキップ）動作をとるよう設計されています。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要モジュールと説明です。パッケージは Python パッケージとして動作します（`python -m kabusys.xxx` で一部スクリプトを実行）。

- src/kabusys/
  - __init__.py
  - config.py — 環境変数/.env 読み込みと Settings クラス
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - ai/
    - news_nlp.py — ニュースセンチメント（OpenAI）
    - regime_detector.py — 市場レジーム判定（OpenAI）
  - monitoring/
    - monitoring_db.py — 監視 DB（SQLite）ラッパー
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — 注文/約定監視（コードベースに含まれる想定）
    - risk_monitor.py — ドローダウン / ポジション制限監視
    - monitoring_engine.py — 各モニタを束ねるエンジン
    - kill_switch.py — Kill Switch 実装
    - alert_manager.py — 通知管理（LINE 等。コードベースに存在すると想定）
  - execution/
    - execution_engine.py — 発注エンジンコア（EngineConfig, run_session 等）
    - broker_factory.py — ブローカークライアント生成（Mock / 実クライアント切替）
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py — 発注周りのコンポーネント
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数計算・資金配分
    - risk_adjustment.py — セクター上限・レジーム乗数
  - research/
    - factor_research.py — ファクター計算（DuckDB）
    - feature_exploration.py — 特徴量探索・IC 等
  - data/（実行時に生成される想定: DB・フラグ等）
    - monitoring.db（デフォルト）, paper_trading.db（ペーパートレード用）, kill.flag, stop_requested.flag, execution.pid
  - logs/（ログ出力先）

（実際のリポジトリによりファイル/サブパッケージの有無や名前が若干異なる場合があります。上はコードベースに基づく主要構成の説明です）

---

## 開発者向け備考

- DB マイグレーション: monitoring_db.init_monitoring_db は冪等でテーブル作成・一部カラム追加を行います。既存 DB 互換のための簡易マイグレーション処理が含まれます。
- ロギング: 全スクリプトは `kabusys.utils.logging_setup.setup_logging(app_name=...)` を呼んで統一的にログを設定します。ログディレクトリ作成に失敗した場合はコンソールのみで継続します。
- プロセス優先度: 起動スクリプトは最初に `set_process_priority("high")` を呼びます（psutil を使用）。権限がない場合は警告のみで続行されます。
- テスト: 各モジュールは比較的純粋関数を多用しているため単体テストを書きやすい構造です。OpenAI 呼び出し等は内部呼び出しをテスト時に差し替え可能に設計されています。

---

## 参考コマンドまとめ

- .env 作成ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- エンジン・監視起動
  ```
  python -m kabusys.run_execution
  python -m kabusys.run_monitoring
  ```

- ペーパートレード検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

README はここまでです。追加で README に含めたい内容（例: サンプル .env、詳細なログの見方、ユニットテスト手順、CI 設定等）があれば教えてください。必要に応じて追記・テンプレート化します。