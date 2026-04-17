# KabuSys — 日本株自動売買システム

このリポジトリは日本株の自動売買に必要なコアコンポーネント群を含むモジュール群です。  
README はコードベース（src/kabusys 以下）の主要な使い方・セットアップ手順・ディレクトリ構成を日本語でまとめたものです。

バージョン: 0.1.0 (src/kabusys/__init__.py に準拠)

---

## プロジェクト概要

KabuSys は日本株向けの自動売買フレームワークです。主な目的は次のとおりです：

- シグナル生成 → ポートフォリオ構築 → 発注（ExecutionEngine）
- 発注・約定・リスク監視（Monitoring）
- Paper Trading（本番 DB と分離して検証可能）
- DuckDB を用いたリサーチ / ファクター計算
- OpenAI を用いたニュース NLP と市場レジーム検知（AI 補助機能）
- 環境設定ウィザード / 設定検証ツール / 検証レポート生成ツールなどの運用補助

設計方針として、DB 書き込みや外部 API 呼び出しは明確に分離されており、テストや Paper Trading のために本番 DB と分離できるようになっています。

---

## 機能一覧

- 実行系
  - ExecutionEngine: 発注・リスク管理・オーダー管理・リコンサイル機能
  - Paper Trading モード（KABUSYS_ENV=paper_trading）では MockBrokerClient を使用し、data/paper_trading.db に記録
- 監視系
  - SystemMonitor: CPU / メモリ / ディスク / データ鮮度 / 実行プロセス監視
  - TradeMonitor: 滞留注文（stale）・約定異常価格の検出
  - RiskMonitor: ドローダウン・ポジション上限の監視、ダッシュボード更新、リスクログ
  - MonitoringEngine: これらをまとめて定期実行し、Kill Switch の評価やアラート通知を行う
- ポートフォリオ構築
  - 候補選定、等金額 / スコア加重、リスク調整（セクター上限、レジーム乗数）、ポジションサイズ計算（ロット単位）
- リサーチ
  - DuckDB を利用したファクター計算（モメンタム・ボラティリティ・バリュー等）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
- AI（任意）
  - ニュース NLP（OpenAI）による銘柄単位センチメントスコアリング（ai_scores）
  - 市場レジーム判定（ma200 比率 + マクロニュースセンチメントの合成）
- ツール
  - .env 対話式ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成（tools/paper_verification_report）
- ユーティリティ
  - プロセス優先度設定 / CPU affinity（psutil 経由で Windows / POSIX を吸収）

---

## 必要条件（依存パッケージ）

最低限の依存例（requirements.txt は含まれていないため、必要なものを列挙します）:

- Python 3.9+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（config/*.yaml の検証を行う場合は任意だが推奨）

インストール例:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

（※ 実際の requirements がある場合はそちらを参照してください）

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成して依存をインストールします（上記参照）。

2. .env を作成する
   - 対話式ウィザードを使う（推奨）:
     ```bash
     python -m kabusys.config_setup
     ```
     ウィザードは .env（デフォルト）を生成・更新します。秘匿項目はマスク表示されます。
   - 直接環境変数を設定することも可能です。

3. 設定検証（必須項目が設定されているか確認）
   ```bash
   python -m kabusys.validate_config
   # 警告も失敗としたい場合:
   python -m kabusys.validate_config --strict
   ```

4. DB パスのデフォルト
   - DuckDB: data/kabusys.duckdb
   - SQLite（monitoring）: data/monitoring.db
   - Paper Trading SQLite: data/paper_trading.db（KABUSYS_ENV=paper_trading 時に使用）
   必要に応じて .env で DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH を上書きします。

5. data/ ディレクトリ
   - PID やフラグファイルは data/ 以下に作成されます。必要なら事前にディレクトリを作ってください（実行時に自動作成される場合があります）。

---

## 使い方

以下は主要なコマンド例です。各スクリプトはパッケージモジュールとして実行可能です。

1. ExecutionEngine を起動する（発注実行）
   - 本番・開発切替は KABUSYS_ENV（development / paper_trading / live）で行います。
   - Paper Trading（モックブローカー）は KABUSYS_ENV=paper_trading に設定すると paper DB を使用します。
   ```bash
   python -m kabusys.run_execution
   ```

   挙動のポイント:
   - 起動時にプロセス優先度を "high" にしようとします（psutil による）。権限や OS によって失敗すると警告のみ出ます。
   - stop フラグ: data/stop_requested.flag が存在すると起動を中止または実行中に停止します。
   - 実行時は data/execution.pid に PID を書きます（設定で変更可能）。

2. Monitoring（監視）を起動する
   ```bash
   python -m kabusys.run_monitoring
   ```
   - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）。
   - Monitoring は KABUSYS_ENV にかかわらず sqlite_path（本番の monitoring DB）を使用して監視ログを残します。
   - stop フラグ: data/stop_requested.flag を検知するとループを終了します。

3. Paper Trading 検証レポート生成
   ```bash
   python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   # DB 指定:
   python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
   ```
   - 簡単な診断（稼働率、注文成功率、レイテンシ等）を stdout に出力します。

4. AI 機能（ニュース NLP / レジーム判定）
   - 環境変数 OPENAI_API_KEY を設定（または関数に api_key を渡す）してから実行します。
   - プログラム的に呼ぶことを想定しています（例: kabusys.ai.score_news）。
   - CLI ラッパーはありませんが、スクリプト／ジョブから import して使用してください。

5. 設定の自動ロードの制御
   - デフォルトでプロジェクトルートの .env / .env.local が自動ロードされます。
   - 自動ロードを無効にするには環境変数を設定:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

---

## 主要な環境変数（抜粋）

- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード

- 実行環境
  - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
  - LOG_LEVEL — DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）

- DB / ファイルパス
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — SQLite（監視 DB）パス（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
  - PID_FILE_PATH — Execution PID ファイルパス（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH — Kill Switch 用フラグファイル（デフォルト: data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動でクリアする (0/1; default 0)

- Paper Trading 動作
  - PAPER_FILL_MODE — instant|partial|never|reject（デフォルト: instant）

- Monitoring
  - MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、デフォルト 60）

- OpenAI
  - OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合に必須）

（完全な一覧は src/kabusys/config.py を参照してください）

---

## Kill Switch / stop フラグについて

- 実行停止のために以下のフラグファイルを利用します:
  - data/stop_requested.flag — run_monitoring / run_execution が存在を検知して処理を停止するためのフラグ（手動で作成）
  - data/kill.flag — KillSwitch が書き込むフラグ。ExecutionEngine の停止トリガーとして使用されます（KillSwitch は一定のリスク条件で書き込む）
- kill.flag は Settings.kill_flag_clear_on_start=1 を有効にしていると起動時に自動でクリアされる可能性があるため、本番では 0 を推奨します。

Kill Switch の書き込み条件例:
- ドローダウン閾値越え（デフォルト 10%）
- ポジション数が上限（RiskMonitor の設定）を超えた場合

---

## その他の注意点 / 実装メモ

- Monitoring の DB 初期化: monitoring のスクリプトは起動時に monitoring DB のテーブルを冪等に作成します（init_monitoring_db）。
- run_monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使って監視ログを残します（監視は常に本番 DB で行うのが想定）。
- run_execution は KABUSYS_ENV=paper_trading の場合、paper_sqlite_path を使用して本番 DB と分離します。
- プロセス優先度設定は psutil を用いて行います。権限不足や非対応 OS の場合は警告でスキップします。
- YAML 設定ファイル（config/*.yaml）を検証するためには PyYAML が必要です。validate_config はインストールされていない場合は YAML の検証をスキップします。
- DuckDB を使ったリサーチ系は prices_daily / raw_financials / raw_news 等のテーブルを前提とします。テーブル構成はプロジェクト内のドキュメント・スキーマを参照してください。
- AI 機能は OpenAI（gpt-4o-mini 等）に依存します。API レートリミット・エラーに対してエクスポネンシャルバックオフでリトライする実装がありますが、API キーとコストに注意してください。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py — 環境変数 / 設定読み込み
- config_setup.py — .env 対話式ウィザード
- validate_config.py — 設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor 起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py — ニュース NLP（OpenAI）処理
  - regime_detector.py — 市場レジーム判定
- monitoring/
  - monitoring_db.py — SQLite 永続化層
  - monitoring_engine.py — 各モニタを束ねるエンジン
  - system_monitor.py, trade_monitor.py, risk_monitor.py, kill_switch.py, alert_manager.py (一部省略)
- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - risk_adjustment.py — セクター上限・レジーム乗数
  - position_sizing.py — 発注株数計算
- research/
  - factor_research.py, feature_exploration.py — DuckDB を用いたファクター計算・解析
- tools/
  - paper_verification_report.py — Paper Trading の検証レポート
- utils/
  - process_priority.py — psutil を用いた優先度/CPU affinity 設定
- execution/ (発注関連のコンポーネント群: broker_factory, execution_engine, order_manager, order_repository, reconciler, risk_manager, order_record など)

トップレベル（プロジェクトルート）
- .env, .env.local — 環境変数（自動ロード対象）
- data/ — デフォルト DB ファイル・PID・フラグファイル配置場所（実行時に作成されることが多い）
- config/ — YAML 設定ファイル（system_config.yaml 等。スクリプトで生成可能な場合あり）

---

## よくある運用ワークフロー（例）

1. 開発環境で .env を作り、validate_config でチェック
2. DuckDB を準備してリサーチ機能を検証（researchモジュール）
3. Paper Trading で発注フローを検証（KABUSYS_ENV=paper_trading）
4. Paper Trading 結果を tools/paper_verification_report で評価
5. 本番投入前に validate_config --strict を実行して最終チェック
6. 本番では run_execution を supervisor / systemd 等で管理、run_monitoring を別プロセスで常時監視

---

## サンプルコマンドまとめ

- .env ウィザード:
  python -m kabusys.config_setup

- 設定検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- Execution 起動:
  python -m kabusys.run_execution

- Monitoring 起動:
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading レポート:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

この README はコードベースの主要機能と運用に関する概要ガイドです。より詳細な API ドキュメントや運用マニュアル（デプロイ手順、systemd ユニット、バックアップ方針など）は別途作成することを推奨します。必要であれば各モジュールの詳細ドキュメント（関数シグネチャ・期待する DB スキーマ）も作成します。