# KabuSys

KabuSys は日本株向けの自動売買・データプラットフォーム用ライブラリ群です。  
データ ETL、ニュース NLP、調査（リサーチ）用ファクター計算、監査ログ、マーケットカレンダー管理、J-Quants / OpenAI 連携などの機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

本ライブラリは以下の目的で設計されています。

- J-Quants API から株価・財務・マーケットカレンダーを差分取得して DuckDB に保存する ETL パイプライン
- RSS ニュース収集と OpenAI によるニュースセンチメント（銘柄別 ai_score）算出
- 市場レジーム（bull/neutral/bear）判定（ETF MA とマクロニュースセンチメントの合成）
- ファクター計算（モメンタム・バリュー・ボラティリティ等）と特徴量解析ユーティリティ
- 監査ログ（シグナル→発注→約定のトレーサビリティ）スキーマ初期化・管理
- データ品質チェック・マーケットカレンダー管理などのデータ基盤機能

設計上の特徴として、Look-ahead バイアス回避、API 呼び出しのリトライ・フェイルセーフ、DuckDB を用いたローカル永続化、LLM 呼び出しの安全化（JSON モード・応答検証）などを重視しています。

---

## 機能一覧

主要な提供機能（モジュール別）

- kabusys.config
  - 環境変数読み込み（.env, .env.local）と settings オブジェクト
- kabusys.data
  - jquants_client: J-Quants API 取得 / DuckDB 保存（差分・ページネーション対応）
  - pipeline: 日次 ETL(run_daily_etl)／個別 ETL(run_prices_etl 等)
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - calendar_management: 営業日判定・カレンダー更新ジョブ
  - news_collector: RSS 取得・前処理・raw_news 保存（SSRF 保護等）
  - audit: 監査ログスキーマ初期化 / init_audit_db / init_audit_schema
  - stats: zscore_normalize 等の統計ユーティリティ
- kabusys.ai
  - news_nlp.score_news: ニュースを銘柄ごとに集約し LLM でセンチメントを算出して ai_scores に書き込む
  - regime_detector.score_regime: ETF（1321）200日MA とマクロニュースで市場レジームを判定し market_regime に書き込む
- kabusys.research
  - factor_research.calc_momentum / calc_value / calc_volatility
  - feature_exploration.calc_forward_returns / calc_ic / factor_summary / rank

---

## 要件

- Python 3.10+
- 必要なライブラリ（例）
  - duckdb
  - openai
  - defusedxml
- （任意）.env に API トークン等を設定

pip で個別に入れる例:
```
pip install duckdb openai defusedxml
```

パッケージを開発モードでインストールする場合（プロジェクトルートに pyproject.toml 等がある想定）:
```
pip install -e .
```

---

## 環境変数（主なもの）

設定は .env / .env.local（プロジェクトルート）または環境変数で行います。kabusys.config.Settings 経由で参照されます。

主なキー:

- JQUANTS_REFRESH_TOKEN（必須）: J-Quants リフレッシュトークン
- OPENAI_API_KEY（必須 for AI 機能）: OpenAI API キー（score_news / score_regime 等で使用）
- KABU_API_PASSWORD: kabuステーション API パスワード（発注系）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（任意）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB 等、デフォルト: data/monitoring.db）
- PID_FILE_PATH / KILL_FLAG_PATH 等の監視設定
- KABUSYS_ENV: 開発環境識別（development / paper_trading / live）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

自動 .env ロードは初期化時に行われます。自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## セットアップ手順

1. リポジトリをクローン（またはコードを取得）
2. 仮想環境を作成して有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```
3. 依存パッケージをインストール
   ```
   pip install duckdb openai defusedxml
   ```
   またはプロジェクトに requirements.txt / pyproject.toml があればそれを使用
4. .env を作成（プロジェクトルート）。最低限以下を設定してください（例）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=your_openai_api_key
   KABUS_API_PASSWORD=...
   DUCKDB_PATH=data/kabusys.duckdb
   LOG_LEVEL=INFO
   KABUSYS_ENV=development
   ```
5. データディレクトリ作成（必要に応じて）
   ```
   mkdir -p data
   ```

---

## 使い方（簡単な例）

以下は Python REPL やスクリプトからの利用例です。実行にあたっては上記で設定した環境変数が利用されます。

- DuckDB 接続を作成して日次 ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())  # ETLResult の内容を確認
```

- ニュースセンチメントをスコアリングして ai_scores に書き込む
```python
from datetime import date
from kabusys.ai.news_nlp import score_news
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # None なら OPENAI_API_KEY を使用
print(f"written {written} codes")
```

- 市場レジーム判定（regime）を実行する
```python
from kabusys.ai.regime_detector import score_regime
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ DB を初期化する
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")  # ファイルの親ディレクトリは自動作成されます
```

- 設定（settings）を参照する
```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.env, settings.log_level)
```

- カレンダー関連ユーティリティ
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026, 1, 1)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

---

## ログ・エラー取り扱い

- LLM 呼び出し（OpenAI）失敗時は、多くの箇所でフェイルセーフ（0.0 にフォールバック）またはスキップして処理を続行します。ログを確認してください。
- J-Quants API 呼び出しはリトライ＋レートリミット制御が組み込まれています。401（トークン期限切れ）は自動リフレッシュを試みます。
- ETL やスキーマ初期化で例外が発生する場合はログ記録され、run_daily_etl は ETLResult.errors にメッセージを追加します。

---

## ディレクトリ構成（主なファイル）

（src 以下をパッケージ化する想定）

- src/kabusys/
  - __init__.py
  - config.py                         -- 環境設定読み込みと Settings
  - ai/
    - __init__.py
    - news_nlp.py                      -- ニュースセンチメント（score_news）
    - regime_detector.py               -- 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py                -- J-Quants API クライアント（fetch/save）
    - pipeline.py                      -- ETL パイプライン（run_daily_etl 等）
    - etl.py                           -- ETL 用公開インターフェース（ETLResult 再エクスポート）
    - quality.py                       -- 品質チェック
    - calendar_management.py           -- マーケットカレンダー管理
    - news_collector.py                -- RSS ニュース収集
    - audit.py                         -- 監査ログスキーマ初期化
    - stats.py                         -- zscore_normalize 等
  - research/
    - __init__.py
    - factor_research.py               -- ファクター計算
    - feature_exploration.py           -- 将来リターン・IC 等の解析
  - monitoring/ (※実装の一部がある想定)
  - execution/ (※発注・約定関連の実装想定)
  - strategy/ (※戦略生成関連の実装想定)

---

## 開発・貢献

- コード品質と安全性（SSRF 防止、XML パース対策、外部 API の扱い）を重視しています。
- 単体テスト（モック）を使って外部 API 呼び出しを置き換え可能な設計になっています（例: kabusys.ai.news_nlp._call_openai_api の差し替え等）。
- 変更・追加機能を提案する場合は、該当モジュールのユニットテスト追加とドキュメント更新をお願いします。

---

## 備考

- この README はコードベースの主要機能と利用方法の要約です。各モジュール内には詳細な docstring と設計方針が記載されていますので、具体的な実装・挙動は該当ファイルを参照してください。
- .env.example や pyproject.toml、requirements.txt がプロジェクトに含まれている場合、それらに合わせてセットアップを行ってください。

ご不明点や README に追記して欲しい項目があれば教えてください。