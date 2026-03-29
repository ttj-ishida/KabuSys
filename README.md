# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
ETL / データ品質チェック / ニュースNLP / 市場レジーム判定 / 監査ログなど、取引・リサーチ基盤に必要な機能群を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の目的で設計された Python パッケージです。

- J-Quants API から株価・財務・カレンダーを差分取得する ETL
- DuckDB を基盤としたデータ保存と品質チェック
- RSS ニュース収集と OpenAI を用いた銘柄センチメントスコアリング（ニュースNLP）
- ETF とマクロニュースを組み合わせた市場レジーム判定（bull/neutral/bear）
- 戦略 → シグナル → 発注 → 約定 のトレーサビリティを担保する監査（audit）スキーマ
- 研究（research）向けのファクター計算・特徴量解析ユーティリティ

設計上の重要点:
- ルックアヘッドバイアス回避（target_date を明示して過去データのみ参照）
- API 呼び出しのリトライ・レート制御・フォールバックを備えた堅牢な実装
- DuckDB を中心とした冪等保存（INSERT ... ON CONFLICT DO UPDATE / DO NOTHING など）
- 外部サービスキーは環境変数 / .env で管理（自動ロード機能あり）

---

## 主な機能一覧

- データ ETL
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（kabusys.data.pipeline）
  - J-Quants からの差分取得、保存（jquants_client）
- データ品質チェック
  - 欠損・重複・スパイク・日付不整合検査（kabusys.data.quality）
- ニュース関連
  - RSS 取得・保存・前処理（kabusys.data.news_collector）
  - ニュースをまとめて OpenAI で銘柄ごとにスコア化（kabusys.ai.news_nlp）
- 市場レジーム判定
  - ETF（1321）の MA とマクロニュースの LLM センチメントを合成（kabusys.ai.regime_detector）
- 研究（Research）
  - モメンタム / バリュー / ボラティリティ等のファクター計算（kabusys.research）
  - forward returns / IC / 統計サマリー（kabusys.research.feature_exploration）
- 監査（Audit）
  - signal_events / order_requests / executions のスキーマと初期化ユーティリティ（kabusys.data.audit）
- 設定管理
  - .env / 環境変数の読み込み・設定ラッパー（kabusys.config）

---

## 動作前提・依存関係

最低限必要な環境（本リポジトリの実装に基づく想定）:

- Python 3.10+
- 必要ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリの urllib 等を使用）

インストール例（開発環境）:
```
python -m pip install -U pip
pip install duckdb openai defusedxml
# パッケージを editable にインストールする場合（プロジェクトルートに pyproject.toml がある前提）
pip install -e .
```

---

## 環境変数 / .env

KabuSys はプロジェクトルートの `.env` / `.env.local` を自動で読み込みます（OS 環境変数が優先）。自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な環境変数（例）:

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID（必須）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 環境 ("development" | "paper_trading" | "live")
- LOG_LEVEL: "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL"

例: `.env`
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=YOUR_KABU_PASSWORD
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

注意:
- Settings クラスは必須キーが未設定のとき ValueError を投げます（`settings.jquants_refresh_token` など）。
- テスト時や CI では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を指定して自前で環境設定することができます。

---

## セットアップ手順（基本）

1. リポジトリをクローン/配置
2. 仮想環境を作成し有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb openai defusedxml
   - （プロジェクト内に pyproject.toml があれば）pip install -e .
4. プロジェクトルートに `.env` を作成（上記参照）
5. 初期 DB（監査用など）の準備（オプション）
   - Python 例:
     ```
     from kabusys.config import settings
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db(settings.duckdb_path)
     conn.close()
     ```
6. ETL / バッチを実行

---

## 使い方（主要な例）

以下例はすべて Python スクリプト内での利用例です。target_date などは明示的に与えることでルックアヘッドを防ぎます。

- DuckDB 接続準備
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行（全 ETL + 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- 単体で株価 ETL / 財務 ETL / カレンダー ETL を実行
```python
from kabusys.data.pipeline import run_prices_etl, run_financials_etl, run_calendar_etl
from datetime import date

fetched, saved = run_prices_etl(conn, target_date=date(2026, 3, 20))
```

- ニューススコアリング（OpenAI を使用）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# api_key を引数で渡すか、環境変数 OPENAI_API_KEY を設定してください
count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"scored {count} codes")
```

- 市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査スキーマ初期化（既存 DB に監査用テーブルを追加）
```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn, transactional=True)
```

- 研究向けユーティリティ（例: モメンタム）
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date

records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は [{ "date":..., "code":..., "mom_1m":..., ... }, ...]
```

注記:
- OpenAI 系関数は `api_key` 引数を受け取ります。None を渡すと環境変数 `OPENAI_API_KEY` を参照します。未設定の場合は ValueError が発生します。
- ETL / ニュース・レジーム処理は外部 API を使うため、API キー・トークン・ネットワーク接続が必要です。

---

## ディレクトリ構成（主要ファイルとモジュールの説明）

プロジェクトは src/kabusys 以下にモジュールを配置しています。主要な構成は以下の通り（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py               : 環境変数 / .env の自動読み込みと Settings クラス
  - ai/
    - __init__.py
    - news_nlp.py           : ニュースの集約・OpenAI でのスコアリングロジック
    - regime_detector.py    : ETF(1321) MA とマクロニュースで市場レジーム判定
  - data/
    - __init__.py
    - pipeline.py           : ETL パイプライン実装（run_daily_etl 等）
    - jquants_client.py     : J-Quants API クライアント（取得・保存・認証）
    - news_collector.py     : RSS フィード取得・前処理・保存ユーティリティ
    - calendar_management.py: 市場カレンダー管理・営業日判定
    - quality.py            : データ品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py              : zscore 等の統計ユーティリティ
    - etl.py                : ETLResult の再エクスポート
    - audit.py              : 監査テーブル DDL と初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py    : モメンタム / バリュー / ボラティリティ等
    - feature_exploration.py: forward returns / IC / 統計サマリー

各ファイルの冒頭に詳細なドキュメント文字列（設計意図・処理フロー・フォールバック方針）が含まれており、実装の振る舞いを読み取れます。

---

## 運用上の注意点 / ベストプラクティス

- ルックアヘッド回避:
  - パッケージ内の多くの関数は内部で `date.today()` を参照しない（target_date を明示する）ため、バッチやバックテストでは target_date を明示的に与えることを推奨します。
- 環境・鍵管理:
  - API キーやトークンは .env / 環境変数で安全に管理してください。CI ではシークレットストアを利用して環境変数注入することを推奨します。
- エラーハンドリング:
  - 外部 API 呼び出しはリトライとフォールバックを備えていますが、障害時のログ確認と再実行フローの設計を行ってください。
- DB バックアップ:
  - DuckDB ファイルは定期的にバックアップしてください。監査データは削除しない前提で設計されています。

---

## 貢献・拡張

- 各モジュールはテスト差し替え（モック）を想定した設計になっています（例: OpenAI 呼び出しのラッパー関数を patch 可能）。
- 新しいデータソースやモデルを追加する場合は既存の ETL / 保存パターン（fetch → save → quality）に合わせて実装してください。
- Issue / Pull Request 形式での貢献を歓迎します。

---

README に書ききれない詳細（各関数の引数仕様・戻り値・副作用等）はソースコード中の docstring を参照してください。必要であれば特定モジュール・関数の利用例や API シーケンス図を追加で作成します。