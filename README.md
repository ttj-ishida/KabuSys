# KabuSys — README

日本株自動売買システムの簡易実装。  
このリポジトリは注文発行・リスク管理・監視・リサーチ・AI（ニュースセンチメント）などのコンポーネントを含むモジュール群から構成されています。

目次
- プロジェクト概要
- 機能一覧
- 必要条件
- セットアップ手順
- 環境変数（主な設定項目）
- 使い方（起動例）
- ディレクトリ構成（主要ファイル説明）
- 付記（挙動の注意点）

---

## プロジェクト概要
KabuSys は日本株向けの自動売買基盤を想定した Python パッケージ群です。  
主な役割は以下の通りです：
- シグナル → 注文発行（ExecutionEngine / OrderManager）
- 発注の再同期・リコンシリエーション
- リスク管理（ドローダウン監視・ポジション数上限など）
- システム監視（プロセス死活、CPU/メモリ/ディスク、データ鮮度）
- 監視ダッシュボード（Streamlit）
- Paper Trading 用検証レポート生成
- ファクター計算・リサーチ（DuckDB を用いた価格・財務データ処理）
- ニュースの LLM ベースセンチメント評価（OpenAI）

設計方針の一端として、DuckDB をデータ解析に、SQLite を監視ログや orders DB に使用し、実行環境（本番 / paper）を環境変数で切り替えます。

---

## 機能一覧
- Execution
  - Order 作成・送信・状態同期
  - リコンシリエーション（再起動後の復旧）
  - RiskManager による発注前チェック（最大ポジション率など）
- Monitoring
  - SystemMonitor：CPU/Memory/Disk、プロセス PID、データ鮮度チェック
  - TradeMonitor：滞留注文（stale orders）、約定価格異常検出
  - RiskMonitor：ドローダウン・ポジション上限監視、ダッシュボード更新
  - MonitoringEngine：上記モニタの統合ループ（ポーリング）
  - AlertManager：LINE Push による通知（任意）
  - Streamlit ダッシュボード（read-only 経由で monitoring DB を表示）
- Research
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC 計算、統計サマリ
- AI
  - ニュースセンチメント（OpenAI を利用して銘柄ごとのスコアを ai_scores テーブルに書き込み）
  - 市場レジーム判定（MA200 とマクロセンチメントの合成）
- Tools
  - Paper Trading 検証レポート（指定期間の稼働率・成功率・レイテンシ等を集計）

---

## 必要条件
- Python 3.10+
- パッケージ（例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボードを使う場合)
  - 他：標準ライブラリのみで動く部分もありますが、上記が主な外部依存です。

パッケージインストール例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil requests openai streamlit
```

（プロジェクトに requirements.txt がある場合はそれを利用してください。）

---

## セットアップ手順
1. リポジトリをクローン / ワークツリーに配置。
2. 仮想環境を作成して依存パッケージをインストール（上記参照）。
3. .env ファイルをプロジェクトルート（pyproject.toml/.git のあるディレクトリ）に配置して環境変数を設定。
   - 自動で .env/.env.local を読み込みます（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可）。
4. データベースディレクトリを作る（例: data/）。
5. 初回実行時に Monitoring 用 SQLite のスキーマは自動作成されます（init_monitoring_db を利用）。

---

## 環境変数（主要項目）
- KABUSYS_ENV: 実行モード（development | paper_trading | live）。デフォルト: development
- SQLITE_PATH: 監視ログ用 SQLite（monitoring）パス。デフォルト: data/monitoring.db
- DUCKDB_PATH: DuckDB ファイルパス。デフォルト: data/kabusys.duckdb
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（分離された DB）。デフォルト: data/paper_trading.db
- PID_FILE_PATH: ExecutionEngine の PID ファイルパス（例: data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（例: data/kill.flag）
- MONITOR_POLL_INTERVAL: Monitoring ポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: Paper Trading の約定モード（instant | partial | never | reject）。デフォルト: instant
- OPENAI_API_KEY: OpenAI API 利用時に必要
- JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD: 外部 API 用トークン（必須とされる設定あり）
- LOG_LEVEL: ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）

注意:
- Monitoring（run_monitoring）は KABUSYS_ENV に依らず常に Settings.sqlite_path（監視 DB）を使います。
- Execution 起動時は `KABUSYS_ENV=paper_trading` の場合、専用の PAPER_TRADING_SQLITE_PATH を使って本番 DB と分離します。

---

## 使い方（起動例）

1. ExecutionEngine を起動（本番または paper_trading）
   - 本番（KABUSYS_ENV=live）:
     ```
     export KABUSYS_ENV=live
     python -m kabusys.run_execution
     ```
   - Paper Trading（データは data/paper_trading.db に記録）:
     ```
     export KABUSYS_ENV=paper_trading
     export PAPER_TRADING_SQLITE_PATH="data/paper_trading.db"
     python -m kabusys.run_execution
     ```

2. Monitoring（ポーリングループ）を起動
   - ポーリング間隔をカスタムにしたい場合:
     ```
     export MONITOR_POLL_INTERVAL=30  # 30秒間隔に変更
     python -m kabusys.run_monitoring
     ```
   - 監視ループは process priority を high に設定し、MonitoringDB を初期化して SystemMonitor の check_once を定期実行します。

3. Streamlit ダッシュボード（監視 DB を読み取り専用で表示）
   ```
   streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   ```
   - 読み取り専用で DB に接続するため、MonitoringEngine を並行して動かしてください。

4. Paper Trading 検証レポート生成
   ```
   python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db
   ```
   - 引数無しで実行するとデフォルト DB path (data/paper_trading.db) を参照します。

5. AI 関連（ニュース評価 / レジーム判定）
   - OpenAI キーをセットし、DuckDB 接続経由で関数を呼ぶ:
     - kabusys.ai.score_news(conn, target_date, api_key=...)
     - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)
   - これらはプログラムから直接呼び出すことを想定しています。

---

## 重要な挙動・注意点
- Settings モジュールはプロジェクトルートの .env/.env.local を自動で読み込みます（ただし OS 環境変数は保護され、.env.local は .env を上書き）。
- MONITOR_POLL_INTERVAL が 1 未満または不正な値の場合は警告が出てデフォルト（60秒）にフォールバックします。
- Paper Trading 時はブローカー呼び出しは MockBrokerClient を使い、DB は data/paper_trading.db に分離されます（本番 DB と混ざりません）。
- OpenAI API 呼び出しはリトライやバックオフ、レスポンス検証を行う実装になっていますが、APIキー未設定時は例外を投げます（呼び出し前にキーを用意してください）。
- Monitoring の SystemMonitor は PID ファイルを参照して ExecutionEngine の生存判定を行い、stale PID を検出すると削除して risk_logs に記録します。
- Monitoring DB のスキーマは init_monitoring_db() で冪等に作成され、古い DB に対する簡単なマイグレーション（カラム追加）も行います。

---

## ディレクトリ構成（主要ファイル）
（src/kabusys 以下を抜粋）

- kabusys/
  - __init__.py — パッケージ情報
  - config.py — 環境変数 / Settings 管理（.env 自動読み込み・検証を含む）
  - run_execution.py — ExecutionEngine 起動スクリプト（paper_trading での挙動分離）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL を使用）
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成 CLI
  - portfolio/
    - portfolio_builder.py — 候補選定 / 等配分・スコア配分
    - position_sizing.py — 発注株数計算・上限・丸め
    - risk_adjustment.py — セクターキャップ / レジーム乗数
  - research/
    - factor_research.py — Momentum / Volatility / Value の計算（DuckDB）
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - ai/
    - news_nlp.py — ニュースを OpenAI でスコアリングして ai_scores に書き込む
    - regime_detector.py — MA200 とマクロセンチメントでレジーム判定
  - monitoring/
    - monitoring_db.py — SQLite スキーマと MonitoringDB ラッパー（ログ保存）
    - system_monitor.py — CPU/メモリ/ディスク・データ鮮度・PID チェック
    - trade_monitor.py — 滞留注文・約定異常チェック
    - risk_monitor.py — ドローダウン / ポジション上限チェック
    - kill_switch.py — kill.flag 書き込みロジック（ExecutionEngine 停止シグナル）
    - alert_manager.py — LINE push による通知（クールダウン管理付き）
    - monitoring_engine.py — 各 Monitor を束ねたループ（テスト用 run_once / run）
    - streamlit_dashboard.py — Streamlit での監視 UI
  - execution/
    - order_manager.py — Order の作成・送信・状態遷移の外向き API
    - reconciler.py — 再起動後の注文・ポジション照合
    - その他（broker 関連のファイルはリポジトリ内に想定）

---

## 付記
- この README は配布されたソースコードのコメント・設計意図を元に作成しています。実際の運用では各 external API キー・パス・運用ポリシーに合わせた追加設定やセキュリティ対策（秘密情報管理、アクセス権限、監査ログなど）を実施してください。
- Python バージョン・ライブラリのバージョン互換性を事前に確認のうえ、仮想環境での依存管理を推奨します。

---

必要であれば、.env.example のサンプルや systemd / supervisor 用の起動ユニットの例、より詳細な運用手順（ログローテーション、バックアップ、監視アラートの閾値チューニングなど）も追加で作成します。どちらを優先しますか？