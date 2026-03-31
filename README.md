# KabuSys

KabuSys は日本株向けの自動売買 / データプラットフォーム向けライブラリ群です。  
データ収集（J-Quants）、ETL、データ品質チェック、研究用ファクター計算、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、監査ログ（約定トレーサビリティ）などを含みます。

---

## 主要な特徴

- J-Quants API 経由での差分取得（株価・財務・上場情報・カレンダー）
  - レート制限・リトライ・トークン自動リフレッシュ対応
- DuckDB を中心としたローカル DB 保存（冪等書き込み）
- 日次 ETL パイプライン（run_daily_etl）
- データ品質チェック（欠損、重複、スパイク、日付不整合）
- ニュース収集（RSS）と前処理、安全対策（SSRF 防止など）
- ニュース NLP（OpenAI）による銘柄別センチメント（score_news）
- 市場レジーム判定（ETF の MA200 とマクロ記事センチメントを合成）
- 研究用ファクター計算（モメンタム、ボラティリティ、バリュー等）
- 監査ログスキーマ（signal / order_request / executions）と初期化ユーティリティ

---

## 必要な環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API 用パスワード（必須）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID — Slack チャネル ID（必須）
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime 使用時に必須）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境（development / paper_trading / live、デフォルト development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）

注意: パッケージ起動時にプロジェクトルート（.git か pyproject.toml がある親ディレクトリ）を探索し `.env` / `.env.local` を自動読み込みします。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

.example の .env（参考）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. Python 仮想環境を作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```

2. 必要パッケージをインストール（最低限）
   ```
   pip install duckdb openai defusedxml
   ```
   プロジェクトに requirements.txt がある場合はそれを利用してください。

3. 環境変数を設定（上記 .env をプロジェクトルートに配置するか環境変数で設定）

4. DuckDB ファイルや data ディレクトリを用意（多くの初期化関数が自動で作成します）
   ```
   mkdir -p data
   ```

---

## 使い方（主要な例）

- DuckDB 接続と設定読み込み
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 監査ログ DB を初期化（ファイル作成 + スキーマ適用）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db(settings.duckdb_path)  # ":memory:" も可
```

- 日次 ETL を実行（市場カレンダー・株価・財務・品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースの収集（RSS をフェッチ）
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```

- ニュース NLP スコアリング（OpenAI API キーは環境変数か api_key 引数）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

n = score_news(conn, target_date=date(2026, 3, 20))  # returns 書き込んだ銘柄数
```

- 市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

- 研究用ファクター（例: モメンタム計算）
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date

records = calc_momentum(conn, date(2026, 3, 20))
# records は各銘柄の辞書リストを返す
```

- データ品質チェックを個別に実行
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=date(2026, 3, 20))
for issue in issues:
    print(issue.check_name, issue.severity, issue.detail)
```

---

## 実装上の注意・設計方針（抜粋）

- Look-ahead bias を避けるため、関数は基本的に内部で date.today() / datetime.today() を参照せず、呼び出し側から target_date を渡す設計になっています。
- J-Quants クライアントはレートリミット（120 req/min）・リトライ・401 リフレッシュに対応しています。
- OpenAI 呼び出し部分はリトライや JSON 検証のフォールバックを備えています。API が失敗した場合は安全側のデフォルト（例: スコア 0.0）にフォールバックします。
- DB への保存は可能な限り冪等（ON CONFLICT / DO UPDATE）にしています。
- ニュース収集では SSRF 対策や受信サイズ制限、defusedxml による XML 処理を行っています。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py — パッケージ初期化、バージョン情報
- config.py — 環境変数 / 設定管理（自動 .env ロード、Settings クラス）

src/kabusys/ai/
- __init__.py
- news_nlp.py — ニュース文章から銘柄別スコアを生成して ai_scores テーブルへ保存
- regime_detector.py — ETF (1321) の MA200 とニュースセンチメントを合成して market_regime を作成

src/kabusys/data/
- __init__.py
- jquants_client.py — J-Quants API クライアント（取得 + DuckDB 保存関数）
- pipeline.py — ETL パイプライン（run_daily_etl 等）
- etl.py — ETLResult 再エクスポート
- calendar_management.py — 市場カレンダーの判定・検索・更新ジョブ
- stats.py — z-score 正規化などの統計ユーティリティ
- quality.py — データ品質チェック（欠損・重複・スパイク・日付整合性）
- audit.py — 監査ログスキーマ初期化（signal / order_requests / executions）
- news_collector.py — RSS ニュース収集、前処理、保存補助

src/kabusys/research/
- __init__.py
- factor_research.py — Momentum / Volatility / Value 等のファクター計算
- feature_exploration.py — 将来リターン計算、IC（情報係数）、統計サマリー

---

## よくある質問

- Q: OpenAI キーが無いと何が動きますか？  
  A: データ収集・ETL・品質チェック・ファクター計算・監査テーブル初期化等は問題なく動きます。ニュース NLP / レジーム判定は OPENAI_API_KEY が必要です（関数引数で直接渡すことも可能）。

- Q: .env はどこに置けばよいですか？  
  A: プロジェクトルート（.git または pyproject.toml のある親ディレクトリ）に `.env` / `.env.local` を置くと自動で読み込まれます。自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。

- Q: DuckDB の初期スキーマはどこにある？  
  A: 本リポジトリにはデータスキーマ作成用のユーティリティ（audit.init_audit_schema など）があります。プロジェクト毎に schema 初期化ロジックを用意する想定です。

---

## 貢献・拡張案

- 追加のニュースソースや RSS パーサの拡張
- kabu ステーション（実際の発注）との連携モジュール
- 研究用のバックテストエンジンとの統合
- スキーマや ETL の CI 用サンプルデータ・テストケースの追加

---

問題報告や改善提案があれば、Issue を立ててください。README の補足や実行例の追加を希望される場合は、どの操作に関する例が欲しいかお知らせください。