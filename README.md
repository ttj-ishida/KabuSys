# KabuSys

日本株向け自動売買フレームワーク（ライブラリ・実行スクリプト群）

このリポジトリは、戦略研究・ポートフォリオ構築・発注エンジン・監視機能・AI を用いたニュース解析などを統合した日本株自動売買システムのコア実装です。各機能はモジュール化されており、ペーパートレード運用や本番運用の切り替え、監視・Kill Switch による安全停止などを備えています。

主な特徴
- 戦略研究用モジュール（ファクター計算・特徴探索）
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ算出）
- ExecutionEngine（発注ロジック、OrderManager、RiskManager、Reconciler）
- 監視機能（SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / MonitoringEngine）
- AI モジュール（OpenAI を使ったニュースセンチメント、レジーム判定）
- ペーパートレード用の分離された DB（data/paper_trading.db）
- CLI ツール：.env ウィザード・設定検証・Paper Trading 検証レポートなど

以下、セットアップ方法・使い方・ディレクトリ構成をまとめます。

## 機能一覧（抜粋）
- 設定管理
  - .env 自動読み込み（プロジェクトルートの `.env`, `.env.local`）
  - `kabusys.config_setup` による対話式 .env 作成
  - `kabusys.validate_config` による起動前チェック
- 実行エンジン
  - ExecutionEngine（発注・リスク制御・Reconciler）
  - BrokerClientFactory（Kabu/Mock 切替、KABUSYS_ENV により Mock を使用）
  - ペーパートレードモード：完全に別 DB（data/paper_trading.db）で動作
- 監視/オートメーション
  - SystemMonitor：プロセス死活・CPU/MEM/DISK・データ鮮度チェック
  - TradeMonitor：滞留注文、約定異常チェック
  - RiskMonitor：ドローダウン・ポジション上限監視、ダッシュボード更新
  - KillSwitch：条件に応じて data/kill.flag を書き込み Execution を停止
  - MonitoringEngine：定期ポーリングとアラート連携
- 研究（Research）
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターン計算、IC（Information Coefficient）など
- AI（OpenAI）
  - news_nlp: raw_news をまとめて LLM に送信し、銘柄別スコアを ai_scores に書き込み
  - regime_detector: ETF 乖離＋マクロニュースで市場レジーム判定
- ツール
  - paper_verification_report: ペーパートレード履歴から成績・健全性レポート生成

## 前提・依存ライブラリ
主に以下が必要になります（プロジェクトに requirements.txt がない場合は適宜追加してください）:
- Python 3.9+
- duckdb
- psutil
- openai（AI 機能利用時）
- PyYAML（設定 YAML の検証オプション時）
- sqlite3（標準ライブラリ）

仮想環境を作成してインストールするのが推奨です。

例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

注意: OpenAI API は有料です。AI 機能を使う場合は API キー（OPENAI_API_KEY）を設定してください。

## 環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: 実行環境（development | paper_trading | live）。デフォルト: development
- DUCKDB_PATH: DuckDB ファイル (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH: 監視 SQLite DB (デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite (デフォルト: data/paper_trading.db)
- LOG_LEVEL: ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL）デフォルト INFO
- OPENAI_API_KEY: OpenAI を用いるモジュールで必要
- PAPER_FILL_MODE: paper_trading 時の約定モード（instant | partial | never | reject）。デフォルト: instant
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか (0|1)。本番では 0 推奨

自動ロード:
- プロジェクトルートに `.env` または `.env.local` がある場合、自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化可）。

## セットアップ手順（簡易）
1. リポジトリをクローン
2. 仮想環境を作成して依存をインストール
3. `.env` を作成
   - 自動で作る: python -m kabusys.config_setup
   - 手動で作る: `.env.example` を参照して `JQUANTS_REFRESH_TOKEN` や `KABU_API_PASSWORD` を設定
4. 設定検証（起動前チェック）:
   - python -m kabusys.validate_config
   - オプション `--strict` を付けると警告も失敗扱いにできます
5. DB 初期化は各起動スクリプトが必要に応じて行います（monitoring は init を行う）

## 使い方（主要コマンド）
- 設定ウィザード（.env 作成・更新）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証（起動前チェック）
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 監視ループ起動（Monitoring; MONITOR_POLL_INTERVAL で間隔上書き可）
  ```
  # デフォルト60秒ごと。環境変数で変更可能:
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```
  補足:
  - 監視は Settings.sqlite_path を使って monitoring DB に書き込みします（環境に関わらず本番 sqlite_path を参照）。
  - 監視は process priority を "high" に設定します（psutil による実行環境依存の処理）。

- ExecutionEngine 起動（実際の発注処理）
  ```
  python -m kabusys.run_execution
  ```
  補足:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い `data/paper_trading.db` に記録します（本番 DB と完全分離）。
  - 起動中は data/execution.pid に PID を書きます。停止指示は data/stop_requested.flag を作成すると検知して停止します。
  - 起動時に data/stop_requested.flag が既にある場合は起動をスキップします。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB 指定:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```
  生成される内容: 稼働率、注文成功率、送信率、レイテンシ統計、判定 PASS/FAIL（しきい値はソース内に設定）

- AI 関連（ニューススコア、レジーム判定）はライブラリ API 経由で利用:
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  例: DuckDB 接続を作って呼ぶ。OpenAI API キーは引数または OPENAI_API_KEY 環境変数から取得。

## 重要なファイル/フラグ
- data/execution.pid — ExecutionEngine の PID
- data/stop_requested.flag — run_execution / run_monitoring が監視する「停止要求」ファイル
- data/kill.flag — KillSwitch が書き込む停止指示ファイル（ExecutionEngine 側で検出・反応）
- data/monitoring.db — 監視ログ SQLite（デフォルト）
- data/paper_trading.db — ペーパートレード用 SQLite（paper_trading モード）
- data/kabusys.duckdb — DuckDB（分析用データベース）

Kill Switch の挙動:
- RiskMonitor がドローダウンなどの条件を満たすと KillSwitch が data/kill.flag を書き込むことがあります。
- ExecutionEngine は kill.flag の存在を検出して自己停止する設計です（安全対策）。
- 本番運用時は KILL_FLAG_CLEAR_ON_START=0 を推奨（起動時に自動でクリアされないようにする）。

MONITOR_POLL_INTERVAL:
- run_monitoring のポーリング間隔を環境変数 MONITOR_POLL_INTERVAL で変更できます（デフォルト 60 秒）。不正な値や 0/負数はデフォルトにフォールバックします。

PAPER_FILL_MODE:
- paper_trading 時の MockBroker の約定モード（instant / partial / never / reject）。不正値は設定エラーになります。

## ディレクトリ構成（主要ファイルのみ）
（ルート: src/kabusys/ を想定）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数/.env 管理（自動読み込み含む）
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 起動前の設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - ai/
    - news_nlp.py             — ニュース → AI スコアリング
    - regime_detector.py      — 市場レジーム判定（MA200 + マクロニュース + LLM）
  - monitoring/
    - monitoring_db.py        — SQLite テーブル定義 / 持続化 API
    - system_monitor.py       — CPU/MEM/DISK / プロセス / データ鮮度監視
    - trade_monitor.py        — 注文滞留 / 約定異常監視
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - kill_switch.py          — kill.flag の作成/削除
    - monitoring_engine.py    — 監視コンポーネントの統合・ポーリング
    - alert_manager.py        — 通知管理（LINE などへの実装想定）
  - execution/                 — 発注エンジン周辺（OrderManager, ExecutionEngine, BrokerFactory 等）
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
    - order_record.py
  - portfolio/
    - portfolio_builder.py    — 候補選定・重み付け
    - position_sizing.py      — 株数決定・資金配分
    - risk_adjustment.py      — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py      — モメンタム / ボラ / バリュー計算
    - feature_exploration.py  — 将来リターン・IC・統計サマリ
  - utils/
    - process_priority.py     — プロセス優先度 / CPU affinity ユーティリティ
  - data/ (ランタイムで作成される)
    - execution.pid
    - stop_requested.flag
    - kill.flag
    - monitoring.db
    - paper_trading.db
    - kabusys.duckdb

## 開発者向けの注意点 / ベストプラクティス
- 本番運用時は KABUSYS_ENV=live に設定する前に validate_config で警告・エラーを全て解消してください。
- `.env` は絶対にバージョン管理にコミットしないでください（秘匿情報を含む）。
- OpenAI を使う AI 機能はコストが発生します。API コールはバッチ化・リトライ制御が入っていますが、利用頻度には注意してください。
- プロセス優先度設定や CPU affinity は OS 権限に依存します。権限不足や未サポート環境では警告ログが出て処理はスキップされます。
- ペーパートレードは本番 DB と分離されます（PAPER_TRADING_SQLITE_PATH）。実際の発注や資金移動は行われませんが、ロジックは本番に近い形で動作します。

## よく使うコマンドまとめ
- .env ウィザード:
  ```
  python -m kabusys.config_setup
  ```
- 設定検証:
  ```
  python -m kabusys.validate_config
  ```
- 監視開始:
  ```
  MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
  ```
- 実行エンジン起動:
  ```
  python -m kabusys.run_execution
  ```
- ペーパートレード検証レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

README はここまでです。必要であれば以下も作成できます：
- requirements.txt の推奨依存リスト
- systemd / supervisor 用のユニットファイルのサンプル（run_execution / run_monitoring 用）
- alert_manager の LINE 実装例（Webhook / Messaging API）
ご希望があれば対応します。