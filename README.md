# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。ETL、データ品質チェック、ニュースセンチメント評価（OpenAI）、市場レジーム判定、ファクター計算、監査ログ等の機能をモジュール化して提供します。

- パッケージ名: kabusys
- バージョン: 0.1.0 (src/kabusys/__init__.py)

---

## プロジェクト概要

KabuSys は日本株のデータ取得から品質チェック、ニュースベースのセンチメント評価、リサーチ（ファクター算出）、
及び自動売買に必要な監査ログ（トレーサビリティ）を支援する Python モジュール群です。

主な設計方針:
- DuckDB を中心としたローカル DB でデータ管理
- J-Quants API を利用した差分 ETL（レートリミット遵守・リトライ付き）
- OpenAI（gpt-4o-mini 等）を用いたニュース NLP（JSON Mode）＋市場レジーム判定
- ルックアヘッドバイアス回避（内部で date.today() を直接使わない設計）
- 冪等性（DB 保存は ON CONFLICT / idempotent）とフェイルセーフ設計

---

## 機能一覧（主要モジュール）

- kabusys.config
  - .env / 環境変数の読み込み（プロジェクトルート自動検出）
  - settings オブジェクト経由で設定値を取得

- kabusys.data
  - jquants_client: J-Quants API クライアント（認証・ページネーション・保存関数）
  - pipeline: ETL 実行（run_daily_etl, run_prices_etl など）と ETLResult
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - news_collector: RSS 取得・前処理（SSRF 対策・URL 正規化・記事ID生成）
  - calendar_management: JPX カレンダー管理・営業日判定
  - audit: 監査ログテーブルの初期化（signal_events / order_requests / executions）
  - stats: 汎用統計ユーティリティ（Zスコア正規化 等）

- kabusys.ai
  - news_nlp.score_news: ニュースを LLM で評価し ai_scores に保存
  - regime_detector.score_regime: ETF (1321) の MA とマクロニュースを合成して市場レジームを判定

- kabusys.research
  - factor_research: モメンタム／ボラティリティ／バリューなどのファクター計算
  - feature_exploration: 将来リターン計算、IC, 統計サマリー 等

---

## 必要環境 / 依存関係

- Python 3.10 以上（PEP 604 型注釈の使用や最新ライブラリ互換のため推奨）
- 主な Python パッケージ:
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリで多くを実装していますが、上記は必須）

インストール例（仮想環境推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb openai defusedxml
# 開発モードでパッケージをインストールする場合
# pip install -e .
```

（プロジェクトに requirements.txt があればそちらを利用してください）

---

## 環境変数 / .env

kabusys はプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索し、`.env` と `.env.local` を自動で読み込みます（環境変数が優先されます）。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な環境変数:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須、jquants_client.get_id_token 等で使用）
- OPENAI_API_KEY        : OpenAI API キー（ai.news_nlp / regime_detector で使用）
- KABU_API_PASSWORD     : kabuステーション API パスワード（注文発注系で使用）
- KABU_API_BASE_URL     : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH           : 監視用 sqlite パス（デフォルト: data/monitoring.db）
- その他監視閾値やログ設定（config.Settings 参照）

例（.env.example）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
```

注意: Settings クラスのプロパティは、未設定時に ValueError を投げるものがあります（必須設定を明示）。

---

## セットアップ手順

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成と依存インストール
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install duckdb openai defusedxml
   # または: pip install -r requirements.txt
   ```

3. 環境変数を設定
   - プロジェクトルートに `.env`（または `.env.local`）を作成するか、環境変数をエクスポートします。
   - 必須: JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY（score_news/score_regime を使う場合）

4. DuckDB データベース初期化（必要に応じてスキーマを作成するスクリプト等を作成して下さい）
   - 監査ログ専用 DB を作る場合:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```
   - ETL 用の DuckDB 接続:
     ```python
     import duckdb
     from kabusys.config import settings
     conn = duckdb.connect(str(settings.duckdb_path))
     ```

---

## 基本的な使い方（コード例）

- 日次 ETL を実行する（市場カレンダー取得 → 株価 → 財務 → 品質チェック）:
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントを評価して ai_scores に保存する:
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY は環境変数に設定しておくか、api_key 引数で指定
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print("written:", n_written)
```

- 市場レジームを判定して market_regime テーブルに書き込む:
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ DB を初期化する:
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn をアプリ側で保持・利用
```

- ファクター計算（研究用途）:
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
moms = calc_momentum(conn, target_date=date(2026, 3, 20))
vals = calc_value(conn, target_date=date(2026, 3, 20))
vols = calc_volatility(conn, target_date=date(2026, 3, 20))
```

- RSS を取得して raw_news に保存（news_collector を組み合わせて利用）
  - news_collector.fetch_rss で記事を取得 → jquants_client に似た保存関数を自前で実装して raw_news に挿入します（リポジトリ内に raw_news 保存ロジックがある想定）。

---

## 注意事項 / 運用メモ

- OpenAI を使う機能（news_nlp, regime_detector）は API キーが必須です。API の失敗時には内部でフェイルセーフ（スコア 0.0 等）を取る実装になっていますが、コストやレート制限に注意してください。
- J-Quants API はレート制限（120 req/min）を守るためモジュール側でスロットリングとリトライを実装しています。ID トークンの自動リフレッシュもサポートされます。
- DuckDB の executemany に空リストを渡せないバージョン等、実行環境による差異に注意してください（pipeline モジュール内で対策済み）。
- データ品質チェックは ETL 後に run_all_checks で実行できます。重大な品質問題が検出された場合は運用側でアラート・対応を行ってください。
- news_collector では SSRF 対策、受信サイズ制限、XML 安全パーサ（defusedxml）を用いています。RSS の保存処理では必ずトランザクションでまとめるなど、冪等性を保ってください。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要構成（抜粋）です:

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - jquants_client.py
    - pipeline.py
    - etl.py
    - news_collector.py
    - calendar_management.py
    - quality.py
    - stats.py
    - audit.py
    - pipeline.py
    - etl.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/
    - __init__.py

（実際のリポジトリには上記以外にもモジュールやユーティリティが含まれる可能性があります）

---

## 開発・貢献

- コードはユニットテストやモックを想定した設計（外部 API 呼び出しを差し替え可能）になっています。テストを書いて PR を送ってください。
- 設計思想や API の安定化は README 上のセクションを拡張して記載していく予定です。

---

## 参考

- 各モジュール内の docstring に詳細な設計方針・注意点・戻り値仕様が記載されています。実装の利用前に該当モジュールの docstring を参照してください。
- 環境変数や .env の取り扱いは kabusys.config.Settings を確認してください（自動ロードの挙動や必須変数の検証を行っています）。

---

この README はリポジトリ内の現行ソースコードから作成しています。追加の実行スクリプト、CI 設定、または運用手順があれば合わせて追記してください。