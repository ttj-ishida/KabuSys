# KabuSys

KabuSys は日本株向けの自動売買システムのプロトタイプです。本リポジトリには、発注エンジン（ExecutionEngine）、監視（Monitoring）、リサーチ（ファクター算出 / 特徴量探索）、AI ベースのニュースセンチメント判定、ポートフォリオ構築ロジックなどが含まれます。

以下はこのコードベースの概要、機能、セットアップ手順、使い方、ディレクトリ構成の説明です。

---

## プロジェクト概要
- 目的: 日本株の自動売買シグナルに基づく発注・ポジション管理、自動リコンシリエーション、運用中の監視・アラート、研究用ファクター計算、ニュースNLP によるセンチメント評価を提供する。
- 設計方針:
  - 発注・監視ロジックは DB（SQLite / DuckDB）経由で状態永続化。
  - Paper trading（検証）と Live（本番）は DB を分離。KABUSYS_ENV によって挙動を切り替え。
  - OpenAI（gpt-4o-mini）を用いたニュースセンチメント・レジーム判定機能を備えるが、API 失敗時は安全側にフォールバックする実装。
  - 主要ロジックは副作用を最小限にした純粋関数で実装（テスト容易性向上）。

---

## 主な機能一覧
- Execution（発注系）
  - Signal Queue ベースの発注処理（シグナル処理ウィンドウ + プッシュドレイン）
  - OrderManager によるクラッシュ耐性のある 2 相永続化フロー（OrderSent の取り扱い）
  - Reconciler による再起動時の自動同期（ブローカー照合）
  - RiskManager による Gate チェック（ポジション上限 / ドローダウン / レート制限等）
  - Paper trading モード（MockBrokerClient を想定、DB を本番と分離）

- Monitoring（監視系）
  - SystemMonitor: CPU/メモリ/ディスク、プロセス PID、データ鮮度チェック
  - TradeMonitor: 注文滞留 / 約定異常価格検出
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新
  - KillSwitch: 条件を満たしたらフラグファイルを書いて ExecutionEngine 停止指示
  - AlertManager: LINE Messaging API による通知（クールダウン制御）
  - Streamlit ベースの監視ダッシュボード（read-only で monitoring DB を参照）

- Research（研究系）
  - ファクター計算: Momentum / Volatility / Value（DuckDB 上の prices_daily / raw_financials を参照）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー

- Portfolio（構築ロジック）
  - 銘柄選定、等金額/スコア加重、リスクベースの株数算出（lot 単位で丸め）
  - セクターキャップ適用、レジーム乗数算出

- AI
  - news_nlp: raw_news を集約して OpenAI に送信し銘柄ごとのセンチメントを ai_scores テーブルに書き込み
  - regime_detector: ETF (1321) の MA200 とマクロニュースの LLM センチメントを合成して市場レジーム判定

- ユーティリティ
  - Settings（環境変数ロード / .env 自動読み込み）
  - プロセス優先度 / CPU affinity 設定ユーティリティ
  - MonitoringDB（SQLite 操作用ラッパー）

---

## 要件 (推奨)
- Python 3.10 以上（型ヒントに `|` を使用しているため）
- 必要な主要ライブラリ（例）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（ダッシュボード実行時）
- SQLite（Python 標準ライブラリに同梱）
- （任意）LINE Messaging API トークン、OpenAI API キー 等

依存はプロジェクト側に requirements.txt / pyproject.toml がある想定です。無ければ手動でインストールしてください:

例:
```
pip install duckdb psutil requests openai streamlit
```

開発時はプロジェクトルートにいる前提で次のようにインストールすることが推奨されます:
```
pip install -e .
```
（pyproject.toml が存在する場合）

---

## セットアップ手順（初期）
1. リポジトリをクローンし、プロジェクトルートへ移動
2. 仮想環境の作成・有効化（推奨）
3. 依存パッケージをインストール（上記参照）
4. .env を作成（下記の最小必須項目を参照）
5. data ディレクトリを作成（必要に応じて）
   ```
   mkdir -p data
   ```

### .env（例）
必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（これらはシステムに応じて必要）
推奨/オプション: OPENAI_API_KEY, KABUSYS_ENV, PAPER_FILL_MODE, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID

例（.env）:
```
# 実運用では .env.local 等で OS 環境変数を上書きする構成も可能
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
OPENAI_API_KEY=sk-...
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=
PAPER_FILL_MODE=instant
SQLITE_PATH=data/monitoring.db
DUCKDB_PATH=data/kabusys.duckdb
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
```

- 自動 .env ロードは Settings モジュールで行われます。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## 使い方（実行方法）

※ 実行方法は開発環境の配置に依存します。`src` を PYTHONPATH に含めるか、パッケージをインストールして実行してください。

- ExecutionEngine（発注エンジン）起動
  - 本番 / 開発 / paper_trading は環境変数 `KABUSYS_ENV` で指定します（allowed: development, paper_trading, live）。
  - paper_trading の場合、MockBrokerClient を使い `data/paper_trading.db` を使用します（本番 DB と分離）。

  実行例（モジュール実行）:
  ```
  # PYTHONPATH=src など適宜設定
  python -m kabusys.run_execution
  ```

  注意:
  - 起動直後にプロセスの優先度を "high" に設定します（権限により失敗する場合は警告ログ）。
  - PID ファイル（デフォルト: data/execution.pid）を用いてプロセス生存チェックを行います。
  - 起動時や実行中に `data/kill.flag` が存在すると kill シグナル扱いになります。削除するには手動で rm するか KillSwitch.clear() を呼びます。

- Monitoring（監視ループ）起動
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  ```
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```

  - Monitoring は常に本番 sqlite_path を使って監視用テーブルを初期化します（init_monitoring_db）。

- Streamlit 監視ダッシュボード
  - 監視 DB を読み取り専用で表示する簡易ダッシュボードがあります。
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- AI 関連（ニュース NLU / レジーム判定）
  - OpenAI API キーを環境変数 `OPENAI_API_KEY` に設定しておく必要があります。
  - news_nlp.score_news(conn, target_date, api_key=None) / regime_detector.score_regime(conn, target_date, api_key=None) を呼び出して使用します（DuckDB 接続を渡す）。

- ローカル DB の初期化
  - monitoring 用テーブルは実行時に自動作成されます（init_monitoring_db）。
  - DuckDB のテーブル（prices_daily, raw_financials, raw_news など）はデータ投入が必要です（ETL パイプラインが別途必要）。

---

## 環境変数の主な一覧（Settings）
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API
- KABU_API_PASSWORD: kabu API パスワード
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時必須）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: AlertManager（LINE）用
- SQLITE_PATH: 監視用 sqlite（デフォルト data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: paper trading 用 sqlite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: paper trading 時の約定モード（instant / partial / never / reject）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START / CPU/MEM/DISK 閾値 等

---

## ディレクトリ構成（主要ファイルと役割）
以下は src/kabusys 以下の主要モジュールと簡単な説明です。

- src/
  - kabusys/
    - __init__.py
      - パッケージ情報（__version__）
    - config.py
      - Settings クラス：.env / 環境変数読み込み、各種設定プロパティ
    - run_execution.py
      - ExecutionEngine 起動スクリプト（KABUSYS_ENV による DB 切替）
    - run_monitoring.py
      - SystemMonitor ポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL 対応）
    - portfolio/
      - portfolio_builder.py：銘柄選定 / 重み計算
      - position_sizing.py：株数計算、リスク・aggregate cap 処理
      - risk_adjustment.py：セクターキャップ / レジーム乗数
      - __init__.py：公開 API
    - execution/
      - execution_engine.py：ExecutionEngine（シグナル処理 / ドレイン）
      - order_manager.py：OrderManager（state machine 外向き API）
      - order_repository.py：SQLite ベースの注文永続化（not shown in snippet）
      - reconciler.py：再起動時の照合・リコンシリエーション
      - reconciler 等
    - monitoring/
      - monitoring_db.py：SQLite テーブル作成 / CRUD ヘルパー（MonitoringDB）
      - system_monitor.py、trade_monitor.py、risk_monitor.py：各監視コンポーネント
      - monitoring_engine.py：複数モニタのポーリング統合
      - kill_switch.py：kill.flag 制御
      - alert_manager.py：LINE push 通知
      - streamlit_dashboard.py：監視ダッシュボード（streamlit）
      - __init__.py：公開 API
    - research/
      - factor_research.py：Momentum / Value / Volatility ファクター計算
      - feature_exploration.py：将来リターン / IC / 統計サマリ
      - __init__.py：公開 API
    - ai/
      - news_nlp.py：ニュースを LLM でセンチメント評価して ai_scores に格納
      - regime_detector.py：ETF MA200 とマクロニュースで市場レジーム判定
      - __init__.py：公開 API
    - utils/
      - process_priority.py：プロセス優先度 / CPU affinity 設定ユーティリティ
      - __init__.py

（注意）データ層（kabusys.data.*）や execution/broker_api 実装、order_repository 等の一部ファイルはここに示されたコードスニペット以外に存在する想定です。本 README は提示されたコードに基づく概要です。

---

## 運用上の注意 / トラブルシューティング
- Python のバージョンは 3.10 以上を推奨します（型ヒントに union 型などを使用）。
- OpenAI を利用する機能は API キーが必要です。API 呼び出しはリトライ・フォールバック実装があるものの、API 使用量・コストに注意してください。
- paper_trading モードでは本番 DB と明確に分離するよう設計されています。KABUSYS_ENV を誤って `live` にしないよう注意してください。
- Monitoring は監視 DB を初期化しますが、DuckDB のデータは別途構築する必要があります（prices_daily / raw_financials / raw_news など）。
- プロセス優先度や CPU affinity の設定は権限依存（特に nice 値の低減や Windows の高度な優先度設定）です。失敗すると警告ログが出ますが処理は継続します。
- kill.flag の存在は ExecutionEngine の発注ループにより検出されます。運用開始前に flag を削除することを確認してください。

---

README に記載のサンプルコマンドや環境変数は開発・検証目的の参考です。実運用では適切な構成管理・API キー保護・監査ログ・テストを行ってください。必要であれば README にデプロイ手順や CI、既知の制約（lot_size の拡張計画等）を追記します。