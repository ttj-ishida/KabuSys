# KabuSys — README (日本語)

バージョン: 0.1.0

KabuSys は日本株向けの自動売買フレームワークです。本リポジトリには以下を含みます：注文実行エンジン（ExecutionEngine）、監視機能（Monitoring）、ポートフォリオ構築ロジック、リサーチ用ファクター計算、ニュース NLP を用いた AI モジュール、検証用ツール類など。設計思想としては「本番環境と検証環境の分離」「ルックアヘッドバイアスの排除」「外部 API 呼び出しは明示的に制御」などを重視しています。

主な責務
- 注文の生成・送信・状態管理（Execution）
- リコンシリエーション（再起動後の同期）
- 監視（システム状態、注文滞留、リスク監視、LINE 通知）
- ポートフォリオ構築（候補選定、重み付け、株数決定、セクター制約）
- リサーチ（ファクター計算、IC 計算など）
- AI モジュール（ニュースからのセンチメント付与、レジーム判定）
- 検証ツール（Paper Trading レポート、Streamlit ダッシュボード）

---

## 機能一覧

- Execution
  - Broker クライアント抽象化・ファクトリ
  - OrderManager（状態遷移、重複防止）
  - Reconciler（OrderSent の復旧、ブローカ―ポジションとローカルの差分検出）
  - RiskManager（取引制限）

- Monitoring
  - SystemMonitor（CPU/メモリ/ディスク、プロセス死活、データ鮮度）
  - TradeMonitor（滞留注文、約定異常）
  - RiskMonitor（ドローダウン・ポジション上限監視）
  - KillSwitch（flag ファイルによる Execution 停止シグナル）
  - AlertManager（LINE Push による通知、クールダウン管理）
  - MonitoringEngine（各 Monitor の束ね実行）
  - Streamlit ダッシュボード（監視データ可視化）

- Portfolio
  - 候補選定（スコア順）
  - 重み計算（等分・スコア加重）
  - ポジションサイズ計算（リスクベース・等分ベース、単元株丸め）
  - セクター集中制限、レジーム乗数

- Research
  - Momentum / Volatility / Value ファクター計算（DuckDB 経由）
  - 将来リターン、IC、統計サマリ

- AI
  - news_nlp: OpenAI を使った銘柄別ニュースセンチメント付与（ai_scores テーブル書込）
  - regime_detector: マクロ記事 + ETF ma200 を組み合わせた日次レジーム判定

- Tools
  - paper_verification_report: Paper Trading 用の検証レポート生成
  - streamlit_dashboard: 監視ダッシュボード

---

## 前提条件 / 必要環境

- Python 3.10+
  - typing の | 演算子や厳密な型アノテーションを利用しています。
- SQLite（標準で同梱）
- DuckDB（duckdb Python パッケージ）
- 推奨インストールパッケージ（例）
  - duckdb
  - psutil
  - requests
  - streamlit（ダッシュボード利用時）
  - openai（AI モジュール利用時）
- ネットワーク（OpenAI / LINE API を利用する場合）

インストール例（仮に requirements.txt があれば）:
```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# requirements.txt がない場合:
pip install duckdb psutil requests
pip install streamlit openai  # 必要に応じて
```

---

## 設定（環境変数）

KabuSys は環境変数（または .env / .env.local）で設定します。自動ロードの挙動は Settings モジュールに実装されています。

読み込み優先順位:
1. OS 環境変数（最優先）
2. .env.local（存在すれば上書き）
3. .env

自動ロードを無効化する:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主要な環境変数（主なものを抜粋）:
- KABUSYS_ENV: 起動環境（development / paper_trading / live、デフォルト: development）
  - paper_trading の場合、MockBrokerClient を使用し database を data/paper_trading.db に分離します。
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector 使用時）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の約定挙動（instant / partial / never / reject、デフォルト: instant）
- PID_FILE_PATH: ExecutionEngine 用 PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: KillSwitch の flag ファイルパス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: ExecutionEngine 起動時に kill.flag を自動クリアするフラグ（"1" で有効）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）

監視特有のしきい値（環境変数で上書き可）:
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT（%）

MONITOR_POLL_INTERVAL:
- run_monitoring のポーリング間隔（秒）。環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。
- 0 以下の値や不正な値はデフォルトにフォールバックします。

PAPER_TRADING の挙動:
- KABUSYS_ENV=paper_trading の場合、Execution は本番 DB を使わず PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使います。本番 DB と完全に分離します。

---

## セットアップ手順（簡易）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成と依存インストール
   ```
   python -m venv .venv
   source .venv/bin/activate
   pip install duckdb psutil requests
   pip install streamlit openai  # 必要に応じて
   ```

3. 環境変数設定
   - プロジェクトルートに .env を作成するか、OS 環境変数で設定してください。
   - 例 (.env):
     ```
     KABUSYS_ENV=development
     JQUANTS_REFRESH_TOKEN=xxxxx
     KABU_API_PASSWORD=yyyyy
     OPENAI_API_KEY=zzzzz
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     ```

4. DB 初期化（監視 DB のスキーマ作成）
   run_monitoring / run_execution 実行時に init_monitoring_db() が呼ばれて自動で作成されます。手動で作る場合:
   ```py
   python -c "import sqlite3; from kabusys.monitoring.monitoring_db import init_monitoring_db; conn=sqlite3.connect('data/monitoring.db'); init_monitoring_db(conn); conn.close()"
   ```

5. data ディレクトリ作成（必要に応じて）
   ```
   mkdir -p data
   ```

---

## 使い方

基本的な起動コマンド例:

- 監視ループ起動（SystemMonitor の単体スクリプト）
  ```
  python -m kabusys.run_monitoring
  ```
  オプション:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- ExecutionEngine 起動（実際の発注 / paper_trading の場合は MockBroker）
  ```
  python -m kabusys.run_execution
  ```
  注意:
  - KABUSYS_ENV=paper_trading を設定すると paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）を使用します。
  - 実行前に kill.flag を削除したい場合は KILL_FLAG_CLEAR_ON_START=1 を設定するか、手動でファイルを削除してください。

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を指定する場合:
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- Streamlit ダッシュボード（監視 UI）
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- AI モジュール呼び出し（スクリプト内から）
  - ニューススコア付与:
    from kabusys.ai.news_nlp import score_news
    score_news(duckdb_conn, target_date, api_key=...)
  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date, api_key=...)

注意事項 / 運用上のヒント:
- プロセス優先度設定 (set_process_priority) は OS によっては権限が必要です。PermissionError や AccessDenied が出た場合は実行ユーザの権限を確認してください。
- OpenAI API 使用時はレート制限やエラー（429 / 5xx）に対するバックオフが入っていますが、API キーの管理とコストに注意してください。
- kill.flag による停止は冪等で、既存の場合は書き込みをスキップします。Execution 側は flag の存在を検出して停止する実装を想定しています。
- MONITOR_POLL_INTERVAL は不正値が設定されるとログに警告が出て 60 秒にフォールバックされます。

---

## ディレクトリ構成

（主要ファイル・ディレクトリのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                        -- 環境変数 / Settings
  - run_monitoring.py                -- SystemMonitor ポーリング起動スクリプト
  - run_execution.py                 -- ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py   -- Paper Trading 検証レポート
  - monitoring/
    - __init__.py
    - monitoring_db.py               -- SQLite 永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - reconciler.py
    - (その他 Execution 関連モジュール)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - utils/
    - process_priority.py
    - __init__.py
  - data/ (期待される出力 DB ファイル・データディレクトリ)
    - kabusys.duckdb (デフォルト)
    - monitoring.db (監視用 SQLite)
    - paper_trading.db (paper_trading 用 SQLite)

---

## よくあるトラブルシューティング

- psutil のプロセス優先度設定で AccessDenied:
  - Linux: 一部の nice 値（負の値）を設定するには root 権限が必要です。運用時は systemd などで優先度を制御することを検討してください。

- OpenAI 呼び出しでエラーや JSON 解析失敗:
  - レスポンスの整形やモデルの挙動によりパースに失敗する場合があります。ログに警告が出力され、失敗したチャンクはスキップされます（フェイルセーフ）。

- DB ファイルが読み込み専用で開けない（Streamlit で URI read-only 指定時）:
  - ファイルパスが正しいか、権限が正しいかを確認してください。また別プロセスがロックしている場合は競合に注意してください。

---

## 貢献・拡張ポイント（参考）

- ポートフォリオ設計: 銘柄別 lot_size のサポート、手数料モデルの強化
- Execution: ブローカー固有のコネクタ追加（kabu API 実装など）
- Research: pandas 等導入による計算高速化（現状は標準ライブラリ + DuckDB）
- テスト: ユニットテスト・統合テストの追加（mock を使った API テスト等）

---

README は以上です。必要であれば、実行例や .env.example のサンプル、systemd / docker-compose 用の起動例なども追記します。どの情報を追加したいか教えてください。