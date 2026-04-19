# KabuSys

日本株自動売買システムのリポジトリ（軽量な構成管理・監視・ペーパートレード対応）。  
この README はリポジトリ内の主要スクリプト/モジュールに基づいて作成しています。

## プロジェクト概要
KabuSys は以下の責務を持つモジュール群で構成された自動売買フレームワークです。

- 注文実行エンジン（ExecutionEngine）／ブローカー抽象化（本番／ペーパートレード）
- 監視サブシステム（System / Trade / Risk のモニタリング、Kill Switch）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算、リスク調整）
- リサーチ（ファクター計算、特徴量探索）
- AI 統合（ニュース NLP によるセンチメント、レジーム判定）
- 運用支援ツール（.env ウィザード、設定検証、ペーパートレード検証レポート等）

設計上の特徴：
- 環境は .env / 環境変数で管理（自動ロード機能あり）
- ペーパートレードは本番 DB と分離（data/paper_trading.db 等）
- DuckDB を分析用に使用、SQLite をログ/監視/発注履歴用に使用
- ログはコンソール出力＋日次ローテーションファイルに保存

## 機能一覧
- 環境設定ウィザード（python -m kabusys.config_setup）
- 設定検証 CLI（python -m kabusys.validate_config）
- ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使い、ペーパートレード専用 DB に記録
- Monitoring 起動スクリプト（python -m kabusys.run_monitoring）
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）
  - 監視は常に本番用 sqlite_path を参照
- モニタリングエンジン（System / Trade / Risk の集約、Kill Switch 評価、Alert 発行）
- Kill Switch（data/kill.flag 書き込みで ExecutionEngine を安全に停止）
- ポートフォリオ構築ユーティリティ（候補選択・重み計算・ポジションサイズ計算・セクター調整）
- リサーチ機能（momentum/value/volatility 等のファクター計算、IC 計算など）
- AI モジュール：
  - ニュース NLP による銘柄別センチメントスコア算出（OpenAI 利用）
  - レジーム判定（ma200 + マクロセンチメントの合成）
- 運用ツール：
  - Paper Trading 検証レポート生成（python -m kabusys.tools.paper_verification_report）

## セットアップ手順（開発 / ローカル実行向け）
1. リポジトリをクローン
2. Python 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール（例）
   - pip install -r requirements.txt
   - 本リポジトリには requirements.txt が無い場合、少なくとも以下を入れてください:
     - duckdb, psutil, openai
     - 開発時は PyYAML を入れると設定検証で config/*.yaml のパースが行われます

4. .env の作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - あるいは手動で .env を作成。必須項目:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - （OpenAI を使う場合）OPENAI_API_KEY を設定

5. データディレクトリ
   - デフォルトの SQLite / DuckDB は `data/` 下に作成されます。必要に応じて .env でパスを変更してください。

6. （任意）ログディレクトリ
   - ログはデフォルトで `logs/` に出力されます。環境変数 LOG_DIR で変更可。

## 環境変数（主なもの）
- 必須:
  - JQUANTS_REFRESH_TOKEN — J-Quants API
  - KABU_API_PASSWORD — kabuステーション API
- 実行環境:
  - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- データベース:
  - DUCKDB_PATH — 分析用 DuckDB（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- AI:
  - OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector 実行に必要）
- ログ / 実行制御:
  - LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト INFO）
  - LOG_DIR — ログディレクトリ（デフォルト logs/）
  - PID_FILE_PATH — ExecutionEngine の PID ファイルパス（デフォルト data/execution.pid）
  - KILL_FLAG_PATH — Kill Switch 用フラグ（デフォルト data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（"1" で有効）
- 実行制御（監視）:
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
- ペーパートレード設定:
  - PAPER_FILL_MODE — instant / partial / never / reject（デフォルト "instant"）

## 使い方（主要コマンド・スクリプト）
- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も検出で終了コード 1

- ExecutionEngine 起動
  - python -m kabusys.run_execution
  - 動作:
    - 起動時にプロセス優先度を高に設定（set_process_priority("high")）
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い paper_sqlite_path に記録（本番 DB と分離）
    - 停止は data/stop_requested.flag（または kill.flag による外部停止判定）で検出

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - 動作:
    - プロセス優先度を高に設定
    - MONITOR_POLL_INTERVAL（秒）で SystemMonitor.check_once() を定期実行
    - stop フラグ（data/stop_requested.flag）でループ終了

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - 環境変数 PAPER_TRADING_SQLITE_PATH で DB 指定可、または --db オプション

- AI 関連（ニューススコア / レジーム判定）
  - 実行には OPENAI_API_KEY が必要です（費用とレート制限に注意）。
  - ニュース評価: kabusys.ai.score_news を利用するコード経由で呼ぶ（モジュール API）。
  - レジーム判定: kabusys.ai.regime_detector.score_regime を利用。

注意: OpenAI 呼び出しはネットワークや API レートの影響を受けます。失敗時はフォールバックやリトライが実装されていますが、運用時は API キー周りの管理とコストにご注意ください。

## Kill Switch / 停止フラグ
- Kill Switch は監視ロジック（RiskMonitor 等）によって評価され、必要なら `data/kill.flag` を書き込んで ExecutionEngine に停止シグナルを送ります。
- ExecutionEngine / Monitoring の起動スクリプトは stop フラグ（data/stop_requested.flag）や kill.flag をチェックして安全に停止します。
- KILL_FLAG_CLEAR_ON_START=1 を .env に設定すると起動時に kill.flag を自動クリアします（本番では推奨されません）。

## ログ
- setup_logging により、コンソール（stdout）と日次ローテーションファイル（logs/<app_name>.log）へ出力。
- ローテーションは日次、バックアップは 30 日分保持。

## ディレクトリ構成（主要ファイル）
以下はソースツリーの主要モジュールと役割の一覧（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py — 環境変数/.env の自動ロードと Settings クラス
  - config_setup.py — 対話式 .env ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - ai/
    - news_nlp.py — ニュースセンチメントの LLM 統合
    - regime_detector.py — 市場レジーム判定
  - monitoring/
    - monitoring_db.py — 監視ログの SQLite 永続化層
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — (発注ログ監視) ※詳細はコード参照
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — フラグファイルを書いて停止を送信
    - alert_manager.py — （アラート発行）※実装参照
  - execution/ — ExecutionEngine 本体・リスク管理・注文管理（実行ロジック）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 発注株数計算（単元丸め・リスク制限）
    - risk_adjustment.py — セクター制限・レジーム乗数
  - research/
    - factor_research.py — ファクター計算（momentum/value/volatility）
    - feature_exploration.py — IC・将来リターン・統計サマリー
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
  - data/ — デフォルト DB・フラグファイル置き場（実行時に使用）

※実際のリポジトリではさらに細かいファイルが存在します。上は主要な構成要素の概要です。

## 運用上の注意
- 本番（KABUSYS_ENV=live）では設定内容（APIキー・通知先・KILL_FLAG_CLEAR_ON_START 等）を慎重に管理してください。validate_config は本番向けの追加チェックを行います。
- データベースファイル（DuckDB/SQLite）はバックアップや保護を行ってください。
- OpenAI 統合機能は外部 API への依存・コスト・レート制限があるため、運用ルールを定めて利用してください。
- process_priority や CPU affinity の設定は OS 権限や環境によって失敗しますが、警告ログでスキップされます。

---

さらに詳細な使い方や API（モジュール関数）の参照はソースコード内の docstring / コメントを参照してください。必要なら README の拡張（インストール手順の詳細、Docker 化、systemd ユニット例など）も作成します — ご希望があれば教えてください。