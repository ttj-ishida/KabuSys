# KabuSys

日本株向けの自動売買システム（ライブラリ＋実行/監視バイナリ群）。  
本リポジトリは、発注エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、リサーチ（ファクター計算／特徴量解析）、および AI を用いたニュースセンチメント評価などのコンポーネントを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は次を目的としたモジュール群です。

- 日次のファクター計算／シグナル生成（DuckDB ベースの価格データ参照）
- ポートフォリオ構築（候補選定、重み計算、銘柄ごとの株数算出）
- 実際の発注エンジン（kabuステーション などのブローカークライアントを抽象化）
- Paper Trading（テスト用に本番 DB と分離して振る舞う）
- 監視機能（プロセス死活、データ鮮度、注文滞留、ドローダウン監視）
- AI 補助機能（OpenAI を用いたニュースセンチメント、レジーム判定）
- 設定ウィザード、検証ツール、レポート生成ツール

設計上のポイント：
- DuckDB を分析・リサーチ用に利用（prices_daily / raw_financials 等のテーブルを想定）
- SQLite を監視ログ・注文履歴などの永続化に利用
- Paper Trading は本番 DB と完全に分離（PAPER_TRADING_SQLITE_PATH）
- AI 呼び出しは外部 API（OpenAI）を使用し、API キーが必要
- 多くのユーティリティは副作用を避けるように設計（純粋関数群あり）

---

## 主な機能一覧

- 実行（Entrypoints）
  - run_execution.py: ExecutionEngine を起動。KABUSYS_ENV により paper_trading モードで動作を分離。
  - run_monitoring.py: SystemMonitor をポーリング実行（MONITOR_POLL_INTERVAL で間隔指定可）。

- 設定・検証
  - config_setup.py: .env を対話的に作成/更新するウィザード。
  - validate_config.py: .env および config/*.yaml の簡易検証 CLI（--strict オプションあり）。

- 監視
  - monitoring/monitoring_db.py: 監視 DB スキーマ初期化・読み書き。
  - monitoring/system_monitor.py: CPU/メモリ/ディスクやデータ鮮度、実行プロセスのチェック。
  - monitoring/trade_monitor.py: 注文滞留や約定異常価格の検出。
  - monitoring/risk_monitor.py: ドローダウン・ポジション上限の監視とアラート記録。
  - monitoring/kill_switch.py: 条件に応じて data/kill.flag を書き込み ExecutionEngine を停止させる仕組み。
  - monitoring/monitoring_engine.py: 各 Monitor を束ねるループ実行器。

- ポートフォリオ
  - portfolio/portfolio_builder.py: 候補選定（スコア順）・重み計算（等配分・スコア加重）。
  - portfolio/position_sizing.py: 各銘柄の株数算出（単元丸め、リスクベース、資金制約対応）。
  - portfolio/risk_adjustment.py: セクター集中抑制・レジーム乗数計算。

- リサーチ
  - research/factor_research.py: Momentum/Volatility/Value 等のファクター計算（DuckDB 使用）。
  - research/feature_exploration.py: 将来リターン計算、IC（Information Coefficient）、統計サマリー。

- AI
  - ai/news_nlp.py: raw_news を集約し OpenAI（gpt-4o-mini 等）で銘柄ごとにセンチメントを算出して ai_scores に保存。
  - ai/regime_detector.py: ETF の MA 乖離とマクロニュースセンチメントを合成して市場レジームを判定。

- ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポートを生成（稼働率、注文成功率、レイテンシなど）。

- ユーティリティ
  - utils/process_priority.py: プロセス優先度および CPU affinity 設定ユーティリティ。

---

## セットアップ手順（ローカル開発向け）

事前準備：
- Python 3.10+ を推奨
- SQLite（OS 標準）と DuckDB の Python パッケージが必要

1. リポジトリをクローン
   ```
   git clone <this-repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成・有効化
   (例)
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール
   実際の requirements.txt は本リポジトリに付属していない想定のため、代表的な依存をインストールしてください：
   ```
   pip install duckdb psutil openai
   # optional: PyYAML を使った設定検証を行う場合
   pip install pyyaml
   ```
   注: OpenAI API を使う機能は openai パッケージを必要とします。AI 機能を使わない場合は不要です。

4. .env の準備
   対話式ウィザードで作成できます：
   ```
   python -m kabusys.config_setup
   ```
   または手動でルートに `.env` を作成してください（例は下段参照）。

5. 設定検証（起動前に推奨）
   ```
   python -m kabusys.validate_config
   # 警告を fail としたい場合は --strict
   python -m kabusys.validate_config --strict
   ```

6. DB 初期化
   - 実行 / 監視起動時に必要なテーブルは自動的に作成されます（monitoring_db.init_monitoring_db）。

---

## 使い方（主要な実行コマンド）

- ExecutionEngine を起動（通常はデーモン的に実行）
  ```
  python -m kabusys.run_execution
  ```
  動作モードは環境変数 KABUSYS_ENV で制御（development / paper_trading / live）。
  - paper_trading の場合は MockBrokerClient を使用し、データは PAPER_TRADING_SQLITE_PATH（default: data/paper_trading.db）へ保存されるため本番 DB とは分離されます。

- Monitoring を起動（SystemMonitor のポーリング）
  ```
  python -m kabusys.run_monitoring
  ```
  ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可。デフォルトは 60 秒。
  監視は監視用 SQLite（Settings.sqlite_path）にログを書きます。Monitoring は常に本番 sqlite_path を使用します（環境に依らず）。

- Paper Trading 検証レポートを生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを明示する場合
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- 設定ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

運用上のファイル／フラグ：
- 停止フラグ（Execution を停止させる）: data/kill.flag（KillSwitch が書き込む）
- 監視スクリプトの停止要求: data/stop_requested.flag
- エンジンの PID ファイル: data/execution.pid

Kill flag のクリア（手動）:
```
rm data/kill.flag
```
（Settings.kill_flag_clear_on_start を 1 に設定すると起動時に自動でクリアされますが、本番環境では 0 を推奨）

---

## 環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン
- KABU_API_PASSWORD — kabuステーション API パスワード

主な任意/推奨:
- KABUSYS_ENV — 実行環境: development / paper_trading / live（default: development）
- DUCKDB_PATH — DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（default: data/paper_trading.db）
- OPENAI_API_KEY — OpenAI を使うモジュール（news_nlp, regime_detector）の API キー
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）
- PAPER_FILL_MODE — paper_trading の mock fill 動作（instant/partial/never/reject）

最初の .env は `python -m kabusys.config_setup` で作成するのが推奨です。

サンプル（.env の最低限の例）
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0
```

---

## 主要ファイル / ディレクトリ構成

（プロジェクトルート直下に src/ を置く構成を想定。ここでは src/kabusys 以下を中心に列挙）

- src/kabusys/
  - __init__.py
  - config.py — 設定 / .env ロード / Settings クラス
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト

  - ai/
    - __init__.py
    - news_nlp.py — ニュース NLP（OpenAI）/ ai_scores 書き込み
    - regime_detector.py — マクロセンチメント + MA でレジーム判定

  - monitoring/
    - monitoring_db.py — SQLite スキーマ初期化 / 永続化 API
    - system_monitor.py — システム / データ鮮度監視
    - trade_monitor.py — 注文滞留 / 約定異常検出
    - risk_monitor.py — ドローダウン / ポジション数監視
    - kill_switch.py — kill.flag 書込ロジック
    - monitoring_engine.py — 各 Monitor を束ねる実行器
    - alert_manager.py — （アラート配送ロジック、未掲示の実装ファイル）

  - portfolio/
    - __init__.py
    - portfolio_builder.py — 候補選定 / 重み計算
    - position_sizing.py — 株数決定ロジック
    - risk_adjustment.py — セクター制限 / レジーム乗数

  - research/
    - __init__.py
    - factor_research.py — Momentum / Volatility / Value 等
    - feature_exploration.py — 将来リターン / IC / 統計サマリー

  - execution/               （実際の実行関連コンポーネント）
    - broker_factory.py
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - order_record.py
    - ...（細かい実装は該当ファイル参照）

  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading 検証レポート

  - utils/
    - __init__.py
    - process_priority.py — プロセス優先度 / CPU affinity 設定

- その他
  - data/ — DB ファイル（duckdb / sqlite）やフラグファイル（kill.flag など）を格納することを想定
  - config/ — system_config.yaml 等の設定テンプレート（validate_config がチェック）

---

## 運用上の注意・ベストプラクティス

- .env は機密情報を含むため Git にコミットしない（config_setup.py の冒頭でも注意を出力）。
- 本番（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START=0 を推奨（誤って Kill Switch をクリアしない）。
- Monitoring は常に Settings.sqlite_path（本番監視 DB）を使用します。paper_trading でも監視は同一 DB を参照する設計です。
- AI 機能を利用する際は OpenAI API の使用料に注意してください。エラー時のフェイルセーフが組み込まれていますが、API 呼び出しが発生します。
- PID ファイル / kill.flag / stop_requested.flag による外部制御を活用して安全にプロセス停止を行ってください。

---

## 開発向けヒント

- DuckDB のテーブル（prices_daily / raw_financials / raw_news 等）はリサーチ・AI モジュールの入力になります。ローカルで分析用データを作成して動作確認してください。
- validate_config.py は PyYAML がインストールされていれば config/*.yaml のパース検証も行います。YAML 検証を行う場合は `pip install pyyaml`。
- テスト時は OpenAI への実際の呼び出しをモックするため、各モジュールの `_call_openai_api` 関数等をパッチして利用できます（コード内でその前提で設計されています）。

---

README に含める追加の情報（例：実際の requirements.txt、運用手順書、systemd ユニットファイル、テストケースなど）が必要であれば、どの情報を優先して追加するか指示してください。