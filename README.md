# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリです。  
データ収集（J-Quants）、ETL、データ品質チェック、ニュースNLP（OpenAI を使ったセンチメント）、市場レジーム判定、監査ログ（トレーサビリティ）、研究用ファクター計算などを含みます。

目的
- データ基盤（価格・財務・カレンダー・ニュース）を DuckDB に蓄積する ETL パイプライン
- ニュースを元に銘柄単位の AI スコアを生成するモジュール（OpenAI）
- ETF とマクロニュースを合成した市場レジーム判定
- 研究用途のファクター計算・統計ユーティリティ
- 発注・約定を追跡するための監査ログテーブル初期化ユーティリティ

バージョン: 0.1.0

---

## 主な機能一覧

- data
  - J-Quants API クライアント（fetch / save 関数）
  - ETL パイプライン（run_daily_etl、個別 ETL ジョブ）
  - カレンダー管理（営業日判定・カレンダーバッチ更新）
  - ニュース収集（RSS → raw_news、SSRF/トラッキング対策）
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize 等）
- ai
  - ニュース NLP スコアリング（score_news: 銘柄別 ai_scores 書き込み）
  - 市場レジーム判定（score_regime: market_regime テーブルへ書き込み）
- research
  - ファクター計算（モメンタム / バリュー / ボラティリティ）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- 設定管理
  - .env / .env.local / 環境変数読み込み（自動ロード、無効化可能）
  - settings オブジェクト経由でアクセス

設計上の特徴
- ルックアヘッドバイアス対策（内部で現在時刻を勝手に参照しない設計）
- DuckDB を核にしたローカル DB 保持・冪等保存（ON CONFLICT）
- OpenAI 呼び出しはリトライ / JSON Mode を使用し堅牢化
- ニュース収集で SSRF・XML インジェクション対策

---

## セットアップ手順

前提
- Python 3.9 以上（型ヒントで | 型等を使用しているため最新の安定版推奨）
- duckdb, openai, defusedxml 等の依存ライブラリ

1. リポジトリをクローン / コピー
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境の作成（任意）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 必要パッケージをインストール
   - requirements.txt があれば `pip install -r requirements.txt` を推奨。
   - 主要パッケージ（例）:
     ```bash
     pip install duckdb openai defusedxml
     ```
   - 開発時に editable install:
     ```bash
     pip install -e .
     ```

4. 環境変数（.env）を用意
   - プロジェクトルートに `.env` または `.env.local` を作成すると自動でロードされます（自動ロード無効化は後述）。
   - 主要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
     - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で使用）
     - KABU_API_PASSWORD: kabu ステーション API パスワード（必要なら）
     - KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
     - KABUSYS_ENV: 環境 (development | paper_trading | live)
     - LOG_LEVEL: ログレベル（DEBUG/INFO/...）
   - 例 `.env`:
     ```
     JQUANTS_REFRESH_TOKEN=your_refresh_token_here
     OPENAI_API_KEY=sk-...
     KABU_API_PASSWORD=...
     DUCKDB_PATH=data/kabusys.duckdb
     ```

5. 自動 .env ロードの制御
   - パッケージ初期化時にプロジェクトルート（.git または pyproject.toml）を探索して `.env` を自動読み込みします。
   - 無効化する場合:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

---

## 使い方（主要な例）

準備: DuckDB 接続と settings を使う例

```python
import duckdb
from kabusys.config import settings

# DuckDB 接続
conn = duckdb.connect(str(settings.duckdb_path))

# 日次 ETL（今日を対象）を実行
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

ニューススコア（OpenAI を使う）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news
import duckdb

conn = duckdb.connect(str(settings.duckdb_path))
# OpenAI API キーは環境変数 OPENAI_API_KEY を参照するか、api_key 引数で渡す
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書込銘柄数:", n_written)
```

市場レジーム判定
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime
conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

監査ログ DB の初期化（監査専用 DB を作成する）
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# conn_audit に対して監査テーブルが作成される
```

J-Quants の id_token を取得（内部で settings.jquants_refresh_token を使う）
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()
```

注意点:
- score_news / score_regime は OpenAI API を呼ぶため課金・レート制限に注意してください。
- テスト時は各モジュール内の `_call_openai_api` や HTTP/ネットワーク呼び出しをモックすると良いです（コード内に patch しやすい設計あり）。

---

## 設定管理の詳細

- settings オブジェクト: `from kabusys.config import settings`
  - settings.jquants_refresh_token
  - settings.duckdb_path, settings.sqlite_path
  - settings.env, settings.is_live / is_paper / is_dev
  - CPU/MEM/ディスク閾値、pid ファイルパス等

- .env 読み込み優先順位:
  1. OS 環境変数（既存の環境）
  2. .env.local（override=True）
  3. .env（override=False）
- 自動ロードを無効化: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py          — ニュース NLP スコアリング（score_news）
  - regime_detector.py   — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py    — J-Quants API クライアント（fetch/save）
  - pipeline.py          — ETL パイプライン（run_daily_etl 等）
  - etl.py               — ETL インターフェース（ETLResult export）
  - calendar_management.py — マーケットカレンダー管理
  - news_collector.py    — RSS ニュース収集（SSRF / XML 安全対策）
  - quality.py           — データ品質チェック（QualityIssue 等）
  - stats.py             — 汎用統計ユーティリティ（zscore_normalize）
  - audit.py             — 監査ログテーブル作成 / init_audit_db
- research/
  - __init__.py
  - factor_research.py   — モメンタム / バリュー / ボラティリティ計算
  - feature_exploration.py — 将来リターン / IC / 統計サマリー
- ai, research, data 以下に設計文書的なコメントが豊富に含まれています。

---

## 開発 / テストのヒント

- ネットワーク呼び出し（OpenAI / J-Quants / RSS）はテストでモックすることを推奨します。モジュール内で小さな呼び出し関数（例: _call_openai_api、_urlopen）が分離されているため差し替えが容易です。
- DuckDB を用いたロジックはインメモリ DB（":memory:"）でテスト可能です。
- settings 自動ロードを無効化して、テスト用に環境変数を制御すると再現性が上がります。

---

## ライセンス / 貢献

このリポジトリにライセンス情報が含まれていない場合は、プロジェクトに適したライセンス（例: MIT）を追加してください。  
バグ報告・機能追加は Issue を立てるか Pull Request を送ってください。

---

README はこのコードベースの主要点をまとめた簡易ドキュメントです。実運用にあたっては以下を推奨します:
- 運用手順書（ETL スケジューリング、監視、ロギング、バックアップ）
- セキュリティ手順（API キーの保管・ローテーション、アクセス制御）
- テストケースと CI（ネットワーク呼び出しはモック化）