# KabuSys

日本株向け自動売買・リサーチ基盤のモジュール集 (KabuSys)。  
この README はリポジトリに含まれる主要なスクリプト・モジュール群の概要、セットアップ方法、使い方、およびディレクトリ構成を説明します。

---

## プロジェクト概要

KabuSys は日本株の自動売買と研究ワークフローを支援するライブラリ群です。主な機能としては：

- 実行エンジン (ExecutionEngine) による発注管理とペーパートレード対応
- 監視コンポーネント（System / Trade / Risk）のポーリングとアラート生成
- ポートフォリオ構築（候補選定・重み算出・ポジションサイズ計算・セクター制限）
- リサーチ（ファクター計算、特徴量探索、フォワードリターン、IC計算）
- AI によるニュースセンチメント評価（OpenAI を利用）
- 簡易的な DB 層（SQLite / DuckDB）との連携とレポート生成ツール

設計方針として、実行系と研究系を分離し、DB や外部 API へのアクセスは明示的に管理されています。ペーパートレード実行時は本番 DB と分離された専用 SQLite を使用します。

---

## 主な機能一覧

- 実行関連
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV に応じて paper_trading モードあり）
  - リスク管理（RiskManager / Reconciler / OrderManager）

- 監視関連
  - run_monitoring.py: SystemMonitor のポーリングループ起動
  - MonitoringEngine: System / Trade / Risk モニタを束ねる
  - Kill Switch（data/kill.flag）によるエンジン停止

- ポートフォリオ構築
  - 候補選び (select_candidates)
  - 等金額 / スコア加重の重み算出
  - ポジションサイズ計算（単元株で丸め、利用可能資金に基づいたスケーリング）
  - セクター集中制限、レジーム乗数

- リサーチ
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン、IC（スピアマン）計算、統計サマリ

- AI（OpenAI）
  - ニュース NLP による銘柄別センチメントスコアリング（ai.news_nlp）
  - 市場レジーム判定（ai.regime_detector）

- ユーティリティ
  - .env 対話型ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - Paper Trading 検証レポート生成ツール（tools/paper_verification_report.py）
  - ログ設定ユーティリティ、プロセス優先度設定ユーティリティ

---

## 前提条件 / 必要環境

- Python 3.10 以上（型アノテーションに `X | Y` 構文を利用）
- 推奨パッケージ（最低限の例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証に任意）
- OS: Linux / macOS / Windows（ただし一部機能はプラットフォーム依存の挙動あり）

例（venv を作って必要パッケージを入れる）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
# 任意: 開発インストール
pip install -e .
```
（requirements.txt があれば `pip install -r requirements.txt` を推奨）

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成・有効化（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

3. 依存パッケージをインストール
   ```bash
   pip install duckdb psutil openai pyyaml
   ```

4. .env の作成（対話式ウィザード）
   ```bash
   python -m kabusys.config_setup
   ```
   ウィザードは J-Quants トークンや kabu API のパスワード、DB パス、KABUSYS_ENV などを対話形式で入力して .env を作成します。
   主要な環境変数:
   - JQUANTS_REFRESH_TOKEN (必須)
   - KABU_API_PASSWORD (必須)
   - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
   - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
   - SQLITE_PATH (デフォルト: data/monitoring.db)
   - KABUSYS_ENV (development | paper_trading | live)
   - OPENAI_API_KEY (AI 機能を使う場合必須)

5. 設定検証
   ```bash
   python -m kabusys.validate_config
   # 警告を厳密扱いにする場合
   python -m kabusys.validate_config --strict
   ```

6. データディレクトリの作成（必要に応じて）
   - デフォルトでは `data/` に SQLite や PID / flag を配置します。
   ```bash
   mkdir -p data logs
   ```

---

## 使い方（よく使うコマンド）

- 実行エンジンを起動
  - 本番 / 開発 / ペーパートレードは `KABUSYS_ENV` で切替
  - ペーパートレード時は `data/paper_trading.db`（設定により上書き）を使用
  ```bash
  # 例: ペーパートレードで起動
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```

  実行の仕組み：
  - プロセス優先度を high にセット（可能な場合）
  - BrokerClientFactory によりブローカークライアントを生成（モック or 実装）
  - EngineConfig をもとに ExecutionEngine.run_session をスレッドで実行
  - 停止は `data/stop_requested.flag` を作ることで検出（実行プロセスがフラグ検知したら停止）

- 監視ループを起動
  ```bash
  # ポーリング間隔を秒で上書き（デフォルト 60 秒）
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```
  動作：
  - SystemMonitor, TradeMonitor, RiskMonitor を利用して定期チェック
  - Monitoring は環境にかかわらず本番の sqlite_path を使う点に注意
  - 停止は `data/stop_requested.flag` を作成することで検知可能

- Paper Trading 検証レポートを生成
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを指定する場合
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- AI を使ったスコアリング（プログラム的利用）
  - OpenAI API キーが必要（環境変数 `OPENAI_API_KEY`）
  - 例（Python スクリプト内で）:
    ```python
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    count = score_news(conn, target_date=date(2026, 4, 10), api_key=None)  # 環境変数を使う場合 api_key=None
    ```

注意点:
- `KABUSYS_ENV=live` は本番発注を行うため、設定を十分に確認してください。
- プロセス優先度設定や CPU affinity の設定は権限や OS により失敗する場合があり、その場合は警告がログに出ますが起動自体は継続します。

---

## 主要ファイル・CLI 一覧

- python -m kabusys.config_setup : .env を対話式で作成
- python -m kabusys.validate_config : 設定検証
- python -m kabusys.run_execution : ExecutionEngine 起動
- python -m kabusys.run_monitoring : SystemMonitor 監視ループ起動
- python -m kabusys.tools.paper_verification_report : ペーパートレード検証レポート

---

## ディレクトリ構成

リポジトリ内の主要なディレクトリとファイル（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py            — ニュース NLP (OpenAI) スコアリング
    - regime_detector.py     — 市場レジーム判定
  - monitoring/
    - monitoring_db.py       — SQLite テーブル初期化 / 永続化層
    - system_monitor.py
    - trade_monitor.py       — （実装あり）
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py       — （実装あり）
  - execution/               — 発注関連（Engine, BrokerFactory, OrderManager など）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - logging_setup.py
    - process_priority.py

補足:
- デフォルトのデータ / フラグ / PID ファイル:
  - data/monitoring.db        (SQLITE_PATH デフォルト)
  - data/kabusys.duckdb       (DUCKDB_PATH デフォルト)
  - data/paper_trading.db     (PAPER_TRADING_SQLITE_PATH デフォルト)
  - data/execution.pid
  - data/stop_requested.flag
  - data/kill.flag

---

## 運用上の注意 / トラブルシューティング

- Live 環境での運用は十分な検証と運用ルールが必要です。validate_config.py で本番向けの追加警告を出します。
- OpenAI を使う機能は API キーと通信コストが発生します。API レート制限やエラー時の挙動は各モジュールでバックオフやフェイルセーフを設けていますが、運用時は注意してください。
- ロギング
  - デフォルトで `logs/` に日次ローテーションのログファイルを出力します（logs/<app_name>.log）。ログディレクトリが作れない場合はコンソール出力のみになります。
- プロセス優先度 / CPU affinity の設定は権限不足により失敗することがあります（その場合は警告が出ます）。
- SQLite / DuckDB のパスは .env または環境変数で指定できます。必要に応じてバックアップを取ってください。

---

## 開発者向けメモ

- 型ヒントは Python 3.10 の新構文を使用しているため、古い Python では動きません。
- DuckDB 接続を受け取って SQL と Python を組み合わせるモジュールが多く、ユニットテストではインメモリ DB やモックを利用すると良いです。
- AI API 呼び出し部は外部クライアントの呼び出しを個別関数でラップしているため、ユニットテストでは該当関数をパッチして挙動をエミュレートできます。

---

必要に応じて README に追加したい箇所（例: 具体的な設定例、より詳細なアーキテクチャ図、開発フローや API ドキュメントなど）があれば教えてください。README をさらに拡張して作成します。