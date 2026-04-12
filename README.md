# KabuSys

日本株自動売買システム（KabuSys）のコードベース README（日本語）。

この README はリポジトリ内の主要モジュールの役割、セットアップ手順、実行方法、ディレクトリ構成の説明をまとめたものです。

注意: 実稼働での運用や API キーの取り扱いには十分注意してください。README 内の一部コマンドは環境依存です（SQLite / DuckDB のパス、OpenAI API キー、kabu API パスワード等）。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買フレームワークで、主に以下の機能を持ちます。

- シグナル → 注文発行 → 発注状態管理のための ExecutionEngine（発注・リスク管理・リコンシリエーション）
- システム稼働状況・注文状態・リスク監視を行う MonitoringEngine（監視ログの永続化、アラート送信、Kill Switch）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算、セクター制限）
- リサーチ用モジュール（ファクター計算、特徴量探索、Forward Return/IC 計算）
- AI 補助機能：ニュースセンチメント評価（OpenAI）や市場レジーム判定
- 運用支援ツール（Paper Trading 検証レポート生成、Streamlit ダッシュボード）

設計上の方針として、データ処理は可能な限り DuckDB / SQLite を用いたローカル処理で完結するようになっています。Paper Trading（検証）用 DB は本番の監視 DB と分離されます。

---

## 機能一覧（主要）

- execution/
  - OrderManager、ExecutionEngine、Reconciler による注文ライフサイクル管理
  - BrokerClientFactory による実ブローカー / モックの切り替え（KABUSYS_ENV=paper_trading など）
  - RiskManager によるレート制限・ポジション上限・ドローダウン監視

- monitoring/
  - SystemMonitor: CPU / メモリ / ディスク / データ鮮度 / プロセス存在チェック
  - TradeMonitor: 滞留注文・約定価格異常検知
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新
  - KillSwitch: 条件に応じてフラグファイルを書き、ExecutionEngine を停止させるためのシグナル
  - AlertManager: LINE Messaging API を使った一方向通知（クールダウン管理）
  - Streamlit ダッシュボード: 監視 DB を読み取り可視化

- portfolio/
  - 候補選定（score/rank ベース）、等分配/スコア加重、リスク調整（セクター上限、レジーム乗数）、ポジションサイズ算出（単元丸め・aggregate cap）

- research/
  - ファクター計算（momentum/value/volatility）
  - 将来リターン計算、IC（Spearman）や統計サマリ

- ai/
  - news_nlp: raw_news をまとめ、OpenAI（gpt-4o-mini）で銘柄別センチメントを算出して ai_scores に格納
  - regime_detector: ETF（1321）の MA200 とマクロニュースの LLM センチメントを合成して日次レジーム判定

- tools/
  - paper_verification_report: Paper Trading DB を集計して PASS/FAIL 判定のレポートを出力

- utils/
  - process_priority: Windows / POSIX 間差分を吸収してプロセス優先度・CPU affinity を設定

- config.py
  - .env 自動読み込み（プロジェクトルート検出）と Settings クラス（環境変数抜き取り／バリデーション）

---

## 動作要件 / 依存（例）

- Python 3.10 以上（Union 型表現や typing の表現から）
- 主要ライブラリ（一例、requirements.txt がない場合は手動インストール）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボード利用時)
- SQLite（Python 組み込みで OK）
- インターネット接続（OpenAI 呼び出しや LINE API 利用時）

インストール例:
```bash
python -m pip install duckdb psutil requests openai streamlit
```

---

## 環境変数（主要）

config.Settings で参照される主な環境変数（代表例）:

- KABUSYS_ENV: "development" | "paper_trading" | "live"（default: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API 用パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（ai.news_nlp / regime_detector 使用時）
- DUCKDB_PATH: DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（monitoring）パス（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（default: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading 時のモック約定モード（instant|partial|never|reject）
- LOG_LEVEL: ログレベル（DEBUG, INFO, ...）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: AlertManager（LINE）用
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

自動 .env ロード:
- プロジェクトルート（.git または pyproject.toml を探索）にある `.env` / `.env.local` を自動で読み込みます。
- OS 環境変数 > .env.local > .env の優先順。
- 自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンしてワークディレクトリに移動
2. Python 仮想環境を作成して有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```
3. 必要パッケージをインストール
   ```bash
   python -m pip install --upgrade pip
   python -m pip install duckdb psutil requests openai streamlit
   ```
4. 環境変数を設定（.env を作成するのが簡便）
   - 例 `.env`:
     ```
     KABUSYS_ENV=development
     JQUANTS_REFRESH_TOKEN=your_jquants_token
     KABU_API_PASSWORD=your_kabu_password
     OPENAI_API_KEY=sk-...
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     LINE_CHANNEL_ACCESS_TOKEN=
     LINE_USER_ID=
     ```
5. データディレクトリを作成
   ```bash
   mkdir -p data
   ```

---

## 使い方（実行例）

- ExecutionEngine（売買エンジン）を起動
  - 本番 / 開発 / paper_trading の挙動は KABUSYS_ENV によって変わります。
  - Paper Trading の場合は MockBrokerClient を使い、別 DB（PAPER_TRADING_SQLITE_PATH）に記録されます。
  ```bash
  python -m kabusys.run_execution
  ```

- Monitoring（ポーリング監視）を起動
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書きできます（デフォルト 60 秒）。
  - Monitoring は実行環境にかかわらず本番 sqlite_path を使用する点に注意（監視ログは production DB を参照）。
  ```bash
  python -m kabusys.run_monitoring
  # 例：ポーリングを 30 秒にする
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

- Streamlit ダッシュボードで監視情報を閲覧
  ```bash
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- Paper Trading 検証レポート生成ツール
  - デフォルト DB: data/paper_trading.db。--db オプションで上書き可能。
  ```bash
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- AI モジュール（スクリプト内／別プロセスから呼び出す）
  - ニューススコアリング: kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続を受け取り、結果をテーブルへ書き込みます。OpenAI API キーが必要です。

---

## 運用上の注意 / 挙動メモ

- run_monitoring の docstring にある通り、Monitoring は常に Settings.sqlite_path（production 監視 DB）を使います。監視データを分離したい場合は運用上でパスを変える必要があります。
- run_execution は KABUSYS_ENV=paper_trading の場合、Paper Trading DB（settings.paper_sqlite_path）に記録し「本番 DB と完全分離」されます。
- KillSwitch はファイルベース（default: data/kill.flag）で ExecutionEngine に停止シグナルを送ります。KillSwitch の書き込みは冪等で、既に存在する場合は再書き込みしません。
- config.Settings は .env 自動ロードを行います。テストや特殊用途で自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- process_priority.set_process_priority("high") が起動スクリプトで呼ばれます（権限により設定できない場合は警告が出てスキップされます）。
- Paper Trading の fill モードは PAPER_FILL_MODE で制御できます（instant|partial|never|reject）。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要ファイルと説明（抜粋）です。

- src/kabusys/__init__.py
  - パッケージ初期化、バージョン情報

- src/kabusys/config.py
  - 環境変数の読み込み・Settings クラス

- src/kabusys/run_execution.py
  - ExecutionEngine 起動スクリプト（KABUSYS_ENV に応じた broker 切替、DB 接続）

- src/kabusys/run_monitoring.py
  - SystemMonitor 単独起動スクリプト（ポーリングループ）

- src/kabusys/execution/
  - order_manager.py, reconciler.py, ... — 発注フロー、リコンシリエーション、リスク管理

- src/kabusys/monitoring/
  - monitoring_db.py — SQLite テーブル初期化 / 永続化層
  - system_monitor.py, trade_monitor.py, risk_monitor.py — 各種チェック
  - monitoring_engine.py — 各 Monitor を束ねる
  - alert_manager.py — LINE 通知
  - kill_switch.py — フラグ書き込みによる停止
  - streamlit_dashboard.py — ダッシュボード

- src/kabusys/portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py — 候補選定・重み・サイズ・セクター制限

- src/kabusys/research/
  - factor_research.py, feature_exploration.py — ファクター計算・IC・summary

- src/kabusys/ai/
  - news_nlp.py — ニュース NLU と ai_scores 書込み
  - regime_detector.py — 日次レジーム判定

- src/kabusys/tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成

- src/kabusys/utils/
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

（上記以外にも execution/order_repository.py、execution/order_record.py、data パッケージ等が存在します。詳細はソースコードを参照してください。）

簡易ツリー（抜粋）:
```
src/kabusys/
├─ __init__.py
├─ config.py
├─ run_execution.py
├─ run_monitoring.py
├─ execution/
├─ monitoring/
├─ portfolio/
├─ research/
├─ ai/
├─ tools/
└─ utils/
```

---

## 開発 / 貢献メモ

- 新しい DB カラム追加時は monitoring_db.init_monitoring_db のマイグレーション処理を拡張してください（現在は一部カラム追加をチェックして自動 ALTER TABLE を行います）。
- OpenAI 呼び出し部分は再現性を考慮してリトライやバックオフ、レスポンスバリデーションが組み込まれています。テスト時は _call_openai_api をモックすることを想定しています。
- 単体テスト・CI を導入する場合、環境変数の自動ロード（.env 読み込み）をオフにするかテスト用 .env を用意してください。

---

必要であれば README に以下の追加を行えます:
- requirements.txt の候補
- .env.example のテンプレート
- 起動時の systemd / supervisor 用 unit ファイル例
- よくあるトラブルシュート（OpenAI エラー、権限関連の psutil エラー等）

どの情報を追加 / 詳細化したいか教えてください。