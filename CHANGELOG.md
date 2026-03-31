CHANGELOG
=========

このファイルは「Keep a Changelog」形式に準拠しており、重要な変更点をバージョンごとに記録します。  
（コードベースからの推測に基づき作成しています）

Unreleased
----------

- 今後の変更を記載します。

[0.1.0] - 2026-03-31
-------------------

Added
- 初回リリース: 基本的な日本株自動売買システムパッケージ "kabusys" を追加。
  - パッケージ公開 API: kabusys.__init__ で data, strategy, execution, monitoring を公開。

- 環境設定管理（src/kabusys/config.py）
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - 読み込みの優先度: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - 強化された .env パーサ: export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの扱いなどに対応。
  - 環境変数取得用 Settings クラスを提供（必須チェック、デフォルト値、型変換、検証ロジックを含む）。
    - J-Quants / kabuステーション / Slack / DB パス / 監視設定 / ログレベル / 環境モード（development/paper_trading/live）等をプロパティとして提供。
    - 不正な値は ValueError で明示。

- AI モジュール（src/kabusys/ai）
  - ニュースセンチメントスコアリング（news_nlp.score_news）
    - raw_news / news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini, JSON mode）へバッチ送信して銘柄ごとのスコアを ai_scores に書き込む。
    - チャンク処理（最大 20 銘柄/チャンク）、1銘柄当たりの記事数と文字数のトリム（上限あり）によりプロンプト肥大化を抑制。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライを実装。
    - レスポンスを厳格にバリデーション（JSON 抽出、results 配列、code の照合、数値検証、±1.0 でクリップ）。
    - 部分失敗があっても他銘柄の既存スコアを保護するため、取得できたコード群のみ DELETE→INSERT を行う（DuckDB の executemany 空リスト対応を考慮）。
    - タイムウィンドウは JST ベースで定義（前日 15:00 ～ 当日 08:30、内部は UTC naive で扱う）で、ルックアヘッドバイアスを防止。

  - 市場レジーム判定（regime_detector.score_regime）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次でレジーム（bull/neutral/bear）を判定。
    - マクロニュース抽出はキーワードベース（複数キーワードリスト）で最大記事件数を制限。
    - OpenAI 呼び出しは専用関数を使用し、API エラー時は macro_sentiment を 0.0 にフォールバックするフェイルセーフを実装。
    - 結果は market_regime テーブルに対して冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。DB 書き込み失敗時は ROLLBACK を試行して例外を伝播。

- Research モジュール（src/kabusys/research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離率（ma200_dev）を計算。データ不足時の扱いを明確化。
    - calc_volatility: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算。true_range の NULL 伝播を適切に扱う。
    - calc_value: raw_financials から直近財務データを取得し PER / ROE を計算（EPS が 0/欠損の場合は None）。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一度のクエリで取得する実装。ホライズンの検証を実施。
    - calc_ic: Spearman ランク相関（IC）を実装。必要レコード数が不足する場合は None を返す。
    - rank / factor_summary: 同順位の平均ランク処理、基本統計量（count/mean/std/min/max/median）を標準ライブラリだけで実装。
  - zscore_normalize を data.stats から再エクスポート（研究向けユーティリティ）。

- Data モジュール（src/kabusys/data）
  - calendar_management:
    - JPX カレンダー管理ロジック（market_calendar テーブル参照）。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。DB 登録優先、未登録日は曜日ベースでフォールバック。
    - calendar_update_job: J-Quants クライアントから差分取得し冪等保存。バックフィルと健全性チェックを実装。
  - ETL パイプライン（pipeline.py / etl.py）
    - ETLResult データクラスを公開。ETL の取得数・保存数・品質問題・エラーの集約をサポート。
    - 差分更新・バックフィル・品質チェックの方針を実装（概要）。jquants_client と quality モジュールとの連携を想定。
  - jquants_client の呼び出し箇所が存在し、API 連携ポイントを設計。

- ロギング、例外処理、安全設計
  - 各所で logger を利用し情報／警告／例外ログを出力。
  - ルックアヘッドバイアス防止のため、内部処理で datetime.today()/date.today() の直接参照を避ける設計方針を明示（target_date 引数ベース）。
  - OpenAI/API 呼び出しでのフェイルセーフ（スコア 0.0 で継続）、およびリトライ戦略を採用。

Changed
- 該当なし（初回リリースのため、変更履歴無し）。

Fixed
- 該当なし（初回リリースのため、修正履歴無し）。

Notes / 設計上の注意
- DuckDB に対する executemany の空リスト取り扱いなど、特定バージョンの挙動を考慮した実装上の防御コードを含む。
- OpenAI のレスポンスを厳密な JSON として期待するが、実運用では前後テキスト混入の可能性を考慮して JSON 部分抽出ロジックを実装している。
- 一部モジュールは外部クライアント（jquants_client, OpenAI）への依存があるため、テスト時は依存部分をモックすることを想定している（コード中に差し替えを想定したコメントあり）。

References
- 実装ファイル（推定）:
  - src/kabusys/config.py
  - src/kabusys/ai/news_nlp.py
  - src/kabusys/ai/regime_detector.py
  - src/kabusys/research/*.py
  - src/kabusys/data/*.py
  - src/kabusys/data/pipeline.py, src/kabusys/data/etl.py

（この CHANGELOG はコード内容から推測して作成しています。追加のリリースノートや破壊的変更などの詳細は、実際のコミット履歴やリリース文書に基づき追記してください。）