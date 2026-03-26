# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ。データ取得（J-Quants）、ETL、ニュースNLP、マーケットレジーム判定、研究用ファクター計算、監査ログ（トレーサビリティ）などを含むモジュール群を提供します。

本READMEはプロジェクトの概要、主な機能、セットアップ手順、代表的な使い方、ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

- 目的: 日本株の自動売買インフラ（データ収集・品質チェック・特徴量生成・AIセンチメント・監査ログ・ETL）を提供する。
- 設計方針のハイライト:
  - Look-ahead bias を避ける設計（内部で date.today() や datetime.today() を不用意に参照しない）。
  - DuckDB を中心としたオンプレ／ローカル分析環境に適した設計。
  - 外部 API 呼び出しに対して堅牢なリトライとレート制御を実装。
  - ニュース収集では SSRF/サイズ攻撃対策、XML の安全パースを考慮。
  - 監査ログ（signal → order_request → execution）を UUID ベースで保持しトレーサビリティを強化。

---

## 主な機能一覧

- 環境設定管理
  - .env / .env.local 自動ロード（ルート検出） / 必須環境変数取得ユーティリティ（kabusys.config.settings）
- データ取得（J-Quants）
  - 株価日足、財務データ、JPXマーケットカレンダー、上場銘柄リスト
  - レート制御・認証トークン自動リフレッシュ・ページネーション対応（kabusys.data.jquants_client）
- ETL パイプライン
  - 差分取得、保存、品質チェック、日次パイプライン run_daily_etl（kabusys.data.pipeline）
- データ品質チェック
  - 欠損、重複、スパイク（前日比閾値）・日付整合性チェック（kabusys.data.quality）
- マーケットカレンダー管理
  - 営業日判定、前後営業日の取得、カレンダー更新ジョブ（kabusys.data.calendar_management）
- ニュース収集 / NLP
  - RSS 収集（SSRF/サイズ対策、前処理）、raw_news 保存（kabusys.data.news_collector）
  - OpenAI を用いた銘柄ごとのニュースセンチメントスコアリング（score_news）
  - マクロニュース × ETF (1321) の MA200 乖離を合成した市場レジーム判定（score_regime）
- 研究（Research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算（kabusys.research）
  - 将来リターン計算、IC（スピアマン）計算、Zスコア正規化（kabusys.research, kabusys.data.stats）
- 監査ログ（Audit）
  - signal_events / order_requests / executions 等の監査テーブルの初期化・DB 作成ユーティリティ（kabusys.data.audit）

---

## セットアップ手順

前提:
- Python 3.10 以上を推奨（typing の `X | None` 構文などを使用）。
- DuckDB を使用するためローカルファイルの読み書き権限が必要。

1. リポジトリをチェックアウト
   - 例: git clone ...

2. 仮想環境を作成・有効化（例: venv）
   - python -m venv .venv
   - source .venv/bin/activate  (UNIX)
   - .venv\Scripts\activate     (Windows)

3. 依存パッケージをインストール
   - 主な依存例:
     - duckdb
     - openai
     - defusedxml
   - （プロジェクトに requirements.txt がある場合はそれを利用）
   - 例:
     - pip install duckdb openai defusedxml

4. ローカル開発インストール（任意）
   - pip install -e .

5. 環境変数 / .env の準備
   - プロジェクトルートの .env または .env.local に必要な環境変数を設定できます。自動読み込みはデフォルトで有効です（プロジェクトルートは .git または pyproject.toml を基準に検出）。
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

.env の例 (.env.example を参考に作成してください):
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=your_openai_api_key
KABU_API_PASSWORD=your_kabu_api_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

主要な環境変数の説明:
- JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（score_news, score_regime 等で使用）
- KABU_API_PASSWORD / KABU_API_BASE_URL: kabuステーション API 用（運用系）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: 通知先 Slack
- DUCKDB_PATH / SQLITE_PATH: データベースファイルパス
- KABUSYS_ENV: one of {development, paper_trading, live}
- LOG_LEVEL: {DEBUG, INFO, WARNING, ERROR, CRITICAL}

---

## 使い方（代表例）

以下は代表的なユースケースと簡単なコード例です。実行は Python スクリプトや REPL から行えます。各例では duckdb 接続オブジェクトを渡しています。

1) DuckDB 接続を作る
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

2) 日次 ETL を実行する（市場カレンダー・株価・財務・品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

3) ニュースのセンチメントスコア（OpenAI 必須）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# OPENAI_API_KEY は環境変数または引数で指定
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {n_written}")
```

4) 市場レジーム判定（ETF 1321 の MA200 とマクロ記事センチメントを統合）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

5) 監査用 DuckDB を初期化する
```python
from kabusys.data.audit import init_audit_db

# ファイル指定、":memory:" を使えばインメモリ DB
audit_conn = init_audit_db("data/audit.duckdb")
```

6) 研究用ファクター計算（例: momentum）
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date

records = calc_momentum(conn, target_date=date(2026,3,20))
# z-score 正規化（data.stats）
from kabusys.data.stats import zscore_normalize
normalized = zscore_normalize(records, ["mom_1m", "mom_3m", "mom_6m", "ma200_dev"])
```

注意点:
- OpenAI を使う処理（score_news / score_regime）は API キーを必要とします。API 呼び出しに失敗した場合はフェイルセーフで 0.0 を返す等の設計になっていますが、レスポンスの妥当性やコストに注意してください。
- ETL / API 呼び出しはレート制御やリトライを組み込んでいますが、運用環境では適切な監視・ログ設定を行ってください。

---

## ディレクトリ構成（主要ファイル）

プロジェクトの主要モジュールは `src/kabusys` 以下にあります。代表的なファイル構成を示します。

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数/設定管理
  - ai/
    - __init__.py
    - news_nlp.py                — ニュースセンチメントスコアリング（OpenAI）
    - regime_detector.py         — マーケットレジーム判定（MA200 + マクロ）
  - data/
    - __init__.py
    - jquants_client.py          — J-Quants API クライアント（取得 & 保存）
    - pipeline.py                — ETL パイプライン（run_daily_etl など）
    - etl.py                     — ETLResult の再エクスポート
    - news_collector.py          — RSS 収集・前処理・保存
    - calendar_management.py     — マーケットカレンダー管理・営業日判定
    - quality.py                 — データ品質チェック
    - stats.py                   — 統計ユーティリティ（zscore_normalize 等）
    - audit.py                   — 監査ログスキーマ初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py         — Momentum/Value/Volatility ファクター
    - feature_exploration.py     — 将来リターン・IC・統計サマリー
  - ai/、research/ の __all__ による公開 API が整えられています。

この他、戦略・実行・モニタリング用のパッケージプレースホルダ（__all__ に含まれる）が定義されており、将来的に「strategy」「execution」「monitoring」モジュールが追加される想定です。

---

## 運用・開発に関する補足

- 自動環境変数読み込み:
  - プロジェクトルート（.git または pyproject.toml があるディレクトリ）を起点に .env と .env.local を自動ロードします。
  - 読み込み順序: OS 環境変数 > .env.local > .env
  - 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- KABUSYS_ENV は development / paper_trading / live のいずれかを設定してください。live のときには本番特有の制約を想定した処理が有効になります。
- OpenAI 呼び出しは JSON Mode（厳密な JSON 出力）を前提にしていますが、LLM の挙動により前後に余計なテキストが付与されることがあるためレスポンスの堅牢なパース・検証処理があります。
- ニュース収集では SSRF や XML 攻撃、巨大レスポンス対策（サイズ制限）を実施しています。

---

## 参考・開発のヒント

- テスト・CI で環境変数自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を有効にします。
- OpenAI クライアントの呼び出し箇所は内部でラップされています。ユニットテスト時は該当関数をモック（patch）することで API コールをスキップできます（例: patch("kabusys.ai.news_nlp._call_openai_api")）。
- DuckDB に関する SQL はモジュール内にコメント付きで残されており、そのまま REPL でクエリを試せます。ETL を本番運用する際はファイルパス/バックアップ・アクセス権に注意してください。

---

必要であれば、README に以下を追加できます:
- requirements.txt の具体的な推奨バージョン
- .env.example の完全なサンプルファイル
- よくある実行例（cron で run_daily_etl を回す例、Slack 通知フロー）
- テーブル定義（DDL）のまとめ

追加してほしい項目があれば教えてください。