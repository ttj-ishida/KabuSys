# KabuSys

軽量な日本株自動売買フレームワークのサブセット実装です。戦略の研究・ファクター計算、発注エンジン、監視・アラート、LLM を用いたニュースセンチメント／レジーム判定などの機能を含みます。本リポジトリには主要なロジック（純粋関数群や監視/実行エンジン）が実装されています。

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方
  - 環境変数（.env）について
  - 実行エンジンの起動
  - 監視プロセスの起動
  - 監視ダッシュボード（Streamlit）
  - AI（ニュース NLP / レジーム判定）の利用
- ディレクトリ構成（主要ファイル説明）
- 注意事項 / トラブルシューティング

---

## プロジェクト概要

KabuSys は日本株向けの自動売買サブシステム群です。本コードベースは以下の領域をカバーします。

- ファクター計算・研究（DuckDB 上の時系列データ参照）
- ポートフォリオ構築（候補選定、重み算出、ポジションサイズ計算）
- 発注エンジン（Signal Queue ベース、OrderManager / ExecutionEngine）
- 発注のリコンシリエーション（再起動時の整合合わせ）
- 監視（システム／注文／リスク監視）、LINE による通知
- ニュースの LLM ベースセンチメント評価と市場レジーム判定
- ローカル永続化：SQLite（監視ログ等） + DuckDB（時系列・リサーチ用）

設計方針として、データベースはローカルファイルを使い、テストや paper_trading モード時は本番 DB と分離できるようになっています。外部サービス（kabu API / J-Quants / OpenAI / LINE）は設定次第で利用します。

---

## 機能一覧

主な機能（抜粋）:

- research
  - モメンタム / ボラティリティ / バリューなどのファクター計算（DuckDB）
  - 将来リターン・IC・統計サマリー等の探索ユーティリティ
- portfolio
  - 候補選定（スコア基準）、等金額／スコア加重配分
  - ポジションサイズ計算（リスクベース、lot丸め、aggregate cap）
  - セクター上限適用、レジーム乗数
- execution
  - OrderManager（DB 永続化を伴う安全な発注フロー）
  - ExecutionEngine（シグナル処理窓 + push ドレインループ）
  - Reconciler（再起動時の照合・自動復旧）
  - RiskManager（発注ゲート、サーキットブレーカー等）※設定値あり
- monitoring
  - SystemMonitor（CPU/メモリ/ディスク・データ鮮度・PID チェック）
  - TradeMonitor（滞留注文・約定価格異常検出）
  - RiskMonitor（ドローダウン / ポジション上限監視）
  - KillSwitch（フラグファイルで ExecutionEngine を停止）
  - AlertManager（LINE Push による通知、クールダウン管理）
  - MonitoringEngine（上記をまとめてポーリング）
  - Streamlit ダッシュボード（簡易 UI）
- ai
  - news_nlp: raw_news をまとめて OpenAI に投げ、銘柄ごとの ai_score を ai_scores テーブルへ書き込み
  - regime_detector: ETF(1321) の MA200 とマクロニュースの LLM スコアを合成して日次レジーム判定

---

## セットアップ手順

前提：
- Python 3.10+（typing の | を使用するため）
- 必要パッケージ（主要なもの）:
  - duckdb
  - psutil
  - openai
  - requests
  - streamlit
  - （その他：標準ライブラリのみで済む箇所もあります）

推奨手順（UNIX 系）:

1. 仮想環境作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 必要パッケージをインストール（プロジェクトに requirements.txt がない場合の例）
   ```
   pip install duckdb psutil openai requests streamlit
   ```

3. プロジェクトルートに .env を作成（省略可能だが環境変数の管理に便利）
   - 当リポジトリの config モジュールはプロジェクトルート（.git または pyproject.toml がある場所）から .env を自動読み込みします。
   - 自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

   例 (.env の最小例):
   ```
   KABUSYS_ENV=development
   JQUANTS_REFRESH_TOKEN=your_jquants_token
   KABU_API_PASSWORD=your_kabu_password
   OPENAI_API_KEY=sk-...
   LINE_CHANNEL_ACCESS_TOKEN=
   LINE_USER_ID=
   SQLITE_PATH=data/monitoring.db
   DUCKDB_PATH=data/kabusys.duckdb
   ```

4. データディレクトリ作成:
   ```
   mkdir -p data
   ```

5. DuckDB / SQLite の DB ファイルは起動時に自動で初期化されるテーブルがあります（monitoring 側は init_monitoring_db が呼ばれます）。

---

## 使い方

基本的な起動例・使い方を示します。

### 環境設定のポイント

- KABUSYS_ENV:
  - development（開発）
  - paper_trading（ペーパートレード: MockBroker を使用し、paper_sqlite_path に記録）
  - live（本番）
- PAPER_FILL_MODE（paper_trading 時の約定挙動）:
  - instant | partial | never | reject（デフォルト "instant"）
- MONITOR_POLL_INTERVAL:
  - 監視ポーリング間隔（秒）。run_monitoring スクリプトはこの環境変数で上書き可能（デフォルト 60）。
- PID / kill flag:
  - PID ファイル: Settings.pid_file_path（デフォルト data/execution.pid）
  - Kill flag: Settings.kill_flag_path（デフォルト data/kill.flag）
  - kill.flag が存在すると ExecutionEngine は起動/途中で停止合図を受けます。

必要な必須環境変数（不足時は Settings が ValueError を投げます）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

OpenAI を使う機能（news_nlp / regime_detector）を使う場合は `OPENAI_API_KEY` を設定してください。LINE 通知は `LINE_CHANNEL_ACCESS_TOKEN` と `LINE_USER_ID` を設定すると有効になります（未設定時はログにのみ出力され、送信はスキップされます）。

### 実行エンジンの起動

ExecutionEngine を起動すると、設定に応じてブローカークライアントを作成し発注を行います。paper_trading モードでは MockBrokerClient を使用し、paper_trading 用 DB（Settings.paper_sqlite_path）へ書き込みます。

起動例（ソースツリーから直接実行する場合）:
```
PYTHONPATH=src python src/kabusys/run_execution.py
```
またはパッケージとしてインストールした場合:
```
python -m kabusys.run_execution
```

起動時の挙動:
- プロセス優先度を "high" に設定しようとします（psutil による。権限により失敗しても警告に留まります）。
- DB 接続（paper_trading モードでは paper_sqlite_path を使用）
- ExecutionEngine.run_session() を呼び出してセッションを実行（シグナル窓: デフォルト 08:50–09:10、ドレイン 09:10–15:30 等。EngineConfig で変更可）
- PID ファイル（data/execution.pid）に PID を書く設計（Settings.pid_file_path）

注意: 起動前に `data/kill.flag` が存在する場合、kill_switch を発動する挙動があります。不要なら削除してください:
```
rm -f data/kill.flag
```

### 監視プロセスの起動

監視用ループ（SystemMonitor 等を定期実行）を起動する:
```
PYTHONPATH=src python src/kabusys/run_monitoring.py
```

オプション: MONITOR_POLL_INTERVAL を秒単位で指定できます（デフォルト 60）。
```
MONITOR_POLL_INTERVAL=30 PYTHONPATH=src python src/kabusys/run_monitoring.py
```

監視プロセスの役割:
- system_status / trade_logs / positions / risk_logs / dashboard テーブルを管理
- KillSwitch 判定で kill.flag を書き、ExecutionEngine を停止させる
- LINE 通知（AlertManager）を使って重要イベントを通知

監視 DB は Settings.sqlite_path（デフォルト data/monitoring.db）です。init_monitoring_db() によりテーブルが冪等に作成されます。

### 監視ダッシュボード（Streamlit）

簡易ダッシュボードを起動して監視 DB を参照できます:
```
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```
- Streamlit は監視 DB を read-only で開こうとします（起動していない場合はエラー表示）。

### AI（ニュース NLP / レジーム判定）機能

OpenAI API キーが必要です（OPENAI_API_KEY 環境変数か関数引数で指定）。

- ニュースの銘柄別センチメント評価（ai.news_nlp.score_news）:
  - DuckDB 接続を渡して特定日で実行すると、ai_scores テーブルに書き込みます。
  - 例（対話実行）:
    ```
    python -c "import duckdb, datetime; from kabusys.ai.news_nlp import score_news; conn=duckdb.connect('data/kabusys.duckdb'); print(score_news(conn, datetime.date.today()))"
    ```
- レジーム判定（ai.regime_detector.score_regime）:
  - ETF(1321) の MA200 とマクロニュースを用いて market_regime テーブルを書き込みます。
  - 例:
    ```
    python -c "import duckdb, datetime; from kabusys.ai.regime_detector import score_regime; conn=duckdb.connect('data/kabusys.duckdb'); score_regime(conn, datetime.date.today())"
    ```

両機能とも OpenAI のレスポンスに依存するため、ネットワークや API 限界に備えたリトライ・フォールバック処理を備えています（但し、APIキー未設定時は ValueError が発生します）。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要モジュールと役割（抜粋）です。

- src/kabusys/
  - __init__.py — パッケージ定義（バージョン）
  - config.py — 環境変数 / Settings 管理（.env 読み込みロジック含む）
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor 単体ポーリング起動スクリプト
- src/kabusys/portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 株数決定、aggregate cap, lot 丸め
  - risk_adjustment.py — セクター上限・レジーム乗数
- src/kabusys/research/
  - factor_research.py — momentum / volatility / value 計算（DuckDB）
  - feature_exploration.py — 将来リターン / IC / summary 集計
- src/kabusys/execution/
  - execution_engine.py — ExecutionEngine 本体（signal loop, push drain）
  - order_manager.py — Order 管理（永続化・send/sync/cancel）
  - reconciler.py — 起動時の注文／ポジション照合
  - order_repository.py, order_record.py, broker_api.py 等（注文 DB / レコード / ブローカー API 抽象）
- src/kabusys/monitoring/
  - monitoring_db.py — SQLite テーブル作成・永続化 API
  - system_monitor.py — システム状態・データ鮮度監視
  - trade_monitor.py — 注文滞留 / 約定異常監視
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag の管理
  - alert_manager.py — LINE 通知ラッパー
  - monitoring_engine.py — まとめてポーリングする Engine
  - streamlit_dashboard.py — Streamlit による簡易 UI
- src/kabusys/ai/
  - news_nlp.py — ニュース集約→OpenAI → ai_scores 書き込み
  - regime_detector.py — 市場レジーム判定処理

（上記は抜粋です。各モジュール内に詳細実装・ドキュメント文字列がありますので参照してください。）

---

## 注意事項 / トラブルシューティング

- Python バージョンは 3.10 以上を推奨（型ヒントの | 等を使用）。
- Settings の必須環境変数が未設定だと ValueError が投げられ起動しません。`.env.example` を参考に `.env` を用意してください（プロジェクトに例があれば）。
- run_* スクリプトは起動時にプロセス優先度を "high" に設定しようとします（psutil）。権限がないと警告になりますがスキップされます。
- OpenAI を使う関数は API レート制限・ネットワーク障害をリトライする実装がありますが、API キーが未設定だとエラーになります。
- paper_trading モード:
  - `KABUSYS_ENV=paper_trading` を指定すると MockBrokerClient が利用され、Orders は `Settings.paper_sqlite_path`（デフォルト data/paper_trading.db）へ記録されます。本番 DB と完全に分離されます。
- kill.flag:
  - 監視側から kill.flag が書かれると ExecutionEngine は停止シグナルとして検出します。起動時に flag をクリアしたい場合は手動で削除するか、Settings.kill_flag_clear_on_start を設定してクリア処理を有効化してください（コード上の利用場所を確認してください）。
- Streamlit が DB を開けない場合:
  - Streamlit 側は DB を read-only で開くため、監視 DB が存在しないか別のプロセスでロック中だとエラー表示になります。まずは MonitoringEngine を起動して DB が作成されているか確認してください。

---

必要に応じて README のサンプル .env、より細かい起動フラグや Engine の設定例（EngineConfig、RiskConfig のパラメータ）を追加できます。特定の項目（例：OrderRepository スキーマ、Broker API の実装例、CI テスト方法）を詳述したい場合は教えてください。