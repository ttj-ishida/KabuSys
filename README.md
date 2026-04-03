# KabuSys

KabuSys は日本株向けの自動売買・データプラットフォームを目的とした Python ライブラリ群です。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集と AI によるニュース/レジーム評価、リサーチ（ファクター計算・IC など）、監査ログ（発注/約定トレーサビリティ）等のモジュールを含みます。

---

## 主な機能

- データ取得・ETL
  - J-Quants API からの日次株価（OHLCV）、財務データ、JPX カレンダーの差分取得・保存（DuckDB）
  - 差分更新・バックフィル・品質チェック（欠損・スパイク・重複・日付整合性）
- ニュース収集
  - RSS フィード取得、前処理、raw_news への冪等保存、銘柄紐付け
  - SSRF/トラッキングパラメータ削除等のセキュアな実装
- AI（LLM）評価
  - ニュースに基づく銘柄別センチメント算出（gpt-4o-mini を想定）
  - マクロニュース + ETF (1321) の MA200 乖離を組み合わせた市場レジーム判定（bull/neutral/bear）
  - API 呼び出しはリトライ・フォールバック実装（API障害時は中立スコア等）
- リサーチ / ファクター
  - モメンタム、ボラティリティ、バリュー等の定量ファクター計算
  - 将来リターン計算、IC（Spearman）計算、Z スコア正規化、統計サマリ
- 監査ログ（Audit）
  - signal → order_request → execution の階層的トレーサビリティ（DuckDB）
  - 冪等性・ステータス管理・UTC タイムスタンプ管理

---

## セットアップ手順（開発向け）

1. レポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. Python 仮想環境作成（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージのインストール（最低限）
   ```
   pip install duckdb openai defusedxml
   ```
   ※ プロジェクトで追加の依存があれば requirements.txt を用意している想定です:
   ```
   pip install -r requirements.txt
   ```

4. パッケージを編集可能モードでインストール（任意）
   ```
   pip install -e .
   ```

---

## 環境変数 / 設定

自動でプロジェクトルート（.git または pyproject.toml を起点）にある `.env` と `.env.local` を読み込みます。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な環境変数（code 内で参照・デフォルト値）:

- J-Quants / API
  - JQUANTS_REFRESH_TOKEN — 必須（J-Quants リフレッシュトークン）
- OpenAI
  - OPENAI_API_KEY — LLM 呼び出しで使用（score_news / score_regime）
- kabuステーション（発注 API）
  - KABU_API_PASSWORD — 必須（API パスワード）
  - KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
- LINE 通知（任意）
  - LINE_CHANNEL_ACCESS_TOKEN
  - LINE_USER_ID
- データベース / パス
  - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
  - SQLITE_PATH — デフォルト: data/monitoring.db
- 監視 / PID
  - PID_FILE_PATH — デフォルト: data/execution.pid
  - KILL_FLAG_PATH — デフォルト: data/kill.flag
  - KILL_FLAG_CLEAR_ON_START — "1" で起動時にクリア
- システム
  - KABUSYS_ENV — 有効値: development / paper_trading / live（デフォルト: development）
  - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

例: `.env`（最小）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（主要ユースケースと例）

以下は代表的な呼び出し例です。各関数は DuckDB の接続オブジェクト（duckdb.connect() が返す接続）を受け取ります。

- DuckDB 接続の作成
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行（市場カレンダー -> 株価 -> 財務 -> 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

# target_date を指定するか省略して今日を使う
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントを算出して ai_scores テーブルへ書き込む
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# OPENAI_API_KEY が環境変数に設定されていれば api_key 引数は不要
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込んだ銘柄数:", n_written)
```

- 市場レジーム（bull/neutral/bear）を評価して market_regime テーブルへ保存
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ（audit）用 DB の初期化
```python
from kabusys.data.audit import init_audit_db
from pathlib import Path

audit_conn = init_audit_db(Path("data/audit.duckdb"))
# audit_conn を使って signal_events / order_requests / executions を利用できます
```

- ファクター計算やリサーチ関数
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

mom = calc_momentum(conn, target_date=date(2026,3,20))
vol = calc_volatility(conn, target_date=date(2026,3,20))
val = calc_value(conn, target_date=date(2026,3,20))
```

注意点:
- score_news / score_regime は OpenAI API キー（引数 or 環境変数 OPENAI_API_KEY）を必要とします。API 呼び出しの失敗はフォールバック/スキップする設計ですが、キー未設定時は ValueError を送出します。
- 各種 ETL / 保存関数は DuckDB テーブル構造（raw_prices, raw_financials, market_calendar 等）を前提とします。初期スキーマは別途用意してください（プロジェクトに schema 初期化ユーティリティがある想定）。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数/設定管理（.env 自動読み込み、settings オブジェクト）
  - ai/
    - __init__.py
    - news_nlp.py — ニュース NLP（LLM）スコアリング、score_news
    - regime_detector.py — 市場レジーム判定、score_regime
  - data/
    - __init__.py
    - calendar_management.py — JPX カレンダー管理・判定ユーティリティ
    - etl.py — ETL 公開インターフェース（ETLResult の re-export）
    - pipeline.py — 日次 ETL パイプライン（run_daily_etl 等）
    - stats.py — 汎用統計ユーティリティ（zscore_normalize）
    - quality.py — データ品質チェック（欠損/スパイク/重複/日付不整合）
    - audit.py — 監査ログスキーマ定義と初期化
    - jquants_client.py — J-Quants API クライアント（取得・保存関数）
    - news_collector.py — RSS ニュース収集・前処理・保存
  - research/
    - __init__.py
    - factor_research.py — モメンタム/ボラ/バリュー ファクター計算
    - feature_exploration.py — 将来リターン、IC、統計サマリ等
  - ai、data、research のほかに strategy / execution / monitoring パッケージが想定されます（__all__ に定義あり）

---

## 運用上の注意

- Look-ahead バイアス対策：モジュール設計上、target_date を明示的に渡すことが推奨され、datetime.today() 等を直接参照しない実装方針です。バックテストでは過去データのみ参照されるように注意してください。
- LLM 呼び出し：API レートやエラーハンドリング（リトライ・フォールバック）が実装されていますが、コスト管理・レート制御は運用側でも留意してください。
- .env 自動読み込み：プロジェクトルート（.git または pyproject.toml）を基準に `.env` / `.env.local` を読み込みます。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を使って無効化可能です。
- DuckDB スキーマ：ETL や保存関数は特定のテーブル・列を前提とします。初回はスキーマ作成スクリプト（別途用意）を実行してください。監査ログ用 init_audit_db がスキーマ初期化を提供します。

---

## さらに詳しく / 開発

各モジュール内の docstring に設計方針、処理フロー、エッジケースやフォールバック動作が詳細に記述されています。実装やテスト時は docstring を参照してください。

不明点・追加したい使用例があれば教えてください。README の補足（例: schema 初期化 SQL、docker-compose、CI 設定など）も作成できます。