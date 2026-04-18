# KabuSys — 日本株自動売買システム（README）

以下はこのコードベースの概要および使い方ドキュメントです。

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方
  - 環境設定ウィザード（.env）
  - 設定検証
  - 実行コンポーネント（Execution / Monitoring）
  - ツール（Paper Trading レポート 等）
  - ライブラリ API（研究・AI モジュール呼び出し）
- 主要な環境変数
- 動作上の注意（Paper vs Live 等）
- ディレクトリ構成
- トラブルシューティング（よくある問題と対処）

---

## プロジェクト概要

KabuSys は日本株の自動売買システム向けのツール群です。システム構成要素は取引実行エンジン（ExecutionEngine）、監視モジュール（Monitoring）、ポートフォリオ構築・サイズ決定ルーチン、リサーチ（ファクター計算・特徴量解析）、およびニュースを用いた NLP（OpenAI）によるスコアリング等を含みます。ローカル SQLite / DuckDB を用いたデータ永続化と、環境変数ベースの設定管理で動作します。

主な設計方針：
- 本番（live）とペーパートレード（paper_trading）を切り替え可能
- DuckDB を分析用途、SQLite を監視 / 発注ログ用途に使用
- OpenAI を使ったニュースセンチメントやレジーム判定機能を持つ
- 守備的なフェイルセーフ（API リトライ、部分失敗の保護、Kill Switch）

---

## 機能一覧

- Execution エンジン（run_execution.py）
  - ブローカークライアント抽象化（本番/Mock）
  - 注文管理、リスク管理、照合（reconciler）を含む実行ワークフロー
  - Paper Trading 時は専用 DB に完全分離して記録

- Monitoring（run_monitoring.py / monitoring パッケージ）
  - システムリソース監視（CPU, メモリ, ディスク）
  - データ鮮度チェック（prices_daily 等）
  - 発注・約定ログ監視（滞留注文・約定異常など）
  - リスク監視（ドローダウン、ポジション上限）
  - Kill Switch（条件により data/kill.flag を書き込む）
  - アラート送信（LINE 等。設定があれば）

- Portfolio（portfolio パッケージ）
  - 候補選定（スコア順ソート）
  - 重み計算（等金額 / スコア重み）
  - セクター制限適用、レジーム乗数
  - ポジションサイズ計算（単元丸め、aggregate cap）

- Research（research パッケージ）
  - Momentum / Volatility / Value ファクター計算（DuckDB）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー

- AI（ai パッケージ）
  - ニュース NLP による銘柄センチメント計算（OpenAI）
  - 市場レジーム判定（ETF MA200 + マクロニュース + LLM）

- ユーティリティ
  - .env 対話的生成（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - Paper Trading 検証レポート（tools/paper_verification_report.py）
  - ロギングセットアップ、プロセス優先度設定ユーティリティ 等

---

## セットアップ手順

前提:
- Python 3.9+ 推奨（type hints に依存）
- 必要パッケージ（例）
  - duckdb
  - psutil
  - openai
  - （YAML を検証したい場合）PyYAML

例（venv を作ってパッケージを入れる）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt   # プロジェクトに requirements.txt がある場合
# 必要なパッケージを個別に:
pip install duckdb psutil openai
# （YAML 検証を使うなら）pip install pyyaml
```

設定ファイルの作成（.env）:
```bash
python -m kabusys.config_setup
```
対話的に .env を生成・更新できます。生成後に設定の妥当性を検証します。

設定検証:
```bash
python -m kabusys.validate_config       # 警告は情報として表示
python -m kabusys.validate_config --strict  # 警告があると exit code=1 にする
```

注意:
- OpenAI を使う機能を利用するには `OPENAI_API_KEY` を環境変数（または .env）に設定してください。
- J-Quants / kabuステーション のトークンは必須（`.env` で設定）。

---

## 使い方

### 環境変数（.env）の管理
- 推奨: `python -m kabusys.config_setup` で対話的に作成
- 重要なキー（例）
  - JQUANTS_REFRESH_TOKEN（必須）
  - KABU_API_PASSWORD（必須）
  - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
  - OPENAI_API_KEY（AI 機能を使う場合）
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB）
  - LOG_LEVEL（デフォルト: INFO）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（任意、アラート用）

（下に主要な環境変数一覧をまとめています）

---

### 設定検証
```bash
python -m kabusys.validate_config
```
不足や警告を表示します。--strict を付けると警告も失敗扱いになります。

---

### 実行コンポーネント

Execution（発注エンジン）起動:
```bash
python -m kabusys.run_execution
```
- `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用し、`data/paper_trading.db`（または PAPER_TRADING_SQLITE_PATH）に記録します。
- 実行時に `data/stop_requested.flag`（停止フラグ）があれば起動せず終了します。
- エンジンは `data/execution.pid` を使います（pid ファイルのパスは Settings から変更可能）。

Monitoring（監視ループ）起動:
```bash
# ポーリング間隔を環境変数で上書き（秒）
export MONITOR_POLL_INTERVAL=30
python -m kabusys.run_monitoring
```
- デフォルトのポーリング間隔は 60 秒。MONITOR_POLL_INTERVAL 環境変数で上書き可能（1 秒以上）。
- 監視は本番 sqlite_path（Settings.sqlite_path）を使います（環境に依らず本番 DB を参照する設計）。
- `data/stop_requested.flag` の存在を検知するとループを終了します。

Paper Trading 検証レポート生成:
```bash
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# DB パスを明示したい場合
python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
```

---

### ライブラリ API（プログラムからの呼び出し）
- 研究系:
  - kabusys.research.calc_momentum / calc_volatility / calc_value
  - kabusys.research.calc_forward_returns, calc_ic, factor_summary
  - 例: DuckDB 接続を作成し、関数を呼ぶ

- AI 系:
  - kabusys.ai.score_news(conn, target_date, api_key=None) — ニュース NLP スコアを ai_scores テーブルへ書き込む
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None) — 市場レジーム判定
  - OpenAI API キーは引数で渡すか、環境変数 OPENAI_API_KEY を使います。

注意: これらは DuckDB 接続（duckdb.connect(...)）を受け取り、データベース上のテーブル（prices_daily, raw_news, ai_scores, market_regime 等）を参照/更新します。

---

## 主要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合）
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
  - is_paper / is_live により挙動が変わる
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用の SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- LOG_DIR — ログ出力ディレクトリ（デフォルト logs/）
- PID_FILE_PATH — 実行時の PID ファイル（デフォルト data/execution.pid）
- KILL_FLAG_PATH — Kill Switch フラグファイル（デフォルト data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1。production では 0 推奨）
- PAPER_FILL_MODE — ペーパートレード時の約定モード（instant/partial/never/reject）

---

## 動作上の注意

- Paper Trading と Live は DB を分離する設計です。Paper 用 DB（PAPER_TRADING_SQLITE_PATH）を用いることで本番データと完全に分離できます。
- Monitoring は監視用 DB（Settings.sqlite_path）を常に使用します（run_monitoring は KABUSYS_ENV に依らず本番 sqlite_path を参照するため運用注意）。
- Kill Switch: risk 条件（ドローダウンや保有上限）に応じて `data/kill.flag` が書き込まれ、実行エンジンの停止トリガーになります。KILL_FLAG_CLEAR_ON_START は誤って本番で自動クリアしない設定（0）を推奨します。
- OpenAI 利用時は API 利用料が発生します。モデルはコード内で gpt-4o-mini を指定しています（変更可能）。
- プロセス優先度設定は psutil を用います。権限不足やプラットフォーム違い（Windows/Linux）により設定が失敗する場合がありますが、失敗時は警告ログに留まり動作は継続します。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py — 設定読み込み・Settings クラス
- config_setup.py — .env 対話式ウィザード
- validate_config.py — 設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor ポーリング起動スクリプト

パッケージ別主要モジュール:
- ai/
  - news_nlp.py — ニュース NLP スコアリング（OpenAI）
  - regime_detector.py — 市場レジーム判定（MA200+LLM）
- monitoring/
  - monitoring_db.py — SQLite 永続化レイヤ（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py — システム状態・データ鮮度監視
  - risk_monitor.py — ドローダウン / ポジション上限監視
  - trade_monitor.py — （trade 関連監視、滞留注文等）※実装ファイルあり
  - monitoring_engine.py — 各 Monitor を束ねるエンジン
  - kill_switch.py — フラグファイル管理
  - alert_manager.py — アラート送信（LINE 等）※実装ファイルあり
- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 発注株数計算
  - risk_adjustment.py — セクター上限・レジーム乗数
- research/
  - factor_research.py — Momentum / Volatility / Value 等
  - feature_exploration.py — 将来リターン・IC・統計サマリ
- utils/
  - logging_setup.py — ログ設定ユーティリティ
  - process_priority.py — プロセス優先度・CPU affinity
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成

補助ファイル:
- data/ — 実行時に生成される SQLite / PID / flag 等（デフォルト）
- logs/ — ログファイル（TimedRotatingFileHandler による日次ローテーション）

---

## トラブルシューティング（よくある問題）

1. 依存パッケージが不足して `ImportError` が出る
   - duckdb, psutil, openai, pyyaml（config の YAML 検証を使う場合）を pip でインストールしてください。

2. OpenAI 関連のエラー
   - `OPENAI_API_KEY` を設定してください。API のネットワーク問題や 429 は内蔵のリトライロジックでハンドルしますが、レートが高いと失敗することがあります。

3. ログファイルが作れない
   - 権限やログディレクトリ（LOG_DIR）の作成に失敗するとファイルハンドラは無効化されコンソール出力のみになります。ログディレクトリの権限を確認してください。

4. run_execution がすぐ終了する
   - `data/stop_requested.flag` が存在すると起動しません。また KILL_FLAG_CLEAR_ON_START の設定によっては起動時に kill.flag が自動でクリアされるかどうかが変わります（本番では 0 推奨）。

5. Monitoring が本番 DB を参照してしまう
   - 仕様として Monitoring は KABUSYS_ENV に関係なく Settings.sqlite_path（本番の監視 DB）を使用します。テスト用に別 DB にしたい場合は Settings の環境変数を明示的に変更してください。

---

この README はこのリポジトリの主要な利用フローと注意点をまとめたものです。各モジュール（例えば ai/news_nlp.py、research/factor_research.py、monitoring/*.py 等）には詳細な docstring と設計方針コメントが含まれています。必要に応じて該当ファイルを参照してください。

何か追加で README に入れたい情報（例: サンプル .env.example、CI/デプロイ手順、ユニットテストの実行方法 等）があれば教えてください。