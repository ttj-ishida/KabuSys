# KabuSys

日本株向け自動売買 / データプラットフォーム用ライブラリ (KabuSys)

このリポジトリは、日本株のデータ取得・ETL、ニュース NLP、リサーチ用ファクター計算、監査ログなどを含む自動売買プラットフォームのコンポーネント群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を主な目的とする Python モジュール群です。

- J-Quants API を用いた株価・財務・カレンダーデータの差分取得と DuckDB への保存（ETL）
- RSS ベースのニュース収集と前処理（raw_news テーブル）
- OpenAI（gpt-4o-mini）を利用したニュースのセンチメント解析（銘柄別 ai_score）やマクロセンチメントを含めた市場レジーム判定
- 研究用ユーティリティ（ファクター計算、将来リターン、IC 計算、Z スコア正規化）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログ（signal → order_request → executions）のスキーマ定義と初期化ユーティリティ

設計上の特徴:
- DuckDB を主要な永続層として利用
- Look-ahead bias を避ける日付取り扱い設計
- API 呼び出しに対する堅牢なリトライ/バックオフやレート制御
- 冪等性を意識した保存処理（ON CONFLICT / DELETE→INSERT パターン）
- テスト容易性を考慮した API キー注入・モック差し替えポイント

---

## 主な機能一覧

- データ取得 / ETL
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（kabusys.data.pipeline）
  - J-Quants API クライアント（kabusys.data.jquants_client）
- ニュース収集 / 前処理
  - RSS フィード取得、URL 正規化、トラッキング削除、SSRF 対策（kabusys.data.news_collector）
- ニュース NLP / レジーム判定
  - 銘柄別ニュースセンチメント（score_news, kabusys.ai.news_nlp）
  - マクロ + MA を組み合わせた市場レジーム判定（score_regime, kabusys.ai.regime_detector）
- 研究用ユーティリティ
  - momentum / volatility / value のファクター計算（kabusys.research.factor_research）
  - 将来リターン / IC / 統計サマリ（kabusys.research.feature_exploration）
  - Z スコア正規化（kabusys.data.stats）
- データ品質チェック
  - 欠損・スパイク・重複・日付不整合（kabusys.data.quality）
- 監査ログスキーマ
  - 監査テーブルの初期化・DB 作成ヘルパー（kabusys.data.audit）

---

## セットアップ手順

前提: Python 3.10+ を推奨（typing の一部表記に依存）

1. リポジトリをクローン
   ```bash
   git clone <このリポジトリのURL>
   cd <repo>
   ```

2. 仮想環境を作成・有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール
   - 代表的な依存パッケージ:
     - duckdb
     - openai
     - defusedxml
   - 例:
   ```bash
   pip install duckdb openai defusedxml
   ```
   （パッケージ一覧はプロジェクトの requirements.txt / pyproject.toml があればそちらを優先してください）

4. 環境変数 (.env) を用意
   - プロジェクトルート（.git があるディレクトリ）に `.env` /  `.env.local` を置くと自動で読み込まれます（優先順: OS 環境変数 > .env.local > .env）。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

5. 主な必須環境変数（.env に設定する例）
   ```
   # J-Quants
   JQUANTS_REFRESH_TOKEN=xxxxx

   # OpenAI
   OPENAI_API_KEY=sk-xxxxx

   # kabuステーション（発注用）
   KABU_API_PASSWORD=your_kabu_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi  # オプション

   # Slack 通知
   SLACK_BOT_TOKEN=xoxb-xxx
   SLACK_CHANNEL_ID=C0123456789

   # DB パス（省略時はデフォルトを使用）
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db

   # 環境
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（代表的なユースケース例）

以下は Python REPL / スクリプト内での利用例です。実行前に環境変数や DB の準備を行ってください。

- DuckDB 接続を使って日次 ETL を走らせる
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントのスコアを計算して ai_scores に書き込む
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # env の OPENAI_API_KEY を使う
print("書き込み銘柄数:", n_written)
```

- 市場レジーム（bull/neutral/bear）を判定して market_regime に書き込む
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY を参照
```

- 監査ログ用 DB の初期化
```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

conn = init_audit_db(settings.duckdb_path)  # transactional=True/False は引数で制御可能
```

- 研究ユーティリティの呼び出し（ファクター計算例）
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
target = date(2026, 3, 20)
mom = calc_momentum(conn, target)
val = calc_value(conn, target)
vol = calc_volatility(conn, target)
```

注意点:
- OpenAI API 呼び出しを行う関数は `api_key` を引数で受け取れます（引数が None の場合は環境変数 OPENAI_API_KEY を使用します）。テスト時は内部の `_call_openai_api` をモックできます。
- ETL / API 呼び出しにはネットワークや API キーの設定が必要です。ローカルでの動作確認は API 呼び出しをモックしてください。

---

## 設定（環境変数）まとめ

重要な環境変数:
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）
- KABU_API_PASSWORD: kabuステーション API パスワード（発注機能使用時）
- KABU_API_BASE_URL: kabu API ベース URL（省略可）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知に使用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_ENV: development / paper_trading / live（デフォルト development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL

.env の自動読み込み:
- プロジェクトルート（.git または pyproject.toml を基準）から `.env` と `.env.local` を自動ロードします。
- 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                         — 環境変数/設定管理
- ai/
  - __init__.py                      — score_news を公開
  - news_nlp.py                       — ニュース NLP（銘柄別センチメント）
  - regime_detector.py                — 市場レジーム判定（MA200 + マクロセンチメント）
- data/
  - __init__.py
  - jquants_client.py                 — J-Quants API クライアント + 保存処理
  - pipeline.py                       — ETL パイプライン（run_daily_etl など）
  - etl.py                            — ETLResult の公開
  - news_collector.py                 — RSS 収集 / 前処理
  - calendar_management.py            — マーケットカレンダー管理（営業日判定など）
  - stats.py                          — Z スコア正規化等の統計ユーティリティ
  - quality.py                        — データ品質チェック
  - audit.py                          — 監査ログテーブルの定義と初期化
- research/
  - __init__.py
  - factor_research.py                — モメンタム/バリュー/ボラティリティ計算
  - feature_exploration.py            — 将来リターン / IC / 統計サマリ
- (その他) strategy/, execution/, monitoring/ が公開 API に含まれる想定（実装は別途）

ドキュメント・設定例:
- .env.example（プロジェクトルートに用意することを推奨）

---

## 開発・テスト上の注意

- OpenAI / J-Quants など外部 API を呼び出す箇所はモック可能な抽象化（関数差し替え）を備えています。ユニットテストでは外部呼び出しをモックして実行してください。
- DuckDB に対する一括 INSERT/DELETE は executemany を使う実装が多く、空配列を渡すと問題になる箇所があります（コード内で空チェック済み）。
- time/date の扱いは Look-ahead bias 回避のため設計されています。関数は内部で date.today()/datetime.today() を直接参照しない実装を心がけています（例外あり）。テスト時は明示的に target_date を渡してください。

---

必要であれば README にサンプルの .env.example、コマンドラインツールの使い方、CI 設定、詳細な API ドキュメント（関数シグネチャごとの説明）などを追加できます。追加希望があれば教えてください。