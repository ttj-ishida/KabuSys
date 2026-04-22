# KabuSys

日本株向けの自動売買システム（ライブラリ兼実行スクリプト群）

このリポジトリは、取引実行エンジン、監視（Monitoring）、ポートフォリオ構築・ポジションサイズ計算、リサーチ（ファクター計算）や AI を使ったニュースセンチメント評価などを含む、総合的な自動売買システムのコードベースです。

主な設計方針：
- 本番・ペーパー（紙上）取引を明確に分離（ペーパー時は MockBroker を使用し、別 DB に記録）
- DuckDB を分析用 DB、SQLite を監視・トレードログ用 DB に利用
- 環境変数 / .env による設定管理と対話式ウィザード、起動前検証ツールを提供
- OpenAI を用いたニュース NLP（任意）やレジーム判定をサポート
- プロセス優先度設定・統一ロギング・Kill Switch 等の運用ユーティリティを含む

---

## 機能一覧

- Execution Engine（発注・注文管理・リスク管理・照合）
  - 本番 / ペーパー取引モードをサポート
  - Broker クライアントの抽象化（実プロバイダ or Mock）
  - OrderManager / RiskManager / Reconciler 等の組み立て
- Monitoring（監視）
  - システムリソース監視（CPU / メモリ / ディスク）
  - データ鮮度チェック（DuckDB の prices_daily 等）
  - 取引ログ監視、滞留注文・約定異常検出
  - Kill Switch（条件を満たすと data/kill.flag を書き込む）
- ポートフォリオ構築
  - 候補選定、等金額配分 / スコア加重、セクター上限適用、レジーム乗数
  - 株数決定（単元株丸め・リスクベース配分・集約キャップ）
- リサーチ
  - ファクター計算（モメンタム／ボラティリティ／バリュー等）
  - 将来リターン、IC（Information Coefficient）などの解析ユーティリティ
- AI（任意）
  - ニュースを OpenAI でスコアリングして ai_scores に保存（score_news）
  - マクロニュース + ETF MA を使った市場レジーム判定（regime_detector）
- ユーティリティ
  - .env 対話式ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - ログ設定ユーティリティ（logging_setup）
  - プロセス優先度 / CPU affinity 設定ユーティリティ
  - Paper Trading 検証レポート生成ツール（tools/paper_verification_report）

---

## 要件（推奨）

- Python 3.10+
- SQLite（組み込み）
- 主要外部パッケージ（実行に必要な場合）
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
  - PyYAML（設定ファイル検証を行う場合、任意）
- その他、requirements.txt がある場合はそちらを参照してください。

例（最小インストール）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

3. 必要パッケージをインストール
   ```
   pip install duckdb psutil openai PyYAML
   ```
   ※ 実環境では requirements.txt が用意されていればそれを使ってください。

4. 環境変数設定（.env ファイル作成）
   - 対話式ウィザードで簡単に .env を作成できます:
     ```
     python -m kabusys.config_setup
     ```
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 主なオプション（デフォルト値は括弧内）:
     - KABUSYS_ENV (development | paper_trading | live) （default: development）
     - DUCKDB_PATH (data/kabusys.duckdb)
     - SQLITE_PATH (data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (data/paper_trading.db)
     - LOG_LEVEL (INFO)
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（アラート用、任意）
     - OPENAI_API_KEY（AI 機能を使う場合）

5. 設定検証（起動前チェック）
   ```
   python -m kabusys.validate_config
   # 警告も失敗扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

---

## 使い方（実行例）

- Execution Engine の起動（本番・ペーパーは KABUSYS_ENV で制御）
  ```
  python -m kabusys.run_execution
  ```
  - ペーパートレード時は KABUSYS_ENV=paper_trading を設定すると MockBroker を使用し、PAPER_TRADING_SQLITE_PATH に記録します。

- Monitoring の起動（監視ループ）
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）でオーバーライド可能（デフォルト 60 秒）。
  - 停止フラグファイル: data/stop_requested.flag を作成すると監視ループが終了します。

- .env の作成 / 更新
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート（SQLite DB を指定して期間フィルタ）
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を直接指定する場合
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI スコアリング（Python から直接呼ぶ例）
  ```py
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 4, 10), api_key="sk-...")
  print("書き込み件数:", written)
  conn.close()
  ```
  - OPENAI_API_KEY 環境変数を設定しておくことで api_key 引数を省略できます。

---

## 運用メモ / 重要事項

- Kill Switch（data/kill.flag）
  - RiskMonitor 等の判定で Kill Switch 条件に該当すると data/kill.flag が作成されます。ExecutionEngine は起動時やループ内でこのフラグを検出し、安全に停止します。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動で kill.flag を削除しますが、本番では 0 を推奨します。

- DB の分離
  - 本番用 monitoring DB: settings.sqlite_path（デフォルト data/monitoring.db）
  - 分離されたペーパートレード DB: settings.paper_sqlite_path（デフォルト data/paper_trading.db）
  - DuckDB は分析用（prices_daily, raw_financials, raw_news 等のテーブルが想定される）

- ログ
  - logging_setup.setup_logging を全起動スクリプトで使用して統一的に管理
  - ログディレクトリは環境変数 LOG_DIR、デフォルトは logs/
  - MONITOR のログファイル名は logs/monitoring.log、Execution は logs/execution.log

- プロセス優先度
  - 起動直後に set_process_priority("high") を実行して高優先度に設定します（プラットフォーム依存・権限によってはスキップされます）

- DB マイグレーション
  - monitoring_db.init_monitoring_db は冪等にテーブルを作成し、既存 DB に不足カラムがあれば ALTER TABLE を試みる簡易的なマイグレーション処理があります。

---

## ディレクトリ構成（抜粋）

以下は主要モジュールのツリー（src/kabusys 配下）。実際のファイルはリポジトリに合わせて確認してください。

- src/kabusys/
  - __init__.py
  - config.py                         — 環境変数 / Settings クラス
  - config_setup.py                   — .env 対話式ウィザード
  - validate_config.py                — 起動前設定検証 CLI
  - run_execution.py                  — ExecutionEngine 起動スクリプト
  - run_monitoring.py                 — Monitoring ポーリング起動スクリプト
  - utils/
    - logging_setup.py                — ログ設定ユーティリティ
    - process_priority.py             — プロセス優先度 / CPU affinity
  - execution/                         — Execution 系（OrderManager 等） *実装省略ファイルあり*
  - monitoring/
    - monitoring_db.py                — Monitoring DB ラッパー（SQLite）
    - system_monitor.py               — システム / データ鮮度監視
    - trade_monitor.py                — 取引監視（滞留注文等）
    - risk_monitor.py                 — ドローダウン / ポジション数監視
    - monitoring_engine.py            — 各 Monitor を束ねる
    - kill_switch.py                  — フラグファイル操作（kill.flag）
    - alert_manager.py                — 通知管理（LINE 等）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py                      — ニュース NLP / OpenAI 呼び出し
    - regime_detector.py               — 市場レジーム判定
  - tools/
    - paper_verification_report.py     — Paper Trading 検証レポート生成ツール

---

## よく使う環境変数（抜粋と説明）

- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABUSYS_ENV — 実行環境: development | paper_trading | live（default: development）
- DUCKDB_PATH — DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH — SQLite 監視 DB（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（default: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG, INFO, ...）
- OPENAI_API_KEY — OpenAI API キー（AI 機能利用時）
- MONITOR_POLL_INTERVAL — monitoring 起動時のポーリング間隔（秒、default: 60）
- LOG_DIR — ログ保存先ディレクトリ（default: logs/）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリア（0 or 1、default: 0）

---

## 開発・拡張のヒント

- DuckDB 上のテーブル構造（prices_daily, raw_financials, raw_news, news_symbols, ai_scores, market_regime, market_breadth 等）に合わせてデータを投入すれば、research / ai モジュールをローカルで試すことができます。
- OpenAI 呼び出し部はリトライ処理・JSON バリデーションを組み込んでいますが、ローカルテスト時はモック化（unittest.mock.patch）すると便利です（news_nlp._call_openai_api など）。
- 設定の自動読み込みはプロジェクトルートを .git または pyproject.toml から探索して行うため、テスト時に自動ロードを抑制したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使えます。

---

必要であれば、この README をベースに「運用手順書」「デプロイ手順」「単体テストの書き方」「設定値リファレンス（.env.example の生成）」などの追加ドキュメントを作成します。どのドキュメントが必要か教えてください。