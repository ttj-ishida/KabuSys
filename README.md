# KabuSys

KabuSys は日本株のデータパイプライン、リサーチ、AI によるニュースセンチメント評価、及び監査ログ機能を備えた自動売買支援ライブラリです。J-Quants / kabuステーション / OpenAI 等と連携して、データ取得（ETL）→ 品質チェック → ファクター計算 → シグナル生成 → 発注監査までの基盤を提供します。

バージョン: 0.1.0

---

## 主要な特徴

- データ取得（J-Quants API）:
  - 株価日足（OHLCV）、財務データ、JPX マーケットカレンダーの差分取得と DuckDB への冪等保存
  - レートリミット／リトライ／トークン自動リフレッシュ対応

- ニュース収集・NLP（OpenAI）:
  - RSS からニュースを安全に収集して raw_news に保存（SSRF 対策、サイズチェック、トラッキング除去）
  - gpt-4o-mini を用いた銘柄別センチメントスコアリング（batch、JSON mode、堅牢なバリデーション）
  - マクロニュースを用いた市場レジーム判定（ma200 + LLM センチメントの合成）

- リサーチ / ファクター:
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Spearman ランク相関）、ファクター統計サマリー
  - Zスコア正規化ユーティリティ

- データ品質管理:
  - 欠損、スパイク（急騰・急落）、重複、日付不整合などのチェック群を提供
  - ETL 後にまとめてチェックを実行可能

- 監査・トレーサビリティ:
  - signal_events / order_requests / executions などの監査テーブルと初期化ユーティリティ
  - UUID ベースの冪等キー設計、UTC タイムスタンプ保存

- 設定管理:
  - .env / 環境変数ベースの設定読み込み（パッケージ配布後も正しく動作するルート検出ロジック）
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能

---

## 必要条件（推奨）

- Python 3.10+
- 必須パッケージ（主要なもの）
  - duckdb
  - openai
  - defusedxml

（プロジェクトに requirements.txt がある想定の場合はそれを使ってください。ない場合は上記を手動インストールしてください）

例:
```
python -m pip install duckdb openai defusedxml
```

---

## セットアップ手順

1. リポジトリをクローン（またはソースを配置）
2. （仮想環境推奨）仮想環境を作成して有効化
3. 依存パッケージをインストール
   ```
   python -m pip install -r requirements.txt
   ```
   requirements.txt が無い場合:
   ```
   python -m pip install duckdb openai defusedxml
   ```

4. 環境変数を設定（.env をプロジェクトルートに置くか OS 環境変数で設定）
   - 自動ロード: package の config.py はプロジェクトルートを .git または pyproject.toml を基準に探索し、`.env` と `.env.local` を自動読込します。テスト等で自動読込を無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

5. 最低限必要な環境変数（.env の例）
   ```
   # J-Quants
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

   # kabuステーション API
   KABU_API_PASSWORD=your_kabu_password
   #KABU_API_BASE_URL=http://localhost:18080/kabusapi  # 任意（デフォルトは上記）

   # OpenAI
   OPENAI_API_KEY=sk-...

   # Slack（通知等で使用）
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567

   # DB パス（任意）
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db

   # システム環境
   KABUSYS_ENV=development  # development|paper_trading|live
   LOG_LEVEL=INFO
   ```

---

## 使い方（主要な API と簡単な例）

以下は代表的なユースケース例です。実行には DuckDB と必要な環境変数が設定されていることを前提とします。

- DuckDB 接続を作る:
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行する:
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュースセンチメント（銘柄別）をスコア化して ai_scores テーブルへ書き込む:
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"written {n_written} codes")
```
- 市場レジームを判定して market_regime テーブルへ書き込む:
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- 監査 DB の初期化（監査用の別 DB を作る例）:
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")  # parent ディレクトリを自動作成
```

- リサーチ用ファクター計算例:
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

momentum = calc_momentum(conn, target_date=date(2026, 3, 20))
vol = calc_volatility(conn, target_date=date(2026, 3, 20))
value = calc_value(conn, target_date=date(2026, 3, 20))
```

- データ品質チェックを単独で実行:
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=date(2026, 3, 20))
for i in issues:
    print(i)
```

注意:
- OpenAI を利用する関数（score_news, score_regime 等）は環境変数 `OPENAI_API_KEY` または引数 api_key を必要とします。
- DuckDB スキーマ（raw_prices, raw_news, ai_scores, market_regime, raw_financials, market_calendar 等）が事前に存在する必要があります（ETL の一部がスキーマ作成を行う場合もありますが、利用前にスキーマ定義を確認してください）。

---

## 設定 / 動作上の注意点

- 自動 .env ロード:
  - src/kabusys/config.py はプロジェクトルート（.git または pyproject.toml を基準）を探索し `.env` と `.env.local` を読み込みます。OS 環境変数は優先され、`.env.local` は `.env` を上書きします。
  - 自動ロードが不要な場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途等）。

- Look-ahead bias 対策:
  - AI / リサーチモジュールは内部で datetime.today() / date.today() を直接参照する実装を避け、明示的に target_date を受け取る設計です。バックテストや再現性のため、常に target_date を渡すことを推奨します。

- フェイルセーフ:
  - LLM 呼び出し失敗時や API エラー時のフォールバックが各モジュールで用意されています（LLM が使えない場合は中立スコアを利用する等）。

---

## ディレクトリ構成（抜粋）

プロジェクトの主要ファイル・ディレクトリ:

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py             — ニュースセンチメント（銘柄別）
    - regime_detector.py      — マクロ + MA200 による市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント & DuckDB 保存
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - etl.py                  — ETL 型の再エクスポート（ETLResult）
    - news_collector.py       — RSS ニュース収集（SSRF 対策・正規化）
    - calendar_management.py  — 市場カレンダー管理 / 営業日判定
    - audit.py                — 監査ログテーブル定義・初期化
    - quality.py              — データ品質チェック
    - stats.py                — 汎用統計ユーティリティ（zscore_normalize 等）
  - research/
    - __init__.py
    - factor_research.py      — モメンタム / バリュー / ボラティリティ等
    - feature_exploration.py  — 将来リターン / IC / 統計サマリー
  - monitoring/ (※コードベース内に実装がある想定のモジュール)
  - execution/, strategy/ 等（README に記載されている機能と整合）

上記は主要モジュールの抜粋です。各ファイル内に詳細な docstring / 実装方針が記載されています。

---

## 開発・テスト

- モジュール内では外部呼び出し（OpenAI, HTTP 等）をモックしやすいように設計されています（プライベート関数を差し替え可能）。
- テストを作成する際は、環境変数の自動ロードを無効化するか（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）、テスト用の .env を用意してください。
- DuckDB のインメモリ接続（":memory:"）は監査 DB 初期化関数でもサポートされています。

---

## 最後に / 貢献

この README はコードベースの概要・セットアップ・代表的な利用方法をまとめたものです。各モジュールにはより詳細な docstring と設計コメントが含まれています。機能拡張やバグ修正・テスト追加等は歓迎します。Pull Request の際は、関連するユニットテストと簡単な利用例を添えてください。

---