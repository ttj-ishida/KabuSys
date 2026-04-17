# KabuSys

日本株向け自動売買・リサーチ基盤ライブラリ（モジュール群）です。本リポジトリは取引実行エンジン、監視、ポートフォリオ構築、ファクター計算、AI を用いたニュースセンチメント評価などの機能を提供します。

以下はこのコードベースの概要・セットアップ・使い方・ディレクトリ構成の簡易 README です。

## プロジェクト概要
- 自動売買 ExecutionEngine（実取引・ペーパートレード対応）
- 監視コンポーネント（System / Trade / Risk Monitor）と Kill Switch
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ決定・セクター制限）
- リサーチ（ファクター計算、特徴量探索、将来リターン・IC 計算）
- AI（OpenAI）を用いたニュースセンチメント評価、レジーム判定
- Paper Trading 用の検証レポート生成ツール

設計方針の一例：
- DuckDB / SQLite をデータストアとして利用（分析用と監視用で分離）
- 実行環境は環境変数で切替（development / paper_trading / live）
- LLM 呼び出しは冗長性（リトライ等）と結果検証を備え、API キーが未設定では安全にフォールバックする

## 主な機能一覧
- 実行系
  - ExecutionEngine（発注・リスク管理・Reconciler 等）
  - BrokerClientFactory（paper_trading 時は MockBrokerClient を利用）
- 監視系
  - SystemMonitor：CPU/メモリ/Disk、プロセス PID、データ鮮度確認
  - TradeMonitor：滞留注文・約定異常検出
  - RiskMonitor：ドローダウン監視・ポジション数上限監視
  - MonitoringEngine：上記をまとめてポーリング、AlertManager 経由で LINE 通知、KillSwitch で ExecutionEngine 停止
  - monitoring_db：監視ログ（SQLite）スキーマと読み書きユーティリティ
- ポートフォリオ
  - 銘柄候補選定、等重/スコア重み、リスク調整（セクター上限・レジーム乗数）、ポジションサイズ計算（単元丸め・aggregate cap）
- リサーチ
  - ファクター計算（Momentum、Value、Volatility、Liquidity）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー
- AI
  - ニュース NLP（OpenAI）による銘柄別センチメント算出（ai_scores への書き込み）
  - 市場レジーム判定（ETF MA とマクロセンチメントの合成）
- ツール
  - 環境設定ウィザード（.env 作成）: kabusys.config_setup
  - 設定検証 CLI: kabusys.validate_config
  - Paper Trading 検証レポート生成: kabusys.tools.paper_verification_report

## セットアップ手順（開発・実行前の準備）
1. Python 環境を用意する
   - 推奨: Python 3.9+（利用する依存ライブラリに依存します）
2. 依存ライブラリをインストールする（例）
   - requirements.txt がある場合:
     - pip install -r requirements.txt
   - 必要な主要パッケージ（例）:
     - duckdb, psutil, requests, openai
     - 開発・検証で YAML 検証を行う場合: PyYAML
3. プロジェクトルートに移動して `.env` を用意する
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - もしくは `.env.example` を参考に手動で作成
4. 設定検証（任意）
   - python -m kabusys.validate_config
   - 警告もエラー扱いにする場合: python -m kabusys.validate_config --strict
5. データディレクトリと DB の初期化
   - 多くのスクリプトは起動時に必要なディレクトリ/テーブルを自動作成します（例: data/ 配下）
   - デフォルト DB パス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db

## 環境変数（主要なもの）
（.env に設定する主要キーとデフォルト / 備考）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (news/regime の LLM 呼び出しに必要)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
- PAPER_FILL_MODE (paper_trading の成行/一部約定等の挙動: instant|partial|never|reject)
- KABUSYS_ENV (development | paper_trading | live) — 実行モード
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID （アラート送信に使用）
- KILL_FLAG_PATH (デフォルト: data/kill.flag)
- KILL_FLAG_CLEAR_ON_START (0/1) — Execution 起動時に kill.flag を自動クリアするか

（設定検証 CLI がさらに詳細チェックを行います）

## 使い方（主要スクリプト・モジュール）
- 環境セットアップ（.env の対話式生成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 監視ループ起動（常駐プロセス）
  - python -m kabusys.run_monitoring
  - 環境変数: MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き（デフォルト 60）
  - 監視は本番用の sqlite_path を常に使用します（KABUSYS_ENV に依存せず）

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を指定すると MockBroker を使い paper_trading DB（デフォルト: data/paper_trading.db）へ記録します
  - 実行中は data/execution.pid に PID を書きます
  - 停止は data/stop_requested.flag / data/kill.flag などのフラグにより制御

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定: --db PATH（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI スコアリング / レジーム判定（プログラムから呼び出す）
  - kabusys.ai.score_news（DuckDB 接続, target_date, api_key）
  - kabusys.ai.regime_detector.score_regime（DuckDB 接続, target_date, api_key）
  - OpenAI API キーが必要。未設定の場合は ValueError（呼び出し側でキャッチしてフォールバック運用を推奨）

## 注意点 / 運用上のポイント
- Paper trading と production DB は分離しています（paper_trading 用 SQLite を使用）。
- MONITOR は常に production sqlite_path を参照する設計です（環境に依らず監視ログは統一）。
- Kill Switch（data/kill.flag）を用いて Execution を安全に停止できます。KillSwitch はドローダウン・ポジション過多等で自動書き込みする場合があります。
- OpenAI 呼び出しはリトライ・レスポンス検証を備えますが、API キーの漏洩に注意し .env を絶対にコミットしないでください。
- `validate_config` は環境変数・DBパス・config/*.yaml の存在等を事前チェックします（PyYAML 未インストール時は YAML 検証をスキップして警告を出します）。

## ディレクトリ構成（主要ファイル）
（リポジトリ内の src/kabusys 配下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数・設定管理（自動 .env ロード）
  - config_setup.py              — .env 対話式ウィザード
  - validate_config.py           — 設定検証 CLI
  - run_monitoring.py            — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - monitoring/
    - monitoring_db.py           — SQLite スキーマ & DB ラッパ
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - alert_manager.py
    - kill_switch.py
  - execution/                    — （発注エンジン・OrderManager 等、実装ファイル群は本ツリーに存在）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - execution_engine.py
    - broker_factory.py
    - ...（他）
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
  - utils/
    - process_priority.py

（上記は抜粋です。実際のリポジトリにはさらに細かなモジュールが含まれます）

## 簡易コマンドまとめ
- .env 作成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- 監視起動:
  - python -m kabusys.run_monitoring
  - 環境変数で: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- 実行エンジン起動:
  - python -m kabusys.run_execution
  - ペーパートレード: KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

## トラブルシューティング（よくある問題）
- YAML 検証でエラー: PyYAML が必要です。pip install pyyaml
- OpenAI 呼び出しでエラー: OPENAI_API_KEY を .env に設定してください。API 呼び出しはネットワーク・レート制限の影響を受けます。
- DB が作られない / パスがない: .env の DUCKDB_PATH / SQLITE_PATH を確認し、親ディレクトリが存在するか確認してください（validate_config で警告が出ます）。
- プロセス優先度設定に失敗する警告: 特権の必要な操作は環境により失敗する場合があり、その場合は警告を出してスキップします（問題が無ければ無視可）。

---

この README はコードベースの主要点をまとめたものです。具体的な挙動・詳細パラメータは各モジュールのドキュメンテーション（ソースコードの docstring）を参照してください。必要であれば README に追加したいセクション（例: AP I 使用例、より詳細な運用手順、デプロイ案内など）を教えてください。