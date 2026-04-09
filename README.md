# KabuSys

日本株の自動売買・データプラットフォーム用ライブラリです。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP スコアリング（OpenAI）、ファクター計算、監査ログ、マーケットカレンダー管理などの機能を備え、運用／研究／戦略実装の基盤を提供します。

---

## 主な特徴

- データプラットフォーム（ETL）
  - J-Quants API からの株価（OHLCV）、財務データ、JPX カレンダー取得
  - 差分取得、ページネーション対応、レートリミット・再試行ロジック
  - データ保存は DuckDB に対する冪等（ON CONFLICT DO UPDATE）

- ニュース収集・NLP
  - RSS 取得（SSRF 対策、トラッキング除去、前処理）
  - OpenAI（gpt-4o-mini）を使った銘柄別センチメントスコアリング（news_nlp）
  - マクロニュースを統合した市場レジーム判定（regime_detector）

- 研究用ユーティリティ
  - ファクター計算（モメンタム、バリュー、ボラティリティ等）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
  - クロスセクション Z スコア正規化

- データ品質チェック
  - 欠損、スパイク、重複、日付不整合の検出（品質チェックを集約実行可能）

- 監査ログ（トレーサビリティ）
  - signal → order_request → execution の階層を保持する監査テーブル群
  - 監査 DB 初期化ユーティリティ（DuckDB）

- 設定管理
  - .env / .env.local / OS 環境変数から設定を読み込む自動ロード機能（無効化可）

---

## 必要条件

- Python 3.10 以上（型注釈で | 演算子等を使用）
- 推奨パッケージ（代表例）
  - duckdb
  - openai
  - defusedxml

インストール例（プロジェクトに requirements.txt がある場合）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

最低限個別に入れる場合:
```bash
pip install duckdb openai defusedxml
```

---

## 環境変数 / 設定

プロジェクトは .env / .env.local をプロジェクトルートから自動読み込みします（OS環境変数が優先）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主要な環境変数（抜粋）:

- J-Quants / データ取得
  - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- kabu ステーション API
  - KABU_API_PASSWORD: kabu API のパスワード（必須）
  - KABU_API_BASE_URL: デフォルト http://localhost:18080/kabusapi
- OpenAI
  - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）
- LINE 通知（任意）
  - LINE_CHANNEL_ACCESS_TOKEN
  - LINE_USER_ID
- データベースパス
  - DUCKDB_PATH: デフォルト data/kabusys.duckdb
  - SQLITE_PATH: 監視用 sqlite デフォルト data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: Paper trading 用 DB（デフォルト data/paper_trading.db）
- 運用設定・監視
  - PID_FILE_PATH / KILL_FLAG_PATH / CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT など
- 実行環境フラグ
  - KABUSYS_ENV: development | paper_trading | live
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL

サンプル .env（例）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=secret
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（開発用）

1. リポジトリをクローン
2. 仮想環境を作成・有効化
3. 必要なライブラリをインストール（上記参照）
4. プロジェクトルートに `.env` を作成して必要な環境変数を設定
5. DuckDB ファイルやディレクトリ（例: data/）が必要なら作成

例:
```bash
git clone <repo-url>
cd <repo>
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
mkdir -p data
cp .env.example .env
# .env を編集してトークン等を設定
```

---

## 使い方（主要ユースケース）

以下はライブラリを Python から直接利用する簡単な例です。詳細は各モジュールのドキュメント（ソース内 docstring）を参照してください。

- DuckDB 接続を作成して日次 ETL を実行:
```python
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースのセンチメントスコアを算出して ai_scores テーブルへ書き込む:
```python
from datetime import date
import duckdb
from kabusys.ai import score_news

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使用
print(f"written {n_written} scores")
```

- 市場レジーム判定を実行:
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026,3,20), api_key=None)
```

- 監査ログ用 DuckDB を初期化:
```python
from kabusys.data.audit import init_audit_db
from pathlib import Path

conn = init_audit_db(Path("data/audit.duckdb"))
# これで監査用テーブルが作成されます
```

- ファクター計算（研究用）:
```python
from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, date(2026,3,20))
value = calc_value(conn, date(2026,3,20))
vol = calc_volatility(conn, date(2026,3,20))
```

---

## よくある操作／トラブルシューティング

- OpenAI 呼び出しが失敗する場合:
  - OPENAI_API_KEY を正しく設定しているか確認
  - ネットワークや API レート制限、レスポンス形式（JSON モード）に依存するためログ確認
  - news_nlp と regime_detector は API 失敗時にはフェイルセーフ（スコア=0）で継続する設計

- .env が読み込まれない:
  - プロジェクトルートが .git または pyproject.toml を基準に判定されます。パッケージ配布後は自動ロードがスキップされる場合があります。
  - 自動ロードを無効にしているか（KABUSYS_DISABLE_AUTO_ENV_LOAD）を確認

- DuckDB の接続・テーブルが見つからない:
  - 必要なテーブルは ETL や init 関数で作成される想定です。スキーマ初期化（audit など）を呼び出しているか確認

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                           — 環境変数 / 設定管理
- ai/
  - __init__.py                        — score_news を公開
  - news_nlp.py                         — ニュース NLP スコアリング
  - regime_detector.py                  — マーケットレジーム判定
- data/
  - __init__.py
  - jquants_client.py                   — J-Quants API クライアント（取得・保存）
  - pipeline.py                         — ETL パイプライン（run_daily_etl 等）
  - etl.py                              — ETL の公開再エクスポート
  - news_collector.py                   — RSS 収集・前処理
  - calendar_management.py              — マーケットカレンダー管理（営業日判定等）
  - quality.py                          — データ品質チェック
  - stats.py                            — 統計ユーティリティ（zscore 等）
  - audit.py                            — 監査ログテーブルの初期化
- research/
  - __init__.py
  - factor_research.py                  — ファクター計算（momentum/value/volatility）
  - feature_exploration.py              — forward returns / IC / factor summary
- ai/、research/ 以下は研究・AI 関連のユーティリティ群

（上記はリポジトリ内の主要モジュールを抜粋したものです。詳しくは各ファイルの docstring を参照してください。）

---

## 貢献・拡張

- 新しい ETL ソースを追加する場合は `kabusys.data.jquants_client` の設計を踏襲し、fetch/save のペアを実装してください。
- ニュースソースを追加する場合は `news_collector.fetch_rss` を利用し、news_symbols 連携を行ってください。
- OpenAI 呼び出し部分はテストのためモック可能な設計になっています（内部の _call_openai_api を差し替え可能）。

---

README は簡易ガイドです。各モジュールの詳細な仕様・設計意図はソースコード内の docstring（英語/日本語混在）に記載しています。運用する際は環境変数と DB のパス、API トークンの管理に注意してください。