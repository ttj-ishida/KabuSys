# KabuSys

日本株向けの自動売買／データ基盤ライブラリ（KabuSys）です。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュース収集・NLP、マーケットレジーム判定、研究用ファクター計算、監査ログなどを含むモジュール群を提供します。

---

## プロジェクト概要

KabuSys は以下の目的で設計された Python モジュール群です。

- J-Quants API からの株価・財務・カレンダーデータ取得と DuckDB への冪等保存
- ニュース収集（RSS）と LLM（OpenAI）を用いたニュースセンチメント解析
- 市場レジーム判定（ETF MA とマクロニュースの組合せ）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 研究用途のファクター計算（モメンタム／ボラティリティ／バリュー等）
- 監査ログスキーマ（シグナル → 発注 → 約定 のトレーサビリティ）
- 開発・運用向け設定管理（.env 自動読み込み等）

コードは look-ahead bias（将来情報の参照）を避ける設計、冪等性、堅牢なリトライ/バックオフ、API レート制御、セキュリティ対策（SSRF対策、XML デフューズ等）に配慮しています。

---

## 主な機能一覧

- 環境設定
  - .env / .env.local を自動読込（プロジェクトルート検出）
  - 必須変数チェック（Settings クラス）
- データ ETL（kabusys.data.pipeline）
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - 差分取得・バックフィル・品質チェック
- J-Quants API クライアント（kabusys.data.jquants_client）
  - トークン管理、ページネーション、レートリミット、保存関数（save_*）
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、URL 正規化、SSRF 等の安全チェック
- データ品質チェック（kabusys.data.quality）
  - 欠損、重複、スパイク、日付不整合の検査
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions テーブル定義と初期化ユーティリティ
- AI（LLM）連携（kabusys.ai）
  - score_news: 銘柄ごとのニュースセンチメントを ai_scores に保存
  - score_regime: ETF（1321）200日MA乖離とマクロニュースを合成して market_regime に保存
- 研究モジュール（kabusys.research）
  - calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank
- 汎用統計ユーティリティ（kabusys.data.stats）
  - zscore_normalize

---

## セットアップ手順

1. 必要環境
   - Python 3.10+（typing, match union 等に依存箇所あり）
   - DuckDB
   - OpenAI SDK（openai）
   - defusedxml
   - その他標準ライブラリ（urllib 等）

2. インストール（例）
   - 仮想環境を作成して有効化してください。
   - 必要なパッケージを pip でインストール（requirements.txt がないため最低限の依存例）:
     ```
     pip install duckdb openai defusedxml
     ```
   - 開発中は editable install:
     ```
     pip install -e .
     ```
     （プロジェクトに setup.py/pyproject.toml があればそちらを利用）

3. 環境変数 / .env
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で抑止可能）。
   - 必須の環境変数（少なくとも以下を設定）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API パスワード（発注などで使用）
     - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID — Slack チャンネル ID
     - OPENAI_API_KEY — OpenAI API キー（score_news/score_regime 実行時に参照）
   - 任意:
     - KABUSYS_ENV = development | paper_trading | live
     - LOG_LEVEL = DEBUG|INFO|WARNING|ERROR|CRITICAL
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（監視DB。デフォルト data/monitoring.db）

   例 .env（参考）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-xxxx
   SLACK_BOT_TOKEN=xoxb-xxxx
   SLACK_CHANNEL_ID=C01234567
   KABU_API_PASSWORD=secret
   KABUSYS_ENV=development
   ```

---

## 使い方（簡易ガイド）

以下は代表的なユースケースの例です。実際にはロガー設定やエラーハンドリングを追記してください。

1) DuckDB コネクションを作成して日次 ETL を実行
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースセンチメントスコアを計算（OpenAI API キーが環境変数にあること）
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("scored:", n_written)
```

3) 市場レジーム判定（1321 の MA とマクロニュース）
```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査ログ DB 初期化（監査専用 DB を作る）
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# テーブルとインデックスが作成される
```

5) 研究用ファクター計算例
```python
import duckdb
from datetime import date
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026,3,20))
# records は各銘柄ごとの辞書リスト
```

--- 

## テスト / 開発運用に関する補足

- 自動 .env 読込を無効にする: 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します（テストで環境を明示的に制御したい場合に有用）。
- OpenAI 呼び出しや外部 HTTP をユニットテストで差し替えるために、モジュール内部の _call_openai_api や _urlopen などを mock/patch する設計になっています。
- DB 保存は多くの箇所で BEGIN/DELETE/INSERT/COMMIT の冪等パターンを採用しています。DuckDB の executemany が空リストを受け付けない制限への配慮もあります。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 配下の主要モジュール一覧（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理
  - ai/
    - __init__.py
    - news_nlp.py            — ニュース NLP / score_news
    - regime_detector.py     — 市場レジーム判定 / score_regime
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント + save_* 関数
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - etl.py                 — ETLResult 再エクスポート
    - news_collector.py      — RSS 収集と正規化
    - calendar_management.py — 市場カレンダー管理
    - quality.py             — データ品質チェック
    - stats.py               — 統計ユーティリティ（zscore）
    - audit.py               — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py     — Momentum/Volatility/Value 等
    - feature_exploration.py — 将来リターン / IC / 統計サマリー

（実際のソースツリーにその他ユーティリティやモジュールが含まれます）

---

## 既知の設計方針・注意点

- ルックアヘッドバイアス対策: 多くの処理で date.today()/datetime.now() を直接参照せず、target_date を明示的に受け取る設計です。バックテスト用途での誤使用に注意してください。
- 冪等性: ETL や保存処理は基本的に ON CONFLICT / DELETE→INSERT のパターンで冪等性を担保しています。
- エラー許容: LLM 呼び出しや外部 API が失敗した場合もフェイルセーフ（ゼロスコアにフォールバック等）で継続する実装方針です。状況に応じて呼び出し側でアラートを出してください。
- セキュリティ: RSS 取得での SSRF 対策、defusedxml による XML 攻撃対策を行っています。

---

必要に応じて README を拡張して、具体的な運用手順（cron ジョブ定義、Slack 通知例、kabuステーション発注フロー、テストの書き方等）を追加できます。どの部分を優先して詳述したいか教えてください。