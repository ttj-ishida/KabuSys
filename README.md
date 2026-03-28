# KabuSys — 日本株自動売買基盤（README）

バージョン: 0.1.0

概要
---
KabuSys は日本株向けのデータ基盤・研究・戦略・監査・AI 支援を含む自動売買システムのライブラリ群です。本リポジトリは主に以下を提供します。

- J-Quants API からのデータ ETL（株価・財務・カレンダー）
- ニュース収集と LLM によるニュースセンチメント（銘柄単位）
- 市場レジーム判定（MA200 とマクロニュースの合成）
- 研究用ファクター計算（モメンタム／バリュー／ボラティリティ等）
- マーケットカレンダー管理・営業日判定ユーティリティ
- 監査ログ（シグナル→発注→約定のトレーサビリティ）初期化
- データ品質チェックユーティリティ

設計のキーポイント
- ルックアヘッドバイアスを避けるため、内部処理で date.today() や datetime.today() に依存しない設計（関数に target_date を明示的に渡す）。
- DuckDB をデータストアとして利用し、SQL と Python の組合せで処理を実装。
- 冪等性（ON CONFLICT / DELETE → INSERT）やリトライ、バックオフ、フェイルセーフを重視。
- 外部 API 呼び出し（OpenAI, J-Quants, RSS 等）には各種保護（レート制限、リトライ、SSRF 対策、レスポンス検証）を実装。

機能一覧
---
主な公開 API と機能（モジュール別）:

- kabusys.config
  - .env 自動ロード（.env / .env.local）と環境変数管理
  - settings: JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / SLACK_BOT_TOKEN / SLACK_CHANNEL_ID などをプロパティで取得

- kabusys.data
  - jquants_client: J-Quants API との連携（取得・保存・認証・ページネーション・保存用ユーティリティ）
  - pipeline: run_daily_etl などの ETL パイプライン、ETLResult
  - news_collector: RSS 取得・前処理・raw_news 保存（SSRF / gzip / XML の安全対策）
  - calendar_management: market_calendar 管理、営業日判定・next/prev/get_trading_days、calendar_update_job
  - quality: データ品質チェック（欠損・スパイク・重複・日付整合性）
  - stats: zscore_normalize 等ユーティリティ
  - audit: 監査ログスキーマの初期化（init_audit_schema / init_audit_db）

- kabusys.ai
  - news_nlp.score_news: ニュースを銘柄ごとに集約し OpenAI でセンチメント評価、ai_scores へ書込
  - regime_detector.score_regime: ETF（1321）の MA200 とマクロニュースの LLM スコアを合成して market_regime に書込

- kabusys.research
  - factor_research.calc_momentum / calc_value / calc_volatility
  - feature_exploration.calc_forward_returns / calc_ic / factor_summary / rank
  - データは DuckDB の prices_daily / raw_financials 等のみ参照（発注等の副作用なし）

セットアップ手順
---
前提:
- Python 3.9+（型ヒントにより 3.10+ を想定する実装もあるため、実運用では 3.10+ 推奨）
- DuckDB, OpenAI SDK, defusedxml などの依存パッケージ

推奨インストール例:
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存パッケージのインストール（簡易例）
   - pip install duckdb openai defusedxml

   ※プロジェクトに requirements.txt / pyproject.toml があればそちらを利用してください。

3. パッケージを開発モードでインストール（任意）
   - pip install -e .

環境変数
---
主要な必須環境変数:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（jquants_client.get_id_token に使用）
- KABU_API_PASSWORD: kabuステーション等の API パスワード（将来の注文 API 等で使用）
- SLACK_BOT_TOKEN: Slack 通知用ボットトークン
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID
- OPENAI_API_KEY: OpenAI API キー（AI モジュールで使用）

デフォルトの DB パス等（環境変数で上書き可）:
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- KABUSYS_ENV: development / paper_trading / live（既定: development）
- LOG_LEVEL: DEBUG/INFO/...

.env 自動読み込み:
- パッケージ import 時にプロジェクトルート（.git または pyproject.toml を探索）から .env と .env.local を自動読み込みします（OS 環境変数 > .env.local > .env の順）。
- 自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

使い方（主要なユースケース）
---
以下は簡単な呼び出し例です。実行前に必要な環境変数を設定してください。

1) DuckDB 接続の準備
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

2) 日次 ETL を実行する
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

3) ニューススコア（銘柄ごとの AI スコア）を作成する
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# OPENAI_API_KEY が環境変数に設定されていること
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込んだ銘柄数:", n_written)
```

4) 市場レジーム判定を実行する
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

5) 研究用ファクター計算（例: モメンタム）
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date

records = calc_momentum(conn, date(2026, 3, 20))
# records は [{ "date": ..., "code": "1301", "mom_1m": ..., ...}, ...]
```

6) 監査ログ DB の初期化
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# テーブルが作成され、UTC タイムゾーンが設定されます
```

7) カレンダー更新ジョブ（夜間バッチの一部）
```python
from kabusys.data.calendar_management import calendar_update_job
from datetime import date

saved = calendar_update_job(conn, lookahead_days=90)
print("保存済み件数:", saved)
```

注意点 / 運用上のポイント
- OpenAI / J-Quants 等の外部 API 呼び出しはレート制限・コストが掛かります。運用環境では適切なスケジューリング（夜間バッチ等）と課金管理を行ってください。
- ETL や AI 処理はルックアヘッドバイアスを回避する設計になっています。バッチ実行時は target_date を正しく設定して下さい。
- DuckDB の executemany は空リストを受け付けないバージョンの挙動に配慮した実装になっています（pipeline / news_nlp 等で考慮済み）。
- news_collector は RSS の SSRF や大容量攻撃に対して多数の保護を入れていますが、運用で利用する RSS ソースは信頼できるものに限定してください。

ディレクトリ構成
---
リポジトリ内の主要ファイル（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュースセンチメント取得（OpenAI）
    - regime_detector.py           — 市場レジーム判定（MA200 + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント（取得・保存）
    - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
    - etl.py                       — ETLResult のエクスポート
    - news_collector.py            — RSS 収集・前処理・保存
    - calendar_management.py       — マーケットカレンダー管理
    - quality.py                   — データ品質チェック
    - stats.py                     — 統計ユーティリティ（zscore_normalize）
    - audit.py                     — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py           — ファクター計算 (momentum/value/volatility)
    - feature_exploration.py       — 将来リターン / IC / 統計サマリー 等
  - ai, data, research 以下にあるユーティリティ・ログ処理・SQL 実装が主要ロジック

貢献 / 開発
---
- テスト: 各モジュールではネットワーク依存部分をモック可能に設計されています（例: _call_openai_api の差し替え、_urlopen のモック等）。
- .env.example を用意し、ローカルで必要な環境変数を管理してください。
- 自動ロードを止めるには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してテストしてください。

ライセンス
---
（ここにプロジェクトのライセンス表記を入れてください）

最後に
---
この README はコードベースから生成した概要です。実際の運用では接続先・トークン・DB パス・ETL スケジュールなどを適切に設定し、テスト環境で十分に検証してから本番へ移行してください。質問や追加のドキュメント（例: API リファレンス、運用手順書、設計ドキュメント）が必要であればお知らせください。