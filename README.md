# KabuSys

日本株自動売買システムのコアライブラリおよび起動スクリプト群です。  
このリポジトリは、シグナル生成・ポートフォリオ構築・発注実行・監視・レポート・AI 支援（ニュース NLP / レジーム判定）といった主要コンポーネントを含みます。

## 主な目的
- 戦略に基づく注文作成と発注管理（ExecutionEngine）
- システム稼働監視・リスク監視・キルスイッチ
- Paper Trading 用の分離された DB と検証ツール
- DuckDB を用いたリサーチ（ファクター計算等）
- OpenAI を用いたニュースセンチメント / レジーム判定の実験的実装

---

## 機能一覧
- 設定管理
  - `.env` の自動読み込み（`.env` / `.env.local`、必要に応じて無効化可）
  - 対話式設定ウィザード（`config_setup.py`）
  - 起動前チェックツール（`validate_config.py`）
- 実行エンジン
  - ExecutionEngine（発注・注文管理・リスク管理・再突合）
  - Paper Trading モード（`KABUSYS_ENV=paper_trading` 時は MockBroker を使用し DB を分離）
- 監視
  - SystemMonitor（CPU / メモリ / ディスク / データ鮮度 / Execution プロセス監視）
  - TradeMonitor（滞留注文・約定異常検出など）
  - RiskMonitor（ドローダウン、ポジション上限監視）
  - KillSwitch（条件に基づく `data/kill.flag` 書き込み）
  - Polling ループ起動スクリプト（`run_monitoring.py`、ポーリング間隔は `MONITOR_POLL_INTERVAL` で上書き可）
- ツール
  - Paper Trading 検証レポート生成（`tools/paper_verification_report.py`）
- リサーチ / ポートフォリオ
  - ファクター計算（モメンタム / バリュー / ボラティリティ）
  - 特徴量解析（IC / 統計サマリ 等）
  - 銘柄選定・重み計算・ポジションサイズ算出・セクター制約の適用
- AI 関連（OpenAI）
  - ニュース NLP による銘柄センチメント（`ai/news_nlp.py`）
  - マクロ + ETF MA によるレジーム判定（`ai/regime_detector.py`）

---

## 前提・依存関係
最小限の実行に必要なパッケージ（例）:
- Python 3.9+
- duckdb
- psutil
- openai
- PyYAML（設定ファイル検証時に推奨）

インストール例:
```
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install duckdb psutil openai pyyaml
```

※ 実行環境や運用方針に応じて追加パッケージ / 固定バージョンを用意してください。

---

## セットアップ手順

1. リポジトリをクローンしてワークディレクトリへ移動
2. 仮想環境作成・有効化
3. 依存パッケージをインストール（上記参照）
4. .env 作成（対話式ウィザード推奨）

対話式ウィザードで `.env` を作成:
```
python -m kabusys.config_setup
```
ウィザードは `.env` を作成・更新します。作成後は設定検証を推奨します。

設定検証:
```
python -m kabusys.validate_config
# 警告も厳格に扱う場合:
python -m kabusys.validate_config --strict
```

自動 `.env` 読み込みについて: `kabusys.config` はプロジェクトルート（.git または pyproject.toml を検出）を基準に `.env` / `.env.local` を自動読み込みします。自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須環境変数（代表例）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

AI 機能を使う場合:
- OPENAI_API_KEY を設定（`ai` モジュールで必要）

DB パスのデフォルト:
- DuckDB: data/kabusys.duckdb
- SQLite (監視): data/monitoring.db
- Paper Trading SQLite: data/paper_trading.db（KABUSYS_ENV=paper_trading 時に使用）

---

## 使い方（起動 / スクリプト）

主要スクリプトはモジュールとして実行します。

- 監視ループ起動（SystemMonitor をポーリング）
```
python -m kabusys.run_monitoring
```
- ポーリング間隔を上書きする:
```
export MONITOR_POLL_INTERVAL=30
python -m kabusys.run_monitoring
```
デフォルト 60 秒。値が 0 以下のときはデフォルトにフォールバックします。

監視は常に本番の SQLite（`Settings.sqlite_path`）を使用します（環境にかかわらず）。

- 実行エンジン起動（ExecutionEngine）
```
python -m kabusys.run_execution
```
注意:
- `KABUSYS_ENV=paper_trading` の場合、MockBrokerClient を生成し、Paper 用 DB（`PAPER_TRADING_SQLITE_PATH` / デフォルト `data/paper_trading.db`）に記録します。本番 DB と完全に分離されます。
- 起動前に `data/stop_requested.flag` が存在すると起動せず終了します（停止フラグ）。
- 実行中は `data/stop_requested.flag` を検知するとエンジンを停止します。

- Paper Trading 検証レポート
```
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# DB パスを明示する場合:
python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
```

- AI スコアリング（プログラムから利用）
news_nlp と regime_detector の関数はライブラリ API として提供されています。例:
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_news(conn, target_date=date(2026,4,10), api_key="YOUR_OPENAI_KEY")
score_regime(conn, target_date=date(2026,4,10), api_key="YOUR_OPENAI_KEY")
```
（OpenAI API キーは引数で渡すか環境変数 `OPENAI_API_KEY` を使用）

---

## ログ・ファイル
- ロギングは共通ユーティリティ `kabusys.utils.logging_setup.setup_logging` で設定されます。
- デフォルトのログ出力先: stdout と 日次ローテーションされるファイル（logs/<app_name>.log）
  - 例: logs/execution.log, logs/monitoring.log
- ログディレクトリは環境変数 `LOG_DIR` で上書き可能。`LOG_LEVEL` でログレベルを制御。

---

## 停止 / キルスイッチ
- `KillSwitch` はリスク条件に応じて `data/kill.flag` に理由を書き込み、ExecutionEngine に停止を促します。`KillSwitch.clear()` で削除可能です。
- 監視 / 実行スクリプトは `data/stop_requested.flag` を見て自分自身のポーリングループ / スレッドを終了します。
- ExecutionEngine は `pid_file`（デフォルト `data/execution.pid`）を使用してプロセス管理します。

---

## ディレクトリ構成（主要ファイル）
（src/kabusys 以下の主要モジュールを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py        # （コードベースに存在）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py        # （コードベースに存在）
  - execution/
    - execution_engine.py    # Engine の実装（発注ループ等）
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py
  - monitoring/              # 監視関連（上にまとめ）
  - data/                    # default データディレクトリ（logs / db 等を配置）
  - config/                  # YAML テンプレート等（system_config.yaml など）

（プロジェクトルート）
- .env.example (想定)
- pyproject.toml / setup.cfg 等

---

## 開発者向けメモ / 注意点
- Settings（kabusys.config.Settings）は環境変数から値を取得します。未設定の必須変数にアクセスすると ValueError が発生します。
- `.env` 読み込みロジックはプロジェクトルート（.git / pyproject.toml）を基準に行うため、CWD に依存しません。
- Monitoring 側は監視 DB（SQLite）を常に本番パスから利用します（環境にかかわらず）。
- ExecutionEngine は Paper Trading 時に DB を分離するため、本番データとログが混ざらないようになっています。
- OpenAI 呼び出しは再試行（指数バックオフ）・レスポンスバリデーション・部分書き込み（冪等性配慮）などのフェイルセーフ処理を実装していますが、API 仕様変更には注意してください。
- DuckDB での executemany 空リストバインドなど、特定バージョン固有の制約を考慮した実装箇所があります。DuckDB の互換性に注意してください。

---

必要に応じて README の各セクションをプロジェクトの運用ルールに合わせて調整してください。特に本番運用時のシークレット管理・ログローテーション・プロセス監視（systemd / supervisor 等）は別途運用ドキュメント化することを推奨します。