# KabuSys

日本株向けの自動売買／データ基盤ライブラリ。  
ETL、ニュース収集・NLP（OpenAI 経由）、ファクター計算、監査ログなどのユーティリティを含み、バックテスト・運用の下位レイヤーとして使えるよう設計されています。

主な設計方針
- ルックアヘッドバイアスに注意したデータ取得/集計（内部で date.today() を直接参照しない等）
- DuckDB を主たるローカルデータストアとして利用
- J-Quants / OpenAI 等外部 API はリトライ・レート制限・トークンリフレッシュ対応
- 各処理は冪等性・フェイルセーフを重視（部分失敗を許容して他処理を継続）

バージョン: 0.1.0

---

## 機能一覧（抜粋）

- 環境設定読み込み
  - `.env` / `.env.local` / OS 環境変数を自動で読み込む（優先順: OS > .env.local > .env）
  - 自動ロード無効化: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
  - 必須設定チェック用の `kabusys.config.settings`

- データ ETL（J-Quants）
  - 株価日足、財務データ、JPX カレンダーの差分取得と DuckDB への保存（冪等）
  - レート制御、リトライ、ID トークン自動リフレッシュ

- データ品質チェック
  - 欠損・スパイク・重複・日付不整合の検出（QualityIssue を返す）

- ニュース収集
  - RSS 収集、URL 正規化、SSRF対策、記事テキスト前処理、raw_news / news_symbols への保存（冪等）

- ニュースNLP（OpenAI）
  - 銘柄別ニュースのバッチセンチメント評価（gpt-4o-mini を JSON モードで利用）
  - チャンク・リトライ・レスポンス検証付き

- 市場レジーム判定
  - ETF (1321) の 200 日 MA 乖離（70%）とマクロニュースセンチメント（30%）を合成して市場レジーム（bull/neutral/bear）を判定・保存

- 監査ログ（audit）
  - signal_events / order_requests / executions 等の監査テーブル定義と初期化ユーティリティ（DuckDB）

- リサーチ支援
  - モメンタム・ボラティリティ・バリュー等のファクター計算、将来リターン計算、IC 計算、Z スコア正規化 等

---

## 必要要件

- Python 3.10+
- ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
  - そのほか標準ライブラリ（urllib, json, logging 等）

（プロジェクトには pyproject.toml がある想定。実行環境に合わせて依存をインストールしてください。）

例:
```bash
python -m pip install "duckdb" "openai" "defusedxml"
# またはプロジェクトの pyproject.toml を利用して pip install -e .
```

---

## 環境変数 / .env

主要な環境変数（必須 / 任意）:

- 必須（ETL や API 呼び出しに必要）
  - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
  - KABU_API_PASSWORD: kabuステーション API のパスワード（発注等を使う場合）

- OpenAI / 通知
  - OPENAI_API_KEY: OpenAI API キー（score_news / regime 判定で必要）
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知（任意）

- DB / パス等（デフォルトが用意されています）
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db)
  - PID_FILE_PATH, KILL_FLAG_PATH 等の監視用設定

- 実行モード / ログ
  - KABUSYS_ENV: development / paper_trading / live (デフォルト development)
  - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL

自動ロードの挙動:
- OS 環境変数 > .env.local > .env の順で読み込みます。
- プロジェクトルートは `.git` または `pyproject.toml` を基準に自動検出。
- 自動ロードを無効にする: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

サンプル `.env`（最低限）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-....
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
LOG_LEVEL=INFO
KABUSYS_ENV=development
```

---

## セットアップ手順（ローカル実行向け）

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境作成（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 依存インストール
   - もし pyproject.toml / requirements.txt があればそれを使ってください。
   例:
   ```bash
   pip install -e .
   # または
   pip install duckdb openai defusedxml
   ```

4. 環境変数設定
   - `.env` または `.env.local` をプロジェクトルートに作成するか、OS 環境変数として設定します。
   - 必須: JQUANTS_REFRESH_TOKEN（ETL 実行時）、OPENAI_API_KEY（AI 機能利用時）

5. DuckDB の準備（任意）
   - デフォルトは data/kabusys.duckdb に接続します。必要ならディレクトリを作成してください。
   ```bash
   mkdir -p data
   ```

---

## 使い方（抜粋）

以下はライブラリ API の代表的な使い方例です。詳細は各モジュールの docstring を参照してください。

- 設定値参照
```python
from kabusys.config import settings
print(settings.duckdb_path)
```

- DuckDB 接続を作成して日次 ETL を実行
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュースセンチメントの生成（OpenAI API キー必要）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {n_written}")
```

- 市場レジーム判定（OpenAI API キー必要）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査 DB 初期化（監査専用 DB を作る）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# テーブルが作成され、UTC タイムゾーンが設定されます
```

- RSS フィードの取得（ニュースコレクタの低レベル関数）
```python
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
for a in articles:
    print(a["id"], a["title"], a["datetime"])
```

ログ出力やエラー処理は各関数内部で行われ、ETL 等の集約関数は結果オブジェクト（ETLResult 等）に状態をまとめます。

---

## よく使うモジュール一覧（ディレクトリ構成）

主要ファイル・モジュール（src/kabusys 配下）:

- kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・設定取得用（settings オブジェクト）
  - ai/
    - __init__.py
    - news_nlp.py
      - ニュースの集約・OpenAI によるセンチメント処理・ai_scores 書き込み
    - regime_detector.py
      - マクロセンチメントと ETF の MA 乖離を合成して market_regime を判定
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得 + DuckDB 保存関数）
    - pipeline.py
      - ETL パイプラインの実装（run_daily_etl 他）
    - etl.py
      - ETLResult 再エクスポート
    - news_collector.py
      - RSS 収集 / 前処理 / 保存ロジック（SSRF 対策・XML 安全化）
    - calendar_management.py
      - JPX カレンダーの扱い、営業日判定等
    - stats.py
      - zscore_normalize 等の汎用統計ユーティリティ
    - quality.py
      - データ品質チェック（欠損・スパイク・重複・日付整合性）
    - audit.py
      - 監査ログテーブル定義・初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py
      - momentum / value / volatility ファクター計算
    - feature_exploration.py
      - 将来リターン計算、IC、統計サマリー等

（パッケージは戦略層・実行層も想定されていますが、今回のコードベースには data / ai / research 周りが中心に含まれています。）

---

## 開発・貢献

- コードにドキュメンテーションが豊富に含まれているため、モジュールの docstring を参照してください。
- 単体テストや CI がある場合はそれに従ってください（この README にはテスト手順を含めていません）。
- 新しい機能やバグ修正は PR を受け付けます。設計方針（冪等性・フェイルセーフ・ルックアヘッド防止）を尊重してください。

---

## 注意事項 / 運用上のヒント

- OpenAI / J-Quants のキーは秘密情報です。Git にコミットしないでください。
- 本パッケージの AI 処理は外部 API に依存し、使用量・コストに注意してください。
- ライブ取引（kabu API 等）に接続する際は、環境を十分に分離（paper_trading/live の切替、ログレベルなど）し、監査ログ・冪等キーを活用して二重発注等を防いでください。
- DuckDB への executemany の空リストバインド等、特定バージョンに依存する挙動に注意しています（pipeline 等で空リストは事前チェックされています）。

---

必要があれば、README に以下を追記できます:
- .env.example の完全なテンプレート
- CI / テスト手順
- 詳しい API リファレンス（関数一覧と引数の説明）
- デプロイ / 運用ガイド（systemd サービス例や監視設定）

ご希望あればそれらを追加します。