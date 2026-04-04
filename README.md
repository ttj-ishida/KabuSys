# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
データ取得（J-Quants）、ETL、ニュース収集・NLP（OpenAI）、リサーチ（ファクター計算）、監査ログなどのユーティリティを提供します。

主な設計方針は「ルックアヘッドバイアス回避」「DuckDB を用いたデータ永続化」「冪等性のある ETL / 保存処理」「外部 API 呼び出しの堅牢化（リトライ・レート制御）」です。

バージョン: 0.1.0

---

## 機能一覧

- 環境変数 / .env の自動読み込みと Settings API
  - .env / .env.local をプロジェクトルートから自動読み込み（無効化可能）
- J-Quants クライアント
  - 株価日足（OHLCV）の取得・保存
  - 財務データ取得・保存
  - JPX マーケットカレンダー取得・保存
  - レート制御・リトライ・自動トークンリフレッシュ対応
- ETL パイプライン
  - run_daily_etl による日次 ETL（カレンダー → 株価 → 財務 → 品質チェック）
  - 差分取得・バックフィル・品質チェックの仕組み
- ニュース収集（RSS）
  - RSS フィード取得、前処理、raw_news への冪等保存、銘柄紐付け
  - SSRF / 大きすぎるレスポンス等のセキュリティ対策
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュースを LLM（gpt-4o-mini 等）でセンチメント評価して ai_scores に書き込み
  - バッチ化・トリム・結果バリデーション・リトライ
- 市場レジーム判定
  - ETF 1321 の 200 日 MA 乖離（70%）とマクロニュース LLM センチメント（30%）を合成して market_regime に保存
  - API フェイルセーフ、リトライ実装
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（スピアマン）計算、統計サマリー
- 監査ログ（Audit）
  - signal_events / order_requests / executions テーブル定義と初期化ユーティリティ
  - 監査トレーサビリティ設計（UUID 連鎖、UTC タイムスタンプ）

---

## セットアップ手順

前提:
- Python 3.10+ を推奨（型注釈で union といった構文を利用）
- DuckDB を使います
- OpenAI API を用いる機能は `openai` SDK（openai パッケージ）を使用

1. レポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境の作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 依存関係のインストール（最低限）
   ```
   pip install duckdb openai defusedxml
   ```
   - 実プロジェクトでは pyproject.toml / requirements.txt に合わせてインストールしてください。

4. パッケージを開発モードでインストール（任意）
   ```
   pip install -e .
   ```

5. 環境変数の設定
   - プロジェクトルートに `.env`（および必要に応じて `.env.local`）を配置すると自動で読み込まれます。
   - 自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須の環境変数（最低限）
- JQUANTS_REFRESH_TOKEN：J-Quants のリフレッシュトークン（ETL 用）
- KABU_API_PASSWORD：kabuステーション等の発注系 API のパスワード（発注機能を使う場合）
- OPENAI_API_KEY：OpenAI を使用する場合（news_nlp / regime_detector）

その他（任意・デフォルトあり）
- KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（通知）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PID_FILE_PATH / KILL_FLAG_PATH / 監視閾値等
- KABUSYS_ENV（development | paper_trading | live、デフォルト development）
- LOG_LEVEL（DEBUG/INFO/...、デフォルト INFO）

例 `.env`（プロジェクトルート）:
```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
```

---

## 使い方（代表的な例）

以下は Python から主要機能を呼ぶ例です。DuckDB の接続は config.Settings で指定したパスを利用します。

1) Settings の利用
```python
from kabusys.config import settings
print(settings.duckdb_path)
```

2) 日次 ETL を実行（run_daily_etl）
```python
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```
- ETL はカレンダー → 株価 → 財務 → 品質チェック の順で実行します。
- ETL は Look-ahead バイアスを避けるため、内部で対象日を営業日に調整します。

3) ニュースのセンチメント評価（銘柄単位）
```python
from kabusys.ai.news_nlp import score_news
import duckdb
from datetime import date
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"Wrote scores for {n_written} symbols")
```
- OpenAI API キーは環境変数 `OPENAI_API_KEY` を使うか、api_key 引数で渡せます。
- 処理はバッチ化され、レスポンスの検証やリトライを行います。

4) 市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime
import duckdb
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```
- ETF 1321 の MA200 乖離とマクロニュースセンチメントを合成して market_regime テーブルに書き込みます。
- OpenAI を使うため OPENAI_API_KEY が必要です。

5) 監査ログ（Audit）スキーマ初期化
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions 等のテーブルが作成されます
```

6) J-Quants の直接利用例
```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
from kabusys.config import settings
from datetime import date

token = get_id_token()  # settings.jquants_refresh_token を利用して取得
records = fetch_daily_quotes(id_token=token, date_from=date(2026,1,1), date_to=date(2026,1,31))
```

注意点:
- 多くの関数は DuckDB 接続（kabusys で期待されるスキーマを持つ）を前提とします。まずは ETL を実行して必要なテーブルを作成・更新してください。
- OpenAI 呼び出しに依存する機能は API 失敗時にフェイルセーフ（スコア 0.0 やスキップ）する設計です。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / .env 読み込みと Settings
  - ai/
    - __init__.py
    - news_nlp.py — ニュースセンチメント（銘柄ごと）
    - regime_detector.py — 市場レジーム判定（ETF + マクロLLM）
  - data/
    - __init__.py
    - calendar_management.py — 市場カレンダーの判定・更新・ユーティリティ
    - etl.py — ETL の公開型（ETLResult など）
    - pipeline.py — ETL 実装（run_daily_etl, run_prices_etl 等）
    - stats.py — zscore_normalize 等の統計ユーティリティ
    - quality.py — データ品質チェック
    - audit.py — 監査ログテーブル定義と初期化
    - jquants_client.py — J-Quants API クライアント（取得/保存）
    - news_collector.py — RSS 収集・前処理・保存
  - research/
    - __init__.py
    - factor_research.py — モメンタム / バリュー / ボラティリティ等
    - feature_exploration.py — 将来リターン / IC / 統計サマリー

---

## 設計上の注意点 / 運用上のヒント

- Look-ahead Bias
  - 多くの処理は日時の取り扱いでルックアヘッドバイアスを避けるよう設計されています（target_date を明示、DB クエリは date < target_date など）。
- 時刻・タイムゾーン
  - 監査ログや fetched_at などは UTC で保存する設計です（init_audit_schema は TimeZone を UTC に設定）。
- 冪等性
  - save_* 関数は ON CONFLICT DO UPDATE（または INSERT ... DO NOTHING）で冪等に保存します。
- リトライ・レート制御
  - J-Quants クライアントは 120 req/min に合わせたスロットリングとリトライを実装しています。
  - OpenAI 呼び出しも RateLimitError 等に対するリトライとバックオフを備えています。
- テスト
  - API 呼び出し部位は差し替え（モック）が想定されています（内部の _call_openai_api 等を patch してテスト可能）。

---

## 開発 / 貢献

- コーディング規約、ユニットテスト、CI のフローはプロジェクト規約に従ってください。
- 外部 API を直接叩くテストはリソース制限のためモックすることを推奨します。
- .env.example を用意して必要な環境変数をドキュメント化しておくと便利です。

---

README に書かれている以上の詳細な API 使用方法や DB スキーマの完全な説明は各モジュールの docstring を参照してください。必要であれば、特定ユースケース（ETL スケジュール、発注フロー、監視設定など）についての追加ドキュメントを作成します。