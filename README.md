# KabuSys

日本株向け自動売買システムのコアライブラリ群。  
このリポジトリにはトレーディング実行・監視・リサーチ・ポートフォリオ構築・AI（ニュース NLP / レジーム判定）などのモジュールが含まれます。

## 概要
KabuSys は次の役割を持つモジュール群で構成されています。

- Execution：発注ロジック、リスク管理、オーダー管理、ブローカー抽象化
- Monitoring：プロセス・システム状態・注文状況・リスク監視、Kill Switch（停止フラグ）
- Research：DuckDB を用いたファクター計算・特徴量解析
- Portfolio：銘柄選定・重み計算・ポジションサイジング・セクター制約
- AI：ニュースセンチメント（OpenAI）や市場レジーム判定
- Tools：ペーパートレード検証レポート等のユーティリティスクリプト
- Utils：ロギング設定・プロセス優先度等のユーティリティ

設計上の特徴：
- DuckDB / SQLite をデータ層として利用（ローカル DB）
- .env による設定管理（config_setup による対話式作成）
- Paper Trading（KABUSYS_ENV=paper_trading）時は本番 DB と完全分離
- OpenAI を使う AI モジュールは API キー必須（フェイルセーフあり）

---

## 主な機能一覧
- 実行エンジン起動スクリプト（run_execution.py）
  - Paper Trading 時は MockBroker を使用し data/paper_trading.db に記録
  - 停止フラグ / pid ファイル管理
- 監視ループ起動スクリプト（run_monitoring.py）
  - システムリソース・データ鮮度・プロセス稼働を定期チェック
  - MONITOR_POLL_INTERVAL でポーリング間隔を変更可能
- 設定ウィザード（config_setup.py）
  - .env の対話的作成・更新を支援
- 設定検証 CLI（validate_config.py）
  - 必須環境変数や config/*.yaml の存在・パスの検証
- Paper Trading 検証レポート（tools/paper_verification_report.py）
  - 稼働率、注文成功率、レイテンシなどを集計・判定
- AI モジュール
  - news_nlp.score_news: OpenAI を用いたニュースの銘柄別センチメント評価
  - regime_detector.score_regime: マクロ + ETF MA200 乖離を合成してレジーム判定
- Portfolio モジュール
  - 銘柄選定・等重/スコア重み・リスクベースの株数算出・セクターキャップ適用
- Utils
  - 統一ログ設定（ログのコンソール出力＋日次ローテーション）
  - プロセス優先度 / CPU affinity の設定

---

## セットアップ手順（ローカル開発用）
前提
- Python 3.10 以上（型記法や union 型を使用しているため）
- Git

1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. 仮想環境（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - 代表的な依存パッケージ:
     - duckdb
     - psutil
     - openai
     - PyYAML（config の検証を行う場合）
   - 例:
     - pip install duckdb psutil openai PyYAML

   （requirements.txt がある場合は pip install -r requirements.txt を使用）

4. .env を用意（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - ウィザードは .env を作成／更新します。
   - 自動ロードはデフォルトで有効（プロジェクトルートの .env / .env.local を読み込み）。
     自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

5. 設定検証
   - python -m kabusys.validate_config
   - 警告もエラー扱いにしたい場合は --strict を付ける

6. ディレクトリ準備
   - デフォルトで使用するディレクトリ:
     - data/（SQLite や PID/フラグファイル用）
     - logs/（ログファイル）
   - ログディレクトリは LOG_DIR 環境変数で変更可能

---

## 環境変数（主要）
多くは .env で管理されます。主要なもの：

必須
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

任意／デフォルトあり
- KABUSYS_ENV — 実行環境（development / paper_trading / live）。デフォルト: development
  - paper_trading の場合は発注に MockBroker を使い data/paper_trading.db に記録
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパー用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）。デフォルト: INFO
- OPENAI_API_KEY — OpenAI を利用する機能で使用
- PAPER_FILL_MODE — paper_trading の注文約定モード（instant / partial / never / reject）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒。デフォルト 60）

監視 / 制御用
- PID_FILE_PATH — 実行エンジンの PID ファイル（デフォルト data/execution.pid）
- KILL_FLAG_PATH — kill.flag のパス（デフォルト data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1。デフォルト 0）

その他
- LOG_DIR — ログファイル保存先（デフォルト logs/）

---

## 使い方（起動/実行例）

1. 設定作成・検証
   - python -m kabusys.config_setup
   - python -m kabusys.validate_config

2. 監視プロセスの起動（SystemMonitor のループ）
   - python -m kabusys.run_monitoring
   - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（秒）

   特徴:
   - 監視は常に本番 sqlite_path を使用（環境に依らない）
   - 停止：プロジェクトルート/data/stop_requested.flag を作成するとループは検知して終了

3. 実行エンジン（ExecutionEngine）の起動
   - python -m kabusys.run_execution
   - KABUSYS_ENV=paper_trading を設定すると MockBroker を使い data/paper_trading.db に書き込む
   - 停止：data/stop_requested.flag により安全に停止
   - PID 管理：data/execution.pid に PID を書き込む（設定に応じて）

4. Paper Trading 検証レポート生成
   - python -m kabusys.tools.paper_verification_report
   - 期間指定:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - SQLite DB 指定:
     - --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数やデフォルトを利用可）

5. AI モジュール（ニューススコア / レジーム判定）
   - OpenAI API キーが必要（OPENAI_API_KEY に設定）
   - 例（news_nlp）:
     - Python スクリプト内で kabusys.ai.news_nlp.score_news を呼ぶ（DuckDB 接続と target_date を渡す）
   - エラーや API 失敗はフェイルセーフで処理される設計

6. Kill Switch
   - RiskMonitor 等の判定により KillSwitch が発動すると data/kill.flag に理由を出力し Execution を停止させる
   - 手動で解除するには該当フラグファイルを削除（または KillSwitch.clear を呼ぶ）

---

## 注意点 / 運用メモ
- Paper Trading と本番 DB は分離されています。KABUSYS_ENV に注意して起動してください。
- .env は機密情報（API トークン / パスワード）を含むため Git 管理に入れないでください。
- OpenAI API 呼び出しは料金と利用制限に依存します。API キーやレート制限に注意してください。
- run_monitoring / run_execution は stop_requested.flag を監視しているので CI/デプロイ環境での停止用フラグと衝突しないように注意してください。
- ログは logs/ 以下に日次ローテーションで出力されます。LOG_DIR 環境変数で変更可能です。

---

## ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理（.env 自動読み込み機能含む）
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py (注: 実装の一部に依存)
  - execution/                — 発注／リスク／オーダー関連（Engine / OrderManager 等）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - data/                     — デフォルトの DB / PID / flag 保存先（実行時に作成される）

（上記は主要ファイルの抜粋です。実際のツリーにはさらに多くのサブモジュールや実装ファイルがあります）

---

## 開発・テストのヒント
- 自動 .env 読み込みはプロジェクトルートの .env / .env.local を基に行われます。テスト時に無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- Logging は kabusys.utils.logging_setup.setup_logging を使用して統一してください。
- OpenAI 呼び出しはモジュール内でラップしているため、ユニットテスト時は該当呼び出し関数をモックしてください（news_nlp._call_openai_api や regime_detector._call_openai_api など）。
- DuckDB 接続は関数に注入する設計のため、テスト用の in-memory DB やテスト用データで容易に検証できます。

---

もし README に追加したい内容（例: Dockerfile、CI/CD 設定、具体的な設定例の .env テンプレート、コマンド例の詳細）があれば教えてください。README をそれに合わせて拡張します。