# KabuSys

日本株向けのデータプラットフォームと自動売買補助ライブラリ群。  
ETL（J-Quants からのデータ取得・保存）、ニュース収集・NLP（OpenAI を利用したセンチメント付与）、ファクター計算、マーケットカレンダー管理、監査ログ（発注／約定トレーサビリティ）等の機能を内包します。

バージョン: 0.1.0

---

## 主要な特徴（機能一覧）

- 環境変数ベースの設定管理（自動で .env / .env.local をプロジェクトルートから読み込み）
- J-Quants API クライアント
  - 株価日足（OHLCV）、財務データ、JPX マーケットカレンダー等の差分取得・ページネーション対応
  - レート制御・リトライ・トークン自動リフレッシュ
  - DuckDB へ冪等保存（ON CONFLICT）
- ETL パイプライン
  - 日次 ETL（カレンダー → 株価 → 財務 → 品質チェック）
  - 品質チェック（欠損、スパイク、重複、日付整合性）
- ニュース収集（RSS）
  - SSRF 対策、トラッキングパラメータ除去、記事ID のハッシュ化、前処理
- ニュース NLP（OpenAI を利用した銘柄別センチメント）
  - バッチ化、JSON Mode、リトライ、レスポンス検証
- 市場レジーム判定（ETF 1321 の MA とマクロニュースの LLM 評価を合成）
- 監査ログ（signal_events / order_requests / executions 等）のスキーマ初期化と DB ユーティリティ
- 研究用ユーティリティ（ファクター計算、将来リターン、IC、統計サマリー）
- 共通ユーティリティ（Z スコア正規化、カレンダー判定、DuckDB 補助等）

---

## 前提（Prerequisites）

- Python 3.10+
- 推奨パッケージ（一例）
  - duckdb
  - openai（OpenAI SDK）
  - defusedxml
  - その他標準ライブラリ以外の依存は setup / pyproject に従うこと

例（pip でインストールする場合）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# またはプロジェクトに pyproject/requirements があればそれに従う
```

---

## 環境変数（必須・主要）

設定は環境変数またはプロジェクトルートの .env / .env.local から読み込まれます。自動読み込みはデフォルトで有効。読み込みを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な変数（必須は明記）:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- OPENAI_API_KEY (必須 for NLP/regime) — OpenAI API キー（score_news / score_regime の引数でも指定可）
- KABU_API_PASSWORD — kabuステーション API 用パスワード（必要に応じて）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン（必要に応じて）
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- KABUSYS_ENV — 環境 ("development" | "paper_trading" | "live")（デフォルト development）
- LOG_LEVEL — "DEBUG" / "INFO" / "WARNING" / "ERROR" / "CRITICAL"（デフォルト INFO）

例 (.env):
```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-....
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをチェックアウト
   - git clone 〜
2. 仮想環境の作成と依存インストール
   - python -m venv .venv
   - source .venv/bin/activate
   - pip install -r requirements.txt  # または必要パッケージを個別に install
3. 環境変数の設定
   - プロジェクトルートに .env を作成（.env.example を参考に）
   - もしくは環境に直接エクスポート
4. DuckDB データベースディレクトリを作成（自動でも作成される処理あり）
   - mkdir -p data
5. 監査 DB の初期化（必要に応じて）
   - 以下の Python スニペット参照

---

## 使い方（主要 API と実行例）

以下は対話的 / スクリプトからの利用例です。すべての例はプロジェクトルートで実行することを前提とします。

- 共通：DuckDB 接続の取得
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

- ETL（日次 ETL の実行）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# target_date を省略すると今日が対象（内部で営業日に調整されます）
res = run_daily_etl(conn, target_date=date(2026,3,20))
print(res.to_dict())
```

- ニュース NLP（銘柄別センチメント付与）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# conn は duckdb 接続
written = score_news(conn, target_date=date(2026,3,20))
print(f"書き込み銘柄数: {written}")
# OPENAI_API_KEY を環境変数で用意していれば api_key 引数は不要
```

- 市場レジーム判定（MA + マクロニュースの LLM 評価）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026,3,20))
```

- 監査ログスキーマの初期化（監査専用 DB 作成）
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# または init_audit_schema(conn) を既存の conn に対して実行可能
```

- 研究用ファクター計算
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

moms = calc_momentum(conn, date(2026,3,20))
vals = calc_value(conn, date(2026,3,20))
vols = calc_volatility(conn, date(2026,3,20))
```

注意:
- OpenAI 呼び出しを伴う関数（score_news, score_regime）は API 呼び出しに課金が発生します。テスト時はモック化推奨。
- DuckDB の executemany に関するバージョン依存の注意点がコード中にあるため、使用する duckdb バージョンに注意してください。

---

## テスト・デバッグのヒント

- 自動で .env を読み込む仕組みはプロジェクトルート（.git または pyproject.toml を基準）から .env を探します。テストで自動ロードを無効にしたい場合は:
  - 環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- OpenAI 呼び出し部は内部でモジュール関数を呼んでいるため、ユニットテストでは該当関数（例: kabusys.ai.news_nlp._call_openai_api）を patch/モックしてください。
- news_collector の HTTP 部分も内部で置き換え可能（_urlopen をモック）です。

---

## ディレクトリ構成（抜粋）

プロジェクトは Python パッケージ kabusys 以下に機能を分割しています。主なファイル・モジュール:

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュースセンチメント付与（OpenAI）
    - regime_detector.py           — 市場レジーム判定（MA + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント & DuckDB 保存
    - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
    - etl.py                       — ETLResult の再エクスポート
    - calendar_management.py       — マーケットカレンダー管理 / 営業日判定
    - news_collector.py            — RSS ニュース収集
    - quality.py                   — データ品質チェック
    - stats.py                     — 共通統計ユーティリティ（zscore_normalize 等）
    - audit.py                     — 監査ログスキーマ定義 / 初期化
  - research/
    - __init__.py
    - factor_research.py           — ファクター計算（momentum / value / volatility）
    - feature_exploration.py       — 将来リターン / IC / summary 等
  - ai、data、research 以下にさらに細かいロジックが実装されています。

---

## 設計上の注意点（重要）

- Look-ahead バイアス対策:
  - 関数群は基本的に `target_date` を受け取り、内部で datetime.today() / date.today() を参照しない方針（バックテスト時のリーク防止）。
  - J-Quants 取得では fetched_at を UTC で保存し、いつデータが取得可能になったかをトレース可能にしています。
- 冪等性:
  - DB への保存は ON CONFLICT（あるいは一意キー）により上書き/排除する実装。
  - 監査ログ側でも order_request_id を冪等キーとして扱う想定。
- フェイルセーフ:
  - LLM / API 部分は失敗時にゼロスコアやスキップで継続する設計（例: macro_sentiment=0.0 フォールバック）。
- セキュリティ:
  - news_collector は SSRF 対策、XML 攻撃対策（defusedxml）、受信サイズ制限等を実装。

---

## 参考・補足

- ロギングは環境変数 LOG_LEVEL で調整してください（デフォルト INFO）。
- kabuステーション等外部ブローカー API 連携が必要な部分は別モジュール（execution / strategy 等）で実装想定です（今回の抜粋では含まれていない機能がある可能性があります）。
- 実運用（live）モードでの発注・資金管理・リスク管理は非常に注意が必要です。paper_trading 環境で十分な検証を行ってください。

---

ご希望があれば、次の内容を追加で作成します:
- pyproject.toml / requirements.txt の例
- CI（テスト・静的解析）用の設定例
- よく使うユーティリティの CLI ラッパー例（ETL を cron / Airflow で回すためのスクリプト）