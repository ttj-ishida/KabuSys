# KabuSys — 日本株自動売買システム（README）

このリポジトリは、日本株向けの自動売買・研究・監視コンポーネント群を含む軽量フレームワークです。  
この README ではプロジェクト概要、主要機能、セットアップ手順、使い方（起動方法）およびディレクトリ構成を日本語で説明します。

重要: 本ドキュメントは src/kabusys 以下のソースコード（主要エントリポイントや設定処理）を基に作成しています。

---

## プロジェクト概要

KabuSys は次のような機能を備えたシステムです。

- 戦略の研究用ファクター計算（DuckDB を参照）
- ポートフォリオ構成（候補選定、重み計算、ポジションサイズ決定）
- 実行（ExecutionEngine）および発注管理（本番/ペーパートレード切替）
- モニタリング（システム稼働・データ鮮度・取引ログ・リスク監視）
- AI モジュール（ニュースを LLM でスコアリング、レジーム判定）
- 運用支援ツール（.env ウィザード・設定検証・ペーパートレード検証レポート）

設計方針の例:
- 本番データとペーパートレード DB を分離（KABUSYS_ENV に依存）
- DuckDB を分析向けに使用、SQLite を監視・注文ログ用に使用
- OpenAI API 呼び出しはリトライ・バリデーションを備えて安全に扱う

---

## 主な機能一覧

- 環境/設定管理
  - .env 自動ロード（プロジェクトルート検出）
  - 対話式ウィザードで .env 作成（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）

- 実行/発注
  - ExecutionEngine を起動するランチャー（run_execution）
  - 本番（live）/ペーパー（paper_trading）を切替可能
  - ペーパートレード時は MockBroker を利用し専用 SQLite（data/paper_trading.db）に記録

- 監視（Monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor を組み合わせた MonitoringEngine
  - 監視ログは SQLite（data/monitoring.db）に永続化（monitoring_db）
  - Kill Switch による外部停止（data/kill.flag）
  - run_monitoring スクリプトでポーリング起動（MONITOR_POLL_INTERVAL 環境変数で間隔変更）

- 研究（Research）
  - ファクター計算（モメンタム、ボラティリティ、バリュー等） — duckdb を利用
  - 特徴量探索・IC 計算・将来リターン取得

- ポートフォリオ構築
  - 候補選定、等重・スコア重み付け、リスクに基づくポジションサイズ計算
  - セクター集中制限やレジーム乗数の適用ロジック

- AI（OpenAI 連携）
  - ニュース記事のセンチメントスコアリング（ai.news_nlp）
  - マクロニュース＋ETF MA による市場レジーム判定（ai.regime_detector）
  - API 呼び出しは JSON-mode / バッチ / リトライ / バリデーション実装済

- 運用ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

---

## 必要依存関係（例）

主要な Python パッケージ（環境によってバージョン指定してください）:

- python >= 3.9
- duckdb
- psutil
- openai
- (任意) PyYAML — config/*.yaml の内容検証を行う場合
- sqlite3（標準ライブラリ）
- その他（logging 等は標準ライブラリ）

インストール例:
- 仮想環境を作成してから:
  - pip install duckdb psutil openai pyyaml

※ 実際の requirements.txt がある場合はそちらを使用してください。

---

## セットアップ手順（概略）

1. リポジトリをクローンし、仮想環境を作成して有効化する
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install duckdb psutil openai pyyaml

3. .env の準備
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - 生成された .env を編集して必須環境変数を設定する（以下参照）

4. 設定検証
   - python -m kabusys.validate_config
   - もし厳密チェックをしたければ: python -m kabusys.validate_config --strict

5. データディレクトリの作成（必要に応じて）
   - デフォルトの DB / ログ格納先は data/ と logs/。自動で作成される場合もありますが、権限等を確認してください。

---

## 主な環境変数（抜粋とデフォルト）

重要な環境変数の例（詳細は src/kabusys/config.py を参照）:

- JQUANTS_REFRESH_TOKEN — 必須（J-Quants API）
- KABU_API_PASSWORD — 必須（kabuステーション API）
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH — 分析用 DuckDB（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（デフォルト: INFO）
- LOG_DIR — ログディレクトリ（デフォルト: logs/）
- OPENAI_API_KEY — OpenAI 呼び出しに必要（AI モジュール使用時）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、run_monitoring 用。デフォルト 60）

Kill/Stop に関するファイル（デフォルトパス）:
- data/kill.flag — Kill Switch による ExecutionEngine 停止トリガー
- data/stop_requested.flag — run_monitoring / run_execution の外部停止判定に使用
- data/execution.pid — ExecutionEngine の PID ファイル（起動時に生成）

注意:
- run_monitoring は監視用 DB に対して環境に関係なく本番 sqlite_path を使用します（コード内の設計）。
- run_execution は KABUSYS_ENV=paper_trading の場合、paper_sqlite_path を使用して本番 DB と分離します。

---

## 使い方（起動・操作例）

1. .env を作成・設定（ウィザード推奨）
   - python -m kabusys.config_setup

2. 設定検証
   - python -m kabusys.validate_config
   - 問題があれば .env を修正し再検証

3. 実行エンジンの起動（例: 開発環境）
   - KABUSYS_ENV=development python -m kabusys.run_execution
   - ペーパートレード:
     - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
     - ペーパーモードでは MockBroker を使い data/paper_trading.db に記録されます

   停止方法:
   - 外部から停止したい場合はプロジェクトルートの data/stop_requested.flag を作成してください（run_execution / run_monitoring が検知して終了します）。
   - Kill Switch（運用による強制停止）: monitoring の KillSwitch が条件を満たすと data/kill.flag を書き込み、ExecutionEngine 停止ロジックを誘発します。

4. 監視ループの起動
   - python -m kabusys.run_monitoring
   - ポーリング間隔を ENV で指定:
     - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

5. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report
   - 期間指定:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB 指定（環境変数より優先）:
     - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

6. AI 関連
   - ai.news_nlp.score_news と ai.regime_detector.score_regime は DuckDB 接続と target_date、OpenAI API キーを渡して呼び出します。例（スクリプト呼び出し想定）:
     - python スクリプト内で OpenAI API キーを指定して呼び出す、または環境変数 OPENAI_API_KEY を設定

ログ:
- setup_logging により標準出力（stdout）と日次ローテートされたファイル（logs/<app_name>.log）へ出力されます。LOG_DIR で変更可能。

---

## 停止・運用に関するメモ

- run_execution/run_monitoring は共に data/stop_requested.flag を監視して安全終了します。
- Kill Switch は監視コンポーネント（RiskMonitor 等）の判定により data/kill.flag を書き込み、ExecutionEngine 停止を誘発します。KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動クリアされますが、本番では 0 を推奨します。
- ログディレクトリ/ファイル作成に失敗した場合はコンソール出力のみで継続します。

---

## ディレクトリ構成（主要ファイル）

リポジトリの主要な構成（src/kabusys を想定）:

- src/kabusys/
  - __init__.py
  - run_execution.py            — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — Monitoring 起動スクリプト
  - config.py                  — 環境変数 / 設定読み込みロジック
  - config_setup.py            — .env 対話ウィザード
  - validate_config.py         — 設定検証 CLI
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - ai/
    - news_nlp.py              — ニュース NLP スコアリング（OpenAI 連携）
    - regime_detector.py       — 市場レジーム判定（MA + マクロセンチメント）
  - monitoring/
    - monitoring_db.py         — SQLite スキーマ・永続化 API
    - system_monitor.py        — システム状態・データ鮮度監視
    - trade_monitor.py         — 注文ログ監視（存在するはずのモジュール）
    - risk_monitor.py          — ドローダウン・ポジション上限監視
    - kill_switch.py           — kill.flag 書込みユーティリティ
    - monitoring_engine.py     — 監視ループのオーケストレーション
    - alert_manager.py         — アラート送信（存在するはずのモジュール）
  - portfolio/
    - portfolio_builder.py     — 候補選定・重み計算
    - position_sizing.py       — 株数決定・スケールダウン・丸め
    - risk_adjustment.py       — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py       — モメンタム/バリュー/ボラティリティ計算
    - feature_exploration.py   — 将来リターン・IC 計算・統計要約
  - utils/
    - logging_setup.py         — 統一的なロギング設定
    - process_priority.py      — プロセス優先度 / CPU affinity 設定

（上記以外に execution/ や data/ など他モジュールが存在する想定があり、ソース内で参照しています）

---

## 開発・拡張のヒント

- DuckDB を使った分析系関数は副作用を持たず、ユニットテストしやすいように設計されています（関数に conn と target_date を渡す）。
- OpenAI 等外部 API は呼び出し部を簡単にモック/パッチできるよう抽象化されており、unittest.mock によるテストが可能です。
- 設定検証やウィザードは運用前チェックを想定しているため、CI で validate_config を実行することを推奨します。
- ログはアプリ名ごとに logs/<app_name>.log に日次ローテートで出力されます。運用時はログローテーション設定・保持日数 (デフォルト 30 日) を確認してください。

---

不足している資料や詳細（例: ExecutionEngine の内部仕様、TradeMonitor, OrderRepository の実装、requirements.txt やデプロイ手順など）が必要であれば、その箇所にフォーカスした README の追加章を作成します。どの部分を詳しく書いて欲しいか教えてください。