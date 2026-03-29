Keep a Changelog に準拠した CHANGELOG.md（日本語）

すべての重大な変更はこのファイルに記録します。

フォーマット:
- 変更内容は Added / Changed / Fixed / Deprecated / Removed / Security のカテゴリで分類しています。
- 各リリースはバージョンと日付で記載しています。

## [Unreleased]
（現在なし）

## [0.1.0] - 2026-03-29
初回リリース。

### Added
- パッケージ基盤
  - kabusys パッケージの初期公開。バージョンは 0.1.0。
  - モジュール公開: data, research, ai, その他基礎モジュール群を __all__ で定義。

- 設定 / 環境変数管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを追加。
  - プロジェクトルート自動検出機能を実装（.git または pyproject.toml を探索）。
  - .env の自動読み込み順序: OS 環境変数 > .env.local > .env。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能。
  - .env 行パーサーで以下に対応:
    - 空行・コメント（#）を無視
    - export KEY=val 形式をサポート
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - クォートなし値におけるインラインコメント判定（直前が空白/タブの場合のみ）
  - 環境変数未設定時に ValueError を投げる必須取得ヘルパー _require。
  - 各種設定プロパティ（J-Quants / kabu API / Slack / DB パス / 実行環境判定 / ログレベル判定）を提供。

- AI（ニュースNLP と レジーム判定）
  - kabusys.ai.news_nlp
    - raw_news と news_symbols を用い、銘柄ごとにニュースを集約して OpenAI（gpt-4o-mini）でセンチメントを評価し ai_scores テーブルへ書き込む機能を追加。
    - ニュース収集ウィンドウ（JST 基準）計算ユーティリティ calc_news_window を実装。
    - バッチ処理: 最大 20 銘柄/API コール、記事数と文字数のトリム (_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK)。
    - JSON モードのレスポンス検証と復元ロジック（前後に余計なテキストが混ざる場合は {} を抽出してパース）。
    - リトライ戦略: 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフ（設定可能）。
    - スコアは ±1.0 にクリップ。部分失敗時に既存データを保護するため DELETE → INSERT の置換戦略で冪等書き込みを実施。
    - テスト容易性確保のため OpenAI 呼び出し箇所は差し替え可能（内部関数を patch 可能に実装）。
  - kabusys.ai.regime_detector
    - ETF 1321（日経225 連動型）200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定する機能を追加。
    - マクロキーワードに基づき raw_news から記事タイトルを抽出して LLM でセンチメント評価。記事が無ければ LLM 呼び出しを行わず macro_sentiment=0.0 を利用。
    - リトライとフォールバック（API 失敗時は macro_sentiment=0.0）を実装。
    - 判定結果は market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - 決定ロジックはルックアヘッドバイアスを防ぐ設計（date < target_date 等の明示的条件）。

- データプラットフォーム（DuckDB ベース ETL / カレンダー）
  - kabusys.data.pipeline
    - ETL の高レベルインターフェースと ETLResult データクラスを実装。取得件数、保存件数、品質問題、エラー情報等を集約して返す仕組み。
    - 差分取得、バックフィル、品質チェック集約の設計に準拠した実装骨子。
  - kabusys.data.etl
    - pipeline.ETLResult を再エクスポートするインターフェースを提供。
  - kabusys.data.calendar_management
    - JPX マーケットカレンダー管理（market_calendar テーブル）と夜間バッチ更新ジョブ calendar_update_job を実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day といった営業日判定ユーティリティを提供。
    - DB にカレンダーがない場合の曜日ベースフォールバックや、DB 値優先の一貫性を確保。
    - バックフィル（直近日数の再フェッチ）、最大探索日数制限、健全性チェック（将来日付が過度に大きい場合のスキップ）を実装。
    - jquants_client を用いた取得・保存処理（fetch/save を呼び出す設計）。例外時はログを出し 0 を返すフェイルセーフ。

- 研究向けファクター群（kabusys.research）
  - factor_research
    - Momentum, Volatility, Value, Liquidity 等の定量ファクター計算を実装:
      - calc_momentum: mom_1m, mom_3m, mom_6m, ma200_dev（200 日 MA に関するデータ不足時は None）。
      - calc_volatility: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、avg_turnover、volume_ratio（データ不足時は None）。
      - calc_value: PER（EPS が 0/欠損時は None）、ROE（raw_financials から最新値を取得）。
    - DuckDB を用いた SQL 主導の計算で、外部 API 呼び出しは行わない設計。
  - feature_exploration
    - calc_forward_returns: target_date から指定ホライズン（デフォルト [1,5,21]）までの将来リターンを計算するユーティリティ。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算。有効レコードが 3 未満の場合は None を返す。
    - rank: 平均ランク（同順位は平均ランク）を返すヘルパー（丸めによる ties の抑制を実装）。
    - factor_summary: 指定カラムの count/mean/std/min/max/median を算出する統計サマリー機能。
  - kabusys.research.__init__ で主要関数群を公開（zscore_normalize は kabusys.data.stats から再エクスポート）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- .env 読み込み:
  - .env の読み込み失敗時に警告を出して処理を継続する安全策を追加（ファイルアクセスエラーを捕捉）。
  - .env のパースで不正行や空キーを正しく扱うように実装。

- AI モジュール:
  - OpenAI レスポンスが不正な JSON を返す場合の復元・フォールバック処理を追加し、パース失敗時に例外を投げず処理を継続するように改善。

- DuckDB 書き込み:
  - executemany に空リストを渡すと失敗する DuckDB の制約を回避するため、事前に空チェックを実施してから実行するようにした（部分書き込みによる既存データ保護）。

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーなどの機密情報は環境変数経由で管理する想定。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動 .env 読み込みを無効化可能（テストや CI 用）。

注記（設計上の重要点）
- ルックアヘッドバイアス防止: news_nlp / regime_detector / research の各処理は内部で datetime.today() / date.today() を参照しない設計（target_date を明示的に受け取り、DB クエリも date < target_date 等でルックアヘッドを防止）。
- フェイルセーフ: 外部 API（OpenAI / J-Quants）呼び出し失敗時は局所的にフォールバックして処理を継続する方針（例: macro_sentiment=0.0、空の取得はスキップ）。
- テスト容易性: OpenAI 呼び出し等は内部関数を patch して差し替え可能に実装している。
- 冪等性: DB への書き込みは基本的に冪等操作（DELETE→INSERT / ON CONFLICT）を採用し、部分失敗時に既存データを不必要に上書きしない工夫をしている。

今後の予定（想定）
- jquants_client の具象実装や、ETL の具体的な差分取得フロー・品質チェックの詳細を追加。
- モデルやプロンプトのチューニング、運用向け監視・メトリクス出力の整備。
- テストカバレッジ拡充（ユニットテスト・統合テスト）および CI 用ワークフロー追加。

（この CHANGELOG はコードベースから推測して記載しています。実装済み機能・挙動の確定は実際のリポジトリ履歴やドキュメントを参照してください。）