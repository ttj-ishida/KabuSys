# KabuSys

日本株向け自動売買システムのユーティリティ / ライブラリ群。  
このリポジトリは取引エンジン起動スクリプト、監視（Monitoring）コンポーネント、ポートフォリオ構築・サイズ計算、ファクター計算（研究用）、および OpenAI を使ったニュース NLP / レジーム判定などを含みます。

---

## 概要

- 実運用を考慮した設計（プロセス優先度設定、ログローテーション、Kill Switch、監視テーブル等）。
- DuckDB（分析用）と SQLite（監視 / ペーパートレードログ）を併用。
- 環境毎の挙動切替（開発 / ペーパートレード / 本番）。
- OpenAI を利用したニュースセンチメント評価および市場レジーム判定モジュールを備える（APIキー必要）。
- 研究用ファクター計算、ポートフォリオ構成、ポジションサイズ計算等は純粋関数として分離されテストしやすい設計。

---

## 主な機能一覧

- 起動スクリプト
  - run_execution.py — ExecutionEngine 起動（KABUSYS_ENV に応じて実ブローカ or MockBroker）
  - run_monitoring.py — SystemMonitor ポーリングループ起動
- 環境設定・検証
  - config_setup.py — .env 対話式ウィザード（.env 作成 / 更新）
  - validate_config.py — 起動前の設定検証 CLI
- 監視 / 安全機構
  - monitoring_engine.py — 各 Monitor（System / Trade / Risk）を束ねる
  - kill_switch.py — kill.flag による ExecutionEngine 停止シグナル
  - risk_monitor.py — ドローダウン / ポジション数上限監視
  - monitoring_db.py — SQLite テーブル定義および永続化 API
- ポートフォリオ構築
  - portfolio/portfolio_builder.py — 候補選定・重み計算
  - portfolio/position_sizing.py — 発注株数計算（リスクベース等）
  - portfolio/risk_adjustment.py — セクターキャップ、レジーム乗数
- 研究用 / 分析
  - research/factor_research.py — モメンタム / ボラティリティ / バリュー計算（DuckDB）
  - research/feature_exploration.py — 将来リターン、IC、統計サマリ
- AI（OpenAI）
  - ai/news_nlp.py — ニュースを集約して LLM で銘柄別センチメント算出 → ai_scores へ保存
  - ai/regime_detector.py — ETF + マクロニュースを用いた市場レジーム判定
- ツール
  - tools/paper_verification_report.py — ペーパートレード DB を解析して検証レポートを作成
- ユーティリティ
  - utils/logging_setup.py — 共通ログ設定（stdout + 日次ローテートファイル）
  - utils/process_priority.py — プロセス優先度 / CPU affinity 設定
  - config.py — 環境変数 / 設定値取りまとめ

---

## 必要要件

- Python 3.10+
- 依存パッケージ（代表例）
  - duckdb
  - psutil
  - openai
  - （任意）PyYAML（config 検証で YAML の中身チェックを行う場合）
- OS: Linux / macOS / Windows（プロセス優先度の挙動は OS に依存）

インストール例（仮想環境推奨）:
```
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```
（requirements.txt がない場合は必要なパッケージを個別にインストールしてください:
`pip install duckdb psutil openai pyyaml`）

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動。

2. Python 仮想環境を作成・有効化して依存パッケージをインストール。

3. .env の作成（対話式ウィザード推奨）:
```
python -m kabusys.config_setup
```
ウィザードで J-Quants / kabuAPI のトークン、KABUSYS_ENV（development|paper_trading|live）等を設定します。

最小例（手動で .env を作る場合）:
```
JQUANTS_REFRESH_TOKEN=your_token
KABU_API_PASSWORD=your_password
KABUSYS_ENV=development
```

4. 設定検証:
```
python -m kabusys.validate_config
# 警告をエラー扱いする strict モード:
python -m kabusys.validate_config --strict
```

5. データディレクトリの作成（デフォルトパスを使用する場合）:
- デフォルト DuckDB: data/kabusys.duckdb
- デフォルト monitoring SQLite: data/monitoring.db
- ログディレクトリ: logs/

logging_setup が起動時にログディレクトリを自動生成しますが、権限等で失敗する場合は手動で作成してください。

---

## 使い方

### 環境変数（主要）

- KABUSYS_ENV: "development" | "paper_trading" | "live"（デフォルト: development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（paper_trading 時に使用。デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- OPENAI_API_KEY: OpenAI API キー（ai モジュール利用時に必要）
- PAPER_FILL_MODE: ペーパー取引時の約定挙動 ("instant"|"partial"|"never"|"reject")
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒。デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: ExecutionEngine 起動時に kill.flag を自動クリアするか ("0" または "1")。本番は 0 推奨。

### 起動 / 停止

- ExecutionEngine を起動（通常はデーモン/サービスとして実行）:
```
python -m kabusys.run_execution
```
- Monitoring を起動:
```
python -m kabusys.run_monitoring
```
- 停止方法:
  - プロセスを終了（Ctrl+C または Systemd 停止等）。
  - 外部から停止フラグを書き込む: プロジェクトの data/stop_requested.flag（run_* スクリプトはこのフラグを検知してループ終了します）。
  - Execution 停止要求（Kill Switch）: data/kill.flag を作成すると ExecutionEngine に停止シグナルを送る仕組み（KillSwitch が監視・書き込みを行う）。

- run_execution の挙動:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して `data/paper_trading.db` に記録（本番 DB とは完全に分離）。
  - PID ファイル: data/execution.pid（設定で上書き可）

- run_monitoring の挙動:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。
  - 監視は環境に関わらず本番 sqlite_path を参照して監視ログを永続化します。

### 監視 / Kill Switch / ログ

- 監視 DB（SQLite）は monitoring_db.init_monitoring_db によって必要テーブルが作成されます。
- kill.flag の存在は Execution 停止を意味するため、本番環境では KILL_FLAG_CLEAR_ON_START=0 にすることを推奨します。
- ログは stdout と logs/<app_name>.log（日次ローテーション、30日保持）に出力されます。

### ツール: Paper Trading レポート

ペーパートレード実行結果の検証レポートを生成:
```
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# DB パスを明示する場合:
python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
```
このツールは稼働率、注文成功率、レイテンシ等を集計して PASS/FAIL を判定します。

### AI モジュール（OpenAI）

- ニュースセンチメント集計:
  - プログラムから呼ぶ場合:
    from kabusys.ai import score_news
    score_news(conn, target_date, api_key="...")

- レジーム判定:
  - from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date, api_key="...")

いずれも OpenAI API キー（OPENAI_API_KEY 環境変数または引数）が必要です。API 呼び出しはリトライやエラー時のフォールバックを組み込んでありますが、API 利用料・レート制限に注意してください。

---

## 主要ファイル / ディレクトリ構成

（src/kabusys 以下の主要要素を抜粋）

- kabusys/
  - __init__.py
  - config.py                — 環境変数/設定管理（自動 .env ロード機能含む）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - utils/
    - logging_setup.py       — 共通ログ設定
    - process_priority.py    — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py       — SQLite テーブル定義 / 永続化 API
    - system_monitor.py      — システム状態 / データ鮮度監視
    - trade_monitor.py       — （trade 関連監視, 記録）
    - risk_monitor.py        — ドローダウン / ポジション制限監視
    - kill_switch.py         — kill.flag 書き込み / 評価
    - monitoring_engine.py   — 各 Monitor をまとめる
    - alert_manager.py       — （アラート）※アラート実装がここにある想定
  - execution/               — ExecutionEngine / 注文管理等（別ファイル群）
  - portfolio/
    - portfolio_builder.py   — 候補選定 / 重み計算
    - position_sizing.py     — 発注株数計算
    - risk_adjustment.py     — セクターキャップ / レジーム乗数
  - research/
    - factor_research.py     — Momentum / Volatility / Value 等の計算（DuckDB）
    - feature_exploration.py — 将来リターン / IC / 統計
  - ai/
    - news_nlp.py            — ニュースを LLM でスコアリングして ai_scores へ保存
    - regime_detector.py     — ETF MA + マクロニュースでレジーム判定
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート

（開発時は src/ を PYTHONPATH に含めて実行すること。`python -m kabusys....` 形式推奨）

---

## 開発者向けメモ / 注意点

- .env は機密情報を含むため Git にコミットしないでください（config_setup が警告します）。
- KABUSYS_ENV:
  - development: ローカル実行・テスト向け（発注抑止の運用が期待される）
  - paper_trading: MockBrokerClient を使い paper DB に記録（本番 DB と分離）
  - live: 本番
- PAPER_FILL_MODE（paper_trading 用）: "instant", "partial", "never", "reject" のいずれか
- MONITOR はデフォルトで実運用の sqlite_path（Settings.sqlite_path）を使用します。監視ログは環境にかかわらず同じ DB に蓄積される設計です。
- ローカル / CI 環境で自動的に .env をロードする機能を持ちます（config.py）。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI の呼び出しをテストする場合は内部の API 呼び出し関数（_kabusys.ai.news_nlp._call_openai_api など）をパッチしてモックすることを推奨します。

---

## トラブルシューティング

- ログファイルが作成されない:
  - logs/ ディレクトリの作成権限や指定した LOG_DIR 環境変数を確認してください。
- DB 作成・マイグレーションに失敗する:
  - sqlite ファイルの親ディレクトリが存在するか、ファイル権限を確認してください。monitoring_db.init_monitoring_db は冪等です。
- OpenAI 呼び出しで失敗が続く:
  - OPENAI_API_KEY と API 利用枠、ネットワークアクセス（プロキシ等）を確認してください。news_nlp/regime_detector はリトライ実装がありますが、API制限は回避できません。

---

README は以上です。実行方法・環境変数の細かい取り扱いは各モジュール内の docstring および config.py を参照してください。必要なら README に含めるコマンド例や .env.example のテンプレートを追加で生成します。どの情報を追加しますか？