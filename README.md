# KabuSys

日本株向けのデータプラットフォーム兼自動売買補助ライブラリです。  
データ取得（J-Quants）、ETL、ニュースのNLPスコアリング（OpenAI）、市場レジーム判定、研究用ファクター計算、監査ログ（約定トレーサビリティ）等のユーティリティを提供します。

主な設計方針は「ルックアヘッドバイアスを排除」「DuckDB を用いたローカルデータ管理」「外部API呼び出しに対する堅牢なリトライ・レートリミット制御」「冪等保存」です。

---

## 機能一覧

- データ取得（J-Quants API）
  - 日足（OHLCV）、財務データ、JPXマーケットカレンダーなどのページネーション対応取得
  - レート制限・トークン自動更新・リトライ実装
- ETLパイプライン
  - 市場カレンダー、日足、財務の差分取得・保存
  - 品質チェック（欠損、スパイク、重複、日付整合性）
  - ETL 実行結果を ETLResult オブジェクトで返却
- ニュース収集
  - RSS フィード取得（SSRF対策、トラッキングパラメータ除去、前処理）
  - raw_news / news_symbols への冪等保存
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュースを統合して LLM でセンチメント評価（gpt-4o-mini を想定）
  - レスポンス検証・スコアクリップ・バッチ処理・リトライ
- 市場レジーム判定
  - ETF 1321 の 200 日MA乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して daily レジームを判定
- 研究用モジュール
  - モメンタム・ボラティリティ・バリューなどのファクター計算
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリー
  - z-score 正規化ユーティリティ
- 監査ログ（Audit）
  - signal_events / order_requests / executions の DDL と初期化関数（DuckDB）
  - 監査用 DB 初期化ユーティリティ

---

## 依存関係（代表的なもの）

（プロジェクトに付属の pyproject.toml / requirements がある想定。ここは代表例です）

- Python 3.10+
- duckdb
- openai (OpenAI SDK)
- defusedxml
- その他標準ライブラリ（urllib, json, logging など）

インストール例（仮）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# またはパッケージとして配布されていれば:
# pip install -e .
```

---

## セットアップ手順

1. リポジトリをクローン / コピー
2. 仮想環境を作成して依存をインストール（上記参照）
3. 環境変数の準備（.env ファイルをプロジェクトルートに置くと自動で読み込まれます）
   - 自動ロードは package 起点で .git または pyproject.toml を探索してプロジェクトルートを決定します
   - 読み込み順: OS 環境 > .env.local（上書き） > .env（初期セット）
   - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
4. DuckDB 用ディレクトリ（デフォルト: data/）を作成するなどファイル配置を準備

推奨: .env.example を用意して必要なキーを記載しておくこと。

---

## 環境変数（主なもの）

必須（アプリの主要機能で使用）
- JQUANTS_REFRESH_TOKEN: J-Quants の refresh トークン（settings.jquants_refresh_token）
- KABU_API_PASSWORD: kabuステーション API のパスワード（settings.kabu_api_password）

OpenAI 関連
- OPENAI_API_KEY: OpenAI 呼び出し時に使用（score_news / score_regime で参照）

オプション / デフォルト
- KABU_API_BASE_URL: デフォルト "http://localhost:18080/kabusapi"
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用
- DUCKDB_PATH: デフォルト "data/kabusys.duckdb"
- SQLITE_PATH: 監視用 SQLite デフォルト "data/monitoring.db"
- PAPER_FILL_MODE: paper trading のモック挙動（instant|partial|never|reject、デフォルト "instant"）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（data/paper_trading.db）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- KABUSYS_ENV: development | paper_trading | live （デフォルト development）
- LOG_LEVEL: DEBUG/INFO/...（デフォルト INFO）

設定が不足すると Settings のプロパティで ValueError が発生します（必須のものは ._require でチェック）。

---

## 使い方（代表的な例）

以下はすべて Python API を直接呼ぶ例です。DuckDB の接続は duckdb.connect() で取得します。

1) 日次 ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースをスコアリングして ai_scores に書き込む（OpenAI API キーが必要）
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"書き込み件数: {written}")
```

3) 市場レジーム判定を実行する
```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

4) 監査ログ（audit）DB を初期化する
```python
import kabusys.data.audit as audit
conn = audit.init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions テーブルが作成されます
```

5) J-Quants から日足を直接取得（テスト／ユーティリティ）
```python
from kabusys.data.jquants_client import fetch_daily_quotes
records = fetch_daily_quotes(date_from=date(2026,1,1), date_to=date(2026,1,31))
```

注意:
- API キーやトークンは環境変数経由で渡すのが推奨です。関数には api_key / id_token を引数で注入できるものが多く、テスト時に差し替え可能です。
- ニュース/LLM 呼び出しはコストとレート制限に注意してください。モック差し替え用の内部関数が準備されています（ユニットテスト向け）。

---

## ディレクトリ構成（主なファイル・モジュール）

（抜粋）

- src/kabusys/
  - __init__.py                 - パッケージ定義（__version__ 等）
  - config.py                   - 環境変数・設定管理（Settings）
  - ai/
    - __init__.py
    - news_nlp.py               - ニュースの LLM スコアリング（score_news）
    - regime_detector.py        - 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py         - J-Quants API クライアント & DuckDB 保存ロジック
    - pipeline.py               - ETL パイプライン（run_daily_etl 他）
    - etl.py                    - ETL 結果クラス再エクスポート
    - news_collector.py         - RSS ニュース収集・前処理
    - calendar_management.py    - 市場カレンダーの判定・更新ロジック
    - quality.py                - データ品質チェック
    - stats.py                  - 共通統計ユーティリティ（zscore_normalize）
    - audit.py                  - 監査ログの DDL / 初期化
  - research/
    - __init__.py
    - factor_research.py        - Momentum / Value / Volatility 等の計算
    - feature_exploration.py    - 将来リターン / IC / 統計サマリー 等

各モジュールはドキュメンテーション文字列（docstring）とログ出力を持ち、設計意図やフェイルセーフ挙動が詳細に記載されています。DuckDB を利用する関数群は接続オブジェクトを引数に取り、外部副作用を限定する設計です。

---

## 実運用・運用上の注意

- OpenAI / J-Quants など外部 API のコストとレート制限を考慮してください（モジュール内でレート制御・リトライを行いますが、設計上の限界はあります）。
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行います。CI やテストで不要な場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB による保存は ON CONFLICT を使用して冪等性を保つように設計されていますが、バックアップや監査要件に応じた運用を行ってください。
- ニュースのRSS取得は SSRF対策等を実装していますが、外部ソースの信頼性に依存するため扱いには注意してください。
- ETL の品質チェックは Fail-Fast にならない設計（問題を集めて報告）です。検出された品質問題に応じて呼び出し側で処理方針を決めてください。

---

この README はコード内の docstring を基に要点をまとめたものです。追加の実行スクリプト・CI 設定・パッケージ化情報（pyproject.toml / setup.cfg 等）がある場合は、それに従って環境を整備してください。