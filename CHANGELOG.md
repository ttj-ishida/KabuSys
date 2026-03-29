CHANGELOG
=========

すべての注目すべき変更をこのファイルに記録します。
このプロジェクトは "Keep a Changelog" の方針に従います。
セマンティックバージョニングを採用します。

フォーマットのキー:
- Added: 新機能
- Changed: 既存機能の変更（後方互換性がある場合）
- Fixed: バグ修正
- Security: セキュリティ関係の修正や注意事項

Unreleased
----------

- （現在なし）

[0.1.0] - 2026-03-29
--------------------

Added
- パッケージ初期リリース: kabusys 0.1.0
  - ルートパッケージと公開インターフェースを定義（src/kabusys/__init__.py）。
  - モジュール群を提供:
    - data: データ取得・ETL・カレンダー管理・品質チェックのためのユーティリティ群
    - research: ファクター計算や特徴量解析ユーティリティ
    - ai: ニュースNLP と 市場レジーム判定のAI関連モジュール
    - （将来的に strategy / execution / monitoring を想定した __all__ 宣言あり）

- 環境設定管理（src/kabusys/config.py）
  - .env および .env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - export 文やクォート、エスケープ、インラインコメントを考慮した堅牢な .env パーサ実装。
  - OS 環境変数を保護する機能（protected set）と override 挙動を提供。
  - 必須環境変数取得ヘルパ（_require）と Settings クラスを提供。各種設定プロパティ（J-Quants, kabu, Slack, DBパス, 環境種別とログレベル判定 等）を実装。
  - 自動読み込みを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。

- ニュースNLP（src/kabusys/ai/news_nlp.py）
  - raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄ごとのセンチメントスコアを算出し ai_scores テーブルへ書き込む処理を実装。
  - タイムウィンドウ（前日15:00 JST ～ 当日08:30 JST）計算ユーティリティ calc_news_window を提供。
  - バッチ処理（最大20銘柄/チャンク）、トークン肥大化対策（記事数・文字数上限）、レスポンス検証ロジックを実装。
  - レート制限・接続断・タイムアウト・5xx に対する指数バックオフリトライ実装と、API異常時にフェイルセーフでスキップする振る舞い。
  - JSON レスポンスの復元（前後に余計なテキストが混入する場合の {} 抽出）や型検証を実装。
  - テスト容易性のため _call_openai_api を置き換え可能（patch可能）に設計。

- 市場レジーム判定（src/kabusys/ai/regime_detector.py）
  - ETF 1321（日経225連動型）の200日移動平均乖離（70%）とマクロニュースのLLMセンチメント（30%）を組合せて市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込みを行う機能を実装。
  - prices_daily / raw_news を用いたデータ取得、OpenAI 呼び出し、スコア合成ロジックを実装。
  - API呼び出しに対するリトライ／フォールバック（失敗時 macro_sentiment=0.0）や、500系エラーとそれ以外の扱い差別化を実装。
  - ルックアヘッドバイアス防止のため日時計算とクエリに排他条件を採用。
  - テスト置換用に _call_openai_api を独自実装し、news_nlp とは別実装でモジュール結合を避ける設計。

- ETL / パイプライン（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
  - ETLResult データクラスを実装し、ETL 実行結果（取得件数・保存件数・品質問題・エラー）を構造化。
  - 差分取得、backfill、品質チェックのための設計方針と補助関数（テーブル存在チェック、最大日付取得など）を実装。
  - etl モジュールで pipeline.ETLResult を再エクスポート。

- カレンダー管理（src/kabusys/data/calendar_management.py）
  - market_calendar を基に営業日判定、next/prev_trading_day、get_trading_days、is_sq_day 等の判定ロジックを実装。
  - DB 未取得時は曜日ベースのフォールバック（週末除外）を採用。
  - JPX カレンダーを J-Quants API から差分取得する夜間ジョブ calendar_update_job を実装（バックフィル、健全性チェック、冪等保存の流れ）。
  - 最大探索範囲や見つからない場合の ValueError など安全策を導入。

- Research（src/kabusys/research/*）
  - ファクター計算: calc_momentum（1M/3M/6M、MA200乖離）、calc_value（PER/ROE）、calc_volatility（20日ATR、流動性指標）を実装。prices_daily / raw_financials のみ参照。
  - 特徴量探索: calc_forward_returns（任意ホライズンの将来リターン）、calc_ic（スピアマンランク相関によるIC）、factor_summary（統計サマリー）、rank（平均ランク処理）を実装。
  - 外部依存を使わずに標準ライブラリ + DuckDB SQL での実装を志向。
  - 入力チェックや欠損データ取り扱い（Noneやデータ不足時の扱い）を明記。

- データアクセス & 汎用
  - DuckDB を前提とした SQL クエリ、日付取り扱い、IDEMPOTENT な DB 書き込み（DELETE→INSERT、BEGIN/COMMIT/ROLLBACK）を各モジュールで採用。
  - ロギング出力（info/debug/warning/exception）を適宜追加し、失敗時の情報把握を容易に。

Changed
- （初期リリースのため該当なし）

Fixed
- （初期リリースのため該当なし）

Security
- API キーは関数引数で注入可能（api_key）かつ環境変数 OPENAI_API_KEY を参照する設計。`.env` 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。

Notes / Known limitations
- OpenAI 実装は gpt-4o-mini を想定しており、OpenAI SDK の将来の変更に備え一部例外ハンドリングで互換性を考慮しているが、SDKの大幅な仕様変更は影響を受ける可能性あり。
- DuckDB の executemany の空リスト扱い等のバージョン依存挙動に配慮した実装をしているが、異なる DuckDB バージョンでは部分的に動作差が生じる可能性がある。
- 本バージョンでは発注（execution）やストラテジーの実行インターフェースは公開名のみ（__all__）として存在し、具体的な注文ロジックは未実装／別モジュールでの実装を想定。

Authors
- 開発チーム（コードベースより推測して作成）

----- 

（この CHANGELOG はコード内のドキュメンテーションと実装から推測して作成しています。実際のリリースノート作成時はコミット履歴・issue 等を基に適宜修正してください。）