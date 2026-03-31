# KabuSys

KabuSys は日本株向けのデータプラットフォームと研究 / 自動売買ユーティリティ群をまとめた Python パッケージです。  
ETL（J-Quants 経由の株価・財務・カレンダー取得）、データ品質チェック、ニュース収集・NLP（OpenAI 利用）、市場レジーム判定、研究用ファクター計算、監査ログ（発注→約定のトレーサビリティ）などの機能を提供します。

バージョン: 0.1.0

---

## 主要機能

- データ取得 / ETL
  - J-Quants API から株価日足、財務データ、JPX マーケットカレンダーを差分取得して DuckDB に保存（冪等性対応）
  - 日次 ETL パイプライン (run_daily_etl)
  - カレンダー更新、差分フェッチ、バックフィル対応

- データ品質チェック
  - 欠損データ、スパイク、重複、日付不整合の検出（QualityIssue モデル）

- ニュース収集 / NLP
  - RSS 取得と前処理（SSRF 対策、トラッキングパラメータ除去）
  - OpenAI を用いた記事単位 / 銘柄単位のセンチメントスコアリング（score_news）
  - ニュース窓の時刻計算（calc_news_window）

- 市場レジーム判定
  - ETF 1321（Nikkei 225 連動型）の 200 日 MA 乖離とマクロニュース LLM センチメントを合成して日次でレジーム（bull/neutral/bear）を判定（score_regime）

- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算（calc_momentum, calc_volatility, calc_value）
  - 将来リターン計算、IC（Information Coefficient）、ファクター統計サマリー
  - クロスセクション Z スコア正規化ユーティリティ

- 監査ログ（Audit）
  - signal_events / order_requests / executions テーブル定義と初期化ユーティリティ（init_audit_schema / init_audit_db）
  - 発注フローのトレーサビリティ確保（UUID ベース）

- 設定管理
  - .env / .env.local / OS 環境変数から設定を自動読み込み（カスタムロジック）
  - settings オブジェクト経由でアクセス（JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY など）

---

## 必須・推奨環境

- Python 3.10+
  - Typing の `X | Y` 形式を使用しているため 3.10 以降を想定しています。
- 主な依存パッケージ（プロジェクトに合わせてインストールしてください）
  - duckdb
  - openai
  - defusedxml

（実際の requirements.txt や setup.cfg / pyproject.toml がある場合はそちらを参照してください）

---

## セットアップ手順

1. リポジトリをクローンし、プロジェクトルートへ移動します。

2. 仮想環境を作成して有効化（例: venv）

   - macOS / Linux:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows:
     ```
     python -m venv .venv
     .\.venv\Scripts\activate
     ```

3. 依存パッケージをインストール（例）
   ```
   pip install duckdb openai defusedxml
   ```

4. 環境変数を設定する
   - プロジェクトルートに `.env` または `.env.local` を置くと、自動的に読み込まれます（優先順: OS 環境 > .env.local > .env）。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途など）。

   最低限必要な環境変数（アプリで参照される必須項目）:
   - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
   - SLACK_BOT_TOKEN — （通知等を使う場合）Slack ボットトークン
   - SLACK_CHANNEL_ID — Slack チャンネル ID
   - KABU_API_PASSWORD — kabu ステーション API のパスワード（発注などを行う場合）
   - OPENAI_API_KEY — OpenAI API キー（score_news / score_regime を使う場合）

   例 `.env`（最小例）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABU_API_PASSWORD=your_kabu_password
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   ```

---

## 使い方（簡易ガイド）

以下は Python スクリプトや REPL から直接使う例です。

共通: settings と DuckDB 接続の取得
```python
from kabusys.config import settings
import duckdb

# settings.duckdb_path は Path オブジェクト（デフォルト "data/kabusys.duckdb"）
conn = duckdb.connect(str(settings.duckdb_path))
```

1) 日次 ETL を実行する
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

# target_date を省略すると今日が対象
result = run_daily_etl(conn, target_date=date(2026, 3, 20))

print(result.to_dict())
```

2) ニュースのセンチメントを算出して ai_scores へ書き込む
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# OPENAI_API_KEY は環境変数に設定するか、api_key 引数で渡す
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print("書き込んだ銘柄数:", n_written)
```

3) 市場レジーム判定（score_regime）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

4) 監査ログ（audit）スキーマの初期化
```python
from kabusys.data.audit import init_audit_db, init_audit_schema

# 専用ファイルを作る場合
audit_conn = init_audit_db("data/audit.duckdb")  # 監査用 DB を作成して接続を返す

# 既存接続に監査スキーマを追加する場合
init_audit_schema(conn, transactional=True)
```

5) 研究用ファクター計算
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

momentum = calc_momentum(conn, target_date=date(2026, 3, 20))
vol = calc_volatility(conn, target_date=date(2026, 3, 20))
value = calc_value(conn, target_date=date(2026, 3, 20))
```

注意:
- OpenAI 呼び出し部はネットワーク/API の失敗に対してフェイルセーフを備えていますが、API キーや料金、レート制限に注意してください。
- 日付処理はルックアヘッドバイアス防止のため、内部で date.today() を直接参照しない設計の関数が多く、target_date を明示することが推奨されます（バックテスト時の再現性向上）。

---

## 設定項目（settings）と既定値

settings オブジェクト（kabusys.config.settings）からアクセス可能な主な設定:

- jquants_refresh_token: 環境変数 JQUANTS_REFRESH_TOKEN（必須）
- kabu_api_password: KABU_API_PASSWORD（必須）
- kabu_api_base_url: KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
- slack_bot_token: SLACK_BOT_TOKEN（必須）
- slack_channel_id: SLACK_CHANNEL_ID（必須）
- duckdb_path: DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- sqlite_path: SQLITE_PATH（デフォルト: data/monitoring.db）
- pid_file_path: PID_FILE_PATH（デフォルト: data/execution.pid）
- cpu_threshold_pct, memory_threshold_pct, disk_threshold_pct（監視用閾値、デフォルトあり）
- KABUSYS_ENV（development / paper_trading / live、デフォルト development）
- LOG_LEVEL（DEBUG/INFO/...、デフォルト INFO）

環境変数の自動読み込み:
- プロジェクトルートはパッケージのファイル位置を基に ".git" または "pyproject.toml" を探索して決定します。
- .env と .env.local が存在する場合、自動で環境変数に読み込まれます。
- テスト時などで自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 配下の主要モジュールを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py             — ニュース NLP / score_news
    - regime_detector.py      — 市場レジーム判定 / score_regime
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント + DuckDB 保存関数
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - etl.py                  — ETLResult のエクスポート
    - news_collector.py       — RSS 収集・前処理
    - quality.py              — データ品質チェック
    - calendar_management.py  — 市場カレンダー管理（is_trading_day 等）
    - stats.py                — zscore_normalize 等の統計ユーティリティ
    - audit.py                — 監査ログテーブル定義・初期化
  - research/
    - __init__.py
    - factor_research.py      — ファクター計算（momentum, value, volatility）
    - feature_exploration.py  — 将来リターン, IC, 統計サマリー
  - ai/、research/ などの他モジュール群...

---

## テスト・開発時の注意点

- OpenAI API 呼び出しや外部 API 呼び出しはテスト中にモック可能なように実装されています（内部 _call_openai_api などをパッチする設計）。
- DuckDB を利用するためローカルファイルに永続化してテストすることができます（":memory:" でインメモリ DB にも接続可）。
- .env の自動読込は開発で便利ですが、CI やテストでは KABUSYS_DISABLE_AUTO_ENV_LOAD を使って明示的な環境制御を行うことを推奨します。

---

## 参考・追加情報

- コード内に詳しい docstring と設計方針・フェイルセーフの説明があります。特に ETL、ニュース NLP、jquants_client、audit の各モジュールには注意点が明記されています。
- 実運用で発注（kabu API）や Slack 通知を行う場合、権限や鍵・パスワードの管理、API レート制限、コスト（OpenAI 呼び出し）に注意してください。

---

もし README にサンプル .env.example、requirements.txt、あるいは CLI / systemd ユニット例を追加したい場合は、必要な情報（使用する外部サービス、望む実行方法）を教えてください。それに合わせた具体的な例を作成します。