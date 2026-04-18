# KabuSys

日本株自動売買システム（KabuSys）のリポジトリ内 README。  
この README はコードベース（src/kabusys 以下）に基づき、セットアップと主要な使い方を日本語でまとめたものです。

---

目次
- プロジェクト概要
- 主な機能
- 前提（依存関係）
- セットアップ手順
- 環境設定（.env）ウィザード
- 設定検証
- 起動 / 使い方（主要スクリプト）
- 停止・Kill Switch の使い方
- ロギング
- ディレクトリ構成（主要ファイル解説）
- 主要な環境変数一覧
- 備考 / 運用上の注意

---

## プロジェクト概要
KabuSys は日本株を対象とした自動売買システムのコードベースです。  
主な役割は以下のとおりです：
- 戦略（ファクター計算・特徴量探索）による銘柄選定
- ポートフォリオ構築・ポジションサイズ計算
- 発注エンジン（ExecutionEngine）とブローカークライアント（paper/live 切替）
- 監視（System / Trade / Risk）および Kill Switch（緊急停止）
- Paper Trading 向けの検証レポート生成
- ニュース NLP を用いた AI スコアリングおよび市場レジーム判定（OpenAI API 利用）

---

## 主な機能
- Research:
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（情報比率）計算、統計サマリー
- Portfolio:
  - 候補選定、等金額/スコア加重、リスク調整（セクター上限、レジーム乗数）、ポジション数計算（単元丸め含む）
- Execution:
  - 本番 / ペーパートレードの切替（paper_trading 環境時は MockBrokerClient を使用し DB を分離）
- Monitoring:
  - システム状態・データ鮮度・取引ログ・リスク監視
  - Kill Switch（閾値超過時に data/kill.flag を書き込み、Execution を停止）
- AI:
  - ニュースを OpenAI に送り銘柄ごとのセンチメントスコアを生成し ai_scores に記録
  - マクロ記事 + ETF MA200 乖離を組み合わせて市場レジーム判定
- ユーティリティ:
  - .env ウィザード（対話式）、設定検証 CLI、Paper Trading 検証レポート生成

---

## 前提（依存関係）
必須（主要）パッケージ（例）:
- Python 3.9+
- duckdb
- psutil
- openai（AI 機能利用時）
- PyYAML（設定ファイルの内容検証を行う場合は必要）

インストール例（仮想環境推奨）:
```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# もし requirements.txt が無い場合:
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリをクローン・作業ディレクトリに移動

2. Python 環境を準備して依存パッケージをインストール（上記参照）

3. .env の作成（対話式ウィザード推奨）
   ```
   python -m kabusys.config_setup
   ```
   ウィザードが .env を生成します。生成後は `python -m kabusys.validate_config` で基本的な検証を行ってください。

4. ローカル DB（data ディレクトリ）やログディレクトリは起動スクリプトが自動で作成しようとしますが、必要に応じて手動で作成しておくと確実です。
   - デフォルト:
     - DuckDB: data/kabusys.duckdb
     - SQLite（監視）: data/monitoring.db
     - Paper Trading SQLite: data/paper_trading.db
     - PID / flag: data/execution.pid, data/kill.flag, data/stop_requested.flag
     - ログ: logs/

---

## 環境設定（.env）
対話式ウィザードで主要な環境変数を設定できます。主要なキー例:
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- KABUSYS_ENV（development / paper_trading / live）
- LOG_LEVEL（DEBUG / INFO / ...）
- KILL_FLAG_CLEAR_ON_START（0/1、production では 0 推奨）
- PAPER_FILL_MODE（instant/partial/never/reject）

.env の自動読み込み:
- デフォルトでプロジェクトルート（.git または pyproject.toml 基準）にある `.env` / `.env.local` が自動で読み込まれます。
- 自動ロードを無効にする場合: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

簡単な .env 例（ウィザードで生成されます）:
```
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0
```

---

## 設定検証
設定・ファイルを起動前に検証します:
```
python -m kabusys.validate_config
# 警告も fail 扱いにする:
python -m kabusys.validate_config --strict
```
このスクリプトは必須環境変数、KABUSYS_ENV、パスの親ディレクトリ、config/*.yaml の存在とパース（PyYAML がインストールされている場合）などをチェックします。

---

## 起動 / 使い方（主要スクリプト）

スクリプトはモジュールとして実行します（パッケージがパスにあること前提）。

1. ExecutionEngine（発注エンジン）起動
   - 本番 / ペーパートレードは KABUSYS_ENV に依存:
     - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、データは data/paper_trading.db に保管（本番 DB と分離）
   ```
   # 実行
   python -m kabusys.run_execution
   ```
   動作:
   - process priority を high に設定（psutil を使用）
   - SQLite / DuckDB に接続
   - ExecutionEngine を別スレッドで起動し、data/stop_requested.flag の存在を監視して終了

2. Monitoring（監視）起動
   ```
   python -m kabusys.run_monitoring
   ```
   オプション:
   - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で秒単位に設定可能（デフォルト 60）
   動作:
   - SystemMonitor（CPU / メモリ / ディスク / データ鮮度 / Execution プロセスの有無）や RiskMonitor、TradeMonitor をポーリングしてログ・アラート生成
   - Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使用する（監視データは共通）

3. Paper Trading 検証レポート生成
   ```
   python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   # DB を明示する場合:
   python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
   ```
   レポートは稼働率、注文成功率、送信率、レイテンシ（P95）等を算出し PASS/FAIL を判定します。

4. 環境設定ウィザード（再掲）
   ```
   python -m kabusys.config_setup
   ```

5. AI 機能（プログラム的に利用）
   - ニューススコアリング:
     - 関数: `kabusys.ai.score_news(conn, target_date, api_key=None)`
     - 引数は DuckDB 接続（duckdb.connect(...) の接続オブジェクト）と target_date（datetime.date）
     - OpenAI API キーは引数または環境変数 `OPENAI_API_KEY`
   - レジーム判定:
     - 関数: `kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)`

---

## 停止・Kill Switch・フラグファイル

- ExecutionEngine と Monitoring の双方で停止フラグを監視します:
  - data/stop_requested.flag: run_execution.py / run_monitoring.py はこのファイルの存在を見て安全終了します（停止フラグを作成することで外部から停止可）。
  - Kill Switch: `KillSwitch` は内部監視で条件を満たすと `data/kill.flag` に理由を書き込みます。ExecutionEngine は起動時にこのフラグの存在を検査し、存在する場合は起動しません（本番の強制停止用）。
- Kill flag を自動でクリアしたい場合は `.env` の `KILL_FLAG_CLEAR_ON_START=1` を設定できますが、本番では推奨されません。

停止例（外部から安全停止を通知）:
```
# 停止リクエスト（任意の内容を書いてよい）
mkdir -p data
echo "stop requested" > data/stop_requested.flag
```

---

## ロギング
- 共通ロギング設定は `kabusys.utils.logging_setup.setup_logging` で行います。
- ログは stdout に加えて日次ローテートされたファイルに出力されます（既定 `logs/<app_name>.log`、30日保持）。
- ログディレクトリは `LOG_DIR` 環境変数または引数 `log_dir` で変更可。
- ログレベルは `.env` の `LOG_LEVEL` / 引数で指定できます（デフォルト INFO）。

---

## ディレクトリ構成（主要ファイルの説明）
（src/kabusys をルートとした主要モジュール）

- kabusys/
  - __init__.py — パッケージメタ情報（__version__ 等）
  - config.py — 環境変数 / 設定管理（Settings クラス、自動 .env ロード）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring 起動スクリプト

  - ai/
    - news_nlp.py — ニュースを OpenAI に送り銘柄スコア（ai_scores）を生成するロジック
    - regime_detector.py — マクロ + ETF MA200 乖離を使って市場レジームを判定
  - monitoring/
    - monitoring_db.py — SQLite ベースの監視 DB 初期化・永続レイヤ
    - system_monitor.py — システム状態・データ鮮度監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - trade_monitor.py — （取引の監視。コードベースにあるはずの監視ロジック）
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - kill_switch.py — kill.flag の管理
    - alert_manager.py — （通知管理。LINE 等へ通知する実装箇所）
  - execution/
    - execution_engine.py — ExecutionEngine のコア（エンジン制御）
    - broker_factory.py — ブローカクライアント生成（本番 / mock 切替）
    - order_manager.py / order_repository.py / reconciler.py / risk_manager.py — 発注 / リスク管理関連
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数決定・資金配分
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — ファクター計算（momentum/volatility/value）
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - data/
    - pipeline.py — データ取り込み・取得ユーティリティ（get_last_price_date 等）
    - stats.py — 正規化ユーティリティ（zscore_normalize 等）
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成 CLI

- data/ （実行時に生成される想定）
  - kabusys.duckdb
  - monitoring.db（SQLite）
  - paper_trading.db（ペーパートレード用 SQLite）
  - execution.pid, kill.flag, stop_requested.flag

- logs/
  - execution.log, monitoring.log, ...（日次ローテーション）

---

## 主要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN — J-Quants API（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABU_API_BASE_URL — kabu API のベース URL
- KABUSYS_ENV — execution モード（development / paper_trading / live）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE — paper_trading の約定モード（instant / partial / never / reject）
- OPENAI_API_KEY — OpenAI 利用時の API キー（AI 機能）
- LOG_LEVEL — ログレベル
- LOG_DIR — ログ出力先ディレクトリ
- MONITOR_POLL_INTERVAL — Monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag をクリアするか（0/1）

---

## 備考 / 運用上の注意
- 本番（KABUSYS_ENV=live）では `.env` の設定・LINE 通知設定・Kill Switch の取扱いを十分に注意してください。validate_config は live のときに警告を出すチェックを行います。
- run_execution はプロセス優先度を上げる処理を行います（psutil を使用）。アクセス権限が無い場合は警告を出して続行します。
- Monitoring と Execution は flag ファイル（stop_requested.flag / kill.flag）によって外部から制御できます。運用用の停止フローを事前に定義しておくことを推奨します。
- AI を使用する機能は外部 API（OpenAI）に依存します。API 呼び出しの失敗やレート制限時はリトライやフォールバック（スコア 0 など）処理が実装されていますが、運用時は API キーと料金、レート制限を管理してください。
- DB マイグレーション: monitoring_db.init_monitoring_db は冪等でテーブル・インデックスを作成し、一部カラム追加の簡易マイグレーションを行います。

---

もし README に追加したい情報（例: 実行時のログ出力例、ユニットテストの実行方法、Docker / systemd ユニット例、CI 設定など）があれば教えてください。必要に応じて実運用向けの手順や systemd ユニットのサンプルも作成します。