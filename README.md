# KabuSys

日本株向けの自動売買システム（ライブラリ / 実行スクリプト群）。  
本リポジトリはトレード実行エンジン、監視（モニタリング）、リサーチ / ファクター計算、AI を使ったニュース分析等のユーティリティを含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の主要な機能を提供します。

- 実行エンジン（ExecutionEngine）：ブローカークライアント経由で注文管理・発注を行う（本番 / ペーパートレード対応）。
- 監視（Monitoring）：システム稼働状況・発注ログ・リスク（ドローダウン / ポジション上限）をポーリングして永続化・アラート/Kill Switch を管理。
- ポートフォリオ構築：シグナルから候補選定、重み付け、ポジションサイズ計算、セクターキャップ等の純粋関数群。
- リサーチ：DuckDB を使ったファクター（モメンタム / ボラティリティ / バリュー）や特徴量探索（IC 等）。
- AI モジュール：OpenAI を利用してニュースセンチメントを算出し、market_regime（市場レジーム）判定に利用。
- ツール群：ペーパートレード検証レポート生成や設定ウィザード / 検証 CLI。

---

## 主な機能一覧

- 実行環境分離
  - KABUSYS_ENV により `development` / `paper_trading` / `live` を切替可能
  - `paper_trading` 時は MockBrokerClient を使い、ペーパートレード用 DB（data/paper_trading.db）へ記録
- 監視
  - system_status / trade_logs / positions / risk_logs / dashboard を SQLite に保存
  - Process 停止検知、データ鮮度チェック、滞留注文・約定異常・ドローダウン検出、Kill Switch 発動
- ポートフォリオ構築
  - 候補選定（スコア順）、等比率/スコア重み、リスクベースの株数計算、セクターキャップ適用等
- リサーチ
  - DuckDB 接続で大量データを高速に処理、ファクター計算（mom, atr, per, roe など）
- AI（OpenAI）
  - ニュースを銘柄別に集約して LLM でセンチメント評価（スコア ±1.0 にクリップ）
  - マクロニュースを使った市場レジーム判定（bull / neutral / bear）
- 運用ユーティリティ
  - .env 対話ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - ペーパートレード検証レポート（tools/paper_verification_report.py）
  - 標準化されたロギング設定（logs/*.log、日次ローテーション）

---

## 必要な依存パッケージ（例）

（プロジェクトの requirements.txt がある場合はそちらを使ってください。以下は本コードで参照される主要ライブラリ）

- Python 3.9+
- duckdb
- psutil
- openai
- PyYAML（config ファイル検証時に任意）
- そのほか標準ライブラリ（sqlite3 など）

インストール例:
```
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリをクローン / 展開
2. 仮想環境を作成して依存をインストール
   ```
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install -U pip
   pip install duckdb psutil openai PyYAML
   ```
3. ディレクトリ作成（初回）
   ```
   mkdir -p data logs
   ```
   - SQLite / DuckDB のデフォルトパスは `data/monitoring.db` / `data/kabusys.duckdb`
   - ログは `logs/<app_name>.log` に出力されます（daily rotation）
4. 環境変数設定
   - 対話式で .env を作る（推奨）
     ```
     python -m kabusys.config_setup
     ```
   - または `.env` を直接作成。必要なキー例は下記参照。
5. 設定検証（任意だが推奨）
   ```
   python -m kabusys.validate_config
   # 警告も含めて失敗扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

---

## 必須（あるいは重要）な環境変数（例）

最低限以下は設定してください（.env に記述）:

- JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
- KABU_API_PASSWORD=your_kabu_api_password
- KABUSYS_ENV=development|paper_trading|live
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- LOG_LEVEL=INFO
- OPENAI_API_KEY=sk-...

ペーパートレード用やオプション:
- PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
- PAPER_FILL_MODE=instant|partial|never|reject
- LINE_CHANNEL_ACCESS_TOKEN=...（アラート用）
- LINE_USER_ID=...（アラート先）
- KILL_FLAG_CLEAR_ON_START=0 or 1

自動 .env ロード:
- 起動時、プロジェクトルート（.git か pyproject.toml を基準）を見つけると `.env` / `.env.local` を自動でロードします。自動ロードを無効にする場合:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```

例（簡易）.env:
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...
```

---

## 使い方（主要スクリプト）

ルートは Python パッケージとして動作します。モジュールを -m で実行するのが推奨。

1. 設定ウィザード
   ```
   python -m kabusys.config_setup
   ```
   対話式に .env を作成・更新します。

2. 設定検証
   ```
   python -m kabusys.validate_config
   ```

3. 実行エンジン起動（ExecutionEngine）
   - 本番/開発/ペーパートレードは KABUSYS_ENV による
   - ペーパートレード時は MockBrokerClient を使用し DB は分離（PAPER_TRADING_SQLITE_PATH）
   ```
   python -m kabusys.run_execution
   ```
   仕組み:
   - プロセス優先度を高に設定し、SQLite / DuckDB に接続
   - BrokerClientFactory により適切なブローカークライアントを作成
   - Engine が別スレッドで実行され、data/stop_requested.flag を確認して停止

   停止制御:
   - 停止フラグ: data/stop_requested.flag（作成されていると起動を中止、または実行中に停止させる）
   - 実行中の PID ファイル: data/execution.pid（設定で別パスを指定可能）
   - Kill Switch: data/kill.flag が書かれると ExecutionEngine に停止シグナル送出（監視側から）

4. 監視ループ起動（Monitoring）
   ```
   python -m kabusys.run_monitoring
   ```
   - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可能（デフォルト 60秒）
     ```
     export MONITOR_POLL_INTERVAL=30
     ```
   - 監視は常に本番 sqlite_path（Settings.sqlite_path）を使用してログ保存
   - SystemMonitor / TradeMonitor / RiskMonitor を用いて監視を実行、Kill Switch を評価して必要なら data/kill.flag を書き込む

5. Paper Trading 検証レポート生成
   ```
   python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   # DB を指定する場合
   python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
   ```

6. AI モジュール（プログラム的呼び出し）
   - news_nlp.score_news(conn, target_date, api_key=None)
   - ai.regime_detector.score_regime(conn, target_date, api_key=None)
   - どちらも OpenAI API キーが必要（引数 or OPENAI_API_KEY 環境変数）

7. リサーチ関数（DuckDB を開いて利用）
   - kabusys.research.calc_momentum(conn, date)
   - kabusys.research.calc_volatility(conn, date)
   - kabusys.research.calc_value(conn, date)
   - これらは DuckDB の tables（prices_daily / raw_financials 等）を前提

---

## 停止 / Kill フローの注意点

- 停止フラグ（監視が参照するもの）
  - data/stop_requested.flag — run_execution/run_monitoring などのスクリプトが起動ループを中止するために見るフラグ
  - data/kill.flag — Kill Switch（監視）によって書かれる。存在すると ExecutionEngine は安全に停止するよう設計されている
- Kill Switch の自動クリアは危険（本番では無効推奨）
  - KILL_FLAG_CLEAR_ON_START=1 にすると起動時に kill.flag をクリアします（開発用）

---

## ロギング

- ログはデフォルトで `logs/<app_name>.log` に日次ローテーションで保存されます（30日保持）。
- ルートロガーは `kabusys.utils.logging_setup.setup_logging(app_name, ...)` で初期化されています。
- LOG_LEVEL 環境変数でログレベルを上書き可能（例: DEBUG/INFO/WARNING/ERROR）

---

## よくあるトラブルシュート

- OpenAI API キーが無い / 未設定
  - news_nlp.score_news / regime_detector.score_regime は api_key 引数か OPENAI_API_KEY 環境変数が必要です。未設定だと ValueError が発生します。
- psutil の優先度設定でアクセス拒否（AccessDenied）
  - set_process_priority は権限や OS によって失敗する場合があります。失敗時は警告が出ますが動作は継続します。
- DuckDB / SQLite ファイル作成に失敗
  - `data` ディレクトリのパーミッションを確認してください。ログディレクトリ作成に失敗してもコンソール出力にフォールバックします。
- PyYAML がない場合
  - `validate_config` は YAML のパース検証をスキップしますが、ファイル存在チェックは引き続き行います。

---

## ディレクトリ構成（抜粋）

プロジェクトの重要なファイル・モジュールの配置（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / Settings 管理（.env 自動ロード機能含む）
  - config_setup.py                — .env 対話ウィザード
  - validate_config.py             — 起動前設定検証 CLI
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - run_monitoring.py              — Monitoring ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py  — ペーパートレード検証レポート
  - ai/
    - news_nlp.py                   — ニュースを LLM でスコアリング
    - regime_detector.py            — 市場レジーム判定
  - monitoring/
    - monitoring_db.py              — SQLite 永続化層（テーブル作成 / マイグレーション含む）
    - system_monitor.py
    - trade_monitor.py (参照されるが抜粋なし)
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (参照されるが抜粋なし)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - (その他: execution/, data/, strategy/ 等のサブパッケージ)

データ / 実行ファイル:
- data/ — default DB・フラグ・PID などを配置するディレクトリ（例: monitoring.db, paper_trading.db, kabusys.duckdb, kill.flag, stop_requested.flag, execution.pid）
- logs/ — ログ出力先

---

## 開発 / 貢献メモ

- .env は決して Git にコミットしないでください（config_setup でも注意書きあり）。
- DuckDB のスキーマ（prices_daily など）はリサーチ / AI モジュールで利用される前提です。データ投入スクリプトは別途管理してください。
- テストや CI では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使い自動 .env ロードを無効化すると扱いやすいです。

---

README は以上です。必要であれば「実行フロー図」「設定例ファイル」「Docker / systemd サービス定義例」なども追加で作成できます。どのドキュメントを優先して追加しますか？