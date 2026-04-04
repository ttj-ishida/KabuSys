# KabuSys

日本株向けの自動売買／データ基盤ライブラリ兼ツール群です。  
DuckDB を用いたデータプラットフォーム、J-Quants / RSS 収集、ニュースの NLP 評価（OpenAI）、研究用ファクター計算、監査ログ（発注 → 約定のトレーサビリティ）といった機能を備えています。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の主要コンポーネントで構成されます。

- data: J-Quants からの ETL、カレンダー管理、ニュース収集、データ品質チェック、監査ログ（order / execution）スキーマ 初期化等
- ai: ニュース NLP（銘柄別センチメント付与）と市場レジーム判定（MA200 とマクロニュースの LLM 判定を合成）
- research: ファクター計算（モメンタム / バリュー / ボラティリティ）や特徴量解析ユーティリティ
- config: 環境変数管理・Settings（.env 自動読み込み、必須トークンの取得）
- その他、監視・実行モジュール（発注・モニタリング等のための基盤が想定されます）

設計方針の要点:
- ルックアヘッドバイアスを避ける（内部で date.today()/datetime.today() を直接参照しない実装指針）
- 冪等性（DB 書き込みは ON CONFLICT 等で重複を上書き）
- フェイルセーフ（外部 API 失敗時はスコア 0 やスキップで処理継続）
- DuckDB をデータ格納の主要 DB として使用

---

## 主な機能一覧

- ETL
  - J-Quants から株価（daily quotes）、財務データ、JPX マーケットカレンダーを差分取得・保存（fetch / save）
  - run_daily_etl で日次 ETL（カレンダー → 株価 → 財務 → 品質チェック）を実行
- データ品質チェック
  - 欠損（OHLC 欠損）、スパイク検出、重複、日付不整合（未来日付、非営業日のデータ）
- ニュース収集
  - RSS 取得・前処理・SSRF 防御・トラッキングパラメータ除去・raw_news 保存（冪等）
- ニュース NLP（OpenAI）
  - 銘柄別のニュースをまとめて LLM に投げ、ai_scores を書き込む（score_news）
  - 市場レジーム判定: ETF 1321 の MA200 乖離 + マクロニュースの LLM センチメントを合成（score_regime）
- 研究用ファクター計算
  - calc_momentum, calc_value, calc_volatility（各ファクターを DuckDB から計算）
  - calc_forward_returns / calc_ic / factor_summary / zscore_normalize 等
- 監査ログ（audit）
  - signal_events / order_requests / executions テーブルを初期化するユーティリティ（init_audit_schema / init_audit_db）
- 設定管理
  - .env / .env.local 自動読み込み（プロジェクトルートは .git または pyproject.toml を基準）
  - 環境変数の必須チェック（例: JQUANTS_REFRESH_TOKEN）

---

## セットアップ手順

前提:
- Python 3.10+（typing 表記から推測）
- ネットワークアクセス（J-Quants / OpenAI / RSS）

例: 仮想環境を作成して開発インストールする手順の一例

1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. パッケージインストール（最低依存想定）
   - pip install duckdb openai defusedxml

   （プロジェクトに pyproject.toml / requirements.txt があればそちらを使用してください。
   実行開発用には logging 設定や追加ライブラリが必要になる場合があります。）

3. 開発インストール（パッケージとして使う場合）
   - pip install -e .

4. 環境変数／.env の準備
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` を置くと自動読み込みされます。
   - 自動ロードを無効化したい場合:
     - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

必須 / 主要環境変数（Settings から）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- OPENAI_API_KEY: OpenAI 呼び出し（score_news / score_regime）の場合に必要（関数は引数で渡すことも可能）
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG / INFO / ...（デフォルト: INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）デフォルト: data/monitoring.db
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知が必要な場合に設定

例の .env（最小）
- JQUANTS_REFRESH_TOKEN=xxxxxxxx
- OPENAI_API_KEY=sk-xxxxxxxx
- KABU_API_PASSWORD=your_kabu_password

---

## 使い方（代表的な例）

以下は Python スクリプト内または REPL での利用例です。

1) DuckDB 接続を作って日次 ETL を実行する
- ETL は DuckDB 接続を受け取ります。settings の duckdb_path を使う例:

```python
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースセンチメントのスコア付与（score_news）
- OpenAI API キーは引数で渡すか環境変数 OPENAI_API_KEY を設定します。

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数を使う
print(f"書き込み銘柄数: {written}")
```

3) 市場レジーム判定（score_regime）
- ETF 1321 の MA200 とマクロ記事 LLM を組み合わせます。OpenAI API キーが必要です。

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

4) 監査ログ DB 初期化
- 監査用に別 DB を用意してスキーマを初期化するユーティリティがあります。

```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# 以後 conn を通じて signal_events / order_requests / executions にアクセス可能
```

5) ファクター計算（研究用）
- calc_momentum / calc_volatility / calc_value 等を使ってモデルに渡す特徴量を取得できます。

```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect(str(settings.duckdb_path))
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は [{ "date": ..., "code": "...", "mom_1m": ..., ... }, ...]
```

注意点:
- OpenAI 呼び出しはネットワークと課金が発生します。テストでは各モジュールの _call_openai_api をモックできます（ソース内コメント参照）。
- J-Quants API 呼び出しは rate limit を考慮していますが、ID トークン（JQUANTS_REFRESH_TOKEN）は必須です。

---

## 環境変数 / 設定項目（主なもの）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- OPENAI_API_KEY (score_news / score_regime 用)
- KABUSYS_ENV (development / paper_trading / live) — デフォルト: development
- LOG_LEVEL — デフォルト: INFO
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT — 監視に関連する設定

詳細は kabusys.config.Settings のプロパティ定義を参照してください。

---

## ディレクトリ構成

主要なファイル／モジュール構成（src/kabusys 以下の抜粋）:

- kabusys/
  - __init__.py
  - config.py               # 環境変数管理（.env 自動読み込み、Settings）
  - ai/
    - __init__.py
    - news_nlp.py           # 銘柄別ニュースセンチメント（score_news）
    - regime_detector.py    # 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py     # J-Quants API クライアント + DuckDB 保存関数
    - pipeline.py          # ETL パイプライン（run_daily_etl 等）
    - calendar_management.py
    - news_collector.py     # RSS 収集（SSRF 対策・正規化・保存）
    - quality.py            # データ品質チェック
    - stats.py              # 汎用統計ユーティリティ（zscore_normalize）
    - audit.py              # 監査ログスキーマ初期化 / init_audit_db
    - etl.py                # ETLResult 再エクスポート
  - research/
    - __init__.py
    - factor_research.py    # calc_momentum / calc_value / calc_volatility
    - feature_exploration.py# calc_forward_returns / calc_ic / factor_summary / rank
  - ai/ (上記)
  - research/ (上記)
  - その他（strategy, execution, monitoring 等の名前空間が用意される想定）

この README では主要モジュールを抜粋しています。詳細はソースコード内の docstring を参照してください（各関数に利用上の注意・設計方針が記載されています）。

---

## 開発上の注意（要点）

- 日付の扱い: バックテストや学習でのルックアヘッドバイアスを防ぐため、各モジュールは内部で現在時刻を直接参照しない設計を意識しています（関数呼び出し側で target_date を渡す）。
- API キー管理: OpenAI/J-Quants のトークンは環境変数か関数引数で渡してください。J-Quants の ID トークンはモジュール内でキャッシュ・自動リフレッシュされます。
- レート制限・リトライ: J-Quants は固定間隔スロットリング、OpenAI 呼び出しはリトライとバックオフ処理が組まれていますが、実行環境の制約に応じて追加の制御が必要な場合があります。
- DB 書き込みの冪等性: save_* 関数は ON CONFLICT による上書きを行い、部分失敗時のデータ保護を意識した実装になっています。

---

## さらに詳しく / 貢献

- ソース内 docstring に設計方針や使用上の注意が多く記載されています。API の利用方法は関数の docstring を参照してください。
- バグ報告や改善提案は Issue / PR で歓迎します。テストや CI の整備、型注釈の充実、ドキュメントの追加を歓迎します。

---

以上。必要であれば各機能（ETL の実行例、news_collector の実行 CLI、監視プロセスの起動方法など）について、より具体的なサンプルや運用手順を追記します。どの部分の詳細が必要か教えてください。