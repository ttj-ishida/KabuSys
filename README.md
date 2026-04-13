# KabuSys

日本株自動売買システムの一部コードベース。戦略・ポートフォリオ構築、発注実行、監視、リサーチ、AI（ニュース解析／レジーム判定）などのコンポーネントを含みます。

以下はこのリポジトリの概要、機能、セットアップ方法と主要な使い方、およびディレクトリ構成の説明です。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システムのモジュール群です。主な役割は次のとおりです。

- 市場データを使ったファクター計算・特徴量分析（research）
- ポートフォリオ候補選定・重み付け・株数決定（portfolio）
- 発注の管理、ブローカー連携、再起動時のリコンシリエーション（execution）
- 実行状況・リスク・注文状態の監視とアラート（monitoring）
- ニュースの自然言語処理を用いた銘柄センチメント評価や市場レジーム判定（ai）
- 運用・検証用ツール（tools）

設計上、DuckDB を用いた時系列／ファクターデータ処理、SQLite を用いた監視ログ保持、外部ブローカーAPIや OpenAI を用いた拡張が想定されています。

---

## 主な機能一覧

- portfolio
  - 候補銘柄選定（score / rank ベース）
  - 等配分・スコア加重配分
  - ポジションサイズ計算（リスクベース / 等配分 / スコア）
  - セクター集中制限・レジーム乗数

- research
  - モメンタム／ボラティリティ／バリュー等のファクター計算（DuckDB）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー

- execution
  - OrderManager / OrderRepository：注文状態管理、送信、再同期
  - Reconciler：起動時の注文・ポジション自動突合せ
  - BrokerClientFactory による実運用 / Paper Trading 切替（モックブローカー）

- monitoring
  - SystemMonitor：CPU/メモリ/ディスク / データ鮮度 / 実行プロセスの監視
  - TradeMonitor：滞留注文・約定異常の検出
  - RiskMonitor：ドローダウン・ポジション上限監視、ダッシュボード更新
  - KillSwitch：致命的リスク検出時にフラグファイルを書き ExecutionEngine を停止
  - AlertManager：LINE Push を用いたアラート送信（クールダウン管理）
  - Streamlit ダッシュボード（監視データ可視化）
  - monitoring DB 初期化 / スキーママイグレーション

- ai
  - ニュース集約 → OpenAI（gpt-4o-mini 等）でセンチメントを取得し ai_scores に保存
  - ETF MA200 + マクロニュースセンチメント合成による市場レジーム判定

- tools
  - Paper Trading の検証レポート生成（成功率・稼働率・レイテンシ等の指標）

---

## 前提条件 / 依存関係

最低限必要な Python パッケージ（代表例）：

- Python 3.9+
- duckdb
- psutil
- requests
- openai
- streamlit (ダッシュボードを使う場合)
- その他、プロジェクトの他モジュールに依存するパッケージがある場合があります。

pip でインストールする例（仮）:

```
pip install duckdb psutil requests openai streamlit
```

（実際の requirements.txt があればそちらを使ってください）

---

## セットアップ手順

1. リポジトリをクローン／配置します。

2. 仮想環境を作成して依存パッケージをインストールします。

3. 環境変数を設定します（.env / .env.local をプロジェクトルートに配置可）。
   - 自動ロードについて：
     - code の config モジュールはプロジェクトルート（.git または pyproject.toml を基準）を探索し `.env` / `.env.local` を読み込みます。
     - 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

4. 必須環境変数（実行に必須なもの）：
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD
   - （AI 機能を使う場合）OPENAI_API_KEY

5. データベースの既定パス（必要に応じて環境変数で上書き可能）：
   - DuckDB: `DUCKDB_PATH`（デフォルト `data/kabusys.duckdb`）
   - SQLite（監視）: `SQLITE_PATH`（デフォルト `data/monitoring.db`）
   - Paper trading SQLite: `PAPER_TRADING_SQLITE_PATH`（デフォルト `data/paper_trading.db`）

6. （任意）Line 通知を有効にする場合、LINE のアクセストークンとユーザーIDを設定：
   - LINE_CHANNEL_ACCESS_TOKEN
   - LINE_USER_ID

---

## 環境変数（主なもの）

- KABUSYS_ENV: 実行環境（development / paper_trading / live）
  - `paper_trading` 時は専用の paper DB に記録しモックブローカーを使用
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: PaperTrading の約定挙動（instant / partial / never / reject）
- PAPER_TRADING_SQLITE_PATH: PaperTrading 用 SQLite ファイルパス
- PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト data/kill.flag）
- OPENAI_API_KEY: OpenAI API キー（ai モジュール用）
- その他：LOG_LEVEL, CPU_THRESHOLD_PCT など監視関連パラメータ

注意: Settings クラスは値の妥当性チェックを行います。不正な値や未設定の必須キーは起動時に例外になります。

---

## 実行方法（主要なスクリプト）

- 監視ループを起動（SystemMonitor 単体起動）
```
python -m kabusys.run_monitoring
```
- 実行エンジン（ExecutionEngine）を起動
```
python -m kabusys.run_execution
```
  - KABUSYS_ENV=paper_trading を指定するとモックブローカーを使用し、`data/paper_trading.db` に記録します。

- Streamlit ダッシュボード（監視データ可視化）
```
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```
  - `--db` で監視 SQLite ファイルパスを指定できます（デフォルト `data/monitoring.db`）。

- Paper Trading 検証レポート
```
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
```
  - `--db` オプションで DB パスを上書き可能（環境変数 PAPER_TRADING_SQLITE_PATH と併用）

- AI 関連（プログラムから呼び出す例）
  - news_nlp.score_news、regime_detector.score_regime は DuckDB 接続と target_date, API key を与えて呼び出します。APIキーは引数または環境変数 OPENAI_API_KEY を使用します。
  - 例（REPL またはスクリプト内）:
    ```
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect('data/kabusys.duckdb')
    score_news(conn, date(2026, 4, 10), api_key='...')  # または環境変数で指定
    ```

---

## 使い方のポイント / 実運用注意点

- 実行開始時にプロセス優先度を "high" に上げる処理が各起動スクリプトで行われます（プラットフォームにより権限が必要な場合があります）。
- Monitoring は KABUSYS_ENV に関係なく本番の sqlite_path を使用します（監視ログは運用 DB に集約される想定）。
- Paper Trading は本番 DB と分離され、`PAPER_TRADING_SQLITE_PATH` を使って独立した SQLite に記録されます。
- kill.flag を使った強制停止機能があり、KillSwitch がトリガー条件を満たすとファイルを書きます（ExecutionEngine は起動時にこれをチェックし、設定によりクリアします）。
- AI を使う機能はネットワーク依存・API 利用料が発生します。OPENAI_API_KEY の管理に注意してください。
- .env の読み込みはプロジェクトルート検出に依存します。CI / テスト等で自動ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py — 環境変数 / 設定管理（.env 自動ロード、Settings クラス）
- run_monitoring.py — SystemMonitor のポーリングループ起動スクリプト
- run_execution.py — ExecutionEngine 起動スクリプト

submodules:
- ai/
  - news_nlp.py — ニュースセンチメント取得（OpenAI）
  - regime_detector.py — マクロ + MA200 によるレジーム判定
- execution/
  - order_manager.py, reconciler.py, ... — 発注・再同期ロジック
- monitoring/
  - monitoring_db.py — SQLite スキーマ初期化 / DB 書き込みラッパー
  - system_monitor.py, trade_monitor.py, risk_monitor.py — 各種監視ロジック
  - alert_manager.py — LINE 通知
  - monitoring_engine.py — 各 Monitor を束ねるエンジン
  - streamlit_dashboard.py — ダッシュボード表示
  - kill_switch.py — フラグファイルによる停止シグナル
- portfolio/
  - portfolio_builder.py — 候補選定・基本重み
  - position_sizing.py — 株数計算・投下キャップ・切り捨て
  - risk_adjustment.py — セクターキャップ・レジーム乗数
- research/
  - factor_research.py — モメンタム・ボラティリティ・バリュー計算
  - feature_exploration.py — 将来リターン・IC・統計サマリー
- tools/
  - paper_verification_report.py — Paper Trading の検証レポート生成
- utils/
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
- data/ (想定配置)
  - kabusys.duckdb (デフォルト)
  - monitoring.db (デフォルト)
  - paper_trading.db (Paper Trading 用デフォルト)

（実際のリポジトリにはさらに多くのファイル・モジュールが存在します。上は主要ファイルの抜粋です。）

---

## よくあるトラブルと対処

- 起動時に環境変数エラー（ValueError が出る）
  - Settings で必須の環境変数が未設定です。`.env.example` を参照して `.env` を作成してください。
- OpenAI 関連が動かない
  - OPENAI_API_KEY が設定されているか確認してください。AI モジュールはキー未設定時に ValueError を投げます（スクリプト内で代替のフェイルセーフがある箇所もあります）。
- monitoring DB が見つからない／読み取り専用で開けない（Streamlit）
  - MonitoringEngine を起動して DB を初期化してください。Streamlit は read-only URI でも開けますが、ファイルが存在しないとエラーになります。
- プロセス優先度の変更に失敗するログが出る
  - 権限不足（Linux での negative nice 値等）や未対応プラットフォームのためスキップされることがあります。警告ログのみで処理自体は継続します。

---

必要に応じて README を拡張して以下を追加できます：
- 実際の API キー管理方針（Vault／CI シークレット）
- 実運用時の systemd / supervisor の起動スクリプト例
- テスト・CI 実行方法
- 詳細な DB スキーマ説明・マイグレーション戦略

ご希望があれば、上記のいずれかを追記して README を拡張します。