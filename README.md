# KabuSys

日本株自動売買システム（KabuSys）のドキュメント README。  
このリポジトリは戦略・発注・監視・研究ツール群を含むモジュール群で構成されています。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買を目的とした統合システムです。  
主な要素は次の通りです。

- ExecutionEngine：ブローカーとのやり取り（発注・約定管理・リスク制御）
- Monitoring：システム稼働状態・オーダー異常・リスク監視と Kill Switch
- Research：DuckDB を用いたファクター計算 / 特徴量解析
- Portfolio：銘柄選定・重み計算・ポジション決定ロジック（純粋関数群）
- AI モジュール：ニュースの NLP によるセンチメント評価 / レジーム判定
- ユーティリティ：設定ウィザード・設定検証・ログ設定等

設計方針の一部：
- 本番 DB とペーパートレード DB を明確に分離可能
- DuckDB を分析用に利用（prices_daily, raw_financials 等）
- OpenAI を利用した NLP 処理は API キー必須・失敗時はフェイルセーフ化

---

## 機能一覧

- 設定関連
  - 対話式 .env 作成ウィザード（python -m kabusys.config_setup）
  - 起動前設定検証 CLI（python -m kabusys.validate_config）
- 実行 / ランタイム
  - ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 DB に書き込む
  - Monitoring 起動スクリプト（python -m kabusys.run_monitoring）
    - 定期ポーリングで System/Trade/Risk をチェック。MONITOR_POLL_INTERVAL で間隔を設定可
- 監視 / 安全装置
  - Kill Switch：条件に応じて data/kill.flag を書き込み、ExecutionEngine を停止させる
  - RiskMonitor：ドローダウン・ポジション上限の監視とログ記録
  - MonitoringDB：監視用 SQLite スキーマの初期化・永続化
- 研究 / ツール
  - ファクター計算（momentum/value/volatility 等）
  - 特徴量探索・IC 計算・統計サマリー
  - Paper Trading 検証レポート生成（python -m kabusys.tools.paper_verification_report）
- AI（OpenAI）
  - ニュースセンチメント評価（kabusys.ai.news_nlp）
  - 市場レジーム判定（kabusys.ai.regime_detector）
  - OpenAI API 呼び出しはリトライ等の耐障害性を備える

---

## セットアップ手順（開発環境向け）

前提：
- Python 3.10 以上（型注釈で | を使用）
- SQLite は標準で同梱
- 推奨パッケージ（最低限）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - pyyaml（config 検証で YAML をパースしたい場合）

例（venv を使う）:
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
2. 必要パッケージをインストール
   - pip install duckdb psutil openai pyyaml
   （プロジェクトに requirements.txt があればそれを利用してください）

3. .env の作成（対話式ウィザード）
   - python -m kabusys.config_setup
   - ウィザードは .env を生成します（.env は絶対に Git 管理下に置かないでください）

4. 設定検証
   - python -m kabusys.validate_config
   - 必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など）が設定されているか確認

5. ディレクトリ
   - 実行時に data/ と logs/ は自動作成されますが、権限に注意してください

---

## 環境変数（主なもの）

- KABUSYS_ENV: 実行環境（development / paper_trading / live）。デフォルト development
  - paper_trading: 発注は仮想（MockBrokerClient）／data/paper_trading.db を使用
  - live: 実際のブローカーへ発注（注意して設定）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI を使う場合は必須（news_nlp / regime_detector）
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- LOG_DIR: ログ保存先（デフォルト logs/）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: ExecutionEngine 起動時に kill.flag を自動クリアする（"1" 有効。production では 0 推奨）

---

## 使い方（主なコマンド）

- .env 作成（対話式）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード（警告も失敗扱い）: python -m kabusys.validate_config --strict

- ExecutionEngine 起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、paper_trading DB に分離される:
    - デフォルト: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で変更可）
  - 起動前に data/stop_requested.flag が存在すると起動を中止します
  - 実行中はデーモンスレッドで engine.run_session を実行し、同フラグで停止

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可（デフォルト 60）
  - Monitoring は KABUSYS_ENV にかかわらず sqlite_path（本番の monitoring DB）を使用
  - stop フラグファイル: data/stop_requested.flag を検出するとループを終了

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - --db を省略すると PAPER_TRADING_SQLITE_PATH または data/paper_trading.db を使います

- AI 関連（プログラムから呼び出し）
  - OpenAI API キーが必要（OPENAI_API_KEY）
  - news_nlp.score_news / regime_detector.score_regime を呼んで DuckDB に書き込みます

---

## 重要ファイル・フラグ

- data/stop_requested.flag
  - 実行スクリプトがこのファイルを検知すると起動中のループを終了します（運用停止用）
- data/kill.flag
  - Monitoring の KillSwitch が条件を満たしたときに書き込む。ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動クリアされる（本番では推奨されない）
- data/execution.pid
  - ExecutionEngine が PID を書き込むために使用される既定パス
- logs/<app_name>.log
  - 各アプリ（execution, monitoring 等）の日次ローテーションログ（logs/ 配下）

---

## 実装上の注意点 / 運用メモ

- monitoring の DB 初期化は init_monitoring_db() により冪等に実行される（既存テーブルがあればスキップ、必要な ALTER も実施）
- ペーパートレードは本番 DB と完全分離するよう設計されている（settings.is_paper に基づく）
- OpenAI の呼び出しはリトライや JSON バリデーションを実装しており、API 失敗時には安全側（スコア 0.0 またはスキップ）で継続します
- process priority（優先度）は起動時に set_process_priority("high") で試みる（権限不足時は警告でスキップ）
- PyYAML が無い場合、validate_config の YAML 検証はスキップされる（警告）

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                — 環境変数/設定の解決ロジック（.env 自動ロード含む）
- config_setup.py          — 対話式 .env ウィザード
- validate_config.py       — 設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — Monitoring 起動スクリプト

- ai/
  - news_nlp.py            — ニュース NLP スコアリング（OpenAI）
  - regime_detector.py     — 市場レジーム判定（MA + マクロ NLP 合成）
- monitoring/
  - monitoring_db.py       — 監視用 SQLite のスキーマ & DB 操作
  - system_monitor.py      — CPU/メモリ/ディスク/データ鮮度監視
  - trade_monitor.py       — （省略）注文関連監視（ソース参照）
  - risk_monitor.py        — ドローダウン・ポジション上限監視
  - kill_switch.py         — kill.flag 書込ロジック
  - monitoring_engine.py   — 各 Monitor を束ねるエンジン
  - alert_manager.py       — （省略）通知管理
- execution/
  - execution_engine.py    — ExecutionEngine 本体（発注セッション管理）
  - broker_factory.py      — BrokerClient の生成（Mock/実ブローカー切替）
  - order_manager.py       — 注文管理
  - order_repository.py    — 発注ログ永続化
  - reconciler.py          — 約定整合処理
  - risk_manager.py        — 実行時リスク管理
- portfolio/
  - portfolio_builder.py   — 候補選定・重み計算
  - position_sizing.py     — 株数算出・資金制約
  - risk_adjustment.py     — セクターキャップ・レジーム乗数
- research/
  - factor_research.py     — ファクター計算（momentum/value/volatility）
  - feature_exploration.py — IC/統計サマリー
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成
- utils/
  - logging_setup.py       — ログ設定ユーティリティ
  - process_priority.py    — プロセス優先度 / CPU affinity ヘルパ
- data/ (実行時に生成されることを想定)
  - monitoring.db
  - paper_trading.db
  - kabusys.duckdb
  - execution.pid / kill.flag / stop_requested.flag
- logs/ (実行時に生成されることを想定)
  - execution.log, monitoring.log, ...

---

## よくある運用フロー（例）

1. リポジトリをクローンして仮想環境を作成
2. python -m kabusys.config_setup で .env を生成
3. python -m kabusys.validate_config で検証
4. 開発/テスト（ペーパートレード）:
   - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
5. 監視の起動:
   - python -m kabusys.run_monitoring
   - 必要に応じて MONITOR_POLL_INTERVAL を設定
6. Paper Trading の検証:
   - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD

---

## 最後に

この README はコードベース（src/kabusys/ 以下）から抽出した主要情報をまとめたものです。  
詳細な設計（PortfolioConstruction.md 等）や実運用のチェックリストは別途管理してください。質問や補足があれば教えてください。