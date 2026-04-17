# KabuSys (日本株自動売買システム) — README

このドキュメントはリポジトリ内のコードベース（src/kabusys）に基づく概要、機能、セットアップおよび基本的な使い方をまとめたものです。実行には環境変数の設定や外部ライブラリが必要になります。以下を順に参照してください。

注意: 本 README はソースコードを参照して作成しています。実行ファイル・運用ポリシーはお使いの環境に合わせて調整してください。

---

## プロジェクト概要

KabuSys は日本株の自動売買システムの主要コンポーネント群を提供する Python パッケージです。主な機能としては、取引執行エンジン、監視（モニタリング）、ポートフォリオ構築・ポジション計算、ファクター／リサーチ、AI（ニュースの NLP によるセンチメント評価）などがあります。

設計方針の要点:
- 本番用 DB と paper_trading（ペーパートレード）用 DB を明確に分離
- DuckDB を分析／リサーチ用に利用、SQLite を監視・ログ保存に利用
- .env による設定管理（自動ロード機能あり、無効化可能）
- OpenAI（gpt-4o-mini 等）を利用したニュース NLP / レジーム検出を実装（API キー必須）
- フェイルセーフ設計（API失敗時のフォールバック、ログ重視）

---

## 主な機能一覧

- Execution（発注）関連
  - 実行エンジンの起動スクリプト: run_execution.py
  - ブローカー抽象（paper_trading 時は MockBrokerClient を使用）
  - 注文管理・再整合（OrderManager / Reconciler / RiskManager）

- Monitoring（監視）
  - run_monitoring.py による定期ポーリング
  - system_monitor: CPU / メモリ / ディスク / プロセス存在確認 / データ鮮度チェック
  - trade_monitor: 滞留注文・約定異常価格の検出
  - risk_monitor: ドローダウンやポジション数の監視とアラート / kill switch 発動
  - AlertManager: LINE Messaging API による通知（任意）

- Portfolio（ポートフォリオ構築）
  - 候補選定、等金額/スコア加重、セクター上限、ポジションサイズ計算（単元丸め含む）

- Research（リサーチ）
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー

- AI（ニュース NLP / レジーム検出）
  - news_nlp.score_news: raw_news をまとめて OpenAI に投げ、銘柄別センチメントを ai_scores に保存
  - regime_detector.score_regime: ETF (1321) の MA 乖離とマクロニュースを合成して日次レジーム判定
  - OpenAI API を使用（OPENAI_API_KEY 必須）

- ユーティリティ
  - config_setup.py: 対話式 .env 作成ウィザード
  - validate_config.py: 環境設定検証 CLI
  - tools.paper_verification_report: ペーパートレード検証レポート生成

---

## 必要な前提依存パッケージ（例）

以下はソースから参照される主なライブラリ例です。実際の requirements.txt が存在する場合はそちらを優先してください。

- Python 3.8+
- psutil
- duckdb
- openai
- requests
- PyYAML（config YAML 検証のために任意）

インストール例:
- pip install psutil duckdb openai requests pyyaml

---

## セットアップ手順

1. リポジトリをクローン / 展開
2. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install psutil duckdb openai requests pyyaml
4. .env を作成
   - 対話式ウィザード: python -m kabusys.config_setup
   - もしくは .env.example を参考に作成し、必要な環境変数を設定
   - 主要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - OPENAI_API_KEY（AI 機能を利用する場合）
5. 設定の検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります
6. data ディレクトリ作成（必要に応じて自動生成されますが、手動で準備しても可）
   - デフォルトの DB/フラグファイルパス:
     - DuckDB: data/kabusys.duckdb
     - Monitoring SQLite: data/monitoring.db
     - Paper Trading SQLite: data/paper_trading.db
     - PID ファイル: data/execution.pid
     - Kill flag: data/kill.flag
     - Stop request flag: data/stop_requested.flag

.env の自動読み込み:
- パッケージ初期化時にプロジェクトルート（.git または pyproject.toml を探索）を見つけると `.env` と `.env.local` を自動で読み込みます。
- 自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

## 使い方

以下は主要なコマンド・使い方の抜粋です。

- 実行エンジン（ExecutionEngine）起動
  - python -m kabusys.run_execution
  - 補足:
    - KABUSYS_ENV が `paper_trading` の場合、MockBrokerClient を使用し paper_trading 用 DB（data/paper_trading.db）に記録します。
    - 起動時に data/stop_requested.flag が存在すると起動を中止します。
    - 実行中に同フラグが作成されるとエンジンは停止します。

- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - 補足:
    - デフォルトのポーリング間隔は 60 秒。環境変数 MONITOR_POLL_INTERVAL で上書き可能（秒）。
    - 監視では本番の sqlite_path（Settings.sqlite_path）を環境に関係なく使用します。
    - 停止は data/stop_requested.flag を作成することで行えます（ファイルの検出でループを抜けます）。

- .env を対話式に作成・更新
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - オプション --strict で警告もエラー扱いにする

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    - --db PATH、または環境変数 PAPER_TRADING_SQLITE_PATH を使用

- AI 機能（プログラムから呼び出す）
  - news NLP（銘柄別センチメント）:
    - from kabusys.ai import score_news
    - score_news(conn, target_date, api_key=...)  # DuckDB 接続が必要
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key=...)

- モニタリングのテスト用ランナー（プログラムから）
  - MonitoringEngine を組み立てて run_once / run を呼べます（ユニットテストや手動チェック用）。

注意点（運用上の取り決め）:
- 本番環境（KABUSYS_ENV=live）では kill flag の自動クリア（KILL_FLAG_CLEAR_ON_START=1）は危険です。デフォルトは 0。
- OpenAI API を利用する機能は API キーの料金とレート制限に注意してください。
- Process priority の設定: 起動時に set_process_priority("high") が試行されます。権限不足等で設定できない場合は警告に留まります。

---

## 主要な設定（Settings）とデフォルト値

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
- SQLITE_PATH: data/monitoring.db（監視ログ）
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用）
- PID_FILE_PATH: data/execution.pid
- KILL_FLAG_PATH: data/kill.flag
- KILL_FLAG_CLEAR_ON_START: 0（既定）
- MONITOR_POLL_INTERVAL: 60（run_monitoring のポーリング間隔を秒で上書き可能）
- PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の約定挙動）

.env の簡易例:
- KABUSYS_ENV=development
- JQUANTS_REFRESH_TOKEN=your_token_here
- KABU_API_PASSWORD=your_password_here
- OPENAI_API_KEY=sk-...
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db

---

## ファイル / ディレクトリ構成（概要）

以下は src/kabusys 以下の主要なファイルとその役割の一覧です（抜粋・要約）。

- __init__.py
  - パッケージ定義、バージョン

- run_execution.py
  - ExecutionEngine の起動スクリプト（ブローカー生成・依存組み立て・スレッド起動・停止フラグ監視）

- run_monitoring.py
  - SystemMonitor をポーリングする起動スクリプト（MONITOR_POLL_INTERVAL による間隔指定）

- config.py
  - 環境変数の読み込み / Settings クラス（.env 自動ロード機能、各種設定のプロパティ）

- config_setup.py
  - .env を対話式に作成・更新するウィザード

- validate_config.py
  - 環境設定と config/*.yaml の存在・簡易検証 CLI

- tools/
  - paper_verification_report.py: Paper Trading 検証レポートを生成

- portfolio/
  - portfolio_builder.py: 候補選定、重み計算（等配分／スコア加重）
  - position_sizing.py: 発注株数計算・単元丸め・aggregate cap
  - risk_adjustment.py: セクター上限、レジーム乗数

- monitoring/
  - monitoring_db.py: SQLite ベースの監視ログ層（テーブル生成・読み書きユーティリティ）
  - system_monitor.py: システム状態・データ鮮度監視
  - trade_monitor.py: 注文滞留・約定異常監視
  - risk_monitor.py: ドローダウン・ポジション上限監視
  - kill_switch.py: kill.flag 書き込みによる ExecutionEngine 停止判定
  - alert_manager.py: LINE push 通知（クールダウン管理）
  - monitoring_engine.py: 各 Monitor を束ねる実行ループ

- ai/
  - news_nlp.py: raw_news を OpenAI に投げて銘柄ごとの ai_score を生成して保存
  - regime_detector.py: ETF MA とマクロニュースを用いた日次レジーム判定

- research/
  - factor_research.py: モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB 利用）
  - feature_exploration.py: 将来リターン計算、IC、統計サマリー

- utils/
  - process_priority.py: プロセス優先度・CPU affinity 設定ユーティリティ

（その他、execution や data 周りに多数のサブモジュールがある想定）

---

## 運用上の補足・注意

- kill.flag / stop_requested.flag:
  - kill.flag: KillSwitch により作成される停止フラグ（ExecutionEngine に対する停止命令トリガー）。Settings.kill_flag_path で指定可能。
  - stop_requested.flag: run_execution/run_monitoring が終了するために外部から置くファイル（data/stop_requested.flag が参照されます）。
- DB マイグレーション:
  - init_monitoring_db が冪等にテーブル・カラムを追加します（既存 DB を壊さないよう注意）。
- 権限やプラットフォーム差:
  - set_process_priority は OS による違い（Windows vs POSIX）を吸収しますが、権限不足では設定が失敗する場合があります。
- テスト:
  - API 呼び出しなどは関数単位でモックできるよう設計されています（example: news_nlp._call_openai_api を unittest.mock.patch で差し替える）。

---

## よく使うコマンドまとめ

- .env 作成（ウィザード）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config [--strict]
- 実行エンジン起動
  - python -m kabusys.run_execution
- 監視起動
  - python -m kabusys.run_monitoring
- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
- AI 機能（スクリプトから呼び出し）
  - Python スクリプト内で kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime を呼ぶ（DuckDB 接続が必要）

---

この README はコードベースの主な箇所をカバーしていますが、実運用時は各モジュール内ドキュメント（関数 docstring）や config/*.yaml（存在する場合）を参照してください。追加の説明やデプロイ手順が必要であれば、その用途（例: systemd サービス化、Docker 化、CI/CD）を教えてください。必要に応じて README を拡張します。