# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買・リサーチ基盤です。  
戦略のリサーチ／ファクター計算、ポートフォリオ構築、発注エンジン（本番 / ペーパートレード対応）、および運用監視（モニタリング・キルスイッチ）を含むモジュール群を提供します。

※ 本リポジトリはパッケージとして `kabusys` 配下の Python モジュール群で構成されています。

---

## 概要

- リサーチ（DuckDB を用いたファクター計算・統計解析）
- ポートフォリオ構築（候補選定・重み計算・株数算出・セクター制約）
- Execution エンジン（BrokerClient 抽象により実口座 / MockBroker に対応）
- 監視（System / Trade / Risk モニタ、Kill Switch、アラート管理）
- AI ユーティリティ（ニュース NLP によるセンチメント、レジーム判定。OpenAI を使用）
- 開発支援ツール（.env ウィザード、設定検証、Paper Trading 検証レポート生成）

設計上の要点：
- 本番 DB とペーパートレード DB は分離（PAPER_TRADING 用 DB を利用）
- .env 自動ロード機能（プロジェクトルートの `.env` / `.env.local`）
- OpenAI 呼び出し部分は安全にリトライ・バリデーションを行う
- DuckDB を分析用 DB、SQLite を監視／履歴用 DB として使用

---

## 主な機能一覧

- 設定関連
  - `kabusys.config_setup` : 対話式 .env ウィザード
  - `kabusys.validate_config` : 起動前の設定チェック（必須環境変数・ファイル存在など）

- 実行 / モニタリング
  - `run_execution.py` : ExecutionEngine 起動スクリプト（KABUSYS_ENV によりペーパートレード切替）
  - `run_monitoring.py` : SystemMonitor ポーリング起動スクリプト（ポーリング間隔は環境変数で調整可能）
  - Kill Switch（`data/kill.flag`）による自動停止、`data/stop_requested.flag` による手動停止

- モニタリングコンポーネント
  - SystemMonitor：CPU/メモリ/ディスク、プロセス存否、データ鮮度チェック
  - TradeMonitor：滞留注文・約定異常価格検出
  - RiskMonitor：ドローダウン・ポジション上限監視、dashboard 更新
  - KillSwitch：条件に応じて kill.flag を書き込み ExecutionEngine を停止させる

- ポートフォリオ構築
  - 銘柄候補選定、等金額／スコア加重の重み計算
  - セクター集中制限、レジーム乗数
  - 株数決定（リスクベース、等配分、スコア配分）、単元（lot）丸め、aggregate cap

- リサーチ / 統計
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー

- AI（OpenAI）
  - news_nlp.score_news: ニュースを LLM でスコアリングし ai_scores テーブルに保存
  - regime_detector.score_regime: ETF MA とマクロニュースを組合せて市場レジーム判定

- ツール
  - tools.paper_verification_report: ペーパートレード DB を解析して PASS/FAIL レポート出力

---

## セットアップ手順（ローカル開発用）

前提
- Python 3.9+（プロジェクトの具体的な最低バージョンは環境に合わせて調整してください）
- SQLite（標準で同梱）
- 推奨: 仮想環境（venv / pyenv 等）

1. リポジトリをクローン / 展開する
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   必要なパッケージ例（プロジェクトの requirements.txt がある場合はそちらを使用）:
   - duckdb
   - psutil
   - openai
   - PyYAML（設定ファイル検証のために任意）
   例:
   pip install duckdb psutil openai pyyaml

4. 環境変数設定（.env）
   - 対話式ウィザードで作成（推奨）
     python -m kabusys.config_setup
   - または手動で `.env` をルートに作成
     必須:
       JQUANTS_REFRESH_TOKEN=
       KABU_API_PASSWORD=
     推奨/任意:
       KABUSYS_ENV=development|paper_trading|live
       DUCKDB_PATH=data/kabusys.duckdb
       SQLITE_PATH=data/monitoring.db
       PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
       OPENAI_API_KEY=（AI機能を使う場合必須）
       LOG_LEVEL=INFO
     注意: `.env` を Git に含めないでください。

5. 設定検証（任意）
   python -m kabusys.validate_config
   - `--strict` を付けると警告も失敗扱い（exit(1)）

6. データディレクトリの作成（必要に応じて）
   - デフォルトの DB パスや PID / フラグファイル用ディレクトリ（`data/`）を作成しておくと良いです。
   mkdir -p data

---

## 実行方法

- ExecutionEngine 起動（デーモン or foreground）
  python -m kabusys.run_execution

  振る舞い:
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、`PAPER_TRADING_SQLITE_PATH`（デフォルト: data/paper_trading.db）へ記録します（本番 DB と完全分離）。
  - 起動時に `data/stop_requested.flag` が存在すると起動せず終了します。
  - 実行中は PID を `data/execution.pid` に書きます。`data/stop_requested.flag` を作ることで監視プロセスからの停止要求や手動停止が可能。

- Monitoring 起動（ポーリング）
  python -m kabusys.run_monitoring

  振る舞い:
  - 監視ループは `MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
    例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は常に本番用の sqlite_path（Settings.sqlite_path）を使用して監視テーブルを書き込みます。
  - ループ中に `data/stop_requested.flag` を検知すると安全に終了します。

- Paper Trading 検証レポート
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  または
  PAPER_TRADING_SQLITE_PATH=data/paper_trading.db python -m kabusys.tools.paper_verification_report

- AI 機能
  - news_nlp.score_news(conn, target_date, api_key=None)
    - `api_key` を指定するか環境変数 `OPENAI_API_KEY` を設定してください。
  - regime_detector.score_regime(conn, target_date, api_key=None)
    - 同様に OpenAI API キーが必要です。
  - OpenAI 呼び出しはレート制限・エラー時にリトライロジックを備えていますが、APIキーが未設定だと例外になります。

---

## 停止 / Kill Switch

- 手動停止（Monitoring / Execution 両方）
  - ファイル `data/stop_requested.flag` を作成すると、`run_monitoring` / `run_execution` は次のループで検知して終了します。
  - 削除は手動で `rm data/stop_requested.flag`（再起動するときは削除しておく）

- 自動停止（Kill Switch）
  - Monitoring のリスク条件（ドローダウン・ポジション上限など）を満たすと、`KillSwitch` が `Settings.kill_flag_path`（デフォルト `data/kill.flag`）へ理由を書き込みます。
  - ExecutionEngine 側は kill.flag をチェックして安全に停止する設計です（Engine 側の設定に依存します）。
  - `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に kill.flag を自動クリアしますが、本番では危険なためデフォルト 0 を推奨します。

---

## 主要な環境変数一覧

必須：
- JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン
- KABU_API_PASSWORD — kabuステーション API パスワード

重要 / 推奨：
- KABUSYS_ENV — execution モード: development / paper_trading / live（デフォルト: development）
- OPENAI_API_KEY — OpenAI を使う機能で必要
- DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL — run_monitoring 用ポーリング間隔（秒）
- PID_FILE_PATH — Execution pid file location（デフォルト: data/execution.pid）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag をクリアするか（"1" = はい）

（その他、PAPER_FILL_MODE などペーパートレード動作に関する設定あり。詳細は `kabusys.config.Settings` を参照）

---

## トラブルシューティング（よくある問題）

- PyYAML がない場合、`validate_config` は YAML の内容検証をスキップします（警告）。
- OpenAI キー未設定で AI 機能を呼ぶと例外が発生します。`OPENAI_API_KEY` を設定してください。
- DuckDB / SQLite のパスの親ディレクトリがない場合、起動時に警告が出ます。必要なら `mkdir -p data` を作成してください。
- `MONITOR_POLL_INTERVAL` に不正値（0 以下、非整数）を与えるとデフォルト値（60 秒）にフォールバックします。

---

## ディレクトリ構成（抜粋）

（プロジェクトルート: src/kabusys 以下を示します）

- src/
  - kabusys/
    - __init__.py
    - config.py               — 環境変数 / 設定読み込み
    - config_setup.py         — .env 対話ウィザード
    - validate_config.py      — 設定検証 CLI
    - run_execution.py        — ExecutionEngine 起動スクリプト
    - run_monitoring.py       — Monitoring 起動スクリプト
    - ai/
      - __init__.py
      - news_nlp.py           — ニュース NLP スコアリング
      - regime_detector.py    — レジーム判定
    - monitoring/
      - monitoring_db.py      — SQLite 監視テーブル
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - monitoring_engine.py
      - kill_switch.py
      - alert_manager.py      — （未掲示のアラート管理）
    - portfolio/
      - __init__.py
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - tools/
      - __init__.py
      - paper_verification_report.py
    - utils/
      - __init__.py
      - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
    - execution/               — 発注関連（OrderManager, Engine 等、参照あり）
    - data/                    — データ / DB / flag（runtime に作成される）
    - config/                  — yaml 設定ファイル（system_config.yaml など）

---

## 開発ノート / 参考

- `.env` の自動ロード
  - デフォルトでプロジェクトルートにある `.env` / `.env.local` を自動で読み込みます。
  - テスト等で自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- DB マイグレーション
  - `monitoring_db.init_monitoring_db` は冪等でテーブルを作成し、既存 DB に足りないカラム（例: latency_ms, peak_value）を追加する簡易マイグレーションを行います。

- ロギング / 優先度設定
  - 起動時に `set_process_priority("high")` を呼んでプロセス優先度を上げる試みを行います（OS 権限により失敗する場合は警告でスキップされます）。

---

必要であれば以下を追加できます：
- requirements.txt のサンプル
- systemd / supervisor 用の unit ファイル例
- さらに詳しい API ドキュメント（各モジュールの公開関数一覧）
- テスト実行方法 / CI 設定例

README の補足や特定セクションの拡張（例: デプロイ手順、Dockerfile、systemd サービス定義など）を希望する場合は教えてください。