# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けのデータプラットフォームおよび自動売買支援ライブラリです。J-Quants API からのデータ収集（ETL）、ニュースの NLP による銘柄スコアリング、マーケットレジーム判定、リサーチ用ファクター計算、監査ログ（発注／約定トレーサビリティ）などを提供します。

主な設計方針:
- ルックアヘッドバイアスを避ける（内部で日付を今日参照しない等）
- DuckDB を主要なローカルデータストアとして使用
- J-Quants / OpenAI など外部 API 呼び出しに対してリトライ・レート制御・フェイルセーフを実装
- 冪等（idempotent）な DB 保存を重視

---

## 機能一覧

- 環境設定管理
  - .env / .env.local から自動または明示的に環境変数を読込
  - 必須設定の検査（Settings オブジェクト）
- データ取得 / ETL（kabusys.data.pipeline）
  - J-Quants からの日次株価（OHLCV）、財務データ、マーケットカレンダーの差分取得・保存
  - 品質チェック（欠損、スパイク、重複、日付不整合）
  - 日次 ETL の統合実行（run_daily_etl）
- カレンダー管理（kabusys.data.calendar_management）
  - 営業日判定 / next/prev 営業日の算出 / 期間内営業日取得
  - JPX カレンダーの差分更新ジョブ
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得（SSRF対策、gzip対応、トラッキングパラメータ除去）
  - raw_news / news_symbols への冪等保存
- ニュース NLP（kabusys.ai.news_nlp）
  - OpenAI（gpt-4o-mini）を用いた銘柄別センチメントスコア計算（ai_scores テーブルへ保存）
  - バッチ処理、レスポンス検証、リトライ制御
- レジーム判定（kabusys.ai.regime_detector）
  - ETF（1321）の 200 日 MA 乖離 + マクロニュース LLM センチメントを合成して市場レジーム判定
- 研究用ユーティリティ（kabusys.research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、統計サマリ、Z スコア正規化
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions を含む監査テーブルの初期化とユーティリティ
  - 監査 DB 初期化関数（init_audit_db）

---

## セットアップ

前提
- Python >= 3.10（Union 型 annotation `X | Y` を使用）
- DuckDB をネイティブに使える環境

（プロジェクトに requirements.txt がある場合はそちらを使用してください。以下は最低限の例です）

推奨パッケージ例:
- duckdb
- openai
- defusedxml

インストール例（venv 推奨）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb openai defusedxml
# 開発中: パッケージを editable install
pip install -e .
```

環境変数
- KabuSys は .env/.env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動ロードします。
- 自動ロードを無効にする場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

主要な環境変数（コード中で参照されるもの）
- JQUANTS_REFRESH_TOKEN（必須）: J-Quants の refresh token
- KABU_API_PASSWORD（必須）: kabuステーション API のパスワード
- KABU_API_BASE_URL（任意）: デフォルト "http://localhost:18080/kabusapi"
- SLACK_BOT_TOKEN（必須）: Slack 通知用
- SLACK_CHANNEL_ID（必須）: Slack 通知先チャンネルID
- DUCKDB_PATH（任意）: デフォルト "data/kabusys.duckdb"
- SQLITE_PATH（任意）: 監視用 SQLite データベースパス（デフォルト "data/monitoring.db"）
- KABUSYS_ENV（任意）: development / paper_trading / live（デフォルト development）
- LOG_LEVEL（任意）: DEBUG/INFO/WARNING/ERROR/CRITICAL
- OPENAI_API_KEY（OpenAI を使う機能で必要）: OpenAI API キー

.env.example を参考に .env を作成してください（リポジトリに例がある前提）。

---

## 使い方（主要ユースケース）

以下は簡単な利用例です。いずれも DuckDB 接続オブジェクト（duckdb.connect(...) の戻り値）を渡して実行します。

1) 設定参照

```python
from kabusys.config import settings

print(settings.jquants_refresh_token)
print(settings.duckdb_path)
print(settings.is_live)
```

2) 監査 DB 初期化（新規 DuckDB ファイルに監査スキーマを作成）

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# 以降 conn を使って監査ログを書き込む
```

3) 日次 ETL 実行（株価・財務・カレンダー取得 + 品質チェック）

```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

4) ニュース NLP による銘柄スコア算出（OpenAI API が必要）

```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# 環境変数 OPENAI_API_KEY を設定しているか、api_key 引数で渡す
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書込銘柄数: {written}")
```

5) 市場レジーム判定

```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

6) 研究用ファクター計算（例: モメンタム）

```python
import duckdb
from datetime import date
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は [{ "date": ..., "code": "...", "mom_1m": ..., ... }, ...]
```

注意点:
- OpenAI 呼び出し部はリトライを行いますが、API キーが未設定だと ValueError を送出します。テスト時は _call_openai_api をモックして外部コールを回避してください（各モジュールで差し替え可能）。
- DuckDB の executemany に空リストを渡すとエラーになるバージョンがあるため、コード内で空チェックしています。

---

## ディレクトリ構成（主要ファイル）

（簡略化したツリー）

- src/
  - kabusys/
    - __init__.py
    - config.py  -> 環境変数・設定管理
    - ai/
      - __init__.py
      - news_nlp.py       -> ニュース NLP スコアリング（OpenAI）
      - regime_detector.py-> 市場レジーム判定（MA200 + マクロニュース）
    - data/
      - __init__.py
      - jquants_client.py       -> J-Quants API クライアント（取得 + 保存）
      - pipeline.py             -> ETL パイプライン（run_daily_etl 等）
      - etl.py                  -> ETL インターフェース再エクスポート
      - calendar_management.py  -> 市場カレンダー管理
      - news_collector.py       -> RSS ニュース収集・保存
      - stats.py                -> 汎用統計ユーティリティ（zscore 等）
      - quality.py              -> データ品質チェック
      - audit.py                -> 監査ログスキーマ定義 / 初期化
    - research/
      - __init__.py
      - factor_research.py      -> Momentum/Value/Volatility の計算
      - feature_exploration.py  -> 将来リターン, IC, 統計サマリ 等

---

## 開発・テストに関するメモ

- 自動で .env を読み込む仕組みを持っています（プロジェクトルートの .env / .env.local）。テスト時に自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI を呼ぶコードは挙動をテスト可能にするため internal 呼出関数（_call_openai_api）をモックして差し替え可能です。
- DuckDB 関連はローカルファイル（data/*.duckdb）や ":memory:" を使用してテスト可能です。
- 大きな外部依存（J-Quants, OpenAI, RSS）を伴う部分は統合テストでモック／スタブ化することを推奨します。

---

## 追加情報 / トラブルシューティング

- .env に必須変数が無い場合、Settings の該当プロパティを参照すると ValueError が発生します。 .env.example を参考に必要なキーをセットしてください。
- J-Quants API はレート制限があるため fetch 系は内部でスロットリングを行います。大量取得やループ処理を行う際は注意してください。
- RSS 収集では SSRF 対策（リダイレクト先の検証、プライベート IP ブロック）や受信サイズ制限を行っています。外部フィードを追加する際は source URL を事前に確認してください。

---

もし README に追加してほしい内容（例: 実際の .env.example, CI / デプロイ手順、詳細な API 使用例やスキーマ定義の自動生成方法など）があれば教えてください。