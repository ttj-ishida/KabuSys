# KabuSys

日本株向けの自動売買／データ基盤ライブラリセットです。  
ETL による市場データ取得（J-Quants）、ニュース収集・NLP（OpenAI）、ファクター計算、品質チェック、監査ログ、研究用ユーティリティ等を含みます。モジュール設計はルックアヘッドバイアス対策・冪等性・堅牢なエラー処理を重視しています。

バージョン: 0.1.0

---

## 主な機能

- 環境変数・設定管理
  - プロジェクトルートの `.env` / `.env.local` 自動読み込み（無効化可能）
  - 必須設定の簡易取得 API（`kabusys.config.settings`）
- データプラットフォーム（data）
  - J-Quants API クライアント（レート制御、リトライ、トークン自動更新）
  - ETL パイプライン（差分取得・バックフィル・品質チェック）
  - 市場カレンダー管理（営業日判定、カレンダー更新ジョブ）
  - ニュース収集（RSS、SSRF 防御、テキスト前処理）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログ（signal → order → execution のトレーサビリティ用スキーマ）
  - 汎用統計ユーティリティ（Z スコア正規化等）
- 研究用ツール（research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）等の解析ユーティリティ
- AI モジュール（ai）
  - ニュースセンチメントスコアリング（OpenAI, JSON mode）
  - 市場レジーム判定（ETF MA200 とマクロニュースの組成）
  - OpenAI 呼び出しはリトライ / フォールバック設計
- 監視・実行・戦略層（パッケージの公開範囲には存在を示すが実装はモジュール群に依存）
  - パッケージ外部からの戦略・約定処理を想定した監査・発注ログ基盤

---

## 動作環境・前提

- Python 3.10+
- DuckDB（Python パッケージとしてインストール）
- OpenAI API キー（AI モジュールを使う場合）
- J-Quants のリフレッシュトークン（データ取得に必要）
- ネットワークアクセス（J-Quants API、RSS、OpenAI）

---

## 必要な環境変数

以下は主要な環境変数（.env に記載して運用）:

- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（省略時: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用ボットトークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- DUCKDB_PATH: DuckDB データベースパス（省略時: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（省略時: data/monitoring.db）
- KABUSYS_ENV: 環境 ("development" | "paper_trading" | "live")（省略時: development）
- LOG_LEVEL: ログレベル ("DEBUG","INFO",...)（省略時: INFO）

自動で `.env` / `.env.local` を読み込む機能が有効になっています。無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

サンプル（.env）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=~/kabusys/data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをクローン
   - 省略（既にコードベースが手元にある前提）

2. Python 仮想環境を作成・有効化（例: venv）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール
   - プロジェクトが pyproject.toml / requirements を持つ想定で、編集済みの環境に合わせて:
   ```
   pip install -U pip setuptools
   pip install -e .
   ```
   - duckdb, openai, defusedxml などが必要です。ローカルに requirements.txt があれば:
   ```
   pip install -r requirements.txt
   ```

4. 環境変数設定
   - プロジェクトルートの `.env` / `.env.local` に必要項目を記載（上のサンプル参照）。
   - テストや CI で自動読み込みを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

---

## 基本的な使い方（コード例）

共通前提:
```
from datetime import date
import duckdb
from kabusys.config import settings
```

- DuckDB 接続（設定に従う）
```
conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL 実行
```
from kabusys.data.pipeline import run_daily_etl

target = date(2026, 3, 20)
result = run_daily_etl(conn, target)
print(result.to_dict())
```

- ニューススコアリング（OpenAI 必須）
```
from kabusys.ai.news_nlp import score_news

# OPENAI_API_KEY は環境変数でも渡せます
count = score_news(conn, date(2026, 3, 20), api_key=None)
print(f"scored {count} codes")
```

- 市場レジーム判定
```
from kabusys.ai.regime_detector import score_regime

score_regime(conn, date(2026, 3, 20), api_key=None)
```

- 監査データベース初期化（監査ログ専用 DB を作る）
```
from kabusys.data.audit import init_audit_db
db_conn = init_audit_db("data/audit.duckdb")
```

- 研究用ファクター計算例
```
from kabusys.research.factor_research import calc_momentum
records = calc_momentum(conn, date(2026, 3, 20))
# 正規化
from kabusys.data.stats import zscore_normalize
normed = zscore_normalize(records, ["mom_1m", "mom_3m", "mom_6m"])
```

注意点:
- AI 系機能は OpenAI の JSON mode を使い、稀なエラーやレスポンスパース失敗に対してフォールバックする設計です（失敗時はスコア 0.0 やスキップ）。
- ETL・保存は冪等性（ON CONFLICT DO UPDATE）を考慮して実装されています。
- テスト時は各モジュール内の API 呼び出し関数（例: `_call_openai_api`, `_urlopen` 等）をモックすることで外部依存を切り離せます。

---

## 典型的なワークフロー

1. 日次バッチ（cron）で:
   - run_daily_etl() を実行して J-Quants からデータを取得・保存
   - calendar_update_job() で市場カレンダーを更新

2. 夜間または朝に:
   - news_collector で RSS を収集して raw_news を更新
   - score_news() で各銘柄のニュースセンチメントを算出して ai_scores に保存
   - score_regime() で市場全体のレジーム判定を保存

3. 戦略側:
   - research のファクター群を使ってシグナル生成
   - 発注の監査ログを order_requests / executions テーブルに残す

---

## ディレクトリ構成（概要）

以下は主要ファイル・モジュールと役割の一覧（src/kabusys 配下）:

- __init__.py
  - パッケージのエクスポート（data, strategy, execution, monitoring）
- config.py
  - 環境変数読み込み、Settings オブジェクト
- ai/
  - __init__.py
  - news_nlp.py: ニュースの集約・OpenAI によるセンチメント解析・結果保存ロジック
  - regime_detector.py: ETF MA200 とマクロニュースで市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py: J-Quants API クライアント（fetch / save 関数）
  - pipeline.py: ETL パイプライン（run_daily_etl 等）
  - etl.py: ETL インタフェース再エクスポート
  - calendar_management.py: 市場カレンダー管理、営業日判定ユーティリティ
  - news_collector.py: RSS 収集・前処理・保存
  - quality.py: データ品質チェック（欠損/スパイク/重複/日付不整合）
  - stats.py: 汎用統計ユーティリティ（zscore_normalize 等）
  - audit.py: 監査ログテーブル定義と初期化
- research/
  - __init__.py
  - factor_research.py: モメンタム・ボラティリティ・バリューの算出
  - feature_exploration.py: 将来リターン計算、IC、統計サマリー等
- その他（strategy, execution, monitoring）
  - パッケージ公開対象に含まれているが、具体的な実装は環境による（プロジェクト拡張点）

---

## テスト・開発時の注意点

- 自動環境変数読み込みが有効になっているため、テスト中に環境を固定したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI / J-Quants / HTTP 呼び出し部分はリトライやフォールバックがあるものの、ユニットテストでは外部呼び出しをモックしてください（モジュール内部でモック対象の関数が明示されています）。
- DuckDB の executemany は空リストを受け付けないバージョンがあるため、パラメータが空の場合には呼び出しをスキップする実装になっています（既にコードに反映済み）。

---

もし README に追加したい内容（例: CI 設定、docker-compose、具体的な SQL スキーマ、運用手順、例の .env.example ファイル等）があれば教えてください。必要に応じて、導入ガイドや API リファレンスの自動生成向けドキュメントも作成できます。