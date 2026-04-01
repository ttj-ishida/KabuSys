# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けのデータプラットフォームと自動売買（研究 → シグナル → 発注）基盤のプロトタイプです。J-Quants からのデータ取り込み、ニュース収集と LLM を用いたニュース・センチメント評価、ファクター計算・特徴量解析、監査ログ（発注→約定トレース）、および運用用のカレンダー管理や品質チェックを提供します。

主な設計方針は「ルックアヘッドバイアスの排除」「冪等性」「フェイルセーフ（APIエラー時は安全なデフォールトで継続）」です。

---

## 機能一覧

- データ取得 / ETL
  - J-Quants API クライアント（株価日足、財務データ、JPX カレンダー）
  - 差分取得・バックフィル・ページネーション対応
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE 相当）

- ニュース収集
  - RSS フィード取得（SSRF 対策、トラッキングパラメータ除去、gzip ハンドリング）
  - 記事の前処理・ID 正規化（SHA-256 ベース）

- ニュース NLP / LLM
  - 銘柄ごとのニュースセンチメント（gpt-4o-mini を想定）を ai_scores に書き込み
  - マクロニュースを用いた市場レジーム判定（ETF 1321 の MA200 乖離と LLM センチメントの合成）

- 研究（Research）
  - モメンタム / ボラティリティ / バリュー 等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）算出、統計サマリー
  - z-score 正規化ユーティリティ

- データ品質チェック
  - 欠損データ、スパイク（急騰・急落）、重複、日付不整合の検出
  - QualityIssue 型で問題の集約（警告/エラーの分類）

- カレンダー管理
  - market_calendar テーブルを基に営業日判定、前後営業日の取得、期間内営業日取得
  - J-Quants からのカレンダー差分更新ジョブ

- 監査ログ（Audit）
  - signal_events / order_requests / executions テーブル群の自動作成
  - 発注から約定までのトレース（冪等キー等）

- 運用・監視設定（環境変数ベースの設定読み込みと管理）

---

## 前提 / 必要パッケージ

- Python 3.10 以上（型ヒントで | 演算子を使用）
- 必要な外部ライブラリ（例）
  - duckdb
  - openai (OpenAI Python SDK)
  - defusedxml

実行環境によっては追加で標準ライブラリ以外のライブラリが必要になる場合があります。requirements.txt を用意しているプロジェクトであればそれを利用してください。

---

## セットアップ手順（開発用）

1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. 仮想環境の作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. パッケージのインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt があれば）pip install -r requirements.txt

4. 環境変数 / .env の準備
   - プロジェクトルートに `.env` / `.env.local` を置くと自動ロードされます（自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 最低限設定すべき環境変数（例）:
     - JQUANTS_REFRESH_TOKEN=...        # J-Quants リフレッシュトークン（必須: ETL）
     - OPENAI_API_KEY=...               # OpenAI API キー（必須: news_nlp / regime_detector）
     - KABU_API_PASSWORD=...            # kabuステーション API パスワード（発注系）
     - SLACK_BOT_TOKEN=...              # Slack 通知（運用監視）
     - SLACK_CHANNEL_ID=...
     - DUCKDB_PATH=data/kabusys.duckdb   # デフォルトの DuckDB パス（任意）
     - SQLITE_PATH=data/monitoring.db
     - KABUSYS_ENV=development|paper_trading|live
     - LOG_LEVEL=INFO|DEBUG|...
   - これらは src/kabusys/config.py の Settings クラスにより取得されます。未設定の必須項目は ValueError を投げます。

5. データディレクトリ作成（必要に応じて）
   - mkdir -p data

---

## 使い方（主要ユーティリティ）

以下は代表的な利用例です。各関数は DuckDB の接続オブジェクト（duckdb.connect(...) が返す接続）を受け取り、DB テーブルを参照／更新します。

- DuckDB 接続作成
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

- 日次 ETL パイプライン実行（カレンダー・株価・財務・品質チェック）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- 単体 ETL ジョブ（例：株価差分 ETL）
```python
from kabusys.data.pipeline import run_prices_etl
fetched, saved = run_prices_etl(conn, target_date=date(2026, 3, 20))
```

- ニュースのセンチメントスコア算出（LLM を呼ぶ）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

count = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"scored {count} codes")
```
- マクロ＋ETF による市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- 監査ログ用 DB 初期化（監査専用 DuckDB）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# init_audit_db は必要なテーブルとインデックスを作成します
```

- RSS 取得（ニュース収集の一部）
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
# 取得した articles は DB に保存するロジックを別途用意する必要があります
```

注意:
- news_nlp.score_news / regime_detector.score_regime は OpenAI API を呼ぶため、API キー（api_key 引数または環境変数 OPENAI_API_KEY）が必要です。
- ETL・ニュース処理系は DuckDB 内の所定テーブル（raw_prices, raw_financials, raw_news, news_symbols, ai_scores, market_calendar, ...）が存在することを前提とします。スキーマ定義はプロジェクトのスキーマ初期化モジュール（別途実装されている場合）を利用してください。

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN (必須: J-Quants 認証)
- OPENAI_API_KEY (必須: LLM 呼び出し)
- KABU_API_PASSWORD (必須: kabuステーション API)
- KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID (運用通知)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT (監視)
- KABUSYS_ENV (development|paper_trading|live)
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動ロードを無効化します。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                         -- 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                     -- ニュースセンチメント（銘柄別）
    - regime_detector.py              -- マクロ + ETF による市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py               -- J-Quants API クライアント + 保存ロジック
    - pipeline.py                     -- 日次 ETL パイプライン + ジョブ
    - etl.py                          -- ETLResult の再エクスポート
    - news_collector.py               -- RSS 収集と前処理
    - calendar_management.py          -- market_calendar 管理 / 営業日ロジック
    - quality.py                      -- データ品質チェック
    - stats.py                        -- z-score 等の統計ユーティリティ
    - audit.py                        -- 監査ログ（テーブル作成・初期化）
  - research/
    - __init__.py
    - factor_research.py              -- Momentum/Value/Volatility 等の計算
    - feature_exploration.py          -- 将来リターン・IC・統計サマリー等

（上記は主要モジュールの抜粋です。実際のリポジトリには追加のユーティリティやテスト、スクリプト等が含まれる可能性があります。）

---

## 開発上の注意点 / ベストプラクティス

- ルックアヘッドバイアス回避のため、各スコア・ETL は target_date を明示的に受け取り、内部で date.today() を乱用しません。バックテストで使用する際は target_date の取り扱いに注意してください。
- OpenAI / J-Quants など外部 API 呼び出しはリトライ・フェイルセーフを組み込んでいますが、API 制限やコストに注意してください。
- DuckDB に対する executemany の空パラメータは一部バージョンで問題となるため（コード中でもガードしています）、大量インサート前にデータが空でないことを確認してください。
- 監査ログは削除を想定していません。監査テーブルは運用側でのバックアップ・管理方針を用意してください。

---

何か特定の機能（例: ETL スケジュール設定、発注シミュレーション、DB スキーマ定義ファイル、requirements.txt や CI 設定）の README 追記が必要であれば、どの項目を追加するか教えてください。