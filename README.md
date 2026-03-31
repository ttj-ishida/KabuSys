# KabuSys

軽量な日本株向けデータプラットフォーム＆自動売買補助ライブラリ。  
J-Quants からのデータ取得（株価・財務・マーケットカレンダー）、DuckDB ベースの ETL、ニュースの収集・NLP（OpenAI）によるセンチメント解析、リサーチ用ファクター計算、監査ログスキーマ（発注/約定トレース）などを提供します。

この README はコードベース（src/kabusys 以下）の主要機能・セットアップ・使い方・ディレクトリ構成をまとめたものです。

---

## 主要な特徴（機能一覧）

- 環境設定管理
  - .env / .env.local の自動読み込み（必要に応じて無効化可能）
  - settings オブジェクトでアプリ設定を参照可能

- データ取得・ETL（J-Quants API）
  - 株価日足（OHLCV）、財務データ、JPX マーケットカレンダーの差分取得
  - ページネーション対応、トークン自動リフレッシュ、レートリミット管理、リトライロジック
  - DuckDB への冪等保存（ON CONFLICT / DO UPDATE）

- データ品質チェック（quality）
  - 欠損、スパイク、重複、日付不整合の検出
  - QualityIssue 型で詳細を返却

- ニュース収集（RSS）とニュース NLP（OpenAI）
  - RSS 取得で SSRF 対策、URL 正規化、記事ID生成、前処理
  - gpt-4o-mini を用いた JSON Mode で銘柄ごとのセンチメントスコア生成（score_news）
  - 市場レジーム判定（ETF 1321 の MA200 とマクロニュースセンチメント合成 → score_regime）

- リサーチ（研究）モジュール
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン計算、IC（Spearman）や統計サマリー、Zスコア正規化ユーティリティ

- 監査ログ（audit）
  - signal_events / order_requests / executions テーブル定義および初期化ユーティリティ
  - 発注 → 約定までのトレーサビリティ確保（UUID ベース）

---

## 必要環境・依存パッケージ

- Python 3.10+
- 必須ライブラリ（例）
  - duckdb
  - openai
  - defusedxml

インストール例（プロジェクトルートで）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb openai defusedxml
# またはパッケージ化されていれば:
# pip install -e .
```

（プロジェクトに pyproject.toml / requirements.txt があればそれに従ってください）

---

## 環境変数（設定）

アプリは .env / .env.local または環境変数から設定を読み込みます。自動ロードはデフォルトで有効です。自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な環境変数（settings で参照されるもの）:

- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須）
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime で使用）
- KABU_API_PASSWORD — kabuステーション API パスワード（発注連携がある場合）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — 通知先 Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite パス（監視用途）
- PID_FILE_PATH — 実行プロセス PID ファイルパス
- KABUSYS_ENV — 実行環境（development / paper_trading / live）
- LOG_LEVEL — ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）

例: `.env`（簡易）

```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-xxxx
KABU_API_PASSWORD=passwd
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

settings はプログラム内で次のように参照できます:

```py
from kabusys.config import settings
token = settings.jquants_refresh_token
is_live = settings.is_live
```

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンして作業ディレクトリへ移動
2. Python 仮想環境を作成・有効化
3. 必要パッケージをインストール（上記参照）
4. `.env` を作成して必須の環境変数（JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY など）を設定
5. DuckDB 用ディレクトリを作成（必要に応じて）:

```bash
mkdir -p data
```

6. 監査 DB 初期化（任意）:

```py
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
```

---

## 使い方（代表的な API と実行例）

- DuckDB 接続を作成

```py
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

- 日次 ETL を実行（市場カレンダー→株価→財務→品質チェック）:

```py
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントをスコア（OpenAI API キーは環境変数または引数で渡す）

```py
from kabusys.ai.news_nlp import score_news
from datetime import date

# api_key を None にすると環境変数 OPENAI_API_KEY を参照します
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print("書き込んだ銘柄数:", n_written)
```

- 市場レジーム判定（ETF 1321 MA200 + マクロニュース）

```py
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

- ファクター計算（研究用）

```py
from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value
from datetime import date

moms = calc_momentum(conn, date(2026,3,20))
vols = calc_volatility(conn, date(2026,3,20))
vals = calc_value(conn, date(2026,3,20))
```

- 監査スキーマの初期化（既存 DuckDB に追加）

```py
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn, transactional=True)
```

- J-Quants の低レベルクライアント利用例

```py
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token

id_token = get_id_token()  # settings.jquants_refresh_token を参照
recs = fetch_daily_quotes(id_token=id_token, date_from=date(2026,1,1), date_to=date(2026,3,20))
```

---

## 注意点（設計上の重要事項）

- ルックアヘッドバイアス対策
  - LLM 呼び出しや ETL / リサーチ関数は内部で datetime.today() / date.today() を直接参照しない設計です（target_date を明示的に渡すことを推奨）。

- 冪等性
  - データ保存は ON CONFLICT / DO UPDATE を基本にしており、再実行に耐えるようになっています。

- フェイルセーフ
  - 外部 API の失敗（OpenAI や J-Quants）に対してはフォールバック（例えば macro_sentiment=0.0）やリトライロジックを組み込んでいます。致命的な例外は上位へ伝搬されますが、多くはログに留めて処理継続する設計です。

- セキュリティ考慮
  - RSS 取得は SSRF 対策（リダイレクト検査、プライベートアドレス拒否）、XML の defusedxml を使用。NewsCollector は URL 正規化とトラッキング除去を実装しています。

---

## ディレクトリ構成（主要ファイル）

プロジェクトの主要なファイル・ディレクトリ構成（src/kabusys を基準）:

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py           — ニュースセンチメント（score_news）
    - regime_detector.py    — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py     — J-Quants API クライアント（fetch_*, save_*）
    - pipeline.py           — ETL パイプライン（run_daily_etl 等）
    - etl.py                — ETL 結果型 ETLResult の再エクスポート
    - news_collector.py     — RSS 収集・前処理
    - calendar_management.py— 市場カレンダー管理 / 営業日判定
    - quality.py            — データ品質チェック
    - stats.py              — zscore_normalize 等統計ユーティリティ
    - audit.py              — 監査ログスキーマ定義・初期化
  - research/
    - __init__.py
    - factor_research.py    — momentum / volatility / value ファクター
    - feature_exploration.py— 将来リターン / IC / 統計サマリー
  - ai/、research/、data/ 以下に多数の補助ユーティリティ関数あり

---

## 開発・テストについて

- モジュール内の多くの外部呼び出し（OpenAI, HTTP リクエスト, J-Quants）には差し替え（モック）ポイントが用意されています（例えば _call_openai_api を patch）。単体テストや統合テスト実行時はこれらをモックして実行してください。
- DuckDB を使ってローカルで状態を再現しやすく、:memory: でのインメモリ DB 初期化も可能です（init_audit_db(":memory:") など）。

---

## 追加情報 / 今後の拡張

- 発注実行（kabu ステーション）や Slack 通知、監視（monitoring）などの機能はコードベースで枠組みがあります。実稼働で利用する際はリスク管理・ドライラン（paper_trading）モードで十分に試験してください。
- モデルやプロンプト、ウィンドウ設計は現状の定義（news window, MA ウィンドウ等）に従っていますが、調査に応じてパラメータをチューニング可能です。

---

ご不明点や追加で README に含めたい実行例（systemd サービス定義、cron ジョブ例、CI 設定など）があれば教えてください。必要に応じてサンプル .env.example も作成します。