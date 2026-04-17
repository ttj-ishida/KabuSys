# KabuSys

日本株自動売買システムのコアライブラリ群および運用ユーティリティ群です。  
このリポジトリには実行エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、リサーチ、AI（ニュースセンチメント／レジーム判定）などのコンポーネントが含まれます。

## 概要
- 実運用を想定したモジュール設計（本番・ペーパートレード分離、永続化は SQLite / DuckDB）
- 監視ループとアラート（LINE Push）機能
- ExecutionEngine による注文管理・リスク管理・リコンシリエーション
- Portfolio 構築ロジック（候補選定・重み付け・ポジションサイズ算出）
- Research 用のファクター計算（DuckDB 上の prices_daily/raw_financials を利用）
- AI（OpenAI）を使ったニュースセンチメント評価・市場レジーム判定
- 運用支援ツール（Paper Trading 検証レポート、Streamlit ダッシュボード）

## 主な機能一覧
- 実行
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV に応じて本番 / ペーパートレードを切替）
  - Broker クライアント抽象化（BrokerClientFactory）
  - 発注の状態管理、再起動時のリコンシリエーション
- 監視
  - run_monitoring.py: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔調整）
  - MonitoringEngine: System / Trade / Risk 各 Monitor の集約
  - AlertManager: LINE へ通知（クールダウン管理）
  - KillSwitch: リスク条件で stop flag（data/kill.flag）を書き、ExecutionEngine を停止
  - Streamlit ダッシュボード（data/monitoring.db を参照）
- Portfolio
  - 候補選定、等重／スコア重み、ポジションサイズ計算、セクター制限、レジーム乗数
- Research
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を利用）
  - 将来リターン、IC（Spearman）などの分析ユーティリティ
- AI
  - news_nlp.score_news: OpenAI を使ってニュースの銘柄別センチメントを ai_scores に書き込み
  - regime_detector.score_regime: MA とマクロニュースを組み合わせて market_regime を更新
- ツール
  - tools/paper_verification_report.py: Paper Trading DB を集計して検証レポートを出力

## 要件
- Python 3.9+
- 主な依存パッケージ（コード内で利用）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（ダッシュボード利用時）
- SQLite（Python 標準ライブラリ）

（実際の requirements.txt は本リポジトリに含まれていないため、下記のようにインストールしてください）
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil requests openai streamlit
```

## セットアップ手順
1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```
2. 仮想環境作成・依存インストール（上記参照）
3. 環境変数の準備
   - プロジェクトルートに `.env`（または `.env.local`）を置くと自動読み込みされます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可）。
   - 主要な環境変数（例）
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - OPENAI_API_KEY (AI 機能利用時必須)
     - KABUSYS_ENV: development | paper_trading | live  （デフォルト: development）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - DUCKDB_PATH（分析用 DuckDB、デフォルト: data/kabusys.duckdb）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（AlertManager 用。未設定時は送信をスキップ）
     - PAPER_FILL_MODE（paper_trading のモック約定動作: instant | partial | never | reject、デフォルト: instant）
     - MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔（秒）を上書き、デフォルト 60）
4. data ディレクトリの作成
   ```
   mkdir -p data
   ```
   （必要に応じて初期 DB ファイルを配置）

## 使い方

### ExecutionEngine（発注エンジン）を起動
- 本番（または development）環境で起動（DEFAULT: 本番 DB 使用）
```
python -m kabusys.run_execution
```
- ペーパートレードで起動（本番 DB と分離）
```
export KABUSYS_ENV=paper_trading
python -m kabusys.run_execution
```
- 実行中に停止させたい場合はプロセスに対して data/stop_requested.flag を作成すると（run_execution/run_monitoring のループが検知して停止処理を行います）：
```
touch data/stop_requested.flag
```

### Monitoring（監視ループ）を起動
```
python -m kabusys.run_monitoring
```
- ポーリング間隔を変更するには環境変数で上書き：
```
export MONITOR_POLL_INTERVAL=30
python -m kabusys.run_monitoring
```
- Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して監視ログを残します（ただし run_execution の paper_trading は分離）。

### Streamlit ダッシュボード（監視 UI）
- 起動コマンド（監視 DB を読み取り専用で開く）
```
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```
- DB が未作成またはロック中の場合はエラーメッセージが表示されます。

### Paper Trading 検証レポート
- デフォルト DB（data/paper_trading.db）を対象にレポートを出力：
```
python -m kabusys.tools.paper_verification_report
```
- 期間指定や DB を指定する例：
```
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db
```

### AI / Research API の利用（ライブラリ呼び出しとして）
- news_nlp.score_news や regime_detector.score_regime は DuckDB 接続と target_date を受け取る純関数です。簡単な使用例（スクリプト内で呼ぶ）：
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect('data/kabusys.duckdb')
n_written = score_news(conn, target_date=date(2026,4,15), api_key='YOUR_OPENAI_API_KEY')
score_regime(conn, target_date=date(2026,4,15), api_key='YOUR_OPENAI_API_KEY')
```
- OPENAI_API_KEY を環境変数に設定しておけば api_key を None にして呼べます。

### 停止 / キルフラグ
- 実行中エンジンを強制停止（KillSwitch トリガー）したい場合は `KILL_FLAG` を書きます（KillSwitch は内部基準で data/kill.flag を書きます）。手動で書いても ExecutionEngine は起動時にオプションを見て処理を行います。
- run_execution/run_monitoring は data/stop_requested.flag を検知して穏やかに終了します。

## 環境変数／Settings のポイント
- Settings クラス経由で環境変数を管理（.env/.env.local 自動読み込み）。自動ロードを止めるには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- KABUSYS_ENV 値は "development" / "paper_trading" / "live" のいずれか。paper_trading の場合、Execution 用の SQLite は PAPER_TRADING_SQLITE_PATH を使い完全に分離されます。
- PAPER_FILL_MODE（ペーパートレードの約定動作）は instant/partial/never/reject のいずれか。

## ディレクトリ構成
（主なファイル・モジュールのみ抜粋）

```
src/kabusys/
├── __init__.py
├── config.py                         # 環境変数・設定管理
├── run_execution.py                  # ExecutionEngine 起動スクリプト
├── run_monitoring.py                 # SystemMonitor ポーリングループ起動スクリプト
├── tools/
│   ├── __init__.py
│   └── paper_verification_report.py   # Paper Trading 検証レポート
├── execution/
│   ├── order_manager.py
│   ├── order_repository.py
│   ├── reconciler.py
│   └── ...                           # Broker / Engine 等（省略）
├── monitoring/
│   ├── __init__.py
│   ├── monitoring_db.py
│   ├── system_monitor.py
│   ├── trade_monitor.py
│   ├── risk_monitor.py
│   ├── monitoring_engine.py
│   ├── alert_manager.py
│   ├── kill_switch.py
│   └── streamlit_dashboard.py
├── portfolio/
│   ├── __init__.py
│   ├── portfolio_builder.py
│   ├── position_sizing.py
│   └── risk_adjustment.py
├── research/
│   ├── __init__.py
│   ├── factor_research.py
│   └── feature_exploration.py
├── ai/
│   ├── __init__.py
│   ├── news_nlp.py
│   └── regime_detector.py
├── utils/
│   ├── __init__.py
│   └── process_priority.py
└── data/                              # 実行時に使用される SQLite / DuckDB / flag ファイル等
    ├── monitoring.db
    ├── kabusys.duckdb
    ├── paper_trading.db
    ├── execution.pid
    ├── stop_requested.flag
    └── kill.flag
```

## 運用時の注意
- 監視（Monitoring）は本番監視 DB（SQLITE_PATH）を使用します。run_execution の paper_trading モードでは発注 DB を分離していますが、監視 DB は共有する想定のため注意してください。
- OpenAI API を使う機能は API 利用料金・呼び出し失敗（429/5xx）への対処（リトライ・フォールバック）を実装していますが、API キーやコスト管理は運用者で行ってください。
- Process priority / CPU affinity の設定はプラットフォーム依存です。権限不足で設定が失敗してもログに警告が出るだけで処理は継続します。
- DB マイグレーション（monitoring_db.init_monitoring_db）は冪等で実行され、既存テーブルへカラム追加の簡易マイグレーション処理を含みます。

## 開発
- ユニットテストを追加して各純粋関数（portfolio / research 等）を検証してください。AI 呼び出し部分はモック化してテストすることを推奨します（ファイル内にモック用の差し替え箇所を想定）。
- Settings の .env パーサは Bash 風の記法（export など）に対応しています。テスト実行時に環境の上書きを避けたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

README はここまでです。必要であれば「導入手順（デプロイ用 systemd サービス定義・Docker 化）」や「API / CLI の詳細ドキュメント」など、より運用向けの章を追加できます。どの情報を優先して追記しますか？