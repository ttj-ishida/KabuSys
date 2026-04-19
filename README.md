KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買／リサーチ／監視を目的とした Python パッケージです。本リポジトリは次の主要機能を含みます。

- 発注エンジン（ExecutionEngine）：本番／ペーパートレード切替対応
- 監視（Monitoring）：システム状態・注文・リスクのポーリングとアラート / Kill Switch
- ポートフォリオ構築：候補選定、重み付け、ポジションサイズ算出、セクター制約など
- 研究（Research）：ファクター計算、将来リターン、IC 計算等（DuckDB を使用）
- AI モジュール：ニュースの NLP スコアリング、レジーム判定（OpenAI API を利用）
- 運用ツール：ペーパートレード検証レポート生成スクリプト 等
- 環境設定ウィザード・設定検証ツール（.env 生成 / validate）

主な特徴
--------
- 環境変数による柔軟な設定（.env 自動ロード & 対話式ウィザード）
- ペーパートレード用 DB を本番 DB と完全に分離
- DuckDB ベースの研究・ファクター計算（SQL と Python の組合せ）
- OpenAI を用いたニュースセンチメント / マクロセンチメント評価（冗長性とリトライ実装）
- SQLite による監視ログ永続化（system_status, trade_logs, positions, risk_logs, dashboard）
- ログはコンソール（stdout）＋日次ローテーションファイル出力（logs/）

セットアップ手順
----------------
前提:
- Python 3.9+（ソース内型注釈等を利用）
- pip 等で必要なパッケージをインストールしてください。主な依存例:
  - duckdb
  - psutil
  - openai
  - PyYAML（設定ファイル検証に必要、任意）
  - その他（実際の requirements.txt / poetry ファイルに従ってください）

手順例:
1. リポジトリをクローンして作業ディレクトリに移動
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows は .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb psutil openai pyyaml
   - （プロジェクトで提供されている requirements.txt / pyproject.toml があればそれに従う）
4. .env を作成
   - 対話式ウィザード: python -m kabusys.config_setup
   - または手動で .env を作成（.env.example を参照することを推奨）
5. 設定検証（起動前の確認）
   - python -m kabusys.validate_config
   - 警告も失敗にする場合: python -m kabusys.validate_config --strict
6. データディレクトリ・ログディレクトリの確認
   - デフォルト DB パス: data/monitoring.db（監視）, data/paper_trading.db（ペーパー時）
   - DuckDB デフォルト: data/kabusys.duckdb
   - ログディレクトリ: logs/

重要な環境変数（抜粋）
-----------------------
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
  - paper_trading の場合、MockBrokerClient を使用し paper_trading.db に記録
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI を利用する機能で必須
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード時の SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）※ run_monitoring 用

使い方（代表的なコマンド）
------------------------
- 環境設定ウィザード（対話式で .env を生成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine を起動（本番 or paper_trading は KABUSYS_ENV に依存）
  - python -m kabusys.run_execution
  - 特記事項:
    - 起動時に data/stop_requested.flag が存在するとエンジンは起動せず終了します。
    - 実行中は data/execution.pid に PID を書き出します。
    - paper_trading モードでは mock ブローカを使用し、PAPER_TRADING_SQLITE_PATH にデータを保存します。

- Monitoring を起動（システム・発注・リスク監視のポーリング）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（デフォルト 60）。
  - 監視は環境に関わらず本番用 sqlite_path（SQLITE_PATH）を使用してログを記録します。
  - 停止は data/stop_requested.flag の作成で行います（スクリプトはこのファイルを監視）。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定: --db PATH  または 環境変数 PAPER_TRADING_SQLITE_PATH を使用

- AI 機能（ニュース NLP / レジーム判定）
  - kabusys.ai.score_news / kabusys.ai.regime_detector をプログラムから呼ぶ
  - 実行には OPENAI_API_KEY が必要（gpt-4o-mini を利用する実装）
  - API 呼び出しはリトライ・バックオフ実装あり。失敗時はフェイルセーフ（スコア 0 等）で継続します。

運用上のファイル / フラグ
------------------------
- data/kill.flag
  - Monitoring の KillSwitch により条件を満たすと書き込まれる（Execution の即時停止命令）
  - すでに存在する場合は追記せずスキップ（冪等）
- data/stop_requested.flag
  - run_execution / run_monitoring の停止トリガとして監視されるファイル
  - 管理者がこのファイルを作成するとプロセスは安全に停止します
- data/execution.pid
  - ExecutionEngine が PID を書き込むファイル
- logs/
  - ログは標準出力（stdout）と logs/<app_name>.log に日次ローテートで保存

注意点・設計上の要点
-------------------
- ペーパートレードは本番 DB と完全に分離されます（PAPER_TRADING_SQLITE_PATH を使用）。
- Monitoring は「監視」専用で、run_monitoring は環境に関わらず本番用 sqlite_path にログを残します（運用上の監視ログは本番 DB に集約する方針）。
- OpenAI を使う機能は API キー必須。レスポンスのバリデーションやクリッピング（±1.0）を行い安全に処理します。
- ログ設定は kabusys.utils.logging_setup.setup_logging 経由で統一されています。ログディレクトリ作成に失敗してもコンソールログは継続します。
- プロセス優先度（set_process_priority）を起動時に "high" に設定することで実行の安定化を図っています（権限や OS により設定失敗する場合があります）。

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py
- config.py                  — 環境変数・.env ロード
- config_setup.py            — .env 対話式ウィザード
- validate_config.py         — 設定検証 CLI
- run_execution.py           — ExecutionEngine 起動スクリプト
- run_monitoring.py          — Monitoring 起動スクリプト

- ai/
  - news_nlp.py              — ニュース NLP スコアリング（OpenAI）
  - regime_detector.py       — 市場レジーム判定（OpenAI）

- monitoring/
  - monitoring_db.py         — SQLite 永続化層
  - system_monitor.py        — システム監視（CPU/Memory/Disk/データ鮮度）
  - trade_monitor.py         — 注文関連監視（滞留・約定異常等）
  - risk_monitor.py          — ドローダウン・ポジション上限監視
  - kill_switch.py           — kill.flag 制御
  - monitoring_engine.py     — 各 Monitor を束ねるエンジン
  - alert_manager.py         — （アラート配送管理）※実装参照

- portfolio/
  - portfolio_builder.py     — 候補選定・重み付け
  - position_sizing.py       — 株数決定・スケーリング・端数処理
  - risk_adjustment.py       — セクターキャップ・レジーム乗数

- research/
  - factor_research.py       — モメンタム / バリュー / ボラティリティ計算（DuckDB）
  - feature_exploration.py   — 将来リターン / IC / 統計サマリー

- utils/
  - logging_setup.py         — ログ初期化ユーティリティ
  - process_priority.py      — プロセス優先度・CPU affinity 設定

- tools/
  - paper_verification_report.py — ペーパートレード検証レポート

テスト・デバッグ
----------------
- 各モジュールは関数単位で純粋関数（副作用の少ない実装）を意識して作られています。DuckDB / SQLite コネクションを渡す設計のため、テスト時にインメモリ DB を使いやすい構成です。
- OpenAI 呼び出し部分は内部で wrapper を切っており、ユニットテストでは該当関数をモックして挙動を検証できます（README 中の _call_openai_api を patch する等）。

ライセンス・バージョン
---------------------
- パッケージバージョン: __version__ = "0.1.0"（src/kabusys/__init__.py）

最後に
------
運用前に必ず:
- python -m kabusys.config_setup で .env を作成
- python -m kabusys.validate_config で設定検証
- ログ・data ディレクトリが書き込み可能であることを確認してください

不明点や追加の実行方法、CI / デプロイ手順が必要であれば教えてください。さらに詳細な起動例や systemd / supervisor 用のユニットファイル例も用意できます。