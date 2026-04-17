# KabuSys

日本株向け自動売買システムのコアライブラリ群と実行用スクリプト群です。  
このリポジトリは、注文実行エンジン、監視（Monitoring）、ポートフォリオ構築・サイズ決定ロジック、ファクター計算・リサーチユーティリティ、LLM を用いたニュースセンチメント / レジーム判定機能などを含みます。

Version: 0.1.0

---

## プロジェクト概要

KabuSys は日本株自動売買に必要なコンポーネントをモジュール化したライブラリ / 実行環境です。主な設計方針は以下です。

- 本番・ペーパートレード（paper_trading）を環境変数で切り替え可能。
- DB（SQLite / DuckDB）を用いた永続化・分析基盤を提供。
- 監視コンポーネントにより稼働状況・注文状況を監視し、必要時に Kill Switch（フラグファイル）で ExecutionEngine を停止可能。
- ニュースを LLM（OpenAI）でスコアリングし、レジーム判定やファクターに活用可能。
- ポートフォリオ構築・ポジションサイジングの純粋関数群を提供（副作用なし、単体テストしやすい）。

---

## 主な機能一覧

- 実行エンジン起動（run_execution.py）
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、本番 DB と分離（data/paper_trading.db）。
  - 実行中は PID ファイルを書き込み、外部から停止フラグで制御可能。

- 監視（run_monitoring.py / MonitoringEngine）
  - システム状態（CPU・メモリ・ディスク、プロセス生存）監視
  - 注文滞留や約定異常価格の検出
  - ドローダウン・ポジション上限監視と Kill Switch 書き込み
  - SQLite 監視 DB（monitoring_db）へのロギング

- ポートフォリオ構築
  - 候補選定（スコア降順）、等配分 / スコア加重、リスクベース配分
  - セクター集中制限、レジーム乗数
  - 単元株（lot）丸め、aggregate cap によるスケールダウン

- リサーチ / ファクター計算
  - モメンタム、ボラティリティ、バリュー等のファクター計算（DuckDB 経由）
  - 将来リターン計算・IC（Information Coefficient）等のユーティリティ

- LLM 統合（OpenAI）
  - ニュースセンチメント（news_nlp.score_news）
  - マクロニュース + ETF MA を組み合わせた市場レジーム判定（regime_detector.score_regime）
  - API 呼び出しはリトライ・フェイルセーフを備え、部分失敗時にも既存データを保護

- CLI ユーティリティ
  - 環境設定ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成（tools.paper_verification_report）

---

## 前提条件 / 依存ライブラリ

最低限の実行に必要な主なライブラリ（環境に応じて適宜インストールしてください）:

- Python 3.9+
- duckdb
- psutil
- openai
- PyYAML（config YAML の厳密な検証に必要。必須ではない）
- sqlite3（標準ライブラリ）

例（pip）:
```
pip install duckdb psutil openai pyyaml
```

※ requirements.txt が無い場合は上のパッケージを手動で導入してください。

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate    # macOS / Linux
   .venv\Scripts\activate       # Windows (PowerShell / CMD)
   ```

3. 必要パッケージをインストール
   ```
   pip install duckdb psutil openai pyyaml
   ```

4. .env の作成（対話式ウィザード推奨）
   ```
   python -m kabusys.config_setup
   ```
   ウィザードが .env を生成します。重要な必須項目:
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD

5. 設定検証
   ```
   python -m kabusys.validate_config
   ```
   --strict オプションで警告も失敗扱いにできます。

6. data ディレクトリの確認（起動時に自動作成される場合もあります）
   - デフォルトの DB / PID / フラグパス: data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db, data/execution.pid, data/kill.flag

---

## 実行方法（使い方）

- 実行エンジン（ExecutionEngine）を起動
  - 通常起動（KABUSYS_ENV に従う）
    ```
    python -m kabusys.run_execution
    ```
  - KABUSYS_ENV=paper_trading に設定すると MockBrokerClient を使い paper_trading DB に記録されます。
    ```
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    ```

- 監視ループを起動
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数でポーリング間隔を上書きできます:
    ```
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```
    デフォルトは 60 秒。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  または PAPER_TRADING_SQLITE_PATH 環境変数で DB パスを指定できます。

- 設定ウィザード / 検証
  ```
  python -m kabusys.config_setup
  python -m kabusys.validate_config
  ```

- プログラムから利用（例）
  - ニューススコアリング（プログラム的に呼ぶ）
    ```py
    from kabusys.ai import score_news
    import duckdb
    conn = duckdb.connect("data/kabusys.duckdb")
    from datetime import date
    score_news(conn, date(2026, 4, 11), api_key="sk-...")
    ```
  - リサーチ関数等もモジュールを直接 import して使用できます（duckdb 接続を渡す設計）。

---

## 主要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (監視 DB、デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB、デフォルト: data/paper_trading.db)
- OPENAI_API_KEY (LLM 機能用)
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID (任意、アラート通知用)
- MONITOR_POLL_INTERVAL (run_monitoring のポーリング間隔, 秒。デフォルト 60)
- PAPER_FILL_MODE (paper_trading のフィルモード: instant | partial | never | reject)

---

## Kill Switch / 停止フラグについて

- 監視コンポーネントは条件に応じて data/kill.flag を書き込みます。ExecutionEngine は起動時・稼働中にこのフラグを検知して安全に停止します。
- ExecutionEngine の停止を外部から指示したい場合は data/kill.flag を作成してください（KillSwitch クラスはフラグ書き込み時に理由を保存します）。
- 監視停止（手動）用フラグ: data/stop_requested.flag（run_monitoring/run_execution がチェックします）。

---

## データベースと初期化

- run_execution / run_monitoring 起動時に monitoring 用 SQLite DB は自動的に初期化（テーブル作成・マイグレーション）されます（monitoring_db.init_monitoring_db）。
- DuckDB は分析用に使用します（prices_daily / raw_financials 等のテーブルが想定されます）。DuckDB ファイルパスは DUCKDB_PATH で設定。

---

## ディレクトリ構成（主要ファイルのみ抜粋）

src/kabusys/
- __init__.py
- config.py                     — 環境変数 / .env 読み込み・Settings
- config_setup.py               — .env 対話式ウィザード
- validate_config.py            — 設定検証 CLI
- run_execution.py              — ExecutionEngine 起動スクリプト
- run_monitoring.py             — SystemMonitor ポーリング起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py                 — ニュース NLP スコアリング（OpenAI）
  - regime_detector.py          — 市場レジーム判定（ETF MA + LLM）
- monitoring/
  - monitoring_db.py            — SQLite 永続化層
  - monitoring_engine.py        — 各 Monitor を束ねる
  - system_monitor.py           — システム状態 / データ鮮度監視
  - trade_monitor.py            — 注文滞留 / 約定異常監視
  - risk_monitor.py             — ドローダウン / ポジション上限監視
  - kill_switch.py              — Kill Switch 実体（フラグファイル）
  - alert_manager.py            — （アラート送信ロジック。未表示部分あり）
- execution/                    — 注文実行関連（OrderManager, ExecutionEngine 等）
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- tools/
  - paper_verification_report.py
- utils/
  - process_priority.py         — プロセス優先度 / CPU affinity 設定ユーティリティ

data/（実行時に作成）
- kabusys.duckdb
- monitoring.db
- paper_trading.db
- execution.pid
- kill.flag
- stop_requested.flag

---

## 開発者向けメモ / 注意事項

- LLM（OpenAI）連携機能を使う場合は OPENAI_API_KEY を設定してください。API 呼び出しはリトライやフェイルオープンの仕組みを持ちますが、API 未設定だと明示的エラーになります（score_news, score_regime 等）。
- run_execution は実行前に kill.flag が立っていると起動を中止します（安全措置）。
- process priority / CPU affinity を設定するには psutil が必要です。権限や OS により設定に失敗する場合がありますが、失敗時は警告を出して無視します。
- DuckDB のテーブルスキーマ（prices_daily / raw_financials / raw_news 等）は外部データ取り込みスクリプト等で準備する想定です。
- .env は絶対にリポジトリにコミットしないでください（config_setup のヘッダーにも注意喚起あり）。

---

必要であれば、README に「実行例」「設定項目の詳細（全キー一覧）」「Dev 環境でのユニットテスト／CI 設定」などの追記もできます。どの追加情報が欲しいか教えてください。