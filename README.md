# KabuSys

日本株向けの自動売買／データ基盤ライブラリ。ETL（J-Quants 経由）、ニュース収集・NLP（OpenAI）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログなどを含む統合パッケージです。

主な設計方針：
- DuckDB を中心としたローカルデータレイクと SQL ベースの処理
- API 呼び出しはリトライ・レートリミット・フェイルセーフあり
- バックテスト向けに Look-ahead バイアスを防止する実装（内部で date.today() を不用意に参照しない等）
- DB 操作は冪等（ON CONFLICT / DELETE→INSERT のパターン）を意識

---

## 機能一覧

- データ取得（J-Quants）
  - 日次株価（OHLCV）、財務情報、JPX マーケットカレンダーの差分取得（ページネーション対応）
  - レート制御（120 req/min 固定間隔）、リトライ、401 の自動トークンリフレッシュ
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）

- ETL パイプライン
  - 日次 ETL（calendar → prices → financials → 品質チェック）
  - 差分更新・バックフィル・品質チェック（欠損・重複・スパイク・日付整合性）

- ニュース収集（RSS）
  - RSS 取得（SSRF 対策、gzip/サイズ保護、トラッキングパラメータ除去）
  - raw_news / news_symbols への冪等保存ロジック（ID は正規化 URL のハッシュ）

- ニュース NLP（OpenAI）
  - 銘柄ごとのニュースを結合して LLM（gpt-4o-mini）に送信、センチメント（-1..1）を ai_scores に保存
  - バッチ（最大 20 銘柄/回）、JSON mode、レスポンス検証、429/ネットワーク/5xx のリトライ

- 市場レジーム判定
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して daily レジームを判定
  - ルックアヘッド回避、フェイルセーフ（API 失敗時に 0.0）

- 研究（research）
  - モメンタム / バリュー / ボラティリティ等のファクター計算（DuckDB SQL + Python）
  - 将来リターン計算、IC（Spearman）やファクター統計サマリー、Z スコア正規化ユーティリティ

- 監査ログ（audit）
  - signal_events / order_requests / executions 等の監査テーブル定義と初期化関数（UTC タイムスタンプ、冪等）
  - 監査専用 DuckDB 初期化ユーティリティ

- 設定管理
  - .env/.env.local または環境変数から設定を自動ロード（プロジェクトルートの検出ロジックあり）
  - 必須環境変数のチェック、KABUSYS_ENV による動作モード判定（development / paper_trading / live）

---

## 必要条件 / 依存関係

- Python 3.10+
- 主な依存 Python ライブラリ：
  - duckdb
  - openai
  - defusedxml

（プロジェクト配布パッケージに requirements.txt / pyproject.toml があればそちらを利用してください）

---

## セットアップ手順

1. リポジトリを取得
   - git clone ... （ローカルで使う場合は .git があると自動で .env を読み込む root 検出が有効になります）

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (または Windows の場合 .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb openai defusedxml
   - （パッケージを開発インストールする場合）pip install -e .

4. 環境変数を用意
   - プロジェクトルート（.git のある階層、または pyproject.toml のある階層）に .env（または .env.local）を作成するか、OS 環境変数を設定します。
   - 自動 .env 読み込みはデフォルトで有効。無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

必須の環境変数（少なくとも実行する機能に応じて設定）：
- JQUANTS_REFRESH_TOKEN : J-Quants の refresh token（get_id_token に使用）
- KABU_API_PASSWORD : kabu API のパスワード（発注等で使用）
- SLACK_BOT_TOKEN : Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID : Slack 通知用チャンネル ID
- OPENAI_API_KEY : OpenAI API を直接利用する場合（関数呼び出しの api_key 引数でも指定可）

その他（任意/デフォルトあり）：
- KABUSYS_ENV : development / paper_trading / live（デフォルト development）
- LOG_LEVEL : DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH : 監視用 SQLite パス（デフォルト data/monitoring.db）

例 (.env)
```
JQUANTS_REFRESH_TOKEN=xxxxx
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（代表的な関数/実行例）

以下は最小限の利用例です。実行前に環境変数（または api_key 引数等）を適切に設定してください。

- DuckDB 接続の取得例
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL 実行（prices / financials / calendar / 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings
import duckdb

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn)  # target_date を指定しないと今日（ただし内部で営業日調整あり）
print(result.to_dict())
```

- ニュース NLP スコア取得（特定日）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key=None なら OPENAI_API_KEY を使う
print("scored:", n_written)
```

- 市場レジーム判定（特定日）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
res = score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
print("regime scored:", res)
```

- 監査ログ DB の初期化（別 DB にする場合）
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")  # :memory: も可
# テーブルが作成され、UTC タイムゾーンがセットされます
```

注意点：
- OpenAI 呼び出しはモデル gpt-4o-mini、JSON mode を使用するため、api_key の設定（環境変数 OPENAI_API_KEY）が必要です。関数の api_key 引数で上書き可能です。
- J-Quants 呼び出しは内部でトークンを取得してキャッシュします。`JQUANTS_REFRESH_TOKEN` の設定が必要です。
- ETL/AI 処理は外部 API を呼ぶため、実行時にネットワーク接続と API キーが必要です。

---

## 自動環境ロードの挙動

- パッケージの起動時に、プロジェクトルート（.git または pyproject.toml のある親ディレクトリ）を探索して .env を自動で読み込みます。
- 読み込み順: OS 環境変数（優先） → .env.local（上書き） → .env（未設定のキーにセット）
- テスト等で自動読み込みを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成（主要ファイル抜粋）

src/kabusys/
- __init__.py
- config.py                — 環境変数 / 設定管理
- ai/
  - __init__.py
  - news_nlp.py            — ニュース NLP（score_news 等）
  - regime_detector.py     — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - pipeline.py            — ETL パイプライン（run_daily_etl 等）
  - jquants_client.py      — J-Quants API クライアント（fetch / save）
  - news_collector.py      — RSS ニュース収集
  - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
  - quality.py             — 品質チェック（check_missing_data, check_spike, ...）
  - stats.py               — 統計ユーティリティ（zscore_normalize）
  - audit.py               — 監査ログ初期化
  - etl.py                 — ETLResult 再エクスポート
- research/
  - __init__.py
  - factor_research.py     — calc_momentum / calc_value / calc_volatility
  - feature_exploration.py — calc_forward_returns / calc_ic / factor_summary / rank

（README はコードベースの抜粋に基づいて作成しています。実際のリポジトリには追加ファイル・ドキュメントが存在する可能性があります）

---

## 運用上のポイント・注意事項

- データ更新は差分取得・バックフィル（デフォルト過去 3 日）方式です。ETL を定期実行するジョブを用意してください。
- AI 呼び出しはコストがかかるため、バッチ実行とキャッシュやスロットリングを検討してください。
- DuckDB の executemany に空リストを渡すと問題となるバージョンがあるため、保存処理は空チェックを行っています。
- 監査ログは削除しない前提です（監査トレースに重要）。テーブルの変更は慎重に行ってください。
- 本パッケージは本番の売買発注を含む機能を持ちます。実際に発注を行う前に paper_trading モードや明確なリスク管理を実装してください（KABUSYS_ENV=paper_trading / live を活用）。

---

必要であれば、この README を README.md としてファイル化する内容を微調整します（インストールコマンドの追加、CI/テスト手順、実運用の例など）。どの情報を追加したいか教えてください。