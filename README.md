# KabuSys — 日本株自動売買システム

軽量な日本株自動売買フレームワークのプロジェクトです。取引実行・監視・リスク管理・ポートフォリオ構築・研究用ファクター計算・ニュースNLP（OpenAI 経由）など、運用に必要な主要コンポーネントを含みます。

## 概要
このリポジトリは、以下の主要機能を持つモジュール群で構成されています。

- ExecutionEngine：発注ロジック、ブローカークライアント抽象化、リスク管理、注文管理
- Monitoring：システム状態・注文の監視、Kill Switch（自動停止）・アラート連携
- Portfolio：銘柄選定、重み付け、ポジションサイジング、セクター制約適用
- Research：DuckDB を使ったファクター計算・特徴量解析（モメンタム、バリュー、ボラティリティ等）
- AI：ニュースのセンチメント評価や市場レジーム判定（OpenAI API を利用）
- Utilities：ログ設定・プロセス優先度設定などのユーティリティ
- CLI ツール：.env 設定ウィザード、設定検証、ペーパートレード検証レポート等

設計方針の一部：
- DuckDB / SQLite を使ったローカル DB 管理（分析用と監視/発注履歴で分離）
- Paper Trading（KABUSYS_ENV=paper_trading）時はモックブローカーを使い、本番 DB と分離
- ルックアヘッドバイアス回避（日時参照方法への配慮）
- フェイルセーフを重視（API 失敗時は安全側で続行）

## 主な機能一覧
- 起動用スクリプト
  - python -m kabusys.run_execution：ExecutionEngine 起動（発注処理）
  - python -m kabusys.run_monitoring：SystemMonitor ポーリング起動（デフォルト 60 秒）
- 環境設定 / 検証
  - python -m kabusys.config_setup：対話式 .env 作成/更新ウィザード
  - python -m kabusys.validate_config：起動前の設定検証（--strict オプションあり）
- ポートフォリオ構築
  - 候補選定・等金額/スコア加重・リスクベースの株数算出・セクターキャップ適用
- 研究用モジュール
  - DuckDB を使ったモメンタム/バリュー/ボラティリティ計算、将来リターン・IC 計算
- AI 関連
  - ニュース記事の銘柄別センチメント評価（OpenAI）
  - マクロニュース + ETF MA 乖離から市場レジーム判定
- 監視・リスク管理
  - system_status / trade_logs / positions / risk_logs / dashboard の永続化
  - ドローダウン・ポジション上限に応じた Kill Switch（data/kill.flag 書き込み）
  - ペーパートレード検証レポート生成ツール

## 必要環境（推奨）
- Python 3.10+
- 推奨パッケージ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証で任意）
- （環境により）SQLite は標準ライブラリで利用可能

※ requirements.txt がある場合はそれを利用してください。ない場合は上のパッケージを手動でインストールしてください。

例：
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

## セットアップ手順（概要）
1. リポジトリをクローンして作業ディレクトリに移動
2. 仮想環境を作成して有効化
3. 依存パッケージをインストール（上記参照）
4. 環境変数設定
   - 推奨: python -m kabusys.config_setup を実行して .env を生成
   - 必須環境変数（一例）
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - OPENAI_API_KEY（AI 機能を使う場合）
   - 重要な設定例（.env のキー）
     - KABUSYS_ENV: development | paper_trading | live
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト data/paper_trading.db）
     - LOG_LEVEL（例: INFO）
     - KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか 0/1）
5. 設定検証
```
python -m kabusys.validate_config
python -m kabusys.validate_config --strict
```
6. 実行前に必要なら data/ ディレクトリを作成（ログや DB は自動作成されることが多いですが念のため）

## 使い方（主要コマンド）
- 環境ウィザード（.env 作成/更新）
```
python -m kabusys.config_setup
```

- 設定検証
```
python -m kabusys.validate_config
python -m kabusys.validate_config --strict
```

- ExecutionEngine を起動（発注処理）
```
python -m kabusys.run_execution
```
挙動：
- KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）に記録します。実口座への発注は行いません。
- 起動時に data/stop_requested.flag が存在すると起動を行わず終了します。
- 実行中は data/execution.pid（デフォルト）に PID を書き込みます。停止は stop flag の作成で行います。

- Monitoring を起動（定期監視）
```
python -m kabusys.run_monitoring
```
挙動：
- ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）。
- 監視は常に本番の sqlite_path を参照して監視ログを保存します（KABUSYS_ENV に依存せず）。
- data/stop_requested.flag を検出するとループを終了します。

- Paper Trading 検証レポート
```
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# または DB を直接指定
python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
```

- ログ
  - デフォルトは logs/<app_name>.log（例: logs/execution.log, logs/monitoring.log）
  - LOG_DIR 環境変数で変更可能
  - ログレベルは LOG_LEVEL（例: INFO, DEBUG）

## 停止と Kill Switch
- 実行中の ExecutionEngine を外部から停止する方法：
  - 強制停止（Kill Switch）: KillSwitch モジュールが条件を満たすと data/kill.flag を書き込み、ExecutionEngine はそれを検出して安全に停止します。
  - 手動停止: data/stop_requested.flag を作成すると run_execution/run_monitoring のループが検知して終了します。
- 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動でクリアします（本番環境では 0 を推奨）。

## 主要な環境変数（抜粋）
- KABUSYS_ENV (development | paper_trading | live) — 実行モード
- JQUANTS_REFRESH_TOKEN — J-Quants API トークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合）
- DUCKDB_PATH（デフォルト data/kabusys.duckdb）
- SQLITE_PATH（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）
- LOG_LEVEL（デフォルト INFO）
- LOG_DIR（デフォルト logs/）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔、秒）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動でクリアするか。0/1）

## ディレクトリ構成（抜粋）
プロジェクトの主要ファイルとディレクトリ構成（src 以下がパッケージ実体）:

```
src/kabusys/
├── __init__.py
├── config.py                   # 環境変数/設定読み込みロジック
├── config_setup.py             # .env 対話ウィザード
├── validate_config.py          # 設定検証 CLI

├── run_execution.py            # ExecutionEngine 起動スクリプト
├── run_monitoring.py           # Monitoring 起動スクリプト

├── utils/
│   ├── __init__.py
│   ├── logging_setup.py        # ログ設定ユーティリティ
│   └── process_priority.py     # プロセス優先度 / CPU affinity

├── monitoring/
│   ├── monitoring_db.py        # SQLite 永続化層
│   ├── system_monitor.py
│   ├── trade_monitor.py        # （省略した実装ファイルが存在）
│   ├── risk_monitor.py
│   ├── kill_switch.py
│   └── monitoring_engine.py

├── execution/
│   ├── execution_engine.py     # エンジン本体（起動・セッション管理）
│   ├── broker_factory.py       # ブローカークライアント生成
│   ├── order_manager.py
│   ├── order_repository.py
│   ├── reconciler.py
│   └── risk_manager.py

├── portfolio/
│   ├── __init__.py
│   ├── portfolio_builder.py
│   ├── position_sizing.py
│   └── risk_adjustment.py

├── research/
│   ├── __init__.py
│   ├── factor_research.py
│   └── feature_exploration.py

├── ai/
│   ├── __init__.py
│   ├── news_nlp.py             # ニュース NLP / OpenAI 呼び出し
│   └── regime_detector.py      # 市場レジーム判定（MA + マクロ NLP）

├── monitoring/                  # 上述の監視関連（別フォルダ）
└── tools/
    ├── __init__.py
    └── paper_verification_report.py
```

（実際のリポジトリにはさらに追加のファイルやディレクトリが含まれる場合があります）

## DB マイグレーション / 初期化
- monitoring_db.init_monitoring_db(conn) が監視用 SQLite のテーブル作成と簡易マイグレーションを実行します（冪等）。
- DuckDB / SQLite の既定パスは .env で変更可能です。

## 開発・貢献
- 新機能追加や修正はモジュール分離の方針に従い、ユニットテストと静的解析（型チェック）を併用することを推奨します。
- OpenAI 関連の関数は外部 API に依存するため、テスト時はモック（unittest.mock）で API 呼び出しを差し替えてください。
- .env は機密情報を含みうるため、絶対にリポジトリにコミットしないでください。

## 参考・補足
- 一部の機能（YAML 検証など）は任意パッケージ（PyYAML）がインストールされていない場合はスキップされます。
- Paper Trading 用 DB は本番の監視 DB と分離されており、ペーパーと本番のデータ混在を避ける設計です。
- ログは stdout（StreamHandler）と日次ローテートされたファイル（TimedRotatingFileHandler）に出力されます。ログディレクトリの作成に失敗した場合はコンソールのみで継続します。

---

不明点や README に追記してほしい箇所（例: 実行フロー図、API のインタフェース仕様、サンプル .env）などがあれば教えてください。必要に応じて README を拡張します。