# KabuSys

日本株向け自動売買システム（ライブラリ兼起動スクリプト群）

このリポジトリは、シグナル生成・ポートフォリオ構築・発注エンジン・監視・研究ツール・AI を組み合わせた自動売買プラットフォームの一部です。  
README は簡易の運用ガイドおよび主要機能の概要を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は以下の機能群を持つモジュール式の自動売買システムです。

- 戦略（ファクター計算 / 特徴量探索）: duckdb 上の時系列データを使ってファクターを計算
- ポートフォリオ構築: 候補選定、配分（等配分／スコアベース／リスクベース）、ポジションサイズ計算
- ExecutionEngine（発注）: 実際の発注処理（paper_trading モードではモックブローカー）
- Monitoring（監視）: システム状態、注文ログ、リスク（ドローダウン等）を定期的にチェック
- Kill Switch: 条件を満たすとフラグファイルを書き ExecutionEngine を停止
- AI モジュール: ニュースの NLP スコアリング、レジーム判定（OpenAI API を使用）
- 運用ツール: Paper Trading 検証レポート生成など

主要な設計方針として、ルックアヘッドバイアス回避、フェイルセーフ（API失敗時は安全側にフォールバック）、DB・ログの明確な分離が挙げられます。

---

## 主な機能一覧

- 設定管理
  - .env 自動ロード（プロジェクトルートの `.env`, `.env.local`）
  - 対話式設定ウィザード: python -m kabusys.config_setup
  - 設定検証 CLI: python -m kabusys.validate_config
- 実行系
  - run_execution: 発注エンジン起動スクリプト（KABUSYS_ENV=paper_trading 時は MockBroker、専用 DB を使用）
  - run_monitoring: SystemMonitor ポーリングループ（MONITOR_POLL_INTERVAL 環境変数で間隔指定）
- 監視
  - system_monitor / trade_monitor / risk_monitor を束ねる MonitoringEngine
  - kill_switch による安全停止（data/kill.flag）
  - MonitoringDB: SQLite を用いた監視ログ永続化（スキーマは init_monitoring_db で自動作成／マイグレーション）
- ポートフォリオ
  - 候補選定、等配分／スコア配分、リスク調整（セクターキャップ、レジーム乗数）
  - ポジションサイズ計算（単元株丸め、aggregate cap 調整）
- 研究（research）
  - ファクター計算（momentum/value/volatility）
  - 将来リターン、IC 計算、統計サマリー等
- AI（OpenAI）
  - news_nlp: ニュースのセンチメントを LLM でスコア化し ai_scores に保存
  - regime_detector: ETF とマクロニュースを組み合わせて市場レジームを判定
- 運用ツール
  - tools/paper_verification_report.py: ペーパートレード結果を検証するレポート生成

---

## 前提（依存関係）

最低限必要なパッケージ（抜粋）:

- Python 3.9+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML (config ファイル検証時に必要、任意)

requirements.txt はリポジトリに含めていないため、環境に合わせてインストールしてください。

例:
```
pip install duckdb psutil openai pyyaml
```

---

## セットアップ手順（クイックスタート）

1. リポジトリをクローン / ソースを配置

2. 仮想環境を作成して依存パッケージをインストール

3. .env の作成（対話式推奨）
   - 対話式ウィザード:
     ```
     python -m kabusys.config_setup
     ```
     ウィザード実行後、`.env` が作成されます。
   - 手動設定:
     - `.env.example` を参照して `.env` を作成
   - 重要な環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - OPENAI_API_KEY（AI 機能を使用する場合）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB。デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE（paper_trading の約定挙動: instant|partial|never|reject）
     - LOG_LEVEL（デフォルト: INFO）

4. 設定検証
   ```
   python -m kabusys.validate_config
   ```
   問題がある場合はメッセージに従って修正してください。`--strict` を付けると警告も失敗扱いになります。

5. データディレクトリ・ログディレクトリの確認
   - デフォルトで `data/` と `logs/` を使用します。`LOG_DIR` 環境変数で変更可能です。

---

## 起動・使い方

- ExecutionEngine（発注エンジン）起動:
  - 本番／開発／紙トレードは KABUSYS_ENV に依存します。
  - 例（paper_trading モードを .env に設定済みの場合）:
    ```
    python -m kabusys.run_execution
    ```
  - 実行中に停止させる方法:
    - `data/stop_requested.flag` を作成すると run_execution/run_monitoring のループが終了します。
    - Monitoring の KillSwitch は `data/kill.flag` を書き、ExecutionEngine の処理を停止させます（KillSwitch の理由テキストを含む）。

- Monitoring（監視ループ）起動:
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能（デフォルト: 60）。
  - run_monitoring は常に本番用の sqlite_path を使用（環境にかかわらず monitoring.db を参照します）。

- Paper Trading（分離された DB）
  - KABUSYS_ENV=paper_trading の場合、run_execution は paper_trading 用の SQLite（PAPER_TRADING_SQLITE_PATH）を使用し、本番 DB と完全に分離します。

- ログ
  - `kabusys.utils.logging_setup.setup_logging()` により stdout と日次ローテートファイル（logs/<app_name>.log）へ出力されます。
  - LOG_LEVEL は `.env` の LOG_LEVEL または環境変数で制御可能。

- 設定自動ロード
  - `kabusys.config` はプロジェクトルート（.git または pyproject.toml）を探して `.env` / `.env.local` を自動で読み込みます。
  - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

---

## 運用上のファイル・フラグ

- data/stop_requested.flag
  - run_monitoring/run_execution がループ終了判定に使う（停止要求）。
- data/kill.flag
  - Monitoring の KillSwitch が安全停止理由を書き込む。ExecutionEngine はこれを検出して停止する。
- data/execution.pid
  - ExecutionEngine の PID ファイル（run_execution が使用）。
- DB ファイル（デフォルト）
  - DuckDB: data/kabusys.duckdb
  - Monitoring SQLite: data/monitoring.db
  - Paper trading SQLite: data/paper_trading.db

---

## AI 機能（OpenAI）について

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news + news_symbols を元に銘柄ごとに OpenAI に問い合わせてスコアを作成し、ai_scores テーブルへ書き込みます。
  - 必要: OPENAI_API_KEY（引数からも渡せます）
  - バッチサイズやリトライロジック、レスポンス検証を組み込んでいます。
- レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の MA200 乖離とマクロニュースの LLM センチメントを合成して 'bull'/'neutral'/'bear' を判定します。
  - API 失敗時はマクロセンチメントを 0.0 として継続するフェイルセーフがあります。

注意: OpenAI API を使用する機能は API キーの管理とコストに注意して運用してください。

---

## ユーティリティ・ツール

- Paper Trading 検証レポート生成:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルト DB: data/paper_trading.db（`--db` で指定可）
  - 稼働率、注文成功率、レイテンシ（P95）などを算出して PASS/FAIL 判定を出力します。

---

## 主要なコマンドまとめ

- 設定ウィザード:
  ```
  python -m kabusys.config_setup
  ```
- 設定検証:
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```
- 発注エンジン起動:
  ```
  python -m kabusys.run_execution
  ```
- 監視起動:
  ```
  python -m kabusys.run_monitoring
  ```
- Paper trading 検証レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
  ```

---

## 重要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- OPENAI_API_KEY — AI 機能用
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — 監視用 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 DB（デフォルト: data/paper_trading.db）
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）
- PAPER_FILL_MODE — paper_trading の fill 挙動（instant/partial/never/reject）
- KILL_FLAG_CLEAR_ON_START — 本番での自動クリア禁止推奨（0 が推奨）

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数・自動 .env ロード
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前チェック CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring 起動スクリプト
  - monitoring/
    - monitoring_db.py — SQLite スキーマと DB ラッパー
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
  - execution/  (発注関連モジュール)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py

補足: 実際のリポジトリにはさらに細かなモジュール（ブローカーファクトリ、order_manager、reconciler、risk_manager など）が含まれます。上記は主要ファイルの概観です。

---

## 運用上の注意

- 本番（KABUSYS_ENV=live）では LINE 通知や kill switch の設定、KILL_FLAG_CLEAR_ON_START 等の設定を慎重に行ってください。
- paper_trading は本番 DB とは分離されますが、.env のパス設定を必ず確認してください。
- ログディレクトリ／DB の親ディレクトリが存在しない場合、validate_config は警告を出します。起動時に自動作成されるケースもありますが事前に確認してください。
- OpenAI 等の外部 API 呼び出しはリトライやフェイルセーフを備えますが、料金やレート制限に注意して運用してください。

---

この README はコードベースの主要な部分を元に作成しています。詳細な設計や運用手順、追加の設定ファイル（config/*.yaml）については該当するドキュメントやソースコードの docstring を参照してください。必要であれば、起動手順や設定項目のテンプレートをさらに詳述したドキュメントを作成します。