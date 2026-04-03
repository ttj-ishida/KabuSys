# KabuSys

日本株自動売買プラットフォーム向けのライブラリ群。市場データの ETL、ニュース収集・NLP（OpenAI を利用したセンチメント評価）、リサーチ用ファクター計算、監査ログ（発注 → 約定のトレーサビリティ）など、自動売買システム構築に必要な基盤機能を提供します。

主な設計方針：
- ルックアヘッドバイアスを防ぐ（内部で datetime.today()/date.today() を直接参照しない等）
- DuckDB をデータストアに利用し、SQL と Python の組み合わせで処理
- 外部 API 呼び出しはリトライ・レート制御・フェイルセーフを組み込み
- 冪等性（DB 保存は ON CONFLICT / idempotent）を重視

バージョン: 0.1.0

---

## 機能一覧

- データ ETL（J-Quants からの株価・財務データ・市場カレンダー取得）
  - 差分取得、バックフィル、品質チェック、ETL 結果集約（ETLResult）
- ニュース収集・前処理（RSS → raw_news）
  - URL 正規化、SSRF 対策、XML パースの安全化（defusedxml）
- ニュース NLP（OpenAI を用いた銘柄ごとのセンチメント）
  - バッチ API 呼び出し、レスポンス検証、スコアを ai_scores に保存（score_news）
- 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロニュース）
  - LLM によるマクロセンチメント評価を合成して market_regime に保存（score_regime）
- 研究（research）モジュール
  - Momentum / Value / Volatility 等のファクター計算（calc_momentum / calc_value / calc_volatility）
  - 将来リターン計算、IC、ファクター統計サマリ、Zスコア正規化
- マーケットカレンダー管理（is_trading_day, next_trading_day, prev_trading_day, calendar_update_job）
- 監査ログ（audit）: signal_events / order_requests / executions テーブル、スキーマ初期化ユーティリティ
- J-Quants API クライアント（認証・ページネーション・レートリミット・保存ユーティリティ）
- 設定管理（環境変数の自動読み込み・Settings オブジェクト）

---

## 要件（推奨）

- Python 3.10 以上（型ヒントの union 記法やその他構文のため）
- 必要パッケージ（例）
  - duckdb
  - openai
  - defusedxml
  - (その他標準ライブラリ以外があれば requirements.txt を参照)

---

## セットアップ手順

1. リポジトリをクローンして仮想環境を作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate    # macOS / Linux
   .venv\Scripts\activate       # Windows
   ```

2. 依存パッケージをインストール
   - プロジェクトに requirements.txt があればそれを使うか、主要パッケージを個別に入れてください。
   ```
   pip install duckdb openai defusedxml
   # または
   pip install -r requirements.txt
   ```

3. パッケージを開発モードでインストール（任意）
   ```
   pip install -e .
   ```

4. 環境変数（.env）を用意
   - プロジェクトルート（pyproject.toml または .git があるディレクトリ）に `.env` / `.env.local` を置くと、自動で読み込まれます（デフォルトで有効）。
   - 自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須（実運用で必要なもの）
- JQUANTS_REFRESH_TOKEN：J-Quants のリフレッシュトークン（ETL で使用）
- KABU_API_PASSWORD：kabu ステーション API のパスワード（注文系）
- OPENAI_API_KEY：OpenAI API キー（news_nlp / regime_detector）

任意・設定例
- KABUSYS_ENV：development / paper_trading / live（デフォルト development）
- LOG_LEVEL：DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
- DUCKDB_PATH：DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH：監視用 SQLite（デフォルト data/monitoring.db）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（通知用）

例 .env（プロジェクトルート）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（基本例）

以下はライブラリを直接呼び出す Python コード例です。DuckDB 接続は duckdb.connect(...) で取得します。

- 日次 ETL を実行する（run_daily_etl）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP スコア計算（score_news）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026,3,20), api_key=None)  # env の OPENAI_API_KEY を使用
print(f"wrote scores for {n_written} codes")
```

- 市場レジーム判定（score_regime）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026,3,20))
```

- 監査スキーマ初期化（監査ログ用 DB）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# テーブルが作成され、UTC タイムゾーンが設定されます
```

- market_calendar 周りの呼び出し例
```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import is_trading_day, next_trading_day

conn = duckdb.connect(str(settings.duckdb_path))
is_td = is_trading_day(conn, date(2026,3,20))
next_td = next_trading_day(conn, date(2026,3,20))
```

ログレベルや環境は環境変数 `LOG_LEVEL` / `KABUSYS_ENV` で制御できます。

---

## 注意点・運用上のヒント

- OpenAI / J-Quants の API 呼び出しはそれぞれレート制御・リトライを内包していますが、APIキーの管理やコスト制御は運用側で厳密に行ってください。
- DuckDB の executemany に関する注意（本コードは DuckDB 0.10 系の挙動を考慮した実装になっています）。
- .env の自動読み込みはプロジェクトルート検出に基づいて行われ、CWD に依存しない実装です。テスト等で自動読み込みを止めたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- ニュース収集モジュールは SSRF 対策、受信バイト制限、XML の安全パース等を組み込んでいます。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 配下の主要モジュールを抜粋）

- kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py            — ニュースの NLP スコアリング（score_news）
    - regime_detector.py     — マーケットレジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（fetch / save 系）
    - pipeline.py            — ETL パイプライン（run_daily_etl 他）、ETLResult
    - etl.py                 — ETLResult 再エクスポート
    - news_collector.py      — RSS ニュース収集・前処理
    - calendar_management.py — マーケットカレンダー管理（is_trading_day 等）
    - quality.py             — データ品質チェック（欠損・スパイク・重複・日付整合）
    - stats.py               — 汎用統計ユーティリティ（zscore_normalize）
    - audit.py               — 監査ログスキーマ初期化（signal_events / order_requests / executions）
  - research/
    - __init__.py
    - factor_research.py     — Momentum/Value/Volatility 等のファクター計算
    - feature_exploration.py — 将来リターン、IC、統計サマリ、rank 等
  - ai/ (上記)
  - research/ (上記)
  - その他: strategy, execution, monitoring 等のパッケージが __all__ として想定されています

---

## 貢献・拡張

- 新しいニュースソース追加、分析モデル変更、発注ブローカーの追加などはモジュール単位で拡張可能です。
- テスト時は各種外部呼び出し（OpenAI / J-Quants / ネットワーク）をモックすることを推奨します（コード内にもテスト用フックや monkeypatch ポイントが用意されています）。

---

必要なら README にサンプル .env.example、requirements.txt の具体的な内容や、代表的なユースケース（ETL スケジュール化、監視ジョブ、戦略実行フロー）を追加できます。追加希望があれば教えてください。