# KabuSys

バージョン: 0.1.0

KabuSys は日本株のデータパイプライン、ファクター研究、ニュースベースの AI スコアリング、監査ログ機能を備えた自動売買／リサーチ用ライブラリです。J-Quants API や kabuステーション、OpenAI（gpt-4o-mini）などと連携し、DuckDB をデータストアとして利用することを想定しています。

主な設計方針:
- ルックアヘッドバイアス回避（内部で date.today()/datetime.today() に依存しない処理設計）
- DuckDB による SQL + Python のハイブリッド実装
- 冪等性（ETL / 保存処理は ON CONFLICT で上書き）
- 外部 API のリトライやフェイルセーフ処理を組み込んだ堅牢な実装

---

## 機能一覧

- 環境設定管理（.env の自動読み込み／必要設定チェック）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能
- データ ETL（J-Quants API からの株価・財務・カレンダー取得）
  - 差分更新、バックフィル、品質チェック（欠損・重複・スパイク・日付整合性）
  - rate limit / retry / token refresh 対応
- ニュース収集（RSS 取得・正規化・raw_news 保存）
  - SSRF 対策・サイズ制限・XML サニタイズ等
- ニュース NLP（OpenAI を用いた銘柄別センチメントスコア）
  - batch 処理、JSON Mode 検証、リトライ
- 市場レジーム判定（ETF 1321 MA とマクロニュースの LLM スコアを合成）
- ファクター計算（モメンタム / ボラティリティ / バリュー 等）
  - calc_momentum, calc_volatility, calc_value
- 研究用ユーティリティ（将来リターン計算、IC、統計サマリ、zscore 正規化）
- 監査ログ（signal → order_request → execution のトレーサビリティ）
  - 監査用テーブル定義と初期化ユーティリティ
- ユーティリティ（統計関数、日付／カレンダー管理、J-Quants クライアント等）

---

## 必要な環境変数（主なもの）

プロジェクトは環境変数またはプロジェクトルートの `.env` / `.env.local` から設定を読み込みます。主に必要となる変数は以下の通りです。

- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- KABU_API_BASE_URL (任意、デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID
- OPENAI_API_KEY
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト: INFO

.example の `.env.example` をリポジトリルートに置いて、それを参考に `.env` を作成してください。自動ロードを無効にしたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## セットアップ手順

1. リポジトリをクローン／配置
2. Python 仮想環境を作成して有効化
   - python >= 3.10 を推奨
3. 必要パッケージをインストール（例: minimal）
   - pip install duckdb openai defusedxml
   - 他に logging 等の標準ライブラリを使用

リポジトリがパッケージ化されていれば:
- pip install -e .

注意:
- OpenAI SDK（ここでは openai の v1 互換 API を利用）や duckdb が必要です。
- ネットワーク接続が必要（J-Quants / RSS / OpenAI）。

---

## 使い方（概要とサンプル）

以下は主要ユーティリティの使用例です。細かい引数や戻り値は各モジュールの docstring を参照してください。

- DuckDB 接続例:
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

- 日次 ETL を実行する:
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# conn は duckdb 接続
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP スコアリング（ai_score を ai_scores テーブルへ書き込む）:
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="YOUR_OPENAI_KEY")
print("書き込み銘柄数:", n_written)
```

- 市場レジーム判定:
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20), api_key="YOUR_OPENAI_KEY")
```

- 監査ログ初期化:
```python
from kabusys.data.audit import init_audit_db

# ファイル DB を作成して監査スキーマを初期化
audit_conn = init_audit_db("data/audit.duckdb")
```

- ファクター計算（例: モメンタム）:
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date

mom = calc_momentum(conn, target_date=date(2026, 3, 20))
# mom は {date, code, mom_1m, mom_3m, mom_6m, ma200_dev} の dict のリスト
```

- z-score 正規化ユーティリティ:
```python
from kabusys.data.stats import zscore_normalize

normalized = zscore_normalize(records=mom, columns=["mom_1m", "mom_3m", "ma200_dev"])
```

ログレベルは環境変数 `LOG_LEVEL` で制御できます。

---

## ディレクトリ構成（主要ファイル）

（パッケージルート: src/kabusys 以下）

- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- data/
  - __init__.py
  - calendar_management.py
  - etl.py
  - pipeline.py
  - stats.py
  - quality.py
  - audit.py
  - jquants_client.py
  - news_collector.py
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- research/* はファクター計算・特徴量探索用モジュール
- data/jquants_client.py は J-Quants API クライアント（取得／保存ユーティリティ）
- data/news_collector.py は RSS 取得と raw_news 登録処理
- data/audit.py は監査ログテーブル定義と初期化ユーティリティ
- ai/news_nlp.py, ai/regime_detector.py は OpenAI を使った NLP 処理

この README の内容はコード内の docstring を要約したものです。より詳しいパラメータや戻り値、例外動作は各モジュールの docstring を参照してください。

---

## 注意事項 / 運用上のヒント

- Look-ahead バイアス防止のため、関数の多くは内部で現在時刻を参照せず、明示的な target_date を受け取ります。テストやバッチ実行時には必ず target_date を明示してください。
- OpenAI 呼び出しは外部 API のため失敗する可能性があります。score_news / score_regime は API エラー時にフェイルセーフ（スコア 0 のフォールバックや該当銘柄のスキップ）を行う実装がありますが、運用ではレート制限・課金状況に注意してください。
- J-Quants API はレート制限とトークンリフレッシュを扱います。`JQUANTS_REFRESH_TOKEN` を .env に設定し、ETL 実行前に有効なトークンを確保してください。
- news_collector は RSS に対して SSRF 対策や gzip/サイズ上限対処を行っています。カスタム RSS を追加する場合はソースの信頼性を考慮してください。
- DuckDB の executemany の挙動（バージョン差）に依存する箇所があります（空リストバインドの回避など）。運用環境の DuckDB バージョンを固定すると安定します。

---

## コントリビューション

バグレポート／改善提案は Pull Request を歓迎します。コード内の docstring と一貫したスタイル（型注釈・詳細な docstring）での拡張をお願いします。

---

必要であれば、README に具体的な .env.example のサンプルや requirements.txt の例、さらに詳しい API 使用例（ログの初期化、エラーハンドリング、ジョブスケジューリング例）も追記できます。どの情報を優先して追加しますか？