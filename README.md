# KabuSys

KabuSys は日本株のデータ収集・品質管理・リサーチ・AI ベースのニュースセンチメント評価・監査ログ管理までを含む、日本株向け自動売買プラットフォームのライブラリ群です。DuckDB をデータ層に用い、J-Quants API や RSS、OpenAI（gpt-4o-mini）等と連携して ETL / 解析 / 監査 / 戦略構築を支援することを目的としています。

バージョン: 0.1.0

---

## 機能一覧

- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須環境変数チェック（settings オブジェクト）

- Data（ETL / データ品質 / カレンダー）
  - J-Quants API クライアント（差分取得、ページネーション、トークン自動リフレッシュ、レート制御）
  - 日次 ETL パイプライン（株価・財務・市場カレンダーの差分取得と保存）
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
  - ニュース収集（RSS → raw_news、SSRF/サイズ/トラッキング対策）
  - 市場カレンダー管理（営業日判定、next/prev_trading_day 等）
  - 監査ログ（signal / order_request / executions）テーブル作成・初期化

- AI（ニュース NLP / 市場レジーム判定）
  - ニュースセンチメント評価（銘柄ごとに OpenAI に送信して ai_scores へ保存）
  - 市場レジーム判定（ETF 1321 の MA200 乖離とマクロ記事の LLM センチメントを合成）

- Research（因子計算・特徴量探索）
  - Momentum / Value / Volatility 等のファクター計算
  - 将来リターン計算、IC（スピアマン）計算、統計サマリー、Zスコア正規化

- ユーティリティ
  - 統計関数（zscore_normalize 等）
  - DuckDB ベースの監査データベース初期化ユーティリティ

---

## 必要環境・依存パッケージ

- Python >= 3.10（タイプヒントに `|` を使用）
- 主要依存:
  - duckdb
  - openai（OpenAI Python SDK）
  - defusedxml
- 事前に pip でインストールしてください。例:

```bash
python -m pip install duckdb openai defusedxml
```

（プロジェクトで追加のパッケージが必要な場合は pyproject.toml / requirements.txt を参照してください）

---

## 環境変数

以下の環境変数が使用されます（多くは必須）:

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu ステーション API 用パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（省略時: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使うとき必須）
- DUCKDB_PATH: DuckDB ファイルパス（省略時: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（省略時: data/monitoring.db）
- KABUSYS_ENV: 実行環境 ("development" | "paper_trading" | "live")（省略時: development）
- LOG_LEVEL: ログレベル（"DEBUG" | "INFO" | ...）（省略時: INFO）

自動的にプロジェクトルートの `.env` → `.env.local` を読み込みます（OS 環境変数が優先）。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

.env ファイル例（参考）:

```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=your_openai_api_key
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
```

---

## セットアップ手順

1. リポジトリをクローン／取得
2. Python 仮想環境を作成・有効化（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows (PowerShell/Cmd)
   ```
3. 依存パッケージをインストール
   ```bash
   python -m pip install --upgrade pip
   python -m pip install duckdb openai defusedxml
   ```
4. 環境変数を設定（.env または環境変数）
   - プロジェクトルートに `.env` や `.env.local` を置くことで自動読み込みされます
5. DuckDB データディレクトリ作成（必要に応じて）
   ```bash
   mkdir -p data
   ```

---

## 使い方（代表的な例）

ここでは一部の主要ユースケースの Python スニペットを示します。実行はプロジェクトルートで行ってください。

- DuckDB 接続の取得例:

```python
import duckdb
from pathlib import Path
db_path = Path("data/kabusys.duckdb")
conn = duckdb.connect(str(db_path))
```

- ETL（日次 ETL）の実行例:

```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# conn は duckdb connection
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント評価（OpenAI キー必須）:

```python
from datetime import date
from kabusys.ai.news_nlp import score_news

n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使用
print(f"ai_scores に書き込んだ銘柄数: {n_written}")
```

- 市場レジーム判定（OpenAI キー必須）:

```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ DB 初期化（監査専用 DB を作る）:

```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/kabusys_audit.duckdb")
# これで監査用テーブル群が作成されます
```

- ファクター計算（Research）:

```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

momentum = calc_momentum(conn, date(2026,3,20))
vol = calc_volatility(conn, date(2026,3,20))
value = calc_value(conn, date(2026,3,20))
```

---

## 自動読み込み・テスト時の挙動

- パッケージ初期化時に `.env` / `.env.local` を自動読み込みします（プロジェクトルートは .git または pyproject.toml を基準に探索）。CWD に依存しない仕様です。
- 自動読み込みを無効化するには、実行環境で `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（ユニットテスト等で便利です）。
- OpenAI 呼び出し関数やネットワーク I/O の一部はユニットテストで差し替え可能なように設計されています（例: モジュール内の `_call_openai_api` を patch するなど）。

---

## ディレクトリ構成

（src 配下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py                     - 環境設定・.env ローダー
  - ai/
    - __init__.py
    - news_nlp.py                  - ニュース NLP（銘柄別 ai_scores 書込み）
    - regime_detector.py           - 市場レジーム判定（ma200 + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py            - J-Quants API クライアント（取得・保存）
    - pipeline.py                  - ETL パイプライン / run_daily_etl 等
    - etl.py                       - ETLResult の公開
    - news_collector.py            - RSS ニュース収集（SSRF/サイズ対策）
    - calendar_management.py       - 市場カレンダー管理（営業日判定）
    - quality.py                   - データ品質チェック
    - stats.py                     - 統計ユーティリティ（zscore）
    - audit.py                     - 監査ログテーブル初期化・DB 作成
  - research/
    - __init__.py
    - factor_research.py           - Momentum / Volatility / Value
    - feature_exploration.py       - 将来リターン / IC / 統計サマリー
  - ai/, data/, research/ 以下にそれぞれの公開 API を提供

（上記以外に strategy / execution / monitoring 等の名前が __init__ でエクスポートされる想定がありますが、今回のコードベース内で確認できるのは上記ファイルです）

---

## ロギングと実行モード

- 環境変数 `KABUSYS_ENV` により挙動フラグが切り替わります（development / paper_trading / live）。
- `LOG_LEVEL` でログ出力レベルを調整できます（デフォルト: INFO）。

---

## 注意事項 / 設計上のポイント

- Look-ahead bias（未来参照）を避ける設計方針が一貫して適用されています。ほとんどの関数は内部で `date.today()` に依存せず、明示的な `target_date` を受け取る設計です。
- OpenAI / J-Quants 等の外部 API 呼び出しはリトライ、バックオフ、フェイルセーフ（失敗時はスコア 0 やスキップ）を備えています。
- DuckDB に対する INSERT は基本的に冪等（ON CONFLICT DO UPDATE）を想定。
- RSS ニュース収集は SSRF、XML Bomb、サイズ超過、トラッキングパラメータ等に対する各種防御策を実装しています。

---

## 貢献・拡張

- 新しい ETL ソースや戦略を追加する場合は data/jquants_client.py や data/pipeline.py、research 以下に実装を追加してください。
- AI モデルやプロンプト改善は kabusys/ai 配下で行ってください。OpenAI SDK のバージョン差異に注意して実装（エラーハンドリング）を保ってください。

---

必要であれば README にサンプル .env.example、より詳細な API 参照（関数一覧と引数説明）、デプロイ手順（systemd / Docker / CI）等を追加できます。どの内容を拡張したいか教えてください。