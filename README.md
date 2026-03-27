# KabuSys

日本株向けのデータプラットフォーム & 自動売買支援ライブラリです。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュースの NLP スコアリング、マーケットレジーム判定、監査ログ（発注→約定のトレーサビリティ）などを提供します。

---

## 主な特徴

- J-Quants API を使った株価（日足）・財務データ・マーケットカレンダーの差分取得（ページネーション・レート制御・トークン自動更新対応）
- DuckDB を用いた ETL パイプライン（差分取得、保存、品質チェック）
- ニュース収集（RSS）→ 前処理 → OpenAI（gpt-4o-mini）による銘柄別センチメントスコア（ai_scores）生成
- マーケットレジーム判定（ETF 1321 の MA200 乖離とマクロニュース LLM 評価の合成）
- 研究用ユーティリティ（ファクター計算、将来リターン、IC 計算、Zスコア正規化 等）
- 監査ログ（signal_events / order_requests / executions）スキーマ初期化ユーティリティ
- データ品質チェック（欠損、スパイク、重複、日付不整合）

---

## 必要条件

- Python 3.10 以上
- 主な依存パッケージ（抜粋）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、OpenAI、RSS ソース）

（具体的な requirements.txt はリポジトリに合わせて用意してください）

---

## 環境変数 / .env

本プロジェクトは .env ファイルまたは環境変数を参照します。自動ロードはパッケージルート（.git または pyproject.toml があるディレクトリ）を起点に行われ、優先順位は OS 環境変数 > .env.local > .env です。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主要な環境変数（必須／任意）:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- OPENAI_API_KEY (必須 for AI) — OpenAI API キー（score_news / score_regime）
- SLACK_BOT_TOKEN (必須) — Slack 通知に使用
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH (任意) — デフォルト: data/kabusys.duckdb
- SQLITE_PATH (任意) — デフォルト: data/monitoring.db
- KABUSYS_ENV (任意) — development / paper_trading / live（デフォルト development）
- LOG_LEVEL (任意) — DEBUG / INFO / WARNING / ERROR / CRITICAL

簡易 .env 例（プロジェクトルートに配置）:
```
JQUANTS_REFRESH_TOKEN=xxxxx
OPENAI_API_KEY=sk-xxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-xxxxx
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（開発用）

1. Python 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt があれば `pip install -r requirements.txt`）

3. パッケージを開発モードでインストール（src レイアウト対応）
   - pip install -e .

4. .env を作成し必須環境変数を設定

---

## 使い方（コード例）

以下は主要なユースケースの簡単な例です。実行前に .env の設定と必要ライブラリのインストールを済ませてください。

- DuckDB 接続の作成
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行（価格・財務・カレンダー取得 + 品質チェック）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP スコアリング（OpenAI 必須）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# api_key を明示するか、OPENAI_API_KEY を環境変数で設定
count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"scored {count} codes")
```

- マーケットレジーム判定
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ専用 DB 初期化
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# これで signal_events, order_requests, executions テーブルが作成されます
```

- ニュース RSS 取得（単体）
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
for a in articles[:5]:
    print(a["datetime"], a["title"])
```

注意:
- OpenAI を利用する機能は API キー未設定時に ValueError を投げます。
- DuckDB に対する書き込みは関数ごとにトランザクションを考慮した実装になっていますが、エラー時の挙動はログや例外を確認してください。

---

## 主要モジュール / ディレクトリ構成

（src/kabusys 配下を抜粋）

- kabusys/
  - __init__.py — パッケージ初期設定（__version__ 等）
  - config.py — 環境変数 / 設定読み込みロジック（.env 自動ロード、Settings オブジェクト）
  - ai/
    - __init__.py
    - news_nlp.py — ニュースの集約・OpenAI による銘柄別センチメント（score_news）
    - regime_detector.py — ETF 1321 MA200 とマクロニュースの LLM 評価を合成して市場レジームを判定（score_regime）
  - data/
    - __init__.py
    - calendar_management.py — 市場カレンダー管理、営業日判定、next/prev_trading_day 等
    - etl.py — ETL インターフェース（ETLResult エクスポート）
    - pipeline.py — 日次 ETL、個別 ETL ジョブ（run_daily_etl, run_prices_etl 等）
    - stats.py — zscore_normalize 等の統計ユーティリティ
    - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
    - audit.py — 監査ログスキーマ初期化（signal_events / order_requests / executions）
    - jquants_client.py — J-Quants API クライアント（取得・保存関数）
    - news_collector.py — RSS 収集・前処理・SSRF 対策等
    - pipeline.py — ETL 管理（上記）
  - research/
    - __init__.py
    - factor_research.py — Momentum / Value / Volatility 等のファクター計算
    - feature_exploration.py — 将来リターン計算、IC、統計サマリー等

（ファイル単位で詳細な docstring があり、用途・設計ポリシーが明記されています）

---

## 動作上の注意・トラブルシューティング

- 型注釈で union operator (|) や、from __future__ import annotations を使用しているため Python 3.10 以上を推奨します。
- OpenAI 呼び出しはネットワークや料金に影響します。ローカルテストではモック（unittest.mock）で _call_openai_api を差し替えることを想定しています。
- J-Quants API のレート制限（120 req/min）に配慮した実装がありますが、同時多発アクセスを避けてください。
- .env の自動読み込みを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時に便利です）。
- DuckDB のバージョンに依存する挙動（executemany の空リストの扱い等）に注意している実装になっていますが、実際の環境で動作確認を行ってください。
- ニュース収集は RSS ソースに依存します。RSS の形式やサイズによりパースエラーやスキップが発生する可能性があります（ログを参照してください）。

---

## 開発・貢献

- 各モジュールは docstring に設計方針や処理フローが記載されています。新機能・改善は該当モジュールの docstring を参考に実装してください。
- テストは外部 API を直接叩かないよう、HTTP 呼び出しや OpenAI 呼び出し箇所をモックして実施してください。
- 重要な外部呼び出し（OpenAI・J-Quants・RSS）には再試行・バックオフ・フェイルセーフが実装されていますが、追加の監視やメトリクス収集を導入することを推奨します。

---

README に載せきれない実装上の詳細や API の使用例は各モジュールの docstring を参照してください。必要であれば、特定機能（ETL、news_nlp、regime_detector、audit 初期化 等）に絞った利用ガイドやサンプルスクリプトを別途作成します。希望があれば教えてください。