# KabuSys

KabuSys は日本株向けの自動売買 / データ基盤ライブラリです。  
J-Quants API からのデータ取得（OHLCV / 財務 / 市場カレンダー）、RSS ニュース収集、LLM を用いたニュースセンチメント評価、ファクター計算、ETL パイプライン、監査ログ（取引トレーサビリティ）などを提供します。  
このリポジトリはバッチ ETL・リサーチ・戦略開発・発注監査に必要なユーティリティをモジュール化しています。

主な目的：
- データ収集と品質管理（DuckDB を利用）
- ニュースの NLP による銘柄別スコアリング（OpenAI）
- 市場レジーム判定（ETF + マクロニュース）
- ファクター計算・特徴量探索（バックテスト前処理）
- 発注フローの監査ログ（監査テーブル初期化）

---

## 機能一覧

- 設定管理
  - .env / 環境変数自動ロード（プロジェクトルート検出）
  - 必須環境変数チェック（settings オブジェクト）
- データ ETL（kabusys.data.pipeline）
  - 日次 ETL（市況カレンダー、株価、財務データ）
  - 差分取得・バックフィル対応・品質チェック
- J-Quants API クライアント（kabusys.data.jquants_client）
  - 株価日足 / 財務 / 上場銘柄情報 / カレンダー取得
  - レートリミット・再試行・トークン自動リフレッシュ
  - DuckDB への冪等保存関数
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得・前処理・SSRF/サイズ/追跡パラメータ対策
- ニュース NLP（kabusys.ai.news_nlp）
  - 銘柄ごとのニュース統合センチメントを OpenAI で評価し ai_scores に書き込み
- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF（1321）の 200 日 MA 乖離 + マクロニュース LLM センチメントで daily レジーム判定
- 研究用ユーティリティ（kabusys.research）
  - モメンタム / ボラティリティ / バリューのファクター計算
  - 将来リターン計算 / IC（スピアマン） / ファクター統計サマリー
- データ品質チェック（kabusys.data.quality）
  - 欠損・重複・スパイク・日付不整合検出
- 監査ログ（kabusys.data.audit）
  - signal_events, order_requests, executions テーブル定義と初期化ユーティリティ
  - 監査 DB 初期化関数（init_audit_db）

---

## セットアップ手順

前提
- Python 3.10+ を推奨（型ヒントに Union 型の表記などを使用）
- DuckDB、openai、defusedxml 等の依存パッケージ

例: 仮想環境作成と依存インストール
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
# requirements.txt を用意している場合
pip install -r requirements.txt
# 最低限の依存例
pip install duckdb openai defusedxml
```

推奨 requirements.txt の一例（プロジェクトに応じて調整してください）:
```
duckdb
openai
defusedxml
```

環境変数（必須）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD : kabu ステーション API のパスワード（必要に応じて）
- SLACK_BOT_TOKEN : Slack 通知を使う場合の Bot Token
- SLACK_CHANNEL_ID : Slack のチャンネル ID

オプション環境変数
- OPENAI_API_KEY : OpenAI API キー（score_news / score_regime に必要）
- KABUSYS_ENV : development / paper_trading / live（デフォルト: development）
- LOG_LEVEL : DEBUG/INFO/...
- DUCKDB_PATH : デフォルト data/kabusys.duckdb
- SQLITE_PATH : デフォルト data/monitoring.db
- KABUSYS_DISABLE_AUTO_ENV_LOAD : 1 を設定すると .env の自動ロードを無効化

.env ファイル自動読み込み
- プロジェクトルート（.git または pyproject.toml を基準）にある `.env` と `.env.local` を自動で読み込みます。
- 自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 使い方（基本例）

以下は簡単な Python スニペット例です。実行前に必須環境変数をセットしてください。

1) DuckDB に接続して日次 ETL を実行する
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

# settings.duckdb_path は Path オブジェクトを返す
conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニューススコアリング（OpenAI が必要）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
# API キーを引数で渡すか環境変数 OPENAI_API_KEY を設定
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print("書き込んだ銘柄数:", n_written)
```

3) 市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

4) 監査用 DuckDB を初期化する
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# テーブルが生成され、UTC タイムゾーンが設定されます
```

5) J-Quants API からのデータ取得（直接呼び出し例）
```python
from kabusys.data.jquants_client import fetch_daily_quotes
from kabusys.config import settings
# id_token は自動で取得される（settings.jquants_refresh_token が必要）
records = fetch_daily_quotes(date_from=None, date_to=None)
print(len(records))
```

---

## よくある操作の注意点

- LLM 呼び出し（OpenAI）：API エラー時はフェイルセーフで一定のフォールバック（0 スコア等）を行う設計です。API キーは環境変数 OPENAI_API_KEY を設定するか各関数に渡してください。
- DuckDB executemany の空リストバインドに注意：一部関数は空 params をチェックしてから executemany を呼び出しています。
- 自動ロードされる .env はプロジェクトルート基準で読み込まれます。CI／テストでは KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py — パッケージエントリ（version 等）
- config.py — 環境変数 / 設定読み込みロジック（.env 自動ロード、settings オブジェクト）
- ai/
  - __init__.py
  - news_nlp.py — ニュースの LLM スコアリング（ai_scores テーブルへ書き込み）
  - regime_detector.py — 市場レジーム判定（ETF 1321 + マクロニュース）
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（取得＋DuckDB 保存）
  - pipeline.py — ETL パイプライン（run_daily_etl 等）
  - etl.py — ETL の結果クラス再公開（ETLResult）
  - news_collector.py — RSS 収集・前処理・保存ユーティリティ
  - calendar_management.py — 市場カレンダーの判定・更新ロジック
  - stats.py — 共通統計ユーティリティ（zscore_normalize）
  - quality.py — データ品質チェック
  - audit.py — 監査ログ（テーブル定義・初期化）
- research/
  - __init__.py
  - factor_research.py — モメンタム / バリュー / ボラティリティ計算
  - feature_exploration.py — 将来リターン計算 / IC / 統計サマリー

各モジュールはドキュメンテーション文字列（docstring）で設計方針や制約が詳述されています。関数の引数や返り値も docstring に明記してあるため、参照して利用してください。

---

## テスト / 開発上のヒント

- モジュール内では datetime.today() / date.today() を直接参照しない設計方針が多く採られています（ルックアヘッドバイアス防止）。関数呼び出し時に target_date を明示的に渡すことを推奨します。
- OpenAI、ネットワーク呼び出し部分はユニットテストでモックしやすいように設計されています（_call_openai_api などを patch）。
- DuckDB のスキーマ変更やバージョン差に起因する挙動は注意してください（executemany の空リスト等）。

---

必要であれば、README に以下の追加を生成できます：
- 具体的な .env.example（サンプル）
- requirements.txt の推奨バージョン固定リスト
- よくあるエラーと対処（例: OpenAI レート制限・J-Quants の 401 トークンリフレッシュ失敗）

必要な項目を教えてください。