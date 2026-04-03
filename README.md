# KabuSys

日本株向け自動売買 / データ基盤ライブラリ（KabuSys）。  
ETL、データ品質チェック、ニュース収集・NLP、ファクター計算、監査ログ、J-Quants クライアント、そして市場レジーム判定などを提供します。

---

## 目次
- プロジェクト概要
- 主な機能一覧
- 動作環境・依存関係
- セットアップ手順
- 環境変数 (.env) と自動読み込み挙動
- 使い方（簡単なコード例）
- ディレクトリ構成
- 補足・運用上の注意

---

## プロジェクト概要
KabuSys は日本株のデータ基盤とリサーチ／自動売買周りのユーティリティ群を集めた Python パッケージです。  
主に以下用途を想定しています。

- J-Quants API からの差分 ETL（株価、財務、カレンダー）
- DuckDB を用いた時系列データ管理・品質チェック
- RSS ニュースの収集と前処理（SSRF 対策・追跡パラメータ除去）
- OpenAI を用いたニュースセンチメント解析（銘柄別 / マクロ）
- 市場レジーム（bull/neutral/bear）判定
- ファクター計算・特徴量探索（モメンタム、バリュー、ボラティリティ等）
- 注文→約定までの監査トレーサビリティ用スキーマ作成

設計方針として「ルックアヘッドバイアス回避」「冪等性」「フェイルセーフ（API失敗 = 続行）」を重視しています。

---

## 主な機能一覧
- data:
  - jquants_client: J-Quants からの取得・DuckDB への保存（差分 / ページネーション / トークン自動リフレッシュ）
  - pipeline / etl: 日次 ETL の実行（calendar / prices / financials）と ETL 結果クラス
  - quality: データ品質チェック（欠損、スパイク、重複、日付整合性）
  - calendar_management: 市場カレンダー管理と営業日判定ユーティリティ
  - news_collector: RSS 収集 + 前処理 + DB 保存（SSRF 対策、トラッキング除去）
  - audit: 注文・約定の監査スキーマ作成ユーティリティ
  - stats: zscore_normalize 等の共通統計ユーティリティ
- ai:
  - news_nlp.score_news: 銘柄別ニュースセンチメントを生成して ai_scores に保存
  - regime_detector.score_regime: ETF (1321) MA200 乖離とマクロニュース（LLM）を合成して market_regime に保存
- research:
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

---

## 動作環境・依存関係
- Python 3.10+
- 主要パッケージ（例）
  - duckdb
  - openai
  - defusedxml

（ネットワーク呼び出しは標準ライブラリ urllib を使用しているため追加の HTTP ライブラリは不要です）

例（インストール）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
```

プロジェクト配布形式に合わせて `pip install -e .` 等を使ってください。

---

## セットアップ手順

1. リポジトリをクローンし仮想環境を準備
   ```
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   pip install duckdb openai defusedxml
   ```

2. DuckDB / SQLite 用ディレクトリを用意（必要に応じて）
   - デフォルトでは `data/kabusys.duckdb` や `data/monitoring.db` を使用します。パスは環境変数で変更可能。

3. 環境変数の準備
   - 必須:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（ETL, jquants_client）
     - KABU_API_PASSWORD: kabu API を使う機能がある場合
   - 任意:
     - OPENAI_API_KEY: OpenAI API キー（ai.score_news / regime_detector を使う場合）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知に使う場合
     - DUCKDB_PATH / SQLITE_PATH / PID_FILE_PATH / KILL_FLAG_PATH / など
   - 例（.env）:
     ```
     JQUANTS_REFRESH_TOKEN=xxxx
     OPENAI_API_KEY=sk-...
     KABU_API_PASSWORD=...
     DUCKDB_PATH=data/kabusys.duckdb
     LOG_LEVEL=INFO
     KABUSYS_ENV=development
     ```

4. .env の自動読み込み
   - パッケージは起動時にプロジェクトルート（.git または pyproject.toml）を探し、`.env`→`.env.local` の順に自動読み込みします（OS 環境変数優先）。
   - 自動読み込みを無効化する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

---

## 使い方（簡易ガイド）

以下は代表的な呼び出し例です。実際はアプリケーション側で適宜組み合わせてください。

- DuckDB 接続と ETL の実行
```python
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント (銘柄単位) を作成
```python
from kabusys.ai.news_nlp import score_news
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")
print(f"書き込み銘柄数: {n_written}")
```

- 市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")
```

- 研究系ユーティリティ例
```python
from kabusys.research.factor_research import calc_momentum
from kabusys.data.stats import zscore_normalize
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026,3,20))
z = zscore_normalize(records, ["mom_1m", "mom_3m", "mom_6m"])
```

- 監査 DB 初期化
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# テーブルが作成された接続が返る
```

---

## 環境変数の注意点
- 必須: JQUANTS_REFRESH_TOKEN（ETL 実行に必要）
- OpenAI を使う機能は OPENAI_API_KEY が必要。関数には api_key 引数を渡してオーバーライド可能。
- config モジュールは自動で .env をロードします。テスト等で自動ロードを抑制したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- KABUSYS_ENV は "development" / "paper_trading" / "live" のいずれか。ログレベルは LOG_LEVEL。

---

## ディレクトリ構成（抜粋）
以下は src/kabusys 以下の主要ファイル・モジュールと簡単な説明です。

- src/kabusys/
  - __init__.py — パッケージ初期化、バージョン
  - config.py — 環境変数／.env 自動読み込み、Settings クラス
- src/kabusys/ai/
  - __init__.py
  - news_nlp.py — 銘柄別ニュースセンチメント生成（OpenAI 呼び出し・バッチ処理・検証）
  - regime_detector.py — ETF MA200 とマクロニュース（LLM）合成による市場レジーム判定
- src/kabusys/data/
  - jquants_client.py — J-Quants API クライアント（取得・保存・リトライ・レート制御）
  - pipeline.py / etl.py — ETL パイプライン、run_daily_etl 等
  - quality.py — データ品質チェック群（欠損・スパイク・重複・日付不整合）
  - calendar_management.py — 市場カレンダー管理、営業日判定ユーティリティ
  - news_collector.py — RSS 収集・前処理（SSRF 対策・ID 生成）
  - audit.py — 発注/約定の監査スキーマ初期化ユーティリティ
  - stats.py — zscore_normalize 等
  - etl.py — ETLResult の公開
- src/kabusys/research/
  - factor_research.py — モメンタム/バリュー/ボラティリティ計算
  - feature_exploration.py — 将来リターン計算、IC、統計サマリー
- そのほか：monitoring / execution / strategy 等のパッケージ（__all__ に含まれるが今回の抜粋により詳細は省略）

---

## 補足・運用上の注意
- ルックアヘッドバイアス防止: 多くのモジュールで date や target_date を明示的に受け取り、現在時刻参照を避ける設計になっています。バックテスト時は target_date を正しく指定してください。
- 冪等性: jquants_client.save_* や ETL の保存処理は基本的に ON CONFLICT を用いて冪等化されています。
- OpenAI 呼び出し:
  - レスポンスの堅牢な検証（JSON パース、キー検証、スコアのクリップ）を行います。
  - API エラーやタイムアウト時はフォールバック（0.0）やリトライを行い、例外は上位に波及しにくい設計です。
- RSS 収集: SSRF 対策（リダイレクト検査、プライベート IP ブロック）、受信サイズ制限、XML の DefusedXML を利用しています。

---

ご要望があれば、README に含める実際の .env.example のテンプレートや具体的な SQL スキーマ（DuckDB 用）・起動スクリプト例、CI/CD 用の簡易手順なども作成します。どの部分を詳細にしたいか教えてください。