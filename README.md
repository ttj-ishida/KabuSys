# KabuSys

日本株向けのデータ基盤・リサーチ・自動売買支援ライブラリです。  
J-Quants / RSS / OpenAI 等と連携してデータ収集（ETL）、品質チェック、特徴量計算、ニュースセンチメント評価、マーケットレジーム判定、監査ログ（発注追跡）などを提供します。

バージョン: 0.1.0

---

## 主な特徴

- データ取得（J-Quants）
  - 株価日足（OHLCV）、財務データ、上場銘柄情報、JPXカレンダー取得（ページネーション・レート制御・トークン自動リフレッシュ）
- ETLパイプライン
  - 差分取得、バックフィル、品質チェック（欠損・スパイク・重複・日付不整合）
  - 日次ETLエントリポイント（run_daily_etl）
- ニュース収集＆NLP
  - RSS からの記事収集（SSRF対策・URL正規化）
  - OpenAI（gpt-4o-mini）を使った銘柄単位ニュースセンチメント（score_news）
  - マクロニュース + ETF (1321) の MA を合成した市場レジーム判定（score_regime）
- 研究（Research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（スピアマン）、統計サマリー、z-score 正規化
- 監査ログ（Audit）
  - signal_events / order_requests / executions 等の冪等・トレーサビリティ対応スキーマ初期化ユーティリティ（init_audit_schema / init_audit_db）
- 設定管理
  - 環境変数または .env / .env.local からの自動読み込み（プロジェクトルート検出、上書きルール）

---

## 必要な環境（目安）

- Python 3.10+
- 主な依存ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリを多用していますが、ネットワーク・DB・OpenAI 連携のため上記等が必要になります）

（実際の requirements.txt はプロジェクトに合わせて作成してください）

---

## セットアップ手順

1. リポジトリをクローン／配置

2. 仮想環境作成・有効化（例）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 依存パッケージをインストール
   （プロジェクトに requirements.txt / pyproject.toml があればそちらを使用）
   ```bash
   pip install duckdb openai defusedxml
   ```

4. 環境変数を用意
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（既定の読み込み順: OS 環境変数 > .env.local > .env）。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

5. 重要な環境変数（必須 / 推奨）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime の利用時）
   - KABU_API_PASSWORD: kabuステーション API パスワード（発注系がある場合）
   - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知（必要に応じて）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
   - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT: 監視設定
   - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL: DEBUG/INFO/...（デフォルト: INFO）

6. DB 初期化（監査ログ等）
   - 監査用 DB を初期化する例:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```
   - 既存の DuckDB 接続に監査スキーマを追加する:
     ```python
     from kabusys.data.audit import init_audit_schema
     import duckdb
     conn = duckdb.connect("data/kabusys.duckdb")
     init_audit_schema(conn, transactional=True)
     ```

---

## 使い方（主要ユーティリティ例）

以下は Python から呼び出す基本的な使い方例です。すべて DuckDB 接続（duckdb.connect）を受け取る関数が多く、テストや運用で柔軟に使えます。

- 日次 ETL を実行する
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースのスコアリング（OpenAI 必須）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print("書き込み銘柄数:", n_written)
  ```

- 市場レジーム判定（1321 + マクロニュース）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 研究系関数例（ファクター計算）
  ```python
  from kabusys.research.factor_research import calc_momentum
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, date(2026, 3, 20))
  ```

- 設定参照
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path, settings.env, settings.log_level)
  ```

---

## .env 読み込みの挙動

- プロジェクトルートの判定はパッケージの位置から行われ、`.git` または `pyproject.toml` を基準に探索します（CWD に依存しません）。
- 読み込み順と優先度:
  1. OS 環境変数（最優先）
  2. .env.local（存在すれば上書き）
  3. .env（未設定のキーにのみ設定）
- 自動読み込みを無効化する:
  - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定することで自動ロードを無効化できます（テスト時に便利）。

---

## ディレクトリ構成（主なファイル・モジュール）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数・設定管理（Settings）
  - ai/
    - __init__.py
    - news_nlp.py         — ニュースセンチメント（OpenAI）と score_news
    - regime_detector.py  — 市場レジーム判定（ETF 1321 MA + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py   — J-Quants API クライアント（取得 / 保存）
    - pipeline.py         — ETL パイプライン（run_daily_etl 等）
    - etl.py              — ETLResult の再エクスポート
    - calendar_management.py — 市場カレンダー管理 / 営業日判定
    - news_collector.py   — RSS 収集・前処理・保存
    - stats.py            — 統計ユーティリティ（z-score）
    - quality.py          — データ品質チェック（欠損/スパイク/重複/日付不整合）
    - audit.py            — 監査ログテーブル作成・初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py  — Momentum/Volatility/Value 計算
    - feature_exploration.py — 将来リターン / IC / summary / rank 等
  - ai/ や research/ はリサーチ・実験用途の関数も含む（本番発注ロジックと分離）

---

## 注意事項 / 設計上のポイント

- ルックアヘッドバイアス対策:
  - 多くのモジュール（news_nlp, regime_detector, pipeline 等）は内部で datetime.today() を無闇に参照せず、外部から target_date を渡して利用する設計です。バックテスト用途では必ず過去の date を指定してください。
- OpenAI 使用:
  - score_news / score_regime は OpenAI API（gpt-4o-mini）を使用します。API のエラーはフェイルセーフとしてスコアを 0 や空スキップにフォールバックする設計ですが、APIキーの設定・コスト管理に注意してください。
- J-Quants API:
  - rate limit（120 req/min）を守るためにクライアントでスロットリングと再試行ロジックを実装しています。401 は自動リフレッシュされるので、JQUANTS_REFRESH_TOKEN の管理に注意してください。
- DuckDB 互換性:
  - DuckDB の executemany の挙動や型バインドの差異（バージョン依存）に配慮した実装を行っています。

---

## 開発 / テストのヒント

- 各種外部呼び出し（OpenAI / J-Quants / HTTP）はモジュール内部で分離されており、ユニットテスト時は該当関数を patch / mock して差し替え可能です（例: kabusys.ai.news_nlp._call_openai_api をモック）。
- デバッグ時は LOG_LEVEL を DEBUG に設定すると詳細ログが得られます。

---

README に含める追加項目（例）：セットアップ用 requirements.txt、運用用の systemd ユニット例、Slack 通知の利用法、CI/CD テスト手順など。必要であれば追記します。