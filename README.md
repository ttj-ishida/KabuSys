# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ群です。  
データ収集（J-Quants / RSS）、ETL、データ品質チェック、特徴量計算（ファクター）、LLM を使ったニュースセンチメント、監査ログ（トレーサビリティ）などを提供します。

主にバックテストや運用バッチで使うことを想定したモジュール群で、DuckDB を主要なオンディスクデータストアとして利用します。

---

## 主な機能一覧

- 環境設定管理
  - .env 自動ロード（プロジェクトルート検出、.env / .env.local）
  - 必須環境変数のラッパー（settings オブジェクト）
- データ取得（J-Quants クライアント）
  - 日次株価（OHLCV）、財務諸表、上場情報、JPX カレンダーの取得・保存
  - レートリミット管理、リトライ、トークン自動リフレッシュ
- ETL パイプライン
  - 差分取得・保存（raw_prices / raw_financials / market_calendar）
  - 品質チェック（欠損・重複・スパイク・日付不整合）
  - 日次 ETL の統合エントリポイント
- ニュース収集
  - RSS 取得（SSRF 対策、トラッキングパラメータ除去、前処理）
  - raw_news / news_symbols へ冪等保存
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュースセンチメントを LLM でスコア化（ai_scores テーブルへ保存）
  - マクロニュースの LLM 評価と ETF MA200 乖離を合成して市場レジーム判定
  - API 遅延・失敗時の堅牢なフォールバック / リトライ処理
- 研究系ユーティリティ
  - モメンタム・ボラティリティ・バリューなどのファクター計算
  - 将来リターン計算、IC（スピアマン）計算、Zスコア正規化、統計サマリー
  - 外部依存を極力排した実装（標準ライブラリ + DuckDB SQL）
- 監査ログ（Audit）
  - signal_events / order_requests / executions テーブル定義と初期化ユーティリティ
  - UUID ベースのトレーサビリティを保証

---

## 必要条件

- Python 3.10 以上（PEP 604 の型記法などを利用）
- DuckDB
- OpenAI Python SDK（LLM 呼び出し）
- defusedxml（RSS パースの安全対策）
- その他標準ライブラリ

例（最小インストール例）:
```bash
python -m pip install "duckdb" "openai" "defusedxml"
```

プロジェクトをパッケージとして開発環境に入れる場合:
```bash
git clone <repo>
cd <repo>
python -m pip install -e .
# もしくは requirements.txt / poetry を用意している場合は適宜インストール
```

---

## 環境変数（.env の例）

自動ロードはプロジェクトルート（.git / pyproject.toml のあるディレクトリ）から .env / .env.local を読み込みます。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主要な環境変数（README 用の例）:

```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

# kabuステーション API
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# OpenAI
OPENAI_API_KEY=sk-...

# Slack 通知
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=CXXXXXXX

# データベースパス（省略時は data/ 以下が既定）
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 実行環境フラグ (development | paper_trading | live)
KABUSYS_ENV=development

# ログレベル (DEBUG | INFO | WARNING | ERROR | CRITICAL)
LOG_LEVEL=INFO
```

注意:
- Settings で必須（_require）になっている変数は未設定だと ValueError が投げられます（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD）。
- .env.local が存在する場合は .env の上書き（優先）となります（OS 環境変数は最優先で保護されます）。

---

## セットアップ手順（ローカルでの準備）

1. リポジトリをクローン / 取得
   ```bash
   git clone <repo>
   cd <repo>
   ```
2. Python 環境の作成（推奨: venv）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```
3. 依存パッケージをインストール
   ```bash
   python -m pip install -U pip
   python -m pip install duckdb openai defusedxml
   # プロジェクトを編集可能インストール
   python -m pip install -e .
   ```
4. .env を作成して必要な環境変数を設定
   - README の「環境変数」セクションを参考に `.env` を作成
5. DuckDB データベースフォルダを作成（必要なら）
   ```bash
   mkdir -p data
   ```

---

## 使い方（代表的な例）

各例は Python REPL / スクリプト内で実行できます。DuckDB 接続には `duckdb.connect(path)` を使ってください。

1) 日次 ETL を実行する（J-Quants から差分取得 → 保存 → 品質チェック）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")  # ファイルパスまたは ":memory:"
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースセンチメントを計算して ai_scores に保存（OpenAI API が必要）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使う場合は None
print(f"書き込んだ銘柄数: {n_written}")
```

3) 市場レジーム（bull/neutral/bear）を判定して market_regime に保存
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

4) 研究用ファクター計算（calc_momentum / calc_volatility / calc_value）
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
value = calc_value(conn, date(2026, 3, 20))
# 結果はリストの辞書形式で返る
```

5) 監査ログ（audit）テーブルの初期化 / 専用 DB の作成
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")  # ディレクトリがなければ自動作成
# 以後 conn を使って signal_events / order_requests / executions を操作
```

6) データ品質チェックを個別に実行
```python
from kabusys.data.quality import run_all_checks
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
issues = run_all_checks(conn, target_date=date(2026, 3, 20))
for i in issues:
    print(i)
```

注意点:
- LLM（OpenAI）呼び出しを伴う処理は API キー（OPENAI_API_KEY）を適切に設定してください。API 利用に伴うコストとレートリミットに注意。
- ETL / データ取得処理は J-Quants の認証トークン（JQUANTS_REFRESH_TOKEN）が必要です。
- 自動ロードされる .env の取り扱いに注意。テスト時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動読み込みを抑止できます。

---

## ディレクトリ構成（主要ファイル）

以下は `src/kabusys` 配下の主要モジュール構成です（抜粋）。

- src/
  - kabusys/
    - __init__.py
    - config.py                   # 環境変数 / 設定読み込み
    - ai/
      - __init__.py
      - news_nlp.py               # ニュースセンチメント（銘柄別）
      - regime_detector.py        # マクロ + MA200 を合成した市場レジーム判定
    - data/
      - __init__.py
      - jquants_client.py         # J-Quants API クライアント（取得 + DuckDB 保存）
      - pipeline.py               # ETL パイプライン（run_daily_etl 等）
      - quality.py                # 品質チェック（欠損・重複・スパイク・日付不整合）
      - news_collector.py         # RSS ニュース収集
      - calendar_management.py    # 市場カレンダー管理（営業日判定）
      - stats.py                  # 共通統計ユーティリティ（zscore_normalize）
      - audit.py                  # 監査ログ（テーブル定義・初期化）
      - etl.py                    # ETLResult の公開 re-export
    - research/
      - __init__.py
      - factor_research.py        # momentum/value/volatility 計算
      - feature_exploration.py    # 将来リターン・IC・統計サマリー

---

## 設計上の注意 / 運用上のポイント

- ルックアヘッドバイアス対策
  - 多くの関数は内部で `date.today()` / `datetime.today()` を参照せず、明示的な `target_date` を受け取る設計です。バックテストで日付を固定して利用してください。
- 冪等性
  - J-Quants 保存やニュース保存、監査テーブルの初期化は冪等となるよう設計されています（ON CONFLICT / PRIMARY KEY を活用）。
- エラーハンドリング
  - LLM や外部 API 呼び出しはリトライ・フォールバック（ゼロ値など）を実装し、全体処理が破綻しないように配慮しています。ただし、API失敗時はスコアが欠損するため結果解釈に注意してください。
- テスト可能性
  - OpenAI / HTTP 呼び出し部分はモック差し替えが容易になるよう個別関数に分離されています（ユニットテストで patch 可能）。
- セキュリティ
  - RSS 取得では SSRF 対策、XML の脆弱性軽減（defusedxml）等を導入しています。運用時にもネットワーク制御を推奨します。

---

## 開発・貢献

バグ報告や機能提案は Issue を作成してください。大きな変更を加える場合は事前に Issue で相談のうえ、Pull Request を送ってください。

---

README に記載の内容はコードの現状に基づく要約です。実際の利用にあたっては各モジュールの docstring / 関数シグネチャを参照してください。必要であればサンプルスクリプト・ユニットテスト例を追加で作成できます。