# KabuSys

日本株向け自動売買システム（ライブラリ兼実行スクリプト群）

このリポジトリは、自動売買（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、ファクターリサーチ、AI（ニュースセンチメント／レジーム判定）などのモジュールを含む一連のコンポーネントを提供します。README は日本語での簡易ガイドです。

---

## 概要

KabuSys は以下の機能を持つモジュール群および起動スクリプトを備えたプロジェクトです。

- ExecutionEngine：発注・注文管理・リスク管理の実行エンジン（本番/ペーパートレード切替対応）
- Monitoring：システム稼働状況、注文ログ、リスクの監視と Kill Switch（停止フラグ）発動
- Portfolio：候補選定、重み付け、ポジションサイズ計算、セクター制約などの純粋関数実装
- Research：DuckDB 上のファクター計算・特徴量探索（モメンタム、バリュー、ボラティリティ等）
- AI：OpenAI を利用したニュースセンチメント（news_nlp）／市場レジーム判定（regime_detector）
- ユーティリティ：ログ設定、プロセス優先度設定、環境設定ウィザード、設定検証ツール
- Tools：ペーパートレード検証レポート等のスクリプト

設計上のポイント：
- DuckDB / SQLite を用いたデータ保存（分析用は DuckDB、監視・発注履歴は SQLite）
- 環境による挙動切替（KABUSYS_ENV: development / paper_trading / live）
- .env / .env.local の自動ロード（必要に応じて無効化可能）
- フェイルセーフ設計：API失敗やデータ欠損時に例外で停止させない運用を想定

---

## 主な機能一覧

- 環境設定ウィザード（.env の作成・更新）: kabusys.config_setup
- 設定検証 CLI（.env と config/*.yaml の整合チェック）: kabusys.validate_config
- 実行エンジン起動スクリプト: run_execution.py
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し paper_trading DB に記録（本番 DB と分離）
- 監視ループ起動スクリプト: run_monitoring.py
  - MONITOR_POLL_INTERVAL でポーリング間隔を変更可能（デフォルト 60 秒）
  - 停止フラグ（data/stop_requested.flag）でループを終了
- 監視永続化（SQLite）: monitoring_db モジュール（system_status・trade_logs・risk_logs・positions・dashboard）
- Kill Switch（data/kill.flag）による ExecutionEngine 停止制御
- Portfolio 関係:
  - 候補選定（select_candidates）
  - 等重・スコア加重（calc_equal_weights / calc_score_weights）
  - ポジションサイズ計算（calc_position_sizes）
  - セクター上限（apply_sector_cap）、レジーム乗数（calc_regime_multiplier）
- Research:
  - ファクター計算（calc_momentum / calc_volatility / calc_value）
  - 将来リターン、IC、統計サマリ（calc_forward_returns / calc_ic / factor_summary）
- AI:
  - ニュースを LLM（gpt-4o-mini 等）に投げて銘柄別スコア付与（score_news）
  - マクロニュース + ETF MA 乖離で市場レジーム判定（score_regime）
  - OpenAI の呼び出しは堅牢化（リトライ / JSON バリデーション / クリップ等）
- ツール:
  - Paper Trading の検証レポート生成: kabusys.tools.paper_verification_report

---

## セットアップ手順

注意: プロジェクトに requirements.txt が含まれていない場合は、必要なパッケージを手動でインストールしてください。

1. Python（推奨: 3.10 以上）を用意

2. 必要なパッケージをインストール（例）
   - duckdb
   - psutil
   - openai
   - pyyaml（config YAML 検証が必要な場合）
   例:
   pip install duckdb psutil openai pyyaml

3. リポジトリルートへ移動し、.env を用意
   - 対話式ウィザードで作成する:
     python -m kabusys.config_setup
   - または手動で `.env` を作成（.env.example を参考に）

4. 設定の検証（推奨）
   python -m kabusys.validate_config
   - 警告も致命扱いにする場合:
     python -m kabusys.validate_config --strict

5. データディレクトリの確認
   - デフォルトの DB / ログ パス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper Trading SQLite: data/paper_trading.db
     - ログディレクトリ: logs/
   - 必要に応じて .env で上書きしてください（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH / LOG_DIR）

6. OpenAI を利用する場合:
   - 環境変数 OPENAI_API_KEY を設定するか、関数呼び出し時に明示的に api_key を渡してください。

---

## 使い方（主要コマンド例）

- 環境設定ウィザード（.env 作成）
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- 監視ループ起動（MONITOR_POLL_INTERVAL 指定可）
  python -m kabusys.run_monitoring
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

  備考:
  - 監視は常に本番 sqlite_path を使用します（運用上の設計）。
  - 停止はプロジェクトルート/data/stop_requested.flag を作ることでループ検知後停止。

- 実行エンジン起動（ExecutionEngine）
  python -m kabusys.run_execution

  環境切替:
  - 本番（live）や開発（development）は KABUSYS_ENV により切替
  - ペーパートレード:
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    → MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録されます

  停止制御:
  - プロジェクトルート/data/stop_requested.flag を作成すると Engine に停止通知
  - Kill Switch は data/kill.flag を書き込むことで ExecutionEngine 停止をトリガーします

- Paper Trading 検証レポート出力
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  オプション --db で SQLite ファイルを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI スコアリング（プログラム内呼び出し例）
  from openai import OpenAI
  import duckdb
  from datetime import date
  from kabusys.ai import score_news  # ai.__init__ では score_news を公開
  conn = duckdb.connect("data/kabusys.duckdb")
  score_news(conn, target_date=date(2026,4,11), api_key="sk-...")

- レジームスコア算出（プログラム内呼び出し）
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date=date(2026,4,11), api_key="sk-...")

---

## 主要な環境変数（要点）

- KABUSYS_ENV: 開発/ペーパー/本番 (development | paper_trading | live)（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabuステーション API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- LOG_DIR: ログ保存先（デフォルト: logs/）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: ペーパートレードの約定挙動（instant | partial | never | reject）
- KILL_FLAG_CLEAR_ON_START: 実行時に kill.flag を自動でクリアするか（0/1）

自動 .env 読み込み:
- ルートにある `.env` と `.env.local` を自動で読み込みます（OS 環境変数が優先）
- 自動読み込みを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## ディレクトリ構成（抜粋）

src/kabusys/ 以下をルートとする。代表的なファイル:

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数 / 設定読み込みロジック
  - config_setup.py            — .env 作成ウィザード CLI
  - validate_config.py         — 設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — Monitoring ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading レポート生成
  - utils/
    - __init__.py
    - logging_setup.py         — ログ設定ユーティリティ
    - process_priority.py      — プロセス優先度 / CPU アフィニティ設定
  - monitoring/
    - monitoring_db.py         — 監視用 SQLite 操作層
    - system_monitor.py        — システム/データ鮮度監視
    - trade_monitor.py         — （注文監視、参照あり）
    - risk_monitor.py          — ドローダウン / ポジション上限監視
    - kill_switch.py           — kill.flag 制御
    - monitoring_engine.py     — 各モニタを束ねるエンジン
    - alert_manager.py         — （アラート送信管理、参照あり）
  - execution/
    - execution_engine.py      — 実行エンジン（EngineConfig 等）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
  - portfolio/
    - portfolio_builder.py     — 候補選定 / 重み付け
    - position_sizing.py       — 株数決定 / スケーリング
    - risk_adjustment.py       — セクター制約 / レジーム乗数
    - __init__.py
  - research/
    - factor_research.py       — Momentum / Value / Volatility など
    - feature_exploration.py   — IC / 将来リターン / 統計
    - __init__.py
  - ai/
    - __init__.py
    - news_nlp.py              — ニュース -> LLM -> ai_scores 反映
    - regime_detector.py       — ETF MA + マクロニュースでレジーム判定

data/ や logs/ は実行時に使用されるディレクトリ（DB・PID・フラグファイル・ログ等）。

---

## 設計上の注意点 / 運用メモ

- Paper Trading と本番データは明確に分離されるよう設計されています（PAPER_TRADING_SQLITE_PATH を利用）。
- 監視（Monitoring）は本番 sqlite_path を参照する設計になっている箇所があります。運用時は設定値を確認してください。
- kill.flag / stop_requested.flag を用いた停止フローにより、安全にエンジン停止を促す仕組みがあります。
- ログディレクトリ作成に失敗した場合はコンソール出力のみになります。権限やパスを確認してください。
- OpenAI 呼び出しにはリトライ・バックオフを組み込んでいますが、API キーや利用制限に注意してください。
- config/*.yaml の検証には PyYAML が必要です（validate_config の YAML 内容検査）。

---

## よくある操作（サマリー）

1. .env の作成:
   python -m kabusys.config_setup

2. 設定チェック:
   python -m kabusys.validate_config

3. 監視起動:
   python -m kabusys.run_monitoring

4. 実行エンジン起動:
   python -m kabusys.run_execution

5. Paper Trading レポート:
   python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

問題や追加のドキュメント（API 仕様や設定例、運用手順など）が必要であれば、欲しい項目を教えてください。README を具体的な運用ポリシー（デプロイ手順 / Systemd サービス定義 / Dockerfile 等）に合わせて拡張できます。