# KabuSys

KabuSys は日本株のデータプラットフォーム・研究・自動売買に必要なユーティリティ群を提供する Python パッケージです。J-Quants API / RSS / OpenAI 等と連携してデータ収集・品質管理・AI によるニュースセンチメント解析・市場レジーム判定・監査ログ管理などを行うことを想定しています。

バージョン: 0.1.0

---

## プロジェクト概要

主な目的は以下です。

- J-Quants API からの株価・財務・カレンダー等の差分 ETL（DuckDB に保存）
- RSS ニュース収集と銘柄紐付け
- OpenAI を使ったニュースセンチメントおよびマクロセンチメント評価（gpt-4o-mini を想定）
- 市場レジーム判定（ETF 1321 の MA とマクロセンチメントの合成）
- 研究用のファクター計算・特徴量分析ユーティリティ
- 発注〜約定までの監査ログ（監査テーブル、監査DB初期化）
- データ品質チェック（欠損・スパイク・重複・日付不整合）

設計方針としては、ルックアヘッドバイアスを避けるために内部で date.today() 等を直接参照しない箇所が多く、DuckDB をメインストアとしたオフライン処理（夜間バッチ等）に適した設計になっています。

---

## 機能一覧

- data/
  - jquants_client: J-Quants API クライアント（認証、取得、DuckDB への冪等保存）
  - pipeline / etl: 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
  - news_collector: RSS 取得と raw_news への保存（SSRF 対策、トラッキング除去）
  - calendar_management: JPX カレンダー管理と営業日判定ヘルパー
  - quality: データ品質チェック（欠損／スパイク／重複／日付整合性）
  - audit: 発注・約定の監査テーブル定義と初期化ユーティリティ
  - stats: 共通統計ユーティリティ（Zスコア正規化など）
- ai/
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを OpenAI で評価して ai_scores に保存
  - regime_detector.score_regime: ETF 1321 の MA とマクロニュースから市場レジーム判定
- research/
  - factor_research: モメンタム / ボラティリティ / バリュー等のファクター計算
  - feature_exploration: 将来リターン計算、IC（Information Coefficient）計算、統計サマリ等
- config
  - 環境変数管理 (.env / .env.local の自動読み込み、必須キーチェック)
- __init__.py で主要パッケージをエクスポート

---

## 前提・依存関係

- Python 3.10+
- 主要ライブラリ（例）:
  - duckdb
  - openai
  - defusedxml
- ネットワーク接続: J-Quants API, OpenAI API, RSS ソース など

パッケージに明示された requirements.txt はありませんが、上の主要ライブラリは少なくともインストールしてください。

例:
pip install duckdb openai defusedxml

（開発環境向けに setuptools / poetry 等を使ってパッケージをインストールすることを推奨します）

---

## セットアップ手順

1. リポジトリをクローン / プロジェクトを配置

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存ライブラリをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml

4. パッケージを開発モードでインストール（任意）
   - pip install -e .

5. 環境変数の設定
   必須の環境変数（少なくとも以下を用意してください）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabuステーション API 用パスワード（使用箇所がある場合）
   - SLACK_BOT_TOKEN: Slack 通知を使う場合
   - SLACK_CHANNEL_ID: Slack チャンネル ID
   - OPENAI_API_KEY: OpenAI API キー（score_news / regime_detector で使用）

   任意 / デフォルト:
   - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
   - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）

   ヒント: プロジェクトルートに .env / .env.local を置くと、自動で読み込まれます。
   自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

6. （オプション）.env の例
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456
   KABUSYS_ENV=development
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 使い方（簡易例）

以下は主要 API の使用例です。プロジェクトのスクリプトや cron ジョブから呼び出す想定です。

- DuckDB 接続準備（settings を利用）
```python
import duckdb
from kabusys.config import settings

db_path = str(settings.duckdb_path)
conn = duckdb.connect(db_path)
```

- 日次 ETL を実行（run_daily_etl）
```python
from kabusys.data.pipeline import run_daily_etl

# target_date を指定しない場合は今日（ただし内部で営業日に調整されます）
result = run_daily_etl(conn)
print(result.to_dict())
```

- ニュースセンチメントのスコア付け（score_news）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# target_date に対して、前日15:00 JST〜当日08:30 JST のニュースを集計して評価
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"wrote scores for {n_written} codes")
```

- 市場レジーム判定（score_regime）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

ret = score_regime(conn, target_date=date(2026, 3, 20))
# 戻り値は 1（成功）を返すことを期待
```

- 監査データベースを初期化（発注/約定ログ用）
```python
from kabusys.data.audit import init_audit_db
from pathlib import Path

audit_conn = init_audit_db(Path("data/audit.duckdb"))
# テーブルが作成され、UTCタイムゾーンが設定されます
```

- カレンダー更新ジョブを手動で実行
```python
from kabusys.data.calendar_management import calendar_update_job
from datetime import date

saved = calendar_update_job(conn, lookahead_days=90)
print(f"saved {saved} calendar entries")
```

注意点:
- OpenAI API を呼ぶ関数（score_news / score_regime）は api_key 引数でキーを渡すか、環境変数 OPENAI_API_KEY を参照します。
- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml の存在する親ディレクトリ）を探索して行います。
- DuckDB への書き込みは多くが冪等（ON CONFLICT DO UPDATE）で実装されています。

---

## 環境変数（要約）

必須:
- JQUANTS_REFRESH_TOKEN
- OPENAI_API_KEY（ai 機能を使う場合）
- SLACK_BOT_TOKEN（Slack 通知を使う場合）
- SLACK_CHANNEL_ID（Slack 通知を使う場合）
- KABU_API_PASSWORD（kabu API を使う場合）

オプション:
- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト INFO）
- DUCKDB_PATH（デフォルト data/kabusys.duckdb）
- SQLITE_PATH（デフォルト data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1（自動 .env ロード無効化）

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py             - パッケージ定義 (version 等)
- config.py               - 環境変数 / 設定管理（.env 自動読み込み、必須チェック）
- ai/
  - __init__.py
  - news_nlp.py           - ニュースセンチメント解析と ai_scores への書込み
  - regime_detector.py    - ETF MA とマクロセンチメントを合成して市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py     - J-Quants API クライアント（取得・保存）
  - pipeline.py           - ETL パイプライン（run_daily_etl 等）
  - etl.py                - ETLResult の再エクスポート
  - news_collector.py     - RSS 取得と前処理・保存
  - calendar_management.py- JPX カレンダー管理と営業日ユーティリティ
  - quality.py            - データ品質チェック
  - stats.py              - 共通統計関数（zscore_normalize 等）
  - audit.py              - 監査テーブル定義と初期化ユーティリティ
- research/
  - __init__.py
  - factor_research.py    - モメンタム / ボラティリティ / バリュー等の計算
  - feature_exploration.py- 将来リターン, IC, 統計サマリ等

---

## 開発・テストのヒント

- 自動 .env 読み込みを無効化するには、テスト実行時に環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットしてください。
- OpenAI / J-Quants 呼び出し部分は内部でラッパー関数に分離され、テスト時にパッチ（unittest.mock.patch）しやすい設計になっています。
- DuckDB はインメモリ（":memory:"）での利用も可能なので、単体テストはインメモリ DB を使うと簡便です。
- 外部 API 呼び出しはネットワーク/レート制限を伴うため、統合テストはモック化を推奨します。

---

## ライセンス / 貢献

（この README にはライセンス情報は含まれていません。プロジェクトルートの LICENSE を参照してください。）

貢献の際は、コードスタイルやテストの追加、ドキュメント改善など歓迎します。Pull Request 前に簡単な issue を立てていただけるとスムーズです。

---

README は以上です。追加で API ドキュメント（関数引数の詳細、副作用、DB スキーマ）や運用手順（cron / GitHub Actions などのサンプル）を作成する場合はお知らせください。