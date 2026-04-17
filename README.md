# KabuSys

日本株向け自動売買システムのパイロット実装（ライブラリ群・起動スクリプト・ユーティリティ）。  
本リポジトリは戦略の研究・ポートフォリオ構築、発注エンジン（実売買／ペーパートレード）、監視（モニタリング）および AI を使ったニュース・レジーム判定などの機能を提供します。

Version: 0.1.0

---

## プロジェクト概要

- DuckDB / SQLite をデータ保管に使用し、価格データやファイナンス情報、ログを保持します。
- ExecutionEngine による発注（本番/ペーパー両対応）、モニタリングコンポーネントによる稼働監視とリスク監視、Kill Switch による強制停止などの運用機能を備えます。
- AI（OpenAI）を用いたニュースセンチメント（銘柄別）とマクロレジーム判定をサポートします（OpenAI APIキー必須）。
- 設定は環境変数（.env）から読み込みます。対話式ウィザード・検証ツールを提供。

---

## 主な機能一覧

- 起動スクリプト
  - python -m kabusys.run_execution : ExecutionEngine を起動（KABUSYS_ENV に応じてペーパー/本番切替）
  - python -m kabusys.run_monitoring : SystemMonitor のポーリングループを起動
- 設定関連
  - python -m kabusys.config_setup : .env の対話式ウィザードで作成／更新
  - python -m kabusys.validate_config : .env / config/*.yaml の簡易検証（--strict オプションあり）
- ペーパートレード検証
  - python -m kabusys.tools.paper_verification_report : ペーパートレード DB から検証レポートを生成
- 研究/ファクター計算（DuckDB を想定）
  - kabusys.research : ファクター計算・特徴量解析用ユーティリティ群（momentum, volatility, value, forward returns, IC 等）
- ポートフォリオ構築
  - kabusys.portfolio : 候補抽出、重み計算、位置サイズ計算、セクター制約・レジーム倍率適用
- AI
  - kabusys.ai.score_news : ニュース記事を LLM でスコア化して ai_scores テーブルへ書き込み
  - kabusys.ai.score_regime : ETF とマクロニュースを組合せて市場レジーム判定（bull/neutral/bear）
- ユーティリティ
  - プロセス優先度 / CPU affinity 設定（kabusys.utils.process_priority）
  - 監視ログ（SQLite）読み書きラッパー（kabusys.monitoring.monitoring_db）

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動
   - git clone <repo-url>
   - cd <repo-root>

2. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - 必須ライブラリ例:
     - duckdb
     - psutil
     - openai
     - （任意）PyYAML（validate_config の YAML 検証に利用）
   - 例:
     - pip install duckdb psutil openai pyyaml

   ※ リポジトリに requirements.txt がある場合はそれを利用してください。

4. データディレクトリを作成（明示的に必要な場合）
   - mkdir -p data

5. .env を作成
   - 対話形式で作成: python -m kabusys.config_setup
   - 必須環境変数（例）
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - OPENAI_API_KEY（AI 機能を使う場合）
   - よく使うデフォルト:
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - KABUSYS_ENV=development|paper_trading|live
     - LOG_LEVEL=INFO

6. 設定検証（推奨）
   - python -m kabusys.validate_config
   - 厳密モード（警告を失敗扱い）:
     - python -m kabusys.validate_config --strict

---

## 使い方（起動例）

- ExecutionEngine を起動（通常）
  - KABUSYS_ENV によって挙動が変わります:
    - development: 発注なし（ローカル開発向け）
    - paper_trading: MockBrokerClient を利用し data/paper_trading.db に記録（本番 DB と分離）
    - live: 本番ブローカーを利用（kabuステーション等）
  - 起動:
    - python -m kabusys.run_execution
  - 補足:
    - 起動時に data/stop_requested.flag が存在するとエンジンは起動せず終了します
    - デフォルトの PID ファイル: data/execution.pid（設定で上書き可）
    - KILL_FLAG_CLEAR_ON_START を 1 にすると起動時に kill.flag を自動クリアする（本番では 0 推奨）

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - 環境変数:
    - MONITOR_POLL_INTERVAL (秒) — ポーリング間隔（デフォルト 60）
  - Monitoring は常に本番 sqlite_path（Settings.sqlite_path）を使用します（環境に関わらず）
  - 監視ループは data/stop_requested.flag を検知すると終了します

- Kill Switch（Execution の強制停止）
  - モニタリング内の KillSwitch が条件を満たした場合、data/kill.flag を作成します
  - ExecutionEngine は起動後に kill.flag を検知すると停止します

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定: --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH
  - 出力: 標準出力に検証サマリ（稼働率、注文成功率、レイテンシ等）

- AI 機能（ニュース/レジーム判定）
  - OPENAI_API_KEY を環境変数または関数引数で提供する必要があります
  - スクリプトやジョブから利用する場合は:
    - from kabusys.ai import score_news
    - score_news(conn, target_date, api_key=...)  # DuckDB 接続を渡す
  - API 呼び出しはリトライ・フェイルセーフ実装済み。失敗時はスコアをスキップまたは中立値へフォールバックします

---

## 重要な環境変数（抜粋）

- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API トークン
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 動作設定 / パス
  - KABUSYS_ENV — development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパー用 SQLite（デフォルト: data/paper_trading.db）
  - PID_FILE_PATH — Execution PID ファイル（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH — kill flag ファイル（デフォルト: data/kill.flag）
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）
- AI
  - OPENAI_API_KEY — OpenAI API キー（news_nlp, regime_detector で使用）
- その他
  - LOG_LEVEL — ログ出力レベル（DEBUG/INFO/...）

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数／.env 自動読み込みと Settings
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - ai/
    - news_nlp.py — ニュースを LLM でスコアリング（ai_scores へ書込）
    - regime_detector.py — マクロ＋ETFでレジーム判定（market_regime へ書込）
  - monitoring/
    - monitoring_db.py — SQLite 監視ログの永続化層
    - system_monitor.py — CPU/MEM/DISK/データ鮮度/プロセス監視
    - trade_monitor.py — 注文滞留・約定異常の検知
    - risk_monitor.py — ドローダウン・ポジション上限の監視
    - kill_switch.py — flag ファイルで Execution を停止させるロジック
    - monitoring_engine.py — 各 Monitor を束ねるループ
    - alert_manager.py — （未表示: 通知管理）
  - execution/ (発注関連、OrderRepository 等)
  - portfolio/ — ポートフォリオ構築ロジック（builder, position_sizing, risk_adjustment）
  - research/ — ファクター計算・特徴量解析（factor_research, feature_exploration）
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
  - data/ etc. — 実行時生成（例: data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db, data/execution.pid, data/kill.flag, data/stop_requested.flag）

---

## 運用上の注意 / ベストプラクティス

- 本番（KABUSYS_ENV=live）では必ず設定を二重チェックしてください（validate_config を利用）。
- kill.flag / stop_requested.flag / execution.pid は運用上重要な制御ファイルです。Git 管理対象にしないでください。
- Paper Trading モードは本番 DB と完全分離されます（PAPER_TRADING_SQLITE_PATH を使用）。ペーパートレードデータを誤って本番 DB に混在させないでください。
- OpenAI を利用する際は API コストとレート制限に注意。news_nlp と regime_detector はリトライ・バッチ処理を行いますが、過剰呼び出しは避けてください。
- DuckDB / SQLite ファイルは同時アクセスの特性に注意（小規模な並列処理は許容しますが、高頻度同時書き込みには向きません）。

---

## トラブルシューティング

- 動かない／依存エラー:
  - 必要な Python パッケージがインストールされているか確認（duckdb, psutil, openai, pyyaml 等）。
- 設定検証でエラーが出る:
  - .env を作成後に python -m kabusys.validate_config を実行し、足りない項目を補完してください。
- Execution がすぐ終了する:
  - data/stop_requested.flag や data/kill.flag の存在を確認（存在すれば削除、必要なら run_execution 前に KILL_FLAG_CLEAR_ON_START=1 を利用）。

---

この README はコードベースの主要な機能・運用を簡潔にまとめたものです。個別のモジュール（ai.news_nlp、portfolio など）は docstring に詳細な設計・注意点が記載されていますので、実装や運用時には各モジュールの docstring を参照してください。