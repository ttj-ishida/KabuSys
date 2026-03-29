# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。ETL、ニュース収集・NLP、ファクター計算、研究用ユーティリティ、監査ログ（トレーサビリティ）、および市場レジーム判定などを含むモジュール群を提供します。

---

## 概要

KabuSys は以下の目的を持つ Python パッケージです。

- J-Quants API からの株価・財務・市場カレンダー取得と DuckDB への差分保存（ETL）
- RSS ベースのニュース収集と前処理（SSRF 対策、トラッキング除去）
- OpenAI（gpt-4o-mini）を利用したニュースセンチメント評価（銘柄別 / マクロ）
- ファクター計算（モメンタム、バリュー、ボラティリティ等）および研究用解析（IC, forward returns 等）
- 監査ログ（signal → order_request → execution のトレーサビリティ）用スキーマ初期化
- 市場カレンダー管理（営業日判定、next/prev trading day 等）
- データ品質チェック（欠損・スパイク・重複・日付不整合）

設計上、バックテストでのルックアヘッドバイアスを避ける実装方針や、API リトライ／フェイルセーフの考慮、DuckDB を中心にした冪等保存などを重視しています。

---

## 主な機能一覧

- data (ETL / news collector / jquants client / calendar / quality / audit)
  - 日次 ETL パイプライン（run_daily_etl）
  - J-Quants API クライアント（fetch / save / token refresh / rate limit）
  - JPX マーケットカレンダー管理と夜間更新ジョブ
  - ニュース収集・前処理（RSS, URL 正規化, SSRF 対策）
  - データ品質チェック（欠損・重複・スパイク・日付不整合）
  - 監査ログ（signal_events / order_requests / executions）スキーマ初期化
- ai (news_nlp / regime_detector)
  - 銘柄別ニュースセンチメントスコアの計算（score_news）
  - マクロ指標と LLM を組み合わせた市場レジーム判定（score_regime）
- research
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量探索・IC・将来リターン計算等（calc_forward_returns, calc_ic, factor_summary）
- util
  - 統計ユーティリティ（zscore_normalize）

---

## セットアップ手順

1. Python 仮想環境を作成・有効化（推奨: Python 3.9+）

   - Unix/macOS:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

2. パッケージのインストール（プロジェクトルートに pyproject.toml がある想定）

   ```
   pip install -e .
   ```

   依存例（プロジェクト側で要求される代表的パッケージ）:
   - duckdb
   - openai
   - defusedxml

   必要に応じてこれらを事前にインストールしてください。

3. 環境変数を設定するか、プロジェクトルートに `.env` / `.env.local` を置く

   自動ロード挙動:
   - パッケージは起動時にプロジェクトルート（.git または pyproject.toml を探索）を見つけると `.env` → `.env.local` の順で読み込みます。
   - 自動読み込みを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途など）。

4. 必須環境変数（例）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabu ステーション API パスワード（発注関連を使う場合）
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必要時）
   - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID
   - OPENAI_API_KEY: OpenAI 呼び出しで使用する API キー（score_news / score_regime 等）

   オプション/その他:
   - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 sqlite パス（デフォルト data/monitoring.db）
   - KABU_API_BASE_URL: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）

---

## 使い方（簡単なコード例）

以下の例は各主要機能の呼び出し方です。実行時は事前に環境変数や DB パスを設定してください。

- DuckDB 接続作成

```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL 実行

```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント（銘柄別）取得

```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# OPENAI_API_KEY が環境変数に設定されていれば api_key は省略可
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"written: {n_written}")
```

- 市場レジーム判定

```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ DB 初期化（監査専用 DB を作成する場合）

```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

audit_conn = init_audit_db(settings.duckdb_path)  # ":memory:" も可
```

- J-Quants からリスト情報を取得（ユーティリティ）

```python
from kabusys.data.jquants_client import fetch_listed_info, get_id_token

id_token = get_id_token()  # settings.jquants_refresh_token を参照
listed = fetch_listed_info(id_token=id_token)
```

- 設定の参照

```python
from kabusys.config import settings
print(settings.env, settings.duckdb_path, settings.is_live)
```

注意点:
- score_news / score_regime は OpenAI を呼び出すため API キーが必要です。テスト時は各モジュール内の _call_openai_api をモックしてください。
- ETL は J-Quants API のレート制限と認証を扱います。settings.jquants_refresh_token を正しくセットしてください。

---

## ディレクトリ構成（主要ファイル）

パッケージは src/kabusys 以下に配置されています。代表的なファイル・ディレクトリ構成は次のとおりです。

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - jquants_client.py
    - pipeline.py
    - etl.py
    - calendar_management.py
    - news_collector.py
    - stats.py
    - quality.py
    - audit.py
    - pipeline.py
    - etl.py
    - ...（他ユーティリティモジュール）
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - monitoring/ (モニタリング系は __all__ に含まれますが実装は個別)
  - execution/（発注関連・broker インターフェース想定）
  - strategy/（戦略モジュール想定）
  - data/（上記と同階層でデータ関連多数）

（注）上記はプロジェクトの主要モジュールを示した抜粋です。詳細はソースツリーを参照してください。

---

## 運用上の注意・設計方針（抜粋）

- ルックアヘッドバイアス防止:
  - 各モジュールは datetime.today() や date.today() を内部で不用意に参照せず、呼び出し側で target_date を指定して処理する設計。
- 冪等性:
  - DuckDB への保存は ON CONFLICT DO UPDATE 等で冪等に行う（ETL の再実行が安全）。
- フェイルセーフ:
  - LLM/API の失敗時はゼロスコアやスキップで続行し、ETL 全体を止めない方針。
- セキュリティ:
  - RSS 収集での SSRF 対策、XML の安全パーシング（defusedxml）、レスポンスサイズ制限等を実装。

---

## トラブルシューティング

- 環境変数が足りない場合、Settings のプロパティが ValueError を投げます。エラーメッセージに従って .env を設定してください。
- OpenAI 呼び出しでレート制限やネットワーク障害が発生する場合、モジュール内で再試行を行いフェイルセーフとして 0.0 を返します。テスト時は API 呼び出し箇所をモックしてください（モジュール内の _call_openai_api を patch）。
- DuckDB の executemany に関する制約（空リストを渡せない等）に注意。モジュールは空チェックを実装していますが、独自コードで executemany を使う場合は注意してください。

---

## 貢献 / 開発メモ

- 自動環境変数ロードはプロジェクトルート検出に依存します。開発環境で意図的に無効化したいときは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI 呼び出しのインターフェースはテスト容易性のため差し替え可能になっています。ユニットテストは外部クライアント呼び出しをモックしてください。

---

必要なら README に含めるサンプル .env.example、CI 実行手順、より詳細な API 使用例（発注処理フロー等）を追加します。どの情報を優先的に補足しましょうか？