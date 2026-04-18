# KabuSys

軽量な日本株自動売買 / 研究用フレームワークの一部です。本リポジトリは戦略研究・ポートフォリオ構築・発注実行（本番 / ペーパートレード）・監視・AIによるニュース評価などのユーティリティ群を収めています。

バージョン: 0.1.0

---

## 概要

このプロジェクトは以下を目的としたモジュール群を提供します。

- 株価データや財務データを使ったファクター計算（research）
- ポートフォリオ候補選定・重み算出・ポジションサイズ計算（portfolio）
- 発注実行エンジン（ExecutionEngine） — 本番 / ペーパートレード切替対応
- 監視サブシステム（System / Trade / Risk の監視、Kill Switch）
- ニュースをLLMでスコアリングするAIモジュール（OpenAI連携）
- 各種ツール（envウィザード・設定検証・ペーパートレード検証レポートなど）
- 共通ユーティリティ（ロギング設定、プロセス優先度設定等）

設計方針は「現実の発注系とは分離された分析/検証ロジック」と「起動時の安全ガード（Kill Switch 等）」、および「外部API呼び出しを明示的に制御する（OpenAIキーは明示指定）」です。

---

## 主な機能一覧

- 設定管理・ウィザード
  - `.env` の対話的生成: `kabusys.config_setup`
  - 設定検証 CLI: `kabusys.validate_config`
- 実行・監視
  - ExecutionEngine 起動スクリプト: `kabusys.run_execution`
    - `KABUSYS_ENV=paper_trading` 時は MockBroker を使用し、ペーパートレードDB（data/paper_trading.db）に記録
  - Monitoring ポーリングループ: `kabusys.run_monitoring`
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で変更可（デフォルト 60 秒）
    - 停止はプロジェクトルートの `data/stop_requested.flag` を作成して行う
  - Kill Switch: 監視結果により `data/kill.flag` を書き込み、ExecutionEngine を停止
- 研究／分析
  - ファクター計算（momentum / volatility / value）
  - 将来リターン、IC（Information Coefficient）計算、統計サマリー
- AI（OpenAI）
  - ニュースセンチメントスコアリング（gpt-4o-mini 想定）: `kabusys.ai.news_nlp`
  - 市場レジーム判定（MA200 とマクロニュースを合成）: `kabusys.ai.regime_detector`
- ペーパートレード検証
  - 検証レポート生成スクリプト: `kabusys.tools.paper_verification_report`
- ロギング／プロセス管理
  - 統一的ログ設定: `kabusys.utils.logging_setup`
  - プロセス優先度 / CPU affinity: `kabusys.utils.process_priority`

---

## セットアップ手順（開発環境向け）

1. Python 環境を作成（例: venv）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   ```

2. 必要なライブラリをインストール
   - 最低限の依存 (プロジェクト内で使用している主な外部パッケージ)
   ```bash
   pip install duckdb psutil openai
   ```
   - `PyYAML` は設定ファイル検証オプション（`validate_config` が YAML の中身を確認する場合に必要）
   ```bash
   pip install pyyaml
   ```

   （実際の運用では requirements.txt を用意してください）

3. プロジェクトルートに移動すると `kabusys.config` が自動で `.env` を読み込みます。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

4. 対話式ウィザードで `.env` を作成
   ```bash
   python -m kabusys.config_setup
   ```
   生成後、`python -m kabusys.validate_config` で検証してください。

5. データ／ログ用ディレクトリ
   - デフォルトの DB / ログパスは `.env` で指定できます（指定しない場合のデフォルトは下記参照）。
   - 必要に応じて `data/` と `logs/` ディレクトリを作成してください（ログは自動作成されますが権限次第で失敗するため注意）。

---

## 主要な環境変数（抜粋）

- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール使用時に必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視 DB）ファイルパス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレードの注文約定モード（instant / partial / never / reject、デフォルト: instant）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログ出力先ディレクトリ（デフォルト: logs）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: ExecutionEngine 起動時に kill.flag を自動でクリアするか（0/1、本番では 0 推奨）

注意: 本番（KABUSYS_ENV=live）では kill フラグや自動クリアの設定に十分注意してください。

---

## 使い方（代表的なコマンド）

- 環境ウィザード（.env 作成）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  # 警告も失敗させたい場合
  python -m kabusys.validate_config --strict
  ```

- ExecutionEngine 起動
  - 通常起動（pid / stop フラグは data/ に置かれる）
  ```bash
  python -m kabusys.run_execution
  ```
  - ペーパートレード
  ```bash
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```
  - 停止: プロジェクトルートの `data/stop_requested.flag` を作成すると起動中ループが停止します。
  - Kill Switch（監視により kill.flag が書かれる）を手動で解除したい場合:
    ```bash
    rm -f data/kill.flag
    ```

- Monitoring 起動
  ```bash
  python -m kabusys.run_monitoring
  # ポーリング間隔を変更する例（秒）
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

- Paper Trading 検証レポート
  ```bash
  # デフォルトDBを使用
  python -m kabusys.tools.paper_verification_report
  # 期間指定
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を明示
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- AI モジュールを使う（例: レジーム判定 / ニューススコア）
  - OpenAI API キーが必要:
    ```bash
    export OPENAI_API_KEY="sk-xxxx"
    ```
  - コード内 API 呼び出しは関数引数でキーを渡すことも可能（テストや一時キー切替に便利）。

---

## 運用上の注意

- 本番（live）環境では `KILL_FLAG_CLEAR_ON_START` を `0` にしておくことを推奨します。誤って Kill Switch を自動クリアすると重要な停止信号を見落とす恐れがあります。
- `data/stop_requested.flag` を作成すると run_monitoring/run_execution のメインループが穏やかに停止します（安全なシャットダウン手段）。
- ExecutionEngine は `data/execution.pid` に PID を書きます。複数起動や重複起動に注意してください。
- AI 関連の呼び出しは API 利用料が発生します。バッチサイズや文字数制限（ソースコード内に定義あり）を確認してください。
- DuckDB / SQLite のファイルパスは `.env` で指定できます。運用上はバックアップや権限、ディスク容量の監視を行ってください。
- `validate_config` は起動前チェックに便利です。CI に組み込むと安全です。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数 / 設定読み込みロジック
  - config_setup.py            — .env 対話ウィザード
  - validate_config.py         — 起動前設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — Monitoring ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py  — ペーパートレード検証レポート
  - ai/
    - news_nlp.py              — ニュース NLP（OpenAI）スコアリング
    - regime_detector.py       — レジーム判定（MA200 + マクロニュース）
  - monitoring/
    - monitoring_db.py         — SQLite 永続化（監視用テーブル）
    - system_monitor.py
    - trade_monitor.py         — （存在するが本READMEでは要約）
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py         —（存在するが本READMEでは要約）
  - execution/
    - execution_engine.py      — 実行エンジン本体（EngineConfig, run_session 等）
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
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

- data/    — 実行時に使用するファイル群（DB、pid、flag など）
- logs/    — ログ出力先（デフォルト）

簡易ツリー例（プロジェクトルート）
```
.
├─ src/
│  └─ kabusys/
│     ├─ ai/
│     ├─ monitoring/
│     ├─ execution/
│     ├─ portfolio/
│     ├─ research/
│     └─ utils/
├─ data/
└─ logs/
```

---

## 追加情報 / 開発メモ

- データ鮮度チェックや監視は DuckDB / prices_daily 等のテーブルに依存します。実行前に必要なデータ投入・ETLを行ってください（`kabusys.data.pipeline` などのモジュール参照）。
- `monitoring_db.init_monitoring_db` はテーブル作成と簡易マイグレーションを行います。既存 DB に対して冪等に実行可能です。
- OpenAI 呼び出し部分は外部API依存のためテスト時にはモック化（patch）が推奨されています。コード内でもモック差し替えを想定した設計になっています。
- `validate_config` は PyYAML が無ければ YAML パース検証をスキップします（警告出力）。

---

必要であれば README にサンプル .env テンプレート、より詳しい発注フロー図、ExecutionEngine の API（メソッド呼び出しや設定パラメータの詳細）、あるいは CI 用の簡単なチェック手順を追加します。どの情報を優先的に追記しますか？