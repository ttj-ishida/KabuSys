# KabuSys

日本株向けの自動売買 / データパイプライン基盤ライブラリ。  
ETL、マーケットカレンダー、ニュース収集、LLMを使ったニュースセンチメント評価、市場レジーム判定、ファクター研究、データ品質チェック、監査ログ（発注/約定トレーサビリティ）などの機能を提供します。

---

## 主な特徴（機能一覧）

- ETL（J-Quants API からの日次株価・財務・カレンダー取得）
  - 差分取得・バックフィル・ページネーション対応
  - DuckDB へ冪等保存（ON CONFLICT DO UPDATE）
- 市場カレンダー管理（JPX カレンダー）
  - 営業日判定 / 前後営業日取得 / 期間内営業日取得
  - 夜間バッチでのカレンダー更新ジョブ
- ニュース収集（RSS）
  - URL 正規化、SSRF 対策、トラッキングパラメータ除去
  - raw_news / news_symbols への冪等保存
- ニュース NLP（OpenAI を利用した銘柄ごとのセンチメント評価）
  - gpt-4o-mini（JSON Mode）を想定したバッチ処理、結果を ai_scores に保存
- 市場レジーム判定（ETF 1321 の MA + マクロニュースの LLMセンチメント合成）
  - ma200 とマクロセンチメントを組み合わせて 'bull' / 'neutral' / 'bear' を判定
- データ品質チェック
  - 欠損、重複、スパイク（急変）、日付整合性チェック
  - QualityIssue データクラスで検出結果を返す
- ファクター計算・探索（研究用）
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン計算、IC（Spearman）や統計サマリー
- 監査ログ（audit）
  - signal_events / order_requests / executions 等の監査テーブル定義・初期化
  - 監査 DB 初期化ユーティリティ（DuckDB）
- 設定管理
  - .env / .env.local / OS 環境変数の読み込み、自動ロード（プロジェクトルート基準）
  - 必須環境変数チェック（settings オブジェクト）

---

## 必要条件 / 依存（代表）

このリポジトリは以下のライブラリを利用します（抜粋）:

- Python 3.10+
- duckdb
- openai (OpenAI Python SDK)
- defusedxml
- (標準ライブラリ: urllib, json, datetime, logging 等)

インストール例（venv を想定）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb openai defusedxml
# またはパッケージ化済みなら:
# pip install -e .
```

requirements.txt が用意されている場合はそれを使ってください。

---

## セットアップ手順

1. リポジトリをクローン:

   ```bash
   git clone <リポジトリURL>
   cd <リポジトリ>
   ```

2. 仮想環境作成・依存インストール（上記参照）

3. 環境変数を用意する（.env/.env.local をプロジェクトルートに配置）

   自動読み込みについて:
   - デフォルトでプロジェクトルート（.git または pyproject.toml のある場所）から `.env` と `.env.local` を読み込みます。
   - 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

4. 必須の環境変数（例）

   ```
   # .env (例)
   JQUANTS_REFRESH_TOKEN=xxxxxxx
   OPENAI_API_KEY=sk-xxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   ```

   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（API 認証）
   - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime のデフォルト取得元）
   - KABU_API_PASSWORD: kabuステーション用パスワード設定
   - SLACK_*: Slack 通知用（利用時）
   - KABUSYS_ENV: `development` | `paper_trading` | `live`
   - DUCKDB_PATH / SQLITE_PATH: デフォルト DB パス（expanduser サポート）

---

## 使い方（主なAPI例）

以下のサンプルは簡単な利用例です。実行環境で必要な環境変数（特に API キー）が設定されていることを確認してください。

- DuckDB 接続を作り、日次 ETL を実行する:

```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
# target_date を指定（省略時は今日）
res = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(res.to_dict())
```

- ニュースセンチメント（ai_scores）を算出して保存する:

```python
from kabusys.ai.news_nlp import score_news
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY が環境変数にある場合、api_key 引数は省略可
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"written codes: {written}")
```

- 市場レジーム（market_regime）を判定して書き込む:

```python
from kabusys.ai.regime_detector import score_regime
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査用 DuckDB を初期化する（order_requests 等のテーブル作成）:

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# 返り値は duckdb.DuckDBPyConnection
```

- 設定値を取得する（Python API）:

```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.duckdb_path)
print(settings.is_live)
```

注意:
- OpenAI の呼び出しはモデル `gpt-4o-mini` を想定しています。APIキーは引数で渡すか環境変数 `OPENAI_API_KEY` を設定してください。
- LLM 呼び出しは外部APIを使用するため、失敗時はフェイルセーフ（スコア=0.0 など）になる実装が多くありますが、ログを確認してください。

---

## ディレクトリ構成（抜粋）

以下はパッケージ内部の主なファイル・モジュール構成です（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                     -- 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                  -- ニュースの LLM センチメント評価（ai_scores）
    - regime_detector.py           -- 市場レジーム判定（ma200 + マクロ記事 LLM）
  - data/
    - __init__.py
    - pipeline.py                  -- ETL パイプライン（run_daily_etl 等）
    - etl.py                       -- ETLResult の再エクスポート
    - jquants_client.py            -- J-Quants API クライアント・保存関数
    - calendar_management.py       -- 市場カレンダー管理・判定ロジック
    - news_collector.py            -- RSS ニュース収集
    - quality.py                   -- データ品質チェック
    - stats.py                     -- 汎用統計ユーティリティ（zscore 正規化等）
    - audit.py                     -- 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py           -- モメンタム / ボラ / バリュー等
    - feature_exploration.py       -- 将来リターン / IC / 統計サマリー
  - (その他: strategy, execution, monitoring 等のパッケージが想定される)

この README は主要なモジュールを紹介しています。実際のリポジトリにはさらに多くの補助モジュール・ユーティリティが含まれます。

---

## 運用上の注意点 / 設計ポリシー（抜粋）

- ルックアヘッドバイアス防止
  - 各処理は internal において date / datetime の参照を外部引数に依存させ、直接 datetime.today()／date.today() を参照しない設計が多く採用されています。
- 冪等性
  - DB 保存は可能な限り ON CONFLICT / DELETE→INSERT のように冪等に設計。
- フェイルセーフ
  - 外部 API (OpenAI / J-Quants / RSS) の失敗はできるだけ局所的に処理し、全体の停止を防ぐ設計。
- セキュリティ
  - RSS の取得では SSRF 対策、defusedxml を利用した XML パースなどを実装。
- テスト容易性
  - LLM 呼び出しや HTTP 呼び出し箇所はモック差し替えしやすいインターフェースになっています。

---

## よくある操作例（チェックリスト）

- DB 初期化（監査用）:
  - init_audit_db("data/audit.duckdb")
- ETL の定期実行:
  - run_daily_etl(conn, target_date=...)
- ニュース収集ジョブ（ニュース収集関数は news_collector.fetch_rss / 保存処理を組み合わせる）
- LLM を使ったスコア取得:
  - score_news / score_regime を呼ぶ（OPENAI_API_KEY を設定）

---

## サポート / コントリビュート

- バグ報告や機能要望は Issue にお願いします。
- コントリビューションガイドライン（Coding style / テスト / PR フロー）がある場合はリポジトリの CONTRIBUTING.md を参照してください（存在する場合）。

---

README のサンプルは以上です。必要であれば以下を追加できます:
- 具体的な SQL スキーマ一覧（raw_prices, raw_news, ai_scores, market_regime 等）
- CI / デプロイ手順（systemd / Kubernetes での運用例）
- 具体的な .env.example ファイル（より詳細な説明付き）