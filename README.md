# KabuSys

日本株向けの自動売買システム（ライブラリ／実行スクリプト群）。  
このリポジトリには、実行エンジン（ExecutionEngine）／監視（Monitoring）／ポートフォリオ構築、リサーチ、AI 補助モジュールなどの主要コンポーネントが含まれます。

> 注意: 本 README はソースコードの内容に基づく概要・使い方ガイドです。実運用では設定・APIキー・ブローカー接続等を十分に確認してください。

## プロジェクト概要
- 自動売買ロジック（ポートフォリオ構築、ポジションサイズ決定、リスク調整など）のユーティリティを提供。
- 実行エンジン（ExecutionEngine）と監視ループ（MonitoringEngine）を別プロセスで動かし、監視からの Kill Switch による自動停止をサポート。
- Paper Trading（ペーパートレード）モードをサポートし、本番 DB と分離して動作可能。
- DuckDB / SQLite を使った分析・監視データ永続化。
- ニュースの NLP（OpenAI）を用いた銘柄別センチメント評価、及びレジーム検出機能を提供（OpenAI API 必須）。

## 主な機能一覧
- 環境設定ウィザード（.env の対話式作成）: kabusys.config_setup
- 設定検証 CLI（.env / config/*.yaml の事前チェック）: kabusys.validate_config
- 実行エンジン起動スクリプト: run_execution.py
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を用い、data/paper_trading.db に記録（本番 DB と分離）
  - execution.pid の管理、stop フラグ検出による安全停止
- 監視ループ起動スクリプト: run_monitoring.py
  - SystemMonitor を定期ポーリングし system_status / risk_logs / trade_logs 等へ記録
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可（デフォルト 60 秒）
  - 監視は環境にかかわらず本番 sqlite_path を使用（監視 DB は本番の監視対象）
- 監視コンポーネント
  - SystemMonitor: CPU/メモリ/ディスク、プロセス PID・データ鮮度チェック
  - TradeMonitor: 滞留注文・約定異常価格検出
  - RiskMonitor: ドローダウン・ポジション上限チェック、ダッシュボード更新、リスクログ
  - KillSwitch / AlertManager 経由で自動停止や通知発行
- ポートフォリオ構築ユーティリティ
  - 候補選定、等金額/スコア加重配分、セクター上限適用、ポジションサイズ計算（単元株丸め等）
- リサーチ機能（DuckDB を使ったファクター計算、将来リターン、ICなど）
- AI モジュール
  - news_nlp: raw_news から OpenAI を用いた銘柄別センチメントスコア算出（ai_scores 書込み）
  - regime_detector: ETF（1321）MA200 とマクロニュースを組合せて日次レジーム判定
- ツール
  - paper_verification_report: ペーパートレード DB を元に検証レポート生成（稼働率・注文成功率・レイテンシ等）

## 要件
- Python >= 3.10（型記法に | を使用しているため）
- 主要依存ライブラリ（例）
  - duckdb
  - psutil
  - openai
  - （任意）PyYAML：validate_config の YAML 検証に使用
- その他、運用に応じたブローカークライアント等

例（pip インストール）:
pip install duckdb psutil openai PyYAML

## セットアップ手順（開発 / 初回導入向け）
1. リポジトリをクローン
   - git clone <repo-url>
2. Python 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install -r requirements.txt
     （requirements.txt がない場合は上記の主要依存を個別にインストール）
4. .env の作成
   - 対話式ウィザードで生成: python -m kabusys.config_setup
   - または手動で .env を作成（後述のサンプル参照）
5. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになる
6. data ディレクトリを作成（必要に応じて）
   - mkdir -p data
   - 実行時に自動作成される箇所もあるが、事前に用意しておくと権限等の問題を回避できます

## 簡単な使い方 / 実行コマンド
- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
    - 実行中は data/execution.pid に PID が書かれる（設定によりパス変更可）
    - 停止: data/stop_requested.flag を作成すると監視・実行ループが検知して終了します
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録
- 監視ループ起動（SystemMonitor を単独で回す）
  - python -m kabusys.run_monitoring
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60）
    - 監視は常に settings.sqlite_path（デフォルト data/monitoring.db）を使用
    - 停止検知: data/stop_requested.flag の存在でループ終了
- Paper Trading レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH を指定するか、環境変数 PAPER_TRADING_SQLITE_PATH を設定
- AI 関連（関数呼び出し）
  - news_nlp.score_news(conn, target_date, api_key=...) など。実際はスクリプトで直接呼ぶのではなく、Engine/スケジューラ等から呼び出す想定。
  - OpenAI API キー: 環境変数 OPENAI_API_KEY を設定するか、関数引数で渡す必要があります。

## 重要な環境変数（抜粋）
- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 実行環境
  - KABUSYS_ENV — development / paper_trading / live （デフォルト: development）
    - paper_trading: ペーパートレード専用 DB を使用（settings.paper_sqlite_path）
    - live: 本番（通知・kill 等に注意）
- DB / ファイルパス
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH — 監視 DB（monitoring）パス（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
  - PID_FILE_PATH — execution.pid のパス（デフォルト data/execution.pid）
  - KILL_FLAG_PATH — kill.flag のパス（デフォルト data/kill.flag）
- 動作制御
  - MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト 60）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアする（"1" で有効、デフォルト "0"）
- AI
  - OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector に必要）
- Paper Trading 挙動
  - PAPER_FILL_MODE — ペーパートレード時の約定挙動（instant|partial|never|reject、デフォルト "instant"）

サンプル（.env の一部）:
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
KABU_API_BASE_URL=http://localhost:18080/kabusapi
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...

（機密情報は .env を Git にコミットしないこと）

## 停止 / Kill Switch
- 実行中の ExecutionEngine / Monitoring ループを外部から止める方法:
  - data/stop_requested.flag を作成すると、run_monitoring / run_execution が検知して安全に終了します（両スクリプトで参照）。
- Kill Switch（監視側から ExecutionEngine を停止する仕組み）
  - KillSwitch は監視結果（ドローダウン超過やポジション上限超過）により KILL_FLAG_PATH（デフォルト data/kill.flag）を書き込みます。
  - Execution 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定していると起動時に自動でクリアされますが、本番では 0 を推奨します。

## データベース / 永続化
- monitoring_db (SQLite)
  - テーブル: system_status, trade_logs, positions, risk_logs, dashboard
  - init_monitoring_db() により冪等的に作成／簡易マイグレーションを行います
- paper_trading.db (SQLite)
  - KABUSYS_ENV=paper_trading 時に MockBrokerClient の注文履歴等を分離して保存
- duckdb (分析用)
  - prices_daily, raw_financials, raw_news, etc.（DuckDB 上のテーブルを参照してファクター計算や AI 処理を行う）

## ディレクトリ構成
以下は主要ファイルの一覧（src/kabusys 配下を抜粋）:

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数/設定管理
  - config_setup.py         — .env 対話式ウィザード
  - validate_config.py      — 設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - ai/
    - __init__.py
    - news_nlp.py           — ニュース NLP（OpenAI）
    - regime_detector.py    — 市場レジーム判定（OpenAI + MA200）
  - monitoring/
    - monitoring_db.py      — SQLite 永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py      — （アラート送信をまとめる想定）
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
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
  - (その他)
    - execution/            — ExecutionEngine 関連（order_manager, broker_factory, ...）
    - data/                 — データパイプライン・DB テーブル定義等（参照されるモジュール群）

（実際のリポジトリではさらに多くのモジュールが存在します）

## 開発上の注意・運用上の注意
- KABUSYS_ENV の設定を誤ると実際の発注が行われる可能性があります。live 環境では特に注意。
- .env は機密情報を含むため絶対に Git にコミットしないでください。
- OpenAI を用いるモジュールは API キー・料金に注意。API エラー時はフォールバックする実装（多くは 0.0 やスキップ）になっていますが、運用ポリシーを決めておいてください。
- monitoring は常に本番の monitoring DB（settings.sqlite_path）を使います。テスト時に別 DB を使う場合は設定で明示的に変更してください。
- process priority / cpu affinity の設定は OS により動作しない場合があります（psutil の権限やプラットフォーム依存）。

## 追加情報 / トラブルシューティング
- validate_config が PyYAML を見つけられない場合、config/*.yaml の検証はスキップされ警告になります。YAML 検証が必要なら PyYAML をインストールしてください。
- DuckDB / SQLite ファイルの親ディレクトリが存在しない場合は警告が出ますが、実行時に自動作成される箇所もあります。権限問題がある場合は事前にディレクトリを作成して権限を確認してください。

---

この README はコード内のドキュメント文字列・設計コメントに基づいて作成しています。より詳細な設計資料（PortfolioConstruction.md, StrategyModel.md 等）がある場合はそちらも参照してください。質問や特定の機能の使い方（例: ポジションサイズ計算のパラメータ調整や AI モジュールのテスト方法）が必要であれば教えてください。