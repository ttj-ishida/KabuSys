# KabuSys

日本株向け自動売買 / データプラットフォーム用ライブラリ。  
ETL、ニュース収集・NLP、ファクター研究、監査ログ、J-Quants / kabu ステーション連携などの機能を提供します。

バージョン: 0.1.0

---

## 主な特徴

- データ取得（J-Quants API）/ ETL パイプライン（差分取得・バックフィル・品質チェック）
- ニュース収集（RSS）と前処理、銘柄紐付け
- ニュースを OpenAI（gpt-4o-mini）でスコアリングして ai_scores に保存
- 市場レジーム判定（ETF 1321 の MA + マクロニュースのセンチメント合成）
- ファクター計算（モメンタム、バリュー、ボラティリティ等）と探索ツール（IC、フォワードリターン等）
- マーケットカレンダー管理（JPX）と営業日ユーティリティ
- 監査ログスキーマ（信号→発注→約定のトレーサビリティ）と初期化ユーティリティ
- DuckDB をデータ格納の主要 DB として利用
- 自動的な .env ロード（プロジェクトルートの .env / .env.local）と Settings ラッパー

---

## 必要条件 / 推奨環境

- Python 3.10+
- 必要パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants / OpenAI / RSS ソース 等）

インストール例（仮想環境推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# パッケージを編集インストールする場合:
# pip install -e .
```

---

## 環境変数 / 設定

設定は環境変数またはプロジェクトルートの `.env` / `.env.local` から自動ロードされます（自動ロード無効化: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`）。

主な環境変数（必須は明記）:
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu API 用パスワード
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- OPENAI_API_KEY — OpenAI API キー（AI スコアリングに必要）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: `data/kabusys.duckdb`）
- SQLITE_PATH — 監視 DB パス（デフォルト: `data/monitoring.db`）
- KABUSYS_ENV — `development` / `paper_trading` / `live`（デフォルト: `development`）
- LOG_LEVEL — `DEBUG`/`INFO`/...（デフォルト: `INFO`）

アプリ内での参照は `from kabusys.config import settings` を使います（プロパティとして取得可能）。

---

## セットアップ手順（開発用の簡易手順）

1. リポジトリをクローン
2. 仮想環境作成・有効化
3. 依存パッケージをインストール（上記参照）
4. プロジェクトルートに `.env` を作成して必要な環境変数を設定
   - `.env.example` を参考にしてください（リポジトリに例ファイルがある想定）
5. DuckDB ファイルの親ディレクトリを作成（もし自動で作られない場合）
   ```bash
   mkdir -p data
   ```

---

## 使い方（代表的な例）

※ すべての操作は Python スクリプト / REPL から行えます。関数は DuckDB 接続（duckdb.connect(...) の返り値）を受け取ります。

- Settings の利用:
```python
from kabusys.config import settings
print(settings.duckdb_path, settings.is_live)
```

- DuckDB 接続作成:
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL 実行:
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

res = run_daily_etl(conn, target_date=date(2026,3,20))
print(res.to_dict())
```

- ニューススコアリング（OpenAI 必須）:
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

count = score_news(conn, target_date=date(2026,3,20))  # OpenAI API キーは環境変数 OPENAI_API_KEY で
print(f"scored {count} codes")
```

- 市場レジーム判定:
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026,3,20))  # OpenAI API キー必要
```

- 監査 DB 初期化（監査ログ専用 DB を作成して接続を得る）:
```python
from kabusys.data.audit import init_audit_db
from pathlib import Path

audit_conn = init_audit_db(Path("data/audit.duckdb"))
# これで signal_events / order_requests / executions テーブルが作成されます
```

- マーケットカレンダー関連ユーティリティ:
```python
from datetime import date
from kabusys.data.calendar_management import is_trading_day, next_trading_day

d = date(2026,3,20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

- RSS フィード取得（ニュース収集の低レベル関数）:
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
for a in articles[:5]:
    print(a["id"], a["title"], a["datetime"])
```

---

## よくある操作 / 注意点

- API キー・機密値は `.env` に保存して管理してください。`.env.local` は `.env` の上書きに使えます。
- 自動 .env ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト等で有用）。
- OpenAI 呼び出しは外部サービスに依存するため、API エラー時は多くの処理がフェイルセーフで継続する実装になっています（ログ記録・0.0フォールバック等）。
- DuckDB の executemany にはバージョン依存の制約があるため、モジュール側で空リストを渡さない等の注意実装がされています。
- network / RSS 関連では SSRF 対策（ホストのプライベート IP チェック）や受信サイズ上限が導入されています。

---

## ディレクトリ構成（主要ファイルと役割）

- src/kabusys/
  - __init__.py — パッケージ定義
  - config.py — 環境変数 / 設定管理（Settings）
  - ai/
    - __init__.py
    - news_nlp.py — ニュースセンチメントの LLM スコアリング（ai_scores 書き込み）
    - regime_detector.py — 市場レジーム判定（MA + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得 + DuckDB 保存）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - etl.py — ETL の公開インターフェース（ETLResult 再エクスポート）
    - news_collector.py — RSS 収集・前処理
    - calendar_management.py — マーケットカレンダー / 営業日ユーティリティ
    - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py — 共通統計ユーティリティ（zscore 等）
    - audit.py — 監査ログ（signal / order_request / executions の DDL・初期化）
  - research/
    - __init__.py
    - factor_research.py — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py — 将来リターン計算、IC、統計サマリー等

---

## 開発・テストに関するメモ

- テスト時は環境依存を避けるため `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して下さい。
- OpenAI / J-Quants クライアント呼び出しはモックしやすいように設計されています（内部呼び出しを差し替え可能）。
- DuckDB を使えばインメモリ（":memory:"）でテスト可能です（audit.init_audit_db 等は ":memory:" を受け取ります）。

---

## 連絡 / 貢献

バグ報告や機能追加の要望は issue を作成してください。プルリク歓迎です。設計思想（Look-ahead バイアス回避、冪等性、フェイルセーフ等）を尊重した実装をお願いします。

--- 

README はこのコードベースの主要機能と使い方のサマリです。詳細は各モジュールの docstring を参照してください。