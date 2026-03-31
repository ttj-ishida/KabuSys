# Changelog

すべての変更は Keep a Changelog の方針に従って記載しています。  
この CHANGELOG は、与えられたコードベースの内容から機能・修正点・設計上の注意点を推測して作成しています。

※ バージョン番号はパッケージの __version__ (= 0.1.0) に基づいています。

Unreleased
----------
（なし）

[0.1.0] - 2026-03-31
-------------------

Added
- 初期リリース: KabuSys 日本株自動売買システムの基礎モジュール群を追加。
  - パッケージ初期化: src/kabusys/__init__.py に __version__ = "0.1.0" と __all__ の公開 API 指定。
- 設定管理:
  - src/kabusys/config.py
    - .env ファイルと環境変数からの設定読み込みを自動化（プロジェクトルートを .git または pyproject.toml から検出）。
    - .env/.env.local の読み込み順序（OS 環境変数 > .env.local > .env）を実装。
    - export 形式やクォート・エスケープ・インラインコメントのパースに対応する独自パーサ実装。
    - 環境変数の必須チェックを行う Settings クラス（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等をプロパティとして公開）。
    - 環境（development/paper_trading/live）やログレベルのバリデーション、データベースパス（duckdb / sqlite）のデフォルト値提供。
    - 自動読み込みを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD フラグをサポート。
- AI（自然言語処理）:
  - src/kabusys/ai/news_nlp.py
    - raw_news と news_symbols から銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントを評価して ai_scores テーブルへ書き込む処理を実装。
    - バッチ処理（銘柄ごと最大 _BATCH_SIZE=20）／記事数・文字数トリム（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）／JSON mode 応答の検証実装。
    - 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライを実装。
    - エラー時はフォールバック（スキップ）し、部分成功時に既存スコアを保護する設計（DELETE → INSERT をコードごとに実行）。
    - calc_news_window 関数（ニュース集計ウィンドウ計算）を実装。ルックアヘッドバイアス防止のため datetime.today() を直接参照しない設計。
  - src/kabusys/ai/regime_detector.py
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込みする処理を実装。
    - マクロキーワードによるニュース抽出、OpenAI 呼び出し（gpt-4o-mini）による JSON レスポンス解析、リトライ／フォールバック（API 失敗時 macro_sentiment=0.0）を実装。
    - 内部で API 呼び出し実装をモジュールごとに分離し、ユニットテスト時に差し替えやすい設計（_call_openai_api を patch 可能）を採用。
- 研究用解析（Research）:
  - src/kabusys/research/
    - factor_research.py: モメンタム（1M/3M/6M・MA200乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金・出来高比）およびバリュー（PER, ROE）計算を DuckDB 上の SQL と Python 組み合わせで実装。
    - feature_exploration.py: 将来リターン計算（任意ホライズン）、IC（Spearman ランク相関）計算、値のランク化ユーティリティ、ファクター統計サマリーを実装。pandas 等外部依存を避ける方針。
    - research/__init__.py で主要関数を再エクスポート。
- データ基盤（Data）:
  - src/kabusys/data/calendar_management.py
    - JPX カレンダー（market_calendar）に基づく営業日判定、next/prev_trading_day、get_trading_days、is_sq_day、calendar_update_job（J-Quants API からの差分取得と冪等保存）を実装。
    - DB データが欠けている場合は曜日ベースのフォールバック（週末は非営業日）を用いる設計。
    - バックフィル・健全性チェック（過剰な未来日付検出）を実装。
  - src/kabusys/data/pipeline.py / etl.py
    - ETLResult データクラス（ETL の取得数・保存数・品質問題・エラーを集約）を実装し公開。
    - 差分取得、バックフィル、品質チェックの流れを想定した設計（jquants_client と quality モジュールとの連携前提）。
  - jquants_client 等のクライアントはモジュール参照により外部 API 呼び出しを行う想定（fetch/save 関数を利用）。
- テスト・運用しやすさ:
  - 多くの外部 API 呼び出し箇所（OpenAI 呼び出し等）は patch による差し替えが想定される形で実装されている（ユニットテスト容易性を考慮）。
  - DuckDB を前提とした SQL 実行結果の取り扱い（date の変換ユーティリティなど）を実装。

Changed
- （初版のため既存からの変更はありません）

Fixed
- （初版のため修正履歴はありません）

Security
- 環境変数を使った API キー管理を標準としている（OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN 等）。
- 自動 .env 読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能（テストやセキュリティ運用を考慮）。

Known issues / Limitations（推測）
- OpenAI API キー未設定時は news_nlp.score_news / regime_detector.score_regime が ValueError を送出するため、運用時に環境変数または引数でのキー注入が必須。
- ai モジュールは外部 API（OpenAI）に依存しているため、ネットワークまたは API 側の制限で部分失敗が発生する可能性がある（多数のフェイルセーフは実装済みで、失敗時は該当チャンクをスキップして進行）。
- strategy / execution / monitoring といった売買実行周りの公開 API はパッケージトップで __all__ に含まれるが、今回提供されたソースリストにはそれらの実装ファイルが含まれていない（将来的な追加が想定される）。
- DuckDB バインド挙動（executemany に空リスト不可など）への対応がコードに見られるため、使用する DuckDB バージョンとの互換性確認が必要。

依存関係（コードから推測）
- duckdb
- openai（OpenAI SDK）
- 標準ライブラリ: datetime, json, logging, os, time, math, typing 等

補足（設計上の重要点）
- ルックアヘッドバイアス防止のため、target_date ベースで過去ウィンドウのみ参照し、datetime.today()/date.today() を直接参照しない設計が各所で徹底されている（研究・評価の再現性を重視）。
- DB への書き込みは冪等性を重視（DELETE → INSERT、ON CONFLICT 期待など）しており、部分失敗時に既存データを不用意に上書きしない方針が採用されている。

---

この CHANGELOG はコードから推測して作成したものであり、実際のリリースノートや意図とは異なる箇所がある可能性があります。必要であれば、リリース日や既知の変更点（実際のコミット履歴に基づく差分）を提供してください。