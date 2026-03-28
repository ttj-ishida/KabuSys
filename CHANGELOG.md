# CHANGELOG

このプロジェクトは Keep a Changelog のフォーマットに準拠しています。  
すべての非互換な変更はメジャー番号の更新とともに記載します。

## [Unreleased]

（現時点では未リリースの変更はありません）

## [0.1.0] - 2026-03-28

初回リリース — 日本株自動売買システムのコア機能を実装。

### 追加（Added）
- パッケージ基盤
  - kabusys パッケージの初期バージョンを作成（__version__ = "0.1.0"）。
  - サブパッケージ公開: data, research, ai, monitoring, strategy, execution 等を想定した __all__ の定義。

- 設定管理（kabusys.config）
  - .env ファイルや環境変数から設定を自動読み込みする仕組みを実装。
  - プロジェクトルート検出機能を追加（.git または pyproject.toml を起点に探索）。
  - .env / .env.local の読み込み順序を実装（OS 環境 > .env.local > .env）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化フラグを追加（テスト用）。
  - .env パーサ実装（コメント、export プレフィックス、クォート・エスケープ対応、インラインコメント処理）。
  - 環境変数必須チェック用 _require と Settings クラスを提供。
  - 必須設定のプロパティ:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - デフォルト値・型変換:
    - KABUSYS_ENV（development/paper_trading/live の検証）
    - LOG_LEVEL（DEBUG/INFO/... の検証）
    - DUCKDB_PATH / SQLITE_PATH の Path 変換

- データプラットフォーム（kabusys.data）
  - カレンダー管理（calendar_management）:
    - market_calendar テーブルを用いた営業日判定ロジックを提供（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB が未取得の場合に曜日ベースでフォールバックする設計。
    - JPX カレンダーを J-Quants から差分取得する夜間バッチ（calendar_update_job）を実装。バックフィル・健全性チェックを実施。
  - ETL パイプライン（pipeline）:
    - 差分取得・保存・品質チェックを想定した ETLResult データクラスを実装。
    - DuckDB による最大日付取得等のユーティリティを提供。
  - etl の公開インターフェースを re-export（ETLResult）。

- 研究モジュール（kabusys.research）
  - factor_research:
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金・出来高比率）、バリュー（PER・ROE）を計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
    - DuckDB を用いた SQL ベースの実装。データ不足時の None ハンドリング。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク変換（rank）、ファクター統計サマリー（factor_summary）を実装。
    - pandas 等に依存せず標準ライブラリのみでの実装を採用。
  - zscore_normalize を data.stats から再公開。

- AI / NLP（kabusys.ai）
  - ニュース NLP（news_nlp）:
    - raw_news と news_symbols を用いて銘柄ごとにニュースを集約、OpenAI（gpt-4o-mini）へバッチ送信して銘柄毎のセンチメントを取得し、ai_scores テーブルへ書き込むワークフローを実装（score_news）。
    - 時間ウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST）と記事トリム（最大記事数、最大文字数）をサポート。
    - API 呼び出しのリトライ（429 / ネットワーク / タイムアウト / 5xx）と指数バックオフを実装。
    - レスポンスの厳密なバリデーションと部分成功時の DB 書き換え戦略（該当コードのみ DELETE→INSERT）を採用。
    - JSON レスポンスに対するロバストなパース（前後余分テキストの復元含む）を実装。
  - 市場レジーム判定（regime_detector）:
    - ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で market_regime を書き込む機能を実装（score_regime）。
    - マクロニュース抽出、OpenAI によるセンチメント算出（_score_macro）、合成ロジック、冪等的な DB 書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
  - テスト容易性:
    - _call_openai_api を関数化し unittest.mock.patch で差し替え可能にしている。

### 変更（Changed）
- 実装上の設計方針として以下を明確化:
  - datetime.today() / date.today() を AI モジュール内で直接参照しない（ルックアヘッドバイアス防止）。
  - API エラーはフェイルセーフ動作（ゼロあるいはスキップ）で継続する方針を採用。
  - DuckDB に対する executemany の空リスト制約を回避するための事前チェックを追加。

### 修正（Fixed）
- OpenAI レスポンスパース時の堅牢性向上:
  - JSON mode で前後に余計なテキストが混ざるケースを復元してパースする処理を追加。
- API 呼び出しのリトライ挙動の強化:
  - 5xx とネットワーク系エラーを区別してエクスポネンシャルバックオフで再試行する実装。
  - リトライ上限超過時に WARN ログを出してフォールバック値（0.0）やスキップを行う。

### セキュリティ/運用上の注意（Security / Ops）
- 環境変数の自動読み込みはデフォルトで有効だが、KABUSYS_DISABLE_AUTO_ENV_LOAD をセットすることで無効化可能（CI / テスト環境向け）。
- .env.local は優先して .env を上書きする設計（ローカル秘密設定の取り扱い）。
- Settings に必須環境変数チェックを行うため、デプロイ前に必要な環境変数を用意すること（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）。

### 既知の制限 / 設計上の備考（Notes）
- DuckDB をデータ層に使用しているため、環境に DuckDB が必要。
- OpenAI クライアント（gpt-4o-mini）へのアクセスには OPENAI_API_KEY が必要。各関数は api_key 引数でキーを注入可能。
- ETL とカレンダー更新は外部 J-Quants クライアント（jquants_client）に依存しており、実行環境に応じたクライアント設定が必要。
- 現時点では PBR や配当利回り等は未実装（calc_value の注記参照）。

---

今後のリリースでは、以下が想定されます:
- 追加のファクター（PBR、配当利回り等）や指標の実装
- モデル・戦略（strategy）・発注（execution）・監視（monitoring）部分の実装・統合
- テストカバレッジ拡充と CI ワークフロー追加

（必要に応じてリリース日や項目を更新してください）