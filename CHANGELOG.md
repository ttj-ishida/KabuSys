# CHANGELOG

すべての重要な変更を記録します。本プロジェクトは Keep a Changelog の指針に従っています。  

## [Unreleased]

（現在の変更はありません）

---

## [0.1.0] - 2026-04-03

初回リリース。日本株自動売買プラットフォームの基盤機能を実装しました。主な追加点は以下の通りです。

### 追加（Added）
- パッケージ基盤
  - パッケージメタ情報を追加（kabusys.__version__ = 0.1.0）。
  - 公開サブパッケージ: data, research, ai, execution, monitoring, strategy を想定した __all__ を定義。

- 環境設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を自動読み込みする機能を実装。
  - 自動ロード順序: OS環境変数 > .env.local > .env。
  - 自動ロードを無効化するための環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート（テスト用途想定）。
  - .env の柔軟なパース実装:
    - コメント行、export 先頭キーワード、シングル／ダブルクォート、バックスラッシュエスケープ、インラインコメントの取り扱い。
  - 環境設定取得用 Settings クラスを追加。主なプロパティ:
    - J-Quants / kabuステーション / LINE Messaging / データベースパス（DuckDB/SQLite）/監視用ファイルパス/リソース閾値/環境種別とログレベル判定など。
  - 必須環境変数未設定時に ValueError を投げる _require() を提供。
  - 有効な環境（development / paper_trading / live）・ログレベルの検証を実装。
  - 設計方針として OS 環境の保護（protected set）を考慮した .env 上書き処理をサポート。

- AI モジュール（kabusys.ai）
  - ニュースセンチメントスコアリング（kabusys.ai.news_nlp）を実装。
    - raw_news / news_symbols を集約して銘柄ごとにニュースをまとめ、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄ごとのスコアを取得。
    - バッチ処理（1コール最大20銘柄）、1銘柄当たり最大10記事・最大3000文字でトリム。
    - 429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライを実装。
    - レスポンスの堅牢なバリデーション（JSON復元処理、results配列・code/score検証、スコアの ±1.0 クリップ）。
    - APIキー未設定時は ValueError を送出。記事が無ければ 0 を返す。
    - 公開API: score_news(conn, target_date, api_key=None)、calc_news_window(target_date) など。
  - 市場レジーム判定（kabusys.ai.regime_detector）を実装。
    - ETF 1321 の 200日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次でレジーム判定（bull/neutral/bear）。
    - マクロキーワードによる raw_news フィルタリング、最大20記事まで取得。
    - OpenAI 呼び出し（gpt-4o-mini）による macro_sentiment 評価（JSON 出力期待）。API失敗時はフェイルセーフで macro_sentiment=0.0。
    - レジーム算出ロジック（スコアのクリップ、閾値判定）と market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - 公開API: score_regime(conn, target_date, api_key=None)。

- データ基盤（kabusys.data）
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルを使用した営業日判定ロジックを実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - DBにデータがない場合は土日ベースのフォールバック（曜日判定）を行い、一貫性を保つ設計。
    - 夜間バッチ job calendar_update_job(conn, lookahead_days=...) を実装し、J‑Quants クライアント経由で差分取得→保存（バックフィル・健全性チェック付き）を行う。
  - ETL パイプライン（kabusys.data.pipeline / etl）
    - ETLResult データクラスを導入（取得件数・保存件数・品質チェック結果・エラー一覧などを保持）。
    - 差分取得・保存・品質チェックの流れを実現するためのユーティリティ関数群を整備（jquants_client / quality モジュールと連携する設計）。
    - テーブル存在確認・最大日付取得等の内部ユーティリティを追加。
  - etl モジュールで pipeline.ETLResult を再エクスポート。

- 研究用機能（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - モメンタム（1M/3M/6M）、200日MA乖離、ボラティリティ（20日ATR）、流動性（20日平均売買代金・出来高比率）等を DuckDB SQL ベースで計算する関数を追加。
    - calc_momentum / calc_volatility / calc_value 公開。
    - raw_financials / prices_daily のみ参照し、本番発注系にアクセスしない設計。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク変換（rank）、統計サマリー（factor_summary）を実装。
    - pandas 等外部依存を使わず、標準ライブラリ・DuckDBで完結する実装。
  - research パッケージから主要関数を __all__ で再エクスポート。

### 変更（Changed）
- 設計方針上の共通点として、AI/研究/データ処理モジュールは「ルックアヘッドバイアス防止」のために datetime.today()/date.today() を内部で直接参照しないようにしており、すべて外部から target_date を渡す API を採用しています。

### 修正（Fixed）
- DB 書き込み周りでの冪等性・例外対処を強化
  - AI スコア／レジーム書き込みや ETL の INSERT/DELETE はトランザクション（BEGIN/COMMIT/ROLLBACK）で囲み、ROLLBACK の失敗時は警告ログを出力するようにしました。
  - DuckDB の executemany に空リストを渡すと失敗する制約への対応（空の場合は実行をスキップ）。

### 設計上の注意（Notes）
- OpenAI API
  - デフォルトモデル: gpt-4o-mini、JSON Mode を期待してレスポンスをパースしています。
  - API キーは関数引数で注入可能（テスト容易化）で、未指定時は環境変数 OPENAI_API_KEY を参照します。未設定時は ValueError を送出します。
  - API 呼び出しはリトライとフェイルセーフ（スコア 0.0 / スキップ）を取り入れており、完全停止しない設計です。
- DuckDB テーブル
  - 各モジュールは特定テーブル（prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials など）を前提としています。利用時はスキーマが整っている前提です。
- ローカル設定ロード
  - .env のパースは Bash 互換の多くのケースに対応しますが、特殊ケースがある場合は .env を整形してください。

---

これらはコードベースから推測してまとめた初回リリースノートです。必要があれば、各モジュールごとにより詳細な使用例や互換性・移行手順の追記も作成します。どのモジュールの詳細が必要か教えてください。