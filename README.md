# KabuSys

日本株向けの自動売買・データ基盤ライブラリです。  
データ ETL、ニュース NLP、ファクター計算、監査ログ、JPX カレンダー管理、J-Quants / kabu ステーション クライアントなどを備え、バックテストや運用バッチに利用できるモジュール群を提供します。

---

## 主な特徴

- データ取得・ETL
  - J-Quants API から株価（OHLCV）、財務データ、上場情報、マーケットカレンダーを差分取得・保存（ページネーション対応・再取得（backfill）対応）
  - DuckDB に対する冪等保存（ON CONFLICT DO UPDATE）
  - API レート制御・リトライ・トークン自動リフレッシュ対応

- データ品質管理
  - 欠損・重複・スパイク・日付不整合などの品質チェックを実行可能（quality モジュール）

- ニュース収集と NLP（OpenAI）
  - RSS 取得（SSRF 対策、トラッキング除去）
  - gpt-4o-mini を用いたニュースセンチメント（銘柄別 ai_score）解析（バッチ・チャンク処理・JSON Mode）
  - マクロニュースを使った市場レジーム判定（ETF 1321 の 200日 MA と LLM スコアの合成）

- リサーチ支援
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB + SQL）
  - 将来リターン、IC（Information Coefficient）、統計サマリー、Zスコア正規化など

- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions 等の監査テーブル定義と初期化ユーティリティ
  - order_request_id による冪等性、UTC タイムスタンプ保存

- 設計上の注力点
  - Look-ahead bias 回避（内部で date.today()/datetime.today() を直接参照しない設計）
  - フェイルセーフ（API失敗時は処理継続、部分書き込み保護）
  - 冪等性・トランザクション制御・指数バックオフ等の堅牢性

---

## セットアップ

前提: Python 3.10+（型アノテーションで | 型を使用しているため）を推奨します。

1. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージのインストール
   - requirements.txt がある場合:
     - pip install -r requirements.txt
   - ない場合は最低限以下をインストールしてください:
     - pip install duckdb openai defusedxml

   （プロジェクトのパッケージ化がある場合は `pip install -e .` を使用してください）

3. 環境変数設定
   - プロジェクトルートに `.env` / `.env.local` を置くと、自動で読み込まれます（優先順位: OS 環境変数 > .env.local > .env）。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須の環境変数（代表）
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン
- KABU_API_PASSWORD: kabu ステーション API パスワード
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack チャンネル ID
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime を API キー引数で渡すことも可）
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）

データベースパス（オプション）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite / DuckDB など（デフォルト: data/monitoring.db）

例 (.env)
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
```

---

## 使い方（代表的な例）

以下は Python スクリプト / REPL から呼び出す例です。DuckDB 接続に対して直接関数を呼び出します。

- 日次 ETL 実行（株価・財務・カレンダー取得 + 品質チェック）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントを生成（前日15:00〜当日08:30 JST ウィンドウ）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # OPENAI_API_KEY を環境変数で設定しているなら None
print(f"scored {count} codes")
```

- 市場レジーム判定（ETF 1321 の MA とマクロニュースを合成）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)  # OPENAI_API_KEY を使用
```

- 監査ログ DB 初期化
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/monitoring.db")
# これで signal_events / order_requests / executions 等のテーブルが作成されます
```

- ファクター計算（例: モメンタム）
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, date(2026, 3, 20))
print(len(records), records[:3])
```

注意:
- OpenAI 呼び出しは gpt-4o-mini（JSON Mode）を使用します。API キーは引数で渡すか環境変数 OPENAI_API_KEY を設定してください。
- LLM 呼び出しはリトライとフェイルセーフを備えています。API 失敗時は 0.0 を用いるなどのフォールバックが組み込まれています。

---

## ディレクトリ構成（主要ファイル）

（ソースは src/kabusys 以下に配置されています）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数・自動 .env ロード
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュース NLP（銘柄別 ai_score）
    - regime_detector.py           — 市場レジーム判定（ma200 + マクロセンチメント）
  - data/
    - __init__.py
    - calendar_management.py       — 市場カレンダー管理・営業日判定
    - etl.py / pipeline.py         — ETL パイプライン／ジョブ
    - jquants_client.py            — J-Quants API クライアント（取得・保存）
    - news_collector.py            — RSS ニュース収集（SSRF 対策 等）
    - quality.py                   — データ品質チェック
    - stats.py                     — 共通統計ユーティリティ（zscore_normalize 等）
    - audit.py                     — 監査ログ（テーブル定義・初期化）
    - etl.py (再エクスポート)      — ETLResult のエクスポート
  - research/
    - __init__.py
    - factor_research.py           — ファクター計算（momentum/value/volatility）
    - feature_exploration.py       — 将来リターン、IC、統計サマリー等

---

## 設計上の重要なポイント・運用上の注意

- Look-ahead bias に配慮
  - 多くの関数（news_nlp, regime_detector, pipeline 等）は内部で date.today() を直接参照せず、明示的な target_date 引数に基づいて処理します。バックテスト等で必ず適切な target_date を渡してください。

- 冪等性
  - J-Quants → DuckDB の保存は ON CONFLICT による更新を行い、再実行しても安全な設計です（ただし一部の操作はトランザクションに依存します）。

- API レート制御 / リトライ
  - J-Quants クライアントは固定間隔スロットリングと指数バックオフ・401 リフレッシュを実装しています。OpenAI 呼び出しもリトライ・バックオフロジックを含みます。

- セキュリティ
  - news_collector は SSRF 対策（リダイレクト検査、プライベート IP 拒否）や XML パースの安全ライブラリ（defusedxml）を利用しています。
  - .env 読み込みはプロジェクトルート（.git または pyproject.toml を探索）基準で行われます。自動ロードを無効にするフラグがあります。

- データベース
  - DuckDB を主要な作業 DB として想定しています。監査ログは別 DB（init_audit_db で初期化）に切り分け可能です。

---

## 開発・テストのヒント

- テスト時は env の自動ロードを無効化:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
- OpenAI 呼び出しや外部 API 呼び出しはモック可能に実装されています（モジュール内の _call_openai_api などを patch）。
- DuckDB をインメモリ ":memory:" で使えば一時的な単体テストが容易です。

---

本 README はコードベースの主要な利用方法と設計思想をまとめた簡易版です。詳細な API パラメータやスキーマ、運用手順は各モジュールの docstring を参照してください。質問や追加のドキュメント化が必要であれば教えてください。