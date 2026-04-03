# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。ETL、データ品質チェック、ニュース NLP、マーケットレジーム判定、ファクター計算、監査ログなどを備え、J‑Quants API や OpenAI を利用したワークフローを想定しています。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株のデータ収集・品質管理・研究・シグナル生成・監査までを想定したユーティリティ群です。主な用途は次のとおりです。

- J‑Quants API からの株価・財務・カレンダー取得（差分 ETL / ページネーション対応）
- DuckDB を用いたローカルデータストア & 冪等保存
- データ品質チェック（欠損、重複、スパイク、日付不整合）
- RSS ベースのニュース収集と前処理（SSRF 対策、トラッキング除去）
- OpenAI（gpt-4o-mini 等）を用いたニュースのセンチメント（銘柄別 / マクロ）スコアリング
- 市場レジーム判定（ETF の MA とマクロセンチメントの合成）
- 研究用ファクター計算（モメンタム／バリュー／ボラティリティ）と特徴量解析
- 発注・約定を含む監査ログ（監査テーブルの初期化・管理）

設計の共通方針として "ルックアヘッドバイアスの回避"、"ETL の冪等性"、"API 呼び出しのフェイルセーフ化とリトライ" が守られています。

---

## 機能一覧

- data
  - jquants_client: J‑Quants API クライアント（認証・レート制御・リトライ・保存関数）
  - pipeline: 日次 ETL（カレンダー → 株価 → 財務 → 品質チェック）
  - calendar_management: JPX カレンダーの管理（営業日判定、next/prev_trading_day 等）
  - news_collector: RSS 取得・前処理・raw_news 保存（SSRF 対策・トラッキング除去）
  - quality: データ品質チェック（missing / duplicates / spike / date consistency）
  - audit: 監査ログ用テーブル定義と初期化（signal → order_request → execution のトレーサビリティ）
  - stats: zscore_normalize などの統計ユーティリティ
- ai
  - news_nlp.score_news: ニュースを銘柄ごとにまとめて LLM に投げ、ai_scores に保存
  - regime_detector.score_regime: ETF の MA と LLM マクロセンチメントを合成して market_regime に保存
- research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
- config: .env 読み込み、環境変数ラッパー（settings オブジェクト）
- audit 初期化ユーティリティ: init_audit_schema / init_audit_db

---

## 前提・依存関係

- Python 3.10 以上（型注釈の | 演算子や挙動を利用）
- 主な外部パッケージ:
  - duckdb
  - openai
  - defusedxml

インストール例（仮に pyproject.toml がある場合）:

```bash
# 仮想環境を作成・有効化した後
pip install -U pip
pip install duckdb openai defusedxml
# 開発中にソースを editable インストールする場合（pyproject.toml / setup がある場合）
pip install -e .
```

---

## 環境変数 / 設定

KabuSys はプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索し、優先順位に従って環境変数を自動ロードします:

読み込み順: OS 環境変数 > .env.local > .env

自動ロードを無効化する場合:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主要な環境変数（.env に記載する例）:

```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

# OpenAI
OPENAI_API_KEY=sk-...

# kabuステーション（発注等で使用）
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# データベース
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 実行・監視
PID_FILE_PATH=data/execution.pid
KILL_FLAG_PATH=data/kill.flag

# 環境 / ログ
KABUSYS_ENV=development   # development | paper_trading | live
LOG_LEVEL=INFO
```

設定へは `from kabusys.config import settings` でアクセスできます（プロパティ経由）。

例：
```python
from kabusys.config import settings
print(settings.duckdb_path)
```

必須の値（未設定時はエラーになるもの）:
- JQUANTS_REFRESH_TOKEN（jquants のリフレッシュトークン）
- KABU_API_PASSWORD（注文 API を使う場合）

OpenAI の API キーは `OPENAI_API_KEY` または ai 関数の api_key 引数で指定できます。

---

## セットアップ手順

1. リポジトリをクローン

```bash
git clone <repo-url>
cd <repo-dir>
```

2. Python 仮想環境の作成・有効化（例）

```bash
python -m venv .venv
source .venv/bin/activate   # macOS / Linux
.venv\Scripts\activate      # Windows
```

3. 依存パッケージをインストール

```bash
pip install -U pip
pip install duckdb openai defusedxml
# 開発用にパッケージを編集可能インストールする場合
pip install -e .
```

4. 環境変数を設定（.env/.env.local をプロジェクトルートに作成）
   - 上記「環境変数 / 設定」を参照してください。

5. データディレクトリを作る（必要に応じて）

```bash
mkdir -p data
```

---

## 使い方（主要なユースケース）

以下はライブラリをインポートして操作する最小例です。実行は Python スクリプトや REPL で行えます。

- DuckDB 接続を作成

```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL 実行（デフォルトは today、ETLResult を返す）

```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

res = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(res.to_dict())
```

- ニュースのセンチメントをスコアリングして ai_scores に保存

```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# OPENAI_API_KEY を環境変数に設定済みなら api_key 引数は不要
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {count} symbols")
```

- 市場レジームをスコアリングして market_regime に保存

```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用 DB の初期化（別 DB にしたい場合）

```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# これで監査テーブルが作成される
```

- 研究用ファクター計算の例

```python
from kabusys.research.factor_research import calc_momentum
from datetime import date

records = calc_momentum(conn, target_date=date(2026, 3, 20))
# zscore 正規化
from kabusys.data.stats import zscore_normalize
normalized = zscore_normalize(records, ["mom_1m", "mom_3m", "mom_6m", "ma200_dev"])
```

---

## 開発・デバッグのヒント

- 自動 .env 読み込みを無効にしたいときは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時など）。
- OpenAI 呼び出しは内部で再試行・フェイルセーフを持っていますが、API キー不足時は ValueError が投げられます。
- DuckDB の executemany は空リストが渡せない箇所の扱いに注意しています（空チェック済み）。
- news_collector は defusedxml を使って XML を安全にパースし、SSRF 対策を盛り込んでいます。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                      -- 環境変数 / 設定管理
    - ai/
      - __init__.py
      - news_nlp.py                  -- ニュースセンチメント・ai_scores 書き込み
      - regime_detector.py           -- 市場レジーム判定・market_regime 書き込み
    - data/
      - __init__.py
      - jquants_client.py            -- J‑Quants API クライアント & DuckDB 保存
      - pipeline.py                  -- ETL パイプライン（run_daily_etl など）
      - calendar_management.py       -- JPX カレンダー管理
      - news_collector.py            -- RSS 収集・前処理
      - quality.py                   -- データ品質チェック群
      - stats.py                     -- zscore_normalize 等
      - audit.py                     -- 監査テーブル定義・初期化
      - etl.py                       -- ETLResult の再エクスポート
    - research/
      - __init__.py
      - factor_research.py           -- モメンタム/ボラティリティ/バリュー計算
      - feature_exploration.py       -- 将来リターン/IC/summary
    - ai/ (上記)
    - research/ (上記)
- pyproject.toml (プロジェクトルートに存在する想定)
- .env.example (プロジェクトルートに用意すると良い)

各モジュールは docstring に仕様・設計方針・フェイルセーフの挙動が明記されています。

---

## 既知の注意点 / 期待される振る舞い

- 多くの関数は「ルックアヘッド・バイアス」を避けるために date 引数を明示的に受け取り、内部で date.today() を不用意に参照しない設計です。バックテスト用途では必ず過去時点のデータだけを入れて評価してください。
- J‑Quants API は rate limit（120 req/min）をクライアント側で守る実装になっていますが、利用時は自身の利用量にも注意してください。
- OpenAI 呼び出しは JSON mode を使いレスポンスの検証を行いますが、LLM の出力により期待した JSON にならない場合はそのチャンクはスキップされます（フェイルセーフ）。
- DuckDB との互換性（executemany の挙動など）はコード内で考慮していますが、DuckDB のバージョン差異に注意してください。

---

必要であれば以下についても README に追加します：
- フルな .env.example（テンプレート）
- CI / テスト実行方法
- データベースのスキーマ定義（DDL の抜粋）
- 実運用時の監視・デプロイ手順

どれを追加したいか教えてください。