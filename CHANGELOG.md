# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
バージョン番号はパッケージの __version__（src/kabusys/__init__.py）に合わせています。

全般的な設計方針（本リリースに共通）
- ルックアヘッドバイアスを避けるため、datetime.today()/date.today() をスコア計算等の内部ロジックで直接参照しない設計。
- DuckDB をデータ層に採用。ETL・集計・調査処理は基本的に DuckDB クエリで完結するよう設計。
- 外部 API 呼び出し（特に OpenAI / J-Quants）はフェイルセーフ（失敗時のデフォルト値や部分書き込み保護）を備える。
- DB 書き込みは可能な限り冪等性（DELETE→INSERT / ON CONFLICT）とトランザクションで保護。
- テストしやすさを考慮して API 呼び出し等は差し替え可能に実装（内部 _call_openai_api を patch 可能など）。

## [0.1.0] - 2026-03-28

Added
- 基本パッケージ構成を追加（src/kabusys）。
  - パッケージバージョン: 0.1.0
  - public API: kabusys.data / kabusys.research / kabusys.ai 等を公開。

- 環境設定管理（src/kabusys/config.py）
  - .env ファイルおよび OS 環境変数の読み込み機能を追加。
  - プロジェクトルート探索ロジックを実装（.git または pyproject.toml を基準）。
  - .env の自動読み込み順序: OS環境 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
  - .env 行パーサを実装（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント対応）。
  - Settings クラスを提供し、J-Quants/OpenAI/Slack/データベースパス/ログレベル/環境種別等のプロパティを取得可能に。

- ニュースNLP（src/kabusys/ai/news_nlp.py）
  - raw_news / news_symbols を集約して銘柄別に記事をまとめ、OpenAI（gpt-4o-mini）で銘柄ごとのセンチメント（-1.0～1.0）を算出する処理を実装。
  - バッチ処理（最大 20 銘柄/リクエスト）、トークン肥大化抑制（記事数・文字数トリム）、JSON Mode の応答バリデーションを実装。
  - リトライ（429・ネットワーク断・タイムアウト・5xx）と指数バックオフ実装。API失敗時は該当チャンクをスキップして処理継続するフェイルセーフを採用。
  - レスポンスの堅牢なパースおよび検証ロジックを追加（余分な前後テキストから {} を抽出するなど）。
  - DuckDB への書き込みは、取得成功コードのみに対して DELETE → INSERT を行い、部分失敗時に既存データを保護。

- 市場レジーム判定（src/kabusys/ai/regime_detector.py）
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定する機能を実装。
  - マクロニュースは news_nlp.calc_news_window によるウィンドウで抽出し、OpenAI で macro_sentiment を算出。API失敗時は macro_sentiment = 0.0 のフォールバック。
  - OpenAI 呼び出しごとにリトライ（RateLimit/APIConnection/APITimeout/5xx）とエクスポネンシャルバックオフを備える。JSON 解析失敗時も安全に 0.0 を返す。
  - 計算結果は market_regime テーブルへトランザクション（BEGIN / DELETE / INSERT / COMMIT）で冪等的に保存。書込み失敗時は ROLLBACK を試行して上位へ例外を伝播。

- データ/カレンダー管理（src/kabusys/data/calendar_management.py）
  - JPX マーケットカレンダー管理ロジックを実装（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
  - market_calendar が未取得の場合の曜日ベースのフォールバックを実装（週末は非営業日扱い）。
  - next/prev の探索は最大 _MAX_SEARCH_DAYS（安全上の上限）を設け無限ループを防止。
  - calendar_update_job: J-Quants から差分取得し market_calendar を冪等保存。バックフィルや健全性チェック（将来日付の異常検出）を実装。

- ETL パイプライン（src/kabusys/data/pipeline.py / src/kabusys/data/etl.py）
  - ETLResult データクラスを追加し、ETL 実行結果（取得/保存件数、品質問題、エラー）を集約。
  - 差分更新・バックフィル・品質チェックの方針とユーティリティ関数（テーブル存在確認・最大日付取得）を実装。
  - etl モジュールは pipeline.ETLResult を再エクスポート。

- リサーチ（src/kabusys/research/*.py）
  - factor_research:
    - モメンタム（1M/3M/6M）、200日移動平均乖離、ATR（20日）、20日平均売買代金、出来高比率などのファクター計算を実装。
    - DuckDB 内で SQL を用いた効率的なウィンドウ集計を採用。データ不足時は None を返す等の堅牢性を確保。
  - feature_exploration:
    - 将来リターン calc_forward_returns（可変ホライズン対応、入力検証あり）。
    - IC（calc_ic）: Spearman ランク相関の実装（同順位は平均ランク）。
    - 統計サマリー（factor_summary）: count/mean/std/min/max/median を計算。
    - rank ユーティリティ: ties の扱い（平均ランク）と丸め対策（round 12 桁）を実装。
  - research パッケージは zscore_normalize を data.stats から再公開し、上記関数群を __all__ で公開。

- その他
  - ai/__init__.py, research/__init__.py における公開 API の整理（__all__ 指定）。
  - 一部モジュールでのロギング強化（info/debug/warning/exception の活用）。
  - OpenAI クライアント呼び出しを各モジュール内に独立実装し、モジュール間でプライベート関数を共有しない設計（テスト時の差し替え容易化）。

Fixed
- OpenAI レスポンス周りの堅牢性向上
  - JSON パース失敗時の復元ロジック、HTTP 5xx/タイムアウト系のリトライ、RateLimit の扱いを明確化してフェイルセーフを実装。
- DuckDB への executemany 空リスト問題への対処
  - DuckDB 0.10 系で executemany に空リストを渡すと失敗するため、書き込み前に空チェックを行うよう修正（news_nlp と score_news の書き込み処理）。
- 環境変数ローダーの堅牢化
  - .env の読み込みに失敗した場合に警告を出すようにし、読み込み関数が例外を投げないように変更。
  - .env 行のパースでクォート・エスケープ・コメント処理を実装し、より多様な .env フォーマットに対応。

Security
- 環境変数上書き時に OS 環境変数を保護する機構を追加（protected set により .env.local/.env が既存の OS 環境変数を上書きしないよう制御）。

Notes / Implementation details
- OpenAI モデルは現状 gpt-4o-mini を指定（news_nlp / regime_detector）。
- ニュースウィンドウは JST ベースで定義し、内部比較は UTC naive datetime を使用（calc_news_window の仕様に基づく）。
- ファクター・リサーチ系は外部 API へアクセスしない（prices_daily / raw_financials のみ参照）。
- ETL / カレンダー更新 / AI スコアリングは部分失敗を許容し、運用時に個別の障害から全体の停止を避ける設計。

Removed
- なし（初版リリース）。

Deprecated
- なし（初版リリース）。

---

今後の予定（参考）
- monitoring や execution 周りの実装公開（パッケージトップの __all__ に含まれているため順次実装予定）。
- OpenAI API の利用量を抑えるためのキャッシュ・要約処理やトークン最適化。
- J-Quants クライアントまわりの詳細実装・単体テストと E2E テストの追加。

もし CHANGELOG に追記してほしい詳細（例: もっと細かいコミット単位の変更、日付の修正、リリースノートの英語版など）があればお知らせください。