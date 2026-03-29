# KabuSys

日本株向けの自動売買 / データプラットフォームライブラリです。  
J-Quants からの市場データ取得、DuckDB での永続化、ニュースの NLP スコアリング（OpenAI）、ファクター計算、ETL・品質チェック、監査ログの初期化など、取引・リサーチに必要な基盤機能を提供します。

---

## 主な特徴（機能一覧）

- 環境設定管理
  - `.env` / 環境変数の自動読み込み（パッケージルート基準）
  - 設定値は `kabusys.config.settings` から取得

- データ取得 / ETL
  - J-Quants API クライアント（株価日足 / 財務データ / マーケットカレンダー）
  - 差分取得・冪等保存（DuckDB）
  - 日次 ETL パイプライン（`run_daily_etl`）

- データ品質チェック
  - 欠損、スパイク、重複、日付整合性の検査（`data.quality`）

- ニュース収集 / NLP
  - RSS 収集・前処理（SSRF 対策、トラッキングパラメータ除去）
  - OpenAI を使った銘柄単位のニュースセンチメント算出（`ai.news_nlp.score_news`）

- 市場レジーム判定
  - ETF（1321）200日移動平均乖離 + マクロニュースセンチメントを合成（`ai.regime_detector.score_regime`）

- リサーチ用ユーティリティ
  - モメンタム / バリュー / ボラティリティ等のファクター計算（`research`）
  - 将来リターン計算、IC（Information Coefficient）計算、Zスコア正規化など

- 監査ログ（トレーサビリティ）
  - シグナル → 発注 → 約定までを追跡する監査スキーマ初期化（`data.audit`）
  - 監査用 DuckDB データベース初期化ユーティリティ

---

## 前提条件（Requirements）

- Python 3.9+
- 主な依存（抜粋）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants / OpenAI / RSS フィードなど）
- J-Quants のリフレッシュトークン、OpenAI API キー等の資格情報

※ 実行環境に合わせて適宜インストールしてください。例:
```
pip install duckdb openai defusedxml
```

---

## セットアップ手順

1. リポジトリをクローン（またはパッケージを配置）
2. Python 仮想環境を作成して有効化
3. 依存パッケージをインストール
   - 例: `pip install -r requirements.txt`（requirements.txt がある場合）
   - または最低限: `pip install duckdb openai defusedxml`
4. プロジェクトルートに `.env` を作成（自動読み込みされます）
   - 自動読み込みは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能
5. DuckDB ファイルパス等の必要ディレクトリがなければ作成

---

## 環境変数（.env に設定する主要項目）

以下は必須・推奨キーの一覧（`.env.example` を作る際の参考）。

- J-Quants / API
  - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン

- kabuステーション API（発注など）
  - KABU_API_PASSWORD (必須)
  - KABU_API_BASE_URL (任意, デフォルト http://localhost:18080/kabusapi)

- OpenAI / ニュース NLP
  - OPENAI_API_KEY (必要に応じて、score_news/score_regime の引数でも指定可能)

- Slack（モニタリング等）
  - SLACK_BOT_TOKEN (必須)
  - SLACK_CHANNEL_ID (必須)

- データベース / ファイルパス
  - DUCKDB_PATH (任意, デフォルト `data/kabusys.duckdb`)
  - SQLITE_PATH (任意, デフォルト `data/monitoring.db`)

- システム
  - KABUSYS_ENV (development | paper_trading | live) デフォルト `development`
  - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)

自動読み込みはプロジェクトルートに `.env` / `.env.local` が置かれている場合、OS 環境変数を保護しつつ読み込まれます。

---

## 使い方（代表的な例）

以下は Python REPL やスクリプトから呼び出す簡単な例です。

- 設定読み出し
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.duckdb_path)
```

- DuckDB 接続を作って ETL を実行（日次 ETL）
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコア算出（OpenAI API キーは環境変数 OPENAI_API_KEY で設定か、api_key 引数で指定）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

n = score_news(conn, target_date=date(2026,3,20), api_key=None)
print(f"ai scores written for {n} codes")
```

- 市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026,3,20), api_key=None)
```

- 監査ログ DB 初期化（監査用 DuckDB ファイルを作る）
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# 以後 conn_audit を使用して監査テーブルへ書き込みが可能
```

注意:
- `score_news` / `score_regime` は OpenAI 呼び出しを行うため API キーと利用料がかかります。
- ETL / J-Quants API 呼び出しには `JQUANTS_REFRESH_TOKEN` が必須です。

---

## 実行上の注意点

- ルックアヘッドバイアス防止
  - 多くの関数（ETL / ニュース集計 / レジーム判定 / ファクター計算等）は内部で `date` 引数を受け取り、現在時刻参照を避ける設計です。バックテスト等で日時の明示を推奨します。

- 冪等性
  - 保存処理は基本的に ON CONFLICT / 適切なキーで冪等に設計されています（DuckDB 側の制約に依存）。

- レート制限 / リトライ
  - J-Quants は API レート制限（120 req/min）を守るよう内部で制御します。OpenAI 呼び出しも再試行ロジックを備えています。

- セキュリティ
  - RSS 収集は SSRF 対策（リダイレクト検査 / プライベートホスト検出）や XML パースの安全化（defusedxml）を行っています。

---

## ディレクトリ構成（概要）

プロジェクトは `src/kabusys` 配下に主要モジュールを配置しています。主なファイル / ディレクトリ:

- src/kabusys/
  - __init__.py
  - config.py              — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py          — ニュースセンチメント（OpenAI）
    - regime_detector.py   — 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py    — J-Quants API クライアント + 保存ロジック
    - pipeline.py          — ETL パイプライン（run_daily_etl 等）
    - etl.py               — ETLResult のエクスポート
    - news_collector.py    — RSS 収集、前処理
    - calendar_management.py — マーケットカレンダー管理
    - stats.py             — 統計ユーティリティ（zscore_normalize 等）
    - quality.py           — データ品質チェック
    - audit.py             — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py   — モメンタム/バリュー/ボラティリティ等
    - feature_exploration.py — 将来リターン・IC・統計集計など

---

## 開発 / テスト

- 自動環境読み込みはパッケージルートの `.env` / `.env.local` を参照します。テスト時に自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI 呼び出し部は内部関数をモックしやすい構成になっています（ユニットテストで差し替え可能）。
- DuckDB を用いるため、テスト用は `:memory:` を使うと便利です。

---

## ライセンス / 責任範囲

この README はコードベースから生成された要約ドキュメントです。実際の商用運用では API 制約、規制、運用リスク（振る舞いの確認、レート制限、資金管理等）を十分に検討してください。

---

必要であれば README に以下を追記できます：
- .env.example の具体的なテンプレート
- よくあるトラブルシューティング（J-Quants 認証エラー、OpenAI レート制限）
- 追加の CLI やスケジューラ（cron / Airflow）での運用例

ご希望があれば上記を追記して README を拡張します。