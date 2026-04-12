# KabuSys

日本株向け自動売買プラットフォームの小規模モジュール群。このリポジトリは戦略・ポートフォリオ構築、実行（ExecutionEngine）、監視（Monitoring）、リサーチ、AI（ニュースNLP／レジーム検出）などのコンポーネントを含みます。

以下はコードベースから作成した README です。

---

## プロジェクト概要

KabuSys は以下の主要機能を持つ自動売買システムのコンポーネント群です。

- マーケットデータ（DuckDB）を用いたファクター計算・リサーチ機能
- ポートフォリオ構築（候補選定・重み付け・ポジションサイジング）
- 実行層（OrderManager / ExecutionEngine / Broker 抽象化）
- 監視・アラート機能（system / trade / risk の監視、LINE へ通知）
- Paper Trading 向けの分離した DB、検証レポート出力ツール
- ニュース記事を LLM（OpenAI）でスコアリングする AI モジュール
- Streamlit ベースの簡易監視ダッシュボード

設計上のポイント:
- DuckDB（prices_daily, raw_financials 等）を利用したオフライン計算（リサーチ）
- SQLite を監視ログ（monitoring.db）と paper_trading 用 DB に使用
- 環境変数 / .env による柔軟な設定（Settings クラスで管理）

---

## 機能一覧

- portfolio
  - 銘柄候補選定（score / rank）
  - 等配分 / スコア加重配分
  - セクター集中制限（apply_sector_cap）
  - レジームに応じた投下資金乗数（calc_regime_multiplier）
  - ポジションサイジング（lot 単位丸め、aggregate cap 調整）
- research
  - Momentum / Volatility / Value ファクター計算（DuckDB）
  - 将来リターン計算、IC（Spearman）計測、統計サマリー
- execution
  - OrderManager / Reconciler：起動時の状態復旧、ブローカー同期
  - Broker 抽象化（paper_trading 時は MockBroker で分離）
  - RiskManager（取引制限・サーキットブレーカー等）
- monitoring
  - SystemMonitor: CPU/Memory/Disk / プロセス生存 / データ鮮度を監視
  - TradeMonitor: 滞留注文／約定異常を検出
  - RiskMonitor: ドローダウン / ポジション数上限監視
  - KillSwitch: 条件発生時にフラグファイルを書き ExecutionEngine に停止指示
  - AlertManager: LINE へのプッシュ通知（クールダウン管理）
  - MonitoringDB: 監視ログの永続化（SQLite）
  - Streamlit ダッシュボード（監視情報の可視化）
- ai
  - news_nlp: ニュース記事を OpenAI でスコアリングして ai_scores へ書き込み
  - regime_detector: ETF（1321）MA200 乖離とマクロニュースの LLM スコアを合成して市場レジーム判定
- tools
  - paper_verification_report: Paper Trading の検証レポートを生成

---

## 前提条件

- Python 3.10 以上（型アノテーションや union 型表記を利用）
- 推奨パッケージ（例）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（ダッシュボード利用時）
- SQLite（標準ライブラリで利用可）
- ネットワーク接続（LINE/OpenAI を使う場合）

（プロジェクトに requirements.txt があればそれを使ってください。無ければ上のパッケージを pip でインストールしてください。）

例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil requests openai streamlit
```

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo_url>
   cd <repo_dir>
   ```

2. 仮想環境作成・有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール
   ```
   pip install duckdb psutil requests openai streamlit
   ```

4. 環境変数を設定（.env / .env.local をプロジェクトルートに置く）
   - 自動ロード: `kabusys.config` はプロジェクトルートに .env / .env.local がある場合、自動で読み込みます（無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 代表的な環境変数（デフォルト値・説明）:
     - KABUSYS_ENV: 開発モード。`development` | `paper_trading` | `live`（デフォルト: development）
     - JQUANTS_REFRESH_TOKEN: 必須（J-Quants API）
     - KABU_API_PASSWORD: 必須（kabuステーション API）
     - OPENAI_API_KEY: OpenAI を使う場合に必須
     - LINE_CHANNEL_ACCESS_TOKEN: LINE 通知用（任意）
     - LINE_USER_ID: LINE 通知先ユーザID（任意）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE: Paper Trading の約定挙動（instant|partial|never|reject）（デフォルト: instant）
     - PID_FILE_PATH: ExecutionEngine 用 PID ファイルパス（デフォルト: data/execution.pid）
     - KILL_FLAG_PATH: KillSwitch 用フラグ（デフォルト: data/kill.flag）
     - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト: 60）
     - LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト: INFO）
   - .env の書式はシェル風に記述できます（コメント・export に対応）。詳細は `kabusys.config` を参照。

5. データディレクトリ作成
   ```
   mkdir -p data
   # 必要に応じて DuckDB / SQLite を配置
   ```

---

## 使い方

以下は代表的な実行方法です。

- ExecutionEngine（取引実行）を起動
  - 本番（設定に応じて Broker が選択されます）
  ```
  python -m kabusys.run_execution
  ```
  - Paper Trading（KABUSYS_ENV を設定）
  ```
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```
  - Paper Trading の DB は `PAPER_TRADING_SQLITE_PATH`（デフォルト `data/paper_trading.db`）に書き込まれ、本番 DB と分離されます。

- Monitoring（SystemMonitor のポーリングループ）を起動
  - デフォルト 60 秒間隔（環境変数 MONITOR_POLL_INTERVAL で上書き可）
  ```
  python -m kabusys.run_monitoring
  ```
  例: 10 秒間隔で実行
  ```
  export MONITOR_POLL_INTERVAL=10
  python -m kabusys.run_monitoring
  ```

  run_monitoring は SystemMonitor をポーリングして `monitoring.db` に記録します。Monitoring は本番 sqlite_path を使用します（KABUSYS_ENV に関わらず本番監視 DB に記録）。

- Streamlit ダッシュボード（監視情報の可視化）
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  監視 DB を読み取り専用で開くため、MonitoringEngine 実行中に表示できます。

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # --db で別 DB を指定可能
  ```

- AI 関連（ニューススコアリング / レジーム判定）
  - OpenAI API キーが必要（環境変数 OPENAI_API_KEY または関数呼び出し時に渡す）
  - ニューススコアリング（プログラム呼び出し例）
    - モジュール関数: `kabusys.ai.score_news(conn, target_date, api_key=None)`
  - レジーム判定: `kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)`

注意:
- ExecutionEngine 側は PID ファイルを作成し、KillSwitch が `data/kill.flag` を書き込むと停止判定を受けます。
- Paper Trading モードではブローカーはモック実装となり、本番のブローカーと完全に分離して動作します。

---

## 設定の主なポイント（Settings）

- 自動で .env を読み込む（プロジェクトルートに .env / .env.local がある場合）
- 必須 env:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- KABUSYS_ENV:
  - development / paper_trading / live（ここで paper_trading を指定すると paper DB を使用）
- PAPER_FILL_MODE: instant / partial / never / reject
- MONITOR_POLL_INTERVAL: run_monitoring 用のポーリング秒数（デフォルト 60）

---

## ディレクトリ構成（抜粋）

リポジトリ内の主要なファイル/ディレクトリと説明を示します（src/kabusys 以下）。

- kabusys/
  - __init__.py
  - config.py
    - 環境変数の読み込みと Settings クラス
  - run_execution.py
    - ExecutionEngine 起動スクリプト（KABUSYS_ENV による Paper Trading 切替）
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL）
  - ai/
    - news_nlp.py
      - raw_news を LLM でスコアリングして ai_scores に書き込む
    - regime_detector.py
      - ETF MA とマクロニュースでレジーム判定
  - monitoring/
    - monitoring_db.py
      - monitoring DB スキーマ初期化 / MonitoringDB クラス（永続化操作）
    - system_monitor.py
      - CPU/Mem/Disk / プロセス / データ鮮度チェック
    - trade_monitor.py
      - 滞留注文 / 約定異常検出
    - risk_monitor.py
      - ドローダウン / ポジション上限監視
    - kill_switch.py
      - フラグファイルによる ExecutionEngine 停止指示
    - alert_manager.py
      - LINE へ通知送信（クールダウン有）
    - monitoring_engine.py
      - 複数 Monitor を束ねるエンジン（テスト用 run_once / 本番 run）
    - streamlit_dashboard.py
      - Streamlit ダッシュボード起動スクリプト
  - execution/
    - order_manager.py, reconciler.py, order_repository.py, order_record.py, ...
    - Broker 抽象化と ExecutionEngine（実行の中核）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - tools/
    - paper_verification_report.py
  - utils/
    - process_priority.py
    - その他ユーティリティ

---

## 運用 / 注意事項

- 監視/実行は長時間稼働プロセスになるため、ログ・PID 管理・プロセス優先度（set_process_priority）などに注意してください。
- Monitoring は本番監視 DB（SQLITE_PATH）へ記録されます。Paper Trading と監視 DB は原則共有されます（監視は環境にかかわらず本番 sqlite_path を使用する設計になっています）。
- KillSwitch はファイルベース（KILL_FLAG_PATH）で停止指示を出します。ExecutionEngine 起動時に `KILL_FLAG_CLEAR_ON_START` を利用して古い flag をクリアするオプションがあります。
- OpenAI / LINE / ブローカー など外部サービスのエラーはフェイルセーフ（ログ出力・スキップ）で扱う箇所が多くありますが、運用時はモニタリングとアラート設定を行ってください。
- DB スキーマのマイグレーション処理が一部含まれます（例: monitoring_db のカラム追加処理など）。バックアップをとった上で運用してください。

---

## 開発者向け

- 単体機能を試す際は各モジュールの public 関数を直接呼び出すことでテストが容易です（例: portfolio.calc_position_sizes, research.calc_momentum 等）。
- OpenAI 周りは外部呼び出しを行う関数をモックしやすいように設計されています（テスト時は _call_openai_api をパッチする等）。
- MonitoringEngine.run_once はユニットテストでの一回実行確認に便利です。

---

必要であれば、README に以下を追加できます:
- requirements.txt（実際に使っているパッケージとバージョン）
- .env.example（必須/任意の環境変数テンプレート）
- 実行フロー図（図解）
- テスト実行方法（pytest 等）

追加希望があれば教えてください。