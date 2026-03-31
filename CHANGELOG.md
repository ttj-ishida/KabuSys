# Changelog

すべての重要な変更点を Keep a Changelog の書式に従って日本語で記載します。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

なお、この CHANGELOG はソースコードの内容から推測して作成しています。

## [Unreleased]
（現時点で未リリースの変更はありません）

## [0.1.0] - 2026-03-31
初回リリース。日本株自動売買システムの基礎機能を提供するモジュール群を追加しました。

### Added
- パッケージ初期化
  - kabusys パッケージのエントリポイントを追加。__all__ に data, strategy, execution, monitoring を公開。
  - パッケージバージョンを 0.1.0 として設定。

- 設定・環境変数管理（kabusys.config）
  - .env ファイルおよび環境変数を読み込む自動ローダーを実装（プロジェクトルートの検出は .git または pyproject.toml を参照）。
  - .env の読み込み優先順位を OS 環境 > .env.local（上書き）> .env（未設定時のみ）と実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env パーサーを強化:
    - export KEY=val 形式に対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理対応
    - クォートなし行でのインラインコメント処理（直前がスペース/タブの場合にのみ # をコメントと認識）
  - 環境設定ラッパー Settings を追加。J-Quants / kabu API / Slack / DB パス / 実行環境・ログレベルなどの取得メソッドを提供。
  - 環境変数未設定時の明示的エラー（_require）、KABUSYS_ENV と LOG_LEVEL の値検証（許容値チェック）を実装。

- データプラットフォーム関連（kabusys.data）
  - ETL パイプラインのインターフェース ETLResult を追加（pipeline モジュールの再公開）。
  - pipeline モジュールを実装:
    - 差分更新、バックフィル、品質チェック（quality モジュール連携）を考慮した ETLResult データクラスを提供。
    - DuckDB での最大日付取得等のユーティリティを実装。
    - デフォルトバックフィル・最小データ日等の定義。
  - マーケットカレンダー管理モジュール calendar_management を追加:
    - market_calendar テーブルを参照して営業日判定、next/prev_trading_day、get_trading_days、is_sq_day 等のユーティリティを提供。
    - DB 未取得時は曜日ベースでフォールバック（週末を非営業日扱い）。
    - JPX カレンダーを J-Quants API から差分取得して冪等保存する夜間バッチ calendar_update_job を実装。
    - バックフィル・先読み・健全性チェック（未来日付の異常検出）を実装。

- 研究（research）モジュール群
  - factor_research モジュール:
    - モメンタム（1M/3M/6M、ma200乖離）、ボラティリティ（20日 ATR 等）、バリュー（PER・ROE）の計算関数（calc_momentum, calc_volatility, calc_value）を実装。
    - DuckDB を利用した SQL ベースの実装で、データ不足時の None 処理やスキャンバッファを考慮。
  - feature_exploration モジュール:
    - 将来リターン算出 calc_forward_returns（任意ホライズン）、IC（スピアマンランク相関）calc_ic、ランク化ユーティリティ rank、統計サマリー factor_summary を実装。
    - ties 対応のランク計算（同順位は平均ランク）や入力検証を実装。

- AI（自然言語処理）モジュール（kabusys.ai）
  - news_nlp モジュール:
    - raw_news と news_symbols を基に銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）の JSON mode を用いて銘柄ごとのセンチメント（ai_score）を算出して ai_scores テーブルに書き込む機能を追加（score_news）。
    - チャンク処理（1 API 呼び出しにつき最大 20 銘柄）、記事トリム（最大記事数・最大文字数）を実装。
    - レート制限・ネットワーク断・タイムアウト・5xx に対する指数バックオフのリトライを実装。
    - レスポンスの堅牢なバリデーション、JSON 前後ノイズからの抽出、スコアの ±1.0 クリップを実装。
    - 部分失敗時に他銘柄スコアを保持するため、DELETE→INSERT によりスコアを書き換える冪等処理を実装（DuckDB executemany の互換性考慮）。
    - テスト容易性のため OpenAI 呼び出し部は差し替え可能（関数を patch 可能）。
  - regime_detector モジュール:
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）と、news_nlp によるマクロセンチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し market_regime テーブルに書き込む機能（score_regime）を追加。
    - LLM 呼び出しは gpt-4o-mini を使用、API エラー時は macro_sentiment を 0.0 にフォールバックするフェイルセーフを実装。
    - DuckDB を用いたデータ取得（ルックアヘッド防止のため date < target_date 等でクエリ）と冪等な DB 書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - OpenAI 呼び出し部はテスト用に差し替え可能。

### Changed
- （実装起点のため特段の変更履歴はなし）  
  ただし、各モジュールは以下の設計方針に統一:
  - datetime.today() / date.today() を直接参照しない（ルックアヘッドバイアス防止）。target_date を明示的に受け取る設計。
  - 外部 API 呼び出し失敗時はシステム全体停止ではなくフォールバックやスキップで継続するフェイルセーフ設計。
  - DuckDB のバージョン差異・制約（ex. executemany の空リスト）を考慮した互換実装。

### Fixed
- .env 読み込みの堅牢性向上
  - ファイルが開けない場合の警告ログ出力。
  - protected 引数で OS 環境を上書きから保護する仕組みを導入。

- OpenAI レスポンス周りのエラーハンドリングを強化
  - APIError の status_code 有無に依存しない安全な判定。
  - JSON パース失敗時のロギングとフォールバック。

- DuckDB 書き込み時のロールバック処理
  - DB 書き込み中に例外が発生した場合に ROLLBACK を試み、さらに ROLLBACK 失敗時の警告ログを追加。

### Security
- 機密情報の取り扱い:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID などの必須環境変数は Settings 経由で明示的に要求するようにし、未設定時は ValueError を発生させることで誤設定を早期検出。

### Notes / Migration / Usage
- 必須環境変数:
  - OpenAI を使う機能（score_news / score_regime）を利用する場合は OPENAI_API_KEY を環境変数または関数引数で指定してください。未指定時は ValueError を投げます。
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は Settings で必須としているため、実行環境で設定してください。
- 自動 .env ロードを無効化したい場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットすると自動読み込みをスキップします（テスト用途等）。
- DuckDB に関する互換性:
  - DuckDB 0.10 系列の executemany の仕様に配慮しているため、空のパラメータリストは事前にチェックしています。
- テストのしやすさ:
  - OpenAI 呼び出しは内部で _call_openai_api を経由しているため、unittest.mock.patch 等で差し替えてユニットテストが可能です。

---

今後のリリースでは、strategy / execution / monitoring モジュールの具体的な取引ロジック・発注実装、より詳細な品質チェックルール、CI 用テストケースの追加などを予定しています。