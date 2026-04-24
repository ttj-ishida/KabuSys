# KabuSys

日本株向け自動売買システムのコアライブラリおよび起動スクリプト群です。  
このリポジトリは取引エンジン（Execution）、監視（Monitoring）、ファクター研究・ポートフォリオ構築、AI を使ったニューススコアリングなど、運用に必要な主要コンポーネントを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の主要機能を備えるモジュール群で構成されています。

- 実行エンジン（ExecutionEngine）: 発注フロー、オーダー管理、リスク管理、リコンサイル等を統合して実際の発注/テスト運用を行う。
- 監視（Monitoring）: システム稼働状況、注文滞留、ドローダウンやポジション上限の監視、Kill Switch（停止フラグ）発動等。
- ポートフォリオ構築: 銘柄選定、重み計算、ポジションサイズ決定、セクター制約・レジーム補正。
- リサーチ（Research）: ファクター計算（Momentum / Volatility / Value 等）、特徴量探索、IC 計算。
- AI モジュール: ニュース記事のセンチメントスコアリング（OpenAI）、市場レジーム判定（MA200 + マクロセンチメント）。
- ユーティリティ: ログ設定、プロセス優先度設定、設定ウィザード・検証ツール、Paper Trading 検証レポート出力など。

---

## 機能一覧（抜粋）

- run_execution.py: ExecutionEngine を起動（KABUSYS_ENV により paper_trading モードで MockBroker を使用）
- run_monitoring.py: SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL で間隔変更可）
- config_setup.py: 対話式 .env 生成ウィザード
- validate_config.py: 環境変数・config/*.yaml の事前検証 CLI
- tools/paper_verification_report.py: Paper Trading の検証レポート生成
- monitoring/*: MonitoringDB、SystemMonitor、TradeMonitor、RiskMonitor、KillSwitch、MonitoringEngine、アラート連携
- portfolio/*: 銘柄選定、重み計算、ポジションサイズ計算、セクター制約・レジーム乗数
- research/*: ファクター計算、将来リターン、IC、統計サマリー
- ai/*: ニュース NLP スコアリング、regime_detector（市場レジーム判定）
- utils/*: logging_setup（統一ログ設定）、process_priority（優先度 / CPU affinity）

---

## 必須 / 推奨依存ライブラリ

（環境に合わせて適宜インストールしてください）

必須（実行に必要な主なパッケージ）
- duckdb
- psutil
- openai (AI モジュールを使用する場合)
- sqlite3（標準ライブラリ）

推奨 / オプション
- PyYAML（validate_config が YAML 検証を行う際に使用）
- その他、運用に合わせたブローカークライアント実装など

例（pip を使ったインストール）:
```bash
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリをクローンしてワークディレクトリに移動
   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. Python と依存パッケージをインストール
   ```bash
   python -m pip install --upgrade pip
   pip install duckdb psutil openai PyYAML
   ```

3. 環境変数（.env）の作成
   - 対話式ウィザードを使う:
     ```bash
     python -m kabusys.config_setup
     ```
     ウィザードは .env（デフォルト）を生成/更新します。生成後は `.env` を絶対に Git にコミットしないでください。

   - または手動で .env を作成:
     必須（例）
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_token
     KABU_API_PASSWORD=your_kabu_password
     ```
     推奨設定:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading モード用）
     - LOG_LEVEL: INFO
     - OPENAI_API_KEY: （AI 機能を使う場合）

4. 設定検証（任意だが推奨）
   ```bash
   python -m kabusys.validate_config
   # 警告も失敗扱いにしたい場合:
   python -m kabusys.validate_config --strict
   ```

5. 初期データディレクトリの作成（必要に応じて）
   - `data/`（DB・pid・フラグファイル置き場）
   - `logs/`（ログ出力先）  
   ただしログ・DB は起動時に自動作成されることが多いです。

---

## 使い方（起動・操作）

### 実行エンジン（ExecutionEngine）起動
- Paper trading（仮想発注）:
  - KABUSYS_ENV を `paper_trading` に設定（.env で指定または環境変数で上書き）
  - Paper Trading 用 DB は `PAPER_TRADING_SQLITE_PATH`（デフォルト: data/paper_trading.db）に分離されます。
- Live（実発注）:
  - KABUSYS_ENV を `live` に設定
  - 実際のブローカー接続設定（kabuステーション等）を確認してください。

起動コマンド:
```bash
python -m kabusys.run_execution
```

- 実行起動時に `data/stop_requested.flag` が存在すると起動を中止します。
- エンジンは `data/execution.pid` を pid ファイルとして扱います。
- プロセス優先度は起動時に "high" に設定されます（プラットフォーム依存で失敗する場合は警告のみ）。

### 監視（Monitoring）起動
起動コマンド:
```bash
python -m kabusys.run_monitoring
```

- デフォルトで 60 秒間隔のポーリングを行います。環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可。
- 監視は Settings.sqlite_path（デフォルト data/monitoring.db）を使用します（run_monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を参照します）。
- 停止は `data/stop_requested.flag` を作成することで行います（ファイル検知でループ終了）。

### Kill Switch
- RiskMonitor と MonitoringEngine の評価により、KillSwitch が `data/kill.flag` を書き込むと ExecutionEngine に停止シグナルを送る設計です。
- ExecutionEngine は起動時の `KILL_FLAG_CLEAR_ON_START` 設定（.env）により kill.flag の自動クリア可否を制御します（本番では 0 推奨）。

### AI 関連（ニューススコア・レジーム判定）
- OpenAI API を使用するため `OPENAI_API_KEY`（または api_key 引数）の設定が必要です。
- ニューススコア（ai.news_nlp.score_news）やレジーム判定（ai.regime_detector.score_regime）は DuckDB 接続を受け取り、DB のテーブル（raw_news, news_symbols, ai_scores, prices_daily 等）を参照して処理します。
- 直接実行可能な CLI スクリプトは含まれていませんが、Python スクリプトやジョブとして呼び出して利用します。

例（簡易的に呼ぶ例）:
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
score_news(conn, target_date=date(2026, 4, 10), api_key="sk-...")
```

### Paper Trading 検証レポート
Paper Trading 用 SQLite（デフォルト data/paper_trading.db）を対象にレポートを生成できます:
```bash
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# または DB を直接指定
python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
```

---

## 環境変数（主要なもの）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live (デフォルト: development)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (監視 DB; デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB; デフォルト: data/paper_trading.db)
- LOG_LEVEL (デフォルト: INFO)
- OPENAI_API_KEY (AI 機能を使う場合)
- MONITOR_POLL_INTERVAL (run_monitoring の秒間隔; デフォルト: 60)
- PAPER_FILL_MODE (paper_trading の MockBroker fill モード: instant|partial|never|reject)

補足:
- 自動環境ロード: ルートに `.env` があれば自動で読み込まれます（ただし OS 環境変数が優先）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
- .env.local は .env の上書きとして読み込まれます（OS 環境変数は保護される）。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数 / Settings 管理
  - config_setup.py         — .env 対話式ウィザード
  - validate_config.py      — 設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート
  - ai/
    - news_nlp.py           — ニュースを LLM でスコアリング
    - regime_detector.py    — 市場レジーム判定（MA200 + マクロ）
  - portfolio/
    - portfolio_builder.py  — 候補選定・重み計算
    - position_sizing.py    — 発注株数算出
    - risk_adjustment.py    — セクター上限・レジーム乗数
  - research/
    - factor_research.py    — Momentum/Value/Volatility 等のファクター
    - feature_exploration.py— 将来リターン / IC / 統計
  - monitoring/
    - monitoring_db.py      — SQLite 永続化層（監視ログ）
    - system_monitor.py     — システム状態・データ鮮度監視
    - trade_monitor.py      — （注文）トレード監視（該当ファイルの実装に依存）
    - risk_monitor.py       — ドローダウン・ポジション上限監視
    - kill_switch.py        — kill.flag の管理
    - monitoring_engine.py  — 各 Monitor を束ねる
    - alert_manager.py      — （アラート送信の抽象）
  - execution/
    - execution_engine.py   — ExecutionEngine, EngineConfig
    - broker_factory.py     — Broker クライアント生成
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - utils/
    - logging_setup.py      — 統一ログ設定
    - process_priority.py   — 優先度 / CPU affinity
  - data/ (運用時に生成)
    - monitoring.db (デフォルト SQLITE_PATH)
    - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
    - kill.flag / stop_requested.flag / execution.pid

---

## 運用上の注意点

- .env は機密情報を含むため絶対にリポジトリにコミットしないでください。
- 本番（KABUSYS_ENV=live）では kill.flag の自動クリア（KILL_FLAG_CLEAR_ON_START=1）は有効にしないでください（安全上の理由で 0 を推奨）。
- run_monitoring は常に Settings.sqlite_path（監視 DB）を使います。監視 DB と発注（paper_trading）DB は用途によって明示的に分離されています。
- OpenAI 利用は API コストとレート制限に注意してください。AI モジュールはリトライ・フォールバックの実装がありますが、運用ポリシーを検討してください。
- ログは `logs/<app_name>.log` に日次ローテーションで保存されます（logs ディレクトリを作成できない場合はコンソールのみ）。

---

## 開発 / テストヒント

- validate_config.py により起動前に必須環境変数や config ファイルの欠落を検出できます。CI に組み込むと安全です。
- MonitoringEngine は単発実行用の `run_once()` メソッドがあり、ユニットテストで個別監視ロジックを検証しやすくなっています。
- AI / OpenAI 呼び出し部分は内部で関数を切り出しているため、ユニットテスト時は該当呼び出しをモックすることでテストが容易です（例: unittest.mock.patch）。

---

必要であれば、README に運用例（systemd ユニット、Dockerfile、cron などでの起動方法）、より詳細な設定項目一覧、各モジュールの API 使用例などを追加で作成します。どの情報がさらに欲しいか教えてください。