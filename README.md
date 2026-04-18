# KabuSys

日本株向けの自動売買フレームワーク（小規模プロトタイプ）。  
信号生成・ポートフォリオ構築・発注エンジン・監視・リスクガード・研究ツール・AIベースのニュースセンチメント/レジーム判定などを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下のような機能を持つモジュール群で構成されています:

- データ分析（DuckDB を用いた価格・財務データ処理）
- ファクター計算・特徴量解析（research）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイジング）
- ExecutionEngine（発注管理・リスク制御・リコンシリエーション）
- 監視（System / Trade / Risk の定期チェック、Kill Switch）
- AI モジュール（OpenAI を使ったニュースセンチメント / レジーム判定）
- 各種 CLI ツール（.env ウィザード、設定検証、Paper Trading レポート生成）

設計上のポイント:
- 環境変数 / .env による設定管理
- Paper Trading は本番 DB とは分離（専用 SQLite）
- 監視は本番の monitoring DB を常に参照してログを保持
- AI コンポーネントは OpenAI API キーを必要とする（環境変数または引数で指定）

---

## 主な機能一覧

- 環境設定ウィザード（kabusys.config_setup）
  - 対話式に .env を作成・更新
- 設定検証 CLI（kabusys.validate_config）
  - .env と config/*.yaml のチェック
- 実行エンジン起動（kabusys.run_execution）
  - KABUSYS_ENV により Paper / Live を切替
  - Paper 環境は MockBroker を使い data/paper_trading.db を使用
- 監視ループ起動（kabusys.run_monitoring）
  - SystemMonitor をポーリングし monitoring DB に記録
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能
- 監視サブシステム
  - SystemMonitor: CPU/メモリ/Disk/データ鮮度/Process チェック
  - TradeMonitor: 滞留注文・約定価格異常検出
  - RiskMonitor: ドローダウン / ポジション上限監視
  - KillSwitch: 条件に応じた data/kill.flag 書き込み
  - MonitoringEngine: 各 Monitor を統合してポーリング・アラート発行
- ポートフォリオ構築ユーティリティ
  - 候補選定 / 等金額・スコア重み配分 / セクター制約適用 / ポジションサイズ計算
- Research（DuckDB ベースのファクター計算、IC 計算など）
- AI（OpenAI を用いたニュース NLP とレジーム判定）
  - バッチ化・リトライ・レスポンス検証を備えた実装
- ツール
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）

---

## セットアップ手順

前提:
- Python 3.9+（typing 記法に合わせて適宜）
- システムに sqlite3 は標準で同梱されていますが、以下 Python パッケージが必要です。

推奨インストール（pip）:
- duckdb
- psutil
- openai
- PyYAML（config/*.yaml 検証を行う場合）
- その他プロジェクトで使用する依存（必要に応じて pyproject.toml / requirements.txt を参照）

例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

.env の準備:
1. ウィザードを使って初期 .env を作成:
   ```bash
   python -m kabusys.config_setup
   ```
2. 生成後に設定を検証:
   ```bash
   python -m kabusys.validate_config
   # 警告もエラー扱いにしたい場合:
   python -m kabusys.validate_config --strict
   ```

ディレクトリに `data/` がない場合は自動作成されますが、事前に作成しておくと権限関連の問題を回避できます。

重要な環境変数（主なもの）:
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- OPENAI_API_KEY（AI モジュール使用時に必要）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（本番での通知用、任意）
- MONITOR_POLL_INTERVAL（監視ポーリング間隔秒、デフォルト 60）

ファイルフラグ・PID:
- data/kill.flag — Kill Switch のトリガーファイル
- data/stop_requested.flag — run_* スクリプトの停止フラグチェックに使用
- data/execution.pid — ExecutionEngine の PID ファイル（存在チェック）

注意（本番運用）:
- KABUSYS_ENV=live の場合は設定を慎重に（LINE 通知設定や Kill Switch 動作を確認）
- KILL_FLAG_CLEAR_ON_START は本番では 0 を推奨

---

## 使い方

一般的なワークフロー例:

1. .env を作成（ウィザード）
   ```bash
   python -m kabusys.config_setup
   ```

2. 設定検証
   ```bash
   python -m kabusys.validate_config
   ```

3. データ準備 / DuckDB ・ prices_daily 等のテーブル用意（本リポジトリの別スクリプトや ETL を利用）

4. ExecutionEngine を起動
   - Paper Trading（環境変数に KABUSYS_ENV=paper_trading を設定）:
     ```bash
     export KABUSYS_ENV=paper_trading
     python -m kabusys.run_execution
     ```
   - 本番（live）:
     ```bash
     export KABUSYS_ENV=live
     python -m kabusys.run_execution
     ```
   実行中に data/stop_requested.flag を作成すると、run_execution 側で検出してエンジンを停止します。

5. 監視プロセス起動
   ```bash
   # ポーリング間隔を 30 秒にする例
   export MONITOR_POLL_INTERVAL=30
   python -m kabusys.run_monitoring
   ```

6. Paper Trading の検証レポート生成
   ```bash
   # デフォルト DB を使う場合
   python -m kabusys.tools.paper_verification_report

   # 期間指定 / DB を指定する場合
   python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db
   ```

AI 関連（プログラムから呼び出す例）:
- ニューススコアリング（DuckDB 接続を渡して実行）
  - 公開 API: kabusys.ai.score_news(conn, target_date, api_key=None)
- レジーム判定:
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

注意: AI 関数は OPENAI_API_KEY を環境変数に設定するか、api_key 引数で渡してください。

プロセス優先度:
- 起動スクリプトは最初に set_process_priority("high") を呼びます。psutil による優先度設定が動作しない場合は警告を出してスキップします。

停止 / Kill Switch:
- RiskMonitor 等の判定により KillSwitch が data/kill.flag を書き込みます。ExecutionEngine はこのフラグを見て停止できます。

---

## 主要ファイル / コマンドの一覧

- python -m kabusys.config_setup
  - .env の対話式生成/更新
- python -m kabusys.validate_config
  - 設定を事前検証
- python -m kabusys.run_execution
  - ExecutionEngine を起動（paper_trading は専用 DB を使用）
- python -m kabusys.run_monitoring
  - SystemMonitor のポーリングを開始
- python -m kabusys.tools.paper_verification_report
  - Paper Trading の検証レポート出力

---

## ディレクトリ構成

（src 以下をパッケージとして想定）

- src/kabusys/
  - __init__.py
  - config.py
  - config_setup.py            — .env 対話ウィザード
  - validate_config.py         — 設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — SystemMonitor ポーリング起動スクリプト
  - utils/
    - __init__.py
    - process_priority.py      — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py         — SQLite ベースの永続化層（監視ログ）
    - system_monitor.py        — CPU / メモリ / データ鮮度 / PID チェック
    - trade_monitor.py         — 滞留注文 / 約定異常チェック
    - risk_monitor.py          — ドローダウン / ポジション上限監視
    - kill_switch.py           — kill.flag 書き込みユーティリティ
    - alert_manager.py         — （アラート送信機能、未記載の実装ファイル）
    - monitoring_engine.py     — 各 Monitor をまとめる
  - execution/                  — 発注エンジン関連（オーダー管理等）※一部参照あり
    - order_manager.py
    - order_repository.py
    - execution_engine.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
    - order_record.py
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
    - news_nlp.py               — ニュースセンチメントスコアリング（OpenAI）
    - regime_detector.py       — ETF MA + マクロニュースでレジーム判定（OpenAI）
    - __init__.py
  - tools/
    - paper_verification_report.py
    - __init__.py
  - monitoring/                 — （上記と同じ）監視関連
  - data/                       — デフォルト DB / フラグ / PID 保存先（リポジトリ直下）
    - monitoring.db (default: data/monitoring.db)
    - kabusys.duckdb (default: data/kabusys.duckdb)
    - paper_trading.db (default for paper trading)

注: 実際のリポジトリでは src 配下にさらに細分化されたモジュール・追加ファイルが存在します。ここには主要な構成を抜粋しています。

---

## 追加の注意点 / 運用上のヒント

- monitoring は常に Settings.sqlite_path（production 監視 DB）を使います。環境にかかわらず監視ログは同一の monitoring DB に書かれます。
- paper_trading 環境では ExecutionEngine は専用の paper_sqlite_path を用いるため、本番データベースと分離されます。
- OpenAI 呼び出しはレート制限・一時エラーに対してエクスポネンシャルバックオフでリトライしますが、APIキー・課金設定は運用者で管理してください。
- psutil を使ったプロセス優先度設定は OS の制約（権限）に依存します。権限が不足すると設定に失敗し警告が出ます。
- .env は絶対にバージョン管理にコミットしないでください（config_setup のヘッダにも注意書きがあります）。

---

この README はコードベースから抽出した主要情報に基づいて作成しています。各モジュールの詳細・使い方や追加スクリプトはソース内ドキュメント（docstring）を参照してください。質問や補足の希望があればお知らせください。