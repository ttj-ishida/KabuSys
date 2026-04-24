# KabuSys

日本株向け自動売買システムの参照実装 (パーツ群のみ抜粋)。  
本 README はリポジトリ内の主要スクリプト／モジュールをもとに、導入・実行方法、機能概要、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買を想定したモジュール群です。主な目的は次のとおりです。

- 戦略（ファクター計算・特徴量解析）とポートフォリオ構築ロジック
- 発注・リスク管理を行う ExecutionEngine（実行エンジン）
- システム監視・アラート・Kill Switch を提供する Monitoring
- Paper Trading（ペーパートレード）向けの分離された DB と検証ツール
- ニュースを LLM（OpenAI）で評価する AI 補助モジュール
- 設定ウィザードおよび起動前検証ツール

設計方針として、実運用で危険になりうる操作（本番 DB の上書きなど）に配慮し、Paper Trading 用 DB 分離、Kill Switch、各種フェイルセーフを備えています。

---

## 主な機能一覧

- 設定管理
  - .env の自動ロード / 対話式設定ウィザード（kabusys.config_setup）
  - 起動前検証 CLI（kabusys.validate_config）
- 実行エンジン（Execution）
  - Broker クライアント生成（実口座 / Mock 選択）
  - 注文管理・リスク管理・照合（Reconciler 等）
  - ExecutionEngine をスレッドで起動 / 停止制御（stop flag）
  - Paper Trading は専用 SQLite（data/paper_trading.db）に記録
- 監視（Monitoring）
  - SystemMonitor（CPU/メモリ/ディスク・データ鮮度 / 実行プロセスの検出）
  - TradeMonitor / RiskMonitor（滞留注文、約定異常、ドローダウン・ポジション数監視）
  - KillSwitch（閾値超過時に data/kill.flag を書き込み Execution を停止）
  - 永続化は SQLite（monitoring DB）
- 研究・リサーチ
  - ファクター計算（モメンタム / ボラティリティ / バリュー 等） — DuckDB 利用
  - 将来リターン・IC 計算・統計サマリ
- AI 支援
  - ニュース NLP（OpenAI を用いた銘柄別センチメントの算出）
  - 市場レジーム判定（ETF MA と LLM センチメントの合成）
- ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）
- ユーティリティ
  - ロギング設定（console + 日次ローテーションファイル）
  - プロセス優先度 / CPU affinity 設定ユーティリティ

---

## 前提・依存関係

最低限必要なもの（主要なライブラリ）：

- Python 3.9+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- pyyaml（設定ファイル検証を行う場合に任意で必要）

インストール例（仮想環境推奨）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb psutil openai
# 設定ファイル YAML の検証を行うなら:
pip install PyYAML
```

（プロジェクトに requirements.txt / pyproject.toml があればそちらを使用してください。）

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動。

2. 必要ライブラリをインストール（上記参照）。

3. .env の作成（対話式ウィザード推奨）:

   ```bash
   python -m kabusys.config_setup
   ```

   ウィザードは J-Quants や kabuステーションのトークンなど必要な環境変数を対話的に入力し `.env` を作成します。

4. 設定の検証（起動前チェック）:

   ```bash
   python -m kabusys.validate_config
   # 警告を厳格に FAIL 扱いにする場合
   python -m kabusys.validate_config --strict
   ```

5. 必要に応じてデータディレクトリを作成（ログ・DB 保存先）:

   - data/ （SQLite DB やフラグファイル）
   - logs/ （ログファイル）

   ログディレクトリは自動作成されますが、アクセス権等の問題がある場合は手動で用意してください。

---

## 主要な環境変数（抜粋）

必須（最低限）:

- JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン
- KABU_API_PASSWORD — kabuステーション API パスワード

運用に影響する設定（代表例）:

- KABUSYS_ENV — 実行環境: development | paper_trading | live
  - paper_trading の場合、MockBrokerClient を使い data/paper_trading.db に記録します
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル
- OPENAI_API_KEY — OpenAI を使う AI 機能で必要
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — 本番環境で Kill Flag を自動クリアするか（0/1、0 推奨）

.env 例（簡易）:

```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...
```

注意: `.env` は絶対にリポジトリにコミットしないでください。

---

## 使い方（主要スクリプト）

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 起動前検証
  - python -m kabusys.validate_config
  - --strict をつけると警告も exit(1) 扱い

- ExecutionEngine（実際の発注エンジン）起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します
  - 実行中は data/execution.pid を生成し、停止は data/stop_requested.flag を作成することで制御できます

- Monitoring（SystemMonitor のポーリング）起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（デフォルト 60 秒）
  - Monitoring は実行環境にかかわらず本番 sqlite_path を使用して監視ログを記録します

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB は data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH により上書き可）

- AI / レジーム判定 / ニューススコアリング
  - OpenAI API キーが必要（OPENAI_API_KEY）
  - 対象関数:
    - kabusys.ai.score_news (news NLP)
    - kabusys.ai.regime_detector.score_regime (レジーム判定)
  - 直接 Python から呼び出すか、用途に合わせて CLI ラッパーを作って利用します

- テスト用ユーティリティ
  - MonitoringEngine.run_once() をインポートしてテスト的に 1 回だけ監視処理を実行可能
  - 各モジュールは純粋関数や独立クラスで構成されており、単体テストが書きやすい設計です

停止とフラグファイル:

- data/stop_requested.flag — run_execution/run_monitoring のループ終了トリガ（監視・実行の両方で参照）
- data/kill.flag — KillSwitch による ExecutionEngine 停止シグナル（Execution 側で検知して停止）

---

## ディレクトリ構成（主要ファイルの説明）

（リポジトリの `src/kabusys` を想定）

- kabusys/
  - __init__.py — パッケージ定義、__version__ 等
  - config.py — 環境変数 / Settings 管理（自動 .env ロード、パースロジック含む）
  - config_setup.py — 対話式 .env ウィザード
  - validate_config.py — 起動前検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - data/ (想定) — SQLite / DuckDB / フラグファイル を保存するディレクトリ（data/monitoring.db, data/paper_trading.db, data/kabusys.duckdb, data/kill.flag など）
  - logs/ (想定) — ログファイルを保存するディレクトリ（logs/execution.log など）
  - utils/
    - logging_setup.py — 統一ログ設定（console + TimedRotatingFileHandler）
    - process_priority.py — プロセス優先度・CPU affinity 設定
  - monitoring/
    - monitoring_db.py — SQLite 監視テーブルの初期化・永続化 API（MonitoringDB）
    - system_monitor.py — システム状態、データ鮮度、実行プロセス検出
    - trade_monitor.py — (滞留注文・約定異常検出等) ※詳細ファイルはリポジトリ内に存在
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — Kill Switch 実装（kill.flag の書き込み）
    - monitoring_engine.py — 上記モニターを束ねるエンジン
    - alert_manager.py — LINE 等への通知管理（実装ありの場合）
  - execution/
    - execution_engine.py — ExecutionEngine 本体
    - broker_factory.py — BrokerClient の生成（実口座 / Mock 切替）
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py — 発注・履歴・照合・リスク管理コンポーネント
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 発注株数計算、ロット丸め、集計調整
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — モメンタム/ボラティリティ/バリュー等のファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン・IC・統計サマリ
  - ai/
    - news_nlp.py — ニュースを OpenAI で採点し ai_scores に書き込む
    - regime_detector.py — ETF MA と LLM 出力を合成して market_regime を書き込む
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成

---

## 運用上の注意・ベストプラクティス

- .env は機密情報を含むため絶対にリポジトリにコミットしないでください（config_setup が警告を出します）。
- 本番運用（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START を 0 にしておくことを推奨します。
- Monitoring は本番 sqlite_path を参照するため、監視が本番 DB を誤って上書きしないよう権限管理・バックアップをしてください。
- OpenAI API を使う機能は API コスト・レイテンシに注意。呼び出しはバッチ化・レートリミット対策を実装済みですが、実運用前に試験を行ってください。
- Paper Trading は本番 DB と分離されているため、まずは KABUSYS_ENV=paper_trading で動作確認を行ってください。

---

## 参考コマンドまとめ

- 対話式 .env 作成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- Execution 起動:
  - python -m kabusys.run_execution
- Monitoring 起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- 依存インストール例:
  - pip install duckdb psutil openai PyYAML

---

もし README に追記したい点（たとえば CI 設定例、systemd ユニットファイル例、より詳細な設定項目一覧やサンプル .env.example）や、特定モジュール（AI 周り、ExecutionEngine の詳しい動作など）を詳述してほしい場合は教えてください。必要に応じて追補した README を作成します。