# CHANGELOG

すべての変更は Keep a Changelog 準拠で記載しています。  
フォーマット: https://keepachangelog.com/ja/

なお、以下はコードベースの内容から推測して作成した変更履歴です。

## [Unreleased]
- 現時点で未リリースの変更はありません。

## [0.1.0] - 2026-03-28
初回リリース。日本株自動売買プラットフォームのコアライブラリを提供します。主な追加点・設計方針は以下の通りです。

### Added
- パッケージ基盤
  - kabusys パッケージを追加。__version__ = 0.1.0。
  - パッケージ公開インターフェースに data, strategy, execution, monitoring を想定してエクスポート。

- 設定／環境変数管理 (kabusys.config)
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml から検出）。
  - 高度な .env パーサを実装（export 形式・シングル/ダブルクォート・エスケープ・インラインコメント対応）。
  - 自動読み込みの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を用意。
  - Settings クラスを追加し、J-Quants / kabu API / Slack / DB パス / 環境モード / ログレベル等の設定を環境変数から取得。未設定時の検証とエラーメッセージを整備。
  - 環境値検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）を実装。

- データ基盤ユーティリティ (kabusys.data)
  - calendar_management: JPX マーケットカレンダー管理と営業日判定ユーティリティを実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - market_calendar が未取得の場合は曜日ベースでフォールバックする一貫したロジック。
    - 夜間バッチ calendar_update_job を実装（J-Quants API からの差分取得と冪等保存、バックフィル・健全性チェックを含む）。
  - pipeline / etl: ETL パイプライン用ユーティリティを追加。
    - ETLResult データクラスを追加（取得・保存件数、品質問題、エラー一覧などを含む）。
    - 差分取得、バックフィル、品質チェック方針をドキュメント化。
  - etl モジュールの公開インターフェース (ETLResult) を再エクスポート。

- 研究（Research）モジュール (kabusys.research)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離などのモメンタム系ファクターを計算。
    - calc_volatility: 20日 ATR、相対 ATR、平均売買代金、出来高比率を計算。
    - calc_value: raw_financials を用いた PER / ROE の計算（最新レポートを target_date 以前から選択）。
    - 設計上、prices_daily / raw_financials のみ参照し外部 API へはアクセスしない。
  - feature_exploration:
    - calc_forward_returns: 各ホライズン（デフォルト 1/5/21 営業日）の将来リターンを計算。
    - calc_ic: スピアマンランク相関（IC）を実装（rank 関数を含む）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
    - rank: 同順位は平均ランクにする実装。
  - research パッケージの便利関数を再エクスポート（zscore_normalize 等）。

- AI / NLP モジュール (kabusys.ai)
  - news_nlp:
    - score_news: raw_news と news_symbols を元に銘柄ごとのニュースセンチメントを OpenAI（gpt-4o-mini）で評価し、ai_scores テーブルへ書き込む。
    - タイムウィンドウ（前日15:00 JST ～ 当日08:30 JST）計算機能を実装（calc_news_window）。
    - チャンク処理（最大 20 銘柄/コール）、記事数・文字数のトリム、JSON Mode のレスポンス検証、リトライ（429/ネットワーク/5xx）と指数バックオフを実装。
    - レスポンスバリデーションで未知コードや無効スコアを無視し、スコアを ±1.0 にクリップ。
    - フェイルセーフ設計: API 呼び出し失敗時は該当チャンクをスキップし、例外を投げずに処理継続。
  - regime_detector:
    - score_regime: ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して日次の market_regime を計算・保存。
    - マクロニュース抽出（マクロキーワードによるタイトルフィルタ）、OpenAI 呼び出し（gpt-4o-mini）によるセンチメント算出、リトライ/フェイルセーフ、スコア合成・ラベリング（bull/neutral/bear）を実装。
    - DB 書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で行う。
  - AI モジュールは OpenAI API キー引数注入が可能で、テスト置換がしやすいよう _call_openai_api を分離。

### Changed
- 設計方針の明確化（全体）
  - すべての日時計算で datetime.today()/date.today() の直接参照を避け、ルックアヘッドバイアス対策を徹底。
  - DB 書き込みは部分失敗対応（code を絞って DELETE → INSERT）や冪等性を重視。
  - DuckDB の実装制約（executemany の空リスト不可等）への対応を組み込んだ実装。

### Fixed / Robustness
- エラー処理・ログの強化
  - .env 読み込み失敗時に警告を出すよう変更。
  - OpenAI API 呼び出し失敗時（各種例外）の振る舞いを明確化し、非致命的エラーはフォールバック（例: macro_sentiment=0.0）して継続するように実装。
  - JSON パース失敗時に周辺テキストを抽出して再試行する等、LLM レスポンスのゆらぎに対する耐性を追加。
  - market_calendar の不整合（NULL 等）を検知して警告を出すように実装。

### Notes / Limitations
- 現バージョンでは本番発注（execution）や具体的な strategy ロジック、monitoring の実装はパッケージ構成上想定されているが、提供コードの主要部分はデータ取得・前処理・研究・AI スコアリングにフォーカスしています。
- OpenAI SDK の仕様変化（例: APIError の属性名等）に対して安全側でのハンドリングを行っていますが、将来的な SDK 変更には追加対応が必要な場合があります。
- ETL / calendar_update_job などは外部 J-Quants クライアント (jquants_client) に依存します。API 呼び出しや保存処理は jquants_client 側で実装される想定です。

---

今後のリリースでは strategy / execution / monitoring 周りの実装、さらにユニットテスト・CI ワークフロー・ドキュメントの追加などを想定しています。必要があればリリースノートを拡張・調整します。