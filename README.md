# KabuSys

日本株向けの自動売買／データパイプライン基盤ライブラリです。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュースNLP（OpenAI）、市場レジーム判定、研究用ファクター計算、監査ログなどの機能を提供します。

---

## 主要機能（概要）

- データ収集 / ETL
  - J-Quants API からの株価（日足）、財務データ、JPXカレンダーの取得（ページネーション対応、レート制御、トークン自動リフレッシュ）
  - DuckDB へ冪等保存（ON CONFLICT DO UPDATE）
  - 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- データ品質チェック
  - 欠損値、スパイク（前日比閾値）、重複、日付整合性チェック
- ニュース収集 / 前処理
  - RSS フィード取得（SSRF 対策、トラッキングパラメータ除去、前処理）と raw_news への保存
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュースを LLM で評価し ai_scores に保存（バッチ／JSON Mode、リトライ）
- 市場レジーム判定
  - ETF 1321 の MA200 乖離とマクロニュースセンチメントを合成して日次レジーム判定
- 研究用ユーティリティ
  - モメンタム／ボラティリティ／バリューの計算
  - 将来リターン、IC（Spearman）やファクター統計の算出
- 監査ログ（トレーサビリティ）
  - シグナル → 発注要求 → 約定 を追跡する監査テーブルの初期化ユーティリティ（DuckDB）

---

## 要件

- Python 3.10+
- 必要な Python パッケージ（代表例）:
  - duckdb
  - openai
  - defusedxml

（プロジェクト配布時に requirements.txt や pyproject.toml で明記することを推奨します）

---

## インストール

開発環境で使う例:

1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install duckdb openai defusedxml

3. ローカルパッケージとしてインストール（任意）
   - pip install -e .

---

## 設定（環境変数 / .env）

パッケージはプロジェクトルート（.git または pyproject.toml を探索）にある `.env` / `.env.local` を自動で読み込みます。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

重要な環境変数（主なもの）:

- JQUANTS_REFRESH_TOKEN (必須)  
  J-Quants のリフレッシュトークン（ETL / jquants_client で使用）
- OPENAI_API_KEY (必須 for AI機能)  
  OpenAI API キー（news_nlp / regime_detector で使用）
- KABU_API_PASSWORD  
  kabuステーション等の発注APIパスワード
- KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID (任意)  
  LINE 通知用
- DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb)  
  DuckDB ファイルパス
- SQLITE_PATH (任意, デフォルト: data/monitoring.db)
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START  
  実行監視関連
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT  
  監視閾値
- KABUSYS_ENV (development | paper_trading | live, デフォルト development)
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL, デフォルト INFO)

例 `.env`:

```
JQUANTS_REFRESH_TOKEN=xxxx...
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=secret
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

.env のパースはシェル風（export を許容、クォートやコメント処理あり）です。

---

## 使い方（主要な API / 実行例）

以下は Python スクリプトから利用する想定の簡単な例です。

1) DuckDB 接続の作成

```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

2) 日次 ETL を実行（差分取得・保存・品質チェック）

```python
from kabusys.data.pipeline import run_daily_etl

# target_date を省略すると今日が対象（バックテストでは明示すること）
result = run_daily_etl(conn, target_date=None, id_token=None)
print(result.to_dict())
```

3) ニューススコアリング（OpenAI を用いた銘柄別センチメント）

```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OpenAI API キーは環境変数 OPENAI_API_KEY または api_key 引数で指定
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {written}")
```

4) 市場レジーム判定（MA200 + マクロセンチメント）

```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

5) 監査ログ DB 初期化

```python
from kabusys.data.audit import init_audit_db
from pathlib import Path

audit_conn = init_audit_db(Path("data/audit.duckdb"))
# テーブルが作成され、UTC タイムゾーン設定が適用されます
```

6) 研究用ファクター計算例

```python
from kabusys.research.factor_research import calc_momentum
from datetime import date

mom = calc_momentum(conn, date(2026, 3, 20))
# レコードリストとして返るので研究用に利用可能
```

---

## 自動読み込みの挙動について

- 起動時にプロジェクトルートを探索し、`.env` → `.env.local` の順で読み込みます（OS環境変数が優先）。
- テストや特別な実行で自動ロードを無効にしたい場合:
  - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成（主要ファイル）

（ソースは `src/kabusys` 配下に配置されています）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数 / 設定管理（自動 .env ロード）
  - ai/
    - __init__.py
    - news_nlp.py          - ニュースの LLM スコアリング（ai_scores 書き込み）
    - regime_detector.py   - 市場レジーム判定（1321 MA200 + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py    - J-Quants API クライアント（取得・保存関数）
    - pipeline.py          - ETL パイプライン（run_daily_etl など）
    - etl.py               - ETLResult の再エクスポート
    - news_collector.py    - RSS 収集・前処理
    - quality.py           - データ品質チェック群
    - stats.py             - 汎用統計ユーティリティ（zscore_normalize）
    - calendar_management.py - 市場カレンダー管理（営業日判定など）
    - audit.py             - 監査ログテーブル定義・初期化
  - research/
    - __init__.py
    - factor_research.py   - Momentum / Value / Volatility 等のファクター
    - feature_exploration.py - 将来リターン、IC、統計サマリー 等
  - ai, data, research 以下はそれぞれの API をエクスポートしています（__all__ 指定あり）

---

## 注意事項 / ベストプラクティス

- Look-ahead bias 回避のため、モジュール内の各関数は date 引数で対象日を明示する設計です。バックテスト等では必ず過去日時を明示してください。
- OpenAI や J-Quants の API 呼び出しはリトライやフェイルセーフを組み込んでいますが、APIキーやレート制限の管理は運用側で行ってください。
- DuckDB への批量挿入は executemany を多用します。DuckDB のバージョン依存の挙動に注意してください（空リストの executemany を避ける等の配慮あり）。
- ニュース収集は外部 HTTP を行うため、SSRF・XML攻撃対策（defusedxml 等）を導入していますが、追加の運用上の安全対策（プロキシ、タイムアウト、監査）は推奨します。
- 監査ログは削除しない前提（FK ON DELETE RESTRICT）。運用でのデータ保持・アーカイブ戦略を検討してください。

---

## 貢献・テスト

- ユニットテストは各 API の副作用（外部 API 呼び出し）をモックする設計が容易です（内部で _call_openai_api や HTTP opener を差し替え可能）。
- .env 自動ロードの無効化や関数の `api_key` / `id_token` 引数注入によりテストがしやすくなっています。

---

README の内容はこのコードベースの現状に基づく概要と使用例です。必要に応じて、実行スクリプト、CI 設定、requirements.txt / pyproject.toml、サンプル DB 初期化スクリプト等を追記してください。