# KabuSys

日本株向け自動売買システムのコードベース（README）。  
本ドキュメントはリポジトリ内の主要モジュールから抽出した情報に基づき、プロジェクト概要・機能・セットアップ・実行方法・ディレクトリ構成を日本語でまとめています。

注意: 実行には各種外部ライブラリ・APIキーが必要です。ここに書かれた内容はソースコードの仕様説明であり、運用前に設定値や権限を十分に確認してください。

---

## プロジェクト概要

KabuSys は日本株の自動売買プラットフォームのコアライブラリ群です。主な目的は以下です。

- 市場データ（DuckDB）に基づくファクター計算・リサーチ機能
- シグナル→ポートフォリオ構築→ポジションサイズ計算（Portfolio Construction）
- 注文の作成・送信・状態管理（Execution）
- 起動時リコンシリエーション（Reconciler）
- 監視 / アラートシステム（Monitoring）
- Paper Trading（模擬売買）用の分離された DB とモックブローカー
- ニュースの NLP によるセンチメント評価（OpenAI を利用）
- Streamlit ベースの監視ダッシュボード、検証レポート生成ツール 等

設計上のポイント:
- 多くのコンポーネントは副作用を持たない純粋関数群（特に portfolio / research）。
- 永続化は SQLite（監視ログ等）・DuckDB（時系列価格データ等）を使用。
- 環境ごとに挙動を切り替える（development / paper_trading / live）。

---

## 主な機能一覧

- research
  - ファクター計算: Momentum / Volatility / Value（DuckDB を使用）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ
- portfolio
  - 候補選定・重み算出（等金額・スコア加重）
  - セクター制約適用・レジーム乗数
  - ポジションサイズ計算（lot 単位丸め・aggregate cap）
- execution
  - OrderManager: 注文作成・注文送信・状態同期
  - Reconciler: 起動時の注文・ポジション照合で自動復旧
  - RiskManager / OrderRepository 等（詳細は実装参照）
- monitoring
  - SystemMonitor: CPU / メモリ / ディスク / データ鮮度 / 実行プロセス監視
  - TradeMonitor: 滞留注文・約定異常価格の検出
  - RiskMonitor: ドローダウン・ポジション上限監視
  - KillSwitch: フラグファイルを書いて ExecutionEngine 停止シグナルを送る
  - AlertManager: LINE Push による通知（クールダウン管理）
  - MonitoringEngine: 各モニタを束ねるポーリングエンジン
  - Streamlit ダッシュボード（read-only で monitoring DB を参照）
- ai
  - news_nlp: raw_news を LLM（OpenAI）で評価して ai_scores に登録
  - regime_detector: ma200 とマクロニュースを合わせて市場レジーム（bull/neutral/bear）を判定
- tools
  - paper_verification_report: Paper Trading 用の検証レポートを生成

---

## 動作環境・依存

推奨 Python バージョン: 3.10+（ソースで | 型等を使用）

主な Python パッケージ:
- duckdb
- psutil
- requests
- openai
- streamlit (ダッシュボード利用時)
- (標準ライブラリ) sqlite3, logging, argparse, typing, datetime など

インストール例:
- 仮想環境を作成してから:
  - pip install duckdb psutil requests openai streamlit

（プロジェクト配布に requirements.txt がある場合はそれに従ってください）

---

## 設定（環境変数 / .env）

本リポジトリは .env / .env.local の自動ロード機能を持ちます（プロジェクトルートに .git または pyproject.toml がある場合）。OS 環境変数が最優先です。自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主要な環境変数（抜粋）:

- KABUSYS_ENV: 起動環境（development / paper_trading / live）  
  - paper_trading の場合、MockBrokerClient を使用し DB を分離します
- JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必須な箇所あり）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須な箇所あり）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager（LINE通知）用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: Paper Trading の約定挙動 ("instant" | "partial" | "never" | "reject")
- PID_FILE_PATH: 実行プロセスの PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: kill flag（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）

Settings クラスに多数の設定が定義されています。詳細は `src/kabusys/config.py` を参照してください。未設定で必須なキーを参照すると ValueError が発生します。

例 .env（最小）:
```
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
JQUANTS_REFRESH_TOKEN=...
LINE_CHANNEL_ACCESS_TOKEN=...
LINE_USER_ID=...
```

---

## セットアップ手順（簡易）

1. リポジトリをクローン / 取得
2. 仮想環境作成（推奨）
   - python -m venv .venv && source .venv/bin/activate
3. 必要パッケージをインストール
   - pip install duckdb psutil requests openai streamlit
4. .env を作成して必要な環境変数を設定（上記参照）
5. データディレクトリを作成（必要に応じて）
   - mkdir -p data
6. DuckDB / SQLite の初期スキーマは実行時に必要に応じて作成されます（monitoring は init_monitoring_db を通じて自動作成）

---

## 実行方法（主要スクリプト）

以下はいずれもソース配下のモジュールとして実行できます（パッケージとしてインストールされていれば python -m でも可）。

- ExecutionEngine（実際の売買処理）
  - モジュール: src/kabusys/run_execution.py
  - 実行例:
    - KABUSYS_ENV=development python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 注意: paper_trading 環境では `PAPER_TRADING_SQLITE_PATH` に指定された DB（デフォルト data/paper_trading.db）を使用し、本番 DB と分離します。

- Monitoring（監視ループ）
  - モジュール: src/kabusys/run_monitoring.py
  - 環境変数:
    - MONITOR_POLL_INTERVAL: ポーリング間隔（秒、デフォルト 60）
  - 実行例:
    - python -m kabusys.run_monitoring

- Paper Trading 検証レポート
  - スクリプト: src/kabusys/tools/paper_verification_report.py
  - 実行例:
    - python -m kabusys.tools.paper_verification_report
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - --db で DBパスを明示可能（優先順位: --db > 環境変数 PAPER_TRADING_SQLITE_PATH > デフォルト data/paper_trading.db）

- Streamlit ダッシュボード（監視）
  - スクリプト: src/kabusys/monitoring/streamlit_dashboard.py
  - 実行例:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 注意: read-only で monitoring DB を参照します。DB が無ければエラーとなるため MonitoringEngine を先に起動してください。

- AI スコアリング / レジーム判定
  - 関数: kabusys.ai.score_news (news_nlp.score_news), kabusys.ai.regime_detector.score_regime
  - OpenAI API キー (OPENAI_API_KEY) が必須（引数から直接渡すことも可能）

---

## 運用上のポイント / 注意事項

- PID / Kill flag
  - ExecutionEngine は PID ファイル（デフォルト data/execution.pid）でプロセスの生存チェックを行います。KillSwitch は kill.flag（デフォルト data/kill.flag）を書いて ExecutionEngine に停止指示を出します。
- Paper Trading
  - `KABUSYS_ENV=paper_trading` を指定すると MockBrokerClient を使用し、本番 DB と完全分離された `data/paper_trading.db` を利用します。実運用時は誤って paper_trading でないことを確認してください。
- 環境変数読み込み
  - 自動ロードはプロジェクトルート（.git または pyproject.toml がある場所）から .env / .env.local を読み込みます。OS の環境変数は .env より優先され、自動ロードを無効化することもできます。
- OpenAI 呼び出し
  - LLM 呼び出し部はリトライ・バックオフ・レスポンス検証を備えていますが、APIキーや料金設定に注意してください。API失敗時はフェイルセーフによりスコア0などで継続する設計の箇所があります（partial failure 対応）。
- DB マイグレーション
  - monitoring_db.init_monitoring_db は既存 DB に対して冪等に必要テーブル/カラムを作成します（軽度のマイグレーションを含む）。

---

## 主要ファイル / ディレクトリ構成

以下はソースルート（src/kabusys）を起点とした主要ファイルの一覧・説明（抜粋）。

- src/kabusys/
  - __init__.py — パッケージメタ情報
  - config.py — Settings クラス（環境変数 / .env ロード）
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
- src/kabusys/ai/
  - news_nlp.py — ニュースの NLP スコアリング（OpenAI）
  - regime_detector.py — 市場レジーム判定（MA200 + マクロニュース）
  - __init__.py
- src/kabusys/research/
  - factor_research.py — Momentum / Volatility / Value ファクター計算（DuckDB）
  - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - __init__.py
- src/kabusys/portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 株数決定・スケーリング・lot丸め
  - risk_adjustment.py — セクターキャップ・レジーム乗数
  - __init__.py
- src/kabusys/execution/
  - order_manager.py — 注文管理の外向き API（OrderManager）
  - reconciler.py — 起動時の注文/ポジション同期
  - その他 (broker_factory, execution_engine, order_repository 等はコードベースに存在します)
- src/kabusys/monitoring/
  - monitoring_db.py — SQLite 永続化層（system_status/trade_logs/positions/risk_logs/dashboard）
  - system_monitor.py, trade_monitor.py, risk_monitor.py — 各種チェック
  - monitoring_engine.py — 各 Monitor を束ねるエンジン
  - alert_manager.py — LINE 通知ラッパ
  - kill_switch.py — kill.flag 制御
  - streamlit_dashboard.py — Streamlit ダッシュボード
  - __init__.py
- src/kabusys/tools/
  - paper_verification_report.py — Paper Trading 用検証レポート
  - __init__.py
- src/kabusys/utils/
  - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ

（上記は主要モジュールの抜粋です。詳細は各ファイルを参照してください。）

---

## よくある利用例（コマンドまとめ）

- 監視プロセスを起動（デフォルト 60 秒間隔）:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- 実運用エンジンを起動（paper_trading / live 切替）:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - KABUSYS_ENV=live python -m kabusys.run_execution
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

---

## 最後に / 参考

この README はリポジトリ内のソースコード（特に config.py、monitoring/*、ai/*、portfolio/*、tools/*）の実装に基づいて作成しています。実運用では APIキー・資金管理・ブローカー接続設定の取扱いに細心の注意を払ってください。追加の運用手順（例えば systemd/unit ファイル、ログローテーション、バックアップ）は運用環境に合わせて実装してください。

必要であれば、README に含めるサンプル .env、systemd ユニット例、より詳細な実行フロー（ExecutionEngine の session 流れや Order State Machine 図）を別ドキュメントとして追記できます。どの情報を優先して拡充したいか教えてください。