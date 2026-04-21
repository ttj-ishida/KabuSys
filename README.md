# KabuSys

日本株向け自動売買システムのコードベース。  
ポートフォリオ構築、発注エンジン、監視・アラート、研究用ファクター計算、ニュースNLP / レジーム判定（LLM利用）などを含むモジュール群で構成されています。

バージョン: 0.1.0

---

## 概要

KabuSys は次の目的を持つモジュール群です。

- 株価データや財務データを用いてファクター計算・シグナル生成
- ポートフォリオ構築・銘柄単位のウェイト算出・注文数量決定
- ExecutionEngine による発注制御（paper_trading モードあり）
- 監視（System / Trade / Risk）と Kill Switch による自動停止
- OpenAI を利用したニュースセンチメント（AI スコア）と市場レジーム判定
- 検証用ツール（ペーパートレード検証レポート等）
- .env 対話式ウィザードと設定検証 CLI

この README では主要な使い方・セットアップ・ディレクトリ構成を説明します。

---

## 主な機能一覧

- Execution
  - ExecutionEngine（発注ロジック、RiskManager、OrderManager、Reconciler 等）
  - paper_trading モード（MockBrokerClient を使い別 DB に記録）
- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor の定期チェック
  - KillSwitch（条件を満たすと data/kill.flag を書き込み、Execution を停止）
  - 監視用 SQLite DB（data/monitoring.db）初期化ユーティリティ
- Portfolio
  - 候補選定、等重・スコア重み計算、ポジションサイズ計算、セクター制約などの純粋関数
- Research
  - ファクター計算（momentum/value/volatility 等）、将来リターン、IC 計算
- AI
  - news_nlp.score_news: OpenAI で記事群を評価して ai_scores に格納
  - regime_detector.score_regime: MA200 とマクロニュースを合成して market_regime を更新
- Utils
  - 統一ログ設定（logs/）、プロセス優先度設定、.env 自動ロード / ウィザード / 検証
- Tools
  - paper_verification_report: ペーパートレード DB から検証レポート生成

---

## 必要条件 / 依存パッケージ

主に以下が必要になります（プロジェクトで明示された直接的依存）:

- Python 3.9+（コード内 type annotation に合わせる）
- duckdb
- psutil
- openai（AI 機能を使う場合）
- （任意）PyYAML（`kabusys.validate_config` が config/*.yaml の検証を行う場合）

インストール例:

```bash
pip install duckdb psutil openai pyyaml
```

（プロジェクトに requirements.txt があればそちらを使用してください）

---

## セットアップ手順（ローカル）

1. リポジトリをクローンしてソースルートへ移動
2. Python 仮想環境を作成して有効化
3. 依存パッケージをインストール（上記参照）
4. .env を作成
   - 対話式ウィザード: `python -m kabusys.config_setup`
   - もしくは手動で `.env` に必要な環境変数を設定
5. 設定検証: `python -m kabusys.validate_config`

注意点:
- 自動で .env をロードする仕組みがあり（プロジェクトルートの `.env` / `.env.local` を参照）、OS 環境変数が優先されます。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 主な環境変数（代表的なもの）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

主要（省略せずに設定推奨）:
- KABUSYS_ENV — 実行環境: `development` | `paper_trading` | `live`  
  - `paper_trading` のときは MockBroker と `data/paper_trading.db` を使用（本番 DB と分離）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（例: INFO）
- OPENAI_API_KEY — OpenAI を利用する機能の API キー
- PAPER_FILL_MODE — paper_trading の注文成約挙動: `instant` | `partial` | `never` | `reject`
- KILL_FLAG_CLEAR_ON_START — 本番での自動クリアを防止する推奨値は `0`

その他:
- LOG_DIR — ログ出力先（デフォルト: logs/）
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、デフォルト: 60）

簡単な .env サンプル:
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...
```

---

## 起動・使い方

各モジュールはモジュール実行（-m）で起動できます。

1. 設定ウィザード（.env 作成）
   ```
   python -m kabusys.config_setup
   ```

2. 設定検証
   ```
   python -m kabusys.validate_config
   # 警告を FAIL として扱う場合:
   python -m kabusys.validate_config --strict
   ```

3. 監視ループ起動（Monitoring）
   ```
   python -m kabusys.run_monitoring
   ```
   - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を秒単位で上書き可能（デフォルト 60）。
   - 監視は常に Settings.sqlite_path（本番 sqlite）を使用して監視 DB を初期化します。
   - 停止: プロジェクトルートの `data/stop_requested.flag` を作成するとループが検知して終了します。

4. ExecutionEngine 起動（発注エンジン）
   ```
   python -m kabusys.run_execution
   ```
   - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用して `data/paper_trading.db` を使います（本番 DB と完全分離）。
   - 起動時に `data/stop_requested.flag` があれば起動しません。
   - Execution は `data/execution.pid` を書きます。
   - 停止: `data/stop_requested.flag` を作成するか、KillSwitch による `data/kill.flag` が書き込まれると停止処理を実行します。

5. Paper Trading 検証レポート（ツール）
   ```
   python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   # DB パス指定:
   python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
   ```

6. AI 機能（ライブラリとして利用）
   - news_nlp.score_news(conn, target_date, api_key=None)
     - DuckDB 接続と target_date（datetime.date）を渡してニューススコアを ai_scores テーブルに書き込みます。
     - OpenAI API キーは引数か環境変数 `OPENAI_API_KEY` を使用します。
   - regime_detector.score_regime(conn, target_date, api_key=None)
     - market_regime テーブルを更新します。
   - これらは library 関数なので Python コード内で呼び出して使用します。

---

## モニタリング / Kill Switch の挙動（要点）

- RiskMonitor が Drawdown やポジション上限違反を検出すると risk_logs に記録し、KillSwitch が条件に応じて `data/kill.flag` を作成します。
- kill.flag が書き込まれると ExecutionEngine 側で検出して発注停止を行います（KillSwitch は冪等に書き込みます）。
- 手動で ExecutionEngine を強制停止したい場合は `data/stop_requested.flag` を作成してください（run_* スクリプトが監視して終了します）。
- run_monitoring は monitoring の DB 初期化を行います（init_monitoring_db）。

---

## ロギング

- ログは `kabusys.utils.logging_setup.setup_logging` により統一設定されます。
- デフォルトは stdout と日次ローテートのファイル（logs/<app_name>.log）に出力し、過去 30 日分を保持します。
- ログディレクトリは環境変数 `LOG_DIR` または引数で上書き可能。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下を想定）

- kabusys/
  - __init__.py
  - config.py — 環境変数 / Settings クラス、自動 .env ロード
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring 起動スクリプト
  - ai/
    - news_nlp.py — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py — 市場レジーム判定（OpenAI）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - execution/ (発注関連の実装群)
    - (BrokerClientFactory, ExecutionEngine, OrderManager, etc.)
  - monitoring/
    - monitoring_db.py — SQLite 永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - data/ (実行時に生成されるファイル)
    - monitoring.db (デフォルト)
    - paper_trading.db (paper_trading モード)
    - kabusys.duckdb (DuckDB, path は DUCKDB_PATH)
    - execution.pid
    - kill.flag / stop_requested.flag
  - logs/ (デフォルトのログ出力先)

---

## 開発メモ / 注意事項

- .env は決して Git にコミットしないでください（config_setup でも警告あり）。
- Monitoring 側の DB 初期化は冪等に実行されます（既存テーブルに対するマイグレーションも一部実装）。
- Paper Trading は本番 DB と物理的に分離するよう設計されています（`PAPER_TRADING_SQLITE_PATH` で変更可能）。
- AI 機能を利用する場合は OpenAI API のレートリミット・課金に注意してください。失敗時はフォールバック（0.0 等）する実装がされている箇所もありますが、運用ポリシーを定めてください。
- プロセス優先度は起動直後に `high` へ設定されます（プラットフォーム依存で設定に失敗する場合はログ警告）。

---

もし README に追加してほしいサンプルコマンド、運用フロー（例: デプロイ / サービス化 / systemd ユニット）、CI / テスト手順などがあれば教えてください。必要に応じてテンプレートや systemd サービス例も作成します。