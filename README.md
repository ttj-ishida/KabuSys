# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からの株価・財務・マーケットカレンダー取得）、ニュース収集・NLP（OpenAI を利用した銘柄センチメント）、研究（ファクター計算）、監査ログ（発注／約定トレース）などの機能を提供します。

---

## 主な特徴（機能一覧）

- データ取得・ETL
  - J-Quants API からの株価日足（OHLCV）、財務データ、JPX カレンダー取得（ページネーション・レート制御・リトライ実装）
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
  - 日次 ETL パイプライン（run_daily_etl）
- データ品質チェック
  - 欠損（OHLC）チェック、スパイク検出、重複チェック、日付整合性チェック
- ニュース収集
  - RSS 取得（SSRF 対策・トラッキングパラメータ除去・gzip 上限チェック）
  - raw_news / news_symbols への冪等保存ロジック（記事ID = 正規化 URL の SHA256）
- AI（LLM）連携
  - ニュースの銘柄別センチメント解析（gpt-4o-mini 想定）→ ai_scores へ書込（score_news）
  - マクロセンチメントと ETF（1321）200日MA乖離の合成による市場レジーム判定（score_regime）
  - API レート・エラーに対するリトライ・フォールバック実装（失敗時は安全側の値を使用）
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算（calc_momentum 等）
  - 将来リターン計算、IC（Spearman）やファクター統計サマリ、Zスコア正規化
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions の DDL 定義と初期化ユーティリティ
  - すべて UTC タイムスタンプで保存、冪等性を考慮した設計

---

## 前提・依存関係（概略）

- Python 3.9+（typing の新構文や Path | None 等を利用）
- 必要な主要パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- その他標準ライブラリ（urllib, json, datetime, logging など）

（実際の requirements はプロジェクトの packaging 設定や pyproject.toml を参照してください）

---

## セットアップ手順

1. リポジトリをクローン / プロジェクトディレクトリへ移動

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. インストール（開発インストール例）
   - pip install -e . 
   - または必要パッケージを直接インストール:
     - pip install duckdb openai defusedxml

4. 環境変数 / .env の準備
   - プロジェクトルートに .env（または .env.local）を配置すると、自動で読み込まれます（優先順位: OS 環境 > .env.local > .env）。
   - 自動読み込みを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 必須の環境変数（コード内で _require を用いているもの）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
     - OPENAI_API_KEY（score_news / score_regime を使う場合）
   - 任意 / デフォルト値
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL: DEBUG/INFO/...（デフォルト: INFO）
     - DUCKDB_PATH（既定: data/kabusys.duckdb）
     - SQLITE_PATH（既定: data/monitoring.db）
   - 例 (.env):
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     OPENAI_API_KEY=sk-...
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

---

## 使い方（簡単な例）

以下は基本的な利用例です。DuckDB 接続を作成して各関数を呼び出します。

- 日次 ETL 実行（株価 / 財務 / カレンダー取得・品質チェック）

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントスコア（OpenAI API キーが必要）

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を利用
print("書き込み銘柄数:", n_written)
```

- 市場レジーム判定（ETF 1321 の MA とマクロニュースを合成）

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ用 DB 初期化

```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# テーブルが作成され、UTC タイムゾーン設定が適用されます
```

- 研究モジュールの利用例（モメンタム計算）

```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records: list of dict (date, code, mom_1m, mom_3m, mom_6m, ma200_dev)
```

---

## 注意点 / 設計上のポイント

- Look-ahead バイアス防止
  - 各 AI / 研究モジュールは内部で現在時刻を参照しない設計（target_date を明示）
  - ETL / 取得関数は fetched_at を UTC で記録
- LLM 呼び出し
  - OpenAI の呼び出しはリトライや JSON バリデーションを行い、失敗時はフェイルセーフ（0 にフォールバックなど）
  - テスト時は内部の _call_openai_api を patch して差し替え可能
- RSS / ネットワーク
  - SSRF 対策（ホストのプライベート判定、リダイレクトチェック）
  - レスポンスサイズ上限（10 MB）・gzip 対応
- 設定ファイルの自動ロード
  - プロジェクトルート（.git または pyproject.toml を探索）を基準に .env/.env.local を読み込む
  - OS 環境変数を保護するため .env の上書きは制御される
- DuckDB の互換性注意
  - executemany に空リストを渡せないバージョンの考慮など、互換性対策が各所に実装されています

---

## ディレクトリ構成（抜粋）

プロジェクトの主要なモジュール構成（src/kabusys 配下）:

- kabusys/
  - __init__.py
  - config.py                            （環境変数 / 設定読み込み）
  - ai/
    - __init__.py
    - news_nlp.py                         （ニュース本文から銘柄別センチメント → ai_scores）
    - regime_detector.py                  （市場レジーム判定）
  - data/
    - __init__.py
    - jquants_client.py                   （J-Quants API クライアント + DuckDB への保存）
    - pipeline.py                         （ETL パイプライン / run_daily_etl 等）
    - etl.py                              （ETLResult 再エクスポート）
    - news_collector.py                   （RSS 収集・前処理）
    - calendar_management.py              （市場カレンダー管理 / 営業日判定）
    - quality.py                          （データ品質チェック）
    - stats.py                            （zscore_normalize 等）
    - audit.py                            （監査ログスキーマ初期化）
  - research/
    - __init__.py
    - factor_research.py                  （モメンタム / ボラティリティ / バリュー計算）
    - feature_exploration.py              （将来リターン・IC・統計サマリ）
  - ai, research, data のほか、パッケージ public API には strategy / execution / monitoring 等が想定される（__all__ に列挙）

（実際のリポジトリではより多くのモジュール・テスト・CLI 等が存在する可能性があります）

---

## ライセンス・貢献

- ライセンス情報はリポジトリのルート（LICENSE / pyproject.toml）を参照してください。
- バグ報告・機能提案は Issue を通じてお願いします。

---

README は以上です。必要ならば、実際の pyproject.toml / requirements.txt を元に「インストール可能パッケージ一覧」「より詳細な実行例」「CI / ローカル開発フロー」などを追記します。どの情報を追加しますか？