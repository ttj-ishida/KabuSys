# KabuSys

日本株向けのデータプラットフォーム & 自動売買支援ライブラリです。  
J-Quants / kabu ステーション / OpenAI（LLM）等を連携して、データのETL、ニュースNLP、マーケットレジーム判定、ファクター計算、監査ログ管理などを提供します。

主な設計方針：
- ルックアヘッドバイアスを避ける（内部処理で `date.today()` を不用意に参照しない）
- DuckDB を中心としたローカルDBでの冪等保存（ON CONFLICT / DELETE→INSERT 等）
- 外部API呼び出しはリトライ・バックオフ・フェイルセーフを備える
- テストしやすい設計：API呼び出しポイントは差し替え可能

---

## 機能一覧

- data
  - ETLパイプライン（J-Quants から株価・財務・カレンダーを差分取得）
  - J-Quants API クライアント（トークン管理・ページネーション・レート制御・保存）
  - 市場カレンダー管理（営業日判定、next/prev trading day）
  - ニュース収集（RSS → raw_news、SSRF対策・サイズ制限・トラッキング除去）
  - データ品質チェック（欠損・重複・スパイク・日付不整合）
  - 監査ログスキーマ（signal / order_request / execution のDDL・初期化）
  - 統計ユーティリティ（Zスコア正規化 等）
- ai
  - ニュースNLP（ニュースをまとめて LLM に投げ、銘柄ごとの sentiment / ai_score を ai_scores に書き込む）
  - 市場レジーム判定（ETF 1321 の MA とマクロニュースの LLM スコアを合成して market_regime に書き込む）
- research
  - ファクター計算（モメンタム / ボラティリティ / バリュー 等）
  - 特徴量探索（将来リターン計算、IC、統計サマリー 等）
- config
  - .env / 環境変数の自動ロード・設定管理（必要な環境変数の取得ユーティリティ）

主な特徴：
- 冪等保存（DuckDB 側での UPDATE/ON CONFLICT 対応）
- LLM 呼び出しは JSON モードや厳密な検証で安全性を担保
- ネットワークエラー・レート制限は指数バックオフで再試行
- 各種処理はフェイルセーフ（API失敗時に例外を投げず代替値で継続する箇所が多い）

---

## セットアップ手順

必要環境
- Python 3.10 以上（typing の `X | None` 等を使用しているため）
- 推奨パッケージ（最低限）:
  - duckdb
  - openai
  - defusedxml

例（venv を使ったセットアップ）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb openai defusedxml
# 開発中ならリポジトリルートで:
pip install -e .
```

環境変数（最低限必要なもの）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（ETL 用）
- KABU_API_PASSWORD: kabuステーション API パスワード（実運用時）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（monitoring / 通知）
- SLACK_CHANNEL_ID: Slack の送信先チャンネル ID
- OPENAI_API_KEY: OpenAI API キー（ai モジュール使用時）
- 任意:
  - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
  - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: SQLite（monitoring）パス（デフォルト: data/monitoring.db）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットすると .env 自動ロードを無効化できます（テスト用）

自動 .env ロード
- プロジェクトルート（.git または pyproject.toml のあるディレクトリ）にある `.env` / `.env.local` を自動で読み込み、OS 環境変数が優先されます。
- 自動読み込みを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

注意: .env.example はリポジトリに含める想定の設定サンプルです（本コードベースでは参照が記載されています）。実運用時は機密情報を安全に管理してください。

---

## 使い方（代表的な例）

以下は簡単な使用例です。各例は DuckDB 接続（duckdb.connect）を前提とします。

1) 日次 ETL の実行（株価・財務・カレンダー取得 + 品質チェック）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースのセンチメント解析（ai -> ai_scores に書き込む）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"written {written} codes")
```

3) マーケットレジーム評価（market_regime に書き込む）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

4) 監査ログスキーマの初期化（監査専用 DB）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn を使って order_events 等を記録できます
```

5) RSS フィード取得（ニュース収集ユーティリティ）
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```

6) リサーチ（ファクター計算例）
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
value = calc_value(conn, date(2026, 3, 20))
```

各関数は docstring に引数・戻り値・副作用（DB書き込みの有無）を記載していますので、利用前に確認してください。

---

## 主要モジュール / ディレクトリ構成

（ソースルート: src/kabusys）

- __init__.py
- config.py
  - Settings: 環境変数読み取り / 必須チェック / 自動 .env ロード
- ai/
  - __init__.py
  - news_nlp.py         — ニュースセンチメント（LLM）で ai_scores を更新
  - regime_detector.py  — MA + マクロニュース（LLM）で market_regime を算出
- data/
  - __init__.py
  - jquants_client.py   — J-Quants API クライアント & DuckDB 保存関数
  - pipeline.py         — ETL パイプライン（run_daily_etl 等）
  - etl.py              — ETLResult 再エクスポート
  - news_collector.py   — RSS 取得・前処理・raw_news への保存支援
  - calendar_management.py — 市場カレンダー管理（営業日判定等）
  - quality.py          — データ品質チェック（欠損/重複/スパイク/日付整合性）
  - stats.py            — 統計ユーティリティ（zscore_normalize）
  - audit.py            — 監査ログテーブルの DDL / 初期化
- research/
  - __init__.py
  - factor_research.py  — モメンタム/ボラティリティ/バリュー計算
  - feature_exploration.py — 将来リターン/IC/統計サマリー 等

（上記に加え、strategy / execution / monitoring などのサブパッケージがメインパッケージの __all__ に含まれる想定）

---

## 設計上の注意点・トラブルシューティング

- OpenAI を使う処理（news_nlp, regime_detector）は API キーを必須にします。API エラー発生時は多くの処理がフォールバック（0.0 スコア等）して継続する設計ですが、結果の欠落に注意してください。
- DuckDB の executemany はバージョン差で空リストを受け入れない実装があります。pipeline では空チェックを行ってから executemany を呼び出しています。
- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml）を基準に行います。パッケージ配布後にcwdに依存しないよう実装済みですが、CI/テスト時に邪魔な場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。
- J-Quants API のレート制限に従うため内部で固定間隔スロットリングを行っています。大量の同期リクエストを行う場合は注意してください。
- news_collector は RSS フィードの最大サイズやリダイレクト先のプライベートIPチェック（SSRF対策）を行います。社内プロキシ等を通す場合は挙動に注意してください。

---

## ライセンス・貢献

このREADME はコードベースの説明を目的に生成されています。実際のライセンスや開発フロー（CONTRIBUTING.md 等）はリポジトリに従ってください。

---

必要なら README をさらに拡充して、各関数の API 参照一覧（関数名・引数・戻り値）や .env.example のテンプレート、データベーススキーマのサンプル、CI 用のテスト手順なども追加します。どの情報を優先して追加しましょうか？