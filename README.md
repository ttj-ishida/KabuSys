# KabuSys — 日本株自動売買システム（README）

このリポジトリは日本株向けの自動売買・運用支援ライブラリと起動スクリプト群を含みます。  
README ではプロジェクト概要、主要機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめています。

---

## プロジェクト概要

KabuSys は以下の役割を持つコンポーネント群から構成されています。

- ExecutionEngine（発注エンジン）: ブローカークライアントを用いた発注・注文管理・リスク管理
- Monitoring（監視）: システム状態・データ鮮度・注文の健全性・ドローダウン等の監視、必要に応じて Kill Switch を発動
- Portfolio / Strategy ユーティリティ: 候補選定、重み算出、ポジションサイズ計算、セクター制約などの純粋関数
- Research / Data 処理: DuckDB を利用したファクター計算、特徴量探索
- AI モジュール: OpenAI を使ったニュースのセンチメントスコア化（ai.news_nlp）、市場レジーム判定（ai.regime_detector）
- ツール: Paper Trading の検証レポート生成など

設計方針の一部:
- 本番／ペーパートレードを切り替え可能（KABUSYS_ENV）
- .env による設定管理（自動ロード機構あり）
- DuckDB（分析用）と SQLite（監視 / 発注ログ）を併用
- フェイルセーフ: API エラーや欠損データ時は安全にフォールバック

---

## 機能一覧

主な機能（抜粋）:

- 起動スクリプト
  - run_execution.py: ExecutionEngine の起動（KABUSYS_ENV=paper_trading 時は Mock ブローカー）
  - run_monitoring.py: SystemMonitor を定期ポーリングして監視ログを記録
- 設定管理
  - config_setup.py: 対話式で .env を生成・更新するウィザード
  - validate_config.py: .env と config/*.yaml の整合性チェック
- 監視 / Kill Switch
  - system_monitor: CPU/メモリ/ディスク/プロセス生存/データ鮮度の監視
  - trade_monitor / risk_monitor: 注文滞留・約定異常・ドローダウン/ポジション上限監視
  - kill_switch: 一定条件で data/kill.flag を書き込み ExecutionEngine を停止させる
- 永続化（Monitoring）
  - monitoring_db: SQLite ベースで system_status, trade_logs, positions, risk_logs, dashboard を管理
- ポートフォリオ構築（純粋関数）
  - 銘柄選定（スコア順）・等金額／スコア重み・ポジションサイズ計算・セクターキャップ適用・レジーム乗数
- Research
  - ファクター（Momentum/Value/Volatility）計算（DuckDB を用いる）
  - 将来リターン・IC / 統計サマリー計算
- AI (OpenAI)
  - news_nlp.score_news: ニュース記事を LLM により銘柄ごとにスコア化して ai_scores テーブルへ保存
  - regime_detector.score_regime: ETF の MA 乖離とマクロニュース LLM を合成して market_regime に保存
- ツール
  - tools/paper_verification_report.py: ペーパートレード DB から検証レポートを生成

---

## セットアップ手順（開発環境）

以下は一般的な Python プロジェクトのセットアップ手順です。requirements.txt はプロジェクトに合わせて用意してください（本コードベースでは duckdb, psutil, openai, などを利用します）。

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成して有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .\.venv\Scripts\activate    # Windows (PowerShell)
   ```

3. 依存パッケージをインストール
   - requirements.txt がある場合:
     ```bash
     pip install -r requirements.txt
     ```
   - 主要パッケージ（例）:
     ```bash
     pip install duckdb psutil openai
     ```

4. .env を作成
   - 対話式ウィザードを使う:
     ```bash
     python -m kabusys.config_setup
     ```
   - もしくは手動でプロジェクトルートに `.env` を作成（例は次節）。

5. 設定検証
   ```bash
   python -m kabusys.validate_config
   ```

注意: `.env` は機密情報（API トークン等）を含むため、絶対に Git にコミットしないでください。

---

## 主要な環境変数（例とデフォルト）

重要な環境変数（必須・任意）:

- 必須:
  - JQUANTS_REFRESH_TOKEN (J-Quants API)
  - KABU_API_PASSWORD (kabuステーション API)

- 実行環境:
  - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）

- データベース:
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (監視 DB, デフォルト: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB, デフォルト: data/paper_trading.db)

- OpenAI:
  - OPENAI_API_KEY (ai モジュールで使用)

- Paper trading 振る舞い:
  - PAPER_FILL_MODE: instant, partial, never, reject（デフォルト: instant）

- ログ:
  - LOG_LEVEL (デフォルト: INFO)
  - LOG_DIR (デフォルト: logs/)

- Kill / PID:
  - PID_FILE_PATH (デフォルト: data/execution.pid)
  - KILL_FLAG_PATH (デフォルト: data/kill.flag)
  - KILL_FLAG_CLEAR_ON_START (0/1、デフォルト: 0)

その他: MONITOR_POLL_INTERVAL は run_monitoring のポーリング間隔（秒）を上書きできます（デフォルト 60 秒）。

例（.env の一部）:
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...
```

---

## 使い方（コマンド例）

プロジェクトはパッケージとして実行可能なモジュールを提供しています。推奨は python -m を使う方法です。

- 環境ウィザード（.env を生成）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```

- ExecutionEngine を起動
  - 本番/開発/ペーパートレードは KABUSYS_ENV に依存します。
  ```bash
  # 起動（バックグラウンドでのデーモン化等はプロセス管理ツールに任せてください）
  python -m kabusys.run_execution
  ```
  - paper_trading モードでは専用の paper_trading DB（PAPER_TRADING_SQLITE_PATH）を使用し、MockBrokerClient を使うように設計されています。

- Monitoring を起動（system monitor のポーリング）
  ```bash
  # ポーリング間隔を上書きする（秒）
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

- Paper Trading 検証レポート（ツール）
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB 指定:
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI モジュールをスクリプトや REPL から呼ぶ例（DuckDB 接続を作成して呼び出す）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  conn = duckdb.connect('data/kabusys.duckdb')
  n_written = score_news(conn, target_date=date(2026,4,10), api_key='sk-...')
  ```

- Kill Switch / 停止制御
  - ExecutionEngine は data/stop_requested.flag（または data/kill.flag）等をチェックして安全に停止します。
  - KillSwitch は監視側から data/kill.flag を書き込むことで ExecutionEngine を停止させます（設定により起動時に自動クリアも可能）。

---

## ロギング

- 共通ログセットアップ関数: kabusys.utils.logging_setup.setup_logging(app_name="...")  
  ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次、30日保持）を設定します。
- ログファイル名は `<LOG_DIR>/<app_name>.log`（デフォルト LOG_DIR=logs/）。

---

## 注意事項 / 運用上のポイント

- .env は絶対に Git にコミットしないでください（秘密情報を含む）。
- 本番（KABUSYS_ENV=live）で動かす場合は validate_config で警告・設定を確認してください。特に LINE 通知や KILL_FLAG_CLEAR_ON_START の設定は重要です。
- OpenAI への呼び出しはレート制限やエラーを想定して実装されていますが、API キーやコスト管理には注意してください。
- DuckDB / SQLite ファイルはデフォルトで data/ 配下に保存されます。バックアップや配置先の権限設定を確認してください。
- process_priority を高くする処理がありますが、OS 権限によっては設定できない場合があります（ログで警告が出ます）。

---

## ディレクトリ構成（抜粋）

以下は主要ファイルを抜粋したツリー（src/kabusys 配下）。実際のリポジトリにはさらにファイルがある可能性があります。

- src/
  - kabusys/
    - __init__.py
    - config.py
    - config_setup.py
    - validate_config.py
    - run_execution.py
    - run_monitoring.py
    - tools/
      - __init__.py
      - paper_verification_report.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - monitoring/
      - monitoring_db.py
      - monitoring_engine.py
      - system_monitor.py
      - trade_monitor.py (参照あり)
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py (参照あり)
    - execution/
      - broker_factory.py (参照あり)
      - execution_engine.py (参照あり)
      - order_manager.py (参照あり)
      - order_repository.py (参照あり)
      - reconciler.py (参照あり)
      - risk_manager.py (参照あり)
    - portfolio/
      - __init__.py
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - utils/
      - __init__.py
      - logging_setup.py
      - process_priority.py
    - monitoring/monitoring_db.py

（注）上記の tree はこの README 作成時の主要ファイルに基づき抜粋しています。実際のプロジェクトには data/、logs/、config/ 等のトップレベルディレクトリが含まれます。

---

## 開発者向けメモ

- 各モジュールは可能な限り副作用を抑えた実装（純粋関数 / 明示的な DB 接続引き渡し）を目指しています。ユニットテストは関数単位で可能です。
- DuckDB による計算は SQL を利用するため、テーブル構成（prices_daily, raw_financials, raw_news, news_symbols, ai_scores, market_regime 等）に依存します。分析用テーブルのスキーマに注意してください。
- AI モジュールは OpenAI SDK（openai）を使用しています。テスト時は HTTP 呼び出し部分をモック（patch）してテスト実行してください。

---

## 問い合わせ / 変更履歴

- バージョンは kabusys.__version__ に定義されています（例: 0.1.0）。
- 変更やバグ報告は issue を通じて行ってください。

---

README は以上です。追加で以下が必要であれば教えてください：
- 具体的な .env.example の自動生成
- systemd / Supervisor を使った実運用のサービス定義例
- 各テーブルスキーマの詳細ドキュメント（DuckDB / SQLite）