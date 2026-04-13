# KabuSys

日本株向け自動売買システムの主要モジュール群の README。  
このリポジトリは戦略・ポートフォリオ構築、注文実行、監視、AI（ニュース/レジーム判定）、および調査用ユーティリティを含みます。

主な内容:
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（起動コマンド・環境変数）
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株の自動売買を想定したモジュール群です。  
主な関心事は以下です。

- 戦略／ポートフォリオ構築（銘柄選定、重み付け、ポジションサイジング、セクター制限）
- 注文実行（ブローカー抽象化、リコンシリエーション、リスク管理）
- 監視（プロセス状態、データ鮮度、注文滞留、ドローダウン監視、アラート）
- 研究（ファクター計算、将来リターン、IC計算、統計サマリー）
- AI（ニュースセンチメント評価、マクロニュースを用いた市場レジーム判定）
- 運用支援ツール（Paper Trading 検証レポート、Streamlit ダッシュボード）

コードは純粋関数的な部分（ポートフォリオ計算など）と、DB / ブローカー / API を扱う実行コンポーネントに分かれています。

---

## 機能一覧

- ポートフォリオ構築
  - 銘柄候補選定（スコア順、ランクによるタイブレーク）
  - 等金額配分・スコア加重配分
  - ポジションサイズ計算（risk-based / equal / score）
  - セクター集中制限、レジーム乗数

- 注文実行
  - OrderManager / ExecutionEngine（ブローカーファクトリ経由で実行）
  - リコンシリエーション（再起動時の注文/ポジション同期）
  - リスクマネジメント（上限比率、利用率、サーキットブレーカー等）

- 監視
  - SystemMonitor: CPU/メモリ/Disk、プロセス PID チェック、データ鮮度チェック
  - TradeMonitor: 注文滞留・約定異常検出
  - RiskMonitor: ドローダウン・ポジション上限監視、kill.flag 書き込み
  - AlertManager: LINE push によるアラート送信（クールダウン管理）
  - MonitoringEngine: 各 Monitor を束ねるポーリングループ
  - SQLite ベースの監視ログ（monitoring_db）

- AI（OpenAI）
  - ニュース NLP（銘柄ごとのセンチメントを LLM で評価し ai_scores に格納）
  - レジーム判定（ETF MA200 乖離＋マクロニュースセンチメントを合成）
  - API リトライ、スコアクリッピング、部分失敗の保護などフェイルセーフ設計

- 研究 / 調査
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン、IC 計算、統計サマリー

- 運用ツール
  - Paper Trading 検証レポート（CLI: python -m kabusys.tools.paper_verification_report）
  - Streamlit 監視ダッシュボード（streamlit run ...）

---

## セットアップ手順

以下はローカルでの開発 / テスト向けの一般的な手順例です。

1. Python 環境（推奨: 3.10+）を用意し仮想環境を作成:
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

2. 必要パッケージをインストール（プロジェクトに requirements.txt がある場合はそちらを使用してください）。主に使用されているライブラリ:
   - duckdb
   - psutil
   - requests
   - openai
   - streamlit
   - （その他テスト用や DB ドライバ等）
   例:
   ```
   pip install duckdb psutil requests openai streamlit
   ```

3. 環境変数を設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すれば無効化）。
   - 必須の主要環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - OPENAI_API_KEY (AI 機能を使う場合)
   - その他（デフォルトが用意されているものもあります）:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading 用、デフォルト: instant）
     - PAPER_TRADING_SQLITE_PATH: paper trading 用の sqlite パス（既定: data/paper_trading.db）
     - SQLITE_PATH: monitoring 用 sqlite（既定: data/monitoring.db）
     - DUCKDB_PATH: DuckDB ファイル（既定: data/kabusys.duckdb）
     - PID_FILE_PATH / KILL_FLAG_PATH / CPU/MEM/DISK 閾値 等

4. データディレクトリの作成:
   ```
   mkdir -p data
   ```

注意:
- Settings モジュールは .git または pyproject.toml の場所からプロジェクトルートを自動検出して `.env` を読み込みます。自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 使い方

主要な起動スクリプトと使い方を示します。

- 監視ループ（SystemMonitor 単体起動）
  - スクリプト: src/kabusys/run_monitoring.py
  - 実行:
    ```
    python -m kabusys.run_monitoring
    ```
  - 補足:
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を指定可能（デフォルト 60 秒）。不正値または 0/負値はデフォルトへフォールバックします。
    - 監視は Settings の sqlite_path を常に使用（KABUSYS_ENV にかかわらず本番監視 DB を想定）。

- 実行エンジン（ExecutionEngine）
  - スクリプト: src/kabusys/run_execution.py
  - 実行:
    ```
    python -m kabusys.run_execution
    ```
  - 補足:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient（モックブローカー）を使用し、paper_trading 用の DB（PAPER_TRADING_SQLITE_PATH、デフォルト: data/paper_trading.db）に記録して本番 DB と完全分離します。
    - 起動時にプロセス優先度を high に設定し、pid ファイルを使用します。

- Streamlit ダッシュボード（監視 UI）
  - スクリプト: src/kabusys/monitoring/streamlit_dashboard.py
  - 実行:
    ```
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
    ```
  - 補足:
    - デフォルトは data/monitoring.db を読み取り専用で開きます。MonitoringEngine が DB を作成・更新する必要があります。

- Paper Trading 検証レポート（CLI）
  - スクリプト: src/kabusys/tools/paper_verification_report.py
  - 実行例:
    ```
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    ```
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH より優先）

- AI 関連
  - ニューススコアリング: kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - どちらも OPENAI_API_KEY を引数または環境変数で渡す必要があります。API 呼び出しはリトライやフェイルセーフが組み込まれています（429/タイムアウト/5xx に対するエクスポネンシャルバックオフ、失敗時にデフォルト値で継続）。

- 環境別挙動（KABUSYS_ENV）
  - development: デフォルト。ローカル開発用。
  - paper_trading: ブローカーはモック。発注ログは PAPER_TRADING_SQLITE_PATH に記録（本番 DB と分離）。
  - live: 本番運用想定。

- その他 / 補助
  - kill.flag による外部停止: KillSwitch は flag ファイルを書き込むことで ExecutionEngine に停止シグナルを送信します（Settings.kill_flag_path を参照）。
  - PID 管理: pid ファイルで実行中プロセスの存在をチェックし、stale PID 検出時はファイルを削除してアラートを出します。

---

## 主要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- OPENAI_API_KEY (AI 機能使用時に必須)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト development
- MONITOR_POLL_INTERVAL — 監視ポーリング秒数（デフォルト 60）
- PAPER_FILL_MODE — instant | partial | never | reject（paper_trading 用）
- PAPER_TRADING_SQLITE_PATH — paper_trading の sqlite パス（デフォルト data/paper_trading.db）
- SQLITE_PATH — 監視 DB（デフォルト data/monitoring.db）
- DUCKDB_PATH — DuckDB ファイル（デフォルト data/kabusys.duckdb）
- PID_FILE_PATH, KILL_FLAG_PATH — 監視・停止制御用パス
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 — 自動 .env ロードを無効化

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

```
src/
└── kabusys/
    ├── __init__.py
    ├── config.py                      # 環境変数 / .env 読み込み・Settings
    ├── run_monitoring.py              # SystemMonitor ポーリング起動スクリプト
    ├── run_execution.py               # ExecutionEngine 起動スクリプト
    ├── tools/
    │   ├── __init__.py
    │   └── paper_verification_report.py
    ├── portfolio/
    │   ├── __init__.py
    │   ├── portfolio_builder.py
    │   ├── risk_adjustment.py
    │   └── position_sizing.py
    ├── research/
    │   ├── __init__.py
    │   ├── factor_research.py
    │   └── feature_exploration.py
    ├── ai/
    │   ├── __init__.py
    │   ├── news_nlp.py
    │   └── regime_detector.py
    ├── monitoring/
    │   ├── __init__.py
    │   ├── monitoring_db.py
    │   ├── system_monitor.py
    │   ├── trade_monitor.py
    │   ├── risk_monitor.py
    │   ├── kill_switch.py
    │   ├── alert_manager.py
    │   ├── monitoring_engine.py
    │   └── streamlit_dashboard.py
    ├── execution/
    │   ├── order_manager.py
    │   ├── reconciler.py
    │   └── (その他ブローカー・エンジン関連モジュール)
    └── utils/
        ├── __init__.py
        └── process_priority.py
```

詳しいモジュール説明はソース内の docstring を参照してください。関数・クラスには設計意図・注意点が豊富にコメントされています。

---

## 運用上の注意点

- DB マイグレーション: monitoring_db.init_monitoring_db は冪等で実行できます。起動時に必要なカラム追加（例: peak_value, latency_ms）を試みます。
- ログ: 各スクリプトは logging.basicConfig(level=logging.INFO) を使用しています。必要に応じて LOG_LEVEL を設定してください（Settings.log_level）。
- OpenAI API: レスポンスのバリデーション、最大トークン対策、チャンク処理等が施されていますが、API 使用にはコストとレート制限の管理が必要です。
- プロセス優先度 / CPU affinity: 起動時に set_process_priority("high") を呼び出してプロセス優先度を上げます（必要に応じて変更してください）。アクセス権限がない場合は警告になります。

---

この README はコードベースに基づいた概要です。詳細な設計（PortfolioConstruction.md、StrategyModel.md 等）が存在する場合はそちらも参照してください。必要であれば起動例やデバッグ手順、テストの書き方についても追記できます。