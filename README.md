# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ群です。  
ETL（J-Quants → DuckDB）、ニュース収集・NLP（OpenAI）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログなど、取引アルゴリズム開発と運用に必要な基盤処理を提供します。

---

## 主要機能

- データ取得・ETL（J-Quants API）
  - 株価日足（OHLCV）、財務諸表、JPXマーケットカレンダーの差分取得／冪等保存
  - レートリミット遵守・リトライ・トークン自動リフレッシュ対応
- ニュース収集（RSS）と前処理（SSRF対策、トラッキングパラメータ除去、gzip対応）
- ニュースNLP（OpenAI）
  - 銘柄ごとのニュース統合センチメント評価（gpt-4o-mini, JSON mode）
  - マクロニュースを用いた市場レジーム判定（ETF 1321 の MA + マクロセンチメントの合成）
- 監査ログ（オーディット）
  - シグナル → 発注 → 約定の完全トレーサビリティ（冪等キー・UTCタイムスタンプ）
  - DuckDB に監査テーブルを冪等で初期化するユーティリティ
- 研究用ユーティリティ
  - モメンタム / バリュー / ボラティリティ系ファクター計算
  - 将来リターン計算、IC（Spearman）計算、ファクター統計要約
- データ品質チェック（欠損・重複・スパイク・日付不整合検出）
- 環境変数/設定管理（自動 .env ロード、保護された上書きロジック）

---

## 必要条件

- Python 3.10+
- 主要外部ライブラリ（実行に必要）:
  - duckdb
  - openai
  - defusedxml
- ネットワーク接続（J-Quants API / OpenAI / RSSソース 等）

（パッケージはプロジェクトのセットアップ方法に従ってインストールしてください。以下のセットアップ例を参照）

---

## セットアップ手順（例）

1. リポジトリを取得
   - git clone ... またはソースを入手

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存ライブラリをインストール（最小）
   - pip install duckdb openai defusedxml

   ※ 実運用では requirements.txt / pyproject.toml を用意して管理してください。

4. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を置くと自動読み込みされます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

   重要な環境変数（例）
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD     : kabuステーション API のパスワード（必須）
   - SLACK_BOT_TOKEN       : Slack Bot トークン（必須）
   - SLACK_CHANNEL_ID      : Slack チャンネル ID（必須）
   - OPENAI_API_KEY        : OpenAI API キー（score_news / score_regime 実行時に使用）
   - KABUSYS_ENV           : 実行環境 ["development" | "paper_trading" | "live"]（デフォルト: development）
   - LOG_LEVEL             : ログレベル ["DEBUG","INFO","WARNING","ERROR","CRITICAL"]（デフォルト: INFO）
   - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH           : 監視用 SQLite パス（デフォルト: data/monitoring.db）

   簡易 `.env` 例:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-xxxx
   SLACK_BOT_TOKEN=xoxb-xxxx
   SLACK_CHANNEL_ID=C01234567
   KABU_API_PASSWORD=your_kabu_password
   ```

---

## 使い方（主要API / コマンド例）

以下はライブラリをインポートして使う簡単な例です。関数は DuckDB 接続（duckdb.connect(...) で得られる接続オブジェクト）を受け取り、結果を返します。

- ETL（日次パイプライン）を実行する
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコア（OpenAI を用いた銘柄別センチメント）を実行
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print("scored:", n_written)
```

- 市場レジーム判定（MA200 とマクロセンチメントの合成）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- 監査ログ用 DB 初期化
```python
from pathlib import Path
from kabusys.data.audit import init_audit_db

conn = init_audit_db(Path("data/audit.duckdb"))
# これで audit 用テーブルが作成されます
```

- 研究系関数の例（モメンタム、ボラティリティ、バリュー）
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026, 3, 20)
mom = calc_momentum(conn, d)
vol = calc_volatility(conn, d)
val = calc_value(conn, d)
```

- 設定取得（環境変数ラッパー）
```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.is_live)
```

注意点:
- AI 系処理（score_news / score_regime）は OPENAI_API_KEY が必要です（引数で明示的に渡すことも可能）。
- データベースのテーブルスキーマは本 README に含まれていません。実行前にスキーマ初期化を行ってください（ETL 用スキーマ初期化ユーティリティをプロジェクトに用意している前提です）。
- DuckDB の executemany は空リストを受け付けないバージョンがあるため、関数内でチェック済みです。

---

## 自動 .env ロードの仕様

- プロジェクトルート（.git または pyproject.toml が見つかる親ディレクトリ）を起点に `.env` と `.env.local` を自動読み込みします。
- 読み込み優先度: OS 環境変数 > .env.local > .env
- テストなどで自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- `.env` のパースはシェル風の `KEY=val`、クォートやエスケープ、`export KEY=...` に対応しています。

---

## ディレクトリ構成

（src/kabusys をルートとした主要ファイル群）

- kabusys/
  - __init__.py
  - config.py  — 環境変数 / 設定管理（.env 自動ロード、settings オブジェクト）
  - ai/
    - __init__.py
    - news_nlp.py         — ニュースセンチメント（OpenAI 呼び出し、チャンク処理、バリデーション）
    - regime_detector.py  — 市場レジーム判定（ETF 1321 の MA + マクロセンチメント合成）
  - data/
    - __init__.py
    - jquants_client.py   — J-Quants API クライアント（取得・保存ロジック、レート制御）
    - pipeline.py         — ETL パイプライン（run_daily_etl など）
    - etl.py              — ETL の公開ラッパー（ETLResult 再エクスポート）
    - news_collector.py   — RSS ニュース収集（SSRF対策・XML防御）
    - quality.py          — データ品質チェック（欠損・スパイク・重複・日付）
    - calendar_management.py — 市場カレンダー管理（営業日判定、更新ジョブ）
    - stats.py            — 汎用統計ユーティリティ（z-score 正規化）
    - audit.py            — 監査ログスキーマ初期化 / audit DB ユーティリティ
  - research/
    - __init__.py
    - factor_research.py  — モメンタム/ボラティリティ/バリュー計算
    - feature_exploration.py — 将来リターン、IC、統計サマリー、ランキングユーティリティ

---

## 実運用上の注意 / ベストプラクティス

- OpenAI API 呼び出しはコストが発生します。テスト時はモック（unittest.mock.patch）で `_call_openai_api` を差し替えてください。
- Look-ahead bias（将来データ参照）を避けるため、多くの関数は `target_date` を明示的に受け取り、date.today() を直接参照しない設計です。バックテスト・研究時もこの方針に従ってください。
- J-Quants API のレート制限（120 req/min）を考慮した実装になっていますが、運用時にはスロットリング状況を監視してください。
- 監査ログ（audit）は削除しない前提です。運用設計に合わせて保管・バックアップ方針を定めてください。
- DuckDB のバージョン差異により executemany や型バインドに差が出る可能性があります。CI で利用する DuckDB バージョンを固定することを推奨します。

---

## 追加情報 / 貢献

- バグ報告、機能リクエスト、PRはリポジトリの issue / PR で受け付けてください。
- テストは AI 呼び出しやネットワーク I/O をモックして実装することを推奨します（_call_openai_api / _urlopen / jquants_client._request などを差し替えられる設計です）。

---

この README はコードベースの主要機能と使い方の要約です。詳細は各モジュールの docstring（関数・クラスのコメント）を参照してください。必要であれば、具体的なセットアップスクリプトや docker-compose、CI ワークフローの例も作成できます。必要な場合は教えてください。