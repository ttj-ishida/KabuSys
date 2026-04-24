# KabuSys

日本株自動売買システム（KabuSys）のコードベース向け README。  
本書はリポジトリ内の主要コンポーネントの概要、セットアップ、使い方、ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買（Execution）と監視（Monitoring）、リサーチ／ポートフォリオ構築、そして AI を活用したニュース・レジーム判定機能を備えたシステムです。  
設計方針として以下を重視しています。

- 本番（live）／ペーパートレード（paper_trading）を区別した運用
- DuckDB（分析用）と SQLite（監視・発注ログ）による二層データ管理
- LLM（OpenAI）を使ったニュースセンチメント／レジーム判定（フェイルセーフ実装）
- 監視モジュールによるリスク検知と Kill Switch（フラグファイルによる安全停止）
- 設定用ウィザードと検証ツールによる起動前チェック

バージョン: 0.1.0（パッケージ識別子: `kabusys`）

---

## 主な機能一覧

- Execution（発注エンジン）
  - 本番/ペーパートレード切替（`KABUSYS_ENV`）
  - ブローカークライアントの抽象化（Mock を含む）
  - リスク管理（ポジション上限、利用率、最大ドローダウン等）
- Monitoring（監視）
  - システムリソース監視（CPU/メモリ/ディスク）
  - データ鮮度チェック（DuckDB 内の prices_daily 等）
  - 取引ログ・リスクログの収集（SQLite）
  - Kill Switch（閾値超過で `data/kill.flag` を書き込み）
- Portfolio（銘柄選定・配分・ポジションサイズ）
  - 候補選定、等金額・スコア加重、リスクベースのポジションサイズ算出
  - セクター上限適用・レジーム乗数の適用
- Research（ファクター計算・特徴量解析）
  - モメンタム、ボラティリティ、バリュー等を DuckDB で計算
  - 将来リターン、IC（情報係数）など解析ユーティリティ
- AI（ニュース NLP / レジーム判定）
  - OpenAI (gpt-4o-mini 等) を使ったニュースセンチメントの集約・書き込み
  - マクロニュースと ETF の MA200 を組み合わせた市場レジーム判定
- ツール類
  - 対話式 `.env` 作成ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成ツール

---

## 前提 / 依存関係

推奨 Python バージョン: 3.10 以上（ソース内で `X | Y` 等の構文を使用）  
主な Python パッケージ（実行環境に応じて選択）:

- duckdb
- psutil
- openai
- （任意）PyYAML — `validate_config` の YAML 検証に使用

※ requirements.txt がある場合はそれを使用してください。なければ上記を pip でインストールしてください。

例:
```
python -m pip install "duckdb" "psutil" "openai" "PyYAML"
```

---

## セットアップ手順

1. リポジトリをクローン／配置
2. 仮想環境を作成・有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Linux / macOS
   .venv\Scripts\activate     # Windows
   ```
3. 依存パッケージをインストール
   ```
   pip install -r requirements.txt    # あれば
   # ない場合:
   pip install duckdb psutil openai PyYAML
   ```
4. 初期設定（対話式ウィザード）
   ```
   python -m kabusys.config_setup
   ```
   - 必須: `JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD`
   - 環境: `KABUSYS_ENV` → `development` / `paper_trading` / `live`
   - データベースパスなどはデフォルト（data/ 以下）を推奨
5. 設定検証（起動前チェック）
   ```
   python -m kabusys.validate_config
   ```
   - `--strict` を付けると警告も失敗扱いになります
6. データディレクトリ / ログディレクトリ確認
   - デフォルト DB: `data/kabusys.duckdb`, `data/monitoring.db`
   - ログ: `logs/` 以下にアプリ名ごとの日次ローテーションログが出力されます

---

## 使い方（主要スクリプト）

- 環境変数設定の注意点
  - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
  - 代表的な変数:
    - KABUSYS_ENV: development | paper_trading | live
    - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
    - SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
    - PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（paper_trading 時に使用）
    - LOG_LEVEL: ログレベル（INFO 等）
    - OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
    - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）

- ExecutionEngine の起動
  - 本番/ペーパートレードは `KABUSYS_ENV` で切替
  - 起動:
    ```
    python -m kabusys.run_execution
    ```
  - 実行時に `data/execution.pid` を使って PID を管理し、停止は `data/stop_requested.flag` によって行います
  - ペーパートレード（KABUSYS_ENV=paper_trading）では専用 SQLite（デフォルト `data/paper_trading.db`）に記録され、本番 DB と分離されます

- Monitoring の起動
  - 起動:
    ```
    python -m kabusys.run_monitoring
    ```
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能（デフォルト 60）
  - 監視は常に監視用 sqlite（Settings.sqlite_path）に対して書き込みを行います
  - Kill Switch: `data/kill.flag` が書かれると ExecutionEngine に停止シグナルを与えます（KillSwitch実装）

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルト DB は `PAPER_TRADING_SQLITE_PATH` 環境変数または `data/paper_trading.db`

- AI / レジーム判定 / ニューススコア
  - ライブラリ API として以下を利用できます（サンプル）:
    - ニューススコア付与: `kabusys.ai.score_news(conn, target_date, api_key=None)`
    - レジーム判定: `kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)`
  - 実行には `OPENAI_API_KEY` が必要（引数でも渡せます）
  - 直接使う場合は DuckDB 接続（duckdb.connect）を渡して呼び出します

---

## 運用上の注意点

- Kill Switch / Stop Flag
  - Kill Switch は `data/kill.flag` に理由を書き込むことで Execution を停止させます。KillSwitch は `monitoring` 側の評価で書き込みます。
  - 手動で Execution を停止する（または再起動を防ぐ）には `data/stop_requested.flag` を利用します（run_*.py が存在を検知して終了します）。
- ログ
  - 共通ロギング設定: `kabusys.utils.logging_setup.setup_logging` を使用。ログは `logs/<app_name>.log` に日次ローテーションで保存されます（デフォルト 30 日分保持）。
- データベースマイグレーション
  - `monitoring_db.init_monitoring_db` は冪等でテーブル作成と簡易マイグレーション（カラム追加）を行います。
- LLM 呼び出しの安全性
  - OpenAI 呼び出しはリトライ／フォールバックが組み込まれており、API 失敗時は安全側の既定値で継続する設計です。

---

## ディレクトリ構成（抜粋）

リポジトリの主要ファイル／ディレクトリ（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定管理（自動 .env ロード）
  - config_setup.py                — .env 対話ウィザード
  - validate_config.py             — 設定検証 CLI
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - run_monitoring.py              — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート
  - ai/
    - news_nlp.py                   — ニュース NLP（OpenAI 連携）
    - regime_detector.py            — 市場レジーム判定（OpenAI 連携）
  - monitoring/
    - monitoring_db.py              — SQLite 永続層（監視ログ）
    - monitoring_engine.py          — Monitor を束ねるループ
    - system_monitor.py             — システム状態監視
    - trade_monitor.py              — 注文関連監視（存在）
    - risk_monitor.py               — ドローダウン/ポジション上限監視
    - kill_switch.py                — Kill Switch 実装
    - alert_manager.py              — アラート送信（存在）
  - execution/
    - execution_engine.py           — 発注エンジン（存在）
    - order_manager.py              — 注文管理
    - order_repository.py           — 注文・ログ保存
    - reconciler.py                 — 注文整合処理
    - broker_factory.py             — ブローカークライアント生成
    - risk_manager.py               — 実稼働時のリスク管理
  - portfolio/
    - portfolio_builder.py          — 候補選定 / 重み計算
    - position_sizing.py            — 株数算出・スケーリング
    - risk_adjustment.py            — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py            — ファクター計算（momentum/value/volatility）
    - feature_exploration.py        — 将来リターン / IC / 統計
  - utils/
    - logging_setup.py              — ログ共通設定
    - process_priority.py           — プロセス優先度 / CPU affinity
  - data/                            — 実行時に生成される（logs・DB・flags）

（実際のツリーはリポジトリを参照してください。上は主要ファイルの抜粋です）

---

## よくあるコマンドまとめ

- .env を作る（対話式）
  ```
  python -m kabusys.config_setup
  ```
- 設定を検証
  ```
  python -m kabusys.validate_config
  ```
- Execution 起動
  ```
  python -m kabusys.run_execution
  ```
- Monitoring 起動
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
- Paper 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

## トラブルシューティング / Tips

- Python バージョンエラーが出る場合は 3.10+ を使用してください（型注釈の新構文など）。
- validate_config で YAML 検証がスキップされた場合は PyYAML をインストールしてください。
- OpenAI を使うスクリプトを実行する場合は `OPENAI_API_KEY` を設定するか、関数呼び出し時に api_key を渡してください。
- ログディレクトリ（デフォルト `logs/`）の作成に失敗するとファイル出力が無効化され、警告がコンソールに出ます。パーミッションを確認してください。
- Kill Switch / stop flag は `data/` 配下のファイルで管理されます。手動で削除・クリアする場合は注意して行ってください。

---

必要があれば、README に動作フローチャート、設定例（.env.example の抜粋）、または各モジュールの詳細ドキュメント（ExecutionEngine のシーケンス、DB スキーマの詳細など）を追加で作成します。どの部分を詳しくしたいか教えてください。