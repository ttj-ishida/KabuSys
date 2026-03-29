# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ集です。  
ETL（J-Quants → DuckDB）・ニュース収集・AI（LLM）によるニュースセンチメント・市場レジーム判定・研究用ファクター計算・監査ログなどを含むモジュール群を提供します。

---

## プロジェクト概要

KabuSys は日本株のデータ取得・品質管理・特徴量計算・AIベースのニュース評価・市場レジーム判定・監査ログを一貫して扱うための内部ライブラリ群です。  
主に以下用途を想定しています。

- J-Quants API からの差分 ETL（株価・財務・マーケットカレンダー）
- RSS ベースのニュース収集と前処理
- OpenAI (gpt-4o-mini 等) を用いたニュースセンチメント解析（銘柄別 / マクロ）
- DuckDB に格納したデータを用いる研究用ファクター計算
- 発注フロー追跡のための監査ログスキーマ初期化

設計上、バックテスト時のルックアヘッドバイアスを避ける工夫（日時参照の制限・DBのクエリ条件）が盛り込まれています。

---

## 主な機能一覧

- データ取得（J-Quants）
  - 株価日足（OHLCV）
  - 財務データ（四半期 BS/PL）
  - JPX マーケットカレンダー
  - 上場銘柄情報

- ETL パイプライン
  - 差分取得（最終取得日をもとに差分フェッチ）
  - 保存（DuckDB へ冪等保存）
  - 品質チェック（欠損・重複・スパイク・日付不整合）

- ニュース処理
  - RSS 取得（SSRF 対策・圧縮対応・トラッキングパラメータ除去）
  - 前処理（URL 除去・空白正規化）
  - raw_news / news_symbols 連携

- AI（OpenAI API）連携
  - 銘柄別ニュースのセンチメント付与（news_nlp.score_news）
  - マクロとETF MA200 乖離の複合から日次市場レジーム判定（regime_detector.score_regime）
  - API 呼び出しはリトライ・バックオフ・フェイルセーフ実装

- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー 等のファクター計算
  - 将来リターン計算・IC（Information Coefficient）計算・統計サマリー
  - z-score 正規化ユーティリティ

- 監査ログ（audit）
  - signal_events / order_requests / executions 等の監査スキーマ初期化
  - 監査 DB 初期化ユーティリティ（init_audit_db）

---

## 必要要件

- Python 3.10+（型アノテーションで | を使用）
- 主な外部依存（例）
  - duckdb
  - openai
  - defusedxml

（プロジェクトの実際の requirements.txt / pyproject.toml を参照してください）

---

## インストール

リポジトリルートでパッケージをインストールします（editable 推奨）:

```bash
pip install -e .
# あるいは
pip install duckdb openai defusedxml
```

プロジェクトに付随する依存は pyproject.toml / requirements を参照して追加でインストールしてください。

---

## 環境変数（設定）

設定は環境変数またはプロジェクトルートの `.env` / `.env.local` から読み込まれます。自動読み込みはデフォルトで有効です（CWD に依存せずパッケージファイル位置からプロジェクトルートを探索します）。自動読み込みを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主要な環境変数:

- J-Quants 関連
  - JQUANTS_REFRESH_TOKEN (必須): J-Quants のリフレッシュトークン

- kabuステーション（ブローカー）関連
  - KABU_API_PASSWORD (必須): kabu API パスワード
  - KABU_API_BASE_URL (任意): デフォルト "http://localhost:18080/kabusapi"

- Slack 通知
  - SLACK_BOT_TOKEN (必須)
  - SLACK_CHANNEL_ID (必須)

- OpenAI
  - OPENAI_API_KEY (AI 機能を使う場合に推奨、関数呼び出し時に引数として渡すことも可能)

- システム
  - KABUSYS_ENV (development | paper_trading | live) - デフォルト development
  - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) - デフォルト INFO

- データベースパス
  - DUCKDB_PATH デフォルト: data/kabusys.duckdb
  - SQLITE_PATH デフォルト: data/monitoring.db

.env の読み込み優先順位:
1. OS 環境変数
2. .env.local（存在すれば上書き）
3. .env

簡単な .env.example:

```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
OPENAI_API_KEY=sk-...
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
```

---

## セットアップ手順（簡易）

1. リポジトリをクローン＆インストール
   - pip install -e . を実行

2. 環境変数を設定（.env をプロジェクトルートに配置）

3. DuckDB ファイル作成（任意）
   - ETL / audit 初期化時に自動でディレクトリ作成されます。
   - 監査 DB を別ファイルで用意する場合:
     - Python から init_audit_db を呼ぶ（下記参照）

4. 依存サービス（J-Quants アクセス可能、OpenAI を使う場合は API キー準備）

---

## 使い方（主要な API / 実行例）

以下はコード例です。実行はプロジェクト内 Python 環境で行ってください。

- DuckDB 接続の作成（設定された DUCKDB_PATH を利用）:

```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行（run_daily_etl）:

```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# target_date を省略すると今日（ローカル日）になります
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースのセンチメントスコア付与（OpenAI API キーが必要）:

```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OPENAI_API_KEY が環境変数に設定されているか、api_key 引数で渡す
count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"scored {count} tickers")
```

- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースを組合せ）:

```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ DB を初期化（監査専用の DuckDB を作る）:

```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit_kabusys.duckdb")
# audit_conn をアプリの監査操作で利用
```

- カレンダー関係のユーティリティ例:

```python
from datetime import date
from kabusys.data.calendar_management import is_trading_day, next_trading_day

d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

注意点:
- AI 機能（news_nlp / regime_detector）は OpenAI API を呼ぶため、OPENAI_API_KEY を環境変数で用意してください（または各関数へ api_key 引数で渡す）。
- ETL の fetch では J-Quants のリフレッシュトークン（JQUANTS_REFRESH_TOKEN）が必要です。
- 多くの関数は DuckDB の接続（duckdb.DuckDBPyConnection）を要求します。

---

## 実装上の留意点 / 性能と安全性

- Look-ahead バイアス防止
  - モジュール内の多くの処理は `datetime.today()` 等を直接参照せず、呼び出し元が target_date を明示して使用する設計です。

- 冪等性
  - データ保存は ON CONFLICT DO UPDATE 等で冪等に行う実装です。

- API 呼び出しの堅牢性
  - J-Quants / OpenAI 呼び出しはリトライ・指数バックオフ・ネットワーク障害へのフェイルセーフを持ちます。

- セキュリティ対策
  - RSS 取得では SSRF 対策（リダイレクト検査・プライベートアドレスブロック）、XML パースに defusedxml を採用、応答サイズ制限などを実施しています。

---

## ディレクトリ構成

主要なファイル・ディレクトリ（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                       -- 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                    -- ニュースセンチメント解析（銘柄別）
    - regime_detector.py             -- マクロ + ETF MA200 による市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py              -- J-Quants API クライアント & DuckDB 保存
    - pipeline.py                    -- ETL パイプライン（run_daily_etl 等）
    - etl.py                         -- ETL 結果クラス公開
    - news_collector.py              -- RSS ニュース収集
    - calendar_management.py         -- 市場カレンダー管理 / 営業日判定
    - quality.py                     -- データ品質チェック
    - stats.py                       -- 汎用統計ユーティリティ（z-score 等）
    - audit.py                       -- 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py             -- モメンタム/バリュー/ボラティリティ等
    - feature_exploration.py         -- 将来リターン / IC / 統計サマリー 等
  - (その他)                         -- strategy / execution / monitoring 等の抽象公開予定

（実際のリポジトリツリーはプロジェクトルートを参照してください）

---

## 開発・テスト TIPS

- 自動 .env 読み込みを無効化する場合:
  - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると .env の自動読み込みが行われません（ユニットテスト等で便利）。

- OpenAI 呼び出しのテスト
  - news_nlp / regime_detector 内の `_call_openai_api` はモック差し替え用に分離されています（unittest.mock.patch を利用）。

- DuckDB の executemany について
  - DuckDB のバージョンによる制約に合わせて空パラメータの扱いに注意（コード内で空リストを避けるガードあり）。

---

## ライセンス・注意事項

この README はコードベースの説明を目的としたドキュメントです。実運用で使用する際は API トークンの保護、発注フローの安全性確認、監査・ロギングの適切な設定を行ってください。またライブ口座での発注機能を追加する場合は十分なテストとガバナンスが必須です。

---

不明点や追加したい使用例があれば教えてください。README に具体的なコマンド例や CI / デプロイ手順を追記できます。