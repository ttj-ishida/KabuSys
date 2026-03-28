# KabuSys

日本株向けの自動売買・データパイプラインライブラリです。  
J-Quants や RSS、OpenAI（LLM）を組み合わせてデータ収集、品質チェック、ファクター計算、ニュースセンチメントの算出、監査ログ管理までを行うことを目的としています。

---

## プロジェクト概要

KabuSys は次の主要コンポーネントを含みます。

- データ収集・ETL（J-Quants からの株価、財務、マーケットカレンダー取得）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- ニュース収集（RSS）とニュースベースの NLP スコアリング（OpenAI）
- 市場レジーム判定（ETF の MA とマクロニュースを LLM で評価）
- 監査ログ（シグナル → 発注 → 約定のトレース可能化）
- 研究用ユーティリティ（ファクター算出、将来リターン、IC 計算、Z スコア正規化 等）

設計上の特徴：
- DuckDB を用いたローカル・軽量データストア
- ETL / 保存は冪等（ON CONFLICT / INSERT … DO UPDATE）を志向
- API 呼び出しはレート制御・リトライ・バックオフを備える
- ルックアヘッドバイアスを避けるため時間参照設計に注意
- LLM 結果は JSON モードで取得し厳密にバリデーション

---

## 主な機能一覧

- ETL:
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（kabusys.data.pipeline）
  - J-Quants クライアント（kabusys.data.jquants_client）
- データ品質:
  - 欠損・重複・スパイク・日付不整合チェック（kabusys.data.quality）
- ニュース:
  - RSS 収集（kabusys.data.news_collector）
  - ニュースセンチメント（kabusys.ai.news_nlp.score_news）
- レジーム判定:
  - 市場レジーム判定（kabusys.ai.regime_detector.score_regime）
- 研究用:
  - モメンタム／ボラティリティ／バリュー等のファクター計算（kabusys.research）
  - Zスコア正規化（kabusys.data.stats.zscore_normalize）
- 監査:
  - 監査スキーマ初期化・監査DB生成（kabusys.data.audit.init_audit_schema / init_audit_db）
- 環境設定:
  - .env / 環境変数の自動ロードと Settings API（kabusys.config.settings）

---

## 必要条件（依存）

主な Python パッケージ（抜粋）：
- python >= 3.10（型注釈に union の短縮表記等を使用）
- duckdb
- openai（OpenAI Python SDK）
- defusedxml

（パッケージ化時には `pyproject.toml` / requirements に依存関係を明記してください）

---

## セットアップ手順

1. リポジトリをクローンして編集モードでインストール（開発向け）:
   ```
   git clone <repo_url>
   cd <repo_root>
   pip install -e .
   ```

2. 依存パッケージをインストール（例）:
   ```
   pip install duckdb openai defusedxml
   ```

3. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を置くと、自動で読み込まれます（優先度: OS 環境変数 > .env.local > .env）。
   - 自動ロードを無効にしたい場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

例: `.env.example` に対応する最低限のキー（プロジェクト内 Settings で参照）:
```
JQUANTS_REFRESH_TOKEN=xxxxx
OPENAI_API_KEY=sk-xxxx
KABU_API_PASSWORD=xxxx
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C01234567
# 任意:
KABU_API_BASE_URL=http://localhost:18080/kabusapi
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

- デフォルト:
  - KABU_API_BASE_URL => "http://localhost:18080/kabusapi"
  - DUCKDB_PATH => "data/kabusys.duckdb"
  - SQLITE_PATH => "data/monitoring.db"
  - KABUSYS_ENV => "development"
  - LOG_LEVEL => "INFO"

---

## 使い方（主要な例）

以下は代表的なユースケースの最小例です。詳細は各モジュールの docstring を参照してください。

- DuckDB 接続準備（設定経由のパスを使う例）:
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行する:
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースのスコアリング（OpenAI API キーは env または引数で指定可能）:
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# api_key を明示的に渡すか、OPENAI_API_KEY を環境変数に設定
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"書き込み銘柄数: {n_written}")
```

- 市場レジーム判定:
```python
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査用の DuckDB を初期化して接続を得る:
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.db")
# テーブルが作成され、UTC タイムゾーンが設定されます
```

- 研究用ファクター算出（例: モメンタム）:
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date

records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records: list of dict, each dict contains keys like "code", "mom_1m", "ma200_dev"
```

---

## 注意事項 / 設計上のポイント

- Look-ahead バイアス対策:
  - 各関数は内部で `date.today()` 等に依存せず、明示的な target_date を使う設計を推奨。
  - ETL / 研究処理をバックテスト等で使う際は、過去データのみを事前に用意して使用してください。

- 冪等性:
  - J-Quants の保存処理やニュースの保存は可能な限り冪等操作（ON CONFLICT）で実装されています。

- レート制御・リトライ:
  - J-Quants クライアントは固定間隔スロットリングと指数バックオフを組み合わせて API を叩きます。
  - OpenAI 呼び出しもリトライとフォールバック（失敗時は安全なデフォルトにフォールバック）を行います。

- セキュリティ:
  - RSS 取得では SSRF 対策（ホスト検証、リダイレクト検査）、XML の defusedxml を使用した安全なパース、受信バイト上限などを実装しています。

---

## 便利な設定 / 環境変数（抜粋）

必須と思われる環境変数：
- JQUANTS_REFRESH_TOKEN — J-Quants の refresh token
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime に未指定時に使用）
- KABU_API_PASSWORD — kabuステーション API のパスワード（戦略や実行モジュールが使用）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — 通知用（モニタリング/運用用）

任意・デフォルトあり：
- KABU_API_BASE_URL — デフォルト "http://localhost:18080/kabusapi"
- DUCKDB_PATH — デフォルト "data/kabusys.duckdb"
- SQLITE_PATH — デフォルト "data/monitoring.db"
- KABUSYS_ENV — "development" / "paper_trading" / "live"
- LOG_LEVEL — "DEBUG" / "INFO" / "WARNING" / "ERROR" / "CRITICAL"

自動 .env ロードを無効化する：
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## ディレクトリ構成（主要ファイル抜粋）

リポジトリは src/ 配下にパッケージとして配置されています（例: src/kabusys/...）。

主要なモジュールと説明：
- src/kabusys/__init__.py
- src/kabusys/config.py — 環境変数/設定の読み込みと Settings
- src/kabusys/ai/
  - news_nlp.py — ニュースセンチメント（score_news）
  - regime_detector.py — 市場レジーム判定（score_regime）
- src/kabusys/data/
  - jquants_client.py — J-Quants API クライアント（fetch/save）
  - pipeline.py — ETL パイプライン（run_daily_etl 等）
  - quality.py — データ品質チェック
  - news_collector.py — RSS 収集
  - calendar_management.py — マーケットカレンダーロジック
  - audit.py — 監査テーブルの初期化・監査 DB
  - etl.py — ETL の公開インターフェース（ETLResult の再エクスポート）
  - stats.py — 汎用統計ユーティリティ（zscore_normalize）
- src/kabusys/research/
  - factor_research.py — ファクター計算（momentum/value/volatility）
  - feature_exploration.py — 将来リターン / IC / 統計サマリー 等

（上記は主なモジュールの概観です。詳細は各ファイルの docstring を参照してください）

---

## 開発・テスト時のヒント

- OpenAI / ネットワーク依存部分はテスト時にモックしやすいよう設計されています。
  - 例: kabusys.ai.news_nlp._call_openai_api を unittest.mock.patch で差し替え可能
- ETL の id_token（J-Quants）は引数注入可能でテストで固定トークンを使えます。
- DuckDB はインメモリ接続 `duckdb.connect(":memory:")` を利用して高速なユニットテストを実行できます。

---

## ライセンス / 貢献

（ここにライセンス情報・貢献方法を記載してください）

---

必要に応じて、README に具体的な CLI やデーモン起動方法、Slack 通知の設定手順、kabuステーション連携などの運用手順を追加できます。追加したい項目があれば教えてください。