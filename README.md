# KabuSys

KabuSys は日本株の自動売買システムの一部を構成するライブラリ／ツール群です。本リポジトリには、実取引実行（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、リサーチ（ファクター計算）、AI を用いたニュースセンチメント評価などの主要コンポーネントが含まれます。

バージョン: 0.1.0

---

## プロジェクト概要

- 日本株アルゴリズムトレードのためのモジュール群。
- 発注・注文管理・リコンシリエーション（再同期）、リスク監視、監視ダッシュボード、ポートフォリオ構築ロジック、ファクター計算、ニュースNLP（OpenAI）を用いたセンチメント評価などを含む。
- DB: SQLite（監視ログや注文ログ）および DuckDB（時系列データ / ファクター計算用）を使用。
- 実行モード:
  - `live` / `development` / `paper_trading`（Paper Trading 時は実ブローカーを模した MockBrokerClient を使用し、paper 用 DB に分離して記録）
- 環境変数は .env / .env.local / OS 環境変数から読み込まれる（自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。

---

## 主な機能一覧

- Execution（実行）
  - OrderManager：注文作成→送信→状態遷移の管理
  - Reconciler：起動時の注文/ポジション照合（再同期）
  - RiskManager：発注前のリスク制約（ポジションサイズ等）
  - Broker クライアントの抽象化（本番/モック切替）

- Monitoring（監視）
  - SystemMonitor：CPU / メモリ / ディスク / プロセス生存 / データ鮮度の監視
  - TradeMonitor：滞留注文・約定価格異常の検出
  - RiskMonitor：ドローダウン検出・ポジション上限監視
  - KillSwitch：フラグファイル書き込みで ExecutionEngine 停止を指示
  - AlertManager：LINE によるプッシュ通知（クールダウン管理）
  - Streamlit ダッシュボード（監視データ可視化）
  - monitoring DB：監視用の SQLite テーブル定義・永続化 API

- Portfolio（配分ロジック）
  - 候補選定、等金額／スコア加重重み計算、セクター上限適用、レジーム乗数、株数決定（単元株丸め・合計キャッシュ制約）

- Research（リサーチ）
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー

- AI（自然言語処理）
  - news_nlp: raw_news をまとめて OpenAI（gpt-4o-mini）に送り、銘柄別センチメントを ai_scores に書き込む
  - regime_detector: ETF の MA200 とマクロニュースの LLM 評価を合成して市場レジーム判定を行い DB に格納

- ツール
  - Paper Trading 検証レポート生成スクリプト（期間指定可）

---

## 必要な環境・依存関係

- Python 3.10 以上（| 型注釈を使用）
- 主な Python パッケージ（例）
  - duckdb
  - openai
  - psutil
  - requests
  - streamlit
- SQLite（標準ライブラリで使用）
- ネットワーク接続（OpenAI / LINE API 使用時）

（注）requirements.txt は本コードベースには含まれていません。上記パッケージを pip でインストールしてください。

例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai psutil requests streamlit
```

---

## 主な環境変数

（Settings クラス経由で参照されます）

必須（使用機能により必須項目は異なります）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン（必要に応じて）
- KABU_API_PASSWORD — kabuステーション API のパスワード（発注をする場合）

任意 / デフォルトあり
- KABUSYS_ENV — 起動環境: `development` | `paper_trading` | `live`（デフォルト: development）
- LOG_LEVEL — ログレベル（例: INFO、DEBUG）
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector で使用）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — AlertManager（LINE）で通知する場合に必要
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite ファイルパス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — Paper Trading の約定モード（instant|partial|never|reject、デフォルト: instant）
- PID_FILE_PATH — ExecutionEngine の PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — KillSwitch フラグファイル（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag をクリアするか（"1" で有効）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）

自動 .env 読込
- プロジェクトルートの `.env` / `.env.local` が自動で読み込まれます（OS 環境変数が優先されます）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## セットアップ手順（開発環境向け、例）

1. リポジトリをクローン
2. 仮想環境を作成・有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows
   ```
3. 必要ライブラリをインストール（例）
   ```bash
   pip install duckdb openai psutil requests streamlit
   ```
4. 環境変数を設定（.env をプロジェクトルートに作成しても可）
   - 例: `.env` に以下を記述
     ```
     KABUSYS_ENV=development
     OPENAI_API_KEY=sk-...
     KABU_API_PASSWORD=****
     LINE_CHANNEL_ACCESS_TOKEN=
     LINE_USER_ID=
     ```
5. データディレクトリを作成（必要に応じて）
   ```bash
   mkdir -p data
   ```

---

## 使い方（主要コマンド）

- ExecutionEngine を起動（本番/開発/ペーパートレードは KABUSYS_ENV の値で切替）
  ```bash
  python -m kabusys.run_execution
  ```
  特記事項:
  - `KABUSYS_ENV=paper_trading` の場合、MockBrokerClient が使用され、Paper Trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録されます。
  - 起動時にプロセス優先度を「high」に設定し、PID ファイルを書きます。

- Monitoring（SystemMonitor のポーリングループ）を起動
  ```bash
  python -m kabusys.run_monitoring
  ```
  - 環境変数 `MONITOR_POLL_INTERVAL`（秒）でポーリング間隔を上書き可能（デフォルト 60 秒）。
  - 監視用 DB は Settings.sqlite_path を使用（Monitoring は環境にかかわらず本番 sqlite_path を使用する実装意図あり）。

- Streamlit ダッシュボードを起動（監視 DB の可視化）
  ```bash
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  - 監視 DB を読み取り専用で開き、Overview / Positions / Orders / System タブを提供します。

- Paper Trading 検証レポート生成
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルト DB: `data/paper_trading.db`（環境変数 `PAPER_TRADING_SQLITE_PATH` で変更可）
  - 出力は標準出力にテキストレポート（稼働率、注文成功率、レイテンシ等）

- AI 系：ニュースセンチメント / レジーム判定（プログラムから利用）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - 実行には `OPENAI_API_KEY` を設定するか、api_key を引数で渡してください。

---

## 実行上の注意点

- Monitoring の DB 初期化: run_* スクリプトは起動時に監視テーブル（monitoring_db.init_monitoring_db）を冪等に作成します。
- Paper Trading モードでは paper_trading の DB と本番 DB は完全に分離して記録される設計です。
- OpenAI / LINE API など外部 API 呼び出しは失敗に対してフェイルセーフ（ログ出力して処理継続）するよう設計されていますが、API キーやレート制限等の取り扱いは実運用で注意してください。
- process priority / cpu affinity の設定には OS 権限が必要な場合があります。psutil による例外は警告として扱われます。
- kill.flag による停止シグナルは KillSwitch を通じて書き込まれます。ExecutionEngine 起動時に `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時にフラグがクリアされます。

---

## ディレクトリ構成

主要ファイル／モジュールの構成を抜粋します。

src/kabusys/
- __init__.py
- config.py  — 環境変数 / Settings
- run_execution.py  — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor 起動スクリプト

サブパッケージ:
- execution/
  - order_manager.py
  - reconciler.py
  - (その他 broker / engine / repository 等の実装ファイル)
- monitoring/
  - monitoring_db.py
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - monitoring_engine.py
  - alert_manager.py
  - kill_switch.py
  - streamlit_dashboard.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- ai/
  - news_nlp.py
  - regime_detector.py
- tools/
  - paper_verification_report.py
- utils/
  - process_priority.py
- data/ (想定されるデータ格納先、実運用で作成)
  - kabusys.duckdb
  - monitoring.db
  - paper_trading.db

（上記はリポジトリ内の主要モジュールの抜粋です。実際のファイル構成はリポジトリを参照してください）

---

## 開発・拡張ポイント（留意事項）

- DuckDB に対する SQL はモジュール内で直接定義されており、テーブル名（prices_daily / raw_financials / raw_news 等）が前提になっています。データの投入方法は別途整備が必要です。
- AI（OpenAI）呼び出しは JSON Mode を使用しており、レスポンス整合性のため厳密なバリデーションを行っています。API のバージョン変更に注意してください。
- position sizing / risk adjustment 等は純粋関数として設計されており、ユニットテストがしやすい構成です。
- DB スキーマのマイグレーション（列追加等）は monitoring_db.init_monitoring_db に簡易的に含まれているため、既存 DB を維持しつつ拡張できます。

---

## ライセンス / 貢献

（本リポジトリにライセンスファイルがあればここに明記してください。サンプル README のため省略しています）

---

質問や README に追加したい項目があれば教えてください。使用例のコマンドや環境変数のテンプレートなど、さらに詳しいセットアップ手順（Docker / systemd ユニット例など）も追記できます。