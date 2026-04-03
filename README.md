# KabuSys

日本株向けの自動売買・データ基盤ライブラリ群です。ETL、ニュース収集・NLP、因子計算、監査ログ、J-Quants / kabuAPI クライアント等のユーティリティを含み、研究（Research）・本番（Execution）・監視（Monitoring）用途を想定しています。

主な設計方針
- Look‑ahead bias（未来情報参照）を防ぐ実装（内部で date.today()/datetime.today() を直接参照しない等）
- DuckDB を中心としたローカルデータ格納と冪等性（ON CONFLICT / DELETE→INSERT）
- 外部 API 呼び出し時の堅牢性（リトライ、バックオフ、レートリミット）
- セキュリティ考慮（RSS の SSRF 防止、XML パースの defusedxml 使用）
- テスト容易性（API 呼び出し箇所を差し替え可能に設計）

---

## 機能一覧

- 環境変数 / 設定読み込み
  - `.env` / `.env.local` の自動読み込み（ルート検出は .git / pyproject.toml ベース）
  - settings オブジェクトで各種設定を取得
- データETL（kabusys.data.pipeline）
  - J-Quants からの差分取得（株価・財務・カレンダー）
  - 保存（DuckDB に冪等保存）
  - 品質チェック（欠損、スパイク、重複、日付整合性）
  - 日次 ETL の統合実行（run_daily_etl）
- J-Quants クライアント（kabusys.data.jquants_client）
  - 認証（refresh_token → id_token）
  - ページネーション対応のデータ取得（daily_quotes / financials / market_calendar / listed info）
  - DuckDB への保存ユーティリティ（raw_prices / raw_financials / market_calendar）
  - レートリミット / リトライ / 401 自動リフレッシュ等の実装
- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得、前処理、raw_news への冪等登録
  - URL 正規化・トラッキングパラメータ削除、SSRF 防止、XML の安全パース
- ニュース NLP（kabusys.ai.news_nlp）
  - OpenAI（gpt-4o-mini）を用いた銘柄単位のニュースセンチメント集計・スコア保存
  - ウィンドウ/トリミング・バッチ化・リトライ・レスポンスバリデーション実装
- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の MA200 乖離（70%）とマクロニュースセンチメント（30%）を合成
  - OpenAI 呼び出し・失敗時フェイルセーフ等
- 研究ユーティリティ（kabusys.research）
  - ファクター計算（momentum / value / volatility）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ
  - z-score 正規化ユーティリティ（kabusys.data.stats）
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions 等の監査テーブル定義・初期化
  - init_audit_db で専用 DuckDB を初期化
- データ品質チェック（kabusys.data.quality）
  - 欠損・スパイク・重複・日付不整合の検出と QualityIssue でのレポート

---

## セットアップ手順

前提
- Python 3.9+（typing の新構文・DuckDB・openai 等を想定）
- DuckDB をローカルで利用（ファイルまたは :memory:）

1. リポジトリをチェックアウト
   - 例: git clone <repo>

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール
   - 必要な主なパッケージ:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject.toml があればそちらを使用してください）

4. 環境変数 / .env の準備
   - プロジェクトルートに `.env` または `.env.local` を置くと自動読み込みされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 最低限設定したい変数:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
   - AI 機能を使う場合:
     - OPENAI_API_KEY=...
   - 任意:
     - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - KABUSYS_ENV (development / paper_trading / live) — デフォルト development
     - LOG_LEVEL (DEBUG / INFO / WARNING / ERROR / CRITICAL)

5. データディレクトリの作成（必要なら）
   - 例: mkdir -p data

---

## 使い方（主要なサンプル）

※ 以下は Python REPL やスクリプト内での利用例です。

設定確認・DB 接続
```python
from kabusys.config import settings
import duckdb

print(settings.jquants_refresh_token)  # 必須トークンの読み出し（未設定だと ValueError）
conn = duckdb.connect(str(settings.duckdb_path))
```

日次 ETL の実行
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# ETL を実行（target_date を省略すると今日）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

ニューススコアリング（OpenAI を利用）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# API キーは引数で渡すか環境変数 OPENAI_API_KEY を設定
n_written = score_news(conn, target_date=date(2026,3,20), api_key=None)
print("scored:", n_written)
```

市場レジーム判定
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026,3,20))
```

監査DB 初期化（監査専用 DB を作る）
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# テーブルが作成された接続が返る
```

ファクター計算（研究用）
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum

records = calc_momentum(conn, target_date=date(2026,3,20))
# records: [{"date": ..., "code": "1301", "mom_1m": ..., "ma200_dev": ...}, ...]
```

品質チェック
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=None)
for i in issues:
    print(i)
```

環境変数自動読み込みの無効化（テスト等）
```bash
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

---

## 設計上の注意点 / 実装ポリシー（抜粋）

- Look‑ahead を防ぐため、target_date を明示的に渡す設計。内部で現在時刻を直接参照する関数は最小化。
- ETL / 保存は冪等（ON CONFLICT）を基本とし、部分失敗が起きても既存データを過度に上書きしない。
- 外部 API 呼び出しは：
  - レート制限（J-Quants は 120 req/min）を守る仕組み
  - リトライ（指数バックオフ）
  - 401 はトークンリフレッシュして 1 回再試行
- ニュース収集は SSRF、XML BOM 等に注意し安全パース・ホスト検査を実施
- OpenAI 呼び出し時は JSON モードレスポンスを期待し、パース失敗時はフェイルセーフとして 0.0 を返す等の堅牢性を持たせる

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py                      — 環境変数 / settings 管理（.env 自動読み込み）
- ai/
  - __init__.py
  - news_nlp.py                   — ニュース NLP（OpenAI）センチメント、score_news
  - regime_detector.py            — 市場レジーム判定、score_regime
- data/
  - __init__.py
  - jquants_client.py             — J-Quants API クライアント、保存ロジック
  - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
  - etl.py                        — ETLResult 再エクスポート
  - news_collector.py             — RSS 収集・前処理・raw_news 保存
  - calendar_management.py        — 市場カレンダー管理（is_trading_day 等）
  - quality.py                    — データ品質チェック
  - stats.py                      — zscore_normalize 等
  - audit.py                      — 監査ログテーブル定義・初期化
- research/
  - __init__.py
  - factor_research.py            — momentum / value / volatility 計算
  - feature_exploration.py        — forward returns, IC, rank, factor_summary
- research、ai、data の下にテスト可能なユーティリティがまとまっています

---

## 環境変数の主な一覧

必須（使用する機能により必須項目が異なります）
- JQUANTS_REFRESH_TOKEN — J-Quants の refresh token（ETL 実行・データ取得に必須）
- KABU_API_PASSWORD — kabu API を使う場合に必要

任意 / 機能により必要
- OPENAI_API_KEY — AI（news_nlp / regime_detector）を使う場合
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知連携
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV — environment: development / paper_trading / live（デフォルト development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）

自動 .env 読み込みはプロジェクトルート（.git か pyproject.toml の存在する親）を基準に行われます。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## テスト & 開発

- モジュール内の外部呼び出し（OpenAI / urllib / J‑Quants）は差し替え可能な設計になっています（テスト時は patch してモック可能）。
- ニュース NLP / Regime Detector の OpenAI 呼び出し箇所は内部関数をモックしてユニットテストを作成してください。
- DuckDB を用いた統合テストは :memory: 接続でも可能です（init_audit_db(":memory:") など）。

---

## ライセンス / 貢献

（この README ではソースリポジトリの LICENSE を参照してください。貢献の手順や PR ポリシーはリポジトリルートの CONTRIBUTING.md をご確認ください。）

---

README に記載の内容や API の使い方について質問があれば、実例コードや具体的なユースケース（ETL のスケジュール、OpenAI のレスポンス処理、監査ログの運用など）に合わせて追記します。