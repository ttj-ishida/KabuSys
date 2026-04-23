# KabuSys

日本株自動売買システム（KabuSys）の README。  
このリポジトリはアルゴリズム取引のためのコアライブラリ群（データ処理・ファクター計算・ポートフォリオ構築・発注エンジン・監視・AI 補助）を含みます。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買フレームワークです。主な設計方針は以下のとおりです。

- DuckDB / SQLite を用いたオンディスク分析・監視データ管理
- 発注エンジンは実取引（live）とペーパートレード（paper_trading）を切替可能
- 監視コンポーネント（System / Trade / Risk）による自動アラート・Kill Switch
- ファクター計算・特徴量探索・リサーチ用ユーティリティ
- OpenAI を用いたニュースセンチメント評価による AI 補助（任意）
- 設定は .env / config/*.yaml で管理。対話式ウィザード・検証ツールあり

---

## 主な機能一覧

- 設定管理
  - .env の自動ロード / 対話式ウィザード（kabusys.config_setup）
  - 起動前チェック（kabusys.validate_config）
- 実行エンジン
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - 実口座（live）／ペーパートレード（paper_trading）を環境で切替
  - ペーパートレードは MockBrokerClient により本番 DB と分離（data/paper_trading.db）
- 監視
  - System / Trade / Risk の各 Monitor（monitoring パッケージ）
  - Monitoring エンジンのポーリングループ（run_monitoring.py）
  - Kill Switch による自動停止（kill.flag 書込み）
  - 監視ログ永続化（SQLite、monitoring_db.py）
- ポートフォリオ構築
  - 候補選定、重み付け、ポジションサイジング、セクターキャップなど（portfolio パッケージ）
- リサーチ
  - ファクター算出（momentum/value/volatility）、特徴量探索、IC 計算（research パッケージ）
- AI サポート（任意）
  - ニュース NLP によるセンチメントスコア（OpenAI を利用）
  - 市場レジーム判定（regime_detector）
- ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

---

## 前提 / 必要環境

- Python 3.10+
- 推奨パッケージ（例）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML (config YAML の検証を行う場合)
- その他: ネットワークアクセス（kabuステーション、J-Quants、OpenAI などの外部 API を使う場合）

例（venv を作成してから）:

```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

※ 実際の requirements.txt がある場合はそれに従ってください。

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ
2. 仮想環境を作成して依存ライブラリをインストール
3. .env の作成
   - 対話式ウィザードを利用:
     ```
     python -m kabusys.config_setup
     ```
   - もしくはプロジェクトルートに `.env` を手動で作成（.env.example を参照）
4. 設定検証（起動前チェック）:
   ```
   python -m kabusys.validate_config
   ```
   - `--strict` を付けると警告もエラー扱いして exit(1) します
5. 必要ディレクトリの作成（通常は自動作成されますが事前に確認しておくと安全）
   - data/ （SQLite 等の DB を格納）
   - logs/ （ログファイル）
6. （オプション）OpenAI を使う場合は環境変数 `OPENAI_API_KEY` を設定

---

## 環境変数（主なもの）

- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 実行環境指定:
  - KABUSYS_ENV: development | paper_trading | live
    - paper_trading の場合、MockBrokerClient と専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用
- データベース:
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- ログ:
  - LOG_LEVEL（例: INFO）
  - LOG_DIR（省略時は logs/）
- モニタ・制御:
  - MONITOR_POLL_INTERVAL: Monitoring ポーリング間隔（秒、デフォルト 60）
  - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START
- AI:
  - OPENAI_API_KEY
- PAPER_FILL_MODE（ペーパートレードの約定モード）:
  - instant | partial | never | reject（デフォルト: instant）

設定は .env / .env.local / OS 環境変数の順で解決されます（詳細は kabusys.config を参照）。

---

## 使い方（主要コマンド）

- 環境設定ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- ExecutionEngine を起動（実取引 / ペーパートレードは KABUSYS_ENV に依存）
  ```
  python -m kabusys.run_execution
  ```
  - 起動時に既に data/stop_requested.flag が存在すると起動を行いません
  - 実行中は data/execution.pid に PID を書く設計（Engine 側で処理）
  - 停止リクエスト: data/stop_requested.flag を作成するとループが終了します

- Monitoring を起動（ポーリング）
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 MONITOR_POLL_INTERVAL で間隔を秒単位で上書き可能（デフォルト 60）
  - run_monitoring は監視用 sqlite（Settings.sqlite_path）を使用（環境値にかかわらず本番パスを使う設計）
  - 同様に data/stop_requested.flag があれば監視ループを終了します

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - --db オプションまたは環境変数 PAPER_TRADING_SQLITE_PATH で DB を指定

- AI 関連（ニューススコア / レジーム判定）
  - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime を呼び出すか、エンジン内で利用
  - OPENAI_API_KEY を設定する必要あり

---

## 停止・Kill Switch について

- stop_requested.flag（data/stop_requested.flag）
  - 手動で作成すると run_monitoring / run_execution のメインループが検知して安全に終了します
- kill.flag（Settings.kill_flag_path 、デフォルト data/kill.flag）
  - 監視コンポーネント（KillSwitch）が自動的に書き込み、ExecutionEngine に「即時停止」を要求します
  - 本番では KILL_FLAG_CLEAR_ON_START を 0（自動クリアしない）にすることを推奨

---

## ログ

- ログは標準出力（stdout）と日次ローテーションされるファイル（logs/<app_name>.log）に出力されます
- ログの設定は kabusys.utils.logging_setup.setup_logging で統一管理
- デフォルトでは 30 日分を保持

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理、.env 自動ロード
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 起動前チェック CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - ai/
    - news_nlp.py             — ニュースセンチメント（OpenAI 利用）
    - regime_detector.py      — 市場レジーム判定（AI + ETF MA）
  - monitoring/
    - monitoring_db.py        — 監視用 SQLite 永続化層
    - system_monitor.py       — システム状態・データ鮮度監視
    - trade_monitor.py        — 発注/約定監視（存在）
    - risk_monitor.py         — ドローダウン / ポジション上限監視
    - kill_switch.py          — Kill Switch 実装
    - monitoring_engine.py    — モニタを束ねるエンジン
    - alert_manager.py        — 通知管理（LINE など）
  - portfolio/
    - portfolio_builder.py    — 候補選定、重み計算
    - position_sizing.py      — 発注株数計算、ユニット丸め、aggregate cap
    - risk_adjustment.py      — セクターキャップ、レジーム乗数
  - research/
    - factor_research.py      — ファクター計算（momentum/value/volatility）
    - feature_exploration.py  — 将来リターン、IC、統計サマリ
  - utils/
    - logging_setup.py        — ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity
  - execution/                — 発注エンジン周り（Engine, BrokerFactory, OrderManager 等）
  - data/ (実行時に生成されることが多い)
    - monitoring.db
    - paper_trading.db
    - kill.flag
    - stop_requested.flag
    - execution.pid
  - logs/ (ログ出力先。自動で作成される)

---

## 開発・テストのヒント

- settings（kabusys.config.Settings）は .env を自動ロードするため、テスト時は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動読み込みを抑止できます。
- OpenAI 周りはテストで外部呼び出しを避けるために _call_openai_api をパッチ（unittest.mock.patch）して差し替える設計です。
- DuckDB / SQLite に対するクエリはモジュールが受け取る接続オブジェクトに対して行うため、テスト用にインメモリ DB を作って渡せます。

---

## よくある質問（Q&A）

- Q: ペーパートレード時のデータは本番 DB と分離されていますか？  
  A: はい。KABUSYS_ENV=paper_trading の場合、Execution は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用します。監視（monitoring）は本来監視用 DB を使います（設計上 monitoring は本番 sqlite_path を参照します）。

- Q: モニタリングのポーリング間隔を変えたいです。  
  A: 環境変数 MONITOR_POLL_INTERVAL を秒で設定してください（例: export MONITOR_POLL_INTERVAL=30）。不正な値（0以下や非整数）は無視されデフォルト 60 秒を使用します。

---

## 最後に

この README はコードベースの主要な機能・運用方法をまとめたものです。実運用前には必ず `python -m kabusys.validate_config` による検証を行い、KABUSYS_ENV 等の重要な設定を確認してください。

不明点や拡張（例: 銘柄別 lot_size、さらなるリスクルール、外部ブローカ対応）についてはコード内ドキュメント（各モジュールの docstring）を参照してください。