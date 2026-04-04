# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けのデータプラットフォーム兼自動売買（バックテスト / リサーチ / 実行）補助ライブラリです。J-Quants / kabuステーション / OpenAI 等と連携して、データ取得（ETL）、ニュースセンチメント評価（LLM）、ファクター計算、監査ログなどを提供します。

---

目次
- プロジェクト概要
- 主な機能
- 前提条件 / 依存関係
- セットアップ手順
- 環境変数（.env）と設定
- よく使う使い方（コード例）
- ディレクトリ構成（主要ファイル説明）
- テスト・デバッグのヒント

---

## プロジェクト概要

このライブラリは以下の役割を担います。

- J-Quants API から株価日足・財務・市場カレンダーを差分取得して DuckDB に保存する ETL パイプライン
- RSS ニュース収集 → OpenAI（gpt-4o-mini）を利用した銘柄ごとのニュースセンチメントスコア算出
- ETF（1321）200日移動平均乖離とマクロニュースを合成する市場レジーム判定（bull/neutral/bear）
- ファクター計算（モメンタム・バリュー・ボラティリティ等）と特徴量解析ユーティリティ
- 監査ログ（signal / order_request / execution）用のスキーマ初期化ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）機能

設計上の特色として、ルックアヘッドバイアス防止、堅牢なリトライ・フェイルセーフ、DuckDB への冪等保存を重視しています。

---

## 主な機能一覧

- ETL
  - run_daily_etl: 市場カレンダー → 株価 → 財務 → 品質チェック の一括処理
  - 個別ジョブ: run_prices_etl / run_financials_etl / run_calendar_etl
- データ取得クライアント（jquants_client）
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar, fetch_listed_info
  - save_daily_quotes / save_financial_statements / save_market_calendar（DuckDB への冪等保存）
- ニュース処理（news_collector）
  - RSS フィード取得・前処理・raw_news 保存を想定
- ニュース NLP（ai.news_nlp）
  - score_news: 銘柄ごとの ai_score を OpenAI で算出し ai_scores テーブルへ格納
- 市場レジーム判定（ai.regime_detector）
  - score_regime: ETF 1321 の ma200 乖離とマクロニュース LLM スコアを合成して market_regime に保存
- 研究用ユーティリティ（research）
  - calc_momentum / calc_value / calc_volatility
  - calc_forward_returns / calc_ic / factor_summary / rank
  - zscore_normalize（data.stats）
- データ品質（data.quality）
  - check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks
- 監査ログ（data.audit）
  - init_audit_schema / init_audit_db: 監査用テーブルを初期化

---

## 前提条件 / 依存関係

- Python >= 3.10（型ヒントに `X | None` 等を使用）
- 必須ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
- その他（用途に応じて）
  - requests（本実装は urllib を使っていますが、プロジェクトで追加する可能性あり）
  - 標準ライブラリ：urllib, json, datetime, logging 等

依存は setup.py / pyproject.toml にまとめている想定です。開発環境では virtualenv / venv を推奨します。

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成して有効化する。

   ```bash
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   # .venv\Scripts\activate    # Windows
   ```

2. 必要パッケージをインストールする（例: pip）。

   ```bash
   pip install -U pip
   pip install duckdb openai defusedxml
   # 開発用にソースを編集して利用する場合:
   pip install -e .
   ```

3. 環境変数を用意する（下記「環境変数」を参照）。リポジトリルートに .env を置くと自動で読み込まれます（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

4. DuckDB データベース等のディレクトリを作成する（必要なら）。

   デフォルト:
   - DuckDB: data/kabusys.duckdb
   - SQLite（監視用）: data/monitoring.db

---

## 環境変数（.env の例）

設定は環境変数から読み取られ、.env / .env.local をプロジェクトルートから自動読み込みします。

重要な環境変数（最小限）:

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須、ETL 実行に必要）
- KABU_API_PASSWORD: kabuステーション API パスワード（発注連携を行う場合）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector が必要な場合）

任意 / 設定可能:

- KABUSYS_ENV: development / paper_trading / live（デフォルト development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
- DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
- SQLITE_PATH: data/monitoring.db
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START / CPU_THRESHOLD_PCT 等（監視用）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（LINE 通知を使う場合）

例 (.env):

    JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
    OPENAI_API_KEY=sk-...
    KABU_API_PASSWORD=your_kabu_password
    KABUSYS_ENV=development
    LOG_LEVEL=INFO
    DUCKDB_PATH=data/kabusys.duckdb

注意: .env の読み込みはプロジェクトルートにある .git または pyproject.toml を検出して行います。自動読み込みを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 使い方（よく使う例）

以下は Python シェルやスクリプトでの利用例です。適宜 logging 設定やエラーハンドリングを追加してください。

- DuckDB 接続を作る

```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行する（J-Quants のトークンは settings から自動取得）

```python
from kabusys.data.pipeline import run_daily_etl

# target_date を指定しない場合は今日（設定により営業日調整あり）
result = run_daily_etl(conn)
print(result.to_dict())
```

- ニュースセンチメントをスコアリングして ai_scores に書き込む

```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# target_date はスコア生成日（JST基準の「当日」）
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込んだ銘柄数:", n_written)
```

- 市場レジーム（daily）を判定して market_regime に書き込む

```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用 DB を初期化する

```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# 以後 audit_conn を使って監査ログ操作を行う
```

- 監査スキーマを既存接続へ追加（トランザクション指定可能）

```python
from kabusys.data import audit

audit.init_audit_schema(conn, transactional=True)
```

---

## 主要モジュールとディレクトリ構成

パッケージルート: src/kabusys/

主要ファイル・モジュール:

- __init__.py
  - パッケージエクスポート: data, strategy, execution, monitoring（strategy 等は将来の拡張を想定）
- config.py
  - 環境変数自動読み込み (.env/.env.local)、Settings クラス（settings）
- ai/
  - __init__.py (score_news をエクスポート)
  - news_nlp.py: ニュースの LLM による銘柄スコア算出（score_news）
  - regime_detector.py: ETF ma200 とニュースを合成する市場レジーム判定（score_regime）
- data/
  - jquants_client.py: J-Quants API クライアント（取得/保存/認証/レート制御）
  - pipeline.py: ETL パイプライン（run_daily_etl 等）と ETLResult
  - news_collector.py: RSS 収集・前処理ロジック
  - calendar_management.py: 市場カレンダー管理（営業日判定など）
  - quality.py: データ品質チェック（欠損/スパイク/重複/日付不整合）
  - stats.py: 共通統計ユーティリティ（zscore_normalize）
  - audit.py: 監査ログスキーマ / 初期化ユーティリティ
  - etl.py: ETLResult の再エクスポート
- research/
  - factor_research.py: ファクター計算（momentum/value/volatility）
  - feature_exploration.py: 将来リターン計算・IC・統計サマリー
  - __init__.py: 研究用ユーティリティのエクスポート

（上記に加え strategy / execution / monitoring 用のモジュールが将来的に含まれる想定）

---

## テスト・デバッグのヒント

- OpenAI / 外部 API 呼び出しはテスト時にモックする想定です。
  - news_nlp._call_openai_api や regime_detector._call_openai_api を unittest.mock.patch で差し替えてテストを行えます。
- .env 自動読み込みを無効にする: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- DuckDB のテーブル状態を整えるために、開発時は :memory: 接続や一時ファイルを利用できます。
- jquants_client._request はリトライ・レート制御実装済みですが、API キーやネットワークの問題はログと例外で検知できます。ログレベルを DEBUG にすると詳細が見えます。

---

## 注意事項 / セキュリティ

- .env に API キーやトークンを平文で置く場合は、リポジトリに含めない（.gitignore に追加）。
- news_collector は SSRF 対策（ホスト検査・リダイレクト時検査）・受信サイズ制限・XML パーサ防備を実装していますが、外部入力を扱う際は常に注意してください。
- 実売買・ライブ環境で使用する場合は KABUSYS_ENV を `live` に設定し、十分な監査とバックテストを行ってください。

---

必要であれば README に次の内容を追加できます:
- API（関数）別の詳細リファレンス
- 実運用のデプロイ手順（systemd / cron / コンテナ化）
- CI / テスト実行方法（pytest など）
- .env.example（サンプルファイル）

必要な追加項目を教えてください。