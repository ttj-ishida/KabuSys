# KabuSys

日本株向け自動売買システムのサンプル実装（ライブラリ＋運用スクリプト群）。

この README はリポジトリ内の主要モジュールを元に自動売買／監視／リサーチ／AI 補助機能の使い方とセットアップ手順をまとめたものです。

---

## プロジェクト概要

KabuSys は以下を目的としたコンポーネント群を含みます。

- 実行エンジン（ExecutionEngine）: ブローカークライアント経由で発注・注文管理・リスク管理を行う。
- 監視（Monitoring）: システム状態・注文滞留・リスク（ドローダウン等）を定期的にチェックし、kill flag で ExecutionEngine を安全停止させる。
- ポートフォリオ構築: 候補選定、重み計算、ポジションサイズ計算、セクター制限などの純粋関数群。
- リサーチ: DuckDB を使ったファクター計算、特徴量探索、IC 計算など。
- AI 支援: OpenAI を用いたニュースセンチメント評価（銘柄単位）、市場レジーム判定。
- ツール: ペーパートレード検証レポート等のユーティリティスクリプト。

設計方針のポイント:
- 本番 DB とペーパートレード DB は分離（KABUSYS_ENV=paper_trading の場合は data/paper_trading.db を使用）。
- 各モジュールはルックアヘッドバイアスを避ける実装（date.today() を直接参照しない等）。
- フェイルセーフ重視（外部 API 失敗時はスキップやフォールバック処理を行う）。

---

## 主な機能一覧

- 実行関連
  - ExecutionEngine の起動スクリプト: run_execution.py
  - ブローカークライアントの切り替え（本番 / Mock for paper_trading）

- 監視関連
  - SystemMonitor: CPU / メモリ / ディスク / プロセス状態 / データ鮮度チェック
  - TradeMonitor: 注文滞留、約定価格異常の検出
  - RiskMonitor: ドローダウンやポジション上限アラート
  - KillSwitch: 条件に応じて data/kill.flag を書き込み ExecutionEngine を停止
  - MonitoringEngine / run_monitoring.py: ポーリングループで上記監視を実行

- ポートフォリオ構築
  - 候補選定（スコア/ランキングベース）
  - 等金額・スコア加重・リスクベースのポジションサイズ計算
  - セクター集中制限、レジーム乗数

- リサーチ
  - ファクター（モメンタム／ボラティリティ／バリュー）計算（DuckDB）
  - 将来リターン計算、IC（スピアマン）計算、統計サマリー

- AI（OpenAI）
  - ニュースセンチメントの銘柄単位スコア化（gpt-4o-mini を想定）
  - マクロニュース + 指標で市場レジーム判定

- ツール
  - ペーパートレード検証レポート生成スクリプト（tools/paper_verification_report.py）
  - 対話式 .env 作成ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）

---

## 事前準備（依存関係）

最低限必要な Python パッケージ（例）:
- python >= 3.9
- duckdb
- psutil
- openai
- PyYAML（config YAML のパースは任意だが validate_config はあると詳細検証を行う）

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

（プロジェクトに requirements.txt がある場合はそれを使用してください。）

---

## 環境変数と設定（主なもの）

基本はルートの `.env`（.env.local）または環境変数で設定します。自動ロード機能によりプロジェクトルートが検出されると .env が読み込まれます（テスト時に無効化可: KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。

主な環境変数：
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (監視用、デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB、デフォルト: data/paper_trading.db)
- OPENAI_API_KEY (AI 機能を使う場合)
- LOG_LEVEL (DEBUG/INFO/...)
- KILL_FLAG_CLEAR_ON_START (0/1) — 起動時に kill.flag を自動クリアするか（本番では 0 推奨）
- PAPER_FILL_MODE (paper_trading 用のフィルモード: instant|partial|never|reject)

注意:
- .env は絶対にリポジトリにコミットしないこと。
- validate_config.py を実行して設定漏れや警告を確認してください。

---

## セットアップ手順（推奨フロー）

1. リポジトリをクローンして仮想環境を作る
   ```bash
   git clone <repo>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   pip install duckdb psutil openai PyYAML
   ```

2. .env を作成（対話式ウィザード推奨）
   ```bash
   python -m kabusys.config_setup
   ```
   ウィザード完了後、`.env` が生成されます。

3. 設定検証
   ```bash
   python -m kabusys.validate_config
   # 厳密モード（警告もエラー扱い）:
   python -m kabusys.validate_config --strict
   ```

4. 必要なディレクトリ作成
   - デフォルトでは data/ 以下に DB や PID/フラグファイルが置かれます。適切に作成・書き込み権限を設定してください。
   ```bash
   mkdir -p data
   ```

---

## 実行方法（運用）

- ExecutionEngine 起動（本番 / paper_trading 切替は KABUSYS_ENV）
  ```bash
  # 例: ペーパートレードで起動
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```
  特徴:
  - paper_trading 環境では MockBrokerClient を利用し、data/paper_trading.db に記録（本番 DB と分離）。
  - 起動時に data/stop_requested.flag が存在すると起動しない。
  - 実行中は data/execution.pid に PID を書き、停止時に削除されます（実装側）。

- 監視ループ起動
  ```bash
  # ポーリング間隔 MONITOR_POLL_INTERVAL（秒）を設定可能（デフォルト 60）
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```
  特徴:
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（SQLITE_PATH / data/monitoring.db）を使用して稼働ログを記録します。
  - 停止: data/stop_requested.flag が作成されるとループが検知して終了します。

- 停止 / Kill スイッチ
  - 実行の強制停止指令は data/kill.flag に理由を記入することで行います（KillSwitch がこれを検知すると ExecutionEngine を停止させる仕組み）。
  - run_monitoring / MonitoringEngine はリスク条件を判定し必要に応じて kill.flag を書き込みます。

- ペーパートレード検証レポート
  ```bash
  python -m kabusys.tools.paper_verification_report \
    --from 2026-04-01 --to 2026-04-11 \
    --db data/paper_trading.db
  ```
  デフォルト DB: PAPER_TRADING_SQLITE_PATH 環境変数または data/paper_trading.db。

- AI 機能（ニュース感情・レジーム判定）
  - OPENAI_API_KEY を設定してから呼び出します。モジュール API を直接呼んで使う想定です（例: kabusys.ai.score_news）。
  - score_news は DuckDB 接続と target_date を受け取り ai_scores テーブルへ書き込みます。
  - regime_detector.score_regime も同様に使用できます。

---

## よく使うコマンドまとめ

- .env 作成ウィザード:
  python -m kabusys.config_setup

- 設定検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- 実行エンジン:
  python -m kabusys.run_execution

- 監視ループ:
  MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring

- ペーパートレード検証レポート:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

## ディレクトリ構成（主なファイル / モジュール）

リポジトリの src/kabusys 以下（抜粋）:

- kabusys/
  - __init__.py
  - config.py               — 環境変数読み込み / Settings クラス
  - config_setup.py         — .env 対話式ウィザード
  - validate_config.py      — 起動前設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor ポーリングループ起動
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - ai/
    - news_nlp.py           — ニュースを LLM でスコアリング
    - regime_detector.py    — 市場レジーム判定
  - monitoring/
    - monitoring_db.py      — SQLite 永続化層（監視ログ）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py      — （アラート送信の抽象化、実装ファイル参照）
  - execution/
    - （注文管理、ブローカー抽象など。実装ファイルがある想定）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
  - data/ (実行時に生成される想定）
    - monitoring.db (SQLITE_PATH)
    - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
    - kabusys.duckdb (DUCKDB_PATH)
    - execution.pid
    - kill.flag
    - stop_requested.flag

---

## 運用上の注意 / ベストプラクティス

- Kill Switch / kill.flag
  - 本番環境では KILL_FLAG_CLEAR_ON_START=0 を推奨。誤って Kill Switch をクリアしてしまうと安全機構が無効化される可能性があります。
  - validate_config.py は本番 env=live の場合に警告を出します。警告を無視しないでください。

- DB 分離
  - paper_trading 用 DB は本番 DB と完全に分離されています（PAPER_TRADING_SQLITE_PATH）。ペーパートレードのデータが本番データを汚染することはありません。

- OpenAI API
  - API キーの管理は環境変数（OPENAI_API_KEY）で行ってください。リクエスト失敗時はフォールバックやスキップする設計ですが、API コストとレート制限に注意してください。
  - ニュース NLP はレスポンスを厳密 JSON として期待しており、バリデーションを厳格に行います。

- プロセス優先度
  - 実行スクリプトは開始時に set_process_priority("high") を呼び、重要プロセスとして扱います。OS によっては権限不足で変更できないことがあります（ログ警告が出ます）。

---

必要に応じて、この README をベースに「デプロイ手順」「サンプル .env.example」「systemd ユニットファイル」「運用 runbook」などを追加できます。追加したい項目があれば教えてください。