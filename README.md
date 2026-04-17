# KabuSys

日本株向け自動売買システム（ライブラリ / 実行スクリプト群）

この README はコードベース（src/kabusys）を対象に、概要、主要機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買・研究・監視を行うためのモジュール群です。  
主な機能はトレーディング実行（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、ファクター計算、研究用ユーティリティ、OpenAI を用いたニュース NLP / 市場レジーム判定などを含みます。  
設計方針として、次の点を重視しています：

- 本番（live）／ペーパートレード（paper_trading）を環境変数で切替
- DB は DuckDB（分析） と SQLite（監視・発注ログ）を併用
- .env による環境変数管理をサポート（config_setup によるウィザード）
- フェイルセーフ（外部 API 失敗時はフォールバックして継続）
- ルックアヘッドバイアス対策（date.today() を直接参照しない設計）

---

## 機能一覧（主要）

- 実行エンジン（ExecutionEngine 起動スクリプト）
  - 本番 / ペーパートレード切替（paper_trading は MockBroker を使用し DB を分離）
  - リスク管理、注文管理、調整（reconciler）を含む
- 監視（Monitoring）
  - SystemMonitor: CPU/メモリ/ディスク/プロセス PID・データ鮮度監視
  - TradeMonitor: 滞留注文・約定価格異常検出
  - RiskMonitor: ドローダウン・保有上限監視、kill switch 連携
  - MonitoringEngine / run_monitoring スクリプトで定期ポーリング
- ポートフォリオ構築
  - 候補選定（select_candidates）、重み計算（等金額／スコア）、
    セクターキャップ適用、レジーム乗数、株数決定（ロット調整・aggregate cap）
- リサーチ / ファクター計算
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を利用）
  - 将来リターン計算、IC（スピアマン）計算、統計サマリー
- AI（OpenAI）連携
  - news_nlp: ニュース記事の銘柄別センチメント（ai_scores）生成
  - regime_detector: マクロ + ETF MA200 乖離に基づく日次レジーム判定
  - OpenAI API の呼び出しはリトライ・JSON 検証・スコアクリップ等の安全処理あり
- ツール
  - config_setup: 対話式 .env 作成ウィザード
  - validate_config: 起動前の設定検証 CLI
  - paper_verification_report: ペーパートレード結果検証レポート生成

---

## 前提条件

- Python 3.10 以上（型ヒントの union 記法や最新ライブラリを想定）
- 必要な Python パッケージ（代表例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config の検証にオプションで使用）
- OS: Linux / macOS / Windows（process priority の実装差異あり）

（requirements.txt がある場合はそれを使用してください。無い場合は上記を個別に pip install してください）

例:
pip install duckdb psutil openai PyYAML

---

## セットアップ手順

1. リポジトリをクローン / 展開する
2. Python 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (Windows は .venv\Scripts\activate)
3. 依存ライブラリをインストール
   - pip install -r requirements.txt  （requirements.txt があれば）
   - または: pip install duckdb psutil openai PyYAML
4. 初期環境 (.env) の作成
   - python -m kabusys.config_setup
     - 対話的に .env を生成します（.env は絶対に VCS にコミットしないでください）
5. 設定検証（任意）
   - python -m kabusys.validate_config
   - 本番前は --strict を付けて警告も失敗扱いにできます
6. DB・data ディレクトリの用意
   - デフォルトのパスは data/ 以下にあります（DuckDB: data/kabusys.duckdb、SQLite: data/monitoring.db 等）
   - 必要に応じて .env で DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH を設定

---

## 環境変数と重要設定

自動ロード:
- パッケージはプロジェクトルートの .env および .env.local を自動で読み込みます（OS 環境変数より優先しない）。
- 自動読み込みを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

重要な環境変数（抜粋）:
- JQUANTS_REFRESH_TOKEN （必須）
- KABU_API_PASSWORD （必須）
- KABUSYS_ENV : development | paper_trading | live （デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- OPENAI_API_KEY（news_nlp / regime_detector 利用時に必要）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START（本番注意。live で 1 にすると起動時に kill.flag を自動クリア）

---

## 使い方（メインスクリプト）

- 環境設定ウィザード
  - python -m kabusys.config_setup
    - .env を対話的に作成 / 更新します

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動（Execution）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、data/paper_trading.db に記録（本番 DB と分離）
    - 起動時に data/stop_requested.flag が既に存在する場合は起動せず終了
    - エンジンはスレッドで run_session を実行。停止は stop フラグ（stop_requested.flag）で可能
    - PID ファイル: data/execution.pid を利用（SystemMonitor がプロセス生存を確認）

- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - オプション（環境変数）:
    - MONITOR_POLL_INTERVAL: ポーリング間隔（秒、デフォルト 60）
  - 挙動:
    - 監視は常に本番用の sqlite_path を使用（環境に依存せず監視 DB は production path を参照）
    - stop_requested.flag を検出するとループを終了
    - SystemMonitor が data 鮮度、プロセス PID、システム資源を記録し、MonitoringDB（SQLite）へ書き込む

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD --to YYYY-MM-DD
    - --db PATH （PAPER_TRADING_SQLITE_PATH 環境変数で指定することも可）
  - 出力: 稼働率・注文成功率・レイテンシ等のサマリと PASS/FAIL 判定

---

## Kill / Stop フラグについて

- 実行停止・安全装置:
  - data/stop_requested.flag：run_execution / run_monitoring スクリプトがポーリングして検出する停止フラグ（ここに任意のファイルを作ると停止処理が行われます）
  - data/kill.flag：KillSwitch が書き込むファイルで ExecutionEngine に対する強制停止指令（リスク条件等で生成）
  - PID ファイル: data/execution.pid（SystemMonitor が存在確認）

注意:
- 本番環境では KILL_FLAG_CLEAR_ON_START を 1 にする設定は危険（自動で kill.flag をクリアしてしまうため）。live 環境では 0 推奨。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py
  - .env 自動読み込み、Settings クラス（環境変数アクセス）
- config_setup.py
  - .env の対話的作成ウィザード
- validate_config.py
  - 起動前検証 CLI
- run_execution.py
  - ExecutionEngine 起動スクリプト（paper_trading での分離対応）
- run_monitoring.py
  - SystemMonitor をポーリングする起動スクリプト
- monitoring/
  - monitoring_db.py — SQLite テーブル作成 / DB 操作ラッパー（MonitoringDB）
  - system_monitor.py — CPU/メモリ/ディスク/プロセス/データ鮮度監視
  - trade_monitor.py — 滞留注文・約定異常の検出
  - risk_monitor.py — ドローダウン / ポジション数監視
  - monitoring_engine.py — 複数モニタの束ね（テスト用 run_once / 常時 run）
  - kill_switch.py — kill.flag の生成 / 管理
  - alert_manager.py — （実装ファイルあり／アラート送信ロジック）
- execution/ (発注関連、Engine, OrderRepository 等)
  - order_manager.py, order_repository.py, execution_engine.py, broker_factory.py, など
- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 株数決定・資金制約、ロット丸め
  - risk_adjustment.py — セクターキャップ、レジーム乗数
- research/
  - factor_research.py — mom/vol/value 等のファクター計算（DuckDB）
  - feature_exploration.py — 将来リターン / IC / 統計サマリ
- ai/
  - news_nlp.py — ニュース記事→銘柄別センチメント（OpenAI）
  - regime_detector.py — ETF MA200 + マクロセンチメントを合成してレジーム判定
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート
- utils/
  - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ

（上記は主要ファイルの抜粋です。詳細な実装は各ファイルを参照してください）

---

## 注意事項 / 運用上のポイント

- .env は機密情報（API トークン・パスワード）を含むため絶対にリポジトリにコミットしないでください。
- OpenAI 利用時は OPENAI_API_KEY を設定してください。API 呼び出しはリトライとパース検証を行いますが、レート制限・課金に注意してください。
- paper_trading モードは本番 DB と完全に分離することを意図しているため、PAPER_TRADING_SQLITE_PATH を適切に設定してください。
- 本番環境（KABUSYS_ENV=live）では kill_flag や KILL_FLAG_CLEAR_ON_START の設定に細心の注意を払ってください。validate_config の警告を必ず確認してください。
- process priority / affinity の設定は OS に依存します（psutil の権限や実装差により失敗することがあります）。失敗した場合はログ警告でスキップされます。

---

## 追加情報 / 開発時ヒント

- テスト用に MonitoringEngine.run_once() を利用して個別 monitor の動作確認が可能です。
- DuckDB を使ったファクター計算は SQL を駆使して高速に集計します。テーブル名（prices_daily / raw_financials 等）に依存しています。
- AI 関連処理（news_nlp, regime_detector）は外部 API を使うため、ユニットテストでは _call_openai_api をモックしてください（モジュール内に注記あり）。

---

必要があれば、この README をベースに「デプロイ手順」「運用マニュアル（監視アラート設定や STOP/RECOVER 操作手順）」「詳細な API 仕様（内部モジュールの関数ドキュメント）」を追加で作成します。どのドキュメントを優先しますか？