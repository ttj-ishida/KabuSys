# KabuSys — 日本株自動売買システム

このリポジトリは日本株自動売買システム「KabuSys」のコアモジュール群です。戦略・ポートフォリオ構築、発注エンジン、監視/リスク管理、リサーチ/ファクター計算、LLM を用いたニュース NLP 等の機能を含みます。

なお本 README はコードベースから抽出した情報に基づく簡易ドキュメントです。実運用前は必ず .env の設定と `python -m kabusys.validate_config` による検証を行ってください。

## プロジェクト概要
- ターゲット: 日本株のアルゴリズム売買（戦略生成 → ポートフォリオ構築 → 発注）
- 構成要素:
  - ExecutionEngine（発注／注文管理／リスク管理）
  - Monitoring（プロセス・注文状況・リスク監視、Kill Switch）
  - Portfolio モジュール（候補選定、重み計算、ポジションサイズ算出）
  - Research（ファクター計算、特徴量解析）
  - AI モジュール（ニュース NLP による銘柄スコア、レジーム判定：OpenAI を利用）
  - CLI ツール（環境設定ウィザード、設定検証、Paper Trading レポート 等）

## 主な機能一覧
- 環境設定ウィザード（.env 作成 / 更新）: kabusys.config_setup
- 設定検証 CLI（.env・config/*.yaml の簡易検証）: kabusys.validate_config
- 発注エンジン起動スクリプト: kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し paper_trading 用 DB に記録（本番 DB と分離）
  - 起動時に PID ファイルを出力、停止はフラグファイルで制御
- 監視ループ起動スクリプト: kabusys.run_monitoring
  - SystemMonitor 等を定期実行し監視ログを SQLite に永続化
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）
- Monitoring サブシステム
  - SystemMonitor: CPU/メモリ/Disk、Execution プロセス存在チェック、データ鮮度チェック
  - TradeMonitor: 滞留注文、約定異常価格チェック
  - RiskMonitor: ドローダウン、ポジション上限監視、ダッシュボード更新
  - KillSwitch: 指定基準で data/kill.flag を書き込み ExecutionEngine の停止をトリガ
  - MonitoringDB: SQLite にテーブル（system_status / trade_logs / positions / risk_logs / dashboard）を作成／書込み
- Portfolio モジュール（純粋関数）
  - 候補選定、等重・スコア重み、リスク調整（セクター上限）、ポジションサイズ算出（単元株丸め・資金制約考慮）
- Research（DuckDB を用いたファクター計算）
  - momentum / volatility / value 等のファクターを算出
  - forward returns / IC / 統計サマリ等の補助関数
- AI（OpenAI を利用）
  - news_nlp.score_news: raw_news を集約して銘柄ごとのセンチメントを LLM で算出し ai_scores テーブルへ書込
  - regime_detector.score_regime: ETF（1321）MA200 とマクロニュースセンチメントを合成して市場レジーム判定 → market_regime に書込
  - API 呼び出しはリトライやフェイルセーフ（失敗時は中立スコア）を備える
- ツール
  - paper_verification_report: Paper Trading DB を集計して稼働率・注文成功率・レイテンシ等の検証レポートを生成

## セットアップ手順（ローカル開発向け）
1. Python 環境を準備（推奨: Python 3.9+）
   - 仮想環境を作成・有効化:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
2. 依存パッケージをインストール
   - 必要な主なパッケージ:
     - duckdb
     - psutil
     - openai
     - PyYAML（config YAML 検証を行う場合）
   - 例:
     - pip install duckdb psutil openai pyyaml
   - （requirements.txt がある場合はそれを使用）
3. .env を作成
   - 初回はウィザードを使うと簡単です:
     - python -m kabusys.config_setup
   - または .env.example を参考に手動作成
   - 重要な環境変数（一例）:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV (development | paper_trading | live) — デフォルトは development
     - OPENAI_API_KEY（AI 機能を使う場合）
     - DUCKDB_PATH（例: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、例: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、例: data/paper_trading.db）
     - LOG_LEVEL（例: INFO）
     - KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動で消すか。開発用）
4. データディレクトリ
   - デフォルトでは data/ 以下にファイルを作成します（SQLite / DuckDB / pid / flags）
   - 必要に応じて .env でパスを変更
5. 設定検証
   - python -m kabusys.validate_config
   - --strict オプションで警告もエラー扱いにできます

## 使い方（主要コマンド）
- 環境ウィザード（.env の作成／更新）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 発注エンジン起動（Execution）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合、paper_trading 用 SQLite に記録し実際の注文は行いません
    - 起動時に PID ファイル (data/execution.pid 等) を書きます
    - 停止は data/stop_requested.flag または Kill Switch（data/kill.flag）で行います
- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で指定可能（例: MONITOR_POLL_INTERVAL=30）
- Paper Trading レポート生成（ログ解析）
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD, --to YYYY-MM-DD, --db PATH
- AI 機能（プログラムから利用）
  - ai.score_news(conn, target_date, api_key=None)
    - DuckDB 接続と target_date を渡す。api_key を None にすると OPENAI_API_KEY 環境変数を参照
  - ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - 同上
  - 実行時は OpenAI API キーとネットワークが必要。失敗時はフェイルセーフにより中立スコアで継続します。
- ストップ方法（手動）
  - data/stop_requested.flag を作成すると run_monitoring / run_execution のループは検知して終了します（各スクリプトの参照パスに依存）
  - KillSwitch により data/kill.flag が書き込まれると ExecutionEngine に停止指示が出ます

## 環境変数（主要）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API のトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI を使う場合に必要
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1）

自動 .env 読み込み
- プロジェクトルート（.git または pyproject.toml がある場所）から .env を自動読み込みします。
- 自動ロードを無効にする: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

## 注意点 / 運用上のポイント
- paper_trading 環境は本番 DB と分離される設計です（PAPER_TRADING_SQLITE_PATH）。
- Monitoring は本来本番用の監視を意識しており、monitoring は常に本番 sqlite_path を参照する実装箇所があります（コード上の扱いに注意）。
- PID ファイルや flag ファイルは data/ 以下に出力されます。自動化された運用ではこれらのパスを適切に管理してください。
- OpenAI 呼び出しは API エラーやレート制限に対してリトライやフォールバックを実装していますが、APIキー・課金制限には注意してください。
- production（KABUSYS_ENV=live）の場合は LINE 通知設定等の確認を行ってください（validate_config でガードあり）。

## ディレクトリ構成（抜粋）
以下はこのコードベースで確認できる主要ファイル／パッケージの構成（src/kabusys 配下）。実際には他にもモジュールが存在する想定です。

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理
  - config_setup.py           — .env 対話ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py  — Paper Trading 検証レポート
  - ai/
    - __init__.py
    - news_nlp.py              — ニュース NLP（OpenAI 呼び出し）
    - regime_detector.py       — レジーム判定（MA + マクロ NLP）
  - monitoring/
    - monitoring_db.py        — SQLite テーブル定義 / 永続化層
    - system_monitor.py       — CPU/メモリ/プロセス/DuckDB データ鮮度監視
    - trade_monitor.py        — 注文滞留 / 約定異常チェック
    - risk_monitor.py         — ドローダウン / ポジション上限監視
    - kill_switch.py          — KillSwitch 制御（data/kill.flag）
    - monitoring_engine.py    — 各 Monitor を束ねるエンジン
    - alert_manager.py        — （アラート送信ロジック: 実装参照）
  - portfolio/
    - portfolio_builder.py    — 候補選定、重み計算
    - position_sizing.py      — 発注株数計算（単元丸め・スケールダウン）
    - risk_adjustment.py      — セクター上限・レジーム乗数
    - __init__.py
  - research/
    - factor_research.py      — momentum / volatility / value 等の計算（DuckDB）
    - feature_exploration.py  — forward returns / IC / 統計サマリ
    - __init__.py
  - utils/
    - process_priority.py     — プロセス優先度 / CPU affinity 設定ユーティリティ
    - __init__.py
  - execution/                — 発注エンジン関連（OrderManager, BrokerFactory 等）
  - data/                     — データ関連モジュール（prices_daily など）（別ファイル群）
  - monitoring、execution 等の詳細実装は該当ファイルを参照してください。

## よくある操作例
- 監視ループを 30 秒間隔で起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper Trading レポート期間指定:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- OpenAI を使ってニューススコアをプログラム的に計算（例）:
  - DuckDB 接続を作成して kabusys.ai.news_nlp.score_news(conn, date(2026,4,1), api_key="sk-...")

## 開発・貢献
- コードはモジュール単位に分離されており、ユニットテストを用意しやすい設計（純粋関数の比率が高い）。
- AI 部分は外部サービスに依存するため、テストでは API 呼び出し部分をモックすることを推奨します。
- 重要: .env を絶対にリポジトリにコミットしないでください（README 内や .gitignore で注意しています）。

---

何か追加で README に加えたい情報（依存関係の厳密なバージョン、実行例のログ、運用用 systemd サービス定義 など）があれば教えてください。必要に応じて追記・整形します。