# Changelog

すべての重要な変更点を記録します。本ファイルは「Keep a Changelog」形式に準拠しています。  

※この CHANGELOG はリポジトリ内のソースコードから実装内容・設計方針を推測して作成しています。

## [Unreleased]

（現時点で未リリースの変更はありません）

## [0.1.0] - 2026-03-26

### Added
- 初回リリース。パッケージ `kabusys` を導入。
  - パッケージ構成（主なモジュール）
    - kabusys.config: 環境変数 / .env 管理
    - kabusys.ai: ニュース NLP（news_nlp）および市場レジーム判定（regime_detector）
    - kabusys.data: データ関連（calendar_management, pipeline, etl 等）
    - kabusys.research: ファクター計算・特徴量解析（factor_research, feature_exploration）
    - kabusys.__init__ により主要サブパッケージを公開（data, strategy, execution, monitoring）
- 環境設定（kabusys.config）
  - プロジェクトルート自動検出機能を追加（.git または pyproject.toml を基準）。
  - .env 自動読み込み機能を実装（優先順位: OS 環境変数 > .env.local > .env）。
  - .env パース処理を強化：
    - export プレフィックス対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応
    - インラインコメントの扱い（クォート外かつ前が空白/タブの場合をコメントと認識）
  - .env 読み込みで既存 OS 環境変数を保護する protected 機構を実装し、override フラグをサポート。
  - 自動ロードを無効化する環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加（テスト用途）。
  - Settings クラスを提供し、必要な環境変数をプロパティ経由で取得（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）。
  - 設定値のバリデーションを実装（例: KABUSYS_ENV / LOG_LEVEL の許容値検査）。
  - デフォルト値として DB パス（DUCKDB_PATH, SQLITE_PATH）や Kabu API ベース URL を設定可能。

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news / news_symbols を元に銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）でセンチメント評価を実施。
  - バッチ処理（最大 20 銘柄／API 呼び出し）、1 銘柄当たりの最大記事数／文字数制限を導入（トークン肥大化対策）。
  - JSON Mode を利用した厳密な JSON レスポンス期待と、レスポンスの堅牢なバリデーション・パース処理を実装（不正レスポンス時はスキップ）。
  - レート制限・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライを実装。
  - スコアは ±1.0 にクリップ。結果を ai_scores テーブルへ冪等的に書き込み（DELETE → INSERT）して部分失敗時の保護を実現。
  - API キー注入（api_key 引数）に対応。未指定時は環境変数 OPENAI_API_KEY を参照。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull / neutral / bear）を判定。
  - マクロニュース抽出のキーワードリストを実装し、該当記事を取得して OpenAI に評価を依頼。
  - OpenAI 呼び出しはリトライ/バックオフ・5xx 判定等の堅牢化を実装。API 失敗時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。
  - 最終結果を market_regime テーブルに冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）し、安全に更新。
  - ルックアヘッドバイアス対策: 内部処理で datetime.today() / date.today() を参照しない設計。prices_daily のクエリは target_date 未満を使用。

- 研究用ファンクション（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離などのモメンタムファクター算出（DuckDB SQL ベース）。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金・出来高比率等のボラティリティ/流動性指標。
    - calc_value: raw_financials と株価を組み合わせた PER / ROE の算出（最新財務レコードの取得ロジック含む）。
    - 設計方針として DuckDB 接続のみを受け取り外部 API に依存しない実装。
  - feature_exploration:
    - calc_forward_returns: 指定日から任意ホライズン（デフォルト [1,5,21] 営業日）の将来リターン取得（LEAD を使用）。
    - calc_ic: スピアマンのランク相関（Information Coefficient）計算（欠測値・同順位処理を考慮）。
    - rank: 同順位は平均ランクを返す実装（丸めで ties 判定の安定化）。
    - factor_summary: count/mean/std/min/max/median を標準ライブラリのみで計算。

- データ管理（kabusys.data）
  - calendar_management:
    - JPX カレンダーを扱うユーティリティ群（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - market_calendar が未取得の場合は曜日ベースのフォールバック（週末を非営業日扱い）を行う一貫した実装。
    - カレンダー更新バッチ calendar_update_job を実装（J-Quants API との差分取得・バックフィル・健全性チェック・保存）。
  - pipeline / etl:
    - ETLResult データクラスを提供し、ETL 処理の取得数 / 保存数 / 品質チェック結果 / エラーを集約。
    - 差分更新・バックフィル方針、品質チェックの扱い（重大度の集約）はドキュメント化。
    - データ保存関数（jquants_client 経由）の呼び出しとエラーハンドリング（例: save_market_calendar の例外捕捉）を実装。
  - kabusys.data.etl では ETLResult を再エクスポート。

### Changed
- 初回リリースのため特記すべき変更履歴は無し（初期導入）。

### Fixed
- （設計上の安全対策）
  - DuckDB の executemany が空リストを受け付けない制約に対応して、実行前に空チェックを行う実装を追加（ai/news_nlp, pipeline 等）。
  - API レスポンスパース失敗や API エラー時に例外を投げずフェイルセーフにフォールバックする挙動を採用（LLM 依存処理の運用耐性向上）。
  - market_calendar の不整合（NULL 等）に対して警告ログと曜日フォールバックを行う保守性の強化。

### Security
- 重要なシークレット（OPENAI_API_KEY など）は Settings 経由での取得を想定。自動 .env 読み込みはテスト用に無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

### Notes
- 多くのモジュールで「ルックアヘッドバイアスを防ぐために現在日時を直接参照しない」設計思想が採用されています。すべての外部 API 呼び出し（OpenAI / J-Quants 等）は呼び出し箇所でリトライやバックオフ、フェイルセーフを実装しています。
- 必須の環境変数（例）:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY
- OpenAI には gpt-4o-mini を想定しており、JSON Mode を用いた厳密な応答フォーマットでの連携を前提としています。

---

今後のリリースでは、ユニットテスト・CI 設定、strategy / execution / monitoring モジュールの詳細実装、ドキュメント（API 使用法・DB スキーマ）等の追加が想定されます。必要であればこの CHANGELOG を拡張してバージョン履歴を細分化します。