# KabuSys

日本株向け自動売買 / データプラットフォーム用ライブラリ。  
ETL（J-Quants）→ DuckDB、ニュース収集・NLP（OpenAI）、市場レジーム判定、ファクター計算、監査ログ等の機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株に特化した以下の処理を一貫して行うためのモジュール群です。

- J-Quants API からの差分 ETL（株価、財務、マーケットカレンダー）
- DuckDB ベースのデータ格納・品質チェック
- RSS ニュース収集と前処理（SSRF・XML攻撃などへの防御を含む）
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント評価（銘柄別 / マクロ）
- ETF（1321）の MA 乖離 + マクロセンチメントを合成した市場レジーム判定
- 研究用ファクター計算（モメンタム・ボラティリティ・バリュー等）
- 監査ログ（signal → order_request → execution のトレース可能なスキーマ）
- 環境変数管理（.env 自動読み込み、テスト用に無効化可能）

設計上、ルックアヘッドバイアスを避ける実装や API リトライ・バックオフ・フェイルセーフの方針が各所に組み込まれています。

---

## 主な機能一覧

- data.jquants_client: J-Quants からの取得・DuckDB への冪等保存
- data.pipeline: 日次 ETL パイプライン（run_daily_etl）
- data.calendar_management: 市場カレンダー管理・営業日判定
- data.news_collector: RSS 取得・記事前処理・保存（SSRF/size 保護）
- ai.news_nlp: ニュース銘柄別の NLP スコア取得（score_news）
- ai.regime_detector: ETF MA と LLM を用いた市場レジーム判定（score_regime）
- research: ファクター計算（momentum, volatility, value）および解析ユーティリティ
- data.quality: データ品質チェック（欠損・重複・スパイク・日付不整合）
- data.audit: 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
- config: .env 自動ロード・環境設定ラッパー（settings）

---

## 必要条件

- Python 3.10+
- 主要依存ライブラリ（抜粋）:
  - duckdb
  - openai
  - defusedxml

プロジェクトに同梱の pyproject.toml / requirements.txt を利用してください。無ければ例示のように個別インストールしてください。

例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# またはリポジトリルートで
# pip install -e .
```

---

## セットアップ手順

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成して依存をインストール
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt   # あれば
   # ない場合:
   pip install duckdb openai defusedxml
   ```

3. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` を置くと自動で読み込まれます。
   - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途）。

   代表的な環境変数（.env に記載例）:
   - JQUANTS_REFRESH_TOKEN=<your_jquants_refresh_token>  （必須：J-Quants 認証）
   - OPENAI_API_KEY=<your_openai_api_key>               （必須：AI スコアリング）
   - KABU_API_PASSWORD=<...>                            （kabuステーション連携がある場合）
   - LINE_CHANNEL_ACCESS_TOKEN=...                     （通知が必要な場合）
   - LINE_USER_ID=...
   - DUCKDB_PATH=data/kabusys.duckdb
   - SQLITE_PATH=data/monitoring.db
   - KILL_FLAG_CLEAR_ON_START=0
   - CPU_THRESHOLD_PCT=90.0
   - LOG_LEVEL=INFO
   - KABUSYS_ENV=development  # development / paper_trading / live

4. データディレクトリ作成（DuckDB ファイル等の格納先）
   ```bash
   mkdir -p data
   ```

---

## 使い方（簡易ガイド）

以下は Python API を直接使う例です。すべて Look-ahead を避ける設計で、target_date を明示的に渡すことを推奨します。

- DuckDB 接続例:
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 監査 DB 初期化:
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db(settings.duckdb_path)
```

- 日次 ETL 実行:
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20), run_quality_checks=True)
print(result.to_dict())
```

- ニュースセンチメント（銘柄別）スコア生成:
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key=None は環境変数を参照
print("scored:", n_written)
```

- 市場レジーム判定:
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- カレンダー更新ジョブ（夜間バッチ想定）:
```python
from kabusys.data.calendar_management import calendar_update_job
calendar_update_job(conn)
```

注意:
- OpenAI 呼び出しはネットワーク依存・エラー時はフェイルセーフ（スコアを 0 にフォールバック）で進行します。
- J-Quants API はレート制限・リトライを実装していますが、認証トークン（refresh token）は必須です。

---

## .env の自動読み込み

- .env 自動読み込みの動作:
  - プロジェクトルート（.git または pyproject.toml を検出）を基準に `.env` → `.env.local` の順で読み込みます。
  - OS 環境変数は上書きされません（`.env.local` は override=True で読み込まれますが OS 変数は保護されます）。
- 無効化:
  - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動読み込みをスキップします（テストで便利）。

---

## ディレクトリ構成（主要ファイル／概要）

src/kabusys/
- __init__.py — パッケージエントリ（version 等）
- config.py — 環境変数 / 設定管理（settings）
- ai/
  - __init__.py
  - news_nlp.py — ニュースをまとめて OpenAI に投げ、ai_scores を作成する（score_news）
  - regime_detector.py — ETF MA とマクロセンチメントで市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（取得・保存ロジック）
  - pipeline.py — ETL パイプライン（run_daily_etl 等）
  - calendar_management.py — マーケットカレンダー管理・営業日判定
  - news_collector.py — RSS 取得・前処理・保存（SSRF 対策・XML 安全処理）
  - quality.py — データ品質チェック
  - stats.py — 汎用統計ユーティリティ（zscore_normalize）
  - etl.py — ETL インターフェース再エクスポート
  - audit.py — 監査ログテーブル定義と初期化（init_audit_schema/init_audit_db）
- research/
  - __init__.py
  - factor_research.py — モメンタム / ボラティリティ / バリュー計算
  - feature_exploration.py — 将来リターン計算、IC、統計サマリー等
- monitoring/, execution/, strategy/ など（パッケージ __all__ に含まれるが実装箇所はプロジェクトに依存）

（README 上では主要モジュールに絞って記載しています。実装全体は src/kabusys 以下をご参照ください。）

---

## 開発・テスト上の注意点

- 型ヒントや新しい構文（X | Y）を使用しているため Python 3.10+ を推奨します。
- OpenAI / J-Quants API 呼び出し部分は外部サービスに依存するため、ユニットテストでは該当関数をモックする想定です（コード内にもモックしやすい設計あり）。
- DuckDB の executemany は空リストでの呼び出しに注意（モジュール内でガードされています）。
- news_collector は defusedxml を用いて XML 攻撃に配慮しています。RSS フィード取得時は SSRF 対策（ホストのプライベート判定等）があります。

---

## トラブルシューティング（よくある質問）

- OpenAI キーが無い / 誤っている:
  - score_news / score_regime は ValueError を投げます。環境変数 OPENAI_API_KEY を確認してください。
- J-Quants 認証エラー:
  - JQUANTS_REFRESH_TOKEN を `.env` に設定してください。get_id_token は自動リフレッシュを行いますが、refresh token 自体が必要です。
- .env が読み込まれない:
  - プロジェクトルートの検出は .git または pyproject.toml を基準にします。ルートが検出されないと自動読み込みは行われません。
  - 自動読み込みを無効化していないか（KABUSYS_DISABLE_AUTO_ENV_LOAD）を確認してください。

---

## ライセンス・貢献

（リポジトリ側の LICENSE / CONTRIBUTING を参照してください）

---

必要であれば README に含めるサンプル .env.example、requirements.txt のテンプレや CLI 実行方法（cron / systemd ユニット例）も作成します。どの追加情報が必要か指示ください。