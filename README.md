# KabuSys — 日本株自動売買システム（README）

このリポジトリは日本株向けの自動売買・研究基盤「KabuSys」の軽量実装です。  
この README ではプロジェクトの概要、機能、セットアップ手順、使い方、およびディレクトリ構成を日本語で説明します。

---

## プロジェクト概要
KabuSys は次の要素を備えた自動売買フレームワークです。

- 発注エンジン（ExecutionEngine）と監視プロセス（Monitoring）
- ペーパートレード用の完全分離 DB モード
- ポートフォリオ構築（候補選定・重み付け・株数算出）
- リスク管理（ドローダウン、ポジション上限などの監視と Kill Switch）
- 研究用モジュール（ファクター計算、特徴量解析）
- ニュース NLP / LLM を用いたセンチメント評価（OpenAI 経由）
- 運用ログは SQLite（監視 / 発注ログ）と DuckDB（分析用）で保存

設計方針として、ルックアヘッドバイアス防止、DB マイグレーション対応、外部 API の失敗に対するフェイルセーフを重視しています。

---

## 主な機能一覧
- run_execution.py
  - ExecutionEngine を起動。KABUSYS_ENV により paper_trading（MockBroker）と live（実発注）を切り替え。
  - ペーパートレード時は専用 SQLite（data/paper_trading.db）を使用して本番 DB と分離。
- run_monitoring.py
  - SystemMonitor のポーリングループを起動。監視情報を SQLite に永続化。
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可（デフォルト 60 秒）。
- config_setup.py
  - .env を対話式に作成 / 更新するウィザード。
- validate_config.py
  - .env と config/*.yaml の基本検証用 CLI（--strict オプションあり）。
- tools/paper_verification_report.py
  - ペーパートレード DB から期間集計レポートを生成（稼働率・成功率・レイテンシ等）。
- ai/news_nlp.py, ai/regime_detector.py
  - OpenAI を用いたニュースセンチメント集計・市場レジーム判定。
- portfolio/*
  - 銘柄選定、重み計算、リスク調整、株数計算（純粋関数で副作用無し）。
- monitoring/*
  - MonitoringDB（永続化層）、SystemMonitor、TradeMonitor、RiskMonitor、KillSwitch、MonitoringEngine、アラート管理など。
- utils/*
  - ロギング初期化、プロセス優先度 / CPU affinity 設定などのユーティリティ。

---

## 必要環境（推奨）
- Python 3.9+
- SQLite（Python 標準ライブラリで使用）
- 推奨パッケージ（少なくとも以下をインストールしてください）:
  - duckdb
  - psutil
  - openai （AI 機能を使う場合）
  - PyYAML（validate_config の YAML 検証を行う場合）
- ネットワーク接続（OpenAI / API 利用時）

インストール例:
```
pip install duckdb psutil openai pyyaml
```
※ requirements.txt があれば `pip install -r requirements.txt` を使用してください（本リポジトリには同ファイルがない場合があります）。

---

## セットアップ手順（初期）
1. リポジトリをクローン / 展開
2. Python 環境を準備（仮想環境推奨）
3. 必要パッケージをインストール（上記参照）
4. 対話式ウィザードで .env を作成:
   ```
   python -m kabusys.config_setup
   ```
   - J-Quants トークン、kabuステーション API パスワードなど必須項目を入力してください。
5. 設定検証:
   ```
   python -m kabusys.validate_config
   ```
   - `--strict` を付けると警告も失敗扱いになります。

---

## 主要環境変数（代表例）
（.env で設定することを想定）

- 必須
  - JQUANTS_REFRESH_TOKEN : J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD     : kabuステーション API パスワード
- 運用設定
  - KABUSYS_ENV           : 実行環境 (development | paper_trading | live) — デフォルト development
  - LOG_LEVEL             : ログレベル（DEBUG/INFO/...）
  - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH           : 監視用 SQLite（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH : Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
  - OPENAI_API_KEY         : OpenAI API キー（AI モジュール使用時）
  - PAPER_FILL_MODE        : ペーパー発注時の fill モード（instant|partial|never|reject）
  - MONITOR_POLL_INTERVAL  : run_monitoring のポーリング間隔（秒）
  - KILL_FLAG_CLEAR_ON_START : 起動時に kill.flag を自動クリアするか（0/1）

.env は絶対にリポジトリにコミットしないでください（secret 情報を含みます）。

---

## 使い方（主要コマンド）

- 実行エンジン起動（ExecutionEngine）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV が `paper_trading` のときは MockBroker を使用し、`data/paper_trading.db` に記録します。
  - 起動時に `data/execution.pid` を書きます。停止は kill.flag / stop_requested.flag を用います（下記参照）。

- 監視プロセス起動（SystemMonitor のループ）
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は `MONITOR_POLL_INTERVAL`（秒）で上書き可（デフォルト 60 秒）。
  - 監視は常に本番用の sqlite_path を参照します（監視 DB は環境にかかわらず本番 sqlite_path を使用）。

- .env ウィザード（初期設定）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- ペーパートレード検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - DB パスは `--db` か環境変数 `PAPER_TRADING_SQLITE_PATH` で指定できます（デフォルト data/paper_trading.db）。

- AI 系（プログラム内 API）
  - ニューススコアリング: `kabusys.ai.score_news(conn, target_date, api_key=None)`
  - レジーム判定: `kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)`
  - これらは DuckDB 接続を受け取り、テーブル（raw_news, news_symbols, ai_scores, prices_daily 等）を参照/更新します。
  - `OPENAI_API_KEY` を環境変数で設定するか、api_key を明示してください。

---

## 停止・Kill Switch の仕組み
- 停止フラグ（手動停止）:
  - run_execution/run_monitoring はプロジェクトルートの `data/stop_requested.flag` の存在を監視します。ファイルが存在するとループを止めます。
- Kill Switch（自動停止）:
  - risk_monitor 等が基準を満たすと `data/kill.flag` を書き込み、ExecutionEngine に停止理由を伝えます。
  - ExecutionEngine は `KILL_FLAG_CLEAR_ON_START` の設定等に基づき起動時にクリアするか判断します。
- PID ファイル:
  - ExecutionEngine は `data/execution.pid` に PID を書きます（run_execution 内定義）。

---

## ロギング
- ログ初期化関数: `kabusys.utils.logging_setup.setup_logging(app_name="execution")`
- デフォルトでコンソール（stdout）と日次ローテートファイル（logs/<app_name>.log）へ出力します。
- ログディレクトリは `LOG_DIR` 環境変数またはデフォルト `logs/`。作成に失敗した場合はコンソールのみで継続します。

---

## DB（ファイル）について
- DuckDB（分析用）: デフォルト `data/kabusys.duckdb`
- 監視用 SQLite: デフォルト `data/monitoring.db`
- ペーパートレード SQLite: デフォルト `data/paper_trading.db`（KABUSYS_ENV=paper_trading 時に使用）
- 初回起動時に必要な親ディレクトリ（data/ や logs/）を手動で作成するか、実行時に自動作成されます。validate_config は親ディレクトリの存在を警告します。

---

## ディレクトリ構成
以下は src/kabusys 以下の主要ファイル／ディレクトリの一覧（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数 / 設定管理
  - config_setup.py         — .env 対話式ウィザード
  - validate_config.py      — 設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py (参照用)
  - execution/              — ExecutionEngine 周りの実装（BrokerFactory 等）
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
  - data/                   — データファイル（logs/や data/ 以下の DB ファイルを配置）
  - config/                 — yaml 設定テンプレート（system_config.yaml 等）

（実際のファイル数やサブモジュールはリポジトリに依存します。上記はコードベースから抽出した主要な構造です。）

---

## 開発者向けメモ・注意点
- 環境自動ロード:
  - config.py は自動的にプロジェクトルートの `.env` と `.env.local` をロードします（OS 環境変数を保護）。テスト等で自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。
- プロセス優先度:
  - 実行スクリプトは起動時に `set_process_priority("high")` を呼びます。権限がない場合は警告を出してスキップします。
- DuckDB の executemany 空リスト制約:
  - 一部コードは DuckDB のバージョン差分（executemany に空リストを渡せない等）に配慮した実装になっています。
- ルックアヘッドバイアス回避:
  - 研究・AI モジュールは `date` / `target_date` を引数に受け取り、`datetime.today()` を参照しない設計です。生の実装に追加する際は注意してください。
- AI（OpenAI）呼び出し:
  - API エラー時はリトライやフォールバックを行う実装ですが、API キーは必ず安全に管理してください。無料クレジットや使用制限に注意。

---

## トラブルシューティング（よくある問題）
- ログディレクトリ / data ディレクトリの作成に失敗する:
  - 実行ユーザーに書き込み権限があるか確認してください。ディレクトリを手動で作成することも可能です（例: mkdir -p data logs）。
- psutil がプロセス優先度変更で AccessDenied を出す:
  - 権限が足りないだけなので重大な障害ではありません。警告が出て処理は継続します。
- OpenAI 呼び出しで JSON 解析エラー:
  - LLM の応答が期待した JSON 形式でないと解析に失敗することがあります。ログを確認してプロンプトや API の制限を調整してください。

---

## 最後に
この README はコードベースの注釈・モジュール実装を基に作成しています。実際の運用に当たっては .env（秘密情報）や本番 DB の取り扱いに十分注意してください。機能追加や運用フローの変更は config/*.yaml やコード中のコメント（PortfolioConstruction.md 等参照）に従うと良いでしょう。

ご不明点や追加で README に載せたい情報があれば教えてください。