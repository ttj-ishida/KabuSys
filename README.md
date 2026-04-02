# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買プラットフォームの基盤ライブラリです。データ ETL、ニュース NLP によるセンチメント分析、マーケットレジーム判定、ファクター算出・研究ユーティリティ、監査ログ（トレーサビリティ）、および J-Quants / JPX と連携するクライアント機能を提供します。

主な設計方針：
- バックテストにおけるルックアヘッドバイアスを避けるため、内部で datetime.today()/date.today() を直接参照しない実装を心がけています。
- DuckDB を主要なデータストアとして想定し、ETL は冪等性（ON CONFLICT）と品質チェックを備えます。
- 外部 API（J-Quants / OpenAI など）呼び出しはリトライやレート制御・フェイルセーフを実装して安全性を高めています。

---

## 機能一覧

- data
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants API クライアント（認証・取得・保存・ページネーション・レート制御）
  - 市場カレンダー管理（営業日判定や next/prev_trading_day）
  - ニュース収集（RSS -> raw_news。SSRF 対策、トラッキングパラメータ除去、前処理）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログ：signal_events / order_requests / executions テーブルの初期化とユーティリティ
  - 統計ユーティリティ（Zスコア正規化など）

- ai
  - ニュース NLP スコアリング（gpt-4o-mini を用いた銘柄単位のセンチメント）
  - 市場レジーム判定（ETF 1321 の MA200 とマクロニュースセンチメントを合成）

- research
  - ファクター計算（Momentum / Value / Volatility / Liquidity）
  - 特徴量探索（将来リターン計算、IC、統計サマリー、ランク付け）

- config
  - 環境変数/設定の読み込み（プロジェクトルートの `.env` / `.env.local` を自動読み込み。無効化フラグあり）
  - settings オブジェクトから各種設定を取得

---

## 前提・要件

- Python 3.10+
- 推奨（プロダクションで使う場合）:
  - duckdb
  - openai
  - defusedxml

最小インストール例（開発環境）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# またはローカルパッケージを editable install
pip install -e .
```

（requirements.txt / pyproject.toml があればそちらを使ってください）

---

## 環境変数

主に以下の環境変数を使用します（必須はコード中で _require によりチェックされます）:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu ステーション API パスワード
- KABU_API_BASE_URL (任意) — kabu API のベース URL (デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- OPENAI_API_KEY (AI 関連を使う場合は必須)
- DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (任意, デフォルト: data/monitoring.db)
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- KABUSYS_ENV (development | paper_trading | live, デフォルト development)
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL, デフォルト INFO)

自動 .env 読み込み:
- プロジェクトルート（.git または pyproject.toml のあるディレクトリ）から `.env` と `.env.local` を自動で読み込みます。
- テスト等で自動読み込みを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

例（プロジェクトルートの .env）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（簡易）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. Python 仮想環境を作成して有効化
   ```
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

3. 必要パッケージをインストール
   ```
   pip install duckdb openai defusedxml
   # またはパッケージ化されている場合:
   pip install -e .
   ```

4. 環境変数準備
   - プロジェクトルートに `.env`（およびローカルの機密は `.env.local`）を作成する。
   - 上記の必須キーを設定する。

5. DuckDB の初期スキーマ（監査テーブル等）が必要な場合は初期化
   - 例: 監査 DB 初期化
   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   # conn は duckdb 接続オブジェクト
   ```

---

## 使い方（主な API 例）

※ すべての操作は duckdb 接続オブジェクト（duckdb.DuckDBPyConnection）を渡して行います。

- 設定参照
```python
from kabusys.config import settings
print(settings.duckdb_path)  # Path オブジェクト
```

- 日次 ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP スコアリング（指定日）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# conn は DuckDB 接続
n_written = score_news(conn, target_date=date(2026,3,20))  # OPENAI_API_KEY は env から取得
print(f"written scores: {n_written}")
```

- 市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026,3,20))
```

- ファクター計算（研究用）
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

momentum = calc_momentum(conn, date(2026,3,20))
value = calc_value(conn, date(2026,3,20))
vol = calc_volatility(conn, date(2026,3,20))
```

- 監査テーブル初期化（既存 DuckDB へ）
```python
from kabusys.data.audit import init_audit_schema
# conn は既存の duckdb 接続
init_audit_schema(conn, transactional=True)
```

- J-Quants API を直接使う（ID トークンの取得）
```python
from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes
token = get_id_token()  # settings.jquants_refresh_token を使う
records = fetch_daily_quotes(id_token=token, date_from=date(2026,3,1), date_to=date(2026,3,20))
```

---

## ディレクトリ構成

主なファイル / モジュール一覧（src/kabusys を起点）:

- src/kabusys/__init__.py
- src/kabusys/config.py
- src/kabusys/ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- src/kabusys/data/
  - __init__.py
  - calendar_management.py
  - pipeline.py
  - etl.py
  - jquants_client.py
  - news_collector.py
  - quality.py
  - stats.py
  - audit.py
  - pipeline.py (ETLResult を含む)
  - etl.py (ETL 公開インターフェース)
- src/kabusys/research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- src/kabusys/ai/__init__.py
- src/kabusys/research/__init__.py
- その他: 監視・戦略・execution などのパッケージスケルトン（__all__ で公開）を想定

（上記はコードベースの抜粋に基づく要約です。実際のリポジトリには追加ファイルやドキュメントがある可能性があります。）

---

## 注意点・トラブルシューティング

- 環境変数未設定時は Settings のプロパティで ValueError が発生します（必須項目を確認してください）。
- DuckDB のファイルパス（DUCKDB_PATH）の親ディレクトリは自動作成されますが、パーミッション等に注意してください。
- OpenAI 呼び出しはレートやエラーに対してリトライ・フェイルセーフが入っていますが、API キーの利用量・料金に注意してください。
- news_collector は RSS 取得で SSRF 対策や応答サイズチェックを行います。外部フィードの仕様によっては取得できない場合があります。
- テスト時に自動 .env ロードを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

貢献・拡張のポイント
- 新しいデータソースの追加は `kabusys.data.jquants_client` 相当のパターンで実装し、対応する save_* を用意してください。
- 新戦略・注文フロー実装時は監査ログ（signal_events / order_requests / executions）を適切に更新してトレーサビリティを保ってください。
- AI モジュールは API 呼び出しの差し替えが容易な設計（テスト時のモックを想定）になっています。

---

この README はコード内の docstring と実装に基づいて作成されています。詳細な設計文書（StrategyModel.md、DataPlatform.md 等）がある場合はそちらも参照してください。疑問点や改善要望があればお知らせください。