# KabuSys

日本株向け自動売買システムのモジュール群（ライブラリ + 起動スクリプト群）

このリポジトリは戦略構築（ポートフォリオ・サイズ計算）、リサーチ（ファクター計算・特徴量解析）、実行エンジン起動、監視、AI を用いたニュース評価など、実運用を想定した各コンポーネントを提供します。

バージョン: 0.1.0

---

## 主な特徴（機能一覧）

- 環境設定管理
  - .env 自動読み込み・対話式ウィザード（config_setup.py）
  - 設定検証ツール（validate_config.py）
- 実行エンジン起動スクリプト
  - run_execution.py — 実発注 / ペーパートレード切替対応（KABUSYS_ENV）
  - ペーパートレード時は MockBrokerClient を使用し DB を分離
- 監視機能
  - run_monitoring.py — SystemMonitor のポーリングループ（MONITOR_POLL_INTERVAL で間隔上書き可）
  - system / trade / risk の各モニタと Kill Switch（data/kill.flag）連動
  - 監視ログ永続化（SQLite）
- ポートフォリオ構築
  - 候補選択、等金額／スコア重み、ポジションサイズ計算、セクター制限、レジーム乗数
- リサーチ
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を使用）
  - 将来リターン、IC（Spearman）や統計サマリ
- AI（LLM）連携
  - ニュースセンチメント（news_nlp.score_news）
  - 市場レジーム判定（regime_detector.score_regime）
  - OpenAI（gpt-4o-mini 想定）を用いたスコアリング（API キー必要）
- ツール
  - paper_verification_report: ペーパートレード DB から検証レポートを生成

---

## 前提条件

- Python 3.9+
- 必要な Python パッケージ（代表例）
  - duckdb
  - psutil
  - openai
  - PyYAML（設定ファイル検証を行う場合に必要）
- SQLite（標準ライブラリで利用）
- OS: Linux / macOS / Windows（ただし一部プロセス優先度設定はプラットフォーム依存）

必要パッケージの一例インストール:
```
pip install duckdb psutil openai pyyaml
```

---

## セットアップ手順

1. リポジトリをクローン／展開し、Python 仮想環境を作成・有効化します。

2. 依存パッケージをインストールします（上記参照）。

3. 環境変数を用意します:
   - 推奨: 対話式ウィザードで .env を作成する
     ```
     python -m kabusys.config_setup
     ```
     ウィザードは .env（デフォルト: プロジェクトルート/.env）を作成・更新します。機密値はマスク表示されます。

4. 設定の検証:
   ```
   python -m kabusys.validate_config
   ```
   警告も含めて厳密にチェックしたい場合:
   ```
   python -m kabusys.validate_config --strict
   ```

5. データディレクトリ（デフォルト `data/`）やログディレクトリ（デフォルト `logs/`）は自動作成されますが、必要に応じて事前に作成してください。

---

## 環境変数（主要なもの）

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行環境
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
    - paper_trading の場合、発注はモック、DB は `data/paper_trading.db`（PAPER_TRADING_SQLITE_PATH）に分離されます。
- DB パス
  - DUCKDB_PATH: デフォルト `data/kabusys.duckdb`
  - SQLITE_PATH: 監視 DB デフォルト `data/monitoring.db`
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード用 DB（paper_trading 時に使用）
- ログ
  - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト INFO）
  - LOG_DIR: ログ出力先（デフォルト `logs/`）
- AI
  - OPENAI_API_KEY: OpenAI API キー（news_nlp, regime_detector で必要）
- 監視
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
  - KILL_FLAG_CLEAR_ON_START: 本番で Kill flag 自動クリアを有効にする場合は `1`（通常は `0` 推奨）

詳しい項目は `kabusys.config.Settings` 内のプロパティを参照してください。

---

## 使い方

### .env の作成（対話ウィザード）
```
python -m kabusys.config_setup
```
入力内容を確認して `.env` に保存します。

### 設定検証
```
python -m kabusys.validate_config
```

### 実行エンジン起動
実稼働／ペーパートレードは KABUSYS_ENV により切替。
- 本番（live）や開発（development）で起動:
```
python -m kabusys.run_execution
```
- ペーパートレード（KABUSYS_ENV=paper_trading）:
```
KABUSYS_ENV=paper_trading python -m kabusys.run_execution
```
実行スクリプトは起動時に `data/execution.pid` を扱い、`data/stop_requested.flag` により外部から優雅に停止できます。

### 監視プロセス起動
監視ループを開始します（デフォルト 60 秒間隔）。間隔は環境変数で上書き可。
```
python -m kabusys.run_monitoring
# 例: ポーリングを30秒に変更
MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
```
監視は常に（KABUSYS_ENV に関係なく）production の sqlite_path（SQLITE_PATH）を使用します。

### 停止 / Kill Switch
- Kill Switch を発動させると ExecutionEngine は `data/kill.flag` の存在を検出してシャットダウン処理を行います。
- 実行中のプロセスを即停止するためには `data/stop_requested.flag`（run_*.py で参照）を作成します（外部ツールや手動でファイルを作成）。

注意: 本番運用時は `KILL_FLAG_CLEAR_ON_START=0` を推奨。

### Paper Trading 検証レポート
ペーパートレード DB から検証レポートを生成します。
```
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
```
引数 `--db` で DB パスを指定可能。環境変数 `PAPER_TRADING_SQLITE_PATH` でも指定可。

### AI 関連
- news_nlp.score_news(conn, target_date, api_key=None)
  - ai_scores テーブルへニュースセンチメントを書き込みます。
  - OPENAI_API_KEY（または api_key 引数）が必要。
- regime_detector.score_regime(conn, target_date, api_key=None)
  - market_regime テーブルへレジーム判定を書き込みます。
  - 同様に OpenAI API キーが必要。

テスト時は内部の API 呼び出し関数（例: kabusys.ai.news_nlp._call_openai_api）をモックすることが可能です。

---

## ログ

- デフォルト出力: コンソール（stdout）と日次ローテーションファイル（logs/<app_name>.log）
- ログ設定は kabusys.utils.logging_setup.setup_logging により統一管理されます。
- 保存日数デフォルト: 30 日

---

## ディレクトリ構成（抜粋）

以下は主要なファイル/パッケージ構成の要約です（src/kabusys 配下）。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数読み込み / Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py (参照あり)
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py (参照あり)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py
  - data/ (実行時に使用されるディレクトリ: DB/flag/pid などを格納)
  - config/ (yaml 設定ファイル群: system_config.yaml 等、テンプレートは scripts 等で生成)

（上記のうち一部ファイルは実装や追加パッケージに依存するため、リポジトリ内に存在しない場合があります。）

---

## 開発上の注意 / 補足

- DuckDB を用いたリサーチ機能はローカルの DuckDB ファイル（DUCKDB_PATH）を参照します。prices_daily / raw_financials 等のテーブルが必要です。
- 実行エンジンは外部ブローカー API と接続します（kabuステーション等）。ペーパートレード時は MockBrokerClient を用いて本番と切り分けられます。
- AI（OpenAI）連携部分はネットワークエラーやレート制限を考慮してリトライ実装が含まれています。API キーの取り扱いは厳重に行ってください（.env を Git 管理しないこと）。
- 一部機能は optional な依存（PyYAML 等）で挙動が変わります。validate_config は PyYAML がない場合に YAML 検証をスキップします。

---

この README はコードベースの主要な使い方と構成を簡潔にまとめたものです。実運用やデプロイの際は .env と config/*.yaml、DB バックアップ、監視・アラート設定を十分に整備してください。必要であれば README を拡張して実行フロー図やシーケンス、さらに詳しい設定例を追加できます。