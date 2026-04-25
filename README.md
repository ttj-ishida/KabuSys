# KabuSys

日本株自動売買システムの軽量ライブラリ群と起動スクリプト群。  
ポートフォリオ構築、ポジションサイジング、モニタリング、ペーパートレード検証、LLM を用いたニュースセンチメント評価などの機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買に関わる主要コンポーネントをモジュール化したコードベースです。主な設計方針は以下のとおりです。

- 戦略・ポートフォリオ構築ロジックは純粋関数（副作用なし）で実装
- 実行（ExecutionEngine）と監視（MonitoringEngine）は独立した起動スクリプトで運用
- Paper Trading（シミュレーション）と Live（実運用）を環境変数で切り替え
- DuckDB/SQLite を用いたデータ保管・解析
- OpenAI（gpt-4o-mini）を用いたニュース NLP / レジーム判定（必要に応じて）

---

## 主な機能一覧

- Execution
  - 実際の発注処理の起動スクリプト（run_execution）
  - Paper Trading 用に MockBroker を選択可能（DBは data/paper_trading.db に分離）
  - リスク管理（RiskManager）、オーダー管理、照合（Reconciler）などの組み立て
- Monitoring
  - System / Trade / Risk の監視コンポーネント（SystemMonitor, TradeMonitor, RiskMonitor）
  - Kill Switch（異常時に flag ファイルを書き ExecutionEngine を停止）
  - run_monitoring によるポーリングループ起動（MONITOR_POLL_INTERVAL で間隔指定）
- Portfolio construction
  - 候補選定、等重/スコア重み、ポジションサイズ計算、セクター制限、レジーム乗数
- Research
  - ファクター計算（Momentum/Value/Volatility 等）、将来リターン計算、IC（Information Coefficient）など
  - DuckDB を使った純粋なデータ処理
- AI（OpenAI）
  - news_nlp: ニュース記事の銘柄ごとのセンチメント評価（ai_scores テーブルへ書込）
  - regime_detector: マクロニュース + ETF MA 乖離で市場レジーム判定（market_regime への書込）
- ユーティリティ
  - ログ設定（logs/ 日次ローテーション）
  - プロセス優先度／CPU affinity 設定
  - .env 対話式ウィザード（config_setup）と設定検証ツール（validate_config）
- ツール
  - paper_verification_report: Paper Trading の実行ログから検証レポートを生成

---

## セットアップ手順

前提
- Python 3.9+ を推奨（コードは型ヒントに依存）
- システムに duckdb のビルド要件が整っていること（多くの環境では wheel が利用可）

例: 仮想環境作成と依存インストール
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb openai psutil
# 任意: PyYAML（validate_config の YAML 検証用）
pip install PyYAML
```

（プロジェクトに requirements.txt を用意する場合はそれを使ってください）

ディレクトリ作成
```bash
mkdir -p data logs
```

.env の作成（対話ウィザード）
```bash
python -m kabusys.config_setup
# 生成後に設定の検証
python -m kabusys.validate_config
```

注意:
- 自動で .env を読み込む仕組みがあります（.env / .env.local）。自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- .env は絶対に Git にコミットしないでください（機密情報を含む）。

必須環境変数（最低限）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

その他よく使う環境変数
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視用、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- OPENAI_API_KEY（AI 機能利用時に必要）
- PAPER_FILL_MODE（paper_trading の約定モード: instant | partial | never | reject）
- KILL_FLAG_CLEAR_ON_START（本番で自動クリアしないことを推奨、デフォルト: 0）

---

## 使い方

一般的なワークフローを示します。

1. .env を作成・確認
   - 対話形式で作る:
     ```bash
     python -m kabusys.config_setup
     ```
   - 設定検証:
     ```bash
     python -m kabusys.validate_config
     # --strict を付与すると警告も FAIL 扱い
     python -m kabusys.validate_config --strict
     ```

2. モニタリング起動（常駐）
   - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を調整（デフォルト 60）
   - 実行:
     ```bash
     python -m kabusys.run_monitoring
     ```
   - 監視は常に本番用の sqlite_path（Settings.sqlite_path）を使います（環境にかかわらず）。

3. 実行エンジン起動（ExecutionEngine）
   - Paper Trading モード:
     ```bash
     export KABUSYS_ENV=paper_trading
     python -m kabusys.run_execution
     ```
     → PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）にログが記録され、本番 DB と分離されます。
   - Live モード:
     ```bash
     export KABUSYS_ENV=live
     python -m kabusys.run_execution
     ```
   - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
   - 実行中に stop_requested.flag が作成されるとエンジンを停止します。
   - PID ファイル: data/execution.pid（設定により変更可）

4. Paper Trading 検証レポート生成
   - DB パスを指定して検証レポートを作る:
     ```bash
     python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db
     ```

5. AI 機能（ニュース NLP / レジーム判定）
   - OpenAI API キーが必要（OPENAI_API_KEY または api_key 引数）
   - ニューススコア (news_nlp.score_news) や regime_detector.score_regime をスクリプト・ジョブから呼び出して ai_scores / market_regime を更新できます。
   - 使用モデル: gpt-4o-mini（コード内で固定）

ログ
- ログはデフォルトで logs/<app_name>.log に日次ローテーションで保存されます（30日分保持）。
- コンソールは stdout に出力されます。

停止制御
- 実行を停止したい場合は data/stop_requested.flag を作成すると run_execution と run_monitoring のループが検知して終了します。
- Kill Switch（自動停止判定）は data/kill.flag を書き込みます。kill.flag が存在する場合、ExecutionEngine は起動しないか停止されます。Kill Switch の評価は MonitoringEngine が行います。

環境のクリア
- kill.flag を手動でクリア:
  ```bash
  rm -f data/kill.flag
  ```

環境変数による細かい挙動
- KILL_FLAG_CLEAR_ON_START=1 を設定すると ExecutionEngine 起動時に kill.flag を自動で削除します（本番では推奨されません）。
- MONITOR_POLL_INTERVAL: 監視ループの間隔（秒）

---

## ディレクトリ構成（要点）

以下は src/kabusys 以下の主要ファイル・ディレクトリの抜粋です。

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理（.env 自動ロードロジック含む）
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 起動前の設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリングループ起動スクリプト
  - utils/
    - logging_setup.py        — ログ初期化ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity ユーティリティ
  - execution/                — 実行エンジン周辺（BrokerFactory, Engine, OrderManager 等）
  - monitoring/
    - monitoring_db.py        — SQLite テーブル初期化・永続化レイヤ
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py             — ニュースセンチメント評価（OpenAI）
    - regime_detector.py      — 市場レジーム判定（MA + マクロニュース）
  - tools/
    - paper_verification_report.py

プロジェクトルートに次のようなファイル／ディレクトリが想定されます:
- .env (環境変数)
- data/ (DBファイル、PID/flag ファイル: monitoring.db, paper_trading.db, kill.flag, stop_requested.flag, execution.pid など)
- logs/ (ログファイル)
- config/ (各種 YAML 設定テンプレート: system_config.yaml 等)

簡易ツリー例:
```
.
├─ src/kabusys/...
├─ config/
├─ data/
│  ├─ monitoring.db
│  ├─ paper_trading.db
│  ├─ kill.flag
│  └─ execution.pid
├─ logs/
└─ .env
```

---

## 開発上の注意点 / 補足

- Monitoring 側は常に Settings.sqlite_path（本番監視 DB）を使用します。Execution は KABUSYS_ENV に応じて paper_trading 用 DB を使い分けます（本番 DB と分離）。
- .env 自動ロードはプロジェクトルート（.git または pyproject.toml を探す）を基準に行われます。テスト時に自動ロードを抑制したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI を使う機能は API 呼び出しに依存するため、APIキーの有無や呼び出し失敗時のフェイルセーフ（スコア 0.0 など）実装に留意しています。API エラーやリトライロジックは各モジュールに実装済みです。
- ログディレクトリの作成に失敗するとファイル出力はスキップされコンソール出力のみになります（setup_logging の挙動）。

---

この README はリポジトリ内コードの主要部分に基づいてまとめています。必要があれば各モジュールの詳細ドキュメント（関数仕様、引数、戻り値、DB スキーマなど）を個別に生成できます。どの部分をさらに詳述しますか？