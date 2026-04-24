# KabuSys

日本株向けの自動売買／リサーチ基盤（プロトタイプ）

KabuSys は日本株の自動売買・リサーチ・監視を行うためのモジュール群です。注文実行エンジン、監視・アラート、ポートフォリオ構築ロジック、ファクター計算、ニュースの NLP 評価（OpenAI）などを含みます。コードは純粋関数的なパーツと、DB（SQLite / DuckDB）を使う実行コンポーネントで分離されています。

主な用途
- 本番 / ペーパートレード（分離された DB）での注文実行
- 実行状況・システム状態の監視と Kill Switch（停止フラグ）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算）
- DuckDB を使ったファクター計算・リサーチ
- OpenAI を使ったニュースセンチメント評価・レジーム判定
- Paper Trading の検証レポート生成

---

## 機能一覧

- Execution Engine
  - ブローカー抽象化（本番 / mock 切り替え）
  - 注文管理・リスク管理・リコンサイル（Reconciler）
  - ペーパートレードは本番 DB と完全分離（`data/paper_trading.db`）
- Monitoring
  - SystemMonitor：CPU / メモリ / ディスク / プロセス状態 / データ鮮度
  - TradeMonitor：注文滞留・約定異常など（trade_logs）
  - RiskMonitor：ドローダウン、ポジション上限監視、ダッシュボード更新
  - KillSwitch：条件に応じて `data/kill.flag` を書き込み ExecutionEngine を停止
  - MonitoringEngine：各モニタを束ねて定期実行、アラート通知連携
- Portfolio
  - 候補選定（スコア順）
  - 重み計算（等金額・スコア加重）
  - ポジションサイズ算出（risk_based / equal / score）、単元株丸め、aggregate cap 調整
  - セクター集約制限・レジーム乗数適用
- Research
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB）
  - 将来リターン計算、IC（スピアマン）や統計サマリー
- AI
  - ニュース NLP（OpenAI）による銘柄別センチメント計算・ai_scores への書き込み
  - レジーム検出（ETF + マクロニュース + LLM）
- ツール
  - Paper Trading 検証レポート生成スクリプト

---

## 前提 / 必要パッケージ

動作確認は Python 3.10+ を想定しています（型ヒントに `X | Y` を使用）。必須・推奨パッケージはプロジェクトに応じて追加してください（requirements.txt は同梱されていない想定）。

主な依存パッケージ（例）
- duckdb
- psutil
- openai
- PyYAML（YAML 検証用、任意）
- sqlite3（標準ライブラリ）

インストール例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境作成・依存インストール（上記を参照）

3. .env の作成（対話式ウィザード）
   ```
   python -m kabusys.config_setup
   ```
   ウィザードは J-Quants / kabu API キー、DB パス、環境（development/paper_trading/live）などを設定します。生成された `.env` は絶対にコミットしないでください。

4. 設定検証（起動前チェック）
   ```
   python -m kabusys.validate_config
   ```
   警告を厳格に扱いたい場合は `--strict` を付けます。

5. データディレクトリ作成（通常は自動で作成されますが、事前に作る場合）
   ```
   mkdir -p data logs
   ```

---

## 主要な環境変数（抜粋）

設定は .env または環境変数で行います。主な変数とデフォルト:

- JQUANTS_REFRESH_TOKEN — J-Quants API（必須）
- KABU_API_PASSWORD — kabuステーション API（必須）
- KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
- OPENAI_API_KEY — OpenAI API キー（AI 機能で必要）
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — paper_trading の約定挙動（instant|partial|never|reject、デフォルト: instant）
- LOG_LEVEL — ログレベル（デフォルト: INFO）
- LOG_DIR — ログ格納ディレクトリ（デフォルト: logs）
- MONITOR_POLL_INTERVAL — SystemMonitor ポーリング間隔（秒、デフォルト: 60）
- KILL_FLAG_CLEAR_ON_START — 本番で Kill Flag を起動時に消すか（0/1、デフォルト: 0）
- PID_FILE_PATH / KILL_FLAG_PATH — PID / kill flag のパス（デフォルトは data/ 以下）

詳細は `kabusys.config.Settings` と `config_setup.py` の説明を参照してください。

---

## 使い方

- Execution（エンジン）起動
  - ペーパートレード / 本番は KABUSYS_ENV によって切り替わります（paper_trading は MockBrokerClient、`PAPER_TRADING_SQLITE_PATH` を使用）。
  ```
  python -m kabusys.run_execution
  ```

  実行中の停止はプロセスに割り付けられた PID ファイルや `data/stop_requested.flag` の作成で検知されます。停止する場合はプロセスを終了するか、監視側の kill flag を使います。

- Monitoring（監視）起動
  ```
  python -m kabusys.run_monitoring
  ```
  MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更できます（秒単位）。監視は本番の sqlite_path を使用して system_status 等を記録します。

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  DB パスは `--db` または `PAPER_TRADING_SQLITE_PATH` 環境変数で指定できます。

- 設定の検証（起動前）
  ```
  python -m kabusys.validate_config
  ```

- 一時停止 / 強制停止用ファイル
  - `data/kill.flag` : KillSwitch が書き込むフラグ。ExecutionEngine はこれを検知して停止します（KillSwitch は条件に応じて作成）。
  - `data/stop_requested.flag` : 起動スクリプト（run_execution/run_monitoring）がループを抜けるために参照する停止フラグ。

---

## ディレクトリ構成（抜粋）

プロジェクトの主要部分（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定
  - config_setup.py           — .env 作成ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring 起動スクリプト
  - execution/                — 発注・リスク・オーダー管理等
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
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
  - utils/
    - logging_setup.py
    - process_priority.py
  - tools/
    - paper_verification_report.py

データ・ログ用ディレクトリ（プロジェクトルート）
- data/   — SQLite / PID / フラグファイルなど（デフォルト）
- logs/   — ログファイル（setup_logging が作成）

---

## 参考・注意事項

- Paper Trading は本番 DB と完全分離する設計です（`KABUSYS_ENV=paper_trading` で MockBrokerClient を使用）。
- OpenAI を用いる機能（ニューススコア、レジーム判定）は API キー（`OPENAI_API_KEY`）が必要です。API エラー時はフェイルセーフ（スコア 0 や処理スキップ）で継続する実装になっています。
- 本番環境（KABUSYS_ENV=live）では `validate_config` が注意喚起を行います。LINE 通知設定なども確認してください。
- .env は機密情報を含むため絶対にリポジトリへコミットしないでください。

---

必要であれば README を用途別（デプロイ手順、運用手順、開発者向けドキュメント）に分割して追記します。追加で記載したい項目があれば教えてください。