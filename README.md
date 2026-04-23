# KabuSys

日本株向けの自動売買・リサーチ基盤（参考実装）。  
本リポジトリはトレード実行エンジン、監視（Monitoring）、ポートフォリオ構築、リサーチ、LLMを使ったニュース解析などを含むモジュール群で構成されています。

---

## 概要

KabuSys は以下のような責務を持つコンポーネント群をまとめたシンプルな自動売買基盤です。

- ExecutionEngine：発注・約定管理・リスク管理を担う実行エンジン
- Monitoring：システム状態・注文状態・リスク指標の定期チェックとアラート発行、Kill Switch
- Portfolio：銘柄選定、配分・株数計算、セクター制限などのポートフォリオ構築ロジック（純粋関数）
- Research：DuckDB を用いたファクター計算・特徴量解析
- AI モジュール：OpenAI を使ったニュースのセンチメント解析 / レジーム判定
- ツール：Paper Trading の検証レポート生成等のユーティリティ

設計方針として、本番DBとペーパートレードDBの分離、フェイルセーフ（API障害やデータ欠損時の安全なフォールバック）、ローカルでの再現性を重視しています。

---

## 主な機能一覧

- 実行環境を切り替え可能（development / paper_trading / live）
- ペーパートレード時は MockBroker を使い専用 SQLite DB（data/paper_trading.db）に記録
- Monitoring：
  - CPU / メモリ / ディスク / プロセス稼働検出
  - データ鮮度チェック（DuckDBのprices_dailyなど）
  - リスク監視（ドローダウン、ポジション上限）
  - Kill Switch（条件に達したら data/kill.flag を作成）
  - ログ・監視テーブルの永続化（SQLite）
- Portfolio モジュール：
  - 候補選定、等配分・スコア加重の重み算出
  - セクターキャップ適用、レジームによる投下資金乗数
  - ポジションサイズの算出（lot丸め、aggregate cap、コストバッファ）
- Research：
  - モメンタム / ボラティリティ / バリューのファクター計算（DuckDB）
  - 将来リターン計算、IC計算、ファクター統計
- AI：
  - ニュースを LLM でスコアリングし ai_scores テーブルへ反映
  - マクロニュース + ETF MA200 を用いた市場レジーム判定
- ユーティリティ：
  - .env 対話式セットアップウィザード
  - 設定検証 CLI
  - Paper Trading 検証レポート生成スクリプト
  - 統一的なログ設定（stdout + 日次ローテートファイル）
  - プロセス優先度 / CPU affinity 設定ユーティリティ

---

## セットアップ手順

前提：
- Python 3.10+（型注釈に | を使っているため 3.10 以上推奨）
- DuckDB（Python パッケージ）、psutil、openai 等を使用

1. リポジトリをクローン・移動
   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境作成・有効化（任意）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール
   必要な主なパッケージ：
   - duckdb
   - psutil
   - openai
   - PyYAML（config ファイル検証を行う場合）
   例：
   ```bash
   pip install duckdb psutil openai PyYAML
   ```

4. .env の初期作成（対話式ウィザード）
   ```bash
   python -m kabusys.config_setup
   ```
   ウィザードは .env を生成します。必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD。必要に応じて OPENAI_API_KEY を環境変数で設定してください。

5. 設定検証
   ```bash
   python -m kabusys.validate_config
   # 警告もエラー扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

6. データディレクトリを確認
   デフォルトでは data/ に DB やフラグファイルを置きます。必要であれば .env の DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH を編集してください。

---

## 使い方

各種コンポーネントはモジュールとして起動できます。プロジェクトルートで実行してください。

- 実行エンジン（ExecutionEngine）起動
  - 本番 / ペーパーの分岐は KABUSYS_ENV で制御。paper_trading の場合、ペーパートレード用 DB に記録します。
  ```bash
  # 例: 開発環境（発注なし）
  KABUSYS_ENV=development python -m kabusys.run_execution

  # 例: ペーパートレード
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  ```

  停止方法: data/stop_requested.flag ファイルを作成すると実行スレッドは停止処理を開始します（run_execution/run_monitoring とも共通）。

- 監視ループ（Monitoring）起動
  ```bash
  # ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で変更可能（デフォルト60秒）
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

  備考: monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使用する設計です（監視ログの永続化先は共通にする）。

- .env ウィザード（再実行）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート生成
  ```bash
  # デフォルト: data/paper_trading.db
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DBパス指定:
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- AI スコアリング / レジーム判定（プログラムから呼び出す）
  - news_nlp.score_news(conn, target_date, api_key=None)
  - regime_detector.score_regime(conn, target_date, api_key=None)
  どちらも OpenAI API キーを引数で渡すか環境変数 OPENAI_API_KEY を設定してください。CLI ラッパーは用意されていないため、スクリプトやジョブから呼び出します。

ログ:
- デフォルトは logs/ ディレクトリにアプリごとのログを日次ローテートで保存します（logs/execution.log, logs/monitoring.log 等）。
- コンソール出力は stdout に出ます。ログレベルは LOG_LEVEL（.env）で調整できます。

停止・Kill Switch:
- Monitoring の KillSwitch がトリガーすると data/kill.flag を書き込みます。ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START によって自動クリアする設定が可能（ただし本番では 0 推奨）。

環境変数（主要なもの）:
- KABUSYS_ENV: development | paper_trading | live（既定: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール必要時）
- DUCKDB_PATH: DuckDB ファイルパス（既定: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（既定: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（既定: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、既定: 60）

---

## ディレクトリ構成（主要ファイル）

以下は主要ファイル／パッケージの抜粋です。実際のツリーは src/kabusys 以下にあります。

```
src/kabusys/
├─ __init__.py
├─ config.py                 # 環境変数・設定読み込みロジック（.env 自動ロード等）
├─ config_setup.py          # .env 対話式ウィザード
├─ validate_config.py       # 設定検証 CLI
├─ run_execution.py         # ExecutionEngine 起動スクリプト
├─ run_monitoring.py        # Monitoring 起動スクリプト

├─ utils/
│  ├─ __init__.py
│  ├─ logging_setup.py      # 統一的なロギング設定
│  ├─ process_priority.py   # プロセス優先度 & CPU affinity
│
├─ monitoring/
│  ├─ monitoring_db.py      # SQLite による監視ログ永続化層
│  ├─ system_monitor.py     # システム状態・データ鮮度監視
│  ├─ trade_monitor.py      # (注文関連の監視) ※ファイルあり
│  ├─ risk_monitor.py       # ドローダウン・ポジション上限監視
│  ├─ kill_switch.py        # Kill switch 制御
│  ├─ alert_manager.py      # (通知管理) ※ファイルあり
│  ├─ monitoring_engine.py  # 各 Monitor を束ねるエンジン
│
├─ execution/
│  ├─ execution_engine.py   # 実行エンジン本体（EngineConfig, run_session 等）
│  ├─ broker_factory.py     # ブローカークライアント生成（Mock含む）
│  ├─ order_manager.py
│  ├─ order_repository.py
│  ├─ reconciler.py
│  ├─ risk_manager.py
│
├─ portfolio/
│  ├─ portfolio_builder.py  # 候補選定・重み計算
│  ├─ position_sizing.py    # 株数決定
│  ├─ risk_adjustment.py    # セクター上限・レジーム乗数
│
├─ research/
│  ├─ factor_research.py    # モメンタム/ボラティリティ/バリュー算出
│  ├─ feature_exploration.py# 将来リターン/IC/統計
│
├─ ai/
│  ├─ news_nlp.py           # ニュースを LLM でスコアリング
│  ├─ regime_detector.py    # レジーム判定（MA200 + LLM）
│
├─ tools/
│  ├─ __init__.py
│  ├─ paper_verification_report.py  # Paper Trading 検証レポート生成
```

（※ 上記は抜粋です。実際のファイル全体は src/kabusys 以下をご参照ください）

---

## 開発上の注意点 / 実運用での留意点

- 本番稼働時は KABUSYS_ENV=live を慎重に設定してください。validate_config は live 時の安全チェック（LINE設定、kill flag設定等）も行います。
- ペーパートレード DB は本番 DB と分離しています（設定により変更可能）。Monitoring は設計上 production sqlite_path を参照するため、監視と実行の DB 統合については設定と運用方針を明確にしてください。
- OpenAI 呼び出しは API 失敗時にフェイルセーフでスキップ/デフォルト値を採る設計ですが、APIキーの管理やレート制限には注意してください。
- ログディレクトリの作成に失敗した場合はコンソール出力のみで継続します。運用環境では logs/ の権限とディスク容量を確保してください。
- process priority / CPU affinity の設定はプラットフォーム依存の制約（権限など）により失敗する場合があります。警告ログで通知されます。

---

## 追加情報 / 参考

- README はプロジェクトの概要と運用に必要な最低限の情報をまとめたものです。各モジュール（monitoring/*.py、execution/*.py、ai/*.py、research/*.py）内に詳細な docstring と設計コメントがあるため、実装を読みながら理解を深めてください。
- 問題や改善案があればイシューを作成してください。

---

必要であれば、この README を英語版に翻訳したり、さらに詳細な運用手順（systemd / cron / Kubernetes 用の起動例、ログローテーション設定、バックアップ方針など）を追記できます。どの部分を拡張しますか？