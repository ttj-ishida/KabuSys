# KabuSys

KabuSys は日本株向けの自動売買フレームワーク（実装中のプロトタイプ）です。  
トレードの実行エンジン、監視・アラート基盤、ポートフォリオ構築ロジック、リサーチ用ファクター計算、LLM を使ったニュースセンチメント評価などを含みます。設計上、本番処理と Paper Trading（模擬取引）は明確に分離されており、監視ログは SQLite、時系列・分析データは DuckDB に格納します。

主な設計方針
- モジュール毎に責務を分離（execution / monitoring / portfolio / research / ai / utils）
- 外部 API 呼び出し（ブローカー・OpenAI 等）は明示的に切替可能（環境変数で制御）
- Look-ahead バイアス対策（日時参照や DB クエリの制限）
- フェイルセーフ（API 失敗時は一部処理をスキップして継続）

---

## 機能一覧
- Execution Engine
  - ブローカー（実稼働 or モック）経由の発注管理
  - 注文状態遷移、リスク管理、再起動時のリコンシリエーション
- Monitoring（監視）
  - システムリソース・プロセス監視（CPU/メモリ/ディスク、PIDファイル）
  - 注文滞留・約定異常検出、ドローダウン／ポジション上限監視
  - Kill Switch（条件を満たすと ExecutionEngine に停止フラグをセット）
  - LINE 経由のアラート送信（AlertManager）
  - Streamlit ダッシュボード
- Portfolio construction
  - 候補選定、等金額・スコア重み付け、セクター上限適用、ポジションサイズ計算（単元考慮・集計キャップ）
- Research
  - Momentum / Volatility / Value 等ファクター計算（DuckDB を使った SQL ベース）
  - 将来リターン、IC（情報係数）、統計サマリの計算
- AI（LLM）
  - ニュースのセンチメント集計と ai_scores への書き込み（OpenAI）
  - マクロニュース＋ETF MA200 に基づく市場レジーム判定（regime_detector）
- ツール
  - Paper Trading 用検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

---

## 必要条件（概略）
- Python 3.10+
  - typing の union 型（A | B）および一部の構文に依存
- 外部パッケージ（代表例）
  - duckdb
  - psutil
  - requests
  - streamlit (ダッシュボード用)
  - openai (AI モジュール用)
- SQLite（標準ライブラリ）／ファイルシステムへの書き込み権限

requirements.txt がない場合は手動でインストール例：
```
python -m pip install duckdb psutil requests streamlit openai
```

---

## セットアップ手順（ローカルでの開始例）
1. リポジトリをクローンし、プロジェクトルートに移動
2. 仮想環境を作成して有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate    # macOS / Linux
   .venv\Scripts\activate       # Windows
   ```
3. 必要パッケージをインストール
   ```
   pip install duckdb psutil requests streamlit openai
   ```
4. data ディレクトリ作成（スクリプトが自動作成することもありますが手動で作るのが確実）
   ```
   mkdir -p data
   ```
5. 環境変数の設定
   - プロジェクトルートの `.env` / `.env.local` を使えます（config.py が自動読み込みします）
   - 主要環境変数（例）
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - OPENAI_API_KEY (AI 機能を使う場合)
     - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB、デフォルト data/paper_trading.db)
     - SQLITE_PATH (監視ログ DB、デフォルト data/monitoring.db)
     - DUCKDB_PATH (DuckDB ファイル、デフォルト data/kabusys.duckdb)
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（LINE アラート用）
     - MONITOR_POLL_INTERVAL（監視ループの秒間隔、デフォルト 60）
   - 自動 .env ロードはデフォルトで有効。無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
6. 初回起動時は監視 DB のスキーマはスクリプト側（init_monitoring_db）で自動作成／マイグレーションされます。

---

## 使い方（主なコマンド例）

注意: パッケージが `src/` 配下にある構成なら、プロジェクトルートで次のいずれかを行ってモジュールを実行します。
- PYTHONPATH を通す:
  ```
  PYTHONPATH=src python -m kabusys.run_monitoring
  ```
  あるいは、開発環境で sys.path に src が含まれていれば直接:
  ```
  python -m kabusys.run_monitoring
  ```

1. 監視ループ起動（Monitoring）
   - デフォルトは production でも monitoring.db を使用（監視は本番 DB を参照）
   - ポーリング間隔を上書きする場合:
     ```
     MONITOR_POLL_INTERVAL=30 PYTHONPATH=src python -m kabusys.run_monitoring
     ```
   - 停止はプロジェクトルートの data/stop_requested.flag を作成することで検知して終了します。

2. Execution Engine 起動
   - 通常実行:
     ```
     PYTHONPATH=src python -m kabusys.run_execution
     ```
   - Paper Trading（MockBroker, 専用 DB に書き込み）:
     ```
     KABUSYS_ENV=paper_trading PYTHONPATH=src python -m kabusys.run_execution
     ```
   - 停止シグナル:
     - KillSwitch から data/kill.flag が書かれるとエンジンは起動停止（killflag は ExecutionEngine 起動時にオプションで制御）
     - また監視側 stop flag（data/stop_requested.flag）でループを停止します。
   - 実行中、PID ファイルは data/execution.pid（設定により変更可）に書き込まれます。古い PID（stale）は SystemMonitor により検出・削除されます。

3. Streamlit ダッシュボード（監視可視化）
   ```
   streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   ```
   - ローカルで read-only モードで DB を開き、ポジション・オーダー・システム状態・最近のリスクログを表示します。

4. Paper Trading 検証レポート
   ```
   PYTHONPATH=src python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db
   ```

5. AI 機能
   - ニューススコアリング/レジーム判定はモジュール関数を直接呼び出して利用します（OpenAI API キーが必要）。
   - 例（スクリプト化して利用する想定）:
     - kabusys.ai.score_news(conn, target_date, api_key=...)
     - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)

---

## ファイル・フラグ / 運用上のポイント
- data/
  - stop_requested.flag — run_monitoring / run_execution の外部停止フラグ（存在すればループを終了）
  - kill.flag — KillSwitch が書き込む停止フラグ（ExecutionEngine 停止トリガー）
  - execution.pid — エンジンの PID（SystemMonitor が stale を検知・削除可能）
  - monitoring.db — 監視ログ（SQLite）
  - paper_trading.db — Paper Trading 用 SQLite（KABUSYS_ENV=paper_trading で使用）
  - kabusys.duckdb — DuckDB（時系列 / リサーチデータ）
- init_monitoring_db は必要なテーブルとインデックスを作成し、既存 DB の簡易マイグレーション（列追加）も行います。
- process priority: 実行スクリプトは起動時に set_process_priority("high") を呼びます（psutil 利用）。権限不足の場合は警告を出して続行します。

---

## 主要なディレクトリ構成（抜粋）
（実際のリポジトリは src/kabusys 配下にモジュール群があります）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env の読み込みと Settings クラス
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - execution/
    - order_manager.py
    - reconciler.py
    - order_repository.py
    - execution_engine.py (他、ブローカー関連)
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
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
  - data/                    — 実行時に使う DB / flag / pid ファイル等（プロジェクトルート）

---

## 注意事項 / 運用上のヒント
- Paper Trading モードは本番 DB と分離されます。KABUSYS_ENV=paper_trading を必ず設定してください。
- OpenAI 等の外部 API を使う機能は API キーが必須です。テスト時や CI ではモック化を推奨します（コード中で _call_openai_api を差し替え可能）。
- `.env` 自動ロードは config.py により行われます。OS 環境変数が優先され、.env.local は .env を上書きします。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
- DB ファイルはファイルロックや同時アクセスに注意してください（特に DuckDB は複数プロセス書き込みで挙動が変わることがあります）。monitoring 用 SQLite は軽量ロギング向けです。
- 本リポジトリは実運用を想定した詳細なロジックを含みますが、ブローカー接続・注文の振る舞いは実装や設定に依存します。実運用の前に十分な検証（Paper Trading, unit/integration tests）を行ってください。

---

README の内容や実行方法で不明な点があれば、どの機能・スクリプトについて詳しく知りたいか教えてください。使用方法に合わせた具体的な例（.env テンプレート、起動シェルスクリプト、systemd ユニット例など）も用意できます。