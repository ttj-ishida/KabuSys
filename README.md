# KabuSys

日本株向け自動売買システム（KabuSys）のリポジトリ用 README。  
このドキュメントはコードベースの主要コンポーネント、セットアップ手順、運用時の使い方、ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買・リサーチ・監視を行うツール群です。主な役割は次のとおりです。

- シグナル生成・ポートフォリオ構築（research / portfolio）
- 発注・エンジン（execution）
- 監視・アラート（monitoring）
- Paper Trading 向け検証ツールや AI を使ったニュースセンチメント評価（tools / ai）
- 環境設定ウィザードと設定検証（config_setup, validate_config）

設計方針の例:
- DuckDB を分析用 DB、SQLite を取引ログ・監視ログ用に使用
- Paper Trading は本番 DB から完全に分離（専用 sqlite ファイル）
- LLM（OpenAI）を使った NLP 機能は API キーを環境変数で与える

---

## 機能一覧

主な機能（抜粋）:

- 環境設定
  - 対話式ウィザードで `.env` を生成・更新（kabusys.config_setup）
  - 起動前チェック（必須環境変数や config/*.yaml の存在確認）（kabusys.validate_config）
- 実行エンジン
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - 本番 / ペーパートレードの分離（KABUSYS_ENV）
  - ブローカー抽象化（BrokerClientFactory）
  - リスク管理（RiskManager、Reconciler 等）
- 監視
  - System / Trade / Risk の監視コンポーネント（monitoring）
  - 監視ポーリングループ（run_monitoring.py）
  - Kill Switch（条件を満たしたら data/kill.flag を書き込んで発注エンジンを停止）
  - 監視ログ永続化（SQLite via monitoring_db）
- リサーチ / ポートフォリオ
  - ファクター計算（momentum / value / volatility）
  - ポートフォリオ候補選定・重み計算・ポジションサイズ計算（portfolio モジュール）
- AI / NLP
  - ニュースのセンチメント評価を OpenAI で行い ai_scores に書き込む（ai.news_nlp）
  - マクロニュース＋ETF MA200 乖離で市場レジーム判定（ai.regime_detector）
- ツール
  - Paper Trading 検証レポート生成（tools.paper_verification_report）

---

## 前提（依存ライブラリ）

主な外部依存（例）:
- Python 3.9+
- duckdb
- psutil
- openai（AI 機能を利用する場合）
- PyYAML（設定ファイルの YAML 検証に使用、必須ではない）

例: pip インストール
```
pip install duckdb psutil openai pyyaml
```

（実際の requirements.txt がある場合はそちらを使用してください）

---

## セットアップ手順

1. リポジトリをクローン／取得
2. 仮想環境を作成して依存をインストール
   - Python 仮想環境を作成・有効化
   - 必要パッケージをインストール（上記参照）
3. 環境変数の準備
   - プロジェクトルートに `.env` を作成することを推奨
   - 対話式ウィザードで作る:
     ```
     python -m kabusys.config_setup
     ```
     主要項目:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（development / paper_trading / live）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパートレード DB、デフォルト: data/paper_trading.db）
     - LOG_LEVEL, KILL_FLAG_CLEAR_ON_START など
4. 設定の検証（起動前に推奨）
   ```
   python -m kabusys.validate_config
   ```
   --strict をつけると警告も失敗扱いになります。

5. データディレクトリの権限や初期ファイルを確認
   - logs/（ログ）
   - data/（sqlite ファイル、kill.flag、execution.pid, stop_requested.flag 等）

注意:
- .env は絶対に Git にコミットしないでください。

---

## 使い方（主要スクリプト）

- 環境設定ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 実行エンジン（ExecutionEngine）起動
  ```
  python -m kabusys.run_execution
  ```
  動作ポイント:
  - 起動時にプロセス優先度を high に設定します（set_process_priority）。
  - KABUSYS_ENV=paper_trading の場合、Broker はモックを使い、DB は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用して本番データと分離します。
  - 起動前に data/stop_requested.flag がある場合は起動しません。
  - エンジンは内部で execution.pid を生成します（data/execution.pid デフォルト）。

- 監視プロセス起動
  ```
  python -m kabusys.run_monitoring
  ```
  動作ポイント:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（デフォルト 60 秒）。
  - 監視は監視用 SQLite（settings.sqlite_path：デフォルト data/monitoring.db）と DuckDB（settings.duckdb_path）を使用します。
  - 停止は data/stop_requested.flag（スクリプトの親ディレクトリ data 内）を作る/消すことで制御します。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  DB パスを直接指定する場合:
  ```
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```
  デフォルト DB は環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db。

- AI 機能（ニューススコア・レジーム判定）
  - OpenAI API を利用するため、環境変数 OPENAI_API_KEY を設定してください。
  - ニュースセンチメント: kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

- ログ
  - デフォルトログディレクトリ: logs/
  - ログレベルは LOG_LEVEL（.env）で設定可能
  - ログファイルはアプリ名別に日次ローテーションで保存（例: logs/execution.log）

---

## 運用上のポイント

- KABUSYS_ENV の値:
  - development / paper_trading / live のいずれかに設定してください。
  - live の場合は本番運用に関する警告が出ます（LINE トークンや Kill Switch 設定等の確認を推奨）。
- Kill Switch / stop フラグ:
  - KillSwitch は監視で検出した深刻な条件（例: ドローダウン超過）に応じて data/kill.flag を書き込みます。ExecutionEngine は kill.flag を検知すると停止します。
  - 起動時に既存の kill.flag を自動で消す挙動は KILL_FLAG_CLEAR_ON_START=1 で有効化できます（本番では無効化推奨）。
- 監視 DB:
  - monitoring_db.init_monitoring_db() は冪等でテーブル・インデックスを作成します。スキーママイグレーション（欠損カラム追加）も含まれます。
- ポーリング間隔:
  - 監視間隔は MONITOR_POLL_INTERVAL 環境変数で変更できます。0 以下は無効扱いでデフォルトに戻ります。
- プロセス優先度:
  - 実行/監視スクリプトは起動時に set_process_priority("high") を試みます。権限によっては警告となることがあります。

---

## 主要環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN — 必須（J-Quants API）
- KABU_API_PASSWORD — 必須（kabuステーション API）
- KABUSYS_ENV — development / paper_trading / live（デフォルト development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト 60）
- OPENAI_API_KEY — OpenAI を使う機能で必要
- PAPER_FILL_MODE — paper_trading 時の執行モード（instant / partial / never / reject）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag をクリアする（"1" で有効）

簡易 .env 例:
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...
KILL_FLAG_CLEAR_ON_START=0
```

---

## ディレクトリ構成（抜粋）

以下は本リポジトリの主要ファイル／モジュールと簡単な説明です。

- src/kabusys/
  - __init__.py — パッケージ定義（バージョン等）
  - config.py — 環境変数・.env 自動読み込み・Settings クラス
  - config_setup.py — 対話式 .env 生成ウィザード
  - validate_config.py — 起動前設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU Affinity 設定
  - monitoring/
    - monitoring_db.py — SQLite 監視ログ永続化層
    - system_monitor.py — システム状態・データ鮮度チェック
    - trade_monitor.py —（取引監視：滞留注文、約定異常など）※実装ファイル参照
    - risk_monitor.py — ドローダウン・ポジション上限の監視
    - kill_switch.py — kill.flag 書き込みユーティリティ
    - monitoring_engine.py — 各 Monitor を束ねる実行ループ
    - alert_manager.py —（アラート送信処理）
  - execution/ — 発注・エンジン関連（EngineConfig, ExecutionEngine, OrderManager 等）
  - portfolio/
    - portfolio_builder.py — 候補選定、重み計算
    - position_sizing.py — 株数決定ロジック
    - risk_adjustment.py — セクター制限・レジーム乗数
  - research/
    - factor_research.py — ファクター計算（momentum/value/volatility）
    - feature_exploration.py — IC 等の分析ユーティリティ
  - ai/
    - news_nlp.py — OpenAI を使ったニュースセンチメントスコアリング
    - regime_detector.py — レジーム判定ロジック（MA + マクロセンチメント）
  - tools/
    - paper_verification_report.py — Paper Trading 向け検証レポート生成

data/（プロジェクトルート）
- stop_requested.flag — 一時停止リクエスト（monitoring/run scripts で使用）
- kill.flag — Kill Switch による発注停止トリガー
- execution.pid — ExecutionEngine の PID 管理

logs/（デフォルト）
- execution.log, monitoring.log 等（日次ローテーション）

---

## よくある運用/デバッグのヒント

- 「起動してもすぐ終了する」場合:
  - data/stop_requested.flag が存在していないか確認
  - KILL_FLAG_CLEAR_ON_START が 1 になっていないか確認（本番では 0 推奨）
- 設定チェックでエラーが出る場合:
  - .env の必須キーが未設定の可能性（validate_config が示します）
- OpenAI 呼び出しで失敗する場合:
  - OPENAI_API_KEY を確認し rate-limit やネットワークをチェック
  - AI 関連処理はフェイルセーフ設計（失敗時はフォールバック値で継続）になっています
- ログの詳細化:
  - LOG_LEVEL=DEBUG をセットして再起動すると詳細ログが得られます

---

この README はコードベースの主要な利用手順と設計上の注意点をまとめたものです。追加のドキュメント（設計資料や API 仕様）がある場合はそちらも参照してください。必要であれば運用手順（systemd サービスファイル、Dockerfile、CI 設定など）のテンプレートも作成できます。必要ならお知らせください。