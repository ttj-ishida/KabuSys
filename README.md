# KabuSys

日本株自動売買システムの Python 実装 (ライブラリ + 実行用スクリプト)。  
このリポジトリは取引実行エンジン、監視/アラート、ポートフォリオ構築、リサーチ/ファクター計算、AI ベースのニュースセンチメント評価などを含みます。

以下はソースコード（src/kabusys）に基づく README です。

---

## プロジェクト概要

KabuSys は日本株の自動売買を想定したモジュール群と起動スクリプト群の集合です。主な責務は次のとおりです。

- ExecutionEngine：注文の生成・送信・状態管理・リコンシリエーション
- Monitoring：システム状態、注文/約定の監視、リスク検出と通知（LINE）
- Portfolio Construction：銘柄選定、重み付け、ポジションサイズ計算、リスク補正
- Research：DuckDB 上の過去価格／財務データを用いたファクター計算・解析
- AI：ニュースを LLM（OpenAI）で解析して銘柄ごとのセンチメント評価
- Tools：Paper Trading の検証レポート生成などユーティリティ

設計方針のポイント：
- DuckDB をデータ分析用に利用、SQLite を監視ログ等の永続化に利用
- 本番と Paper Trading を明確に分離（Paper 用 DB）
- ルックアヘッドバイアス回避（日時参照の扱いに注意）
- フェイルセーフ：外部 API 失敗時は安全にフォールバックする実装

---

## 機能一覧

- 実行関連
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - ブローカークライアントの抽象化（BrokerClientFactory）
  - 注文管理（OrderManager / OrderRepository / Reconciler）

- 監視関連
  - SystemMonitor：CPU/MEM/Disk、データ鮮度、実行プロセス監視
  - TradeMonitor：滞留注文・約定異常検出
  - RiskMonitor：ドローダウン / ポジション上限監視
  - KillSwitch：条件により kill.flag を書き込んで Execution を止める
  - AlertManager：LINE Push による一方向通知
  - Streamlit ダッシュボード（データ閲覧）

- ポートフォリオ構築
  - 候補選定（select_candidates）
  - 等重 / スコア重み付け（calc_equal_weights / calc_score_weights）
  - セクター上限適用（apply_sector_cap）
  - レジーム乗数（calc_regime_multiplier）
  - ポジションサイズ計算（calc_position_sizes）

- リサーチ / ファクター
  - モメンタム / ボラティリティ / バリュー計算（calc_momentum, calc_volatility, calc_value）
  - 将来リターン、IC、統計サマリー等のユーティリティ

- AI（OpenAI）
  - ニュースセンチメント評価（news_nlp.score_news）
  - マクロセンチメント + MA200 で市場レジーム判定（regime_detector.score_regime）

- ツール
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）
  - 監視 DB 初期化は接続時に自動で行われます（init_monitoring_db）

---

## セットアップ手順

注意: コードは Python 3.10+ を想定（型アノテーションの union などを使用）。

1. リポジトリをチェックアウト
2. 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - duckdb
   - psutil
   - requests
   - openai
   - streamlit (ダッシュボード利用時)
   例:
   ```
   pip install duckdb psutil requests openai streamlit
   ```
   （requirements.txt がある場合はそれを使ってください）

4. 環境変数 / .env
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（既定の優先順位: OS 環境 > .env.local > .env）。
   - 自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

5. 主な必要環境変数（例）
   - JQUANTS_REFRESH_TOKEN — J-Quants 用トークン（必須）
   - KABU_API_PASSWORD — kabu API パスワード（必須）
   - OPENAI_API_KEY — OpenAI API キー（AI 機能利用時）
   - KABUSYS_ENV — 実行環境: development | paper_trading | live (デフォルト: development)
   - SQLITE_PATH — 監視 DB path（デフォルト: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（paper_trading のときのみ使用）
   - DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知用（任意）
   - PAPER_FILL_MODE — paper_trading の注文約定モード（instant, partial, never, reject）
   - MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト: 60）
   - PID_FILE_PATH / KILL_FLAG_PATH — ファイルパスの上書き

6. データディレクトリ
   - `data/` 配下に監視DBやPID・フラグファイルを配置する想定です。自動で作成されますが、パーミッションに注意してください。

---

## 使い方

### 実行エンジンを起動
- 通常実行（環境変数で KABUSYS_ENV を制御）
```
# 本番/開発共通（Settings に従う）
python -m kabusys.run_execution
```

- Paper Trading（MockBroker + 専用 DB を使用）
```
KABUSYS_ENV=paper_trading python -m kabusys.run_execution
```
- エンジンは起動中に data/stop_requested.flag が存在すると停止します。停止用のフラグファイルはプロジェクトルートの data/ に作成されます（run_execution 内で _STOP_FLAG をチェック）。

### 監視ループを起動
```
python -m kabusys.run_monitoring
```
- 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を指定可能（デフォルト 60 秒）。不正値（0 以下や非整数）は無視されデフォルトにフォールバックします。
- 監視は Settings.sqlite_path（本番用パス）を使用してログを書きます（monitoring は KABUSYS_ENV に依存せず本番 sqlite_path を使う設計）。
- 監視ループも data/stop_requested.flag を検知して終了します。

### Paper Trading 検証レポート
- SQLite（paper_trading DB）から検証レポートを生成：
```
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# または DB を直接指定
python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
```
- レポートは稼働率、注文成功率、送信率、P95 レイテンシなどを算出し PASS/FAIL を判定します。

### Streamlit ダッシュボード
- 監視 DB を読み取り専用で表示（実行中に確認する用途）：
```
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```

### AI 機能（ニュース NLP / レジーム検出）
- OpenAI API キーが必要です（OPENAI_API_KEY 環境変数または関数引数で指定）。
- news_nlp.score_news / regime_detector.score_regime を呼ぶことでニューススコアやレジーム判定を行います。
- API 呼び出しは冪等性・リトライ・部分失敗保護を考慮した実装になっています（失敗時はフェイルセーフで継続）。

### 停止・強制停止の仕組み
- run_execution / run_monitoring は data/stop_requested.flag を監視して終了します。
- KillSwitch は監視結果に基づき data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送る用途で利用します（ExecutionEngine 側で kill.flag を検知して停止する設計）。

---

## 主要ディレクトリ構成（src/kabusys）

概要のみ抜粋（実ファイルは src/kabusys 以下を参照）:

- kabusys/
  - __init__.py — パッケージ定義（バージョン等）
  - config.py — Settings クラス、.env 自動読込ロジック、環境変数管理
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト

- kabusys/execution/
  - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, broker_factory.py, broker_api.py, order_record.py ...
  - 注文作成、送信、同期、再起動時のリコンシリエーションを扱う

- kabusys/monitoring/
  - monitoring_db.py — SQLite のテーブル作成・ログ永続化
  - system_monitor.py — CPU/MEM/Disk、データ鮮度、PID チェック
  - trade_monitor.py — 注文滞留・価格異常検出
  - risk_monitor.py — ドローダウン・ポジション上限
  - kill_switch.py — kill.flag 書込ロジック
  - alert_manager.py — LINE Push 通知
  - monitoring_engine.py, streamlit_dashboard.py

- kabusys/portfolio/
  - portfolio_builder.py — 候補選定 / 重み計算
  - position_sizing.py — 株数計算・スケールダウンロジック
  - risk_adjustment.py — セクターキャップ・レジーム乗数

- kabusys/research/
  - factor_research.py — モメンタム/ボラ/バリュー計算
  - feature_exploration.py — 将来リターン・IC・統計量

- kabusys/ai/
  - news_nlp.py — ニュースを LLM でスコアリングして ai_scores に書き込む
  - regime_detector.py — MA200 とマクロセンチメントを組み合わせたレジーム判定

- kabusys/tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト

- kabusys/utils/
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

---

## 追加ノート / 運用上の注意

- Settings クラスで環境変数の妥当性チェックを行います（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）。設定値が正しくないと起動時に例外が出ます。
- monitoring は常に本番用の sqlite_path を参照します。Paper Trading の監視ログと混ざらないよう設計されています（Paper Trading 時は run_execution が paper_sqlite_path を使用）。
- OpenAI API を使う処理は API 利用量・レート制限に注意してください。コード側でリトライとバックオフは入っていますが、運用側でも制限管理が必要です。
- PID ファイルやフラグファイル（data/*.pid, data/kill.flag, data/stop_requested.flag）はディスク上に残るため、起動前に不要なフラグをクリアする運用ルールを設けてください（KillSwitch.clear() 等を利用）。

---

もし README に追加したい内容（例: 具体的な設定例の .env テンプレート、requirements.txt の生成、デプロイ手順や systemd ユニット例など）があれば教えてください。必要に応じてサンプル .env、systemd ユニット、Dockerfile なども作成します。