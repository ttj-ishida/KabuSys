# KabuSys

日本株自動売買システム（ライブラリ兼実行スクリプト群）

このリポジトリは、シグナル生成・ポートフォリオ構築・発注（ExecutionEngine）・監視（Monitoring）・研究/分析・AI（ニュースセンチメント/レジーム検出）などを含む、自動売買システムの主要コンポーネントを提供します。

---

## プロジェクト概要

- DuckDB を用いた時系列データ・財務データの分析／リサーチ機能
- 発注エンジン（ExecutionEngine）とブローカークライアント抽象化（実運用 / ペーパートレードを分離）
- 監視サブシステム（SystemMonitor / TradeMonitor / RiskMonitor）と Kill Switch（フラグファイルによる安全停止）
- ニュースの LLM（OpenAI）によるセンチメント評価と市場レジーム判定
- ペーパートレード検証用レポート生成ツール

設計方針として「本番 DB とペーパートレード DB の分離」「ルックアヘッドバイアスの排除」「フェイルセーフ（API失敗時のフォールバック）」などが守られています。

---

## 主な機能一覧

- 実行（発注）関連
  - ExecutionEngine 起動スクリプト（`run_execution.py`）
  - ブローカー実装を環境により切替（本番 / ペーパートレード）
  - OrderRepository / OrderManager / RiskManager / Reconciler 等の発注周りコンポーネント

- 監視関連
  - SystemMonitor：CPU/メモリ/Disk/プロセス状態、データ鮮度監視
  - TradeMonitor：滞留注文・約定価格異常検知
  - RiskMonitor：ドローダウン・ポジション上限監視
  - MonitoringEngine：定期ポーリング、アラート発行、Kill Switch 評価
  - SQLite ベースの監視ログ永続化（`monitoring_db.py`）

- ポートフォリオ構築（純粋関数群）
  - 候補選定、等配分/スコア配分、ポジションサイジング（単元丸め）、セクター制約、レジーム乗数

- 研究・特徴量（research）
  - モメンタム／バリュー／ボラティリティ等のファクター計算（DuckDB SQL）
  - 将来リターン計算、IC（Information Coefficient）等の評価ユーティリティ

- AI（OpenAI）
  - ニュース NLP：銘柄毎のセンチメントを LLM で算出して DB に格納（`ai/news_nlp.py`）
  - レジーム判定：ETF の MA とマクロニュースの LLM 評価を合成（`ai/regime_detector.py`）

- ツール
  - ペーパートレード検証レポート生成（`tools/paper_verification_report.py`）
  - 対話式 .env 作成ウィザード（`config_setup.py`）
  - 設定検証 CLI（`validate_config.py`）

---

## 前提条件

- Python 3.9+
- 必要パッケージ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML 検証を行う場合）
- SQLite は Python 組込みの sqlite3 を使用

（実際の requirements.txt はプロジェクトに応じて用意してください。最低限上記パッケージはインストールしてください）

---

## インストールとセットアップ

1. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML

3. 環境変数（.env）を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは `.env` を手動で作成して以下を設定:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (ペーパートレード専用 DB、デフォルト: data/paper_trading.db)
     - OPENAI_API_KEY (AI 機能を使う場合)
     - PAPER_FILL_MODE (paper_trading 時の挙動: instant | partial | never | reject) — デフォルト: instant
     - その他: LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID / LOG_LEVEL / KILL_FLAG_CLEAR_ON_START など

4. 設定検証（任意）
   - python -m kabusys.validate_config
   - 警告も失敗扱いにする場合: python -m kabusys.validate_config --strict

注意: デフォルトではモジュール起動時にプロジェクトルートの `.env` / `.env.local` を自動ロードします。自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 実行方法（使い方）

### 1) 実行エンジン（ExecutionEngine）
- 起動:
  - python -m kabusys.run_execution
- 挙動:
  - KABUSYS_ENV が `paper_trading` の場合、MockBrokerClient を使用し、ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録します（本番 DB とは完全分離）。
  - 起動時に data/stop_requested.flag が存在すると起動をスキップします。
  - 実行中に stop flag が作成されると Engine に停止命令を送ります（フラグファイル方式）。
  - 実行時に data/execution.pid に PID を書きます。

### 2) 監視（Monitoring）
- 起動:
  - python -m kabusys.run_monitoring
- 挙動:
  - SystemMonitor を定期ポーリングして監視ログを SQLite（Settings.sqlite_path）に記録します。
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します（設計上の分離）。
  - 停止フラグ（data/stop_requested.flag）を検出するとループを終了します。

### 3) ペーパートレード検証レポート
- 生成:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

### 4) AI 機能（OpenAI）
- ニューススコア算出:
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - OPENAI_API_KEY または api_key 引数が必要
- レジーム判定:
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
- 注意:
  - API 呼び出しはリトライ/バックオフ・レスポンス検証などのフェイルセーフ処理あり
  - API キーが未設定の場合は例外が送出されます

---

## 主要設定／環境変数（抜粋）

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 運用
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
  - OPENAI_API_KEY: OpenAI を利用する場合に必要

- データベース
  - DUCKDB_PATH (例: data/kabusys.duckdb)
  - SQLITE_PATH (監視 DB, 例: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (ペーパートレード用 DB)

- その他
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60。1 未満または不正値は無視され 60 にフォールバック）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアする (0/1)
  - PID_FILE_PATH / KILL_FLAG_PATH のデフォルトは data 以下

---

## ディレクトリ構成

（主要ファイル・パッケージのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py            — 環境変数 / Settings 管理（.env 自動読み込み機能）
  - config_setup.py      — 対話式 .env 作成ウィザード
  - validate_config.py   — 起動前の設定検証 CLI
  - run_execution.py     — ExecutionEngine 起動スクリプト
  - run_monitoring.py    — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py        — ニュースセンチメント（OpenAI）
    - regime_detector.py — 市場レジーム判定（OpenAI + MA）
  - monitoring/
    - monitoring_db.py   — SQLite スキーマ / 永続化
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py   — （アラート送信の抽象。コード末尾に未表示部分あり）
  - execution/            — 発注エンジン周り（OrderRepository 等）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - process_priority.py — プロセス優先度・CPU affinity 設定

---

## 主要モジュールの簡単な説明

- config.py
  - .env/.env.local を自動ロード（必要に応じて無効化可）
  - Settings クラスでアプリ設定をプロパティとして提供

- run_execution.py
  - ExecutionEngine を組み立てて起動する CLI スクリプト
  - paper_trading の場合は専用 DB に書き込む・MockBroker を使用

- run_monitoring.py
  - SystemMonitor のポーリングループ（MONITOR_POLL_INTERVAL）

- monitoring/monitoring_db.py
  - 監視用 SQLite のスキーマ作成と DB 操作用の軽量ラッパー（MonitoringDB）

- ai/news_nlp.py / ai/regime_detector.py
  - OpenAI を用いたテキスト評価と DB への書き込み。API エラー時は安全側にフォールバック。

- portfolio/**
  - 候補選定、重み算出、ポジションサイズ決定など、純粋関数群で実装（副作用なし）

---

## よくある注意点 / トラブルシューティング

- MONITOR_POLL_INTERVAL が 0 や負の値だと無効値扱いされデフォルト 60 秒にフォールバックします。
- Monitoring は KABUSYS_ENV にかかわらず Settings.sqlite_path（本番の監視 DB）を使用します。ペーパートレードの監視も本番 DB を見る設計になっている点に留意してください。
- ペーパートレードを本番 DB と混同しないよう、PAPER_TRADING_SQLITE_PATH を設定して下さい（run_execution が paper_trading のときのみ使用）。
- OpenAI を利用する機能（news_nlp / regime_detector）は必ず API キーが必要です。API 呼び出しはレート制限やサーバエラーに対してリトライ処理がありますが、上限超過するとスキップされます。
- Kill Switch（data/kill.flag）や停止フラグ（data/stop_requested.flag）はフラグファイル方式でプロセス間同期を行います。起動前にフラグの有無を確認してください。
- .env は絶対に Git にコミットしないでください（config_setup でも警告あり）。

---

## 開発・拡張メモ

- DuckDB クエリは大量データ分析向けに設計されているため、prices_daily / raw_financials 等のテーブル構造に合わせてデータ投入が必要です。
- AI モジュールのテストは外部 API 呼び出しをモックできるよう設計されています（内部の呼び出し関数を patch して差し替え可能）。
- position_sizing や risk_adjustment は将来的に銘柄単位の lot_size 等で拡張できるようコメントで留意されています。

---

README は以上です。必要であれば、実行例、より詳細な環境変数一覧、要件ファイル（requirements.txt）の雛形、または各モジュールの API ドキュメント（関数シグネチャと用途）を追加で作成します。どれが必要か教えてください。