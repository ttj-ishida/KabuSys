# KabuSys

日本株向けのデータ基盤・研究・AI支援・監査ログを備えた自動売買システムのライブラリ群です。  
このリポジトリは ETL（J-Quants 経由の株価／財務／カレンダー取得）、ニュース収集・NLP スコアリング、レジーム判定、ファクター計算、データ品質チェック、監査ログ（order → execution トレース）などを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買やリサーチのための共通ライブラリセットです。主に以下の役割を持ちます。

- Data (ETL) — J-Quants API から株価・財務・カレンダー等を差分取得し DuckDB に保存 / 品質チェック
- News Collector — RSS フィードを収集し前処理して raw_news に保存、銘柄紐付け
- AI (ニュース NLP / レジーム判定) — OpenAI（gpt-4o-mini）を使ったニュースセンチメント評価、ETF + マクロを組み合わせた市場レジーム判定
- Research — ファクター計算（モメンタム/ボラティリティ/バリュー等）、特徴量解析（将来リターン、IC、サマリー）
- Audit — シグナルから約定まで追跡可能な監査ログスキーマと初期化ユーティリティ
- Utilities — 日付 / カレンダー判定、統計ユーティリティ、環境設定管理 等

設計上の重点：
- ルックアヘッドバイアスを避ける（日時を直接参照しない処理設計）
- 冪等性（ON CONFLICT や固有 ID を利用）
- フェイルセーフ（API 失敗は局所的に処理継続）
- DuckDB を中心に軽量かつ SQL ベースで処理

---

## 主な機能一覧

- ETL（kabusys.data.pipeline）
  - run_daily_etl: 市場カレンダー・株価・財務の差分取得と品質チェックを実行
  - 個別 ETL: run_prices_etl / run_financials_etl / run_calendar_etl
  - ETL 結果を ETLResult データクラスで返却

- J-Quants クライアント（kabusys.data.jquants_client）
  - fetch / save 関数群（daily_quotes, financial_statements, market_calendar, listed_info）
  - レート制御、リトライ、トークン自動リフレッシュ、ページネーション対応

- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、URL 正規化、トラッキング除去、SSRF 対策、記事ID生成、前処理、raw_news への冪等保存

- ニュース NLP / レジーム判定（kabusys.ai）
  - score_news: 銘柄ごとのニュースセンチメントを OpenAI により算出して ai_scores に保存
  - score_regime: ETF (1321) の MA とマクロニュースの LLM センチメントを合成して市場レジームを判定

- ファクター / 研究（kabusys.research）
  - calc_momentum, calc_volatility, calc_value
  - calc_forward_returns, calc_ic, factor_summary, rank
  - zscore_normalize（kabusys.data.stats）

- カレンダ管理（kabusys.data.calendar_management）
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
  - calendar_update_job: J-Quants からの差分更新ジョブ

- 品質チェック（kabusys.data.quality）
  - 欠損・スパイク・重複・日付不整合チェック
  - run_all_checks で一括実行し QualityIssue を返す

- 監査ログ（kabusys.data.audit）
  - 監査テーブルのDDL と初期化（init_audit_schema / init_audit_db）

---

## セットアップ手順

※ 以下は一般的手順です。プロジェクトの配布パッケージに requirements.txt / pyproject.toml がある前提で適宜変更してください。

1. Python 環境を用意（推奨: 3.10+）
2. 必要パッケージをインストール（例）:
   - duckdb
   - openai
   - defusedxml
   - （その他 requests 等が必要な場合あり）
   
   例:
   ```
   pip install duckdb openai defusedxml
   ```

3. パッケージをインストール / 開発環境に登録:
   ```
   pip install -e .
   ```
   （プロジェクトがセットアップ可能な場合）

4. 環境変数を設定
   - ルートに `.env` を置くと自動読み込み（.git か pyproject.toml が存在するプロジェクトルートに依存）
   - 自動読み込みを無効にする場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

必須（またはよく使われる）環境変数:
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API 用パスワード（必須）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID — Slack チャンネル ID（必須）
- OPENAI_API_KEY — OpenAI 呼び出しに使用（score_news / score_regime で必要）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 ("development" / "paper_trading" / "live")（デフォルト: development）
- LOG_LEVEL — ログレベル ("DEBUG"/"INFO"/...)（デフォルト: INFO）

例 .env:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
```

---

## 使い方（主要な関数・実行例）

以下は Python REPL / スクリプト内での利用例です。

- DuckDB に接続して日次 ETL を実行する例:
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- news NLP（OpenAI）でスコアを計算する例:
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を利用
print("written:", n_written)
```

- レジーム判定の実行例:
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ DB の初期化:
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
```

- カレンダー操作例:
```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import is_trading_day, next_trading_day

conn = duckdb.connect(str(settings.duckdb_path))
print(is_trading_day(conn, date(2026, 1, 1)))
print(next_trading_day(conn, date(2026, 1, 1)))
```

注意点:
- AI 機能を使う場合、OpenAI API キー（OPENAI_API_KEY）が必要です。トークンが未設定だと ValueError が投げられます。
- J-Quants API を利用するための JQUANTS_REFRESH_TOKEN が必須です。
- ETL / save_* 関数は冪等設計ですが、初期スキーマ（raw_prices 等）が存在することを前提とします（スキーマ初期化は別途行ってください）。

---

## ディレクトリ構成（主なファイル説明）

- src/kabusys/
  - __init__.py — パッケージ定義
  - config.py — 環境変数 / .env 自動読み込み / Settings
  - ai/
    - __init__.py
    - news_nlp.py — ニュースセンチメント（OpenAI） → ai_scores へ書込
    - regime_detector.py — ETF MA とマクロセンチメント合成による市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（fetch / save / auth / rate limit）
    - pipeline.py — 日次 ETL パイプライン & 個別 ETL ジョブ
    - etl.py — ETLResult の再エクスポート
    - news_collector.py — RSS 取得・正規化・保存
    - calendar_management.py — market_calendar 管理、営業日判定、calendar_update_job
    - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py — zscore_normalize 等の統計ユーティリティ
    - audit.py — 監査ログスキーマ定義・初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py — モメンタム/ボラティリティ/バリューの計算
    - feature_exploration.py — 将来リターン計算、IC、統計サマリー、ランク変換
  - research/（その他）...
- pyproject.toml / setup.cfg / requirements.txt（存在する場合、インストール情報）

---

## 設計上の注意・ベストプラクティス

- ルックアヘッドバイアス防止:
  - 多くの処理は target_date を引数に取り、datetime.today()/date.today() を直接参照しない設計です。バックテストや再現性を保つため、必ず target_date を明示して呼び出すことを推奨します。
- 冪等性:
  - ETL の保存処理は ON CONFLICT（または主キー）による上書きを行うため、同じデータを複数回取り込んでも安全です。
- フェイルセーフ:
  - 外部 API の失敗（OpenAI / J-Quants 等）は局所的に処理継続する設計（多くは警告ログとスキップ）になっています。運用ではログ・アラートを監視してください。
- セキュリティ:
  - news_collector は SSRF 対策・トラッキングパラメータ除去・gzip サイズ制限等の防御を実装していますが、運用上のネットワークポリシーと合わせて運用してください。
- リソース:
  - J-Quants のレート制限（120 req/min）や OpenAI の料金を考慮した呼び出し計画を立ててください。

---

## 貢献・ライセンス

本 README はコードベースの説明用に自動生成しました。実際の運用や拡張を行う際は、テストカバレッジの追加、例外ハンドリングやメトリクスの強化、CI パイプライン整備を行ってください。ライセンス情報はリポジトリルートの LICENSE ファイルを参照してください（存在する場合）。

---

必要であれば、README に以下の追加情報も作成します:
- requirements.txt / pyproject.toml の想定依存リスト
- データベーススキーマ（テーブル定義サンプル）
- よくあるトラブルシューティング（OpenAI の JSON Mode エラー、J-Quants トークンエラー 等）
- 実運用のデプロイ手順（Dockerfile / systemd / Airflow など）

どれを追加しますか？