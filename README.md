# KabuSys

日本株向けの自動売買システム（ライブラリ兼実行スクリプト群）。  
シグナル生成・ポートフォリオ構築・発注実行・監視・リスク管理・調査用ユーティリティを含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の機能を持つモジュール群から構成される自動売買基盤です。

- DuckDB / SQLite を用いたデータ分析・ログ永続化
- ファクター計算（モメンタム / バリュー / ボラティリティ等）
- ポートフォリオ構築（銘柄選定・重み計算・株数決定）
- ExecutionEngine（ブローカークライアント経由での発注管理、paper_trading モードでのモック動作）
- 監視（SystemMonitor / TradeMonitor / RiskMonitor）、Kill Switch による安全停止
- AI ユーティリティ（ニュースセンチメント評価、レジーム判定） — OpenAI API 使用
- 運用支援ツール（.env ウィザード / 設定検証 / Paper Trading 検証レポート生成）

設計方針の一例:
- 実行環境ごとに DB 分離（paper_trading は専用 SQLite）
- 監視は production の sqlite_path を参照（実運用向け）
- ルックアヘッドバイアス対策（日時の取り扱い設計に注意）

---

## 主な機能一覧

- execution/
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - ブローカー抽象化（MockBrokerClient / 実ブローカーのファクトリ）
  - 注文管理・リコンシリエーション・リスクチェック
- monitoring/
  - SystemMonitor（プロセス・CPU/メモリ/ディスク・データ鮮度）
  - TradeMonitor（滞留注文 / 価格異常検知 等）
  - RiskMonitor（ドローダウン・ポジション上限監視）
  - KillSwitch（フラグファイルにより ExecutionEngine を停止）
  - MonitoringEngine（複数モニタの統合・アラート発行）
- portfolio/
  - 銘柄選定・重み算出・株数決定・セクター制約・レジーム乗数
- research/
  - ファクター計算（momentum / value / volatility）
  - 特徴量探索（forward returns, IC, summary）
- ai/
  - news_nlp: ニュースから銘柄毎にセンチメントを算出し ai_scores に書き込む（OpenAI）
  - regime_detector: ETF とマクロニュースを合成して market_regime を算出（OpenAI）
- utils/
  - ロギング設定（ファイルローテーション含む）
  - プロセス優先度 / CPU affinity 設定
- tools/
  - paper_verification_report: Paper Trading 検証レポート生成 CLI

---

## 要件（例）

- Python 3.9+（型ヒントの Union 表記などを利用）
- 主要 Python パッケージ（例）
  - duckdb
  - psutil
  - openai（AI 機能を使用する場合）
  - PyYAML（設定検証で YAML ファイル検証を行いたい場合）
- SQLite（標準ライブラリに含まれます）
- ネットワーク接続（kabuステーション API / OpenAI 等を使用する場合）

requirements.txt は本リポジトリに含まれていないため、必要に応じて以下をインストールしてください（例）:

```
pip install duckdb psutil openai pyyaml
```

（AI 機能を使わない場合は `openai` は不要）

---

## 初期セットアップ

1. リポジトリルートで Python 仮想環境を作成・有効化（任意）:

   ```
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```

2. 依存パッケージをインストール:

   ```
   pip install -r requirements.txt    # 存在する場合
   # または最低限:
   pip install duckdb psutil
   ```

3. .env を作成（対話式ウィザード推奨）:

   ```
   python -m kabusys.config_setup
   ```

   - ウィザードは J-Quants トークン、kabu API パスワード、DB パス、KABUSYS_ENV 等を設定します。
   - 生成した .env は絶対に Git にコミットしないでください。

4. 設定検証:

   ```
   python -m kabusys.validate_config
   # 警告も厳密に FAIL にしたい場合:
   python -m kabusys.validate_config --strict
   ```

---

## 主要な環境変数（抜粋）

- KABUSYS_ENV: 実行環境。`development` | `paper_trading` | `live`（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: （必須）J-Quants API 用トークン
- KABU_API_PASSWORD: （必須）kabuステーション API パスワード
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- OPENAI_API_KEY: OpenAI API キー（ai モジュール使用時）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: Paper Trading の約定モード（instant|partial|never|reject）

自動読み込み:
- プロジェクトルートにある `.env` と `.env.local` が自動読み込みされます（OS 環境変数を上書きしない挙動）。自動ロードを抑制する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 使い方

### 実行エンジン (ExecutionEngine) 起動

- Paper trading と live（本番）で DB が分離されるため、環境変数 `KABUSYS_ENV` を設定してください。

起動例（標準）:

```
python -m kabusys.run_execution
```

- KABUSYS_ENV=paper_trading の場合は MockBrokerClient が使われ、デフォルトで `data/paper_trading.db` に記録されます。
- 起動時に `data/stop_requested.flag` が存在すると起動をスキップします。
- 実行中は `data/execution.pid` が使用されます。

停止:
- `data/stop_requested.flag` を作成すると監視スクリプトや Engine が検知し終了します。
- KillSwitch による停止は `data/kill.flag` に理由を書き込むことで発動します（監視コンポーネントが判定して書き込みます）。

### 監視 (Monitoring) 起動

```
python -m kabusys.run_monitoring
```

- 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書きできます（秒、デフォルト 60）。
- Monitoring は常に production の sqlite_path を使用して監視ログを記録します。
- 停止フラグ: `data/stop_requested.flag` を作ると監視ループが終了します。

### 設定検証

```
python -m kabusys.validate_config
python -m kabusys.validate_config --strict
```

- `.env` の必須項目や config/*.yaml の存在等をチェックします。PyYAML がない場合は YAML 検証がスキップされます。

### .env 対話式ウィザード

```
python -m kabusys.config_setup
```

### Paper Trading 検証レポート生成

```
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# DB 指定:
python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
```

- 注文成功率、送信率、稼働率、P95 レイテンシなどを集計し PASS/FAIL を判定します。

### AI モジュール（ニュース NLP / レジーム判定）

- これらは OpenAI API を使用します。`OPENAI_API_KEY` を設定してください。
- プログラム内から呼び出す API:

  - ニュースセンチメント: `kabusys.ai.score_news(conn, target_date, api_key=None)`
  - レジーム判定: `kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)`

  例（Python REPL から）:

  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  conn = duckdb.connect("data/kabusys.duckdb")
  score_news(conn, date(2026, 4, 1), api_key="sk-...")
  ```

- AI 呼び出しはネットワークエラー・制限等に対してリトライ実装がありますが、API キー・料金管理は運用側で注意してください。

---

## ログ

- デフォルトのログディレクトリ: `logs/`
- ログファイル名は起動アプリ名（例: `execution.log`, `monitoring.log`）。日次ローテーション（30日保持）。
- ログ設定は `kabusys.utils.logging_setup.setup_logging` で一元管理されます。

---

## 監視・停止フロー (概略)

- SystemMonitor / TradeMonitor / RiskMonitor が定期実行され、MonitoringDB（SQLite）へ記録。
- RiskMonitor でドローダウンやポジション上限が検出されると risk_logs を追記し、KillSwitch が `data/kill.flag` を書き込みうる。
- ExecutionEngine は起動時に `kill_flag_clear_on_start` を確認し、必要に応じて kill.flag をクリアできます（環境変数 KILL_FLAG_CLEAR_ON_START=1）。

---

## ディレクトリ構成（主要部分）

```
src/
  kabusys/
    __init__.py
    config.py
    config_setup.py
    validate_config.py
    run_execution.py
    run_monitoring.py
    utils/
      logging_setup.py
      process_priority.py
    portfolio/
      portfolio_builder.py
      position_sizing.py
      risk_adjustment.py
    research/
      factor_research.py
      feature_exploration.py
    ai/
      news_nlp.py
      regime_detector.py
      __init__.py
    monitoring/
      monitoring_db.py
      system_monitor.py
      trade_monitor.py
      risk_monitor.py
      monitoring_engine.py
      kill_switch.py
    execution/        # ブローカー・エンジン等（参照のみ）
    tools/
      paper_verification_report.py
    data/             # 実行時に使うデータファイル (logs, sqlite, duckdb 等)
```

（実際のリポジトリにはさらにサブモジュールや補助ファイルがあります）

---

## 開発・運用上の注意

- .env にシークレット情報を含めるため、絶対にバージョン管理に含めないでください。
- 本番（KABUSYS_ENV=live）では `KILL_FLAG_CLEAR_ON_START=0` を推奨します。validate_config は live 用の追加警告を出します。
- DuckDB/SQLite のパスはデフォルトで `data/` 配下にあります。バックアップやアクセス権に注意してください。
- AI 機能を使う際は API 使用料・応答の妥当性に注意し、レスポンスのバリデーション実装を尊重してください（既にコード内で多くの検査とクリップが行われます）。

---

## 参考コマンドまとめ

- .env 作成（ウィザード）:
  ```
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- Execution 起動:
  ```
  python -m kabusys.run_execution
  ```

- Monitoring 起動:
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

- Paper Trading レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

README はここまでです。必要であれば以下を追加できます:
- さらに詳しい設定項目リスト（全環境変数）
- Systemd / Docker でのデプロイ例
- CI / テストの実行方法
どれを追加したいか教えてください。