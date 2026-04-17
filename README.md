# KabuSys

日本株向け自動売買システムの一部コードベースです。本リポジトリはトレード実行（ExecutionEngine）、監視（Monitoring）、リサーチ（ファクター計算・特徴量探索）、AI（ニュースセンチメント・レジーム判定）、ポートフォリオ構築等のコンポーネントを含みます。

---

## プロジェクト概要

KabuSys は日本株アルゴリズム取引のためのモジュール群です。主な目的は以下です。

- 市場データ（DuckDB）を用いたファクター計算／リサーチ
- 発注エンジン（ExecutionEngine）による注文管理（実運用 / ペーパートレード対応）
- システム稼働・注文状態・リスク監視（SQLite を利用）
- ニュースの自然言語解析（OpenAI）によるセンチメント算出と市場レジーム判定
- ポートフォリオ構築・ポジションサイズ計算の純関数群
- 設定ウィザード・検証ツール・運用向けユーティリティ

設計方針として、できる限り外部サーバー（取引 API 等）への依存を分離し、ペーパートレード時は専用 DB に記録して本番データと分離するようになっています。

---

## 機能一覧

- Execution
  - 実際のブローカークライアントまたはモック（KABUSYS_ENV=paper_trading）を用いた発注
  - ExecutionEngine の起動スクリプト（run_execution.py）
  - PID / stop フラグによる停止制御
- Monitoring
  - システムリソース監視（CPU / メモリ / ディスク）
  - データ鮮度チェック（DuckDB の最終日付参照）
  - 注文滞留チェック・約定異常チェック
  - リスク監視（ドローダウン・ポジション上限）
  - Kill Switch（条件を満たせば data/kill.flag に理由を書き込む）
  - 監視ループ起動スクリプト（run_monitoring.py）
- Research
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ
- AI
  - ニュース NLP（OpenAI）による銘柄別センチメント付与（ai_scores テーブル）
  - マクロニュース + ETF MA200 を組み合わせた市場レジーム判定（bull/neutral/bear）
  - OpenAI 呼び出しはリトライ・バックオフを備えフェイルセーフ
- Portfolio
  - 候補選定、等重・スコア重み、ポジションサイズ計算、セクターキャップ、レジーム乗数
- Tools
  - Paper Trading 検証レポート生成スクリプト（期間指定可能）
- 設定関連
  - 対話式 .env 作成ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）

---

## セットアップ手順

以下はローカルで開発・実行するための概略手順です。

前提
- Python 3.9+（コードは型注釈 etc.を利用）
- OS によっては psutil でプロセス優先度設定に権限が必要

1. リポジトリをクローンして作業ディレクトリに移動
   - git clone ... && cd <repo>

2. 仮想環境を作成して有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  # macOS/Linux
   - .venv\Scripts\activate     # Windows

3. 必要パッケージをインストール
   - 必須ライブラリ（少なくとも）:
     - duckdb
     - psutil
     - requests
     - openai
     - （任意）PyYAML（config 検証で YAML ファイル検証を行う場合）
   - 例:
     - pip install duckdb psutil requests openai pyyaml

   > 注意: リポジトリに requirements.txt がない場合はプロジェクト方針に合わせて依存を管理してください。

4. .env を作成
   - 対話式ウィザードを実行:
     - python -m kabusys.config_setup
   - または手動で .env を作成（.env.example を参考に設定）

5. 設定を検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります

6. DB 初期化
   - run_monitoring.py / run_execution.py 起動時に必要なテーブルは自動作成されます（monitoring DB マイグレーション含む）。

---

## 環境変数（主なもの）

- KABUSYS_ENV: 実行環境（development / paper_trading / live）
  - paper_trading の場合は MockBrokerClient を使用し data/paper_trading.db を利用
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で必要）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（SQLite）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- PID_FILE_PATH: ExecutionEngine の PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: Kill スイッチファイルパス（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒, デフォルト 60）

---

## 使い方（主要コマンド）

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード（警告も失敗扱い）:
    - python -m kabusys.validate_config --strict

- 実行エンジン起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は専用の paper DB に記録して本番 DB と分離
    - data/execution.pid を使用してプロセス存在確認
    - data/stop_requested.flag を検知すると停止

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（秒）
  - 監視は常に本番 sqlite_path を参照（run_monitoring の実装上の仕様）
  - stop フラグは data/stop_requested.flag（存在で監視ループ終了）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数の代替）

- AI スコアリング / レジーム判定
  - モジュール関数を呼び出して利用
    - kabusys.ai.score_news  → ai_scores へ書き込み
    - kabusys.ai.regime_detector.score_regime  → market_regime へ書き込み
  - いずれも OPENAI_API_KEY が必要（引数で API キーを渡すことも可）

運用ヒント
- デーモン化 / 永続化には systemd / supervisor / docker 等を使用してください。
- run_monitoring は監視 DB を本番用 sqlite_path で開きます（環境にかかわらず）。

---

## 監視・停止制御の仕組み（簡易まとめ）

- PID 管理: ExecutionEngine は data/execution.pid を書き、 SystemMonitor はその PID をチェックしてプロセス生存を判定します。古い（stale） PID は検出されると削除されます。
- Kill Switch: RiskMonitor がルール（ドローダウン、ポジション上限など）を満たすと KillSwitch が data/kill.flag に理由を書き込みます。ExecutionEngine はこのフラグの検出で停止する設計です。
- run_monitoring 側の停止フラグ: data/stop_requested.flag があると監視ループを止めます（運用側の手動停止用）。

---

## ディレクトリ構成（抜粋）

以下は主要なディレクトリ/ファイルの概観（src/kabusys 以下）。

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数 / Settings 管理
  - config_setup.py            — .env 対話式ウィザード
  - validate_config.py         — 設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — Monitoring 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py              — ニュース NLP / OpenAI 経由で ai_scores を生成
    - regime_detector.py       — マクロ + ETF によるレジーム判定
  - monitoring/
    - monitoring_db.py         — SQLite テーブル定義・永続化層
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - alert_manager.py
    - kill_switch.py
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - utils/
    - __init__.py
    - process_priority.py       — psutil を使った優先度/affinity 設定
  - (その他) data/ や config/（yaml）など運用用ファイルがプロジェクトルートに存在

---

## 注意点 / 運用上の留意事項

- 本番運用（KABUSYS_ENV=live）時は .env の設定を慎重に行ってください。validate_config の live guard が警告を出します。
- OpenAI への問い合わせは API 負荷・費用が発生します。API キーの管理とレート制御に注意してください。
- process priority / CPU affinity の設定は権限に依存し、失敗することがあります（警告ログが出ますが処理自体は継続します）。
- データベースのパスや PID / flag ファイルの場所は Settings 経由で変更可能です。
- run_monitoring は説明どおり「監視は本番 sqlite_path を使う」設計になっているため、テスト時は設定に注意してください。

---

この README はコードベースの主要な使い方と構成をまとめたものです。実行前に python -m kabusys.config_setup で .env を作成し、python -m kabusys.validate_config で検証することを推奨します。必要があれば各モジュールの docstring（ソース内のコメント）を参照してください。