# KabuSys

日本株向け自動売買システムのモジュール群です。ポートフォリオ構築、発注エンジン、監視・アラート、リサーチ用ファクター計算、LLM を使ったニュース NLP などを含むライブラリ／起動スクリプト群を提供します。

---

## プロジェクト概要

KabuSys は以下の主要コンポーネントで構成される自動売買基盤です。

- ExecutionEngine：ブローカーと連携して注文を発行・管理する実行エンジン（paper_trading モードを含む）
- Monitoring：システム・注文・リスクを定期的にチェックしてアラートや Kill Switch を管理
- Portfolio Construction：銘柄選定、重み計算、ポジションサイズ算出、リスク調整ロジック（純粋関数）
- Research：DuckDB ベースのファクター計算・特徴量探索ツール
- AI：OpenAI を利用したニュースセンチメント（news_nlp）や市場レジーム判定（regime_detector）
- ユーティリティ：ログ設定、プロセス優先度設定、設定ファイルウィザード／検証など

設計方針として「本番データへのルックアヘッド回避」「部分失敗時のフェイルセーフ」「DB の冪等操作」「テスト容易性（関数分離/差し替え可能）」が意識されています。

---

## 主な機能一覧

- 設定管理
  - .env 自動ロード（プロジェクトルートを検出）
  - 対話式設定ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）
- 実行エンジン
  - 本番 / paper_trading（モックブローカー）分離
  - Risk Manager / Order Manager / Reconciler を組み合わせた実行制御
- 監視（Monitoring）
  - SystemMonitor: CPU/メモリ/Disk、実行プロセスの存在、データ鮮度チェック
  - TradeMonitor: 滞留注文や約定異常の検出（trade_logs）
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新、リスクログ
  - KillSwitch: 条件を満たしたら data/kill.flag を書き込み ExecutionEngine を停止
  - MonitoringEngine: 各 Monitor のポーリング集約とアラート送出
- ポートフォリオ構築
  - 候補選定、等重・スコア重み付け
  - セクターキャップ適用、レジーム乗数
  - ポジションサイズ決定（単元丸め、aggregate cap、risk-based）
- リサーチ
  - Momentum / Volatility / Value ファクター計算（DuckDB 経由）
  - 将来リターン、IC 計算、ファクター統計
- AI 関連
  - ニュースセンチメント（OpenAI を用いたバッチ評価・JSON モード対応・リトライ）
  - マクロニュース＋ETF MA を合成した市場レジーム判定
- ツール
  - Paper Trading の検証レポート生成（python -m kabusys.tools.paper_verification_report）

---

## 必要な依存パッケージ（代表例）

（プロジェクトに requirements.txt がない場合、以下をインストールしてください）

- Python 3.10+（コードは型ヒントで | を使用しているため 3.10 以上を推奨）
- duckdb
- psutil
- openai
- PyYAML（config/*.yaml の内容検証に必要。無くても動作は可能）
- そのほか環境に応じたパッケージ（sqlite3 は標準）

例:
```bash
pip install duckdb psutil openai pyyaml
```

---

## 環境変数（主なもの）

必須
- JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン
- KABU_API_PASSWORD — kabuステーション API パスワード

主要（デフォルト値あり）
- KABUSYS_ENV — 実行環境（development / paper_trading / live）（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
- OPENAI_API_KEY — OpenAI API キー（AI 機能利用時に必要）
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START 等（Settings 経由で参照）

その他
- PAPER_FILL_MODE — paper_trading の fill モード（instant / partial / never / reject）

.env は直接作成せず、対話式で生成することを推奨します（python -m kabusys.config_setup）。

---

## セットアップ手順（推奨）

1. リポジトリをクローン／取得する
2. 仮想環境作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows は .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb psutil openai pyyaml
4. 環境変数ファイルを作成
   - python -m kabusys.config_setup
     - 対話式に .env を生成します（.env は必ず Git にコミットしないでください）
5. 設定を検証
   - python -m kabusys.validate_config
   - 本番前は --strict を付けて警告も FAIL 扱いにできます
6. データディレクトリ / ログディレクトリ の確認
   - デフォルト DB 等が格納される data/ および logs/ を確認（自動作成されますが権限に注意）

---

## 使い方（起動例）

- 監視（SystemMonitor ベースのポーリング）を起動:
  - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
  - 停止は data/stop_requested.flag を作成するか Ctrl+C

- 実行エンジン（ExecutionEngine）を起動:
  - 本番風に起動（注意して使用）:
    - KABUSYS_ENV=live python -m kabusys.run_execution
  - ペーパートレード（モックブローカー・DB を分離）:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- 設定ウィザード:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで SQLite ファイルを指定することも可能

- AI ニューススコアリング（ライブラリ利用例）
  - プログラムから呼び出す:
    - from openai import OpenAI
      from kabusys.ai.news_nlp import score_news
      # duckdb 接続を渡して score_news(conn, target_date, api_key=...)
  - OPENAI_API_KEY 環境変数を設定しておくと api_key を省略できます

停止・制御フラグ
- data/stop_requested.flag — run_monitoring / run_execution の外側から「起動スクリプトのループを抜ける」ために利用
- data/kill.flag — KillSwitch が条件を満たした場合に書き込まれる（ExecutionEngine はこれを検知して停止）
- data/*.pid — 実行中プロセスの PID 管理用に使用

ログ
- デフォルトは logs/<app_name>.log に日次ローテーションで保存（logs ディレクトリは自動作成）
- コンソールにも出力（stdout）

---

## 主要モジュール・ディレクトリ構成

以下はコードベース（src/kabusys）で確認できる主要ファイル・ディレクトリと簡単な説明です。

- kabusys/
  - __init__.py — パッケージ定義（__version__）
  - config.py — Settings クラス（環境変数読み込み、デフォルト、バリデーション）
  - config_setup.py — .env 対話式ウィザード（CLI）
  - validate_config.py — 設定検証 CLI
  - run_monitoring.py — SystemMonitor のポーリング起動スクリプト（MONITOR_POLL_INTERVAL に対応）
  - run_execution.py — ExecutionEngine 起動スクリプト（paper_trading を自動分離）
  - utils/
    - logging_setup.py — ログ設定ユーティリティ（Stream + TimedRotatingFile）
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
  - monitoring/
    - monitoring_db.py — SQLite による監視ログ永続化層（テーブル作成・操作）
    - system_monitor.py — システム状態・データ鮮度のチェック
    - trade_monitor.py — （注文ログの監視: 滞留注文や約定異常の検出）※ファイル参照あり
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — Kill Switch（flag ファイル生成）
    - monitoring_engine.py — 各 Monitor を束ねるジョブループ
    - alert_manager.py — アラート送信管理（LINE 等）
  - execution/
    - execution_engine.py — ExecutionEngine（セッション管理）
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py — 実行系コンポーネント
  - portfolio/
    - portfolio_builder.py — 候補選定、重み計算
    - position_sizing.py — 発注株数計算（単元丸め、aggregate cap）
    - risk_adjustment.py — セクター上限・レジーム乗数
  - research/
    - factor_research.py — Momentum / Volatility / Value 等のファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン計算、IC、統計サマリー
  - ai/
    - news_nlp.py — ニュース記事の LLM ベースセンチメントスコアリング
    - regime_detector.py — マクロ＋ETF MA による市場レジーム判定（LLM を併用）
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成スクリプト

（上記は抜粋です。実際のコードでさらに細かいモジュールが存在します。）

---

## 注意事項 / ベストプラクティス

- .env を絶対に Git にコミットしないでください（README ヘッダや config_setup にも明記）
- KABUSYS_ENV=live のときは十分に設定を確認してください（validate_config の live ガードが警告を出します）
- OpenAI を使う機能は API コストとレートリミットに注意してください（news_nlp はバッチ & リトライ実装あり）
- paper_trading モードは本番 DB と分離されます（PAPER_TRADING_SQLITE_PATH を使用）
- ログディレクトリや data ディレクトリの権限・所有者に注意（自動作成に失敗する可能性があるため）

---

## 開発・テストのヒント

- many functions are pure: portfolio.* や research.* の多くは DB に依存しない純粋関数設計で、ユニットテストが容易です
- OpenAI の呼び出し部分は内部関数を patch してモックできます（news_nlp._call_openai_api 等）
- validate_config.run_wizard / monitoring_engine.run_once 等は CLI での単体実行・統合テストに便利です

---

以上が README の概要です。必要であれば、本 README をベースに「環境ごとの起動手順（systemd サービス定義例、Dockerfile、docker-compose）」や「詳細な API / DB スキーマドキュメント」を追加できます。どのドキュメントを優先して欲しいか教えてください。