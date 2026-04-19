# KabuSys

日本株向け自動売買システムの参照実装（ライブラリ / 起動スクリプト /運用ツール群）。

以下はこのリポジトリに含まれる主要機能、セットアップ・運用手順、開発時に便利なコマンド群をまとめた README です。

## プロジェクト概要
KabuSys は日本株自動売買のためのコンポーネント群を提供します。主な要素は次のとおりです。

- ExecutionEngine（発注エンジン）: ブローカークライアントを用いて注文管理、リスク管理、約定の再整合を行う。
- Monitoring（監視）: システム稼働状況・データ鮮度・注文状態・リスク指標を定期モニタリングし、必要に応じて Kill Switch（強制停止）を発動する。
- Portfolio（ポートフォリオ構築）: 候補選定、重み計算、ポジションサイズ決定、セクター制限・レジーム乗数など純粋関数群。
- Research（リサーチ）: DuckDB を用いたファクター計算・特徴量探索ユーティリティ。
- AI（ニュース NLP / レジーム判定）: OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価・市場レジーム判定機能（任意）。
- ツール群: .env 対話式ウィザード、設定検証、Paper Trading 検証レポート生成スクリプトなど。

設計方針として、運用上の安全策（ペーパートレード分離、Kill Switch、ログ回転、DB マイグレーションの冪等性、LLM 呼び出しのリトライ/フォールバック）を盛り込んでいます。

---

## 機能一覧
- 実行環境切替（KABUSYS_ENV: development / paper_trading / live）
  - paper_trading では MockBrokerClient を使用し、Paper 用 SQLite DB（data/paper_trading.db など）へ記録する。
- 監視ループ（SystemMonitor / TradeMonitor / RiskMonitor）とアラート（AlertManager 経由）
- Kill Switch：重大なリスク検出時に data/kill.flag を書き込み ExecutionEngine を停止
- 設定ウィザード（対話式 .env 生成）
- 設定検証 CLI（.env と config/*.yaml の存在／基本整合性チェック）
- Paper Trading 検証レポート生成（稼働率、注文成功率、レイテンシ等の判定）
- DuckDB を使ったファクター計算（Momentum, Volatility, Value など）
- ニュース NLP / レジーム判定（OpenAI を利用、API キー必須）
- ログ管理: 日次ローテーション（logs/<app_name>.log）、コンソールは stdout 出力

---

## 必要条件（依存）
最低限必要な Python パッケージ（例）
- python >= 3.10（リポジトリの型注釈などから推定）
- duckdb
- psutil
- openai（AI 機能を使う場合）
- PyYAML（config YAML 検証を行う場合）
- その他はサブモジュールや利用機能に応じて追加

インストール例:
```bash
pip install duckdb psutil openai pyyaml
```

（プロジェクトでは requirements.txt を用意していればそちらを使ってください）

---

## セットアップ手順（開発 / 初期運用）
1. リポジトリをクローン／チェックアウト
2. Python 環境を用意（仮想環境推奨）
   - python -m venv .venv
   - source .venv/bin/activate
3. 依存パッケージをインストール
   - pip install -r requirements.txt  または  pip install duckdb psutil openai pyyaml
4. .env の作成（対話ウィザード）
   - python -m kabusys.config_setup
     - J-Quants トークン、kabu API パスワード、DB パス、KABUSYS_ENV 等を設定
   - 自動ロード: プロジェクトルートの .env / .env.local は自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）
5. 設定検証
   - python -m kabusys.validate_config
   - 問題が無いか確認（--strict で警告もエラー扱い）
6. データディレクトリ（logs/、data/）が必要に応じて作成されます。多くのモジュールは起動時にディレクトリを作成しますが、必要に応じて手動で作成してください。

---

## 使い方（主要コマンド）
※いずれもプロジェクトルートから実行することを想定しています（.env 自動ロードが有効な場合）。

- 設定ウィザード（.env の作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード: python -m kabusys.validate_config --strict

- ExecutionEngine（実際の発注ロジック）起動
  - python -m kabusys.run_execution
  - 動作: 起動時にプロセス優先度を "high" に設定。KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 DB に記録（本番とは分離）
  - 実行中の停止:
    - 外部から停止フラグ（data/stop_requested.flag）を作成すると起動スレッドが検知して停止します。
    - Kill Switch（監視側）が data/kill.flag を書き込んだ場合も Engine 側が検出して停止します。
  - PID ファイル: data/execution.pid（エンジンが利用）

- Monitoring（監視ループ）起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き（デフォルト: 60 秒）
  - 監視は Settings.sqlite_path（本番 SQLite）を使用（KABUSYS_ENV に依らず）
  - 停止:
    - stop_requested.flag を作成するとループが終了します

- Paper Trading 検証レポート生成（ツール）
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - 環境変数 PAPER_TRADING_SQLITE_PATH で DB を指定可能（デフォルト: data/paper_trading.db）
  - 出力: 稼働率、注文成功率、送信率、レイテンシ等の判定と PASS/FAIL

- AI 関連（ニュース NLP / レジーム判定）
  - OpenAI API キー（OPENAI_API_KEY または関数引数）を必要とします。
  - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime をプログラムから呼び出して使用します。
  - LLM 呼び出しはリトライ・フォールバック設計（失敗時は安全側のデフォルト値で継続）

---

## 運用上の重要ポイント
- KABUSYS_ENV
  - 有効値: development / paper_trading / live
  - paper_trading は発注を模擬（本番 DB と分離）
  - live は本番のため設定ミス（LINE 通知未設定、KILL_FLAG_CLEAR_ON_START=1 等）に注意
- データベース
  - DuckDB: デフォルト data/kabusys.duckdb（分析用）
  - SQLite (monitoring): data/monitoring.db（監視ログ）
  - Paper Trading SQLite: data/paper_trading.db（paper_trading 時に使用）
- Kill / Stop フラグ
  - 実行エンジンは data/stop_requested.flag を定期チェックして安全に停止できます（運用停止時の手段）
  - Kill Switch（監視側）は data/kill.flag を書き込み ExecutionEngine に強制停止シグナルを送ります（発動要因はドローダウン超過やポジション上限超過など）
  - Execution 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動でクリアする挙動になりますが、本番では推奨されません
- ログ
  - デフォルトは logs/<app_name>.log（日時ローテーション・30日保持）
  - コンソール出力は stdout（cron 等での運用に合わせるため stderr ではなく stdout）
  - 環境変数 LOG_DIR / LOG_LEVEL で上書き可能
- プロセス優先度
  - 起動スクリプトは set_process_priority("high") を呼び出して優先度を上げようとしますが、権限や OS に依存して失敗する場合があります（警告のみ）
- .env 自動ロード
  - プロジェクトルート（.git または pyproject.toml を基準）を特定して .env / .env.local を自動ロードします
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能

---

## 主要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (AI 機能を使う場合)
- KABUSYS_ENV (development / paper_trading / live) — デフォルト: development
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL) — デフォルト: INFO
- LOG_DIR (デフォルト: logs/)
- MONITOR_POLL_INTERVAL (監視ポーリング間隔 秒、デフォルト 60)
- KILL_FLAG_CLEAR_ON_START (0/1、デフォルト 0)

詳細は kabusys.config.Settings のプロパティ実装を参照してください（デフォルト値・妥当性チェックが定義されています）。

---

## ディレクトリ構成（主要ファイル）
以下は src/kabusys 配下の主な構成です（抜粋）。

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数読み込み / Settings
    - config_setup.py          — .env 対話ウィザード
    - validate_config.py       — 設定検証 CLI
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
    - utils/
      - logging_setup.py       — ログ設定ユーティリティ
      - process_priority.py    — 優先度 / CPU affinity
    - execution/                — 発注・リスク・再整合など（エンジン本体）
      - execution_engine.py
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py
      - broker_factory.py
    - monitoring/
      - monitoring_db.py       — 監視用 SQLite 永続層
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - monitoring_engine.py
      - kill_switch.py
      - alert_manager.py
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
    - tools/
      - paper_verification_report.py

ルートに存在が期待されるディレクトリ／ファイル（実行/運用時）:
- data/                      — SQLite DB やフラグファイル（data/monitoring.db, data/paper_trading.db, data/kill.flag, data/stop_requested.flag, data/execution.pid 等）
- logs/                      — ログ出力先（logs/execution.log, logs/monitoring.log など）
- .env / .env.local          — 環境変数設定（config_setup で作成可能）
- config/*.yaml              — 運用用の設定テンプレート（validate_config で検証）

---

## よくある運用シナリオ
- 開発（ローカルで動かす）
  - KABUSYS_ENV=development（デフォルト）、.env を作成して execution を起動（実際の発注は行われない実装を想定）
- ペーパートレード
  - KABUSYS_ENV=paper_trading を設定。paper 用 DB に記録され、本番 DB と分離される。
  - Paper トレード検証: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- 本番
  - KABUSYS_ENV=live。事前に validate_config で警告・必須項目を確認すること。Kill Switch や LINE 通知設定等を整備する。

---

## 開発者向けメモ
- DB マイグレーションは簡易的にコード内で実行（monitoring_db.init_monitoring_db がカラム追加などを行う）
- AI 関連の API 呼び出しはリトライ制御とレスポンス検証を行う実装になっているため、テスト時は外部呼び出し部分をモックしてください（モジュール内に _call_openai_api を用意しており patch 可能）
- Logging はすべての起動スクリプトから setup_logging を呼んで統一してください

---

## トラブルシュート
- 起動直後に kill.flag が存在していると ExecutionEngine を起動しない挙動があります。運用でエンジンを再起動したい場合は data/kill.flag を削除してください（ただし本番では慎重に）。
- ログディレクトリ作成に失敗した場合はファイル出力が無効化されコンソール出力のみになります。パーミッションや SELinux を確認してください。
- OpenAI 呼び出しで 429/タイムアウト/5xx が発生した場合は内部でリトライ後にフォールバックしますが、API キーやレート制限設定を確認してください。

---

この README はリポジトリのコードから要点を抜粋して作成しています。詳細な挙動や内部 API は各ソースファイル（src/kabusys 以下）を参照してください。質問や追加したい項目があれば教えてください。