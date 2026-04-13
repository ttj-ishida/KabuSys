# KabuSys

日本株自動売買システムのコンパクトな実装（ライブラリ＋実行スクリプト群）。  
このリポジトリは、発注実行エンジン、監視機構、ポートフォリオ構築、ファクター計算、AI を使ったニュースセンチメント評価、検証ツール等を含みます。

主な設計方針:
- 本番・ペーパートレードを環境変数で切替可能（KABUSYS_ENV）
- DuckDB / SQLite をデータ層に利用（時系列・ファクターは DuckDB、監視ログは SQLite）
- OpenAI（gpt-4o-mini）をニュース/マクロセンチメント評価に利用（任意）
- フェイルセーフ設計：API エラーはスキップ or フォールバックして継続

---

## 機能一覧
- Execution
  - ExecutionEngine（発注エンジン）起動スクリプト（run_execution.py）
  - ブローカーファクトリにより本番 / Mock（paper_trading）を切替
  - リコンシリエーション（再起動時の注文・ポジション同期）
  - リスク管理（利用率・ポジション上限・ドローダウン等）
- Monitoring
  - SystemMonitor（CPU/メモリ/ディスク、プロセス生存、データ鮮度）
  - TradeMonitor（滞留注文、約定価格異常）
  - RiskMonitor（ドローダウン、ポジション上限）
  - KillSwitch（フラグファイルで ExecutionEngine に停止シグナル）
  - AlertManager（LINE Push による通知）
  - monitoring ポーリングループ起動スクリプト（run_monitoring.py）
  - Streamlit ダッシュボード（監視可視化）
- Portfolio
  - 候補選定(select_candidates)、重み計算（等分／スコア加重）
  - ポジションサイズ決定（risk_based 等）、セクター制約、レジーム乗数
- Research
  - ファクター計算（momentum／value／volatility）
  - 特徴量探索、将来リターン計算、IC（Information Coefficient）等
- AI
  - ニュース NLP（news_nlp.score_news）：raw_news を LLM に投げて銘柄ごとの ai_score を生成
  - レジーム判定（regime_detector.score_regime）：MA + マクロニュースセンチメントから市場レジーム判定
- Tools
  - Paper Trading 検証レポート出力ツール（kabusys.tools.paper_verification_report）
  - Streamlit ベースの監視ダッシュボード

---

## セットアップ手順

前提:
- Python 3.9+（コードは型注釈等を使用）
- SQLite（標準ライブラリ）
- 必要な外部パッケージ（pip でインストール）

推奨手順（例）:
1. 仮想環境を作成・有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .\.venv\Scripts\activate   # Windows (PowerShell 等)
   ```

2. 必要パッケージをインストール
   リポジトリに requirements.txt がない場合は主要パッケージを個別に:
   ```bash
   pip install duckdb psutil requests streamlit openai
   ```
   - DuckDB: ファクター計算・データ処理用
   - psutil: プロセス / リソース監視
   - requests: LINE API 呼び出し
   - streamlit: ダッシュボード
   - openai: LLM 呼び出し（AI 機能を使う場合）

3. 環境変数 / .env
   - 自動でプロジェクトルートの `.env` / `.env.local` を読み込みます（OS 環境変数が優先）。
   - 自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト等）。

   代表的な環境変数（最低限必要なもの）:
   - JQUANTS_REFRESH_TOKEN — J-Quants API 用（必要に応じて）
   - KABU_API_PASSWORD — kabuステーション API パスワード（発注を行う場合）
   - OPENAI_API_KEY — OpenAI 呼び出しに必要（news_nlp / regime_detector）
   - KABUSYS_ENV — 環境: development | paper_trading | live（デフォルト: development）
   - PAPER_FILL_MODE — paper_trading 時の Fill 動作（instant / partial / never / reject）
   - PAPER_TRADING_SQLITE_PATH — Paper DB（デフォルト: data/paper_trading.db）
   - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
   - PID_FILE_PATH / KILL_FLAG_PATH — 実行監視用ファイルパス
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知用（任意）
   - LOG_LEVEL — ログレベル（DEBUG/INFO/...）

   .env の書式は Bash 形式（export も可）で、コメントやクォートに対応しています。

---

## 使い方

基本的な起動例を示します。実行はプロジェクトルート（pyproject.toml または .git が存在する場所）で行ってください。

1. 監視ループを起動（SystemMonitor をポーリング）
   - ポーリング間隔を環境変数で上書き: `MONITOR_POLL_INTERVAL`（秒、デフォルト 60）
   ```bash
   # 監視ループをフォアグラウンドで起動
   python -m kabusys.run_monitoring
   ```

   動作のポイント:
   - 起動時にプロセス優先度を "high" に設定しようとします（set_process_priority）。
   - 監視は monitoring 用の sqlite_path（Settings.sqlite_path）を使用します（KABUSYS_ENV に依存せず本番 DB パスを参照する点に注意）。

2. 実行エンジンを起動（発注エンジン）
   ```bash
   python -m kabusys.run_execution
   ```
   - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、`PAPER_TRADING_SQLITE_PATH`（デフォルト: data/paper_trading.db）に記録します（本番 DB と分離）。
   - 起動時に Reconciler による自動同期が行われます。
   - 実行エンジンもプロセス優先度を "high" にセットします。

3. Paper Trading 検証レポート（コマンドライン）
   ```bash
   python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   # または DB を直接指定
   python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
   ```
   - 指定期間の稼働率、注文成功率、送信率、レイテンシ等を計算して標準出力にレポートを出力します。

4. Streamlit ダッシュボード（監視 UI）
   ```bash
   streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   ```
   - read-only モードで SQLite を開き、Overview / Positions / Orders / System のタブで情報を表示します。

5. AI 関連（OpenAI）
   - news_nlp.score_news / regime_detector.score_regime は OpenAI API キー（OPENAI_API_KEY）を必要とします。
   - モデル: gpt-4o-mini（JSON Mode を利用）
   - エラー・レート制限はリトライ（指数バックオフ）で耐性が実装されています。

---

## 重要な注意点 / 動作仕様
- .env の自動ロード順:
  - OS 環境変数 > .env.local（存在する場合） > .env
  - OS 環境変数を保護するため .env.local/.env の上書きロジックがあります。
- run_monitoring は MONITOR_POLL_INTERVAL で間隔制御（デフォルト 60 秒）。0 や負の値は無効としてデフォルトにフォールバックします。
- Monitoring は Settings.env に依存せず常に Settings.sqlite_path（本番監視 DB）を使用します。Execution は KABUSYS_ENV=paper_trading のとき専用の paper DB を使い完全に分離されます。
- OpenAI を使用する機能は API キー未設定だと例外や ValueError を投げる箇所があります（起動前に環境変数を設定してください）。
- プロセス優先度 / CPU affinity の設定はプラットフォーム依存で、失敗時は警告を出してスキップします（権限不足等）。

---

## ディレクトリ構成（抜粋）
以下は主要ファイル・モジュールの一覧です（src/kabusys 以下）。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env 読み込みと Settings
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading 検証レポート CLI
  - monitoring/
    - __init__.py
    - monitoring_db.py       — monitoring 用 SQLite 永続化層
    - system_monitor.py      — システム状態監視
    - trade_monitor.py       — 注文滞留・約定異常監視
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — フラグファイルによる停止シグナル
    - alert_manager.py       — LINE push 通知
    - monitoring_engine.py   — 各 Monitor を束ねるエンジン
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - execution/
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - ... (broker_factory, execution_engine, risk_manager など)
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
    - news_nlp.py            — ニュースセンチメントスコアリング（OpenAI）
    - regime_detector.py     — レジーム判定（MA + マクロニュース）
    - __init__.py
  - utils/
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
    - __init__.py

（実際のリポジトリでは data/ 配下にデフォルト DB が置かれます: data/kabusys.duckdb、data/monitoring.db、data/paper_trading.db 等）

---

## 追加のヒント / よくある質問
- 本番稼働前にまず Paper Trading（KABUSYS_ENV=paper_trading）で一通りの動作確認を行ってください。Paper トレードは DB やブローカー呼び出しが分離されています。
- OpenAI キーを使う機能はレート制限やコストが発生します。テスト時はモック（関数パッチ）で代替することが想定されています（コード内にテスト用の差し替えポイントが明記されています）。
- Streamlit から SQLite を read-only で開く際は URI を利用してロックを回避しています（streamlit_dashboard.py を参照）。

---

この README はコードベースの主要点をまとめたものです。詳細な API 使用方法や各モジュールの仕様は該当ソース（src/kabusys/...）の docstring / コメントを参照してください。必要であれば、各コンポーネントごとの詳しいドキュメント（使い方例や設計文書）も作成します。