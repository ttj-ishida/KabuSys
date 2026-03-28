# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ。  
ETL（J-Quants からのデータ取り込み）、ニュース収集・NLP（OpenAI）、調査（ファクター計算）、監査ログ、マーケットカレンダー管理などの機能を提供します。

バージョン: 0.1.0

---

## 主な機能

- データ収集 / ETL
  - J-Quants API から株価日足（OHLCV）、財務データ、JPX カレンダーを差分取得して DuckDB に保存（冪等処理・リトライ・レート制御）
  - データ品質チェック（欠損・重複・スパイク・日付不整合）
- ニュース収集
  - RSS フィードの収集（SSRF 対策、トラッキングパラメータ除去、前処理）
  - raw_news / news_symbols への冪等保存
- ニュース NLP（OpenAI）
  - 銘柄別ニュースを LLM（gpt-4o-mini）でセンチメント化し ai_scores に保存（バッチ・リトライ・レスポンス検証）
  - マクロニュースを使った市場レジーム判定（ma200 と LLM センチメント合成）
- 調査（Research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン、IC（Spearman）、統計サマリー、Zスコア正規化ユーティリティ
- 監査ログ（Audit）
  - シグナル→発注→約定までトレーサビリティを保つ監査テーブル定義と初期化ユーティリティ
- マーケットカレンダー管理（営業日判定、更新ジョブ）

---

## 必要な環境変数（.env）

自動的にプロジェクトルートの `.env` / `.env.local` を読み込みます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

主な環境変数（例）:

- JQUANTS_REFRESH_TOKEN=<your_jquants_refresh_token>
- OPENAI_API_KEY=<your_openai_api_key>
- KABU_API_PASSWORD=<kabu_station_api_password>
- KABU_API_BASE_URL=http://localhost:18080/kabusapi
- SLACK_BOT_TOKEN=<slack_bot_token>
- SLACK_CHANNEL_ID=<slack_channel_id>
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- KABUSYS_ENV=development  # 有効値: development / paper_trading / live
- LOG_LEVEL=INFO

.env のパースはシェル風（export KEY=val, quotes, inline コメント等）に対応します。

---

## セットアップ手順

1. リポジトリをクローン（既にプロジェクト配布を想定）
2. Python 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール

（requirements.txt は本リポジトリに無い想定のため、主要依存を例示します）
- pip install duckdb openai defusedxml

パッケージとしてインストールする場合:
- pip install -e .

4. 環境変数を設定
   - プロジェクトルートに `.env` を作成するか、OS 環境変数を設定してください。
   - 例（.env）:
     ```
     JQUANTS_REFRESH_TOKEN=xxxx
     OPENAI_API_KEY=sk-xxxx
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=DEBUG
     ```
5. DuckDB データベースや監査DBの初期化（必要に応じて）

---

## 使い方（代表的な利用例）

以下は Python スクリプトや REPL からの呼び出し例です。

- DuckDB に接続して日次 ETL を実行する（J-Quants 必須）
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコアリング（OpenAI APIキー必須）
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-xxxx")
print(f"書き込んだ銘柄数: {written}")
```

- 市場レジーム判定（OpenAI APIキー必須）
```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-xxxx")
```

- 監査DB初期化（監査テーブルを作成）
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# conn は初期化済み DuckDB 接続を返します
```

- マーケットカレンダー更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"保存レコード数: {saved}")
```

注意:
- AI を使う機能（news_nlp / regime_detector）は OPENAI_API_KEY を必須とします（引数 api_key を通して注入可能）。
- ETL の外部 API 呼び出し（J-Quants）は JQUANTS_REFRESH_TOKEN が必要です。

---

## モジュール / ディレクトリ構成

主要ファイルおよび役割の一覧（src/kabusys 以下）:

- __init__.py
  - パッケージのエクスポート (data, strategy, execution, monitoring)
- config.py
  - 環境変数の自動ロード（.env / .env.local）、Settings クラス（設定値取得）
- ai/
  - __init__.py
  - news_nlp.py — ニュースの LLM スコアリング、score_news を提供
  - regime_detector.py — ma200 と LLM を合成した市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（取得・保存・認証・レート制御）
  - pipeline.py — ETL パイプライン（run_daily_etl 等）
  - etl.py — ETL の公開インターフェース（ETLResult を再エクスポート）
  - quality.py — データ品質チェック（欠損・重複・スパイク・日付不整合）
  - news_collector.py — RSS 取得・前処理・保存ロジック（SSRF 対策等）
  - calendar_management.py — マーケットカレンダー、営業日判定、更新ジョブ
  - stats.py — 汎用統計ユーティリティ（zscore_normalize など）
  - audit.py — 監査ログ（DDL・初期化関数）
- research/
  - __init__.py
  - factor_research.py — Momentum/Volatility/Value 等のファクター計算
  - feature_exploration.py — 将来リターン、IC、統計サマリー等

（実行時は src をパッケージルートとして import してください）

---

## 実装上の注意点 / 設計方針（短いまとめ）

- ルックアヘッドバイアス防止:
  - 関数は date 引数を受け取り、内部で date.today() を直接参照しない設計。
  - 外部 API 取得時に fetched_at を保存して「いつ知っていたか」をトレース可能に。
- 冪等性:
  - DB への保存は基本的に ON CONFLICT DO UPDATE / INSERT ... ON CONFLICT を使って冪等処理。
- フェイルセーフ:
  - 外部 API（OpenAI / J-Quants）失敗時には可能な限りフォールバック（ゼロスコア、スキップなど）してシステム全体を停止させない設計。
- セキュリティ:
  - news_collector は SSRF・XML 関連攻撃対策（URL スキーム検証、プライベートアドレス検査、defusedxml 利用、受信サイズ上限）を実装。

---

## トラブルシューティング

- 環境変数が読み込まれない / テスト時に読み込みを無効化したい:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードをスキップします。
- OpenAI 呼び出し時のエラー:
  - API のレート制限・ネットワークエラー・5xx に対して内部でリトライを行いますが、API キーやネットワークの状態を確認してください。
- DuckDB の executemany に関する注意:
  - 一部関数では DuckDB のバージョン差異（executemany に空リストを渡せない等）に配慮した実装になっています。エラーが出る場合は DuckDB のバージョンを確認してください。

---

## 参考

- 主要設定: kabusys.config.Settings
- ETL メイン: kabusys.data.pipeline.run_daily_etl
- ニュース NLP: kabusys.ai.news_nlp.score_news
- レジーム判定: kabusys.ai.regime_detector.score_regime
- 監査初期化: kabusys.data.audit.init_audit_db / init_audit_schema

---

必要であれば、README に具体的な CLI（例: invoke / Makefile / entrypoints）や requirements.txt、pyproject.toml との連携手順を追加できます。追加希望があれば教えてください。