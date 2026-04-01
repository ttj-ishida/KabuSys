# KabuSys

KabuSys は日本株向けのデータプラットフォームと自動売買（リサーチ / シグナル / 発注監査）を想定したライブラリ群です。J-Quants API や RSS、OpenAI（LLM）などを利用してデータ収集・ETL・ニュースセンチメント評価・市場レジーム判定・ファクター計算・監査ログ等を提供します。

主な設計方針：
- ルックアヘッドバイアス回避（datetime.today()/date.today() を直接参照しない設計）
- DuckDB を用いたローカルデータストアと idempotent な保存（ON CONFLICT）
- 外部 API 呼び出しはリトライ・レート制御・フェイルセーフを実装
- LLM 呼び出しは JSON mode を利用し厳密なレスポンスを期待・検証

---

## 機能一覧

- 環境設定管理
  - .env / .env.local 自動読み込み（プロジェクトルート検出）
  - 必須環境変数のラップ提供（settings）
- データ取得・ETL（J-Quants）
  - 日次株価（OHLCV）取得・保存（fetch / save）
  - 財務データ取得・保存
  - JPX マーケットカレンダー取得・保存
  - 差分取得 / バックフィル / 品質チェック（quality）
- ニュース収集
  - RSS フィード取得・前処理・raw_news への冪等保存
  - SSRF / 大容量レスポンス対策、URL 正規化
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュースをまとめて LLM に投げてセンチメントを ai_scores に保存（score_news）
  - レスポンス検証・スコアクリップ・バッチ処理・リトライ
- 市場レジーム判定（regime_detector）
  - ETF 1321 の 200 日移動平均乖離（70%）とマクロニュースセンチメント（30%）を合成して日次レジーム判定
  - LLM 呼び出しはフェイルセーフ（失敗時は中立扱い）
- リサーチ / ファクター計算
  - Momentum / Volatility / Value 等のファクター計算（prices_daily, raw_financials ベース）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー、Z スコア正規化
- 監査ログ（Audit）
  - シグナル → 発注リクエスト → 約定をトレースする監査テーブル・初期化ユーティリティ（init_audit_db / init_audit_schema）
  - 全て UTC タイムスタンプ、冪等設計
- その他ユーティリティ
  - 市場カレンダー補助（is_trading_day / next_trading_day / get_trading_days 等）
  - DuckDB 接続を前提とした各種ユーティリティ

---

## 要件（推奨）

- Python 3.10+
- 主要依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワーク接続（J-Quants API、OpenAI、RSS 等）
- 環境変数設定（下記参照）

インストールはプロジェクトの pyproject.toml / requirements.txt に従ってください。開発時は editable install 推奨:
```
python -m pip install -e .
```

---

## 環境変数（主なもの）

以下はこのコードベースで参照される主要な環境変数です。実運用では .env/.env.local をプロジェクトルートに置いて管理します（config モジュールが自動読み込みします。無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。

必須（使用箇所によっては任意）:
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（jquants_client.get_id_token で使用）
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector などで使用）
- KABU_API_PASSWORD — kabuステーション API のパスワード（発注実装時）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（監視等）
- SLACK_CHANNEL_ID — Slack チャンネル ID

その他（デフォルトあり）:
- KABUSYS_ENV — "development" / "paper_trading" / "live"（デフォルト "development"）
- LOG_LEVEL — "DEBUG" / "INFO" / "WARNING" / "ERROR" / "CRITICAL"
- DUCKDB_PATH — DuckDB データベースパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト data/monitoring.db）
- PID_FILE_PATH — 実行監視用 PID ファイル（デフォルト data/execution.pid）

---

## セットアップ手順

1. ソースを取得
   - git clone してプロジェクトルートに移動

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - python -m pip install -r requirements.txt
   - または個別に: python -m pip install duckdb openai defusedxml

4. 開発インストール（任意）
   - python -m pip install -e .

5. 環境変数を設定
   - プロジェクトルートに .env を作成（.env.example を参照）
   - 例:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-...
     KABU_API_PASSWORD=...
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     ```

6. DuckDB 初期スキーマ（監査テーブル等）を作成する場合:
   - Python REPL やスクリプト内で init_audit_db を呼ぶ（使用例は下記）

---

## 使い方（簡易例）

以下は主要な API の呼び出し例です。全て Python コードで DuckDB 接続を渡して利用します。

1) DuckDB 接続準備
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

2) 日次 ETL を実行する（市場カレンダー・株価・財務・品質チェック）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

3) ニュースセンチメント（銘柄別）を生成
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # None で環境変数 OPENAI_API_KEY 使用
print(f"written {n_written} scores")
```

4) 市場レジーム判定（例: ETF 1321）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

5) 監査 DB 初期化（監査専用 DB を作る場合）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# または in-memory:
# audit_conn = init_audit_db(":memory:")
```

6) ファクター計算、リサーチユーティリティ
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from kabusys.data.stats import zscore_normalize

mom = calc_momentum(conn, target_date=date(2026, 3, 20))
vol = calc_volatility(conn, target_date=date(2026, 3, 20))
val = calc_value(conn, target_date=date(2026, 3, 20))
normed = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])
```

注意:
- OpenAI 呼び出しはネットワークと API キーを必要とします。テスト時は _call_openai_api をモックできます。
- ETL / API 関連はリトライ・レート制御が入っているため、大量の並列呼び出しに注意してください。

---

## ディレクトリ構成（抜粋）

プロジェクトは src 配下の kabusys パッケージで構成されています。代表的なファイルを示します。

- src/kabusys/
  - __init__.py
  - config.py                        — 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py                    — ニュースセンチメント（LLM）
    - regime_detector.py             — 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py              — J-Quants API クライアント + 保存ロジック
    - pipeline.py                    — ETL パイプライン（run_daily_etl 他）
    - etl.py                         — ETLResult 再エクスポート
    - news_collector.py              — RSS 収集・前処理
    - calendar_management.py         — 市場カレンダー管理
    - quality.py                     — データ品質チェック
    - stats.py                       — 統計ユーティリティ（zscore_normalize 等）
    - audit.py                       — 監査ログスキーマ初期化・ユーティリティ
  - research/
    - __init__.py
    - factor_research.py             — Momentum / Value / Volatility 等
    - feature_exploration.py         — 将来リターン / IC / summary
  - ai/__init__.py
  - research/__init__.py
  - data/etl.py

各モジュールはコメントで設計方針と入出力を明記しているので、用途に応じて関数を組み合わせて運用できます。

---

## 運用上の注意

- 自動環境変数読み込み:
  - config モジュールはプロジェクトルート（.git または pyproject.toml）を基準に .env, .env.local を読み込みます。
  - テスト等で無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- LLM 呼び出し:
  - レスポンスの検証を行いますが、出力フォーマットの逸脱があるとスキップして安全側（中立スコア）にフォールバックします。
- ETL の耐障害性:
  - 各ステップは例外ハンドリングされ、部分失敗しても他のステップを継続します。結果は ETLResult.errors / quality_issues に格納されます。
- データベース: DuckDB を使用（ファイル or :memory:）。監査ログは別 DB に分離することが推奨されます。

---

この README はコード内のドキュメント文字列（docstring）に基づき作成しています。詳細な API やスキーマの仕様は各モジュールの docstring を参照してください。追加のセットアップや運用手順（CI/CD、スケジューリング、監視）が必要な場合は別途ドキュメント化することを推奨します。