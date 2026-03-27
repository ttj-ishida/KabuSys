Keep a Changelog に準拠した形式で、提示されたコードベースの内容から推測して CHANGELOG.md（日本語）を作成しました。初期リリース（0.1.0）として主要機能・設計方針・フェイルセーフや注意点をまとめています。

Keep a Changelog
=================

すべての変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠しています。

Unreleased
----------

- なし（初期公開）

[0.1.0] - 2026-03-27
-------------------

Added
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージエントリポイントを定義（src/kabusys/__init__.py）
    - __version__ = "0.1.0"
    - パブリックモジュール: data, strategy, execution, monitoring をエクスポート

- 設定・環境変数管理（src/kabusys/config.py）
  - .env / .env.local のプロジェクトルート自動検出＆読み込み機能を実装
    - 検出基準: 親ディレクトリに .git または pyproject.toml があること
    - 優先順位: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能
    - .env パーサーは export 文、シングル/ダブルクォート、エスケープ、行内コメント等に対応
    - .env の上書き制御（override と protected）により OS 環境変数を保護
  - Settings クラスを提供し、必要な設定プロパティを取得
    - J-Quants / kabuステーション / Slack / DB（duckdb/sqlite）/システム環境など
    - env（development / paper_trading / live）や LOG_LEVEL のバリデーション
    - is_live / is_paper / is_dev のユーティリティプロパティ

- AI ニュース解析（src/kabusys/ai/news_nlp.py）
  - raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）で銘柄ごとにセンチメントを評価
  - タイムウィンドウ（前日15:00 JST ～ 当日08:30 JST）に対応する calc_news_window 実装
  - バッチ処理（最大 20 銘柄/チャンク）、1銘柄あたり記事数・文字数制限（トリム）を実装
  - OpenAI 呼び出しは JSON Mode を期待し、出力のバリデーションと数値クリップ（±1.0）を行う
  - リトライ戦略: 429 / ネットワーク断 / タイムアウト / 5xx を対象とした指数バックオフ
  - 部分成功時の DB 書き込み保護（取得できたコードのみ DELETE → INSERT）
  - フェイルセーフ: API エラー時はスキップして処理継続（例外を投げない）
  - テスト容易性のため _call_openai_api を patch で差し替え可能

- 市場レジーム判定（src/kabusys/ai/regime_detector.py）
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成
  - マクロニュースは news_nlp の窓計算を利用して抽出、OpenAI（gpt-4o-mini）で macro_sentiment を算出
  - スコア合成・閾値によるラベル付け（bull / neutral / bear）
  - DB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装
  - API 呼び出し失敗時は macro_sentiment=0.0（フェイルセーフ）およびリトライ処理
  - ルックアヘッドバイアス防止設計: date 引数ベースで過去データのみ参照

- リサーチ（src/kabusys/research/）
  - factor_research: calc_momentum / calc_value / calc_volatility を実装
    - モメンタム（1M/3M/6M リターン、ma200 乖離）
    - バリュー（PER、ROE）
    - ボラティリティ・流動性（20日 ATR、平均売買代金、出来高比率）
    - DuckDB のウィンドウ関数を活用し営業日スキャン範囲や欠損時の None 処理を実装
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank を実装
    - 将来リターンの計算（可変ホライズン対応、入力バリデーション）
    - Spearman ランク相関（IC）計算（同順位は平均ランク）
    - 統計サマリー（count/mean/std/min/max/median）を標準ライブラリで実装
  - research パッケージで zscore_normalize を再エクスポート

- データ基盤（src/kabusys/data/）
  - calendar_management: market_calendar を基にした営業日判定や next/prev_trading_day, get_trading_days, is_sq_day を実装
    - DB 登録値優先、未登録日は曜日ベースでフォールバック
    - 更新バッチ calendar_update_job: J-Quants API から差分取得、バックフィル・健全性チェックを実装
  - pipeline / etl:
    - ETLResult データクラスを公開（取得数、保存数、quality_issues、errors 等を保持）
    - 差分更新・バックフィル・品質チェックの設計に対応するユーティリティ実装
    - _get_max_date やテーブル存在チェックなどの内部ユーティリティ

Changed
- （初回リリースのため該当なし）

Fixed
- （該当なし、初回機能実装時に考慮されたフォールバック／フェイルセーフを明記）
  - OpenAI 呼び出し・パース失敗時は例外を上位に伝播させず 0.0 やスキップで継続する実装
  - DuckDB の executemany に対する空リスト制約を回避するため、事前チェックを追加

Security
- 環境変数の扱い:
  - 自動ロード時に OS 環境変数を protected として上書きされないよう保護
  - OPENAI_API_KEY など必須環境変数は Settings から取得時に未設定なら ValueError を投げ明示化

Notes / Implementation details / 既知の振る舞い
- ルックアヘッドバイアス防止:
  - score_news / score_regime などは内部で datetime.today() を参照せず、必ず target_date を引数で受け取る設計
- OpenAI API:
  - gpt-4o-mini を想定、JSON Mode（response_format={"type": "json_object"}）での応答を期待
  - API レスポンスのパースや検証に堅牢性を持たせている（余分な前後テキストのサニタイジング等）
- DuckDB 互換性:
  - executemany に空リストを渡せない環境（例: DuckDB 0.10）への対応を実装
  - 日付値は date オブジェクトで扱うことを前提に型変換ヘルパを用意
- テスト容易性:
  - OpenAI 呼び出しは内部的に分離されており、unittest.mock.patch による差し替えが容易
- DB 書き込みの冪等性:
  - calendar / ai_scores / market_regime の更新は既存行を削除して挿入する等で冪等性を確保

Deprecated
- なし

Removed
- なし

References
- モジュール内ドキュメント（ソース内 docstring）に沿った実装・設計方針に基づく初期リリースです。テスト・本番運用時は .env の取り扱いや OPENAI_API_KEY、KABU_API_PASSWORD、Slack トークンなどの機密情報管理に注意してください。