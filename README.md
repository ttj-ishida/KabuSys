# KabuSys

日本株向けのデータパイプライン・リサーチ・自動化支援ライブラリ。  
DuckDB を中心としたデータ格納・ETL、J-Quants API クライアント、ニュースの NLP スコアリング、マーケットレジーム判定、リサーチ用ファクター計算、データ品質チェックや監査ログ初期化など、投資アルゴリズム開発・運用に必要な中核処理を提供します。

現在のバージョン: 0.1.0

---

## 特徴（機能一覧）

- 環境設定管理
  - .env ファイルの自動読み込み（プロジェクトルート検出、上書き制御、OS環境変数保護）。
- Data ETL（J-Quants 統合）
  - J-Quants API から株価（OHLCV）/財務/マーケットカレンダーの差分取得と DuckDB への冪等保存。
  - ETL の上位エントリポイント（日次 ETL 実行）と個別 ETL（prices / financials / calendar）。
  - レートリミッタ、リトライ、401 リフレッシュ対応を備えた堅牢な API クライアント。
- ニュース収集・前処理
  - RSS 取得（SSRF 対策・リダイレクト検査・受信サイズ制限・URL 正規化）と raw_news への冪等保存（記事ID は正規化URLのハッシュ）。
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュースを統合して LLM に投げ、センチメント（ai_scores）を計算・書き込み。
  - リトライ / レスポンス検証 / スコアクリップなどフェイルセーフ設計。
- 市場レジーム判定
  - ETF（1321）の 200 日移動平均乖離とマクロ系ニュースセンチメントを合成して日次レジーム（bull/neutral/bear）を算出・保存。
- 研究（Research）ユーティリティ
  - モメンタム / ボラティリティ / バリュー系ファクター計算。
  - 将来リターン計算、IC（Information Coefficient）、ファクターの統計サマリ、Zスコア正規化。
- データ品質チェック
  - 欠損・スパイク・重複・日付不整合チェックを実装。QualityIssue を返して呼び出し側で方針決定可能。
- 監査ログ初期化
  - signal / order_request / executions を含む監査スキーマを DuckDB に冪等作成するヘルパー。
- マーケットカレンダー管理
  - DB ベースの営業日判定・前後営業日取得・カレンダー差分更新ジョブを提供。

---

## セットアップ

前提
- Python 3.10+（typing 記法や型アノテーションに依存）
- DuckDB、OpenAI クライアントなどの外部ライブラリが必要

推奨手順（例）

1. リポジトリをクローン
   git clone <リポジトリ URL>
   cd <repo>

2. 仮想環境の作成と有効化
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows (PowerShell では Activate.ps1)

3. 必要パッケージをインストール
   pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject.toml がある場合はそれを使用してください）
   pip install -e .

4. 環境変数設定
   プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

必須の環境変数（例）
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（ETL 用）
- KABU_API_PASSWORD: kabuステーション API パスワード（発注系）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector）
- 他（オプション）
  - KABUSYS_ENV: development | paper_trading | live（デフォルト development）
  - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL
  - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH（監視 DB デフォルト data/monitoring.db）
  - PID_FILE_PATH / KILL_FLAG_PATH 等の監視用パス

.sample .env（例）
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-xxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## 使い方（主要な API 利用例）

以下は Python REPL / スクリプトから呼ぶ想定の例です。各関数は DuckDB の接続オブジェクト（duckdb.connect(...) の戻り値）を受け取ります。

1) DuckDB 接続を開く
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

2) 日次 ETL を実行する
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# target_date を指定せずに実行すると本日を対象（ただし ETL 内で営業日調整あり）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

3) ニュース NLP（銘柄ごとの AI スコア）を実行する
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OpenAI API キーを環境変数で設定している場合は api_key を省略可
written_count = score_news(conn, target_date=date(2026, 3, 20))
print(f"written {written_count} codes")
```

4) 市場レジーム判定を実行する
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

5) 監査ログ DB の初期化（監査専用 DB を作る例）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# audit_conn を使って監査テーブルにアクセスできます
```

6) 研究系ユーティリティ（ファクター計算）
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum

records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は各銘柄の辞書リスト
```

注意事項
- OpenAI 呼び出しは API キー（OPENAI_API_KEY）が必要です。関数は api_key 引数を受け取るものもあり、テスト用に注入可能です。
- ETL / API 呼び出しは外部ネットワーク・課金が発生します。必ずテスト環境で動作確認を行ってください。
- 各処理はルックアヘッドバイアス対策（target_date 未満のデータ限定等）を意識して実装されています。バックテスト等での利用時は設計方針を遵守してください。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
  - パッケージのエントリポイント。公開サブパッケージを定義。

- config.py
  - 環境変数 / .env 読み込み・設定管理。settings オブジェクトを通じてアクセス。

- ai/
  - __init__.py
  - news_nlp.py: ニュースを用いた銘柄センチメントスコア算出（OpenAI 利用）。
  - regime_detector.py: ETF MA とマクロニュースを組み合わせた市場レジーム判定。

- data/
  - __init__.py
  - calendar_management.py: JPX カレンダー取得・営業日判定ロジック。
  - etl.py: ETL 関連の公開インターフェース（ETLResult 再エクスポート）。
  - pipeline.py: ETL パイプライン（差分取得・保存・品質チェック）。
  - stats.py: Zスコアなど統計ユーティリティ。
  - quality.py: データ品質チェック（欠損・スパイク・重複・日付不整合）。
  - audit.py: 監査ログスキーマ作成・初期化ユーティリティ。
  - jquants_client.py: J-Quants API クライアント（取得 + DuckDB への保存関数）。
  - news_collector.py: RSS 取得・前処理・保存ユーティリティ。

- research/
  - __init__.py
  - factor_research.py: Momentum / Volatility / Value などのファクター計算。
  - feature_exploration.py: 将来リターン計算、IC、統計サマリー、ランク関数。

（上記以外に strategy / execution / monitoring 等のサブパッケージが想定されていますが、ここに示したのは現在のコードベースに含まれる主要モジュールです。)

---

## テスト & 開発メモ

- 環境変数自動読み込みは、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定することで無効化できます。ユニットテスト時に .env の自動読み込みを抑止したい場合に便利です。
- OpenAI 呼び出し部分は内部で _call_openai_api 的な関数を用意しており、unit test では patch による差し替えが容易です。
- J-Quants クライアントは rate limiting、リトライ、トークン自動リフレッシュを備えています。実際の API を叩くテストはモックや API 連携用のインテグレーションテストとして分離してください。
- DuckDB の executemany はバージョン依存の挙動（空リスト不可など）があるため、実装で保護されています。DuckDB のバージョンを上げる場合は互換性テストを推奨します。

---

## 連絡 / 貢献

バグ報告やプルリクエストはリポジトリの Issue / PR を使用してください。  
設計方針に関する議論（Look-ahead-bias 対策、冪等性、監査要件など）はドキュメント化の上で合意を取ることを推奨します。

---

以上。必要であれば README に含めるサンプル .env.example や具体的な CLI スクリプト例（ETL の cron 設定例など）も作成しますので、その場合は用途（運用 or 開発）を教えてください。