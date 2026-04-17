# KabuSys

KabuSys は日本株の自動売買・研究・監視を行うための Python コードベースです。本リポジトリは取引エンジン、監視基盤、ポートフォリオ構築、ファクター計算、ニュース NLP（OpenAI）連携などのコンポーネントを含みます。

以下はこのコードベースの README（日本語）です。

---

## プロジェクト概要

KabuSys は次の役割を持つモジュール群で構成されています。

- Execution: ブローカー API 経由で発注を行う ExecutionEngine、OrderManager、OrderRepository 等
- Monitoring: システム状態・注文状態・リスク（ドローダウンやポジション上限）を定期監視し、ログとアラートを管理
- Portfolio: 候補選定、重み付け、ポジションサイズ算出、セクター制約やレジーム乗数
- Research: DuckDB 上の価格・財務データからファクター・将来リターン・IC 等を算出
- AI: OpenAI を用いたニュースセンチメント（news_nlp）や市場レジーム判定（regime_detector）
- Tools: Paper Trading の検証レポート生成などのユーティリティスクリプト

設計ポリシーの一部:
- DuckDB を研究用 DB、SQLite を監視・発注ログに使用（Paper Trading は本番 DB と明確に分離）
- 外部 API 呼び出しは明示的にキーを必要とし、失敗時はフェイルセーフ動作（スキップやデフォルト値）を行う
- 自動読み込みされる .env ファイルのルールを持つ（プロジェクトルート基準）

---

## 主な機能一覧

- システムモニタリング
  - CPU / メモリ / ディスク使用率の定期ログ
  - Execution プロセスの存否チェック（PID ファイル）
  - 株価データ鮮度チェック（DuckDB の prices_daily）
  - モニタリング結果の永続化（SQLite、monitoring_db）
- トレード監視
  - 滞留注文（stale orders）検出
  - 約定異常（価格乖離）検出
  - トレード関連ログ（trade_logs）への保存
- リスク監視
  - ドローダウン監視（ハイウォーターマーク管理）
  - ポジション数上限監視
  - アラート発行と risk_logs への記録
- Kill Switch
  - しきい値超過で data/kill.flag を書き込み ExecutionEngine を停止させる仕組み
- Alert（LINE）
  - LINE Messaging API への push 通知（クールダウン管理）
- Execution
  - ブローカー抽象（実ブローカー / MockBroker のファクトリ）
  - 再起動時のリコンシリエーション（Reconciler）
  - OrderManager による状態遷移管理
- Portfolio 構築
  - 候補選定、等重・スコア重み、リスクベースの単元数算出、セクター上限、レジーム乗数
- Research
  - Momentum / Volatility / Value などのファクター計算
  - Forward returns、IC（Spearman）や統計サマリ
- AI（OpenAI）
  - ニュースを LLM で評価して ai_scores に保存
  - マクロニュースと ETF の MA200 を合成して市場レジーム判定
- ツール
  - Paper Trading 検証レポート生成スクリプト（期間指定可）
  - Streamlit ダッシュボード（monitoring DB の可視化）

---

## セットアップ手順

前提:
- Python 3.10 以上（typing の | 記法等を使用）
- システムに duckdb、psutil、requests、openai、streamlit 等のライブラリをインストール

例: 仮想環境を作成してインストール
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# requirements.txt がない場合:
pip install duckdb psutil requests openai streamlit
```

環境変数（主なもの）
- 必須（実運用時）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- OpenAI 関連
  - OPENAI_API_KEY
- システム / 動作モード
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- データベースパス（デフォルトあり）
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
- その他
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（LINE 通知用）
  - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）
  - LOG_LEVEL（DEBUG/INFO/...）

.env の自動読み込み:
- プロジェクトルート（.git または pyproject.toml のあるディレクトリ）から .env と .env.local を自動読み込みします。
- OS 環境変数 > .env.local > .env の優先順位。
- 自動読み込みを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

注意:
- Paper Trading（KABUSYS_ENV=paper_trading）は本番 SQLite DB と完全に分離された PAPER_TRADING_SQLITE_PATH を使用します。
- 監視プロセスは KABUSYS_ENV にかかわらず本番 sqlite_path（SQLITE_PATH）を参照して monitoring ログを記録します（設計上の意図）。

---

## 使い方

以下は主要な起動方法と使い方例です。

1) 監視ループの起動（Monitoring）
- デフォルトのポーリング間隔は 60 秒。環境変数 MONITOR_POLL_INTERVAL で秒数を変更できます。
- 起動:
```bash
python -m kabusys.run_monitoring
# または
python src/kabusys/run_monitoring.py
```
- 停止:
  - 監視ループはプロジェクトルート/data/stop_requested.flag の存在を検知して終了します（flag ファイルを作ると停止）。
  - もしくは Ctrl+C（KeyboardInterrupt）。

2) Execution エンジンの起動（発注エンジン）
- 通常（本番/開発）:
```bash
python -m kabusys.run_execution
```
- Paper Trading（MockBroker を使用、データは data/paper_trading.db に保存）:
```bash
KABUSYS_ENV=paper_trading python -m kabusys.run_execution
```
- 動作:
  - 起動時に process priority を "high" に設定します（utils.process_priority）。
  - 起動前に data/stop_requested.flag が存在すると起動をスキップします。
  - 実行中に data/stop_requested.flag を作成するとエンジンを停止します。
  - PID ファイルは data/execution.pid（設定で変更可）に書き込まれます。

3) Streamlit ダッシュボード（監視 UI）
- 起動:
```bash
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```
- 読み取り専用で SQLite ファイルを開き、Overview / Positions / Orders / System を表示します。

4) Paper Trading 検証レポート
- usage:
```bash
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# DB パスを指定する場合:
python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
```
- 出力: 稼働率、注文成功率、送信率、P95 レイテンシ等のサマリと PASS/FAIL 判定を標準出力に表示します。

5) AI 関連（ニューススコア / レジーム判定）
- 実行関数はモジュール API（kabusys.ai.news_nlp.score_news や kabusys.ai.regime_detector.score_regime）として提供されています。これらは OpenAI API キー（OPENAI_API_KEY）を必要とします。
- スクリプト的に呼び出すか、別途 CLI ラッパーを作って利用してください。

6) Kill / Stop フラグ
- Execution を強制停止させる条件（ドローダウンやポジション上限超過）を満たすと monitoring 側から data/kill.flag が書き込まれます。Execution 起動時にこのフラグが検出されると起動をスキップします。
- 手動でクリアする場合:
```bash
rm data/kill.flag
# または Python API で KillSwitch.clear() を呼ぶ
```

---

## 環境変数の主な一覧（重要項目）

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- DUCKDB_PATH: DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（default: data/paper_trading.db）
- PID_FILE_PATH: Execution エンジンの PID ファイルパス（default: data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（default: data/kill.flag）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、default: 60）
- PAPER_FILL_MODE: instant | partial | never | reject（Paper Trading の約定モード）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）

（詳細は kabusys/config.py に定義されています。デフォルトやバリデーションルールを必ずご確認ください）

---

## ディレクトリ構成

以下は主要なファイル/ディレクトリの構成と簡単な説明（src/kabusys 以下）。

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / 設定管理（.env 自動読み込みロジック含む）
  - run_monitoring.py — SystemMonitor のポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - ai/
    - news_nlp.py — ニュースを LLM でスコアリングして ai_scores 保存
    - regime_detector.py — マクロ + MA200 で市場レジームを判定
  - monitoring/
    - monitoring_db.py — monitoring 用 SQLite のスキーマ + DB ラッパー
    - system_monitor.py — CPU/メモリ/ディスク/データ鮮度/プロセスチェック
    - trade_monitor.py — 滞留注文 / 約定異常検出
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 管理（書込・クリア）
    - alert_manager.py — LINE 通知クライアント
    - monitoring_engine.py — 各 Monitor を束ねるポーリングエンジン
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - execution/
    - order_manager.py — 発注状態遷移 API
    - reconciler.py — 再起動時の同期・照合ロジック
    - （その他：broker_factory, execution_engine, order_repository 等）
  - portfolio/
    - portfolio_builder.py — 候補選定、重み計算
    - position_sizing.py — 単元丸め / ポジションサイズ計算
    - risk_adjustment.py — セクター上限 / レジーム乗数
    - __init__.py
  - research/
    - factor_research.py — Momentum / Volatility / Value の計算
    - feature_exploration.py — 将来リターン、IC、統計サマリ
    - __init__.py
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - utils/
    - process_priority.py — プロセス優先度・CPU affinity 設定ユーティリティ

データディレクトリ（プロジェクトルート配下、コードから参照される既定値）
- data/
  - monitoring.db (default SQLITE_PATH)
  - paper_trading.db (Paper Trading 用)
  - kabusys.duckdb (default DUCKDB_PATH)
  - execution.pid
  - stop_requested.flag
  - kill.flag

---

## 運用上の注意・ベストプラクティス

- 環境分離:
  - Paper Trading（検証）時は必ず KABUSYS_ENV=paper_trading を使用し、PAPER_TRADING_SQLITE_PATH を確認してください。本番データと混在しないように注意。
- 鍵の管理:
  - OPENAI_API_KEY / JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD 等は安全に管理し、.env をバージョン管理しないでください。
- 自動起動 / サービス化:
  - run_monitoring/run_execution は常駐プロセスとして動作します。systemd 等でサービス化する際は PID ファイルや stop/kill フラグの扱いを明確にしてください。
- ロギング:
  - デフォルトは INFO。トラブルシュート時は LOG_LEVEL=DEBUG を設定して詳細ログを取得してください。
- DB バックアップ:
  - DuckDB / SQLite のバックアップとローテーション方針を用意してください（特に本番取引ログは重要）。

---

## 開発・拡張のヒント

- DuckDB 接続をモックして研究関数を単体テスト可能です（モジュールは外部 API を直接叩かない設計）。
- OpenAI 呼び出し箇所は個別にラップされておりテスト時にパッチ可能（例: unittest.mock.patch）。
- ポートフォリオ関係関数は純粋関数として実装されているため、単体テストが容易です。

---

この README はコードベースの主要点をまとめたものです。実装の詳細や細かい API 仕様については該当モジュールの docstring / ソースコードを参照してください。必要であれば README に入れるコマンド例や環境変数テンプレート（.env.example）を追加で作成します。希望があれば教えてください。