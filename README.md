# KabuSys — README (日本語)

このリポジトリは日本株向けの自動売買・研究プラットフォームの一部実装です。戦略の研究、ポートフォリオ構築、実行（ExecutionEngine）、監視（Monitoring）、AIを使ったニュース解析などのユーティリティ群を含みます。

以下は repository の概要、機能、セットアップ方法、使い方、ディレクトリ構成の説明です。

目次
- プロジェクト概要
- 機能一覧
- 必要要件 / 依存パッケージ
- セットアップ手順
- 環境変数 (.env) について
- 実行例 / 使い方
- 主要スクリプトの動作メモ
- ディレクトリ構成（主要ファイルの説明）
- 注意点 / 運用上のポイント

---

## プロジェクト概要

KabuSys は日本株自動売買システム向けのユーティリティ群です。  
主な目的は以下の通りです。

- ファクター計算・研究（DuckDB を用いた時系列データ解析）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイジング）
- 実行エンジン（ExecutionEngine）による注文制御（本番 / ペーパートレード両対応）
- 監視モジュール（System / Trade / Risk Monitor）による常時監視と Kill Switch
- AI を用いたニュース NLP（OpenAI API を使った銘柄ごとのセンチメント評価）
- 各種 CLI ツール（設定ウィザード・設定検証・ペーパートレード検証レポート等）

主要設計方針の例:
- DuckDB と SQLite を用途に応じて使い分ける（分析用: DuckDB、監視/発注ログ: SQLite）
- 環境依存設定は .env または環境変数で管理
- 本番とペーパートレードを明確に分離（データベースや broker クライアントなど）

---

## 機能一覧

- 環境設定ウィザード（kabusys.config_setup）
  - .env の対話的作成 / 更新を支援
- 設定検証 CLI（kabusys.validate_config）
  - 必須環境変数・設定ファイルの有無をチェック
- 実行エンジン起動スクリプト（run_execution.py）
  - 本番 / ペーパートレード切り替え
  - ブローカークライアントの生成、ExecutionEngine の起動
- 監視ループ起動スクリプト（run_monitoring.py）
  - SystemMonitor を定期実行して system_status などを記録
  - MONITOR_POLL_INTERVAL でポーリング間隔を変更可能
- 監視データ永続化（monitoring_db.py）
  - system_status, trade_logs, positions, risk_logs, dashboard 等のテーブル操作
- リスク監視（risk_monitor.py）・Kill Switch（kill_switch.py）
  - ドローダウン・ポジション上限などをチェックして kill.flag を書き込む
- AI モジュール（ai/news_nlp.py, ai/regime_detector.py）
  - OpenAI を使ったニュースセンチメントや市場レジーム判定
- 研究用モジュール（research/*.py）
  - ファクター計算（momentum / volatility / value 等）
  - 将来リターン・IC 計算・統計サマリー
- ポートフォリオ構築（portfolio/*.py）
  - 候補選定、重み計算、ポジションサイズ算出、セクター制限
- ツール（tools/paper_verification_report.py）
  - ペーパートレード結果の検証レポート生成

---

## 必要要件 / 依存パッケージ

明示的な requirements.txt は含まれていませんが、本コードが依存する主要パッケージは以下です。

- Python 3.9+
- duckdb
- psutil
- openai (OpenAI Python SDK)
- PyYAML（設定ファイルの YAML 検証時に任意）
- （SQLite は標準ライブラリで使用）

インストール例（仮想環境推奨）:
```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install duckdb psutil openai pyyaml
```

必要に応じて他のパッケージ（例: numpy 等）を追加してください（現在の実装は標準ライブラリ中心に書かれています）。

---

## セットアップ手順

1. リポジトリをクローン / ワークツリーに配置
2. 仮想環境の作成・有効化（任意だが推奨）
3. 依存パッケージをインストール（上記参照）
4. .env の作成
   - 対話式で作る場合:
     ```bash
     python -m kabusys.config_setup
     ```
   - または .env.example を参考に手動で作成
5. 設定検証:
   ```bash
   python -m kabusys.validate_config
   ```
   --strict オプションを使うと警告も失敗扱いになります。
6. 必要なディレクトリ作成（デフォルトパスを使用する場合）
   - data/ （SQLite や pid/flag 用）
   - logs/ （ログ保存）

---

## 環境変数 (.env) の主な項目

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）

主要オプション（デフォルト値）:
- KABUSYS_ENV — 実行環境（development / paper_trading / live）（default: development）
- DUCKDB_PATH — 分析用 DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（monitoring.db）パス（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（default: data/paper_trading.db）
- LOG_LEVEL — ログレベル（default: INFO）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知用（任意）
- OPENAI_API_KEY — OpenAI を使用する際は必須（AI 機能利用時）

config_setup で生成される .env の候補項目は config_setup.py の _ITEMS に詳述されています。

例（.env の最小例）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0
```

注意:
- run_monitoring は KABUSYS_ENV にかかわらず本番の sqlite_path（Settings.sqlite_path）を使用します（監視は常に本番監視 DB を対象とする設計）。
- run_execution は KABUSYS_ENV が paper_trading の場合、paper_sqlite_path を使用して本番データと分離します。

---

## 実行例 / 使い方

基本的な CLI 実行の例を示します。

設定ウィザード:
```bash
python -m kabusys.config_setup
```

設定検証:
```bash
python -m kabusys.validate_config
# strict モード（警告も失敗扱い）
python -m kabusys.validate_config --strict
```

監視ループを起動（デフォルト 60 秒間隔）:
```bash
# 環境変数で間隔を上書き
export MONITOR_POLL_INTERVAL=30
python -m kabusys.run_monitoring
```
- 停止は data/stop_requested.flag を作成するか Ctrl+C（KeyboardInterrupt）
- stop フラグファイルパス: <project_root>/data/stop_requested.flag（コード内定義）

実行エンジン（ExecutionEngine）を起動:
```bash
# 本番 or ペーパートレードは KABUSYS_ENV で切替
export KABUSYS_ENV=paper_trading
python -m kabusys.run_execution
```
- ペーパートレードでは MockBrokerClient を使用し、data/paper_trading.db に記録されます
- 実行はスレッドで開始し、data/stop_requested.flag が作成されると停止します
- 実行中は pid ファイル (data/execution.pid) が使用されます

ペーパートレード検証レポート生成:
```bash
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db
```

AI を用いたニューススコアリング / レジーム判定（プログラム的に呼び出す例）:
- 必要: OPENAI_API_KEY 環境変数を設定
- 例（score_news）:
  ```py
  from kabusys.ai.news_nlp import score_news
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  from datetime import date
  score_news(conn, date(2026,4,1), api_key=None)  # api_key None → 環境変数を参照
  ```
- 同様に regime 判定は kabusys.ai.regime_detector.score_regime を使用

ログ:
- ロギングは kabusys.utils.logging_setup.setup_logging により統一
- デフォルトログディレクトリ: logs/
- 起動スクリプトはそれぞれ logs/<app_name>.log（例: logs/execution.log, logs/monitoring.log）へ日次ローテーション出力

---

## 主要スクリプトの動作メモ

- run_monitoring.py
  - SystemMonitor を使ったポーリングループを起動
  - 環境変数 MONITOR_POLL_INTERVAL で秒数を設定（デフォルト 60）
  - 監視 DB（sqlite）は Settings.sqlite_path を使用（環境にかかわらず本番 path）

- run_execution.py
  - ExecutionEngine を起動して発注ロジックを動かす
  - KABUSYS_ENV=paper_trading のときは paper_sqlite_path を使って DB を分離
  - ブローカークライアントは BrokerClientFactory.create(settings) で生成

- config_setup.py
  - .env を対話式に作成・更新するウィザード

- validate_config.py
  - 環境変数や config/*.yaml の存在・簡易検証を行う

---

## ディレクトリ構成（主要ファイルの説明）

以下は src/kabusys 配下の主なモジュールと簡単な説明です（抜粋）。

- kabusys/
  - __init__.py — パッケージ初期化（version 等）
  - config.py — Settings クラス：環境変数の取得・検証と .env 自動読み込みロジック
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前検証 CLI
  - run_monitoring.py — 監視ループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト

- kabusys/ai/
  - news_nlp.py — ニュースを OpenAI で解析し ai_scores テーブルへ書込み
  - regime_detector.py — マクロ + ETF ma200 を使って市場レジームを判定

- kabusys/monitoring/
  - monitoring_db.py — SQLite テーブル作成・アクセスラッパー
  - system_monitor.py — CPU/メモリ/ディスク/データ鮮度/プロセス監視
  - trade_monitor.py — 発注ログ / 滞留注文 / 約定異常チェック（コードベースに存在）
  - risk_monitor.py — ドローダウンやポジション上限監視
  - kill_switch.py — kill.flag 書込 / クリア API
  - monitoring_engine.py — 各モニタのまとめとアラート発行

- kabusys/execution/
  - (ExecutionEngine, OrderManager, Reconciler, RiskManager, BrokerClientFactory 等の実装)
  - run_execution.py から利用

- kabusys/portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 発注株数計算（lot 単位丸め、aggregate cap）
  - risk_adjustment.py — セクター上限・レジーム乗数

- kabusys/research/
  - factor_research.py — momentum / volatility / value ファクター計算（DuckDB）
  - feature_exploration.py — 将来リターン・IC・統計サマリー

- kabusys/tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成スクリプト

- kabusys/utils/
  - logging_setup.py — ログ設定ユーティリティ
  - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ

補足:
- data/ 配下は DB ファイルや flag/pid ファイルを置く想定（例: data/monitoring.db, data/paper_trading.db, data/kill.flag, data/execution.pid）。
- logs/ はログファイルの保存先（設定で変更可能）。

---

## 注意点 / 運用上のポイント

- run_monitoring は監視 DB（Settings.sqlite_path）を使うため、監視プロセスを別環境（例: development）で動かしても production DB を参照する点に注意してください。
- ペーパートレードでは paper_sqlite_path にデータを記録するため、本番 DB と分離できます。KABUSYS_ENV を適切に設定してください。
- AI を利用する機能は OpenAI API キー（OPENAI_API_KEY）が必須です。API コール時にはレート制限やエラーに対するリトライ・フォールバック処理が実装されていますが、コストと呼び出し頻度に注意してください。
- kill.flag（Settings.kill_flag_path）を書き込むと ExecutionEngine が停止する仕組みです。運用時に誤って削除/設定しないようにしてください。KILL_FLAG_CLEAR_ON_START が 1 のときは起動時に自動クリアされますが、本番では 0 を推奨します。
- ログディレクトリ作成に失敗した場合はコンソール出力のみで継続します（logging_setup の設計により安全にフォールバック）。

---

必要であれば、README の補足（API ドキュメント、ExecutionEngine の詳細設計、DB スキーマや SQL サンプル、ユニットテストの実行方法など）を追加できます。どの項目を深掘りしましょうか？