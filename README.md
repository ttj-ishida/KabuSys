# KabuSys

日本株向けの自動売買／データプラットフォームライブラリです。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュース収集・NLP（OpenAI）、市場レジーム判定、リサーチ用ファクター計算、監査ログなどを一貫して提供します。

主な設計方針
- ルックアヘッドバイアスを防ぐ（内部で date.today() 等に依存しない設計）
- DuckDB を中心としたローカルデータレイヤ
- 外部 API 呼び出しに対して堅牢なリトライ・レートリミット制御
- 冪等性を重視した DB 書き込み（ON CONFLICT ベース）
- 品質チェックでデータの健全性を保つ

---

## 機能一覧
- 環境設定管理
  - .env / .env.local を自動読み込み（プロジェクトルート検出）
  - 必須環境変数を Settings クラスで取得可能
- データ取得（J-Quants クライアント）
  - 日次株価（OHLCV）、財務データ、JPX マーケットカレンダー、上場銘柄情報取得
  - レートリミット制御、トークン自動リフレッシュ、ページネーション対応、リトライ
  - DuckDB への冪等保存関数
- ETL パイプライン
  - 日次 ETL（カレンダー → 株価 → 財務 → 品質チェック）
  - 差分更新・バックフィル対応
  - ETL 実行結果を ETLResult で取得
- データ品質チェック
  - 欠損・スパイク・重複・日付不整合などの検出
  - QualityIssue 型で詳細を収集
- ニュース収集
  - RSS フィード取得、前処理、raw_news への冪等保存（SSRF・XML Bomb 対策あり）
- ニュース NLP / AI
  - 銘柄ごとのニュースセンチメント算出（OpenAI gpt-4o-mini を利用）
  - マクロニュースから市場レジーム（bull/neutral/bear）判定
  - API 呼び出しはリトライ・フェイルセーフを持つ
- 監査ログ（audit）
  - signal_events / order_requests / executions テーブル定義
  - 監査用 DuckDB 初期化ユーティリティ
- Research ユーティリティ
  - Momentum / Value / Volatility 等のファクター計算
  - 将来リターン計算、IC（スピアマン）計算、Zスコア正規化、統計サマリー

---

## セットアップ手順

前提
- Python 3.10+ （typing の union 型や型注釈を利用）
- Git, ネットワーク接続（API 利用時）

1. リポジトリをクローン
   ```
   git clone <this-repo-url>
   cd <this-repo>
   ```

2. 仮想環境の作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージのインストール（例）
   - 最低限必要なパッケージ:
     - duckdb
     - openai
     - defusedxml
   例:
   ```
   pip install duckdb openai defusedxml
   ```
   （プロジェクトで requirements.txt / pyproject.toml があればそちらを使ってください）

4. 環境変数の設定
   - プロジェクトルートの .env または .env.local に設定できます。自動ロードの挙動:
     - OS 環境変数 > .env.local > .env の順で優先
     - 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
   - 必須の環境変数（Settings 参照）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API パスワード（売買実行で使用）
     - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID — Slack 通知対象チャンネル ID
     - OPENAI_API_KEY — OpenAI を利用する機能で必要（score_news / score_regime 等）
   - 任意/デフォルト:
     - KABUSYS_ENV — "development" / "paper_trading" / "live"（デフォルト development）
     - LOG_LEVEL — "DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL"（デフォルト INFO）
     - KABU_API_BASE_URL — kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH — 監視用途の SQLite パス（デフォルト data/monitoring.db）

   サンプル .env:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   ```

5. DuckDB スキーマ・監査 DB の初期化（例）
   - 監査専用 DB を作る場合:
   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   ```
   - ETL 等で使用するメイン DB は用途に応じてテーブル作成ユーティリティ（本リポジトリのスキーマ初期化機能）を用いてください。

---

## 使い方（代表的な例）

- 設定参照
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)  # 必須: 未設定なら例外
```

- DuckDB 接続
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL の実行
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)
print(result.to_dict())
```

- ニュースのスコアリング（OpenAI 必須）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# OPENAI_API_KEY が環境変数に設定されているか、api_key 引数で渡す
num_written = score_news(conn, target_date=date(2026, 3, 20))
print("written:", num_written)
```

- マーケットレジーム判定（1321 を使用）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

- RSS フェッチ（ニュース収集）
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```

- 監査ログ初期化（既出）
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
```

- リサーチ API（例: モメンタム）
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date

factors = calc_momentum(conn, target_date=date(2026, 3, 20))
# z-score 正規化
from kabusys.data.stats import zscore_normalize
normed = zscore_normalize(factors, ["mom_1m", "mom_3m", "mom_6m"])
```

---

## 環境変数 / 設定一覧（要点）
- JQUANTS_REFRESH_TOKEN (必須)
- OPENAI_API_KEY (AI 機能利用時に必須)
- KABU_API_PASSWORD (実取引連携時に必須)
- KABU_API_BASE_URL (任意、デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID (通知用)
- DUCKDB_PATH (デフォルト data/kabusys.duckdb)
- SQLITE_PATH (デフォルト data/monitoring.db)
- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で .env 自動ロードを無効化可能

---

## ディレクトリ構成（主要ファイル）
（ルートに src/kabusys パッケージを想定）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py             — ニュースの OpenAI スコアリング
    - regime_detector.py      — マーケットレジーム判定
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント + 保存ロジック
    - pipeline.py             — ETL パイプライン (run_daily_etl 等)
    - etl.py                  — ETL 公開インターフェース（ETLResult 再エクスポート）
    - news_collector.py       — RSS 収集・前処理
    - calendar_management.py  — 市場カレンダー管理 / 営業日ロジック
    - quality.py              — データ品質チェック
    - stats.py                — 汎用統計ユーティリティ（zscore）
    - audit.py                — 監査ログ（テーブル定義と初期化）
  - research/
    - __init__.py
    - factor_research.py      — Momentum / Value / Volatility 等
    - feature_exploration.py  — 将来リターン、IC、統計サマリー
  - ai/、research/、data/ 以下にさらに詳細な機能が含まれます。

---

## 運用上の注意
- OpenAI API や J-Quants API の利用は有料・レート制限あり。API キーは適切に管理してください。
- 実際の売買実行（kabuステーション連携）は取り扱い注意（テスト環境で十分検証を行ってください）。
- ETL・AI 呼び出しによりキーやトークンが必要です。CI/Test では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使用して外部環境を固定できます。
- DuckDB の executemany はバージョン差異に注意（空リストでの呼び出し回避等がコードに反映されています）。

---

## 貢献・開発
- バグ報告・機能要望は issue を作成してください。
- コード貢献時はユニットテストを追加し、環境依存のテストはモックで代替することを推奨します（外部 API 呼び出しはモックすべき）。

---

README に含めるべき追加情報や、サンプル .env.example の生成、あるいは CI 用のセットアップ手順が必要であれば指示してください。