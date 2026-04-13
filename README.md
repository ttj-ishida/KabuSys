# KabuSys

KabuSys は日本株向けの自動売買（注文発行 / 監視 / リサーチ / AI）コンポーネント群を含む Python パッケージです。本リポジトリは以下の機能群を提供します。

- 注文管理・ExecutionEngine（ブローカー抽象化、リコンシリエーション、リスク管理）
- 監視機能（システム状況、注文滞留、リスク監視、kill flag）
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ計算）
- リサーチ（ファクター計算、将来リターン、IC 計算）
- ニュースに基づく LLM（OpenAI）によるセンチメントスコアリングとレジーム判定
- 運用支援ツール（Paper Trading 検証レポート、Streamlit ダッシュボード）

以下は開発／運用者向けの README になります。

## 特長（抜粋）

- モジュール設計により、Execution（発注系）と Monitoring（監視系）が明確に分離
- Paper Trading モード（`KABUSYS_ENV=paper_trading`）で本番 DB と完全分離して検証可能
- DuckDB を使った高速な時系列ファクター計算（prices_daily / raw_financials など参照）
- OpenAI（gpt-4o-mini）を使ったニュースセンチメント評価と市場レジーム判定（フェイルセーフ設計）
- SQLite ベースの監視ログ（自動マイグレーション対応）と Streamlit ダッシュボード

---

## 必要条件

- Python 3.10 以上（型ヒントの union 演算子 `|` を使用）
- 推奨パッケージ（pip 等でインストール）:
  - duckdb
  - psutil
  - openai
  - requests
  - streamlit
- SQLite（Python 標準ライブラリ）
- ネットワークアクセス（ブローカー API / OpenAI / LINE push を使用する場合）

（プロジェクトに requirements.txt がある場合はそれを利用してください。）

例:
```
pip install duckdb psutil openai requests streamlit
```

---

## 環境変数（主なもの）

設定クラスは `kabusys.config.Settings` に実装されています。主な環境変数とデフォルトは以下の通りです。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン（必須）
- KABU_API_PASSWORD — kabuステーション API のパスワード（必須）

任意 / デフォルトあり:
- KABUSYS_ENV — 起動環境: `development` (default) / `paper_trading` / `live`
  - `paper_trading` の場合、MockBrokerClient を使用し、`data/paper_trading.db` に記録する。
- KABU_API_BASE_URL — kabu API ベース URL（default: http://localhost:18080/kabusapi）
- OPENAI_API_KEY — OpenAI API キー（AI 機能で必要）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — AlertManager（LINE 送信）設定
- DUCKDB_PATH — DuckDB ファイル（default: data/kabusys.duckdb）
- SQLITE_PATH — 監視ログ用 SQLite（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（default: data/paper_trading.db）
- PAPER_FILL_MODE — Paper Trading の約定動作（default: "instant"）。有効値:
  - instant / partial / never / reject
- PID_FILE_PATH — ExecutionEngine PID ファイル（default: data/execution.pid）
- KILL_FLAG_PATH — kill.flag のパス（default: data/kill.flag）
- MONITOR_POLL_INTERVAL — Monitoring ポーリング間隔（秒、デフォルト: 60）。0 以下は無効としてデフォルト利用。
- LOG_LEVEL — ログレベル（DEBUG/INFO/...、default: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると自動的な .env ロードを無効化

注意: .env 自動読み込みはプロジェクトルート（.git または pyproject.toml がある場所）を起点に行われます。必要に応じ .env / .env.local を用意してください。

---

## セットアップ手順（ローカル開発・簡易）

1. Python 仮想環境の作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```

2. 必要パッケージをインストール
   ```
   pip install duckdb psutil openai requests streamlit
   ```

3. 環境変数設定
   - プロジェクトルートに `.env` を配置するか、環境変数をエクスポートしてください。
   - 例（.env）:
     ```
     KABUSYS_ENV=development
     JQUANTS_REFRESH_TOKEN=...
     KABU_API_PASSWORD=...
     OPENAI_API_KEY=...
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     ```
   - 自動ロードを無効にする場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

4. データディレクトリの作成（必要に応じ）
   ```
   mkdir -p data
   ```

5. （任意）DuckDB / 必要テーブルを準備してください（prices_daily / raw_financials / raw_news 等はリサーチ・AI 機能で参照されます）。

---

## 起動・使い方

### ExecutionEngine（実運用 / Paper Trading）
ExecutionEngine を起動すると、ブローカークライアントを生成しセッションを実行します。Paper Trading モードではデータベースが分離されます。

- 実行:
  ```
  python -m kabusys.run_execution
  ```

- Paper Trading（検証）モードで起動:
  ```
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  ```
  - この場合 `PAPER_TRADING_SQLITE_PATH`（デフォルト: data/paper_trading.db）に記録されます。
  - `PAPER_FILL_MODE` で約定挙動を制御（instant/partial/never/reject）。

### Monitoring（監視ループ）
監視用プロセスは SystemMonitor を定期実行し、SQLite の監視テーブルにログします。

- 実行（デフォルト 60 秒間隔）:
  ```
  python -m kabusys.run_monitoring
  ```

- ポーリング間隔を上書き:
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

- Monitoring は KABUSYS_ENV にかかわらず本番の `sqlite_path` を使用します（監視は常に本番 DB を参照想定）。

### Streamlit ダッシュボード（監視 UI）
監視用 SQLite を読み取り専用で表示する簡易ダッシュボード。

- 実行:
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

### Paper Trading 検証レポート（コマンドライン）
paper_trading の SQLite を読み取りレポートを標準出力に出力します。

- 実行（全期間）:
  ```
  python -m kabusys.tools.paper_verification_report
  ```

- 実行（期間指定）:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

- DB パスを明示:
  ```
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

### AI / リサーチ関数（ライブラリ API）
コード内の関数を直接呼び出して処理できます（例: ニューススコア・レジーム判定・ファクター計算）。

- 例: ニューススコアを付与する（Python スクリプト内）
  ```py
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 4, 10), api_key="sk-...")
  print("written:", written)
  ```

- 例: レジーム判定
  ```py
  from kabusys.ai.regime_detector import score_regime
  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,4,10), api_key="sk-...")
  ```

注意: OpenAI API キーは `OPENAI_API_KEY` 環境変数、または関数の `api_key` 引数で渡してください。API 呼び出しは失敗時にフェイルセーフ（代替値）で継続する実装になっています。

---

## 重要な挙動・設計メモ

- Process Priority:
  - run_execution.py / run_monitoring.py は起動直後に `set_process_priority("high")` を呼びます。プラットフォームにより効果がない場合があります（権限不足など）。
- Monitoring DB:
  - `init_monitoring_db(conn)` はテーブル作成とシンプルなマイグレーション（カラム追加）を行います。冪等設計。
- Kill Switch:
  - `data/kill.flag` の存在は ExecutionEngine に停止シグナルを送る仕組みです。`KillSwitch` は閾値超過時にファイルを書きます。
- Paper Trading:
  - `KABUSYS_ENV=paper_trading` 時はブローカーはモックを使い、本番 DB と分離して `PAPER_TRADING_SQLITE_PATH` にログを残します。
- AI 呼び出し:
  - OpenAI の結果は JSON mode を利用し、レスポンスのバリデーション・リトライ・クリッピング等を実装しています。API の失敗は基本的に例外を投げずデフォルト値で継続します（運用安全重視）。

---

## ディレクトリ構成（抜粋）

以下は主要なファイル・ディレクトリと簡単な説明です。

- src/kabusys/
  - __init__.py — パッケージ定義
  - config.py — 環境変数 / 設定読み込みロジック（.env 自動ロード含む）
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - execution/
    - order_manager.py — 注文作成/送信の外向け API
    - reconciler.py — 起動時の注文/ポジション再同期ロジック
    - (その他ブローカー関連、order_repository など)
  - monitoring/
    - monitoring_db.py — SQLite 永続化レイヤ（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py — システム状態・データ鮮度チェック
    - trade_monitor.py — 滞留注文 / 約定異常検出
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - kill_switch.py — kill.flag の作成・評価
    - alert_manager.py — LINE push 通知
    - monitoring_engine.py — 各モニタを束ねるポーリングエンジン
    - streamlit_dashboard.py — Streamlit によるダッシュボード
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数・単元丸め・利用上限
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — momentum / volatility / value 等のファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - ai/
    - news_nlp.py — ニュースを集約し OpenAI に投げて銘柄別センチメントを ai_scores に書き込む
    - regime_detector.py — ma200 とマクロニュースでレジーム（bull/neutral/bear）を判定
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート出力
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ

---

## よくある運用コマンド一覧（まとめ）

- Execution 起動（本番 / dev）
  ```
  python -m kabusys.run_execution
  ```

- Execution 起動（Paper Trading）
  ```
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  ```

- Monitoring 起動（デフォルト 60s）
  ```
  python -m kabusys.run_monitoring
  ```

- Monitoring 起動（30s 間隔）
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

- Streamlit ダッシュボード
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

## 補足 / 運用上の注意

- 環境変数や API キーは漏洩に注意して管理してください（CI/CD の Secret 等を利用）。
- 実運用時はプロセス制御（systemd / Supervisor 等）で自動再起動・ログ管理を行うことを推奨します。
- DuckDB / prices_daily 等のデータ品質がリサーチ・AI 結果に直結します。データ鮮度監視を必ず有効にしてください。
- 本リポジトリは安全性 / フェイルセーフを考慮した実装がされていますが、戦略ロジック・リスク設定は各運用者の責任で検証してください。

---

この README はコードベースの主要点をまとめたものです。詳細な API 仕様や実装ドキュメント（PortfolioConstruction.md、StrategyModel.md 等）が別途ある場合はそちらも参照してください。必要であれば README にデプロイ例（systemd ユニット、Dockerfile、CI 設定）を追加できます。