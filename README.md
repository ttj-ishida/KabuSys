# KabuSys

日本株自動売買システム（KabuSys）の README。  
このリポジトリは、戦略研究・ファクター計算・ポートフォリオ構築・発注エンジン・監視機能・AI を組み合わせた自動売買基盤の実装を含みます。

---
## プロジェクト概要
KabuSys は日本株向けの自動売買基盤です。主な目的は以下です。

- DuckDB を使った研究（ファクター/特徴量算出・IC評価）
- ポートフォリオ構築（候補選定、重み算出、ポジションサイズ計算）
- 発注エンジン（本番 / ペーパートレードを分離）
- 監視サブシステム（システム状態、注文ログ、リスク監視、Kill Switch）
- OpenAI を使ったニュース NLP・市場レジーム検出の統合
- 運用支援ツール（設定ウィザード、設定検証、ペーパートレード検証レポート）

各機能はモジュール単位で分割され、テスト・研究・運用それぞれで使えるよう設計されています。

---
## 主な機能一覧
- 設定管理
  - .env 自動ロード（.env / .env.local）
  - 対話式設定ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
- 発注・実行
  - ExecutionEngine（run_execution 起動スクリプト）
  - paper_trading 環境の完全分離（data/paper_trading.db など）
  - ブローカークライアントファクトリ（Mock 対応）
  - OrderManager / RiskManager / Reconciler
- 監視（Monitoring）
  - SystemMonitor（CPU/メモリ/Disk、データ鮮度、プロセス生存確認）
  - TradeMonitor（注文滞留、約定異常等の検知）
  - RiskMonitor（ドローダウン、ポジション上限監視）
  - KillSwitch（危険時に data/kill.flag を書き込み ExecutionEngine を停止）
  - MonitoringEngine（監視のポーリングループ）
  - SQLite を使った永続化（監視ログ・トレードログ・ダッシュボード等）
- ポートフォリオ構築
  - 候補選定（スコア順ソート）
  - 重み計算（等金額・スコア加重）
  - セクター制限（apply_sector_cap）
  - レジーム依存乗数（calc_regime_multiplier）
  - ポジションサイズ計算（risk_based / equal / score）
- 研究（research）
  - ファクター計算（momentum, volatility, value）
  - 将来リターン計算・IC（Information Coefficient）評価
  - 統計サマリー（factor_summary 等）
- AI 統合
  - ニュース NLP（OpenAI を用いた銘柄別センチメント → ai_scores テーブルへ）
  - 市場レジーム判定（ETF MA200 乖離 + マクロニュースの LLM 評価の合成）
  - API の堅牢な呼び出し（リトライ、レスポンス検証、部分書き込み）
- 運用ツール
  - ペーパートレードの検証レポート生成（kabusys.tools.paper_verification_report）
  - ログ設定ユーティリティ（stdout + 日次ローテーションファイル）
  - プロセス優先度 / CPU affinity ユーティリティ

---
## 前提 / 必要環境
- Python 3.10+
- 必須パッケージ（例）
  - duckdb
  - psutil
  - openai
- 任意（機能に応じて）
  - PyYAML（config/*.yaml のパース検証用）
- 標準の SQLite（Python に同梱）

簡単なインストール例（venv 推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb psutil openai PyYAML
```
（実際の requirements.txt / extras はプロジェクトに応じて用意してください）

---
## セットアップ手順
1. レポジトリをクローンして作業ディレクトリへ移動
2. 仮想環境作成・パッケージインストール（上記参照）
3. 対話式で .env を作成・更新:
   ```bash
   python -m kabusys.config_setup
   ```
   - J-Quants トークン（JQUANTS_REFRESH_TOKEN）や kabuステーション API パスワード（KABU_API_PASSWORD）は必須です。
   - KABUSYS_ENV は `development` / `paper_trading` / `live` のいずれか。
4. 設定検証:
   ```bash
   python -m kabusys.validate_config
   ```
   - `--strict` を付けると警告も失敗扱いになります。
5. 必要に応じてデータディレクトリを作成（SQLite / DuckDB のデフォルトパスは `data/`）
6. ログディレクトリ（デフォルト `logs/`）は自動で作成されます。環境変数 `LOG_DIR` を指定すると変更可能です。

重要な環境変数（主要なもの）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV（development | paper_trading | live）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB）
- OPENAI_API_KEY（AI 機能利用時）
- LOG_LEVEL（DEBUG/INFO/...）
- LOG_DIR（ログ出力先）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか。デフォルト 0）
- MONITOR_POLL_INTERVAL（監視ポーリング間隔（秒）を上書き、デフォルト 60）

自動 .env ロードを無効化する場合:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト等で便利）。

---
## 使い方 — 起動スクリプト
主要な起動スクリプトはモジュールとして実行できます。

- 実行エンジン（ExecutionEngine）起動:
  ```bash
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV が `paper_trading` の場合、MockBrokerClient を使用しデータは `data/paper_trading.db` に記録され、本番 DB と分離されます。
  - 起動時に `data/stop_requested.flag` が存在すると起動をスキップします。
  - 実行中に `data/stop_requested.flag` を作成すると安全に停止できます。

- 監視ループ起動:
  ```bash
  python -m kabusys.run_monitoring
  ```
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書き可能（デフォルト 60）。
  - 監視は常に本番 sqlite_path（Settings.sqlite_path）を使用します（環境にかかわらず）。
  - 停止は `data/stop_requested.flag` を作成するか Ctrl+C。

- 設定検証:
  ```bash
  python -m kabusys.validate_config
  ```

- 設定ウィザード:
  ```bash
  python -m kabusys.config_setup
  ```

- ペーパートレード検証レポート:
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルトの DB パスは `data/paper_trading.db`。`--db` または環境変数 `PAPER_TRADING_SQLITE_PATH` で指定可能。

ログ:
- setup_logging が統一的に使われます。コンソール出力は stdout、ファイルは `logs/<app_name>.log` に日次ローテーションで出力（30日保持）。

プロセス優先度:
- 起動スクリプトは最初に `set_process_priority("high")` を呼び、可能な場合プロセス優先度を上げます（プラットフォーム依存）。

---
## 注意点 / 運用上のヒント
- 本番環境（KABUSYS_ENV=live）は十分に設定を確認してから起動してください（validate_config による警告・注意喚起あり）。
- Kill Switch（data/kill.flag）を用いることで危険時に ExecutionEngine を停止させられます。`KILL_FLAG_CLEAR_ON_START=1` の設定は本番で危険になり得ます（デフォルト 0 を推奨）。
- OpenAI を使う機能は API キー（OPENAI_API_KEY）と通信の信頼性に依存します。API エラー・レート制限に対してリトライ実装がありますが、運用時はコスト・レート制限に注意してください。
- DuckDB は研究・指標計算に利用されます。prices_daily / raw_financials / raw_news などのテーブルが前提です。
- SQLite のスキーマは init_monitoring_db で自動作成・マイグレーションを行います。

---
## ディレクトリ構成（主要ファイル・モジュール）
以下はソースツリー（src/kabusys）内の主要ファイルと簡単な説明です。

- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数 / Settings クラス、.env 自動ロードロジック
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring ポーリングループ起動スクリプト

  - ai/
    - news_nlp.py — ニュースを OpenAI でスコアリングして ai_scores に書き込む
    - regime_detector.py — 市場レジーム判定（MA + マクロニュース LLM 結合）
  - monitoring/
    - monitoring_db.py — SQLite のスキーマ初期化・読み書きラッパ
    - system_monitor.py — システム状態 / データ鮮度監視
    - trade_monitor.py — （注文周りの監視: 滞留注文・約定異常等）※参照実装あり
    - risk_monitor.py — ドローダウン / ポジション上限チェック
    - kill_switch.py — kill.flag 制御
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - alert_manager.py — アラート送信管理（LINE 等、実装箇所参照）
  - execution/
    - execution_engine.py — 発注・セッション管理のコア
    - broker_factory.py — ブローカークライアント生成（Mock 対応）
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py — 発注周りのコンポーネント
  - portfolio/
    - portfolio_builder.py — 候補選定・重み算出
    - risk_adjustment.py — セクター制限・レジーム乗数
    - position_sizing.py — 発注株数計算（lot 丸め、aggregate cap）
  - research/
    - factor_research.py — モメンタム/ボラティリティ/バリュー等の算出
    - feature_exploration.py — 将来リターン計算・IC, 統計要約
  - data/
    - pipeline.py — （データ取得・最終日取得等のユーティリティ）
    - stats.py — zscore_normalize 等研究用ユーティリティ
  - utils/
    - logging_setup.py — ログ設定ユーティリティ（stdout + 日次ファイル）
    - process_priority.py — プロセス優先度 / CPU affinity
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成ツール

その他:
- data/ — SQLite / flag / pid ファイル 等の保存先（デフォルト）
- logs/ — ログファイル（デフォルト）

（実際のリポジトリでは上記に加えて config/*.yaml、scripts、ドキュメント等が存在する場合があります）

---
## 開発者向けメモ
- DuckDB 用のクエリは conn.execute(...).fetchall() を多用しており、検索範囲を適切に限定しています（パフォーマンス目的）。
- AI 統合部分は API 呼び出しをラップしており、テスト時は _call_openai_api をパッチしてスタブ化できます。
- 設定の自動読み込みはプロジェクトルート（.git または pyproject.toml）を起点に行います。CWD に依存しない設計です。
- ログディレクトリ作成に失敗した場合はファイルハンドラをスキップして stdout のみで運用します。
- 監視・実行スクリプトはいずれもプロセス優先度を high に試みます（権限によりスキップされることがあります）。

---
## ライセンス / 貢献
（ここにライセンスや貢献方法を記載してください。プロジェクトごとのポリシーに従って編集をお願いします。）

---

README に不明点や追加で記載したい運用手順（例: systemd ユニットのサンプル、Docker 化手順）があれば教えてください。必要に応じて追記します。