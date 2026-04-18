# KabuSys

日本株向けの自動売買 / 研究プラットフォームのコアライブラリ群です。  
このリポジトリには監視・実行・ポートフォリオ構築・ファクター研究・AI（ニュース NLP / レジーム判定）等の主要コンポーネントが含まれます。

> 注意: README はこのコードベースに含まれるモジュール群の利用方法とセットアップ手順をまとめたものです。実行時の本番設定（APIキー・パスワード等）は決してリポジトリにコミットしないでください（.env を使用します）。

---

目次
- プロジェクト概要
- 主な機能
- 要求環境 / 依存関係
- セットアップ手順
- 使い方（実行コマンド例）
- 環境変数（主な項目）
- ディレクトリ構成
- 運用上の注意

---

## プロジェクト概要

KabuSys は以下の機能を組み合わせた日本株向けの自動売買・研究基盤です（ライブラリ＋起動スクリプト）：

- ExecutionEngine（発注エンジン）起動スクリプト（run_execution）
  - 本番とペーパートレードを区別して専用 DB にアクセス
- Monitoring（監視）コンポーネント（run_monitoring / MonitoringEngine）
  - システム状態、注文ログ、リスク（ドローダウン／ポジション数）を監視
  - Kill Switch による緊急停止シグナル発行
- 研究モジュール（research）
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 特徴量探索（Forward returns, IC 等）
- ポートフォリオ構築モジュール（portfolio）
  - 候補選定・重み付け・ポジションサイズ決定・セクターキャップ等
- AI モジュール（ai）
  - ニュース NLP による銘柄センチメント（OpenAI 使用）
  - マクロ + ETF MA に基づく市場レジーム判定
- 運用ツール（tools）
  - Paper Trading の検証レポート生成スクリプト
- 設定管理 / 検証 / ウィザード（config_setup, validate_config）
- ロギング・プロセス優先度ユーティリティなどのユーティリティ群（utils）

---

## 主な機能一覧

- 実行エンジンの起動 / 停止管理（PID ファイル、stop フラグ）
- 監視ループ（CPU/MEM/DISK、データ鮮度、Execution プロセス存在確認）
- リスクモニタ（ドローダウン・ポジション上限検出）と kill.flag 発行
- 取引ログ / ダッシュボード / リスクログの SQLite 永続化（monitoring_db）
- DuckDB を用いた分析・ファクター計算（prices_daily, raw_financials 等を想定）
- OpenAI を用いたニュースセンチメント（batch + JSON mode、リトライロジック）
- Paper Trading 向けの検証レポート生成（注文成立率・レイテンシ等）
- 対話式 .env 作成ウィザードと起動前の設定検証 CLI

---

## 要求環境 / 依存関係

- Python 3.10+
- 必須ライブラリ（実行する機能によって変わります）
  - duckdb
  - psutil
  - openai (AI 機能を使用する場合)
- 任意 / 推奨
  - PyYAML（config/*.yaml の検証に使用。なくても動作するが検証が省略されます）

インストール例（仮想環境内）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

（requirements.txt があれば `pip install -r requirements.txt` を推奨します。）

---

## セットアップ手順

1. リポジトリをクローンして Python 仮想環境を作る
2. 必要パッケージをインストール（上記参照）
3. .env の用意
   - 対話式ウィザードで作成:
     ```bash
     python -m kabusys.config_setup
     ```
   - もしくは手動でルートに `.env` を配置（.env.example を参考に）
   - 重要: `.env` は絶対に Git にコミットしないでください
4. 起動前に設定検証:
   ```bash
   python -m kabusys.validate_config      # 警告は表示
   python -m kabusys.validate_config --strict  # 警告も FAIL 扱い
   ```

---

## 使い方

以下は典型的な起動・利用コマンド例です。

- ExecutionEngine を起動する
  - 本番 / ペーパートレードの振る舞いは KABUSYS_ENV に依存します。
  - 起動:
    ```bash
    python -m kabusys.run_execution
    ```
  - エンジンはデーモン風にスレッドで動き、data/execution.pid に PID を書きます。
  - 停止は data/stop_requested.flag の作成、または kill.flag による停止等で制御されます。

- Monitoring を起動する
  - ポーリング間隔は環境変数で上書き可（秒、デフォルト 60 秒）
    ```bash
    export MONITOR_POLL_INTERVAL=30
    python -m kabusys.run_monitoring
    ```
  - 監視は常に本番用の sqlite_path を参照してログを残します（設定に応じて path を指定）。

- Paper Trading 検証レポート生成
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを明示する場合:
  python -m kabusys.tools.paper_verification_report --db /path/to/data/paper_trading.db
  ```

- AI 系（ニューススコア / レジーム判定）
  - OpenAI API キーが必要（環境変数 OPENAI_API_KEY または関数引数で指定）
  - プログラムとして呼び出す例（Python REPL 等）:
    ```python
    from kabusys.ai.news_nlp import score_news
    from kabusys.ai.regime_detector import score_regime
    import duckdb
    conn = duckdb.connect("data/kabusys.duckdb")
    # ニューススコアを書き込む（target_date: datetime.date）
    n = score_news(conn, target_date, api_key="sk-xxx")
    # レジーム判定
    r = score_regime(conn, target_date, api_key="sk-xxx")
    ```

- .env ウィザードを実行する
  ```bash
  python -m kabusys.config_setup
  ```

- 設定を検証する
  ```bash
  python -m kabusys.validate_config
  ```

---

## 環境変数（主な項目）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

主な任意 / デフォルト:
- KABUSYS_ENV — 実行環境（development | paper_trading | live）。デフォルト: development
  - paper_trading: MockBroker を利用し data/paper_trading.db に記録（本番 DB と分離）
  - live: 本番運用（実際に発注）
- DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- OPENAI_API_KEY — OpenAI 呼び出しに必要（AI 機能を使う場合）
- MONITOR_POLL_INTERVAL — Monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（開発用: "1"）

その他:
- LOG_DIR — ログ出力先ディレクトリ（デフォルト: logs/）
- PID_FILE_PATH / KILL_FLAG_PATH — PID / Kill フラグのパス（Settings 参照）

注意:
- KILL_FLAG_CLEAR_ON_START を本番で "1" にするのは危険です（Kill Switch を自動解除してしまうため）。live では "0" 推奨。
- .env の自動ロードはデフォルトで有効（プロジェクトルートを .git または pyproject.toml で検出）。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要モジュール一覧（抜粋）です。

- src/
  - kabusys/
    - __init__.py
    - config.py                 — 設定 / .env ロードロジック
    - config_setup.py           — .env 対話式ウィザード
    - validate_config.py        — 起動前設定検証 CLI
    - run_execution.py          — ExecutionEngine 起動スクリプト
    - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
    - tools/
      - paper_verification_report.py  — Paper Trading 検証レポート
    - ai/
      - news_nlp.py             — ニュース NLP（OpenAI 経由）
      - regime_detector.py      — 市場レジーム判定（ETF MA + マクロ）
    - research/
      - factor_research.py      — モメンタム / バリュー / ボラティリティ
      - feature_exploration.py  — 将来リターン / IC / 統計サマリ
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py (参照あり)
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
      - alert_manager.py (参照あり)
    - utils/
      - logging_setup.py        — 共通ログ設定
      - process_priority.py     — プロセス優先度設定ユーティリティ

補足:
- data/（プロジェクトルート）: DB ファイル・PID・flag 等を格納する想定ディレクトリ
- logs/: ログファイル（デフォルト daily ローテーションで保存）

---

## 運用上の注意 / ベストプラクティス

- .env を絶対にリポジトリにコミットしないこと。
- 本番環境（KABUSYS_ENV=live）では設定を慎重に確認してください。validate_config は live 用のガードや警告を出します。
- Kill Switch の仕組み: risk monitor が条件を満たすと data/kill.flag を書き込み、ExecutionEngine を安全に停止させます。Kill Switch を不用意に無効化しないでください（KILL_FLAG_CLEAR_ON_START）。
- Logging: setup_logging() により stdout と日次ローテートのファイルに記録されます。ログディレクトリは環境によって書込み権限に注意してください。
- OpenAI の利用: レート制限や API エラーに対してリトライが入る実装ですが、API キー管理 / コスト管理は運用者側で行ってください。
- DB マイグレーション: monitoring_db.init_monitoring_db() は簡易的なマイグレーション（カラム追加）を行いますが、大規模変更は別途マイグレーション手順を用意してください。

---

もし README に追加したい情報（例: 実行パラメータの詳細、ExecutionEngine の API、trade_monitor の仕様、デバッグ手順など）があれば教えてください。必要に応じてセクションを拡張してより具体的な操作手順や例を追記します。