# CHANGELOG

すべての変更は Keep a Changelog 準拠で記載しています。  
このファイルはコードベースの内容から推測して作成しています。

## [Unreleased]

## [0.1.0] - 2026-04-01
初回リリース。

### Added
- パッケージ全体
  - kabusys パッケージ初版 (バージョン 0.1.0) を追加。モジュール群は data / research / ai / monitoring / execution / strategy 等を想定して公開 API を整備。
  - パッケージメタ情報: src/kabusys/__init__.py に __version__ = "0.1.0"。

- 設定・環境管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を自動読み込みする仕組みを追加。
  - プロジェクトルート検出ロジック: __file__ を起点に親ディレクトリを探索して .git または pyproject.toml を検知。
  - .env の堅牢なパーサ (_parse_env_line):
    - コメント行・空行を無視、export プレフィックスのサポート。
    - シングル/ダブルクォート内でのバックスラッシュエスケープ対応。
    - 非クォート値でのインラインコメント判定（直前が空白／タブの場合）。
  - .env 読み込みの優先順位: OS 環境変数 > .env.local > .env。OS 環境変数を保護する protected オプションを実装。
  - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラスを公開:
    - J-Quants / kabu ステーション / Slack / DB パス / 監視閾値 / システム設定（env, log_level）等のプロパティを提供。
    - env / log_level の妥当性チェック（許容値の検証）。
    - Path 型でのパス解決（expanduser サポート）。

- AI: ニュース NLP と市場レジーム判定 (src/kabusys/ai)
  - ニュースセンチメントスコアリング (news_nlp.score_news)
    - raw_news と news_symbols を集約し、銘柄ごとに記事テキストを結合して OpenAI (gpt-4o-mini, JSON mode) に送信してセンチメントを算出。
    - バッチ処理（最大 20 銘柄/リクエスト）、1 銘柄あたりの最大記事数／文字数制限でトークン増大を抑制。
    - 再試行戦略: 429 / ネットワーク断 / タイムアウト / 5xx を対象に指数バックオフでリトライ。
    - レスポンスバリデーション: JSON パースと構造検査（results 配列、code/score 構造）、未知コードは無視、スコアは ±1.0 にクリップ。
    - 書き込みは冪等化: 成功したコードのみ DELETE → INSERT（部分失敗時に既存データを保護）。DuckDB 0.10 の executemany 空リスト制約に対応。
    - タイムウィンドウ計算（calc_news_window）: JST ベースで前日 15:00 ～ 当日 08:30 を UTC に変換して厳密に扱う（ルックアヘッドバイアス回避）。
    - テスト容易性: OpenAI 呼び出し箇所を差し替え可能（内部 _call_openai_api を patchable）。
  - 市場レジーム判定 (regime_detector.score_regime)
    - ETF 1321 の 200 日移動平均乖離 (ma200_ratio) とマクロニュースの LLM センチメントを組合せて日次の市場レジームを判定（重み: MA 70% / マクロ 30%）。
    - LLM は gpt-4o-mini を使用し JSON 出力から macro_sentiment を抽出。
    - マクロ記事がない場合は LLM 呼び出しをスキップし macro_sentiment=0.0。
    - API エラー時はフォールバック (macro_sentiment=0.0) して処理を継続（例外を曝さないフェイルセーフ）。
    - 結果は market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。DB 書き込み失敗時は ROLLBACK と例外再送出。

- データプラットフォーム (src/kabusys/data)
  - カレンダー管理 (calendar_management.py)
    - JPX カレンダーの夜間バッチ更新 job (calendar_update_job) を実装。J-Quants API から差分取得して market_calendar を冪等更新。
    - 営業日判定ユーティリティ群: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB 未取得日へのフォールバックは曜日ベース（土日を休業日）で一貫性を保つ実装。
    - バックフィル、先読み、健全性チェック（将来日付の異常検出）を実装。
  - ETL パイプライン (pipeline.py / etl.py)
    - ETLResult データクラスを公開（取得件数、保存件数、品質問題リスト、エラーリスト等を含む）。
    - 差分更新・バックフィル・品質チェックを行う設計方針に対応するためのユーティリティを実装。
    - jquants_client を用いた取得／save を想定、品質チェック結果を収集して呼び出し元で判断できるように設計。

- リサーチ / ファクター計算 (src/kabusys/research)
  - factor_research モジュール:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離を計算。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から EPS/ROE を組合せて PER / ROE を計算（PBR は未実装）。
    - DuckDB を用いた SQL ベース実装。ルックアヘッドバイアス回避のため target_date 未満／以前のデータのみ参照。
  - feature_exploration モジュール:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）で将来リターンを計算。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。
    - factor_summary: 各ファクター列の基本統計量（count, mean, std, min, max, median）。
    - rank: 同順位は平均ランクを返す堅牢なランク付けユーティリティ。
  - research パッケージは主要関数を __all__ で再公開し、zscore_normalize を data.stats から再エクスポート。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Security
- 初回リリースのため該当なし。

### Notes / 設計上の重要な点
- ルックアヘッドバイアス対策:
  - target_date を明示的に受け取り、内部で datetime.today()/date.today() に依存しない設計。
  - prices_daily 等のクエリは target_date 未満・以前のデータのみを参照するよう注意が払われている。
- OpenAI との連携:
  - JSON mode を使用し厳密な JSON 出力を期待するプロンプトを設定。
  - LLM 呼び出しは冪等性やテスト容易性を考慮して内部関数を分離（patch で差し替え可能）。
  - API 障害に対しては明示的なフォールバック（スコア 0.0 や処理スキップ）を実装し、ETL/分析を止めない設計。
- DuckDB 互換性:
  - DuckDB のバージョン差分を考慮した実装（executemany の空リスト回避など）。
- 外部依存抑制:
  - 特に research モジュールは pandas 等の外部ライブラリに依存せず標準ライブラリと DuckDB のみで実装。
- テストしやすさ:
  - OpenAI 呼び出し等の箇所は差し替え可能にしてユニットテストでモックしやすくしている。

### Known limitations / 今後の改善候補（推測）
- ai/news_nlp の出力スキーマやモデルのバージョン変更に対する互換性対応が将来的に必要。
- calc_value では PBR・配当利回りが未実装。将来的に追加予定。
- jquants_client の具体的実装は外部依存のため、API 仕様変更時に pipeline/calendar の修正が必要。
- エラーハンドリングの粒度や監視・アラートの強化（Slack 通知等）は運用要件により拡張可能。

---

以上。必要であれば、各機能ごとのより詳細な変更点（関数単位の説明や想定される入力/出力スキーマ）を追記します。どの粒度を希望しますか？