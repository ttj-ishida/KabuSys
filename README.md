# KabuSys

日本株向け自動売買システムのモジュール群。ポートフォリオ構築、ポジションサイズ計算、監視（Monitoring）、注文実行まわりのユーティリティ、研究用ファクター計算、LLM を使ったニュースセンチメント／レジーム判定などを含みます。

以下はこのリポジトリの概要・セットアップ・使い方・ディレクトリ構成のまとめです。

---

## プロジェクト概要

KabuSys は以下の主要機能を持つモジュール群です。

- シグナル → 注文の発行・管理（OrderManager / ExecutionEngine）
- 注文・約定の永続化（SQLite）と集計（DuckDB）
- 監視システム（SystemMonitor / TradeMonitor / RiskMonitor）とアラート（LINE 送信）
- Paper Trading 用の分離された DB と Mock ブローカー実行モード
- Streamlit ダッシュボードによる監視表示
- 研究用モジュール（ファクター計算・IC 計算など、DuckDB を利用）
- LLM（OpenAI）を使ったニュースセンチメント（ai.news_nlp）および市場レジーム判定（ai.regime_detector）
- テスト／検証用ツール（paper_verification_report など）

---

## 主な機能一覧

- ポートフォリオ構築
  - 候補選定（score / equal）
  - 重み計算（等金額・スコア重み）
  - ポジションサイズ算出（リスクベース・配分ベース）
  - セクター集中制限、レジーム乗数適用

- 監視（Monitoring）
  - システム状態（CPU/メモリ/ディスク、プロセス生存）を定期記録
  - 注文の滞留検出、約定価格異常検出
  - ドローダウン・ポジション数監視、Kill Switch（flag ファイルで Execution 停止）
  - LINE によるアラート（冷却時間あり）
  - Streamlit ダッシュボード（read-only 接続）

- 実行（Execution）
  - ブローカ抽象（BrokerClientFactory）
  - OrderManager / Reconciler による起動時リコンシリエーション
  - paper_trading モードでは MockBroker を使い data/paper_trading.db に記録（本番 DB と完全分離）

- 研究（Research）
  - Momentum / Volatility / Value 等のファクター計算（DuckDB 上で SQL）
  - 将来リターン・IC 計算・統計サマリ

- AI（LLM）
  - ニュースを銘柄別にまとめて OpenAI に送って -1.0〜1.0 のスコアを ai_scores に書き込む
  - マクロニュースと ETF ma200 乖離を合成して日次で market_regime を判定

- ユーティリティ
  - process priority / CPU affinity（psutil 利用）
  - .env 自動ロード（プロジェクトルート検出）と Settings 抽象化

---

## 必要条件（推奨）

- Python 3.10+
  - 型注釈に `|`（Union）を使用しているため Python 3.10 以上を推奨します
- SQLite（標準ライブラリ）
- 主要依存パッケージ（一例）:
  - psutil
  - duckdb
  - openai
  - requests
  - streamlit (ダッシュボード利用時)
- 追加（プロジェクトにより変動）

インストール例（pipenv / venv / poetry 等で仮想環境を推奨）:
```
pip install psutil duckdb openai requests streamlit
```

---

## セットアップ手順

1. リポジトリをクローン & 仮想環境を作成
2. 必要パッケージをインストール（上記参照）
3. data ディレクトリを作成（DB 保存用）
```
mkdir -p data
```
4. 環境変数を設定
   - プロジェクトルートに `.env` を置くと自動ロードされます（.env.local を優先して上書き）
   - 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定

必須 / 主要な環境変数（抜粋）:
- JQUANTS_REFRESH_TOKEN — 必須（J-Quants 用）
- KABU_API_PASSWORD — 必須（kabu API）
- OPENAI_API_KEY — ai.news_nlp / ai.regime_detector を使う場合は必須
- KABUSYS_ENV — 起動モード: `development`（デフォルト）| `paper_trading` | `live`
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH — paper trading 用 DB（デフォルト: data/paper_trading.db）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知用（任意）
- PID_FILE_PATH — デフォルト: data/execution.pid
- KILL_FLAG_PATH — デフォルト: data/kill.flag
- MONITOR_POLL_INTERVAL — 監視ループの秒間隔（run_monitoring 用、デフォルト 60）

例 .env（必要に応じて編集）:
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_kabu_password
OPENAI_API_KEY=sk-xxxx
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=
```

---

## 実行方法（主要なスクリプト・モジュール）

パッケージルートから Python モジュールとして実行することを想定しています。

- 監視ループ起動（SystemMonitor 単体）
```
python -m kabusys.run_monitoring
```
- 実行エンジン起動（ExecutionEngine）
```
python -m kabusys.run_execution
```
  - KABUSYS_ENV=paper_trading の場合、MockBroker を使用し PAPER_TRADING_SQLITE_PATH に記録します。

- Streamlit ダッシュボード（監視 DB を read-only で開く）
```
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```

- Paper Trading 検証レポート生成ツール
```
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# --db で DB パスを明示できます
```

- AI スコア／レジーム判定をプログラム的に呼ぶ
  - ai.news_nlp: kabusys.ai.score_news(conn, target_date, api_key=None)
  - ai.regime_detector: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続（duckdb.connect(...)）を渡して使用します。API キーは引数または環境変数 OPENAI_API_KEY を参照します。

モジュール特有の挙動:
- run_monitoring: 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書き可能（デフォルト 60）
  - 0 以下や不正な値は無視され、デフォルトにフォールバックします
- run_execution: 起動時に `Settings.is_paper` を確認し、paper_trading では paper_sqlite_path を使用

---

## 主要コンポーネントの説明（簡易）

- kabusys.config.Settings
  - .env/.env.local の自動読み込み（プロジェクトルート判定）
  - 設定値の抽象化（DB パス、閾値、環境など）
- kabusys.monitoring
  - MonitoringDB: SQLite を使った永続化（テーブル作成とマイグレーション含む）
  - SystemMonitor / TradeMonitor / RiskMonitor: 各種チェック
  - MonitoringEngine: 監視ループの統括（アラート送信・Kill Switch 評価）
  - AlertManager: LINE への通知（クールダウン管理）
  - streamlit_dashboard: 監視情報の可視化
- kabusys.execution
  - OrderManager / Reconciler / ExecutionEngine（起動・注文管理）
  - BrokerClientFactory により paper_trading では MockBroker を構成
- kabusys.portfolio
  - 候補選定・重み計算・リスク調整・ポジションサイズ計算（純粋関数群）
- kabusys.research
  - ファクター計算（momentum/volatility/value）および feature_exploration ユーティリティ
- kabusys.ai
  - news_nlp: 銘柄ごとにニュースを集約し OpenAI に投げてスコアを書き込む
  - regime_detector: ETF ma200 とマクロニュースを合成して日次レジーム判定

---

## ディレクトリ構成

（抜粋）src/kabusys 以下:

- __init__.py
- config.py
- run_monitoring.py
- run_execution.py

- ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py

- monitoring/
  - __init__.py
  - monitoring_db.py
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - monitoring_engine.py
  - alert_manager.py
  - kill_switch.py
  - streamlit_dashboard.py

- execution/
  - order_manager.py
  - reconciler.py
  - (その他 broker 関連モジュール等)

- portfolio/
  - __init__.py
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py

- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py

- monitoring/tools/
  - paper_verification_report.py

- utils/
  - __init__.py
  - process_priority.py

- data/（実行時に使用する、リポジトリルート直下の想定ディレクトリ）
  - kabusys.duckdb（デフォルト）
  - monitoring.db（SQLite、デフォルト）
  - paper_trading.db（paper_trading モード時に分離して使用）

---

## 注意点 / 運用メモ

- 環境分離
  - paper_trading モードは本番の SQLite DB とは別に動作するよう設計されています。PAPER_TRADING_SQLITE_PATH を確認してください。

- API キーの管理
  - OPENAI_API_KEY 等の機密情報は .env に入れるか環境変数で管理してください。`.env` を誤ってコミットしないよう注意してください。

- PID / Kill Flag
  - ExecutionEngine は起動時に PID を data/execution.pid に書く想定です。監視側はこの PID を参照してプロセス生存を評価します。
  - KillSwitch は data/kill.flag を書くことで ExecutionEngine 停止のシグナルを送ります。設定 `KILL_FLAG_CLEAR_ON_START=1` で起動時にフラグを自動削除できます。

- マイグレーション
  - monitoring_db.init_monitoring_db は既存 DB に対して冪等にテーブル作成や簡単なカラム追加（マイグレーション）を行います。

- 外部 API エラーの扱い
  - AI 呼び出し（OpenAI）では 429 / ネットワーク切断 / タイムアウト / 5xx に対する指数バックオフを実装しており、最終的に失敗した場合はフォールバックして継続します（例: macro_sentiment=0.0）。

---

必要であれば、README に次の点も追加できます：
- 依存パッケージの固定（requirements.txt / pyproject.toml 例）
- デプロイ手順（systemd ユニット例）
- 実行例のログ出力サンプル
- テストの書き方とユニットテスト実行方法

どれを追加しましょうか？