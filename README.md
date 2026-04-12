# KabuSys

日本株向け自動売買システム（ライブラリ／ランタイム）。  
本リポジトリは、シグナル → ポートフォリオ構築 → 発注 → 監視・リコンシリエーション／レポーティングまでを含むモジュール群を提供します。

---

## 概要

- 株取引に必要なアルゴリズム（ファクター計算、ポートフォリオ構築、ポジションサイズ計算）を DuckDB 上の市場データ（prices_daily / raw_financials）で算出する研究用コンポーネントを含みます。
- 発注（ExecutionEngine）周りはブローカー抽象化（実ブローカー／Paper Trading の MockBroker）により、本番と検証を分離できます。
- 監視（Monitoring）機能は SQLite に監視ログを永続化し、LINE 通知・kill flag による自動停止・Streamlit ダッシュボード表示などを備えます。
- OpenAI を使ったニュース NLP（銘柄別センチメント）や市場レジーム判定（LLM + ma200）機能を含みます。

---

## 主な機能一覧

- 研究系
  - ファクター計算（momentum / value / volatility）
  - 将来リターン計算・IC（Spearman）算出・特徴量サマリ
- ポートフォリオ構築
  - 候補選定、等配分・スコア配分、リスク基づくポジションサイズ計算
  - セクター集中制限、レジーム乗数（bull/neutral/bear）
- 発注・実行
  - OrderManager／ExecutionEngine（ブローカー抽象化）
  - 起動時のリコンシリエーション（Reconciler）
  - Paper Trading 用の DB 分離（data/paper_trading.db）
- 監視（Monitoring）
  - SystemMonitor（プロセス・リソース・データ鮮度）
  - TradeMonitor（滞留注文・約定価格異常）
  - RiskMonitor（ドローダウン・ポジション上限）
  - KillSwitch（flag ファイルで ExecutionEngine 停止）
  - AlertManager（LINE プッシュ通知、クールダウン管理）
  - Streamlit ダッシュボード（監視情報の可視化）
- AI 関連
  - ニュース NLP（OpenAI を用いた銘柄別センチメント -> ai_scores）
  - 市場レジーム判定（ma200 とマクロニュースの合成）

---

## セットアップ手順

前提: Python 3.9+（プロジェクトの実行環境に合わせてください）

1. リポジトリをクローン／チェックアウト
   - プロジェクトルートは .git または pyproject.toml を基準に自動検出されます。

2. 必要パッケージをインストール（例）
   - 最低限の依存:
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit (dashboard を使う場合)
   - pip 例:
     ```
     pip install duckdb psutil requests openai streamlit
     ```
   - 実プロジェクトでは requirements.txt / poetry 等を用意して管理してください。

3. 環境変数の準備
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（既存 OS 環境変数は保護されます）。
   - 自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
   - 主要な環境変数（一部、デフォルト値あり）:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - OPENAI_API_KEY (AI 機能を使う場合必須)
     - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
     - PAPER_FILL_MODE: instant | partial | never | reject （デフォルト: instant）
     - PAPER_TRADING_SQLITE_PATH（Paper Trading 用 DB、デフォルト: data/paper_trading.db）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - DUCKDB_PATH（DuckDB ファイル、デフォルト: data/kabusys.duckdb）
     - PID_FILE_PATH（ExecutionEngine の PID ファイル、デフォルト: data/execution.pid）
     - KILL_FLAG_PATH（kill.flag のパス、デフォルト: data/kill.flag）
     - MONITOR_POLL_INTERVAL（監視ポーリング間隔秒、デフォルト: 60）
     - LOG_LEVEL（DEBUG/INFO/…、デフォルト: INFO）
     - KILL_FLAG_CLEAR_ON_START=1 を設定すると ExecutionEngine 起動時に既存の kill.flag をクリアできます。

4. データファイル／ディレクトリの作成
   - data ディレクトリや DB ファイルの生成が必要な場合は適宜作成してください。監視・実行スクリプトは起動時に DB スキーマ（monitoring）を初期化します。

---

## 使い方

簡単な実行例を示します。いずれもプロジェクトルートで実行してください。

- 監視ループを起動
  - 監視は常に本番用の sqlite_path（Settings.sqlite_path）を使用します。
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔を環境変数で上書き:
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

- ExecutionEngine（発注エンジン）を起動
  - KABUSYS_ENV が paper_trading の場合、MockBrokerClient を使用し paper_trading DB（PAPER_TRADING_SQLITE_PATH）に記録します（本番 DB と分離）。
  ```
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  ```
  - 起動時に PID ファイルを書き、プロセス優先度を high に設定します（権限により失敗する場合は警告）。

- Paper Trading 検証レポート生成ツール
  - 指定期間の検証レポートを標準出力に出します。
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルト DB は data/paper_trading.db。別パスを使う場合:
  ```
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- Streamlit ダッシュボード（監視）
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  - read-only で SQLite DB を開きます。MonitoringEngine が記録している DB を参照してください。

- AI 機能（ニュース NLP / レジーム判定）
  - OpenAI API キー（OPENAI_API_KEY）が必要です。関数はライブラリ API として利用可能:
    - kabusys.ai.score_news(conn, target_date, api_key=None)
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

---

## 注意事項 / 動作上のポイント

- .env ローダ:
  - プロジェクトルート（.git または pyproject.toml を基準）から `.env` と `.env.local` を自動ロードします。OS 環境変数は保護され、.env.local は上書き可能です。
- DB 管理:
  - 監視用の SQLite（monitoring）スキーマは起動時に自動で初期化・マイグレーションを行います（init_monitoring_db）。
  - Paper Trading は設定により本番 DB と物理的に分離されます（PAPER_TRADING_SQLITE_PATH）。
- プロセス優先度:
  - 起動スクリプトは psutil を用いてプロセス優先度（high/normal/low）や CPU affinity を設定します。権限によっては設定できない場合があります（警告ログのみ）。
- Kill Switch:
  - 一定のリスク条件（ドローダウン・ポジション上限）に達した場合、kill.flag を書き込んで ExecutionEngine に停止指示を送ります。kill.flag の存在は冪等に扱われます。
- OpenAI 呼び出し:
  - レート制限や一時的なネットワーク障害へのリトライロジックを実装しています（exponential backoff）。API エラーやパース失敗はフェイルセーフでスコアをデフォルトにフォールバックする設計です。
- ロギング:
  - 各モジュールは logging を使用します。LOG_LEVEL 環境変数でログレベルを変更できます。

---

## ディレクトリ構成（抜粋）

以下は本コードベースの主要ファイル／モジュールの構成です（完全な一覧ではありません）。

- src/kabusys/
  - __init__.py
  - config.py
  - run_monitoring.py         — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
  - data/                     — （DuckDB / データパイプライン関連モジュールが想定）
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
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
    - __init__.py
  - execution/
    - order_manager.py
    - reconciler.py
    - (その他発注関連モジュール)
  - utils/
    - process_priority.py
    - __init__.py

---

## 追加情報・開発メモ

- モジュールは可能な限り副作用を抑え、純粋関数（portfolio / research）と副作用を持つ I/O 層（monitoring_db, broker API）を明確に分離しています。
- テストを書く際は Settings の自動 .env ロードを無効化する（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）か、環境変数をモックしてください。
- AI 関連の OpenAI 呼び出し箇所はユニットテスト時に差し替えやすいように内部呼び出しを別関数化してあります（_call_openai_api のモックなど）。

---

必要に応じて README を拡張します（例: requirements.txt、デプロイ手順、CI 設定、より詳細な環境変数一覧や schema 定義など）。追加で記載したい項目があれば教えてください。