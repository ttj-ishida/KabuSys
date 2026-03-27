# KabuSys

日本株向けのデータプラットフォーム兼リサーチ／自動売買補助ライブラリです。  
DuckDB をデータストアに、J-Quants API と RSS / OpenAI（gpt-4o-mini 系）を組み合わせて、データ収集（ETL）、品質チェック、ニュースNLP、マーケットレジーム判定、ファクター計算、監査ログ管理などを提供します。

主な設計方針：
- ルックアヘッドバイアスを避けるため、内部で `date.today()` / `datetime.today()` を直接参照しない（呼び出し側から日付を渡す設計）。
- DB 操作は冪等性（INSERT ... ON CONFLICT / DELETE+INSERT など）とトランザクションで安全に。
- 外部 API 呼び出しにはリトライ・レート制限・フェイルセーフを組み込み。

バージョン: 0.1.0

---

## 機能一覧

- データ取得 / ETL
  - J-Quants API クライアント（株価日足、財務データ、マーケットカレンダー、上場情報）
  - 差分更新／ページネーション対応
  - DuckDB への冪等保存（raw_prices, raw_financials, market_calendar など）
  - 日次 ETL パイプライン（run_daily_etl）
- データ品質管理
  - 欠損データ、スパイク、重複、日付不整合のチェック（quality モジュール）
- ニュース収集
  - RSS フィードの取得と前処理（news_collector）
  - 記事 ID 正規化（URL 正規化 → SHA256）
  - SSRF や XML 脆弱性対策（defusedxml / リダイレクト検査 / レスポンスサイズ制限）
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュースをまとめて LLM でセンチメント評価し ai_scores に書き込む（news_nlp.score_news）
  - マクロニュースを用いた市場レジーム判定（regime_detector.score_regime）
  - API 呼び出しは JSON Mode、リトライ、タイムアウト、フェイルセーフ実装
- リサーチ / ファクター計算
  - モメンタム / ボラティリティ / バリュー等の定量ファクター計算（research パッケージ）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
  - Zスコア正規化ユーティリティ
- カレンダー管理
  - JPX マーケットカレンダーの取得・保存、営業日判定、next/prev_trading_day など
- 監査ログ（トレーサビリティ）
  - signal_events, order_requests, executions といった監査テーブル定義と初期化ユーティリティ（audit.init_audit_db / init_audit_schema）
- 環境設定管理
  - .env / .env.local 自動ロード（プロジェクトルート検出: .git or pyproject.toml）
  - settings オブジェクト経由で各種設定取得（J-Quants トークン、Kabu API、Slack、DB パス等）

---

## 前提（Prerequisites）

- Python 3.10 以上（型注釈で | 演算子を使用）
- 必要な Python パッケージ:
  - duckdb
  - openai
  - defusedxml
- J-Quants アカウント（リフレッシュトークン）
- OpenAI API キー（news_nlp / regime_detector で使用）
- （任意）kabu API パスワード / Slack トークン 等

---

## セットアップ手順

1. リポジトリをクローン
   - 例: git clone <repo-url>

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb openai defusedxml

   （プロジェクトに pyproject.toml / requirements.txt があればそれを使用してください）
   - pip install -e .

4. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` または `.env.local` を配置すると自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可）。
   - 必須の環境変数（少なくとも次を用意してください）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）
     - KABU_API_PASSWORD: kabu API パスワード（実際のブローカ接続に必要な場合）
     - SLACK_BOT_TOKEN: Slack 通知を使う場合
     - SLACK_CHANNEL_ID: Slack 通知を使う場合
   - データベースパス（任意、デフォルトを使用する場合は不要）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視用 sqlite、デフォルト: data/monitoring.db）

5. DuckDB スキーマ初期化
   - audit.init_audit_db やプロジェクトで必要なスキーマを用意してください。スクリプトやマイグレーションがある場合はそれを実行。

---

## 使い方（主要 API / 実行例）

下記は Python スクリプト等からの呼び出し例です。読み替えて利用してください。

- 設定オブジェクトの参照
```python
from kabusys.config import settings
print(settings.duckdb_path)
```

- DuckDB 接続
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL の実行
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP（ai スコアリング）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
count = score_news(conn, target_date=date(2026,3,20), api_key=None)  # api_key None -> OPENAI_API_KEY を使用
print(f"scored {count} symbols")
```

- 市場レジーム判定
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026,3,20))
```

- 監査ログ DB 初期化（監査専用 DB）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn を用いて監査テーブルの使用開始
```

注意点：
- OpenAI の呼び出しは料金とレート制限があります。テスト時はモック化（unittest.mock.patch）することを推奨します。
- ETL / API 呼び出しはネットワークや API エラーを含むためログや例外処理を適切に扱ってください。

---

## ディレクトリ構成（主要ファイル）

プロジェクトは src 配下にパッケージ化されています。主要なモジュールと役割は以下の通りです。

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数 / .env 自動ロード、settings オブジェクト提供
  - ai/
    - __init__.py
    - news_nlp.py         — ニュースを LLM でセンチメント評価し ai_scores に書き込む
    - regime_detector.py  — マクロニュース + ETF MA で市場レジームを判定
  - data/
    - __init__.py
    - jquants_client.py   — J-Quants API クライアント + DuckDB 保存ロジック
    - pipeline.py         — ETL パイプライン（run_daily_etl 等）
    - etl.py              — ETLResult を再エクスポート
    - news_collector.py   — RSS 取得・前処理・raw_news への保存ロジック
    - calendar_management.py — 市場カレンダーの管理・営業日判定
    - stats.py            — zscore_normalize 等の汎用統計関数
    - quality.py          — データ品質チェック（欠損・スパイク・重複・日付）
    - audit.py            — 監査ログスキーマ作成・初期化
  - research/
    - __init__.py
    - factor_research.py  — モメンタム/ボラティリティ/バリュー等のファクター計算
    - feature_exploration.py — 将来リターン計算 / IC / 統計サマリー
  - ai/、data/、research/ はそれぞれ独立した責務を持つよう設計されています。

---

## 運用上の注意 / ベストプラクティス

- 機密情報（API キー、トークン）は .env に入れて管理し、リポジトリには含めないでください。
- OpenAI 呼び出しを行う箇所はテスト時に必ずモックする（ネットワーク・課金を避けるため）。
- DuckDB のファイルパスは settings.duckdb_path で管理。バックアップやスナップショット運用を検討してください。
- ETL は定期バッチ（夜間）で実行する想定です。calendar_update_job / run_daily_etl をスケジューリングしてください。
- 監査テーブル（audit）は削除しない前提で設計されています。必要に応じてアーカイブ戦略を用意してください。

---

## 参考 / トラブルシューティング

- .env 自動読み込みが働かない場合:
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 が設定されていないか確認
  - プロジェクトルートに .git または pyproject.toml があるか確認
- J-Quants API の 401 が発生する場合:
  - JQUANTS_REFRESH_TOKEN が正しいか確認。jquants_client は 401 時にトークンを自動リフレッシュしますが、トークン自体が無効だと失敗します。
- OpenAI レスポンスの JSON パースエラーや形式違いが起きる場合:
  - LLM の出力は厳密な JSON を期待していますが、予期しない出力が混入することがあります。ログを確認し、必要ならリトライやプロンプト調整を行ってください。

---

README は随時更新してください。追加した機能（発注・実行モジュール、監視・通知など）はここに追記して運用ガイドラインを整備するとよいでしょう。