# KabuSys — 日本株自動売買システム

このリポジトリは日本株向けの自動売買システム（KabuSys）のコアライブラリと起動スクリプト、運用用ツール群を含みます。  
本 README はコードベース（src/kabusys 以下）をもとに、セットアップ・起動・主な機能を日本語でまとめたものです。

注意: .env や API キー等の秘密情報は決してバージョン管理にコミットしないでください。

---

## プロジェクト概要

KabuSys は以下のような責務を持つモジュール群から構成されます。

- execution: 発注エンジン、オーダーマネージャ、リスク管理、ブローカークライアントの集約
- monitoring: システム稼働監視、トレード監視、リスク監視、Kill Switch 発動ロジック、監視ログ永続化（SQLite）
- ai: ニュースの NLP スコアリング・市場レジーム判定（OpenAI を使用）
- research: ファクター計算・特徴量探索（DuckDB を用いた分析）
- portfolio: 候補銘柄選定、配分・株数決定、セクター制約・レジーム補正
- utils: ロギング設定、プロセス優先度 / CPU affinity 設定などユーティリティ
- tools: ペーパートレード検証レポート等の運用ツール

スクリプト / エントリポイント:
- 起動スクリプト: `run_execution.py`, `run_monitoring.py`
- 設定支援: `config_setup.py`
- 設定検証: `validate_config.py`
- 運用ツール: `tools/paper_verification_report.py`

---

## 主な機能一覧

- ExecutionEngine 起動（本番 / ペーパー分離）
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い `data/paper_trading.db` に記録
- Monitoring
  - システム（CPU/メモリ/ディスク）、プロセス存在、データ鮮度監視
  - トレードログ監視（滞留注文・約定異常の検出）
  - リスク監視（ドローダウン・ポジション数上限）と Kill Switch（flag ファイルによる停止）
  - 監視ログ永続化（SQLite）と簡易ダッシュボードテーブル
- AI
  - ニュース記事を LLM（OpenAI）に送り銘柄ごとのセンチメントスコアを DuckDB に書き込み
  - マクロニュース＋ETF MA 乖離から日次の市場レジーム（bull/neutral/bear）判定
- Research / Portfolio
  - DuckDB 上でファクター算出（モメンタム、ボラティリティ、バリューなど）
  - 候補選定、重み算出、ポジションサイズ計算、セクター制約・レジーム乗数
- 運用ツール
  - ペーパートレード検証レポート生成（成功率・稼働率・レイテンシ等）

---

## 前提・依存（主要）

最低限必要なライブラリ（例）:
- Python 3.9+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（config 検証で YAML を検査したい場合）

実際は環境に応じて requirements.txt を用意してください（本リポジトリに明示的な requirements は含まれていません）。

---

## セットアップ手順

1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール（例）
   - pip install duckdb psutil openai PyYAML

3. .env の作成（対話ウィザード推奨）
   - python -m kabusys.config_setup
     - 対話的に .env を作成 / 更新します（デフォルトはプロジェクトルートの .env）。

4. 設定の検証
   - python -m kabusys.validate_config
   - 警告を厳格に扱う場合:
     - python -m kabusys.validate_config --strict

5. データディレクトリの作成（必要に応じて）
   - デフォルトの DB / PID / ログは `data/` / `logs/` 下に作成されます。スクリプトが自動作成しますが、権限やパスに注意してください。

---

## 環境変数（主なもの）

重要な環境変数（必須 / 主要）:

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- OPENAI_API_KEY (AI 機能を使う場合)
- KABUSYS_ENV: `development` | `paper_trading` | `live`（デフォルト: development）
  - paper_trading の場合、発注はモッククライアントにより `data/paper_trading.db` に記録され、本番 DB と分離されます
- DUCKDB_PATH: デフォルト `data/kabusys.duckdb`
- SQLITE_PATH: 監視 DB のパス（デフォルト `data/monitoring.db`）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード時の sqlite（デフォルト `data/paper_trading.db`）
- LOG_LEVEL: ログレベル（INFO 等）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: ペーパートレードの約定挙動（instant|partial|never|reject）
- KILL_FLAG_CLEAR_ON_START: 起動時に `kill.flag` を自動削除するか（0/1）

例: .env に書かれるべき主要項目（サンプル、実運用では秘密は隠す）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_password_here
OPENAI_API_KEY=sk-...
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
```

※ `.env` は config_setup で生成・更新できます。

---

## 使い方（起動コマンド）

プロジェクトルートで以下コマンドを実行します（モジュールとして起動）。

- ExecutionEngine を起動（本番 / paper に応じて挙動が変わる）
  - python -m kabusys.run_execution
  - 実行中は `data/execution.pid` を作成し、停止は `data/stop_requested.flag` を作成するか Kill Switch により `data/kill.flag` が書かれると正常に停止します。
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い `data/paper_trading.db` に記録します。

- Monitoring を起動（ポーリングループ）
  - python -m kabusys.run_monitoring
  - デフォルト 60 秒間隔。環境変数 `MONITOR_POLL_INTERVAL` で秒数を上書き可能（正の整数）。
  - 監視は本番の sqlite_path を常に使用します（KABUSYS_ENV に依らず本番 DB を参照）。

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告があるだけでも exit(1) で失敗扱い

- ペーパートレード検証レポート（運用ツール）
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  - デフォルト DB: `data/paper_trading.db` または環境変数 `PAPER_TRADING_SQLITE_PATH`

---

## AI 機能の利用

- ニュース NLP スコアリング
  - 関数: `kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)`
  - DuckDB 接続を渡して実行します。`api_key` が None の場合は環境変数 `OPENAI_API_KEY` を参照します。
  - 書き込み先テーブル: `ai_scores`（DuckDB）

- 市場レジーム判定
  - 関数: `kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)`

注意: OpenAI API を使うため、API キーとネットワーク環境が必要です。API 呼び出しは再試行ロジックとフォールバック（API 失敗時のセーフ挙動）を持ちますが、使用にはコストがかかります。

---

## ログ / ファイル配置・運用上のフラグ

- ログ
  - デフォルトは `logs/` ディレクトリ（`kabusys.utils.logging_setup.setup_logging` により作成）
  - 各アプリ名ごとに `logs/<app_name>.log`（例: `logs/execution.log`, `logs/monitoring.log`）
  - ローテーション: 日次、30世代保持

- データ / 制御ファイル（デフォルト）
  - DB: `data/kabusys.duckdb`, `data/monitoring.db`, `data/paper_trading.db`
  - PID: `data/execution.pid`
  - 停止フラグ: `data/stop_requested.flag`（run_* スクリプトはこのファイルを見て停止）
  - Kill Switch: `data/kill.flag`（KillSwitch が書き込み、ExecutionEngine を停止させるトリガー）
  - これらのパスは Settings で上書き可能（環境変数で指定）

---

## 開発者向け・モジュール呼び出し例

Python から直接モジュールを使うこともできます。簡単な例:

- DuckDB 接続とモメンタム計算
```python
import duckdb
from datetime import date
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
result = calc_momentum(conn, date(2026, 4, 1))
```

- ニューススコア付与（AI）
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
count = score_news(conn, date(2026,4,1), api_key="sk-...")
```

---

## トラブルシューティング / 注意点

- .env の自動読み込み
  - `kabusys.config` はプロジェクトルート（.git または pyproject.toml を基準）を自動検出し `.env` / `.env.local` をロードします。自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- データベースのマイグレーション
  - `init_monitoring_db()` は存在しないテーブル・カラムを作成する簡単なマイグレーションを行います（冪等）。既存の DB にカラムがない場合に追加します。

- プロセス優先度設定
  - 起動スクリプトは起動時に `set_process_priority("high")` を呼びますが、権限によっては設定に失敗することがあります（警告ログ）。Linux/Windowsで差分を吸収する実装です。

- モニタリングは本番 sqlite_path を参照します
  - `run_monitoring.py` は KABUSYS_ENV にかかわらず本番の `sqlite_path` を使用する設計です。モニタリング DB と発注 DB が分離されている環境では注意してください。

---

## ディレクトリ構成（抜粋）

以下は主要ファイル / ディレクトリの構成（src/kabusys を基準）です。現物のツリーと差分がある場合がありますが、概観は次の通りです。

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / Settings
  - config_setup.py              — .env 対話ウィザード
  - validate_config.py           — 起動前設定検証 CLI
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py  (概念上の存在; 実装がここにある場合に利用)
  - utils/
    - logging_setup.py
    - process_priority.py
  - execution/                    — 発注関連のサブパッケージ（OrderManager 等）

プロジェクトルートには想定される補助ファイル:
- .env (ユーザー作成)
- data/ (DB・PID・flag 等を置くディレクトリ)
- logs/ (ログファイル)
- config/ (各種 YAML テンプレート: system_config.yaml, ...)

---

## 最後に

- .env の必須項目（特に API_KEY 等）を正しく設定し、`python -m kabusys.validate_config` で検証してください。  
- 本番運用時は KABUSYS_ENV=live の設定に細心の注意を払い、kill flag / 自動クリア設定などを確認してください。  
- AI 機能を使用する場合は OpenAI のコストと rate limit を考慮してください。

質問や README の補足を希望する箇所があれば教えてください。必要に応じて起動例や .env のテンプレートをさらに詳しく提供します。